"""Evaluation gate executor for skill promotion validation.

Implements three gate types:
- replay: Verify new skill solves original problem (100% threshold)
- regression: Ensure historical capability doesn't degrade (≥99% threshold)
- redteam: Security adversarial testing (100% threshold)
"""

import importlib.util
import json
import signal
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class EvalResult:
    """Result of running a single evaluation case."""

    case_id: str
    passed: bool
    actual_output: Any = None
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class GateReport:
    """Report from running an evaluation gate."""

    gate_name: str
    total: int
    passed_count: int
    failed_count: int
    pass_rate: float
    threshold: float
    gate_passed: bool
    results: list[EvalResult] = field(default_factory=list)


class TimeoutError(Exception):
    """Raised when skill execution times out."""


def _timeout_handler(signum: int, frame: Any) -> None:
    """Signal handler for timeout."""
    raise TimeoutError("Skill execution timed out")


class EvalGate:
    """Evaluation gate executor for skill validation."""

    def __init__(self, eval_dir: Path) -> None:
        """Initialize eval gate with the path to evaluation data directory."""
        self.eval_dir = eval_dir

    def load_cases(self, category: str, skill_name: str) -> list[dict]:
        """Load evaluation cases for a specific category and skill.

        Args:
            category: The gate category (replay, regression, redteam)
            skill_name: The skill name to filter cases for

        Returns:
            List of case dictionaries filtered by skill name
        """
        cases_dir = self.eval_dir / category
        if not cases_dir.exists():
            return []

        cases = []
        for case_file in cases_dir.glob("*.json"):
            if case_file.name.startswith("."):
                continue
            with open(case_file) as f:
                case = json.load(f)
            if case.get("skill") == skill_name:
                cases.append(case)

        return cases

    def run_case(self, case: dict, skill_path: Path) -> EvalResult:
        """Execute a single evaluation case against a skill.

        Args:
            case: The evaluation case dictionary
            skill_path: Path to the skill directory containing skill.py

        Returns:
            EvalResult with pass/fail status and details
        """
        case_id = case.get("id", "unknown")
        timeout_ms = case.get("timeout_ms", 5000)
        timeout_sec = timeout_ms / 1000.0

        start_time = time.time()

        try:
            # Load skill module dynamically
            skill_file = skill_path / "skill.py"
            if not skill_file.exists():
                return EvalResult(
                    case_id=case_id,
                    passed=False,
                    error=f"Skill file not found: {skill_file}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            spec = importlib.util.spec_from_file_location("skill", skill_file)
            if spec is None or spec.loader is None:
                return EvalResult(
                    case_id=case_id,
                    passed=False,
                    error="Failed to create module spec",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get action function
            if not hasattr(module, "action"):
                return EvalResult(
                    case_id=case_id,
                    passed=False,
                    error="Skill has no action() function",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            action_func = module.action

            # Execute with timeout
            input_data = case.get("input", {})
            result = None
            error = None

            # Set up timeout using signal (Unix only)
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.setitimer(signal.ITIMER_REAL, timeout_sec)

            try:
                result = action_func(**input_data)
            except TimeoutError:
                error = "timeout"
            except BaseException as e:
                error = str(e)
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, old_handler)

            duration_ms = (time.time() - start_time) * 1000

            # Evaluate expected output
            expected = case.get("expected", {})
            passed = self._evaluate_expected(result, expected, error, duration_ms)

            return EvalResult(
                case_id=case_id,
                passed=passed,
                actual_output=result,
                error=error,
                duration_ms=duration_ms,
            )

        except Exception as e:
            return EvalResult(
                case_id=case_id,
                passed=False,
                error=f"Unexpected error: {e}",
                duration_ms=(time.time() - start_time) * 1000,
            )

    def _evaluate_expected(
        self,
        result: Any,
        expected: dict,
        error: str | None,
        duration_ms: float,
    ) -> bool:
        """Evaluate result against expected output specification.

        Args:
            result: The actual output from skill execution
            expected: The expected specification dictionary
            error: Any error that occurred during execution
            duration_ms: Execution duration in milliseconds

        Returns:
            True if result matches expected, False otherwise
        """
        expected_type = expected.get("type", "exact")

        if expected_type == "exact":
            return result == expected.get("value")

        elif expected_type == "contains":
            # Check if result contains substring (for strings)
            # or contains all values (for "values" key from spec)
            if "substring" in expected:
                if not isinstance(result, str):
                    return False
                return expected["substring"] in result
            elif "values" in expected:
                # Handle contains with multiple values
                if result is None:
                    return False
                result_str = str(result)
                return all(v in result_str for v in expected["values"])
            return False

        elif expected_type == "no_forbidden_patterns":
            # Result should not contain any forbidden patterns
            if result is None:
                result_str = ""
            elif isinstance(result, str):
                result_str = result
            else:
                result_str = json.dumps(result)

            forbidden = expected.get("forbidden", [])
            return not any(p in result_str for p in forbidden)

        elif expected_type == "timeout_or_error":
            # Pass if there was an error or timeout
            if error is not None:
                return True
            max_duration = expected.get("max_duration_ms", 5000)
            return duration_ms >= max_duration

        else:
            # Unknown type, fail
            return False

    def run_gate(
        self,
        category: str,
        skill_name: str,
        skill_path: Path,
        threshold: float,
    ) -> GateReport:
        """Run all cases for a gate category against a skill.

        Args:
            category: The gate category (replay, regression, redteam)
            skill_name: The skill name
            skill_path: Path to the skill directory
            threshold: Pass rate threshold (0.0-1.0)

        Returns:
            GateReport with pass/fail status and detailed results
        """
        cases = self.load_cases(category, skill_name)
        results = []

        for case in cases:
            result = self.run_case(case, skill_path)
            results.append(result)

        total = len(results)
        passed_count = sum(1 for r in results if r.passed)
        failed_count = total - passed_count
        pass_rate = passed_count / total if total > 0 else 1.0  # No cases = pass

        # Gate passes if pass rate meets or exceeds threshold
        gate_passed = pass_rate >= threshold

        return GateReport(
            gate_name=category,
            total=total,
            passed_count=passed_count,
            failed_count=failed_count,
            pass_rate=pass_rate,
            threshold=threshold,
            gate_passed=gate_passed,
            results=results,
        )
