"""Rollback functionality for skill version management."""

import argparse
from datetime import datetime
from pathlib import Path

from .audit import AuditLogger
from .registry import Registry


def rollback_skill(
    skill_name: str,
    target_version: str,
    registry_path: Path,
    audit_log_path: Path,
    prod_path: Path | None = None,
) -> bool:
    """Rollback a skill to a previous version.

    Args:
        skill_name: Name of the skill to rollback.
        target_version: Version to rollback to.
        registry_path: Path to the registry JSON file.
        audit_log_path: Path to the audit log file.
        prod_path: Optional path to the production skills directory (unused in MVP).

    Returns:
        True on successful rollback.

    Raises:
        ValueError: If skill or version doesn't exist, or target version was never validated.
    """
    registry = Registry(registry_path)
    audit = AuditLogger(audit_log_path)

    # Load registry data
    data = registry.load()

    # Validate skill exists
    if skill_name not in data.skills:
        raise ValueError(f"Skill not found: {skill_name}")

    entry = data.skills[skill_name]

    # Validate target version exists
    if target_version not in entry.versions:
        raise ValueError(f"Version not found: {target_version}")

    target = entry.versions[target_version]

    # Validate target version was previously prod or staging (validated)
    # A version is valid for rollback if it was ever promoted (promoted_at set)
    # or its status is/was prod or disabled (disabled versions were previously prod)
    if target.status == "staging" and target.promoted_at is None:
        raise ValueError(
            f"Cannot rollback to version {target_version}: "
            "version was never promoted to production"
        )

    # Get current prod version info for logging
    current_prod_version = entry.current_prod
    from_version = current_prod_version if current_prod_version else "none"

    # Disable current prod version if exists and different from target
    if current_prod_version and current_prod_version != target_version:
        current = entry.versions[current_prod_version]
        current.status = "disabled"
        current.disabled_at = datetime.now()
        current.disabled_reason = f"Rollback to {target_version}"

        # Log DISABLE event
        audit.log(
            "DISABLE",
            skill=skill_name,
            version=current_prod_version,
            reason=f"Rollback to {target_version}",
        )

    # Set target version as prod
    target.status = "prod"
    entry.current_prod = target_version

    # Save registry
    registry.save(data)

    # Log ROLLBACK event
    audit.log(
        "ROLLBACK",
        skill=skill_name,
        **{"from": from_version},  # 'from' is a keyword, use dict unpacking
        to=target_version,
    )

    return True


def main() -> None:
    """CLI entry point for rollback."""
    parser = argparse.ArgumentParser(
        description="Rollback a skill to a previous version"
    )
    parser.add_argument(
        "--skill",
        required=True,
        help="Name of the skill to rollback",
    )
    parser.add_argument(
        "--to",
        required=True,
        dest="target_version",
        help="Target version to rollback to",
    )
    parser.add_argument(
        "--registry",
        required=True,
        type=Path,
        help="Path to the registry JSON file",
    )
    parser.add_argument(
        "--audit-log",
        required=True,
        type=Path,
        help="Path to the audit log file",
    )
    parser.add_argument(
        "--prod-dir",
        type=Path,
        default=None,
        help="Path to production skills directory (optional)",
    )

    args = parser.parse_args()

    try:
        rollback_skill(
            skill_name=args.skill,
            target_version=args.target_version,
            registry_path=args.registry,
            audit_log_path=args.audit_log,
            prod_path=args.prod_dir,
        )
        print(f"Successfully rolled back {args.skill} to version {args.target_version}")
    except ValueError as e:
        print(f"Error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
