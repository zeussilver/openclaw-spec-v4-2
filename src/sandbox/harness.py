#!/usr/bin/env python3
"""sandbox/harness.py - In-container skill verification entry point.

SECURITY CRITICAL:
- Catches BaseException (not Exception) to prevent SystemExit/KeyboardInterrupt bypass
- Strict `result is True` check (not truthy - 1, "yes", [] all fail)
"""
import sys
import importlib.util
import traceback

VERIFICATION_SUCCESS = "VERIFICATION_SUCCESS"
VERIFICATION_FAILED = "VERIFICATION_FAILED"


def main(skill_path: str) -> int:
    """Execute skill verification in sandbox.

    Args:
        skill_path: Path to skill directory containing skill.py

    Returns:
        0 if verify() returns exactly True, 1 otherwise
    """
    try:
        # Load skill module
        skill_file = f"{skill_path}/skill.py"
        spec = importlib.util.spec_from_file_location("skill", skill_file)
        if spec is None or spec.loader is None:
            print(f"{VERIFICATION_FAILED}: Cannot load skill module from {skill_file}")
            return 1

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Check required functions exist
        if not hasattr(module, 'verify'):
            print(f"{VERIFICATION_FAILED}: Missing verify() function")
            return 1

        if not hasattr(module, 'action'):
            print(f"{VERIFICATION_FAILED}: Missing action() function")
            return 1

        # Execute verify()
        result = module.verify()

        # CRITICAL: Strict check - must be exactly True (not truthy)
        if result is True:
            print(VERIFICATION_SUCCESS)
            return 0
        else:
            print(f"{VERIFICATION_FAILED}: verify() returned {result!r}, expected True")
            return 1

    except BaseException as e:
        # SECURITY: Catch ALL exceptions including SystemExit, KeyboardInterrupt
        # This prevents bypass attempts like `raise SystemExit(0)`
        print(f"{VERIFICATION_FAILED}: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <skill_path>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
