"""Tests for SkillLoader."""

import json
from pathlib import Path

import pytest

from src.skill_loader import LoadedSkill, SkillLoader


def _write_registry(path: Path, *, name: str, version: str) -> None:
    data = {
        "skills": {
            name: {
                "name": name,
                "current_prod": version,
                "current_staging": None,
                "versions": {
                    version: {
                        "version": version,
                        "code_hash": "abc",
                        "manifest_hash": "def",
                        "created_at": "2026-02-04T00:00:00",
                        "status": "prod",
                        "validation": {},
                        "promoted_at": "2026-02-04T00:00:00",
                        "disabled_at": None,
                        "disabled_reason": None,
                    }
                },
            }
        },
        "updated_at": "2026-02-04T00:00:00",
    }
    path.write_text(json.dumps(data, indent=2))


def _write_manifest(path: Path, *, name: str, version: str, network: bool = False) -> None:
    manifest = {
        "name": name,
        "version": version,
        "description": "A valid skill description for testing.",
        "inputs_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
        },
        "outputs_schema": {
            "type": "string",
        },
        "permissions": {
            "filesystem": "none",
            "network": network,
            "subprocess": False,
        },
        "dependencies": [],
    }
    path.write_text(json.dumps(manifest, indent=2))


def _write_skill_code(path: Path, *, include_action: bool = True, include_verify: bool = True) -> None:
    parts = ["\"\"\"Sample skill for SkillLoader tests.\"\"\"\n\n"]
    if include_action:
        parts.append(
            "def action(text: str) -> str:\n"
            "    return text.upper()\n\n"
        )
    if include_verify:
        parts.append(
            "def verify() -> bool:\n"
            "    return action(\"ok\") == \"OK\"\n"
        )
    path.write_text("".join(parts))


def _setup_skill_dir(tmp_path: Path, *, name: str, version: str) -> Path:
    prod_root = tmp_path / "skills_prod"
    skill_dir = prod_root / name / version
    skill_dir.mkdir(parents=True)
    return skill_dir


def _make_loader(tmp_path: Path, *, name: str, version: str) -> SkillLoader:
    registry_path = tmp_path / "registry.json"
    _write_registry(registry_path, name=name, version=version)
    return SkillLoader(
        prod_path=tmp_path / "skills_prod",
        registry_path=registry_path,
    )


def test_load_manifest_and_module_and_loaded_skill(tmp_path: Path) -> None:
    name = "sample_skill"
    version = "1.0.0"
    skill_dir = _setup_skill_dir(tmp_path, name=name, version=version)

    _write_manifest(skill_dir / "skill.json", name=name, version=version)
    _write_skill_code(skill_dir / "skill.py")

    loader = _make_loader(tmp_path, name=name, version=version)

    manifest = loader.load_manifest(name)
    assert manifest.name == name

    module = loader.load_module(name)
    assert hasattr(module, "action")

    loaded = loader.load(name)
    assert isinstance(loaded, LoadedSkill)
    assert loaded.name == name
    assert loaded.version == version

    action = loader.get_action(name)
    verify = loader.get_verify(name)
    assert callable(action)
    assert callable(verify)


def test_missing_manifest_raises(tmp_path: Path) -> None:
    name = "sample_skill"
    version = "1.0.0"
    skill_dir = _setup_skill_dir(tmp_path, name=name, version=version)

    _write_skill_code(skill_dir / "skill.py")
    loader = _make_loader(tmp_path, name=name, version=version)

    with pytest.raises(FileNotFoundError):
        loader.load_manifest(name)


def test_missing_skill_code_raises(tmp_path: Path) -> None:
    name = "sample_skill"
    version = "1.0.0"
    skill_dir = _setup_skill_dir(tmp_path, name=name, version=version)

    _write_manifest(skill_dir / "skill.json", name=name, version=version)
    loader = _make_loader(tmp_path, name=name, version=version)

    with pytest.raises(FileNotFoundError):
        loader.load_module(name)


def test_missing_action_raises(tmp_path: Path) -> None:
    name = "sample_skill"
    version = "1.0.0"
    skill_dir = _setup_skill_dir(tmp_path, name=name, version=version)

    _write_manifest(skill_dir / "skill.json", name=name, version=version)
    _write_skill_code(skill_dir / "skill.py", include_action=False, include_verify=True)
    loader = _make_loader(tmp_path, name=name, version=version)

    with pytest.raises(AttributeError):
        loader.get_action(name)


def test_missing_verify_raises(tmp_path: Path) -> None:
    name = "sample_skill"
    version = "1.0.0"
    skill_dir = _setup_skill_dir(tmp_path, name=name, version=version)

    _write_manifest(skill_dir / "skill.json", name=name, version=version)
    _write_skill_code(skill_dir / "skill.py", include_action=True, include_verify=False)
    loader = _make_loader(tmp_path, name=name, version=version)

    with pytest.raises(AttributeError):
        loader.get_verify(name)


def test_manifest_mvp_violation_raises(tmp_path: Path) -> None:
    name = "sample_skill"
    version = "1.0.0"
    skill_dir = _setup_skill_dir(tmp_path, name=name, version=version)

    _write_manifest(skill_dir / "skill.json", name=name, version=version, network=True)
    _write_skill_code(skill_dir / "skill.py")
    loader = _make_loader(tmp_path, name=name, version=version)

    with pytest.raises(ValueError):
        loader.load_manifest(name)
