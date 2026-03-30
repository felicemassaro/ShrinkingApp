from __future__ import annotations

import json
import os
import re
import sys

from PySide6 import QtCore


_PHASE_PATTERN = re.compile(r"\bPHASE\s+([a-z0-9-]+)(?:\s+(.*))?$", re.IGNORECASE)
_DD_PROGRESS_PATTERN = re.compile(
    r"stderr:\s+(\d+)\s+bytes\b.*copied,\s+([0-9.]+)\s+s,\s+([0-9.]+)\s+([kMGT]?B/s)",
    re.IGNORECASE,
)
_RESIZE_PROGRESS_PATTERN = re.compile(
    r"stdout:\s+(Relocating blocks|Scanning inode table)\s+([\-X]+)$",
    re.IGNORECASE,
)

_PHASE_PROGRESS = {
    "prepare": 5,
    "inspect": 10,
    "filesystem-check": 20,
    "filesystem-shrink": 30,
    "filesystem-patch": 65,
    "partition-shrink": 75,
    "truncate": 85,
    "compress": 92,
    "finalize": 97,
    "done": 100,
}


def _speed_to_bytes_per_second(value: float, unit: str) -> float:
    multipliers = {
        "B/s": 1.0,
        "kB/s": 1_000.0,
        "MB/s": 1_000_000.0,
        "GB/s": 1_000_000_000.0,
        "TB/s": 1_000_000_000_000.0,
    }
    return value * multipliers.get(unit, 1.0)


