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
    job_log = QtCore.Signal(str)
    job_progress = QtCore.Signal(int, int, float, float)
    job_finished = QtCore.Signal(bool, object, str)
    job_running_changed = QtCore.Signal(bool)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._process = QtCore.QProcess(self)
        self._process.setProcessChannelMode(QtCore.QProcess.SeparateChannels)
        self._process.readyReadStandardError.connect(self._on_ready_stderr)
        self._process.readyReadStandardOutput.connect(self._on_ready_stdout)
        self._process.finished.connect(self._on_finished)

        self._stderr_buffer = ""
        self._stdout_buffer = ""
        self._stderr_lines: list[str] = []
        self._job_total_bytes: int | None = None

    def is_running(self) -> bool:
        return self._process.state() != QtCore.QProcess.NotRunning

    def start_job(self, *, title: str, cli_args: list[str], total_bytes: int | None = None) -> None:
        if self.is_running():
            raise RuntimeError("A job is already running.")

        self._stderr_buffer = ""
        self._stdout_buffer = ""
        self._stderr_lines = []
        self._job_total_bytes = total_bytes

        if os.geteuid() == 0:
            program = sys.executable
            arguments = ["-m", "shrinkingapp.app", *cli_args]
        else:
            program = "pkexec"
            arguments = [sys.executable, "-m", "shrinkingapp.app", *cli_args]

        self.job_started.emit(title)
        self.job_running_changed.emit(True)
        self._process.start(program, arguments)

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
            phase = phase_match.group(1).replace("-", " ").title()
            detail = (phase_match.group(2) or "").strip()
            self.job_phase.emit(phase, detail)

        progress_match = _DD_PROGRESS_PATTERN.search(line)
        if progress_match and self._job_total_bytes:
            copied = int(progress_match.group(1))
            speed_value = float(progress_match.group(3))
            speed_bps = _speed_to_bytes_per_second(speed_value, progress_match.group(4))
            eta = 0.0
            if speed_bps > 0 and copied < self._job_total_bytes:
                eta = (self._job_total_bytes - copied) / speed_bps
            self.job_progress.emit(copied, self._job_total_bytes, speed_bps, eta)

    def _on_ready_stderr(self) -> None:
        data = bytes(self._process.readAllStandardError()).decode("utf-8", errors="replace")
        self._emit_stderr_lines(data)

    def _on_ready_stdout(self) -> None:
        data = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._emit_stdout_lines(data)

    def _on_finished(self, exit_code: int, exit_status: QtCore.QProcess.ExitStatus) -> None:
        if self._stderr_buffer.strip():
            trailing = self._stderr_buffer.strip()
            self._stderr_lines.append(trailing)
            self._handle_log_line(trailing)
        self._stderr_buffer = ""

        success = exit_status == QtCore.QProcess.NormalExit and exit_code == 0
        summary = None
        error_text = ""
        stdout_text = self._stdout_buffer.strip()

        if success and stdout_text:
            try:
                summary = json.loads(stdout_text)
            except json.JSONDecodeError:
                summary = {"raw_stdout": stdout_text}
        elif not success:
            if stdout_text:
                error_text = stdout_text
            elif self._stderr_lines:
                error_text = "\n".join(self._stderr_lines[-20:])
            else:
                error_text = "The backend command failed."

        self.job_running_changed.emit(False)
        self.job_finished.emit(success, summary, error_text)
