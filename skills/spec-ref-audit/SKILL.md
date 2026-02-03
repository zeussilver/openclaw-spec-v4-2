---
name: spec-ref-audit
description: Audit spec references ($ref, Markdown links, and path mentions) and report dangling or risky references.
---

# Spec Ref Audit

## Trigger Conditions
- You added or removed spec files.
- You changed document names or paths.
- You need to verify reference integrity before release.

## Inputs / Outputs
- Inputs:
  - Repo root.
  - Optional: spec subdirectory.
- Outputs:
  - Console output listing errors and warnings.
  - Optional report file in `reports/`.

## Steps
1. Run the reference audit:
   - `uv run python tools/contract_lint/lint.py`
2. Review:
   - `$ref errors` (hard failures)
   - `Markdown reference errors` (hard failures)
   - `Markdown reference warnings` (path mentions; review for intent)
3. Convert findings into actions:
   - Fix real broken links.
   - Convert plain text paths to actual Markdown links if they are meant to be navigable.

## Do / Don’t
- Do treat `$ref` issues as P0 (breaks parsing).
- Do keep warnings as P2 unless they block navigation.
- Don’t attempt to “fix” runtime artifacts (e.g., `data/*.json`) as broken links.

## Acceptance Checklist
- [ ] `$ref` count is zero or all refs resolve.
- [ ] No broken Markdown links in `spec/`.
- [ ] Warnings reviewed and either fixed or explicitly accepted.

## Example (OpenClaw)
- Run: `uv run python tools/contract_lint/lint.py`
- Focus files: `spec/README.md`, `spec/architecture.md`, `spec/changes/TEMPLATE.md`
