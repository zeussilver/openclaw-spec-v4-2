# Repo Profile — openclaw-spec-v4-2 (dev)

## 1) Required command outputs (verbatim)

### `git status`
```
On branch dev
Your branch is ahead of 'origin/dev' by 13 commits.
  (use "git push" to publish your local commits)

Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
	new file:   spec/README.md
	new file:   spec/acceptance.md
	new file:   spec/architecture.md
	new file:   spec/changes/TEMPLATE.md
	new file:   spec/contracts/skill_schema.json
	new file:   spec/eval/redteam.md
	new file:   spec/eval/test_cases.md
	new file:   spec/gsd_tasks.md
	new file:   spec/iteration.md
	new file:   spec/overview.md
	new file:   spec/roadmap_b.md
	new file:   spec/security.md

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   docs/USAGE_FOR_BOSS.md
	modified:   pyproject.toml
	modified:   reports/change_impact.md
	modified:   reports/final_brief.md
	modified:   reports/repo_review.md
	modified:   reports/spec_architecture.md
	modified:   uv.lock

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	.DS_Store
	.claude/
	.gsd/
	.prompts/
	.swarm-logs/
	CLAUDE.md
	init-project.sh
	scripts/
```

### `git rev-parse --abbrev-ref HEAD`
```
dev
```

### `git log -n 20 --oneline`
```
5db197a docs: add repo profile, final brief, and example manifest
83dc8fd Merge branch 'codex/skill-creator' into dev
0274f3e Merge branch 'codex/dx-writer' into dev
f39f534 Merge branch 'codex/repo-reviewer' into dev
cadb01c Merge branch 'codex/change-impact' into dev
fcb7ed3 Merge branch 'codex/contract-linter' into dev
2a49afc Merge branch 'codex/spec-architect' into dev
6651c0a skills: add spec validation and change detection skills
e4d67bf docs: add boss usage and contributor guide
a80ddaa docs(repo): add repo review report
7a1ed85 docs(spec): add change impact report
0074230 tools(spec): add contract lint script and report
16a3184 docs(spec): add spec architecture report
f39a92e integration: cross-module wiring, e2e tests, security integration tests
5b752a4 task-7: promote gates (replay, regression, redteam)
b2eb1ef task-6: night evolver with MockLLM
4fd0b84 task-4: AST gate (static security analysis)
1b5226d task-5: docker sandbox harness and runner
2d9407e task-8: rollback and audit logging
3bdb55b task-3: skill contracts and registry
```

### `ls`
```
CLAUDE.md
README.md
data
docker
docs
examples
init-project.sh
pyproject.toml
reports
scripts
skills
skills_prod
skills_staging
spec
src
tests
tools
uv.lock
```

### `tree -L 4` (not installed) → fallback `find . -maxdepth 4 -print`
```
.
./skills_prod
./skills_prod/.gitkeep
./.swarm-logs
./.swarm-logs/verify-wave-4.log
./.swarm-logs/verify-wave-2.log
./.swarm-logs/verify-wave-3.log
./.swarm-logs/verify-wave-1.log
./.swarm-logs/task-8.log
./.swarm-logs/integration.log
./.swarm-logs/task-4.log
./.swarm-logs/task-5.log
./.swarm-logs/task-7.log
./.swarm-logs/task-6.log
./.swarm-logs/task-2.log
./.swarm-logs/pytest-final.log
./.swarm-logs/task-3.log
./.swarm-logs/task-1.log
./.swarm-logs/ruff-final.log
./tools
./tools/contract_lint
./tools/contract_lint/lint.py
./docker
./docker/.gitkeep
./docker/requirements.allowlist.txt
./docker/Dockerfile.sandbox
./docker/entrypoint.sh
./.DS_Store
./uv.lock
./.pytest_cache
./.pytest_cache/CACHEDIR.TAG
./.pytest_cache/README.md
./.pytest_cache/.gitignore
./.pytest_cache/v
./.pytest_cache/v/cache
./.pytest_cache/v/cache/nodeids
./.pytest_cache/v/cache/lastfailed
./.ruff_cache
./.ruff_cache/0.14.14
./.ruff_cache/0.14.14/13696935653559848236
./.ruff_cache/0.14.14/5470316929987289270
./.ruff_cache/CACHEDIR.TAG
./.ruff_cache/.gitignore
./pyproject.toml
./tests
./tests/test_registry.py
./tests/conftest.py
./tests/test_mock_llm.py
./tests/test_security_integration.py
./tests/test_rollback.py
./tests/test_night_evolver.py
./tests/test_skill_model.py
./tests/test_promote.py
./tests/__init__.py
./tests/__pycache__
... (git internals omitted for brevity)
```

## 2) Repo structure (evidence-backed)
- Top-level directories: `data/`, `docker/`, `docs/`, `examples/`, `reports/`, `scripts/`, `skills/`, `skills_prod/`, `skills_staging/`, `spec/`, `src/`, `tests/`, `tools/` (from `ls`).
- `spec/` now staged for tracking (see `git status` staged files).
- The codebase is Python with tests under `tests/` and core logic in `src/`.

## 3) Spec type identification
- JSON Schema: `spec/contracts/skill_schema.json` contains `$schema: http://json-schema.org/draft-07/schema#` (file content previously reviewed).
- Markdown specs: `spec/overview.md`, `spec/architecture.md`, `spec/security.md`, `spec/acceptance.md`, `spec/gsd_tasks.md`, `spec/iteration.md`, `spec/roadmap_b.md`, `spec/eval/*.md`, `spec/changes/TEMPLATE.md`, `spec/README.md`.
- No OpenAPI/Swagger/AsyncAPI/Proto/GraphQL files detected by `find` (only `docs/` matched the pattern search).

## 4) Validation entry points
- Python tooling and dependencies declared in `pyproject.toml`: `jsonschema`, `pytest`, `ruff`, `mypy` (dev).
- Existing spec review checkpoint script: `scripts/spec-review.sh` (manual checklist; references `spec/` and `.gsd/STATE.md`).
- No CI workflows found: `.github/workflows` directory does not exist.

## 5) Notable observations / assumptions
- `spec/` is now staged for tracking, resolving prior “untracked spec” risk.
- Version alignment: `pyproject.toml` updated to `2.0.0` to match spec headers.
