---
name: detect-breaking-changes
description: Compare baseline vs current branch to identify breaking changes in specs and contracts, and produce migration notes.
---

# Detect Breaking Changes

## Trigger Conditions
- You are preparing a release.
- You changed `spec/contracts/skill_schema.json` or API-facing docs.
- You need a migration note for downstream users.

## Inputs / Outputs
- Inputs:
  - Baseline reference (tag > main > last stable commit).
  - Current branch (usually `dev`).
- Outputs:
  - `reports/change_impact.md` with summary, breaking changes, and migration steps.

## Steps
1. Select baseline:
   - Prefer latest tag; else `main`; else last stable commit hash.
2. Summarize diff:
   - `git diff --stat <baseline>..HEAD`
   - `git log --oneline <baseline>..HEAD`
3. Focus on contract changes:
   - `spec/contracts/skill_schema.json`
   - `spec/**/*.md` (API/CLI changes)
4. Flag breaking change patterns:
   - Field removals
   - Constraint tightening (regex, min/max, enum shrink)
   - Semantic changes in docs (path/CLI change)
5. Write migration guidance and recommended version bump (major/minor/patch).

## Do / Don’t
- Do treat schema “required” changes and enum shrink as breaking.
- Do cite file paths and diffs for every claim.
- Don’t label a change “breaking” without evidence.

## Acceptance Checklist
- [ ] Baseline selection explained.
- [ ] Diff summary included.
- [ ] Breaking changes listed (or explicitly “none”).
- [ ] Migration path provided.
- [ ] Version bump recommendation included.

## Example (OpenClaw)
- Baseline: `main` (no tags)
- Summary: `git diff --stat main..dev`
- Report: `reports/change_impact.md`
