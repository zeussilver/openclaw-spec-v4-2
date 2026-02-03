"""End-to-end tests for the full OpenClaw pipeline.

Tests the complete flow: Day Logger -> Night Evolver -> Promote -> Rollback
with audit logging verification at each step.
"""

import json
from datetime import datetime
from pathlib import Path


from src.audit import AuditLogger
from src.day_logger import build_queue, parse_log
from src.models.queue import NightlyQueue
from src.night_evolver import evolve
from src.promote import promote_skill
from src.registry import Registry
from src.rollback import rollback_skill


class TestFullPipeline:
    """Test the complete Day -> Night -> Promote -> Rollback pipeline."""

    def test_full_pipeline(self, tmp_path: Path) -> None:
        """Test the complete pipeline from log parsing to rollback."""
        # Set up paths
        log_file = tmp_path / "runtime.log"
        queue_path = tmp_path / "nightly_queue.json"
        registry_path = tmp_path / "registry.json"
        staging_path = tmp_path / "skills_staging"
        prod_path = tmp_path / "skills_prod"
        eval_dir = tmp_path / "eval"
        audit_log_path = tmp_path / "audit.log"

        # ===== STEP 1: Create test log with MISSING tag =====
        log_content = """2026-02-01 10:00:00 INFO Starting service
2026-02-01 10:01:00 WARN [MISSING: convert text to uppercase]
2026-02-01 10:02:00 INFO Processing request
"""
        log_file.write_text(log_content)

        # ===== STEP 2: Run day_logger to parse log =====
        capabilities = parse_log(log_file)
        assert len(capabilities) == 1
        assert "uppercase" in capabilities[0][0].lower()

        queue = build_queue(capabilities)
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        with open(queue_path, "w") as f:
            json.dump(queue.model_dump(mode="json"), f, indent=2, default=str)

        # ===== STEP 3: Verify queue has 1 pending item =====
        with open(queue_path) as f:
            queue_data = json.load(f)
        assert len(queue_data["items"]) == 1
        assert queue_data["items"][0]["status"] == "pending"

        # ===== STEP 4: Run night_evolver with MockLLM and --skip-sandbox =====
        summary = evolve(
            queue_path=queue_path,
            staging_path=staging_path,
            registry_path=registry_path,
            provider_name="mock",
            audit_log_path=audit_log_path,
            skip_sandbox=True,
        )

        assert summary["succeeded"] >= 1, f"Expected at least 1 success, got {summary}"

        # ===== STEP 5: Assert staging directory exists with skill files =====
        skill_dirs = list(staging_path.glob("*/*/skill.py"))
        assert len(skill_dirs) >= 1, f"No skill.py found in staging: {list(staging_path.glob('**/*'))}"

        # Find text_echo skill (MockLLM generates this for "uppercase" capability)
        text_echo_dir = staging_path / "text_echo" / "1.0.0"
        assert text_echo_dir.exists(), f"text_echo/1.0.0 not found, got: {list(staging_path.glob('*/*'))}"
        assert (text_echo_dir / "skill.py").exists()
        assert (text_echo_dir / "skill.json").exists()

        # ===== STEP 6: Assert registry shows text_echo with staging version =====
        registry = Registry(registry_path)
        entry = registry.get_entry("text_echo")
        assert entry is not None, "text_echo not in registry"
        assert entry.current_staging == "1.0.0", f"Expected staging 1.0.0, got {entry.current_staging}"

        # ===== STEP 7: Create eval test data for text_echo =====
        self._create_eval_data(eval_dir, "text_echo")

        # ===== STEP 8: Run promote =====
        prod_path.mkdir(parents=True, exist_ok=True)
        success = promote_skill(
            skill_name="text_echo",
            staging_path=staging_path,
            prod_path=prod_path,
            registry_path=registry_path,
            eval_dir=eval_dir,
            audit_log_path=audit_log_path,
        )

        assert success, "Promotion failed"

        # ===== STEP 9: Assert registry shows text_echo as prod =====
        entry = registry.get_entry("text_echo")
        assert entry is not None
        assert entry.current_prod == "1.0.0", f"Expected prod 1.0.0, got {entry.current_prod}"

        # Verify prod directory
        prod_skill_dir = prod_path / "text_echo" / "1.0.0"
        assert prod_skill_dir.exists(), f"Prod skill dir not found: {prod_skill_dir}"

        # ===== STEP 10: Simulate rollback =====
        # First, create a fake v0.9.0 entry that was previously promoted
        data = registry.load()
        from src.models.registry import SkillVersion, ValidationResult

        v0_9_0 = SkillVersion(
            version="0.9.0",
            code_hash="old_hash",
            manifest_hash="old_manifest_hash",
            created_at=datetime.now(),
            status="disabled",
            validation=ValidationResult(),
            promoted_at=datetime.now(),  # Was previously promoted
            disabled_at=datetime.now(),
            disabled_reason="Superseded by 1.0.0",
        )
        data.skills["text_echo"].versions["0.9.0"] = v0_9_0
        registry.save(data)

        # Now rollback from 1.0.0 to 0.9.0
        rollback_skill(
            skill_name="text_echo",
            target_version="0.9.0",
            registry_path=registry_path,
            audit_log_path=audit_log_path,
        )

        # ===== STEP 11: Assert registry shows rollback =====
        entry = registry.get_entry("text_echo")
        assert entry is not None
        assert entry.current_prod == "0.9.0", f"Expected rollback to 0.9.0, got {entry.current_prod}"

        # Check 1.0.0 is now disabled
        v1_0_0 = entry.versions.get("1.0.0")
        assert v1_0_0 is not None
        assert v1_0_0.status == "disabled"

        # ===== STEP 12: Assert audit.log contains all events =====
        audit_content = audit_log_path.read_text()
        assert "[GENERATE]" in audit_content, "Missing GENERATE event"
        assert "[AST_GATE]" in audit_content, "Missing AST_GATE event"
        assert "[STAGING]" in audit_content, "Missing STAGING event"
        assert "[PROMOTE]" in audit_content, "Missing PROMOTE event"
        assert "[ROLLBACK]" in audit_content, "Missing ROLLBACK event"

    def _create_eval_data(self, eval_dir: Path, skill_name: str) -> None:
        """Create evaluation test data for a skill."""
        # Replay test case
        replay_dir = eval_dir / "replay"
        replay_dir.mkdir(parents=True)
        replay_case = {
            "id": f"replay-{skill_name}-001",
            "skill": skill_name,
            "input": {"text": "hello", "format": "upper"},
            "expected": {"type": "exact", "value": "HELLO"},
            "timeout_ms": 5000,
        }
        (replay_dir / f"{skill_name}_replay.json").write_text(
            json.dumps(replay_case, indent=2)
        )

        # Regression test case
        regression_dir = eval_dir / "regression"
        regression_dir.mkdir(parents=True)
        regression_case = {
            "id": f"regression-{skill_name}-001",
            "skill": skill_name,
            "input": {"text": "WORLD", "format": "lower"},
            "expected": {"type": "exact", "value": "world"},
            "timeout_ms": 5000,
        }
        (regression_dir / f"{skill_name}_regression.json").write_text(
            json.dumps(regression_case, indent=2)
        )

        # Redteam test case (security test)
        redteam_dir = eval_dir / "redteam"
        redteam_dir.mkdir(parents=True)
        redteam_case = {
            "id": f"redteam-{skill_name}-001",
            "skill": skill_name,
            "input": {"text": "test", "format": "upper"},
            "expected": {
                "type": "no_forbidden_patterns",
                "forbidden": ["/etc/passwd", "/proc/", "../"],
            },
            "timeout_ms": 5000,
        }
        (redteam_dir / f"{skill_name}_redteam.json").write_text(
            json.dumps(redteam_case, indent=2)
        )


