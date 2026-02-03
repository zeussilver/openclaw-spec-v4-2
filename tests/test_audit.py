"""Tests for audit logging functionality."""

import re
from pathlib import Path

from src.audit import AuditLogger


class TestAuditLogger:
    """Test cases for AuditLogger class."""

    def test_creates_file_if_not_exists(self, tmp_path: Path) -> None:
        """Test that audit logger creates the log file if it doesn't exist."""
        log_path = tmp_path / "audit.log"
        assert not log_path.exists()

        logger = AuditLogger(log_path)
        logger.log("TEST", key="value")

        assert log_path.exists()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that audit logger creates parent directories if needed."""
        log_path = tmp_path / "nested" / "dir" / "audit.log"
        assert not log_path.parent.exists()

        logger = AuditLogger(log_path)
        logger.log("TEST", key="value")

        assert log_path.exists()

    def test_appends_without_overwriting(self, tmp_path: Path) -> None:
        """Test that multiple log calls append rather than overwrite."""
        log_path = tmp_path / "audit.log"
        logger = AuditLogger(log_path)

        logger.log("FIRST", key="value1")
        logger.log("SECOND", key="value2")
        logger.log("THIRD", key="value3")

        content = log_path.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 3
        assert "[FIRST]" in lines[0]
        assert "[SECOND]" in lines[1]
        assert "[THIRD]" in lines[2]

    def test_correct_format_with_timestamp(self, tmp_path: Path) -> None:
        """Test that log format matches: ISO8601_TIMESTAMP [OPERATION] key=value."""
        log_path = tmp_path / "audit.log"
        logger = AuditLogger(log_path)

        logger.log("PROMOTE", skill="text_echo", version="1.0.0")

        content = log_path.read_text().strip()
        # ISO8601 timestamp pattern: 2026-02-01T10:00:00Z
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z \[PROMOTE\] skill=text_echo version=1\.0\.0$"
        assert re.match(pattern, content), f"Log line doesn't match expected format: {content}"

    def test_rollback_event_format(self, tmp_path: Path) -> None:
        """Test ROLLBACK event log format."""
        log_path = tmp_path / "audit.log"
        logger = AuditLogger(log_path)

        logger.log("ROLLBACK", skill="text_echo", **{"from": "1.0.0"}, to="0.9.0")

        content = log_path.read_text().strip()
        assert "[ROLLBACK]" in content
        assert "skill=text_echo" in content
        assert "from=1.0.0" in content
        assert "to=0.9.0" in content

    def test_promote_event_format(self, tmp_path: Path) -> None:
        """Test PROMOTE event log format."""
        log_path = tmp_path / "audit.log"
        logger = AuditLogger(log_path)

        logger.log("PROMOTE", skill="text_echo", version="1.0.0", gates="replay,regression,redteam")

        content = log_path.read_text().strip()
        assert "[PROMOTE]" in content
        assert "skill=text_echo" in content
        assert "version=1.0.0" in content
        assert "gates=replay,regression,redteam" in content

    def test_disable_event_format(self, tmp_path: Path) -> None:
        """Test DISABLE event log format."""
        log_path = tmp_path / "audit.log"
        logger = AuditLogger(log_path)

        logger.log("DISABLE", skill="text_echo", version="1.0.0", reason="Rollback to 0.9.0")

        content = log_path.read_text().strip()
        assert "[DISABLE]" in content
        assert "skill=text_echo" in content
        assert "version=1.0.0" in content

    def test_special_characters_in_values_spaces(self, tmp_path: Path) -> None:
        """Test that values with spaces are properly quoted."""
        log_path = tmp_path / "audit.log"
        logger = AuditLogger(log_path)

        logger.log("DISABLE", skill="text_echo", reason="Rollback to version 0.9.0")

        content = log_path.read_text().strip()
        # Values with spaces should be quoted
        assert 'reason="Rollback to version 0.9.0"' in content

    def test_multiple_spaces_in_value(self, tmp_path: Path) -> None:
        """Test handling of multiple spaces in values."""
        log_path = tmp_path / "audit.log"
        logger = AuditLogger(log_path)

        logger.log("TEST", message="This is a long message with spaces")

        content = log_path.read_text().strip()
        assert 'message="This is a long message with spaces"' in content

    def test_none_values_excluded(self, tmp_path: Path) -> None:
        """Test that None values are excluded from log output."""
        log_path = tmp_path / "audit.log"
        logger = AuditLogger(log_path)

        logger.log("TEST", present="yes", absent=None)

        content = log_path.read_text().strip()
        assert "present=yes" in content
        assert "absent" not in content

    def test_numeric_values(self, tmp_path: Path) -> None:
        """Test handling of numeric values."""
        log_path = tmp_path / "audit.log"
        logger = AuditLogger(log_path)

        logger.log("SANDBOX", skill="test", duration=3.2, exit_code=0)

        content = log_path.read_text().strip()
        assert "duration=3.2" in content
        assert "exit_code=0" in content

    def test_boolean_values(self, tmp_path: Path) -> None:
        """Test handling of boolean values."""
        log_path = tmp_path / "audit.log"
        logger = AuditLogger(log_path)

        logger.log("AST_GATE", skill="test", passed=True)

        content = log_path.read_text().strip()
        assert "passed=True" in content

    def test_all_operations(self, tmp_path: Path) -> None:
        """Test all documented operation types."""
        log_path = tmp_path / "audit.log"
        logger = AuditLogger(log_path)

        operations = [
            ("GENERATE", {"skill": "test", "version": "1.0.0", "provider": "mock"}),
            ("AST_GATE", {"skill": "test", "version": "1.0.0", "passed": True}),
            ("SANDBOX", {"skill": "test", "version": "1.0.0", "passed": True}),
            ("STAGING", {"skill": "test", "version": "1.0.0"}),
            ("PROMOTE", {"skill": "test", "version": "1.0.0"}),
            ("ROLLBACK", {"skill": "test", "from": "1.0.0", "to": "0.9.0"}),
            ("DISABLE", {"skill": "test", "version": "1.0.0"}),
        ]

        for op, kwargs in operations:
            logger.log(op, **kwargs)

        content = log_path.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 7

        for i, (op, _) in enumerate(operations):
            assert f"[{op}]" in lines[i]

    def test_empty_kwargs(self, tmp_path: Path) -> None:
        """Test logging with no key-value pairs."""
        log_path = tmp_path / "audit.log"
        logger = AuditLogger(log_path)

        logger.log("TEST")

        content = log_path.read_text().strip()
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z \[TEST\]$"
        assert re.match(pattern, content), f"Log line doesn't match expected format: {content}"

    def test_timestamp_is_utc(self, tmp_path: Path) -> None:
        """Test that timestamp ends with Z indicating UTC."""
        log_path = tmp_path / "audit.log"
        logger = AuditLogger(log_path)

        logger.log("TEST", key="value")

        content = log_path.read_text().strip()
        # Extract timestamp (everything before the first space followed by [)
        timestamp = content.split(" [")[0]
        assert timestamp.endswith("Z"), f"Timestamp should end with Z (UTC): {timestamp}"
