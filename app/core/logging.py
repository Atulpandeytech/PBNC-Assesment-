import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict
from contextvars import ContextVar

# Context variables for request and document correlation IDs
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="none")
document_id_ctx: ContextVar[str] = ContextVar("document_id", default="none")

SENSITIVE_KEYS = {"password", "secret", "token", "key", "authorization", "api_key", "gemini_api_key"}


class JSONLogFormatter(logging.Formatter):
    """Formats log records as structured JSON with correlation IDs and redaction."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_ctx.get(),
            "document_id": document_id_ctx.get(),
        }

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        # Include custom extra fields if provided
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and key not in log_payload:
                if any(s in key.lower() for s in SENSITIVE_KEYS):
                    log_payload[key] = "***REDACTED***"
                else:
                    log_payload[key] = value

        return json.dumps(log_payload, default=str)


def setup_logging(debug: bool = False) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Remove existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(JSONLogFormatter())
    root_logger.addHandler(stream_handler)

    # Quiet external noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)


logger = logging.getLogger("pragati_bharti")
