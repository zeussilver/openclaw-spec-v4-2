"""Tests for day_logger module."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from src.day_logger import MISSING_PATTERN, build_queue, parse_log
from src.models.queue import NightlyQueue, QueueItem


class TestMissingPattern:
    """Tests for the MISSING_PATTERN regex."""

    def test_simple_match(self):
        """Test matching a simple MISSING tag."""
        match = MISSING_PATTERN.search("[MISSING: test capability]")
        assert match is not None
        assert match.group(1) == "test capability"

    def test_match_with_whitespace(self):
        """Test matching MISSING tag with extra whitespace."""
        match = MISSING_PATTERN.search("[MISSING:   spaced capability  ]")
        assert match is not None
        assert match.group(1) == "spaced capability  "

    def test_match_in_log_line(self):
        """Test matching MISSING tag embedded in a log line."""
        line = "2024-01-01 10:00:00 ERROR [MISSING: file parser] - task failed"
        match = MISSING_PATTERN.search(line)
        assert match is not None
        assert match.group(1) == "file parser"

    def test_no_match(self):
        """Test no match for lines without MISSING tag."""
        assert MISSING_PATTERN.search("normal log line") is None
        assert MISSING_PATTERN.search("[INFO: something]") is None
        assert MISSING_PATTERN.search("MISSING: no brackets") is None


class TestParseLog:
    """Tests for parse_log function."""

    def test_parse_single_missing(self, tmp_path: Path):
        """Test parsing log with single MISSING tag."""
        log_file = tmp_path / "test.log"
        log_file.write_text("[MISSING: test capability]\n")

        result = parse_log(log_file)

        assert len(result) == 1
        assert result[0][0] == "test capability"
        assert result[0][1] == "[MISSING: test capability]"

    def test_parse_multiple_missing(self, tmp_path: Path):
        """Test parsing log with multiple MISSING tags."""
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "[MISSING: first]\n"
            "normal line\n"
            "[MISSING: second]\n"
            "[MISSING: third]\n"
        )

        result = parse_log(log_file)

        assert len(result) == 3
        assert result[0][0] == "first"
        assert result[1][0] == "second"
        assert result[2][0] == "third"

    def test_parse_duplicate_missing(self, tmp_path: Path):
        """Test parsing log with duplicate MISSING tags (parse_log returns all)."""
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "[MISSING: duplicate]\n"
            "[MISSING: duplicate]\n"
            "[MISSING: duplicate]\n"
        )

        result = parse_log(log_file)

        # parse_log returns all occurrences, dedup happens in build_queue
        assert len(result) == 3
        assert all(r[0] == "duplicate" for r in result)

    def test_parse_no_missing(self, tmp_path: Path):
        """Test parsing log with no MISSING tags."""
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "normal log line 1\n"
            "normal log line 2\n"
            "INFO: something happened\n"
        )

        result = parse_log(log_file)

        assert len(result) == 0

    def test_parse_complex_missing(self, tmp_path: Path):
        """Test parsing MISSING tags with complex content."""
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "2024-01-01 10:00:00 ERROR [MISSING: JSON parser with schema validation] - failed\n"
            "2024-01-01 10:01:00 WARN [MISSING: CSV to Excel converter] - not found\n"
        )

        result = parse_log(log_file)

        assert len(result) == 2
        assert result[0][0] == "JSON parser with schema validation"
        assert result[1][0] == "CSV to Excel converter"
        assert "ERROR" in result[0][1]
        assert "WARN" in result[1][1]

    def test_parse_empty_file(self, tmp_path: Path):
        """Test parsing empty log file."""
        log_file = tmp_path / "empty.log"
        log_file.write_text("")

        result = parse_log(log_file)

        assert len(result) == 0


class TestBuildQueue:
    """Tests for build_queue function."""

    def test_build_queue_single_item(self):
        """Test building queue with single capability."""
        capabilities = [("test capability", "context line")]

        queue = build_queue(capabilities)

        assert len(queue.items) == 1
        assert queue.items[0].capability == "test capability"
        assert queue.items[0].occurrences == 1
        assert queue.items[0].status == "pending"
        assert queue.items[0].context == "context line"

    def test_build_queue_dedup_case_insensitive(self):
        """Test deduplication is case-insensitive."""
        capabilities = [
            ("Test Capability", "ctx1"),
            ("test capability", "ctx2"),
            ("TEST CAPABILITY", "ctx3"),
        ]

        queue = build_queue(capabilities)

        assert len(queue.items) == 1
        # First occurrence wins for the actual string
        assert queue.items[0].capability == "Test Capability"
        assert queue.items[0].occurrences == 3

    def test_build_queue_dedup_strips_whitespace(self):
        """Test deduplication strips whitespace."""
        capabilities = [
            ("  test  ", "ctx1"),
            ("test", "ctx2"),
            ("test  ", "ctx3"),
        ]

        queue = build_queue(capabilities)

        assert len(queue.items) == 1
        assert queue.items[0].capability == "test"
        assert queue.items[0].occurrences == 3

    def test_build_queue_merge_with_existing(self):
        """Test merging with existing queue."""
        existing = NightlyQueue(
            items=[
                QueueItem(
                    id="existing-id",
                    capability="existing capability",
                    first_seen=datetime(2024, 1, 1),
                    occurrences=5,
                    context="old context",
                    status="pending",
                )
            ]
        )
        capabilities = [
            ("existing capability", "new context"),
            ("new capability", "new ctx"),
        ]

        queue = build_queue(capabilities, existing)

        assert len(queue.items) == 2
        # Existing item preserved with incremented count
        existing_item = next(i for i in queue.items if i.id == "existing-id")
        assert existing_item.occurrences == 6
        assert existing_item.context == "old context"  # Context preserved
        # New item added
        new_item = next(i for i in queue.items if i.capability == "new capability")
        assert new_item.occurrences == 1

    def test_build_queue_preserves_status(self):
        """Test that existing item status is preserved."""
        existing = NightlyQueue(
            items=[
                QueueItem(
                    id="completed-id",
                    capability="completed task",
                    first_seen=datetime(2024, 1, 1),
                    occurrences=1,
                    status="completed",
                ),
                QueueItem(
                    id="failed-id",
                    capability="failed task",
                    first_seen=datetime(2024, 1, 1),
                    occurrences=1,
                    status="failed",
                ),
            ]
        )
        capabilities = [
            ("completed task", "ctx"),
            ("failed task", "ctx"),
        ]

        queue = build_queue(capabilities, existing)

        completed = next(i for i in queue.items if i.id == "completed-id")
        failed = next(i for i in queue.items if i.id == "failed-id")
        assert completed.status == "completed"
        assert failed.status == "failed"

    def test_build_queue_empty_capabilities(self):
        """Test building queue with no capabilities."""
        queue = build_queue([])

        assert len(queue.items) == 0

    def test_build_queue_preserves_existing_with_no_new(self):
        """Test that existing items are preserved even with no new capabilities."""
        existing = NightlyQueue(
            items=[
                QueueItem(
                    id="existing-id",
                    capability="existing",
                    first_seen=datetime(2024, 1, 1),
                    occurrences=1,
                    status="pending",
                )
            ]
        )

        queue = build_queue([], existing)

        assert len(queue.items) == 1
        assert queue.items[0].id == "existing-id"


class TestCLI:
    """Tests for CLI functionality."""

    def test_cli_basic(self, tmp_path: Path):
        """Test basic CLI invocation."""
        log_file = tmp_path / "test.log"
        log_file.write_text("[MISSING: cli test capability]\n")
        out_file = tmp_path / "queue.json"

        result = subprocess.run(
            [sys.executable, "-m", "src.day_logger", "--log", str(log_file), "--out", str(out_file)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert out_file.exists()

        with open(out_file) as f:
            data = json.load(f)

        queue = NightlyQueue.model_validate(data)
        assert len(queue.items) == 1
        assert queue.items[0].capability == "cli test capability"

    def test_cli_merge_existing(self, tmp_path: Path):
        """Test CLI merges with existing queue file."""
        log_file = tmp_path / "test.log"
        out_file = tmp_path / "queue.json"

        # Create initial queue
        initial_queue = NightlyQueue(
            items=[
                QueueItem(
                    id="existing-id",
                    capability="existing",
                    first_seen=datetime(2024, 1, 1),
                    occurrences=1,
                    status="completed",
                )
            ]
        )
        with open(out_file, "w") as f:
            json.dump(initial_queue.model_dump(mode="json"), f, default=str)

        # Run with new log
        log_file.write_text("[MISSING: new capability]\n[MISSING: existing]\n")

        result = subprocess.run(
            [sys.executable, "-m", "src.day_logger", "--log", str(log_file), "--out", str(out_file)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0

        with open(out_file) as f:
            data = json.load(f)

        queue = NightlyQueue.model_validate(data)
        assert len(queue.items) == 2

        existing = next(i for i in queue.items if i.id == "existing-id")
        assert existing.status == "completed"
        assert existing.occurrences == 2

    def test_cli_creates_output_directory(self, tmp_path: Path):
        """Test CLI creates output directory if needed."""
        log_file = tmp_path / "test.log"
        log_file.write_text("[MISSING: test]\n")
        out_file = tmp_path / "subdir" / "nested" / "queue.json"

        result = subprocess.run(
            [sys.executable, "-m", "src.day_logger", "--log", str(log_file), "--out", str(out_file)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert out_file.exists()

    def test_cli_prints_summary(self, tmp_path: Path):
        """Test CLI prints summary to stdout."""
        log_file = tmp_path / "test.log"
        log_file.write_text("[MISSING: one]\n[MISSING: two]\n[MISSING: one]\n")
        out_file = tmp_path / "queue.json"

        result = subprocess.run(
            [sys.executable, "-m", "src.day_logger", "--log", str(log_file), "--out", str(out_file)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "3 MISSING tags" in result.stdout
        assert "2 items" in result.stdout
