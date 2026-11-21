import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_NOISY_LIBS = ("httpx", "httpcore", "urllib3", "sentence_transformers", "huggingface_hub", "qdrant_client")


def setup_logging(level: str = "INFO", log_file: str | None = None) -> None:
    formatter = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
        )
    for handler in handlers:
        handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers = handlers

    for name in _NOISY_LIBS:
        logging.getLogger(name).setLevel(logging.WARNING)
