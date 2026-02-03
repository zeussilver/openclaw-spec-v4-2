"""Skill promotion from staging to production.

Runs three evaluation gates:
- replay: 100% pass rate required
- regression: ≥99% pass rate required
- redteam: 100% pass rate required

All gates must pass for promotion to succeed.
"""

import argparse
import shutil
from pathlib import Path

from .audit import AuditLogger
from .eval.gate import EvalGate, GateReport
from .registry import Registry


def promote_skill(
    skill_name: str,
    staging_path: Path,
    prod_path: Path,
    registry_path: Path,
    eval_dir: Path,
    audit_log_path: Path,
) -> bool:
    """Promote a single skill from staging to production.

    Args:
        skill_name: Name of the skill to promote
        staging_path: Path to staging skills directory
        prod_path: Path to production skills directory
        registry_path: Path to registry JSON file
        eval_dir: Path to evaluation data directory
        audit_log_path: Path to audit log file

    Returns:
        True if promotion succeeded, False otherwise
    """
    registry = Registry(registry_path)
    audit = AuditLogger(audit_log_path)

    # Get staging version from registry
    entry = registry.get_entry(skill_name)
    if entry is None:
        return False

    staging_version = entry.current_staging
    if staging_version is None:
        return False

    # Build skill path
    skill_path = staging_path / skill_name / staging_version

    if not skill_path.exists():
        return False

    # Run evaluation gates
    eval_gate = EvalGate(eval_dir)

    # Gate thresholds
    gates = [
        ("replay", 1.0),
        ("regression", 0.99),
        ("redteam", 1.0),
    ]

    gate_results: dict[str, GateReport] = {}
    all_passed = True

    for gate_name, threshold in gates:
        report = eval_gate.run_gate(gate_name, skill_name, skill_path, threshold)
        gate_results[gate_name] = report
        if not report.gate_passed:
            all_passed = False

    # Record gate results in registry validation
    data = registry.load()
    if skill_name in data.skills:
        skill_entry = data.skills[skill_name]
        if staging_version in skill_entry.versions:
            version = skill_entry.versions[staging_version]
            version.validation.promote_gate = {
                gate_name: {
                    "total": report.total,
                    "passed": report.passed_count,
                    "failed": report.failed_count,
                    "pass_rate": report.pass_rate,
                    "threshold": report.threshold,
                    "gate_passed": report.gate_passed,
                }
                for gate_name, report in gate_results.items()
            }
            registry.save(data)

    if not all_passed:
        # Log failure
        failed_gates = [name for name, r in gate_results.items() if not r.gate_passed]
        audit.log(
            "PROMOTE_FAILED",
            skill=skill_name,
            version=staging_version,
            failed_gates=",".join(failed_gates),
        )
        return False

    # Copy skill to production
    prod_skill_path = prod_path / skill_name / staging_version
    prod_skill_path.parent.mkdir(parents=True, exist_ok=True)

    if prod_skill_path.exists():
        shutil.rmtree(prod_skill_path)
    shutil.copytree(skill_path, prod_skill_path)

    # Update registry
    registry.promote(skill_name, staging_version)

    # Log success
    audit.log(
        "PROMOTE",
        skill=skill_name,
        version=staging_version,
        replay_rate=gate_results["replay"].pass_rate,
        regression_rate=gate_results["regression"].pass_rate,
        redteam_rate=gate_results["redteam"].pass_rate,
    )

    return True


def promote_all(
    staging_path: Path,
    prod_path: Path,
    registry_path: Path,
    eval_dir: Path,
    audit_log_path: Path,
) -> dict[str, list[str]]:
    """Promote all eligible skills from staging to production.

    Args:
        staging_path: Path to staging skills directory
        prod_path: Path to production skills directory
        registry_path: Path to registry JSON file
        eval_dir: Path to evaluation data directory
        audit_log_path: Path to audit log file

    Returns:
        Dictionary with "promoted", "failed", and "skipped" lists
    """
    registry = Registry(registry_path)

    result = {
        "promoted": [],
        "failed": [],
        "skipped": [],
    }

    for skill_name in registry.list_skills():
        entry = registry.get_entry(skill_name)
        if entry is None:
            continue

        # Skip if no staging version
        if entry.current_staging is None:
            result["skipped"].append(skill_name)
            continue

        # Try to promote
        success = promote_skill(
            skill_name,
            staging_path,
            prod_path,
            registry_path,
            eval_dir,
            audit_log_path,
        )

        if success:
            result["promoted"].append(skill_name)
        else:
            result["failed"].append(skill_name)

    return result


def main() -> None:
    """CLI entry point for skill promotion."""
    parser = argparse.ArgumentParser(
        description="Promote skills from staging to production"
    )
    parser.add_argument(
        "--staging",
        type=Path,
        required=True,
        help="Path to staging skills directory",
    )
    parser.add_argument(
        "--prod",
        type=Path,
        required=True,
        help="Path to production skills directory",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        required=True,
        help="Path to registry JSON file",
    )
    parser.add_argument(
        "--eval-dir",
        type=Path,
        required=True,
        help="Path to evaluation data directory",
    )
    parser.add_argument(
        "--skill",
        type=str,
        default=None,
        help="Promote a specific skill (promotes all if not specified)",
    )
    parser.add_argument(
        "--audit-log",
        type=Path,
        default=Path("data/audit.log"),
        help="Path to audit log file (default: data/audit.log)",
    )

    args = parser.parse_args()

    if args.skill:
        # Promote single skill
        success = promote_skill(
            args.skill,
            args.staging,
            args.prod,
            args.registry,
            args.eval_dir,
            args.audit_log,
        )
        if success:
            print(f"Successfully promoted {args.skill}")
        else:
            print(f"Failed to promote {args.skill}")
            exit(1)
    else:
        # Promote all skills
        result = promote_all(
            args.staging,
            args.prod,
            args.registry,
            args.eval_dir,
            args.audit_log,
        )

        if result["promoted"]:
            print(f"Promoted: {', '.join(result['promoted'])}")
        if result["failed"]:
            print(f"Failed: {', '.join(result['failed'])}")
        if result["skipped"]:
            print(f"Skipped (no staging): {', '.join(result['skipped'])}")

        if result["failed"]:
            exit(1)


if __name__ == "__main__":
    main()
