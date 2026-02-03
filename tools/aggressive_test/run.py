#!/usr/bin/env python3
"""Aggressive skill ingestion + sandbox test runner.

Fetches skills from allowlisted sources, validates manifests, runs AST gate,
then executes in sandbox (optionally with network enabled).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import date
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "reports" / "aggressive_test"
DATA_DIR = ROOT / "data" / "aggressive_skills"

sys.path.insert(0, str(ROOT))

from src.security.ast_gate import ASTGate  # noqa: E402
from src.validators.manifest import validate_manifest  # noqa: E402
from src.sandbox.runner import SandboxRunner  # noqa: E402


@dataclass
class SkillResult:
    name: str
    source: str
    path: str
    manifest_valid: bool
    manifest_errors: list[str]
    ast_passed: bool
    ast_violations: list[str]
    sandbox_passed: bool
    sandbox_metrics: dict
    logs_path: str | None
    error: str | None = None


def _load_sources(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("sources", [])


def _clone_repo(url: str, dest: Path) -> None:
    subprocess.run(
        ["git", "clone", "--depth", "1", url, str(dest)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _resolve_source(source: dict, temp_dirs: list[tempfile.TemporaryDirectory]) -> Path:
    source_type = source.get("type")
    if source_type == "path":
        path_value = source.get("path", "")
        path = Path(path_value)
        if not path.is_absolute():
            path = (ROOT / path).resolve()
        return path

    if source_type == "git":
        url = source.get("url")
        if not url:
            raise ValueError("git source missing url")
        temp_dir = tempfile.TemporaryDirectory()
        temp_dirs.append(temp_dir)
        repo_dir = Path(temp_dir.name)
        _clone_repo(url, repo_dir)
        subdir = source.get("subdir")
        return (repo_dir / subdir).resolve() if subdir else repo_dir

    raise ValueError(f"Unsupported source type: {source_type}")


def _copy_skill(src: Path, dest_dir: Path) -> Path:
    if not src.exists():
        raise FileNotFoundError(f"Skill path not found: {src}")
    if not src.is_dir():
        raise FileNotFoundError(f"Skill path is not a directory: {src}")
    dest = dest_dir / src.name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return dest


def _load_manifest(skill_dir: Path) -> dict:
    manifest_path = skill_dir / "skill.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing skill.json in {skill_dir}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _load_code(skill_dir: Path) -> str:
    code_path = skill_dir / "skill.py"
    if not code_path.exists():
        raise FileNotFoundError(f"Missing skill.py in {skill_dir}")
    return code_path.read_text(encoding="utf-8")


def run_tests(
    sources_path: Path,
    allow_network: bool,
    network_mode: str,
    timeout: int,
    max_skills: int | None,
) -> tuple[list[SkillResult], str]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = DATA_DIR / run_id
    logs_dir = run_dir / "logs"
    skills_dir = run_dir / "skills"
    logs_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)

    sources = _load_sources(sources_path)
    if max_skills is not None:
        sources = sources[:max_skills]

    results: list[SkillResult] = []
    temp_dirs: list[tempfile.TemporaryDirectory] = []

    try:
        for source in sources:
            name = source.get("name") or "unnamed"
            try:
                src_path = _resolve_source(source, temp_dirs)
                skill_path = _copy_skill(src_path, skills_dir)
                manifest = _load_manifest(skill_path)
                manifest_name = manifest.get("name", name)
                code = _load_code(skill_path)

                manifest_valid, manifest_errors = validate_manifest(manifest)

                gate = ASTGate()
                gate_result = gate.check(code)

                sandbox = SandboxRunner(
                    timeout=timeout,
                    network_mode=network_mode,
                    allow_network=allow_network,
                )

                logs_path: Path | None = None
                sandbox_passed = False
                metrics: dict = {}

                if sandbox.is_available():
                    sandbox_passed, logs, metrics = sandbox.run(skill_path)
                    logs_path = logs_dir / f"{manifest_name}.log"
                    logs_path.write_text(logs, encoding="utf-8")
                else:
                    logs_path = logs_dir / f"{manifest_name}.log"
                    logs_path.write_text("Docker not available", encoding="utf-8")

                results.append(
                    SkillResult(
                        name=manifest_name,
                        source=source.get("type", "unknown"),
                        path=str(skill_path),
                        manifest_valid=manifest_valid,
                        manifest_errors=manifest_errors,
                        ast_passed=gate_result.passed,
                        ast_violations=gate_result.violations,
                        sandbox_passed=sandbox_passed,
                        sandbox_metrics=metrics,
                        logs_path=str(logs_path) if logs_path else None,
                    )
                )
            except Exception as exc:
                results.append(
                    SkillResult(
                        name=name,
                        source=source.get("type", "unknown"),
                        path="",
                        manifest_valid=False,
                        manifest_errors=[],
                        ast_passed=False,
                        ast_violations=[],
                        sandbox_passed=False,
                        sandbox_metrics={},
                        logs_path=None,
                        error=str(exc),
                    )
                )
    finally:
        for temp_dir in temp_dirs:
            temp_dir.cleanup()

    return results, run_id


def write_report(
    results: list[SkillResult],
    run_id: str,
    allow_network: bool,
    network_mode: str,
    note: str | None = None,
) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"{run_id}.md"
    total = len(results)
    passed = sum(1 for r in results if r.manifest_valid and r.ast_passed and r.sandbox_passed)
    report_lines = [
        f"# Aggressive Test Report ({run_id})",
        "",
        f"- allow_network: {allow_network}",
        f"- network_mode: {network_mode}",
        f"- total_skills: {total}",
        f"- fully_passed: {passed}",
        "",
        "## Results",
    ]
    if note:
        report_lines.append(f"Note: {note}")
        report_lines.append("")

    if not results:
        report_lines.append("No sources configured.")
    else:
        for result in results:
            status = "PASS" if (result.manifest_valid and result.ast_passed and result.sandbox_passed) else "FAIL"
            report_lines.append(f"- {result.name}: {status}")
            report_lines.append(f"  - source: {result.source}")
            report_lines.append(f"  - path: {result.path}")
            report_lines.append(f"  - manifest: {'OK' if result.manifest_valid else 'FAIL'}")
            if result.manifest_errors:
                for err in result.manifest_errors:
                    report_lines.append(f"    - {err}")
            report_lines.append(f"  - ast_gate: {'OK' if result.ast_passed else 'FAIL'}")
            if result.ast_violations:
                for v in result.ast_violations:
                    report_lines.append(f"    - {v}")
            report_lines.append(f"  - sandbox: {'OK' if result.sandbox_passed else 'FAIL'}")
            if result.logs_path:
                report_lines.append(f"  - logs: {result.logs_path}")
            if result.error:
                report_lines.append(f"  - error: {result.error}")

    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggressive skill test runner")
    parser.add_argument(
        "--sources",
        type=Path,
        default=ROOT / "tools" / "aggressive_test" / "sources.json",
        help="Path to sources.json",
    )
    parser.add_argument("--allow-network", action="store_true", help="Allow network in sandbox")
    parser.add_argument(
        "--network-mode",
        default="bridge",
        help="Docker network mode when allow-network is enabled (default: bridge)",
    )
    parser.add_argument("--timeout", type=int, default=30, help="Sandbox timeout in seconds")
    parser.add_argument("--max-skills", type=int, default=None, help="Limit number of skills")
    parser.add_argument(
        "--window-days",
        type=int,
        default=None,
        help="If set, only run within N days from first run",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=DATA_DIR / ".window_start",
        help="State file storing start date for window",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.allow_network:
        network_mode = args.network_mode
    else:
        network_mode = "none"

    if args.window_days is not None:
        args.state_file.parent.mkdir(parents=True, exist_ok=True)
        if args.state_file.exists():
            start_text = args.state_file.read_text(encoding="utf-8").strip()
            try:
                start_date = date.fromisoformat(start_text)
            except ValueError:
                start_date = date.today()
        else:
            start_date = date.today()
            args.state_file.write_text(start_date.isoformat(), encoding="utf-8")

        if (date.today() - start_date).days >= args.window_days:
            run_id = time.strftime("%Y%m%d-%H%M%S")
            report_path = write_report(
                [],
                run_id,
                args.allow_network,
                network_mode,
                note="Test window complete; disable automation to stop further runs.",
            )
            print(f"Report written: {report_path}")
            return 0

    results, run_id = run_tests(
        sources_path=args.sources,
        allow_network=args.allow_network,
        network_mode=network_mode,
        timeout=args.timeout,
        max_skills=args.max_skills,
    )
    report_path = write_report(results, run_id, args.allow_network, network_mode)
    print(f"Report written: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
