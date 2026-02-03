"""Tests for Night Evolver."""

import json
import subprocess
import sys
import uuid
from datetime import datetime

import pytest

from src.models.queue import NightlyQueue, QueueItem
from src.night_evolver import (
    evolve,
    get_provider,
    load_queue,
    save_queue,
    write_to_staging,
)
from src.llm.mock import MockLLM
from src.registry import Registry


@pytest.fixture
def tmp_paths(tmp_path):
    """Create temporary paths for queue, staging, registry, and audit log."""
    return {
        "queue": tmp_path / "queue.json",
        "staging": tmp_path / "staging",
        "registry": tmp_path / "registry.json",
        "audit": tmp_path / "audit.log",
    }


@pytest.fixture
def pending_item():
    """Create a pending queue item for text echo."""
    return QueueItem(
        id=str(uuid.uuid4()),
        capability="convert text to uppercase",
        first_seen=datetime.now(),
        occurrences=1,
        context="[MISSING: convert text to uppercase]",
        status="pending",
    )


@pytest.fixture
def pending_filename_item():
    """Create a pending queue item for filename normalize."""
    return QueueItem(
        id=str(uuid.uuid4()),
        capability="normalize filename",
        first_seen=datetime.now(),
        occurrences=1,
        context="[MISSING: normalize filename]",
        status="pending",
    )


@pytest.fixture
def unknown_capability_item():
    """Create a pending queue item for unknown capability."""
    return QueueItem(
        id=str(uuid.uuid4()),
        capability="quantum teleportation",
        first_seen=datetime.now(),
        occurrences=1,
        context="[MISSING: quantum teleportation]",
        status="pending",
    )


class TestGetProvider:
    """Test get_provider function."""

    def test_returns_mock_llm(self):
        """Should return MockLLM for 'mock' provider."""
        provider = get_provider("mock")
        assert isinstance(provider, MockLLM)

    def test_raises_for_unknown_provider(self):
        """Should raise ValueError for unknown provider."""
        with pytest.raises(ValueError) as exc_info:
            get_provider("openai")
        assert "Unknown provider" in str(exc_info.value)


class TestQueueOperations:
    """Test queue loading and saving."""

    def test_load_empty_queue_when_file_missing(self, tmp_path):
        """Should return empty queue when file doesn't exist."""
        queue_path = tmp_path / "missing.json"
        queue = load_queue(queue_path)
        assert len(queue.items) == 0

    def test_load_queue_from_file(self, tmp_path, pending_item):
        """Should load queue from JSON file."""
        queue_path = tmp_path / "queue.json"
        queue = NightlyQueue(items=[pending_item])

        with open(queue_path, "w") as f:
            json.dump(queue.model_dump(mode="json"), f, default=str)

        loaded = load_queue(queue_path)
        assert len(loaded.items) == 1
        assert loaded.items[0].capability == pending_item.capability

    def test_save_queue_creates_file(self, tmp_path, pending_item):
        """Should save queue to JSON file."""
        queue_path = tmp_path / "queue.json"
        queue = NightlyQueue(items=[pending_item])

        save_queue(queue_path, queue)

        assert queue_path.exists()
        with open(queue_path) as f:
            data = json.load(f)
        assert len(data["items"]) == 1

    def test_save_queue_creates_parent_dirs(self, tmp_path, pending_item):
        """Should create parent directories if needed."""
        queue_path = tmp_path / "nested" / "dir" / "queue.json"
        queue = NightlyQueue(items=[pending_item])

        save_queue(queue_path, queue)
        assert queue_path.exists()


class TestWriteToStaging:
    """Test write_to_staging function."""

    def test_creates_skill_directory(self, tmp_path):
        """Should create skill directory structure."""
        llm = MockLLM()
        pkg = llm.generate_skill("text echo")
        staging = tmp_path / "staging"

        skill_dir = write_to_staging(staging, pkg, "1.0.0")

        assert skill_dir.exists()
        assert (skill_dir / "skill.py").exists()
        assert (skill_dir / "skill.json").exists()

    def test_directory_structure_correct(self, tmp_path):
        """Should create correct directory structure."""
        llm = MockLLM()
        pkg = llm.generate_skill("text echo")
        staging = tmp_path / "staging"

        skill_dir = write_to_staging(staging, pkg, "1.0.0")

        expected = staging / "text_echo" / "1.0.0"
        assert skill_dir == expected

    def test_skill_py_content_correct(self, tmp_path):
        """Should write correct skill.py content."""
        llm = MockLLM()
        pkg = llm.generate_skill("text echo")
        staging = tmp_path / "staging"

        skill_dir = write_to_staging(staging, pkg, "1.0.0")

        content = (skill_dir / "skill.py").read_text()
        assert content == pkg.code

    def test_skill_json_content_correct(self, tmp_path):
        """Should write correct skill.json content."""
        llm = MockLLM()
        pkg = llm.generate_skill("text echo")
        staging = tmp_path / "staging"

        skill_dir = write_to_staging(staging, pkg, "1.0.0")

        with open(skill_dir / "skill.json") as f:
            manifest = json.load(f)
        assert manifest == pkg.manifest


