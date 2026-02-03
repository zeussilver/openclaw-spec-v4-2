"""Registry class for managing skill versions."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from .models.registry import RegistryData, SkillEntry, SkillVersion, ValidationResult


class Registry:
    """Manages the skill registry for version tracking and lifecycle management."""

    def __init__(self, registry_path: Path) -> None:
        """Initialize registry with the path to the registry JSON file."""
        self.registry_path = registry_path

    def load(self) -> RegistryData:
        """Load registry data from file. Returns empty registry if file missing."""
        if not self.registry_path.exists():
            return RegistryData()
        with open(self.registry_path) as f:
            data = json.load(f)
        return RegistryData.model_validate(data)

    def save(self, data: RegistryData) -> None:
        """Save registry data to file with indent=2."""
        data.updated_at = datetime.now()
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, "w") as f:
            json.dump(data.model_dump(mode="json"), f, indent=2, default=str)

    def add_staging(
        self,
        name: str,
        version: str,
        code_hash: str,
        manifest_hash: str,
        validation: ValidationResult,
    ) -> SkillVersion:
        """Add a new skill version to staging."""
        data = self.load()

        skill_version = SkillVersion(
            version=version,
            code_hash=code_hash,
            manifest_hash=manifest_hash,
            created_at=datetime.now(),
            status="staging",
            validation=validation,
        )

        if name not in data.skills:
            data.skills[name] = SkillEntry(name=name)

        entry = data.skills[name]
        entry.versions[version] = skill_version
        entry.current_staging = version

        self.save(data)
        return skill_version

    def promote(self, name: str, version: str) -> bool:
        """Promote a staging version to production."""
        data = self.load()

        if name not in data.skills:
            return False

        entry = data.skills[name]
        if version not in entry.versions:
            return False

        skill_version = entry.versions[version]
        if skill_version.status != "staging":
            return False

        # Mark old prod as disabled if exists
        if entry.current_prod and entry.current_prod in entry.versions:
            old_prod = entry.versions[entry.current_prod]
            old_prod.status = "disabled"
            old_prod.disabled_at = datetime.now()
            old_prod.disabled_reason = f"Superseded by {version}"

        # Promote new version
        skill_version.status = "prod"
        skill_version.promoted_at = datetime.now()
        entry.current_prod = version

        # Clear staging if this was the staging version
        if entry.current_staging == version:
            entry.current_staging = None

        self.save(data)
        return True

    def rollback(self, name: str, target_version: str) -> bool:
        """Rollback to a previous version."""
        data = self.load()

        if name not in data.skills:
            return False

        entry = data.skills[name]
        if target_version not in entry.versions:
            return False

        target = entry.versions[target_version]

        # Cannot rollback to a non-prod/disabled version that was never in prod
        if target.status == "staging" and target.promoted_at is None:
            return False

        # Disable current prod
        if entry.current_prod and entry.current_prod != target_version:
            current = entry.versions[entry.current_prod]
            current.status = "disabled"
            current.disabled_at = datetime.now()
            current.disabled_reason = f"Rollback to {target_version}"

        # Restore target version
        target.status = "prod"
        entry.current_prod = target_version

        self.save(data)
        return True

    def get_entry(self, name: str) -> SkillEntry | None:
        """Get a skill entry by name."""
        data = self.load()
        return data.skills.get(name)

    def list_skills(self) -> list[str]:
        """List all skill names in the registry."""
        data = self.load()
        return list(data.skills.keys())


def compute_hash(content: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()
