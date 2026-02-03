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


def _run_cmd(cmd: list[str], *, retries: int = 3, backoff_sec: float = 1.0) -> subprocess.CompletedProcess[str]:
    last: subprocess.CompletedProcess[str] | None = None
    for attempt in range(retries):
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode == 0:
            return proc
        last = proc
        time.sleep(backoff_sec * (2**attempt))
    assert last is not None
    raise RuntimeError(f"Command failed after {retries} attempts: {' '.join(cmd)}\n{last.stderr.strip()}")


def _load_sources(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("sources", [])


def _clone_repo(url: str, dest: Path) -> None:
    _run_cmd(["git", "clone", "--depth", "1", url, str(dest)], retries=3, backoff_sec=2.0)


def _gh_search_code(
    query: str,
    *,
    filename: str | None = None,
    limit: int = 30,
    owners: list[str] | None = None,
    repos: list[str] | None = None,
) -> list[dict]:
    cmd = ["gh", "search", "code", query, "--limit", str(limit), "--json", "repository,path,url,sha"]
    if filename:
        cmd.extend(["--filename", filename])
    for owner in owners or []:
        cmd.extend(["--owner", owner])
    for repo in repos or []:
        cmd.extend(["--repo", repo])

    proc = _run_cmd(cmd, retries=3, backoff_sec=2.0)
    try:
        return json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse gh search output: {exc}") from exc


def _expand_github_code_search(
    source: dict,
    temp_dirs: list[tempfile.TemporaryDirectory],
) -> list[tuple[str, Path]]:
    query = source.get("query")
    if not query:
        raise ValueError("github_code_search source missing query")

    filename = source.get("filename")
    limit = int(source.get("limit") or 30)
    owners = source.get("owners")
    repos = source.get("repos")

    hits = _gh_search_code(
        query,
        filename=filename,
        limit=limit,
        owners=list(owners) if isinstance(owners, list) else None,
        repos=list(repos) if isinstance(repos, list) else None,
    )

    # Clone each repo once; then point to the directory containing the hit path.
    repo_to_dir: dict[str, Path] = {}
    candidates: list[tuple[str, Path]] = []
    seen_dirs: set[str] = set()

    for hit in hits:
        repo_info = hit.get("repository") or {}
        repo_name = repo_info.get("nameWithOwner") or repo_info.get("url") or "unknown"
        repo_url = repo_info.get("url")
        path_in_repo = hit.get("path")

        if not repo_url or not path_in_repo:
            continue

        if repo_name not in repo_to_dir:
            temp_dir = tempfile.TemporaryDirectory()
            temp_dirs.append(temp_dir)
            repo_dir = Path(temp_dir.name)
            _clone_repo(repo_url, repo_dir)
            repo_to_dir[repo_name] = repo_dir

        repo_dir = repo_to_dir[repo_name]
        skill_dir = (repo_dir / Path(path_in_repo).parent).resolve()
        key = f"{repo_name}:{skill_dir}"
        if key in seen_dirs:
            continue
        seen_dirs.add(key)
        candidates.append((repo_name, skill_dir))

    return candidates


def _ensure_sandbox_image(image: str) -> None:
    # Build from local Dockerfile.sandbox. This is intentionally opinionated.
    _run_cmd(
        ["docker", "build", "-t", image, "-f", str(ROOT / "docker" / "Dockerfile.sandbox"), str(ROOT)],
        retries=2,
        backoff_sec=5.0,
    )


def _process_skill_dir(
    skill_dir: Path,
    *,
    source_label: str,
    name_hint: str,
    skills_dir: Path,
    logs_dir: Path,
    sandbox_no_net: SandboxRunner,
    sandbox_net: SandboxRunner | None,
    sandbox_available: bool,
    enforce_mvp_constraints: bool,
    allow_network: bool,
    network_requires_permission: bool,
    stress_sandbox: bool,
) -> SkillResult:
    # Copy into the run directory to ensure we're testing the exact snapshot.
    skill_path = _copy_skill(skill_dir, skills_dir)
    manifest = _load_manifest(skill_path)
    manifest_name = manifest.get("name", name_hint)
    code = _load_code(skill_path)

    manifest_valid, manifest_errors = validate_manifest(
        manifest, enforce_mvp_constraints=enforce_mvp_constraints
    )

    gate = ASTGate()
    gate_result = gate.check(code)

    safe_name = manifest_name.replace("/", "_")
    logs_path = logs_dir / f"{safe_name}.log"

    sandbox_passed = False
    metrics: dict = {}

    should_run_sandbox = stress_sandbox or (manifest_valid and gate_result.passed)
    if not should_run_sandbox:
        metrics["skipped"] = True
        metrics["reason"] = "blocked_by_manifest_or_ast_gate"
        logs_path.write_text("SKIPPED: blocked by manifest validation or AST gate", encoding="utf-8")
    elif not sandbox_available:
        metrics["skipped"] = True
        metrics["reason"] = "docker_not_available"
        logs_path.write_text("SKIPPED: Docker not available or sandbox image missing", encoding="utf-8")
    else:
        use_network = False
        if allow_network and sandbox_net is not None:
            if not network_requires_permission:
                use_network = True
            else:
                use_network = (manifest.get("permissions", {}) or {}).get("network") is True
        sandbox = sandbox_net if use_network else sandbox_no_net
        sandbox_passed, logs, metrics = sandbox.run(skill_path)
        metrics["network_used"] = use_network
        logs_path.write_text(logs, encoding="utf-8")

    return SkillResult(
        name=manifest_name,
        source=source_label,
        path=str(skill_path),
        manifest_valid=manifest_valid,
        manifest_errors=manifest_errors,
        ast_passed=gate_result.passed,
        ast_violations=gate_result.violations,
        sandbox_passed=sandbox_passed,
        sandbox_metrics=metrics,
        logs_path=str(logs_path) if logs_path else None,
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
    sources: list[dict],
    allow_network: bool,
    network_mode: str,
    timeout: int,
    max_skills: int | None,
    sandbox_image: str,
    build_sandbox_image: bool,
    enforce_mvp_constraints: bool,
    network_requires_permission: bool,
    stress_sandbox: bool,
) -> tuple[list[SkillResult], str]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = DATA_DIR / run_id
    logs_dir = run_dir / "logs"
    skills_dir = run_dir / "skills"
    logs_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)

    results: list[SkillResult] = []
    temp_dirs: list[tempfile.TemporaryDirectory] = []
    processed = 0

    sandbox_no_net = SandboxRunner(
        image=sandbox_image,
        timeout=timeout,
        network_mode="none",
        allow_network=False,
    )
    sandbox_net: SandboxRunner | None = None
    if allow_network:
        sandbox_net = SandboxRunner(
            image=sandbox_image,
            timeout=timeout,
            network_mode=network_mode,
            allow_network=True,
        )

    sandbox_available = sandbox_no_net.is_available()
    if not sandbox_available and build_sandbox_image:
        try:
            _ensure_sandbox_image(sandbox_image)
        except Exception as exc:
            results.append(
                SkillResult(
                    name="sandbox_image",
                    source="docker_build",
                    path=str(ROOT),
                    manifest_valid=False,
                    manifest_errors=[],
                    ast_passed=False,
                    ast_violations=[],
                    sandbox_passed=False,
                    sandbox_metrics={},
                    logs_path=None,
                    error=f"Failed to build sandbox image: {exc}",
                )
            )
        sandbox_available = sandbox_no_net.is_available()

    try:
        for source in sources:
            if max_skills is not None and processed >= max_skills:
                break

            source_type = source.get("type", "unknown")
            name = source.get("name") or "unnamed"

            if source_type == "github_code_search":
                try:
                    candidates = _expand_github_code_search(source, temp_dirs)
                    for repo_name, skill_dir in candidates:
                        if max_skills is not None and processed >= max_skills:
                            break
                        try:
                            result = _process_skill_dir(
                                skill_dir,
                                source_label=f"github:{repo_name}",
                                name_hint=name,
                                skills_dir=skills_dir,
                                logs_dir=logs_dir,
                                sandbox_no_net=sandbox_no_net,
                                sandbox_net=sandbox_net,
                                sandbox_available=sandbox_available,
                                enforce_mvp_constraints=enforce_mvp_constraints,
                                allow_network=allow_network,
                                network_requires_permission=network_requires_permission,
                                stress_sandbox=stress_sandbox,
                            )
                            results.append(result)
                        except Exception as exc:
                            results.append(
                                SkillResult(
                                    name=f"{repo_name}:{skill_dir.name}",
                                    source=f"github:{repo_name}",
                                    path=str(skill_dir),
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
                        processed += 1
                except Exception as exc:
                    results.append(
                        SkillResult(
                            name=name,
                            source="github_code_search",
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
                    processed += 1
                continue

            try:
                src_path = _resolve_source(source, temp_dirs)
                result = _process_skill_dir(
                    src_path,
                    source_label=source_type,
                    name_hint=name,
                    skills_dir=skills_dir,
                    logs_dir=logs_dir,
                    sandbox_no_net=sandbox_no_net,
                    sandbox_net=sandbox_net,
                    sandbox_available=sandbox_available,
                    enforce_mvp_constraints=enforce_mvp_constraints,
                    allow_network=allow_network,
                    network_requires_permission=network_requires_permission,
                    stress_sandbox=stress_sandbox,
                )
                results.append(result)
            except Exception as exc:
                results.append(
                    SkillResult(
                        name=name,
                        source=source_type,
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
            processed += 1
    finally:
        for temp_dir in temp_dirs:
            temp_dir.cleanup()

    return results, run_id


def write_report(
    results: list[SkillResult],
    run_id: str,
    allow_network: bool,
    network_mode: str,
    sandbox_image: str,
    enforce_mvp_constraints: bool,
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
        f"- sandbox_image: {sandbox_image}",
        f"- enforce_mvp_constraints: {enforce_mvp_constraints}",
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
    parser.add_argument(
        "--network-always-on",
        action="store_true",
        help="When --allow-network is set, grant network to all skills (default: only if manifest.permissions.network is true)",
    )
    parser.add_argument(
        "--stress-sandbox",
        action="store_true",
        help="Run sandbox even when manifest validation or AST gate fails (more aggressive, higher risk)",
    )
    parser.add_argument(
        "--sandbox-image",
        default="openclaw-sandbox:latest",
        help="Docker image name for sandbox execution",
    )
    parser.add_argument(
        "--build-sandbox-image",
        action="store_true",
        help="Build sandbox image if missing",
    )
    parser.add_argument(
        "--relax-mvp-constraints",
        action="store_true",
        help="Disable MVP constraints (allow permissions.network/subprocess to be true)",
    )
    parser.add_argument(
        "--github-query",
        default=None,
        help="Optional GitHub code search query to discover skills dynamically",
    )
    parser.add_argument(
        "--github-filename",
        default="skill.json",
        help="Filename filter used with --github-query (default: skill.json)",
    )
    parser.add_argument(
        "--github-limit",
        type=int,
        default=30,
        help="Result limit used with --github-query (default: 30)",
    )
    parser.add_argument(
        "--github-owner",
        action="append",
        default=[],
        help="Owner filter used with --github-query (repeatable)",
    )
    parser.add_argument(
        "--github-repo",
        action="append",
        default=[],
        help="Repo filter used with --github-query (repeatable, e.g. org/repo)",
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

    sources = _load_sources(args.sources)
    if args.github_query:
        sources.append(
            {
                "type": "github_code_search",
                "name": "github-query",
                "query": args.github_query,
                "filename": args.github_filename,
                "limit": args.github_limit,
                "owners": args.github_owner or None,
                "repos": args.github_repo or None,
            }
        )

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
                args.sandbox_image,
                not args.relax_mvp_constraints,
                note="Test window complete; disable automation to stop further runs.",
            )
            print(f"Report written: {report_path}")
            return 0

    results, run_id = run_tests(
        sources=sources,
        allow_network=args.allow_network,
        network_mode=network_mode,
        timeout=args.timeout,
        max_skills=args.max_skills,
        sandbox_image=args.sandbox_image,
        build_sandbox_image=args.build_sandbox_image,
        enforce_mvp_constraints=not args.relax_mvp_constraints,
        network_requires_permission=not args.network_always_on,
        stress_sandbox=args.stress_sandbox,
    )
    report_path = write_report(
        results,
        run_id,
        args.allow_network,
        network_mode,
        args.sandbox_image,
        not args.relax_mvp_constraints,
    )
    print(f"Report written: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
