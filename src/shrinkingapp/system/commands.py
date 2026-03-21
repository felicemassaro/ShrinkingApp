from __future__ import annotations

import os
import signal
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


CommandArg = str | os.PathLike[str]
StreamCallback = Callable[[str, str], None]
_ACTIVE_PROCESSES: set[subprocess.Popen[str]] = set()
_ACTIVE_PROCESSES_LOCK = threading.Lock()


@dataclass(slots=True)
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str


class CommandError(RuntimeError):
    def __init__(self, result: CommandResult):
        joined = " ".join(result.args)
        super().__init__(f"Command failed with exit code {result.returncode}: {joined}")
        self.result = result


def _register_process(process: subprocess.Popen[str]) -> None:
    with _ACTIVE_PROCESSES_LOCK:
        _ACTIVE_PROCESSES.add(process)


def _unregister_process(process: subprocess.Popen[str]) -> None:
    with _ACTIVE_PROCESSES_LOCK:
        _ACTIVE_PROCESSES.discard(process)


def terminate_process_tree(
    process: subprocess.Popen[str],
    *,
    grace_seconds: float = 3.0,
    logger=None,
) -> None:
    if process.poll() is not None:
        return

    if logger is not None:
        logger.info("Terminating active command tree for pid=%s", process.pid)

    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except ProcessLookupError:
        return

    try:
        process.wait(timeout=grace_seconds)
        return
    except subprocess.TimeoutExpired:
        if logger is not None:
            logger.warning("Command tree pid=%s did not exit after SIGTERM; forcing SIGKILL", process.pid)

    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except ProcessLookupError:
        return


def terminate_active_processes(*, grace_seconds: float = 3.0, logger=None) -> None:
    with _ACTIVE_PROCESSES_LOCK:
        active_processes = list(_ACTIVE_PROCESSES)

    for process in active_processes:
        terminate_process_tree(process, grace_seconds=grace_seconds, logger=logger)


def require_commands(commands: Sequence[str]) -> None:
    missing = [command for command in commands if shutil.which(command) is None]
    if missing:
        raise RuntimeError(f"Missing required commands: {', '.join(sorted(missing))}")


def run_command(
    args: Sequence[CommandArg],
    *,
    check: bool = True,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    logger=None,
    input_text: str | None = None,
    stream_callback: StreamCallback | None = None,
) -> CommandResult:
    argv = [os.fspath(arg) for arg in args]
    if logger is not None:
        logger.info("$ %s", " ".join(argv))

    process = subprocess.Popen(
        argv,
        cwd=os.fspath(cwd) if cwd is not None else None,
        env=env,
        stdin=subprocess.PIPE if input_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    _register_process(process)

    try:
        if input_text is not None and process.stdin is not None:
            process.stdin.write(input_text)
            process.stdin.close()

        stdout_parts: list[str] = []
        stderr_parts: list[str] = []

        def emit(kind: str, text: str) -> None:
            if not text:
                return
            if logger is not None:
                logger.info("%s: %s", kind, text)
            if stream_callback is not None:
                stream_callback(kind, text)

        def consume(stream, sink: list[str], kind: str) -> None:
            buffer: list[str] = []
            while True:
                chunk = stream.read(1)
                if chunk == "":
                    break
                sink.append(chunk)
                if chunk in ("\n", "\r"):
                    line = "".join(buffer).rstrip("\r\n")
                    emit(kind, line)
                    buffer.clear()
                else:
                    buffer.append(chunk)
            if buffer:
                emit(kind, "".join(buffer))

        stdout_thread = threading.Thread(
            target=consume,
            args=(process.stdout, stdout_parts, "stdout"),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=consume,
            args=(process.stderr, stderr_parts, "stderr"),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()
        returncode = process.wait()
        stdout_thread.join()
        stderr_thread.join()

        result = CommandResult(
            args=argv,
            returncode=returncode,
            stdout="".join(stdout_parts),
            stderr="".join(stderr_parts),
        )

        if check and result.returncode != 0:
            raise CommandError(result)
        return result
    finally:
        _unregister_process(process)


def detect_tool_versions(commands: Sequence[str]) -> dict[str, str | None]:
    version_args = ("--version", "-V", "-v")
    versions: dict[str, str | None] = {}
    for command in commands:
        versions[command] = None
        for flag in version_args:
            try:
                result = run_command([command, flag], check=False)
            except OSError:
                break
            if result.returncode != 0:
                continue
            output = (result.stdout or result.stderr).strip()
            if output:
                versions[command] = output.splitlines()[0]
                break
    return versions