class TestEvolveSingleItem:
    """Test evolve with a single queue item."""

    def test_evolve_single_pending_item(self, tmp_paths, pending_item):
        """Should process a single pending item successfully."""
        queue = NightlyQueue(items=[pending_item])
        save_queue(tmp_paths["queue"], queue)

        summary = evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            skip_sandbox=True,
        )

        assert summary["processed"] == 1
        assert summary["succeeded"] == 1
        assert summary["failed"] == 0

    def test_item_marked_completed(self, tmp_paths, pending_item):
        """Should mark item as completed after success."""
        queue = NightlyQueue(items=[pending_item])
        save_queue(tmp_paths["queue"], queue)

        evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            skip_sandbox=True,
        )

        updated_queue = load_queue(tmp_paths["queue"])
        assert updated_queue.items[0].status == "completed"

    def test_staging_directory_created(self, tmp_paths, pending_item):
        """Should create staging directory with skill files."""
        queue = NightlyQueue(items=[pending_item])
        save_queue(tmp_paths["queue"], queue)

        evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            skip_sandbox=True,
        )

        skill_dir = tmp_paths["staging"] / "text_echo" / "1.0.0"
        assert skill_dir.exists()
        assert (skill_dir / "skill.py").exists()
        assert (skill_dir / "skill.json").exists()


class TestEvolveMultipleItems:
    """Test evolve with multiple queue items."""

    def test_evolve_multiple_items(self, tmp_paths, pending_item, pending_filename_item):
        """Should process multiple pending items."""
        queue = NightlyQueue(items=[pending_item, pending_filename_item])
        save_queue(tmp_paths["queue"], queue)

        summary = evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            skip_sandbox=True,
        )

        assert summary["processed"] == 2
        assert summary["succeeded"] == 2
        assert summary["failed"] == 0

    def test_all_items_marked_completed(self, tmp_paths, pending_item, pending_filename_item):
        """Should mark all items as completed."""
        queue = NightlyQueue(items=[pending_item, pending_filename_item])
        save_queue(tmp_paths["queue"], queue)

        evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            skip_sandbox=True,
        )

        updated_queue = load_queue(tmp_paths["queue"])
        assert all(item.status == "completed" for item in updated_queue.items)


class TestSkipNonPending:
    """Test that non-pending items are skipped."""

    def test_skip_completed_items(self, tmp_paths, pending_item):
        """Should skip already completed items."""
        pending_item.status = "completed"
        queue = NightlyQueue(items=[pending_item])
        save_queue(tmp_paths["queue"], queue)

        summary = evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            skip_sandbox=True,
        )

        assert summary["processed"] == 0
        assert summary["skipped"] == 1

    def test_skip_failed_items(self, tmp_paths, pending_item):
        """Should skip already failed items."""
        pending_item.status = "failed"
        queue = NightlyQueue(items=[pending_item])
        save_queue(tmp_paths["queue"], queue)

        summary = evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            skip_sandbox=True,
        )

        assert summary["processed"] == 0
        assert summary["skipped"] == 1


class TestASTGateFailure:
    """Test AST Gate failure handling."""

    def test_unknown_capability_marked_failed(self, tmp_paths, unknown_capability_item):
        """Should mark item as failed when LLM can't generate skill."""
        queue = NightlyQueue(items=[unknown_capability_item])
        save_queue(tmp_paths["queue"], queue)

        summary = evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            skip_sandbox=True,
        )

        assert summary["failed"] == 1
        updated_queue = load_queue(tmp_paths["queue"])
        assert updated_queue.items[0].status == "failed"

    def test_mixed_success_and_failure(self, tmp_paths, pending_item, unknown_capability_item):
        """Should handle mix of successful and failed items."""
        queue = NightlyQueue(items=[pending_item, unknown_capability_item])
        save_queue(tmp_paths["queue"], queue)

        summary = evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            skip_sandbox=True,
        )

        assert summary["succeeded"] == 1
        assert summary["failed"] == 1


class TestRegistryUpdate:
    """Test registry updates after successful evolution."""

    def test_registry_updated_after_success(self, tmp_paths, pending_item):
        """Should update registry with staging entry."""
        queue = NightlyQueue(items=[pending_item])
        save_queue(tmp_paths["queue"], queue)

        evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            skip_sandbox=True,
        )

        registry = Registry(tmp_paths["registry"])
        entry = registry.get_entry("text_echo")
        assert entry is not None
        assert entry.current_staging == "1.0.0"

    def test_registry_contains_validation_results(self, tmp_paths, pending_item):
        """Should store validation results in registry."""
        queue = NightlyQueue(items=[pending_item])
        save_queue(tmp_paths["queue"], queue)

        evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            skip_sandbox=True,
        )

        registry = Registry(tmp_paths["registry"])
        entry = registry.get_entry("text_echo")
        version = entry.versions["1.0.0"]
        assert version.validation.ast_gate is not None
        assert version.validation.ast_gate["passed"] is True


