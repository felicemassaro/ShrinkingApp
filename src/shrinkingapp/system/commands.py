from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


CommandArg = str | os.PathLike[str]


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
) -> CommandResult:
    argv = [os.fspath(arg) for arg in args]
    if logger is not None:
        logger.info("$ %s", " ".join(argv))

    completed = subprocess.run(
        argv,
        cwd=os.fspath(cwd) if cwd is not None else None,
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )

    result = CommandResult(
        args=argv,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )

    if logger is not None:
        if result.stdout.strip():
            for line in result.stdout.rstrip().splitlines():
                logger.info("stdout: %s", line)
        if result.stderr.strip():
            for line in result.stderr.rstrip().splitlines():
                logger.info("stderr: %s", line)

    if check and result.returncode != 0:
        raise CommandError(result)
    return result


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
            output = (result.stdout or result.stderr).strip()
            if output:
                versions[command] = output.splitlines()[0]
                break
    return versions