class JobProcessController(QtCore.QObject):
    job_started = QtCore.Signal(str)
    job_phase = QtCore.Signal(str, str)
    job_percent = QtCore.Signal(int)
    job_log = QtCore.Signal(str)
    job_progress = QtCore.Signal(object, object, object, object)
    job_finished = QtCore.Signal(bool, object, str, bool)
    job_running_changed = QtCore.Signal(bool)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._process = QtCore.QProcess(self)
        self._process.setProcessChannelMode(QtCore.QProcess.SeparateChannels)
        self._process.started.connect(self._on_started)
        self._process.errorOccurred.connect(self._on_process_error)
        self._process.readyReadStandardError.connect(self._on_ready_stderr)
        self._process.readyReadStandardOutput.connect(self._on_ready_stdout)
        self._process.finished.connect(self._on_finished)
        self._abort_timer = QtCore.QTimer(self)
        self._abort_timer.setSingleShot(True)
        self._abort_timer.timeout.connect(self._force_kill)

        self._stderr_buffer = ""
        self._stdout_buffer = ""
        self._stderr_lines: list[str] = []
        self._job_total_bytes: int | None = None
        self._job_title = ""
        self._abort_requested = False
        self._completion_emitted = False

    def is_running(self) -> bool:
        return self._process.state() != QtCore.QProcess.NotRunning

    def start_job(self, *, title: str, cli_args: list[str], total_bytes: int | None = None) -> None:
        if self.is_running():
            raise RuntimeError("A job is already running.")

        self._stderr_buffer = ""
        self._stdout_buffer = ""
        self._stderr_lines = []
        self._job_total_bytes = total_bytes
        self._job_title = title
        self._abort_requested = False
        self._completion_emitted = False
        self._abort_timer.stop()

        if os.geteuid() == 0:
            program = sys.executable
            arguments = ["-m", "shrinkingapp.app", *cli_args]
        else:
            program = "pkexec"
            arguments = [sys.executable, "-m", "shrinkingapp.app", *cli_args]

        self.job_running_changed.emit(True)
        self._process.start(program, arguments)

    def abort_job(self) -> None:
        if not self.is_running() or self._abort_requested:
            return
        self._abort_requested = True
        self.job_phase.emit("Aborting", "stopping backend job")
        self.job_log.emit("Abort requested by user.")
        self._process.terminate()
        self._abort_timer.start(3000)

    def _force_kill(self) -> None:
        if not self.is_running():
            return
        self.job_log.emit("Backend job did not exit after SIGTERM; forcing termination.")
        self._process.kill()

    def _on_started(self) -> None:
        self.job_started.emit(self._job_title)

    def _on_process_error(self, error: QtCore.QProcess.ProcessError) -> None:
        if self._completion_emitted:
            return
        if error != QtCore.QProcess.ProcessError.FailedToStart:
            self.job_log.emit(f"Backend process error: {self._process.errorString()}")
            return

        self._completion_emitted = True
        self._abort_timer.stop()
        error_text = self._process.errorString() or "The backend command failed to start."
        if self._stderr_lines:
            error_text = f"{error_text}\n\n" + "\n".join(self._stderr_lines[-20:])
        self._stderr_buffer = ""
        self._stdout_buffer = ""
        self._abort_requested = False
        self.job_running_changed.emit(False)
        self.job_finished.emit(False, None, error_text, False)

    def _emit_stderr_lines(self, text: str) -> None:
        self._stderr_buffer += text
        while True:
            newline_index = min(
                [index for index in (self._stderr_buffer.find("\n"), self._stderr_buffer.find("\r")) if index != -1],
                default=-1,
            )
            if newline_index == -1:
                break
            line = self._stderr_buffer[:newline_index].rstrip("\r\n")
            self._stderr_buffer = self._stderr_buffer[newline_index + 1 :]
            if line:
                self._stderr_lines.append(line)
                self._handle_log_line(line)

    def _emit_stdout_lines(self, text: str) -> None:
        self._stdout_buffer += text

    def _handle_log_line(self, line: str) -> None:
        self.job_log.emit(line)

        phase_match = _PHASE_PATTERN.search(line)
        if phase_match:
            raw_phase = phase_match.group(1).lower()
            phase = raw_phase.replace("-", " ").title()
            detail = (phase_match.group(2) or "").strip()
            self.job_phase.emit(phase, detail)
            phase_percent = _PHASE_PROGRESS.get(raw_phase)
            if phase_percent is not None:
                self.job_percent.emit(phase_percent)

        progress_match = _DD_PROGRESS_PATTERN.search(line)
        if progress_match and self._job_total_bytes:
            copied = int(progress_match.group(1))
            speed_value = float(progress_match.group(3))
            speed_bps = _speed_to_bytes_per_second(speed_value, progress_match.group(4))
            eta = 0.0
            if speed_bps > 0 and copied < self._job_total_bytes:
                eta = (self._job_total_bytes - copied) / speed_bps
            self.job_progress.emit(copied, self._job_total_bytes, speed_bps, eta)

        resize_match = _RESIZE_PROGRESS_PATTERN.search(line)
        if resize_match:
            stage = resize_match.group(1).lower()
            bar = resize_match.group(2)
            total_slots = bar.count("-") + bar.count("X")
            if total_slots <= 0:
                return
            completed_slots = bar.count("X")
            if stage == "relocating blocks":
                base_percent = 30
                span_percent = 25
            else:
                base_percent = 55
                span_percent = 10
            percent = base_percent + int((completed_slots / total_slots) * span_percent)
            self.job_percent.emit(min(100, max(0, percent)))

    def _on_ready_stderr(self) -> None:
        data = bytes(self._process.readAllStandardError()).decode("utf-8", errors="replace")
        self._emit_stderr_lines(data)

    def _on_ready_stdout(self) -> None:
        data = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._emit_stdout_lines(data)

    def _on_finished(self, exit_code: int, exit_status: QtCore.QProcess.ExitStatus) -> None:
        if self._completion_emitted:
            self._completion_emitted = False
            self._stderr_buffer = ""
            self._stdout_buffer = ""
            self._stderr_lines = []
            self._job_title = ""
            return
        self._abort_timer.stop()
        if self._stderr_buffer.strip():
            trailing = self._stderr_buffer.strip()
            self._stderr_lines.append(trailing)
            self._handle_log_line(trailing)
        self._stderr_buffer = ""

        success = exit_status == QtCore.QProcess.NormalExit and exit_code == 0
        aborted = self._abort_requested and not success
        summary = None
        error_text = ""
        stdout_text = self._stdout_buffer.strip()

        if success and stdout_text:
            try:
                summary = json.loads(stdout_text)
            except json.JSONDecodeError:
                summary = {"raw_stdout": stdout_text}
        elif aborted:
            error_text = "Job aborted by user."
        elif not success:
            if stdout_text:
                error_text = stdout_text
            elif self._stderr_lines:
                error_text = "\n".join(self._stderr_lines[-20:])
            else:
                error_text = "The backend command failed."

        self._abort_requested = False
        self._job_title = ""
        self.job_running_changed.emit(False)
        self.job_finished.emit(success, summary, error_text, aborted)