class TestDayLoggerIntegration:
    """Integration tests for Day Logger."""

    def test_parse_and_dedupe(self, tmp_path: Path) -> None:
        """Test log parsing with deduplication."""
        log_file = tmp_path / "test.log"
        log_content = """[MISSING: convert text to uppercase]
[MISSING: convert text to uppercase]
[MISSING: normalize filename]
[MISSING: convert text to uppercase]
"""
        log_file.write_text(log_content)

        capabilities = parse_log(log_file)
        assert len(capabilities) == 4  # All occurrences captured

        queue = build_queue(capabilities)
        assert len(queue.items) == 2  # Deduplicated to 2 unique

        # Find the uppercase item and check occurrences
        uppercase_item = next(
            (item for item in queue.items if "uppercase" in item.capability.lower()),
            None,
        )
        assert uppercase_item is not None
        assert uppercase_item.occurrences == 3

    def test_merge_with_existing_queue(self, tmp_path: Path) -> None:
        """Test merging new capabilities with existing queue."""
        log_file = tmp_path / "test.log"
        log_file.write_text("[MISSING: new capability]")

        # Create existing queue with one item
        existing = NightlyQueue(
            items=[
                {
                    "id": "existing-id",
                    "capability": "existing capability",
                    "first_seen": datetime.now().isoformat(),
                    "occurrences": 5,
                    "context": "",
                    "status": "pending",
                }
            ]
        )

        capabilities = parse_log(log_file)
        queue = build_queue(capabilities, existing)

        assert len(queue.items) == 2
        # Existing item should be preserved
        existing_item = next(
            (item for item in queue.items if item.id == "existing-id"), None
        )
        assert existing_item is not None
        assert existing_item.occurrences == 5


