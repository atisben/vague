"""Local logging for vague.

Off by default. Opt in by setting VAGUE_LOG=debug|info|warning. Logs are written
to ~/.vague/logs/vague.log (rotating), which survives across the short-lived
`vague` subprocesses an LLM runtime spawns. Set VAGUE_LOG_STDERR=1 to also echo
to stderr when running vague by hand.

Nothing is ever sent off the machine. See docs/telemetry.md.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "warn": logging.WARNING,
    "error": logging.ERROR,
}
_OFF = {"", "off", "none", "0", "false"}
_LOGGER_NAME = "vague"


def _home() -> Path:
    return Path(os.environ.get("VAGUE_HOME", Path.home() / ".vague"))


def get_logger() -> logging.Logger:
    """Return the configured `vague` logger. Configures once per process."""
    logger = logging.getLogger(_LOGGER_NAME)
    if getattr(logger, "_vague_configured", False):
        return logger
    logger._vague_configured = True  # type: ignore[attr-defined]
    logger.propagate = False

    level_name = os.environ.get("VAGUE_LOG", "").strip().lower()
    if level_name in _OFF:
        logger.addHandler(logging.NullHandler())
        return logger

    logger.setLevel(_LEVELS.get(level_name, logging.INFO))
    fmt = logging.Formatter("%(asctime)s pid=%(process)d %(levelname)s %(name)s %(message)s")

    try:
        log_path = _home() / "logs" / "vague.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        # Never let logging setup break a command.
        pass

    if os.environ.get("VAGUE_LOG_STDERR", "").strip().lower() in ("1", "true", "yes"):
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)

    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


def reset_logging() -> None:
    """Tear down handlers and force reconfiguration. For tests only."""
    logger = logging.getLogger(_LOGGER_NAME)
    for h in list(logger.handlers):
        logger.removeHandler(h)
    if hasattr(logger, "_vague_configured"):
        delattr(logger, "_vague_configured")
