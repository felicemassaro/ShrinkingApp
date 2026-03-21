from __future__ import annotations


def log_phase(logger, phase: str, detail: str | None = None) -> None:
    message = f"PHASE {phase}"
    if detail:
        message = f"{message} {detail}"
    logger.info(message)