class TestNightEvolverIntegration:
    """Integration tests for Night Evolver."""

    def test_unknown_capability_fails(self, tmp_path: Path) -> None:
        """Test that unknown capabilities are marked as failed."""
        queue_path = tmp_path / "queue.json"
        registry_path = tmp_path / "registry.json"
        staging_path = tmp_path / "staging"

        # Queue with unknown capability
        queue_data = {
            "items": [
                {
                    "id": "test-id",
                    "capability": "do something completely unknown xyz123",
                    "first_seen": datetime.now().isoformat(),
                    "occurrences": 1,
                    "context": "",
                    "status": "pending",
                }
            ],
            "updated_at": datetime.now().isoformat(),
        }
        queue_path.write_text(json.dumps(queue_data, indent=2))

        summary = evolve(
            queue_path=queue_path,
            staging_path=staging_path,
            registry_path=registry_path,
            provider_name="mock",
            skip_sandbox=True,
        )

        assert summary["failed"] == 1
        assert summary["succeeded"] == 0

        # Check queue item marked as failed
        with open(queue_path) as f:
            updated_queue = json.load(f)
        assert updated_queue["items"][0]["status"] == "failed"

    def test_multiple_capabilities(self, mock_queue: Path, tmp_path: Path) -> None:
        """Test processing multiple capabilities in one run."""
        registry_path = tmp_path / "registry.json"
        staging_path = tmp_path / "staging"

        summary = evolve(
            queue_path=mock_queue,
            staging_path=staging_path,
            registry_path=registry_path,
            provider_name="mock",
            skip_sandbox=True,
        )

        assert summary["succeeded"] == 2
        assert summary["failed"] == 0


class TestPromoteIntegration:
    """Integration tests for Promote."""

    def test_promotion_copies_to_prod(
        self, mock_skill_dir: Path, mock_registry: Path, mock_eval_dir: Path, tmp_path: Path
    ) -> None:
        """Test that promotion copies skill to prod directory."""
        staging_path = mock_skill_dir.parent.parent  # skills_staging
        prod_path = tmp_path / "skills_prod"
        audit_log_path = tmp_path / "audit.log"

        success = promote_skill(
            skill_name="text_echo",
            staging_path=staging_path,
            prod_path=prod_path,
            registry_path=mock_registry,
            eval_dir=mock_eval_dir,
            audit_log_path=audit_log_path,
        )

        assert success

        # Check prod directory has the skill
        prod_skill = prod_path / "text_echo" / "1.0.0" / "skill.py"
        assert prod_skill.exists()

        # Check registry updated
        registry = Registry(mock_registry)
        entry = registry.get_entry("text_echo")
        assert entry is not None
        assert entry.current_prod == "1.0.0"


class TestRollbackIntegration:
    """Integration tests for Rollback."""

    def test_rollback_updates_registry(self, tmp_path: Path) -> None:
        """Test that rollback properly updates registry state."""
        registry_path = tmp_path / "registry.json"
        audit_log_path = tmp_path / "audit.log"

        # Create registry with two versions
        registry = Registry(registry_path)
        from src.models.registry import (
            RegistryData,
            SkillEntry,
            SkillVersion,
            ValidationResult,
        )

        v1 = SkillVersion(
            version="1.0.0",
            code_hash="hash1",
            manifest_hash="manifest1",
            created_at=datetime.now(),
            status="disabled",
            validation=ValidationResult(),
            promoted_at=datetime.now(),  # Was previously promoted
            disabled_at=datetime.now(),
            disabled_reason="Superseded by 2.0.0",
        )
        v2 = SkillVersion(
            version="2.0.0",
            code_hash="hash2",
            manifest_hash="manifest2",
            created_at=datetime.now(),
            status="prod",
            validation=ValidationResult(),
            promoted_at=datetime.now(),
        )
        entry = SkillEntry(
            name="test_skill",
            current_prod="2.0.0",
            versions={"1.0.0": v1, "2.0.0": v2},
        )
        data = RegistryData(skills={"test_skill": entry})
        registry.save(data)

        # Rollback to 1.0.0
        rollback_skill(
            skill_name="test_skill",
            target_version="1.0.0",
            registry_path=registry_path,
            audit_log_path=audit_log_path,
        )

        # Verify registry state
        entry = registry.get_entry("test_skill")
        assert entry is not None
        assert entry.current_prod == "1.0.0"
        assert entry.versions["1.0.0"].status == "prod"
        assert entry.versions["2.0.0"].status == "disabled"


class TestAuditLogging:
    """Integration tests for audit logging across the pipeline."""

    def test_audit_log_format(self, tmp_path: Path) -> None:
        """Test that audit log entries have correct format."""
        audit_path = tmp_path / "audit.log"
        audit = AuditLogger(audit_path)

        audit.log("TEST_EVENT", key1="value1", key2=123, key3=True)

        content = audit_path.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 1

        line = lines[0]
        # Check format: timestamp [OPERATION] key=value
        assert "[TEST_EVENT]" in line
        assert "key1=value1" in line
        assert "key2=123" in line
        assert "key3=True" in line
        # Check timestamp format (ISO8601)
        assert line.startswith("20")  # Year 20xx
        assert "T" in line  # ISO8601 separator

    def test_audit_preserves_history(self, tmp_path: Path) -> None:
        """Test that audit log appends without overwriting."""
        audit_path = tmp_path / "audit.log"
        audit = AuditLogger(audit_path)

        audit.log("EVENT1", data="first")
        audit.log("EVENT2", data="second")
        audit.log("EVENT3", data="third")

        content = audit_path.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3
        assert "[EVENT1]" in lines[0]
        assert "[EVENT2]" in lines[1]
        assert "[EVENT3]" in lines[2]
