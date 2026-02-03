"""Night Evolver - Generate and validate skills from the nightly queue.

Main flow for each pending queue item:
1. LLM generate → SkillPackage
2. AST Gate check → reject if failed
3. Manifest validation → reject if failed
4. Write to staging directory
5. Sandbox run → reject if failed (optional, skipped if Docker unavailable)
6. Registry update with validation results
7. Audit log all events
8. Mark item completed or failed
"""

import argparse
import json
import sys
import warnings
from pathlib import Path

from .audit import AuditLogger
from .llm import MockLLM
from .llm.base import LLMProvider, SkillPackage
from .models.queue import NightlyQueue
from .models.registry import ValidationResult
from .registry import Registry, compute_hash
from .sandbox.runner import SandboxRunner
from .security.ast_gate import ASTGate
from .validators.manifest import validate_manifest


def get_provider(provider_name: str) -> LLMProvider:
    """Get an LLM provider by name.

    Args:
        provider_name: The provider name ("mock" supported).

    Returns:
        An LLMProvider instance.

    Raises:
        ValueError: If provider is not supported.
    """
    if provider_name == "mock":
        return MockLLM()
    raise ValueError(f"Unknown provider: {provider_name}. Supported: mock")


def load_queue(queue_path: Path) -> NightlyQueue:
    """Load the nightly queue from a JSON file.

    Args:
        queue_path: Path to the queue JSON file.

    Returns:
        NightlyQueue instance (empty if file doesn't exist).
    """
    if not queue_path.exists():
        return NightlyQueue()
    with open(queue_path) as f:
        data = json.load(f)
    return NightlyQueue.model_validate(data)


def save_queue(queue_path: Path, queue: NightlyQueue) -> None:
    """Save the nightly queue to a JSON file.

    Args:
        queue_path: Path to the queue JSON file.
        queue: NightlyQueue to save.
    """
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with open(queue_path, "w") as f:
        json.dump(queue.model_dump(mode="json"), f, indent=2, default=str)


def write_to_staging(staging_path: Path, skill_pkg: SkillPackage, version: str) -> Path:
    """Write a skill package to the staging directory.

    Creates: staging_path/<name>/<version>/skill.py and skill.json

    Args:
        staging_path: Base staging directory.
        skill_pkg: The skill package to write.
        version: Version string for the directory name.

    Returns:
        Path to the skill directory.
    """
    skill_dir = staging_path / skill_pkg.name / version
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Write skill.py
    skill_py = skill_dir / "skill.py"
    skill_py.write_text(skill_pkg.code)

    # Write skill.json
    skill_json = skill_dir / "skill.json"
    with open(skill_json, "w") as f:
        json.dump(skill_pkg.manifest, f, indent=2)

    return skill_dir


