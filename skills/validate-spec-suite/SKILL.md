---
name: validate-spec-suite
description: Validate OpenClaw specs and contracts (JSON Schema + doc links + examples) and emit an auditable report.
---

# Validate Spec Suite

## Trigger Conditions
- You edited `spec/` or `spec/contracts/skill_schema.json`.
- You are preparing a release or merging to `main`.
- You need a concrete “spec health” signal for CI or review.

## Inputs / Outputs
- Inputs:
  - Repo root (current working directory).
  - Optional: path list if the repo is not in the current workspace.
- Outputs:
  - Console lint output from `tools/contract_lint/lint.py`.
  - `reports/contract_lint_report.md` summarizing findings.

## Steps
1. Ensure dependencies are available:
   - `uv sync`
2. Run spec/contract lint:
   - `uv run python tools/contract_lint/lint.py`
3. If `skills/**/skill.json` exist, validate them against the schema:
   - Example (shell):
     ```bash
     for f in $(find skills -name skill.json); do
       uv run python -m jsonschema -i "$f" spec/contracts/skill_schema.json
     done
     ```
4. Write or update `reports/contract_lint_report.md` with:
   - Command output summary
   - P0/P1/P2 findings
   - Next actions

## Do / Don’t
- Do keep failures actionable with file paths and line numbers when possible.
- Do downgrade “path mentions” in backticks to warnings unless they are real links.
- Don’t auto-fix spec files without a clear owner or approval.
- Don’t mark warnings as P0 unless they break parsing or codegen.

## Acceptance Checklist
- [ ] `tools/contract_lint/lint.py` exits 0 or all errors are explained.
- [ ] Any schema/implementation mismatch is called out.
- [ ] Report saved to `reports/contract_lint_report.md`.

## Example (OpenClaw)
- Schema: `spec/contracts/skill_schema.json`
- Lint command: `uv run python tools/contract_lint/lint.py`
- Report: `reports/contract_lint_report.md`
