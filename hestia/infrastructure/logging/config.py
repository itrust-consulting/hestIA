from __future__ import annotations

import datetime
import json
import logging
import logging.handlers
import pathlib
import queue
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hestia.config.settings import Settings

# ---------------------------------------------------------------------------
# Shared context variable — populated by CorrelationMiddleware per request
# ---------------------------------------------------------------------------

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# ---------------------------------------------------------------------------
# Standard LogRecord attributes to exclude from the JSON extra fields
# ---------------------------------------------------------------------------

_SKIP_ATTRS = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime", "taskName",
    "request_id",  # handled explicitly in the formatter
})

# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        data: dict = {
            "ts": datetime.datetime.utcfromtimestamp(record.created).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),  # stamped by _RequestIdFilter
            "msg": record.getMessage(),
        }
        for key, val in record.__dict__.items():
            if key not in _SKIP_ATTRS and not key.startswith("_"):
                data[key] = val
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, default=str, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Request-id filter — runs in the caller's context before the record is
# queued, so the ContextVar is still accessible.  The background formatter
# thread then reads record.request_id instead of the ContextVar directly.
# ---------------------------------------------------------------------------

class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


# ---------------------------------------------------------------------------
# Routing filters — keep system and audit streams separate in one queue
# ---------------------------------------------------------------------------

class _AuditFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith("hestia.audit")


class _SystemFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not record.name.startswith("hestia.audit")


# ---------------------------------------------------------------------------
# Setup — called once at app startup
# ---------------------------------------------------------------------------

_listener: logging.handlers.QueueListener | None = None


def setup_logging(settings: "Settings") -> None:
    global _listener

    log_dir = pathlib.Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    json_fmt = _JsonFormatter()

    # system.log — size-rotated, excludes audit records
    system_fh = logging.handlers.RotatingFileHandler(
        log_dir / "system.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    system_fh.setFormatter(json_fmt)
    system_fh.setLevel(level)
    system_fh.addFilter(_SystemFilter())

    # audit.log — time-rotated (daily), 90-day retention, audit records only
    audit_fh = logging.handlers.TimedRotatingFileHandler(
        log_dir / "audit.log",
        when="midnight",
        interval=1,
        backupCount=90,
        encoding="utf-8",
        utc=True,
    )
    audit_fh.setFormatter(json_fmt)
    audit_fh.setLevel(logging.INFO)
    audit_fh.addFilter(_AuditFilter())

    handlers: list[logging.Handler] = [system_fh, audit_fh]

    if settings.log_to_console:
        console_fh = logging.StreamHandler()
        console_fh.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s  %(message)s", datefmt="%H:%M:%S")
        )
        console_fh.setLevel(level)
        console_fh.addFilter(_SystemFilter())
        handlers.append(console_fh)

    # Single queue → single background thread → all handlers
    log_queue: queue.Queue = queue.Queue(maxsize=-1)
    queue_handler = logging.handlers.QueueHandler(log_queue)
    # Filter must live on the handler, not the logger — propagated records skip
    # parent logger filters and go straight to callHandlers(), so only handler
    # filters are guaranteed to run for every record that passes through.
    queue_handler.addFilter(_RequestIdFilter())

    _listener = logging.handlers.QueueListener(log_queue, *handlers, respect_handler_level=True)
    _listener.start()

    # hestia.* is the root for all app loggers
    hestia_logger = logging.getLogger("hestia")
    hestia_logger.setLevel(logging.DEBUG)
    hestia_logger.addHandler(queue_handler)
    hestia_logger.propagate = False


def shutdown_logging() -> None:
    if _listener:
        _listener.stop()