def evolve(
    queue_path: Path,
    staging_path: Path,
    registry_path: Path,
    provider_name: str,
    audit_log_path: Path | None = None,
    skip_sandbox: bool = False,
) -> dict:
    """Night Mode main flow - process pending queue items.

    Args:
        queue_path: Path to the nightly queue JSON file.
        staging_path: Path to the staging directory.
        registry_path: Path to the registry JSON file.
        provider_name: Name of the LLM provider ("mock").
        audit_log_path: Optional path for audit logging.
        skip_sandbox: If True, skip sandbox verification entirely.

    Returns:
        Summary dict: {processed, succeeded, failed, skipped}
    """
    # Initialize components
    queue = load_queue(queue_path)
    registry = Registry(registry_path)
    llm = get_provider(provider_name)
    ast_gate = ASTGate()
    sandbox = SandboxRunner()
    audit = AuditLogger(audit_log_path) if audit_log_path else None

    # Check sandbox availability once
    sandbox_available = not skip_sandbox and sandbox.is_available()
    if not skip_sandbox and not sandbox_available:
        warnings.warn(
            "Docker sandbox unavailable - sandbox verification will be skipped. "
            "Build the sandbox image with: docker build -f docker/Dockerfile.sandbox -t openclaw-sandbox:latest .",
            stacklevel=2,
        )

    summary = {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}

    for item in queue.items:
        # Skip non-pending items
        if item.status != "pending":
            summary["skipped"] += 1
            continue

        summary["processed"] += 1
        item.status = "processing"

        # Track validation results for registry
        validation = ValidationResult()

        try:
            # 1. Generate skill
            if audit:
                audit.log("GENERATE", capability=item.capability, item_id=item.id)

            skill_pkg = llm.generate_skill(item.capability, item.context)

            # 2. AST Gate check
            gate_result = ast_gate.check(skill_pkg.code)
            validation.ast_gate = {
                "passed": gate_result.passed,
                "violations": gate_result.violations,
            }

            if audit:
                audit.log(
                    "AST_GATE",
                    skill=skill_pkg.name,
                    passed=gate_result.passed,
                    violations=len(gate_result.violations),
                )

            if not gate_result.passed:
                item.status = "failed"
                summary["failed"] += 1
                continue

            # 3. Manifest validation
            manifest_valid, manifest_errors = validate_manifest(skill_pkg.manifest)

            if not manifest_valid:
                if audit:
                    audit.log(
                        "MANIFEST_INVALID",
                        skill=skill_pkg.name,
                        errors="; ".join(manifest_errors),
                    )
                item.status = "failed"
                summary["failed"] += 1
                continue

            # 4. Write to staging
            version = skill_pkg.manifest.get("version", "1.0.0")
            skill_dir = write_to_staging(staging_path, skill_pkg, version)

            if audit:
                audit.log("STAGING", skill=skill_pkg.name, version=version, path=str(skill_dir))

            # 5. Sandbox verification (optional)
            if sandbox_available:
                passed, logs, metrics = sandbox.run(skill_dir)
                validation.sandbox = {
                    "passed": passed,
                    "metrics": metrics,
                }

                if audit:
                    audit.log(
                        "SANDBOX",
                        skill=skill_pkg.name,
                        passed=passed,
                        duration_ms=metrics.get("duration_ms"),
                    )

                if not passed:
                    item.status = "failed"
                    summary["failed"] += 1
                    continue
            else:
                # Mark sandbox as skipped
                validation.sandbox = {"passed": None, "skipped": True}

            # 6. Registry update
            code_hash = compute_hash(skill_pkg.code)
            manifest_hash = compute_hash(json.dumps(skill_pkg.manifest, sort_keys=True))

            registry.add_staging(
                name=skill_pkg.name,
                version=version,
                code_hash=code_hash,
                manifest_hash=manifest_hash,
                validation=validation,
            )

            # 7. Mark completed
            item.status = "completed"
            summary["succeeded"] += 1

        except ValueError as e:
            # LLM generation failed (unknown capability)
            if audit:
                audit.log("GENERATE_FAILED", capability=item.capability, error=str(e))
            item.status = "failed"
            summary["failed"] += 1

        except Exception as e:
            # Unexpected error
            if audit:
                audit.log("ERROR", capability=item.capability, error=str(e))
            item.status = "failed"
            summary["failed"] += 1

    # Save updated queue
    save_queue(queue_path, queue)

    return summary


def main() -> None:
    """CLI entry point for night evolver."""
    parser = argparse.ArgumentParser(
        description="Night Evolver - Generate and validate skills from the nightly queue"
    )
    parser.add_argument(
        "--queue",
        required=True,
        help="Path to the nightly queue JSON file",
    )
    parser.add_argument(
        "--staging",
        required=True,
        help="Path to the staging directory",
    )
    parser.add_argument(
        "--registry",
        required=True,
        help="Path to the registry JSON file",
    )
    parser.add_argument(
        "--provider",
        default="mock",
        choices=["mock"],
        help="LLM provider to use (default: mock)",
    )
    parser.add_argument(
        "--audit-log",
        help="Path to audit log file (optional)",
    )
    parser.add_argument(
        "--skip-sandbox",
        action="store_true",
        help="Skip sandbox verification entirely",
    )

    args = parser.parse_args()

    summary = evolve(
        queue_path=Path(args.queue),
        staging_path=Path(args.staging),
        registry_path=Path(args.registry),
        provider_name=args.provider,
        audit_log_path=Path(args.audit_log) if args.audit_log else None,
        skip_sandbox=args.skip_sandbox,
    )

    # Print summary
    print("Night Evolver completed:")
    print(f"  Processed: {summary['processed']}")
    print(f"  Succeeded: {summary['succeeded']}")
    print(f"  Failed:    {summary['failed']}")
    print(f"  Skipped:   {summary['skipped']}")

    # Exit with error if any failures
    if summary["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
