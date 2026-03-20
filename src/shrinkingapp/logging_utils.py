from __future__ import annotations

import logging
from pathlib import Path


def derive_log_path(output_image: Path, explicit_path: Path | None = None) -> Path:
    if explicit_path is not None:
        explicit_path.parent.mkdir(parents=True, exist_ok=True)
        return explicit_path
    log_path = Path(f"{output_image}.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return log_path


def derive_manifest_path(output_image: Path) -> Path:
    manifest_path = Path(f"{output_image}.manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    return manifest_path


def setup_job_logger(name: str, log_path: Path) -> logging.Logger:
    logger_name = f"{name}:{log_path}"
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger

