"""Tests for SandboxRunner configuration options."""

import pytest

from src.sandbox.runner import SandboxRunner


def test_network_mode_requires_opt_in():
    """Non-none network mode requires allow_network=True."""
    with pytest.raises(ValueError):
        SandboxRunner(network_mode="bridge")


def test_network_mode_opt_in_ok():
    """Opt-in allows non-none network mode."""
    runner = SandboxRunner(network_mode="bridge", allow_network=True)
    assert runner.network_mode == "bridge"
