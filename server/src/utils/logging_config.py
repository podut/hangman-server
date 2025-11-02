"""Logging configuration with structured JSON formatting."""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    
    Outputs logs as JSON objects with:
    - timestamp: ISO 8601 format
    - level: log level name
    - logger: logger name
    - message: log message
    - request_id: if available in extra
    - Additional fields from 'extra' parameter
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log structure
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add request_id if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Add event type if present
        if hasattr(record, "event"):
            log_data["event"] = record.event
        
        # Add other extra fields (excluding internal logging fields)
        excluded_fields = {
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "message", "pathname", "process", "processName",
            "relativeCreated", "thread", "threadName", "exc_info",
            "exc_text", "stack_info", "request_id", "event"
        }
        
        for key, value in record.__dict__.items():
            if key not in excluded_fields and not key.startswith("_"):
                log_data[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """
    Colored formatter for console output (non-JSON).
    
    Adds colors to log levels for better readability in development.
    """
    
    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        # Add request_id to message if present
        if hasattr(record, "request_id"):
            original_msg = record.getMessage()
            record.msg = f"[{record.request_id}] {original_msg}"
            record.args = ()
        
        return super().format(record)


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """
    Configure application logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ('json' or 'text')
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Set formatter based on format type
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = ColoredFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    
    # Log configuration
    root_logger.info(
        f"Logging configured: level={log_level}, format={log_format}",
        extra={"event": "logging_configured"}
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
