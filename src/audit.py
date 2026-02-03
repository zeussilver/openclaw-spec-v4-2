"""Audit logging for OpenClaw skill lifecycle operations."""

from datetime import datetime, timezone
from pathlib import Path


class AuditLogger:
    """Logs skill lifecycle operations to an audit file.

    Log format: ISO8601_TIMESTAMP [OPERATION] key1=value1 key2=value2
    Example: 2026-02-01T10:00:00Z [ROLLBACK] skill=text_echo from=1.0.0 to=0.9.0

    Operations: GENERATE, AST_GATE, SANDBOX, STAGING, PROMOTE, ROLLBACK, DISABLE
    """

    def __init__(self, log_path: Path) -> None:
        """Initialize audit logger with the path to the audit log file."""
        self.log_path = log_path

    def log(self, operation: str, **kwargs: str | int | float | bool | None) -> None:
        """Append an audit log entry.

        Args:
            operation: The operation name (e.g., ROLLBACK, PROMOTE, DISABLE)
            **kwargs: Key-value pairs to include in the log entry.
                      Values containing spaces will be quoted.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Format key=value pairs, quoting values with spaces
        pairs = []
        for key, value in kwargs.items():
            if value is None:
                continue
            str_value = str(value)
            # Quote values containing spaces
            if " " in str_value:
                str_value = f'"{str_value}"'
            pairs.append(f"{key}={str_value}")

        # Build log line
        kv_string = " ".join(pairs)
        if kv_string:
            log_line = f"{timestamp} [{operation}] {kv_string}\n"
        else:
            log_line = f"{timestamp} [{operation}]\n"

        # Ensure parent directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Append to file (create if not exists)
        with open(self.log_path, "a") as f:
            f.write(log_line)
