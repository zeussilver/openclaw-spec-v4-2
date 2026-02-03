# Repo Profile — openclaw-spec-v4-2 (dev)

## 1) Required command outputs (verbatim)

### `git status`
```
On branch dev
Your branch is up to date with 'origin/dev'.

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
	spec/

nothing added to commit but untracked files present (use "git add" to track)
```

### `git rev-parse --abbrev-ref HEAD`
```
dev
```

### `git log -n 20 --oneline`
```
f39a92e integration: cross-module wiring, e2e tests, security integration tests
5b752a4 task-7: promote gates (replay, regression, redteam)
b2eb1ef task-6: night evolver with MockLLM
4fd0b84 task-4: AST gate (static security analysis)
1b5226d task-5: docker sandbox harness and runner
2d9407e task-8: rollback and audit logging
3bdb55b task-3: skill contracts and registry
e553c1e task-2: day logger (log parsing and queue)
f55f27b task-1: project skeleton and dependency lock
d8e673f init: openclaw project
```

### `ls`
```
CLAUDE.md
README.md
data
docker
init-project.sh
pyproject.toml
scripts
skills
skills_prod
skills_staging
spec
src
tests
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
./tests/__pycache__/test_sandbox.cpython-311-pytest-9.0.2.pyc
./tests/__pycache__/test_e2e.cpython-311-pytest-9.0.2.pyc
./tests/__pycache__/test_security_integration.cpython-311-pytest-9.0.2.pyc
./tests/__pycache__/test_eval_gate.cpython-311-pytest-9.0.2.pyc
./tests/__pycache__/test_mock_llm.cpython-311-pytest-9.0.2.pyc
./tests/__pycache__/test_promote.cpython-311-pytest-9.0.2.pyc
./tests/__pycache__/test_audit.cpython-311-pytest-9.0.2.pyc
./tests/__pycache__/test_rollback.cpython-311-pytest-9.0.2.pyc
./tests/__pycache__/test_day_logger.cpython-311-pytest-9.0.2.pyc
./tests/__pycache__/test_ast_gate.cpython-311-pytest-9.0.2.pyc
./tests/__pycache__/test_registry.cpython-311-pytest-9.0.2.pyc
./tests/__pycache__/test_manifest_validator.cpython-311-pytest-9.0.2.pyc
./tests/__pycache__/test_skill_model.cpython-311-pytest-9.0.2.pyc
./tests/__pycache__/conftest.cpython-311.pyc
./tests/__pycache__/__init__.cpython-311.pyc
./tests/__pycache__/test_night_evolver.cpython-311-pytest-9.0.2.pyc
./tests/test_audit.py
./tests/test_sandbox.py
./tests/test_day_logger.py
./tests/test_manifest_validator.py
./tests/test_e2e.py
./tests/test_eval_gate.py
./tests/test_ast_gate.py
./skills_staging
./skills_staging/.gitkeep
./spec
./spec/architecture.md
./spec/overview.md
./spec/changes
./spec/changes/TEMPLATE.md
./spec/contracts
./spec/contracts/skill_schema.json
./spec/README.md
./spec/gsd_tasks.md
./spec/iteration.md
./spec/eval
./spec/eval/redteam.md
./spec/eval/test_cases.md
./spec/roadmap_b.md
./spec/security.md
./spec/acceptance.md
./.claude
./.claude/settings.json
./README.md
./.gsd
./.gsd/STATE.md
./.prompts
./.prompts/task-6-night-evolver.md
./.prompts/task-5-sandbox.md
./.prompts/task-3-registry.md
./.prompts/task-8-rollback-audit.md
./.prompts/task-4-ast-gate.md
./.prompts/task-9-integration.md
./.prompts/task-7-promote.md
./.prompts/task-1-skeleton.md
./.prompts/task-2-day-logger.md
./init-project.sh
./.gitignore
./.venv
./.venv/.lock
./.venv/bin
./.venv/bin/ruff
./.venv/bin/activate.bat
./.venv/bin/dmypy
./.venv/bin/activate.ps1
./.venv/bin/mypyc
./.venv/bin/coverage-3.11
./.venv/bin/python3
./.venv/bin/pytest
./.venv/bin/coverage3
./.venv/bin/python
./.venv/bin/activate.fish
./.venv/bin/python3.11
./.venv/bin/pydoc.bat
./.venv/bin/activate_this.py
./.venv/bin/jsonschema
./.venv/bin/mypy
./.venv/bin/stubtest
./.venv/bin/pygmentize
./.venv/bin/activate
./.venv/bin/activate.nu
./.venv/bin/normalizer
./.venv/bin/deactivate.bat
./.venv/bin/coverage
./.venv/bin/py.test
./.venv/bin/stubgen
./.venv/bin/activate.csh
./.venv/pyvenv.cfg
./.venv/CACHEDIR.TAG
./.venv/.gitignore
./.venv/lib
./.venv/lib/python3.11
./.venv/lib/python3.11/site-packages
./scripts
./scripts/spec-review.sh
./scripts/advance-task.sh
./scripts/run-swarm.sh
./.python-version
./skills
./skills/.gitkeep
./.git
... (git internals omitted here for brevity)
```

## 2) Repo structure (evidence-backed)
- Top-level directories: `data/`, `docker/`, `scripts/`, `skills/`, `skills_prod/`, `skills_staging/`, `spec/`, `src/`, `tests/` (from `ls` output above).
- The `spec/` directory exists but is currently **untracked** per `git status`. It contains the spec docs and schema (from `find` output).
- The codebase is Python with tests under `tests/` and core logic in `src/`.

## 3) Spec type identification
- JSON Schema: `spec/contracts/skill_schema.json` contains `$schema: http://json-schema.org/draft-07/schema#` (see file content).
- Markdown specs: `spec/overview.md`, `spec/architecture.md`, `spec/security.md`, `spec/acceptance.md`, `spec/gsd_tasks.md`, `spec/iteration.md`, `spec/roadmap_b.md`, `spec/eval/*.md`, `spec/changes/TEMPLATE.md` (from `find`).
- No OpenAPI/Swagger/AsyncAPI/Proto/GraphQL files detected by `find` (command returned empty output).

## 4) Validation entry points
- Python tooling and dependencies declared in `pyproject.toml`: `jsonschema`, `pytest`, `ruff`, `mypy` (dev). This implies potential validation via `pytest` and `jsonschema` tooling.
- Existing spec review checkpoint script: `scripts/spec-review.sh` (manual checklist; references `spec/` and `.gsd/STATE.md`).
- No CI workflows found: `.github/workflows` directory does not exist (confirmed via `ls .github` failure).

## 5) Notable observations / assumptions
- **Untracked spec/docs/scripts**: `spec/`, `scripts/`, `CLAUDE.md`, `init-project.sh` show as untracked in `git status`. This may indicate local-only spec additions or a mismatch with repository tracking. Needs confirmation.
- **Version indication in spec**: `spec/README.md` declares version `2.0.0` with last update `2026-02-03` (evidence in file content).