class TestSummaryOutput:
    """Test evolve summary output."""

    def test_summary_has_all_fields(self, tmp_paths, pending_item):
        """Summary should have all required fields."""
        queue = NightlyQueue(items=[pending_item])
        save_queue(tmp_paths["queue"], queue)

        summary = evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            skip_sandbox=True,
        )

        assert "processed" in summary
        assert "succeeded" in summary
        assert "failed" in summary
        assert "skipped" in summary

    def test_summary_counts_correct(self, tmp_paths, pending_item, pending_filename_item, unknown_capability_item):
        """Summary counts should be accurate."""
        # One completed (skip), two pending (1 success, 1 fail)
        pending_item_copy = QueueItem(
            id=str(uuid.uuid4()),
            capability="text echo",
            first_seen=datetime.now(),
            status="completed",  # Already done
        )

        queue = NightlyQueue(
            items=[pending_item_copy, pending_filename_item, unknown_capability_item]
        )
        save_queue(tmp_paths["queue"], queue)

        summary = evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            skip_sandbox=True,
        )

        assert summary["skipped"] == 1
        assert summary["processed"] == 2
        assert summary["succeeded"] == 1
        assert summary["failed"] == 1


class TestAuditLogging:
    """Test audit logging integration."""

    def test_audit_log_created(self, tmp_paths, pending_item):
        """Should create audit log when path provided."""
        queue = NightlyQueue(items=[pending_item])
        save_queue(tmp_paths["queue"], queue)

        evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            audit_log_path=tmp_paths["audit"],
            skip_sandbox=True,
        )

        assert tmp_paths["audit"].exists()

    def test_audit_log_contains_operations(self, tmp_paths, pending_item):
        """Audit log should contain expected operations."""
        queue = NightlyQueue(items=[pending_item])
        save_queue(tmp_paths["queue"], queue)

        evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            audit_log_path=tmp_paths["audit"],
            skip_sandbox=True,
        )

        content = tmp_paths["audit"].read_text()
        assert "[GENERATE]" in content
        assert "[AST_GATE]" in content
        assert "[STAGING]" in content


class TestCLI:
    """Test CLI interface."""

    def test_cli_help(self):
        """CLI should display help without error."""
        result = subprocess.run(
            [sys.executable, "-m", "src.night_evolver", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Night Evolver" in result.stdout

    def test_cli_requires_queue(self):
        """CLI should require --queue argument."""
        result = subprocess.run(
            [sys.executable, "-m", "src.night_evolver"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "required" in result.stderr.lower()


class TestEndToEnd:
    """End-to-end test: day_logger → night_evolver."""

    def test_e2e_day_to_night(self, tmp_path):
        """Full flow: parse log → build queue → evolve skills."""
        # Create test log file
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "INFO: Starting up...\n"
            "[MISSING: echo text to console]\n"
            "DEBUG: Processing request\n"
            "[MISSING: normalize filename for storage]\n"
            "INFO: Done\n"
        )

        queue_file = tmp_path / "queue.json"
        staging_dir = tmp_path / "staging"
        registry_file = tmp_path / "registry.json"

        # Run day_logger
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.day_logger",
                "--log",
                str(log_file),
                "--out",
                str(queue_file),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"day_logger failed: {result.stderr}"
        assert queue_file.exists()

        # Run night_evolver
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.night_evolver",
                "--queue",
                str(queue_file),
                "--staging",
                str(staging_dir),
                "--registry",
                str(registry_file),
                "--provider",
                "mock",
                "--skip-sandbox",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"night_evolver failed: {result.stderr}"

        # Verify staging has skills
        assert staging_dir.exists()
        assert (staging_dir / "text_echo" / "1.0.0" / "skill.py").exists()
        assert (staging_dir / "safe_filename_normalize" / "1.0.0" / "skill.py").exists()

        # Verify registry updated
        assert registry_file.exists()
        registry = Registry(registry_file)
        assert registry.get_entry("text_echo") is not None
        assert registry.get_entry("safe_filename_normalize") is not None

        # Verify queue items marked completed
        queue = load_queue(queue_file)
        assert all(item.status == "completed" for item in queue.items)


class TestEmptyQueue:
    """Test handling of empty queue."""

    def test_empty_queue_returns_zero_counts(self, tmp_paths):
        """Should return zeros for empty queue."""
        queue = NightlyQueue(items=[])
        save_queue(tmp_paths["queue"], queue)

        summary = evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            skip_sandbox=True,
        )

        assert summary["processed"] == 0
        assert summary["succeeded"] == 0
        assert summary["failed"] == 0
        assert summary["skipped"] == 0

    def test_missing_queue_file_returns_empty(self, tmp_paths):
        """Should handle missing queue file gracefully."""
        summary = evolve(
            queue_path=tmp_paths["queue"],
            staging_path=tmp_paths["staging"],
            registry_path=tmp_paths["registry"],
            provider_name="mock",
            skip_sandbox=True,
        )

        assert summary["processed"] == 0
