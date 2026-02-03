#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

try:
    import jsonschema
except Exception as exc:  # pragma: no cover
    print(f"ERROR: jsonschema not available: {exc}")
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[2]
SPEC_DIR = ROOT / "spec"
SCHEMA_PATH = SPEC_DIR / "contracts" / "skill_schema.json"

MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
CODE_REF_RE = re.compile(r"`([^`]+\.(?:md|json|jsonschema))`")


def load_schema(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(data)
    return data


def find_refs(obj, refs: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "$ref" and isinstance(value, str):
                refs.append(value)
            else:
                find_refs(value, refs)
    elif isinstance(obj, list):
        for item in obj:
            find_refs(item, refs)


def check_markdown_links(md_path: Path) -> list[str]:
    text = md_path.read_text(encoding="utf-8")
    errors: list[str] = []
    for _, target in MD_LINK_RE.findall(text):
        if target.startswith("http://") or target.startswith("https://") or target.startswith("mailto:"):
            continue
        if target.startswith("#"):
            # Anchor-only link, skip anchor validation for now
            continue
        target_no_anchor = target.split("#", 1)[0]
        if not target_no_anchor:
            continue
        resolved = (md_path.parent / target_no_anchor).resolve()
        if not resolved.exists():
            errors.append(f"{md_path}: link target not found: {target}")
    return errors


def check_backtick_refs(md_path: Path) -> list[str]:
    text = md_path.read_text(encoding="utf-8")
    warnings: list[str] = []
    for target in CODE_REF_RE.findall(text):
        if "<" in target or ">" in target:
            # placeholder like NNN-<desc>.md
            continue
        if target.startswith("data/") or target.endswith("registry.json"):
            # runtime artifacts, not spec files
            continue
        if target.endswith(".json") and not target.startswith("spec/"):
            # only validate spec-scoped json files
            continue
        target_no_anchor = target.split("#", 1)[0]
        resolved = (md_path.parent / target_no_anchor).resolve()
        if not resolved.exists():
            warnings.append(f"{md_path}: backtick ref not found: {target}")
    return warnings


def main() -> int:
    if not SPEC_DIR.exists():
        print(f"ERROR: spec directory not found at {SPEC_DIR}")
        return 2

    print("== Contract Lint ==")

    # JSON Schema validation
    if not SCHEMA_PATH.exists():
        print(f"ERROR: schema not found: {SCHEMA_PATH}")
        return 2

    schema = load_schema(SCHEMA_PATH)
    refs: list[str] = []
    find_refs(schema, refs)
    print(f"Schema OK: {SCHEMA_PATH}")
    print(f"$ref count: {len(refs)}")

    # Validate $ref paths if any
    ref_errors: list[str] = []
    for ref in refs:
        if ref.startswith("http://") or ref.startswith("https://"):
            continue
        if ref.startswith("#"):
            continue
        ref_path = (SCHEMA_PATH.parent / ref).resolve()
        if not ref_path.exists():
            ref_errors.append(f"$ref not found: {ref}")

    # Markdown link checks
    md_errors: list[str] = []
    md_warnings: list[str] = []
    for md in SPEC_DIR.rglob("*.md"):
        md_errors.extend(check_markdown_links(md))
        md_warnings.extend(check_backtick_refs(md))

    if ref_errors:
        print("\n$ref errors:")
        for err in ref_errors:
            print(f"- {err}")
    else:
        print("\n$ref checks: OK")

    if md_errors:
        print("\nMarkdown reference errors:")
        for err in md_errors:
            print(f"- {err}")
    else:
        print("\nMarkdown reference checks: OK")

    if md_warnings:
        print("\nMarkdown reference warnings (backtick refs):")
        for warn in md_warnings:
            print(f"- {warn}")
    else:
        print("\nMarkdown backtick ref warnings: none")

    total_errors = len(ref_errors) + len(md_errors)
    print(f"\nTotal errors: {total_errors}")
    print(f"Total warnings: {len(md_warnings)}")
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
