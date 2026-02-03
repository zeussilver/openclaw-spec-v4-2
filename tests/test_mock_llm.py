"""Tests for MockLLM provider."""

import pytest

from src.llm.base import LLMProvider, SkillPackage
from src.llm.mock import MockLLM
from src.security.ast_gate import ASTGate
from src.validators.manifest import validate_manifest


class TestMockLLMInterface:
    """Test MockLLM implements LLMProvider correctly."""

    def test_inherits_from_llm_provider(self):
        """MockLLM should be a subclass of LLMProvider."""
        assert issubclass(MockLLM, LLMProvider)

    def test_instance_is_llm_provider(self):
        """MockLLM instance should be an LLMProvider."""
        llm = MockLLM()
        assert isinstance(llm, LLMProvider)


class TestTextEchoGeneration:
    """Test text_echo skill generation."""

    @pytest.fixture
    def llm(self):
        return MockLLM()

    @pytest.mark.parametrize(
        "capability",
        [
            "echo text",
            "convert text to uppercase",
            "text uppercase converter",
            "case converter",
            "lowercase transformer",
        ],
    )
    def test_generates_text_echo_for_triggers(self, llm, capability):
        """Should generate text_echo for matching keywords."""
        pkg = llm.generate_skill(capability)
        assert pkg.name == "text_echo"
        assert isinstance(pkg, SkillPackage)

    def test_text_echo_has_required_fields(self, llm):
        """Generated package should have all required fields."""
        pkg = llm.generate_skill("echo text")
        assert pkg.name == "text_echo"
        assert isinstance(pkg.code, str)
        assert len(pkg.code) > 0
        assert isinstance(pkg.manifest, dict)
        assert isinstance(pkg.tests, list)

    def test_text_echo_manifest_name_matches(self, llm):
        """Manifest name should match package name."""
        pkg = llm.generate_skill("text echo")
        assert pkg.manifest["name"] == pkg.name

    def test_text_echo_has_version(self, llm):
        """Manifest should have a version."""
        pkg = llm.generate_skill("text echo")
        assert "version" in pkg.manifest
        assert pkg.manifest["version"] == "1.0.0"

    def test_text_echo_has_required_manifest_fields(self, llm):
        """Manifest should have all required fields."""
        pkg = llm.generate_skill("text")
        required_fields = [
            "name",
            "version",
            "description",
            "inputs_schema",
            "outputs_schema",
            "permissions",
        ]
        for field in required_fields:
            assert field in pkg.manifest, f"Missing manifest field: {field}"


class TestFilenameNormalizerGeneration:
    """Test safe_filename_normalize skill generation."""

    @pytest.fixture
    def llm(self):
        return MockLLM()

    @pytest.mark.parametrize(
        "capability",
        [
            "normalize filename",
            "sanitize file name",
            "safe filename converter",
            "filename normalizer",
        ],
    )
    def test_generates_filename_for_triggers(self, llm, capability):
        """Should generate safe_filename_normalize for matching keywords."""
        pkg = llm.generate_skill(capability)
        assert pkg.name == "safe_filename_normalize"

    def test_filename_has_required_fields(self, llm):
        """Generated package should have all required fields."""
        pkg = llm.generate_skill("normalize filename")
        assert pkg.name == "safe_filename_normalize"
        assert isinstance(pkg.code, str)
        assert len(pkg.code) > 0
        assert isinstance(pkg.manifest, dict)

    def test_filename_manifest_name_matches(self, llm):
        """Manifest name should match package name."""
        pkg = llm.generate_skill("filename normalize")
        assert pkg.manifest["name"] == pkg.name


class TestUnknownCapability:
    """Test handling of unknown capabilities."""

    def test_raises_value_error_for_unknown(self):
        """Should raise ValueError for unknown capabilities."""
        llm = MockLLM()
        with pytest.raises(ValueError) as exc_info:
            llm.generate_skill("calculate quantum entanglement")
        assert "cannot generate skill" in str(exc_info.value).lower()

    def test_error_message_includes_capability(self):
        """Error message should include the capability."""
        llm = MockLLM()
        capability = "brew coffee automatically"
        with pytest.raises(ValueError) as exc_info:
            llm.generate_skill(capability)
        assert capability in str(exc_info.value)


class TestASTGateCompliance:
    """Test that generated code passes AST Gate."""

    @pytest.fixture
    def llm(self):
        return MockLLM()

    @pytest.fixture
    def gate(self):
        return ASTGate()

    def test_text_echo_passes_ast_gate(self, llm, gate):
        """text_echo code should pass AST Gate."""
        pkg = llm.generate_skill("text echo")
        result = gate.check(pkg.code)
        assert result.passed, f"AST Gate violations: {result.violations}"

    def test_filename_passes_ast_gate(self, llm, gate):
        """safe_filename_normalize code should pass AST Gate."""
        pkg = llm.generate_skill("filename normalize")
        result = gate.check(pkg.code)
        assert result.passed, f"AST Gate violations: {result.violations}"

    def test_text_echo_uses_only_allowed_imports(self, llm, gate):
        """text_echo should only use allowed imports (json)."""
        pkg = llm.generate_skill("text echo")
        # Should have json import
        assert "import json" in pkg.code
        # Should not have forbidden imports
        result = gate.check(pkg.code)
        assert result.passed

    def test_filename_uses_only_allowed_imports(self, llm, gate):
        """safe_filename_normalize should only use allowed imports (re)."""
        pkg = llm.generate_skill("filename")
        # Should have re import
        assert "import re" in pkg.code
        # Should not have forbidden imports
        result = gate.check(pkg.code)
        assert result.passed


class TestManifestValidation:
    """Test that generated manifests pass validation."""

    @pytest.fixture
    def llm(self):
        return MockLLM()

    def test_text_echo_manifest_validates(self, llm):
        """text_echo manifest should pass validation."""
        pkg = llm.generate_skill("text echo")
        valid, errors = validate_manifest(pkg.manifest)
        assert valid, f"Manifest validation errors: {errors}"

    def test_filename_manifest_validates(self, llm):
        """safe_filename_normalize manifest should pass validation."""
        pkg = llm.generate_skill("filename normalize")
        valid, errors = validate_manifest(pkg.manifest)
        assert valid, f"Manifest validation errors: {errors}"

    def test_manifests_have_safe_permissions(self, llm):
        """Generated manifests should have safe permission defaults."""
        for capability in ["text echo", "filename normalize"]:
            pkg = llm.generate_skill(capability)
            perms = pkg.manifest.get("permissions", {})
            assert perms.get("network") is False
            assert perms.get("subprocess") is False
            assert perms.get("filesystem") == "none"


class TestContextParameter:
    """Test that context parameter is accepted (even if ignored)."""

    def test_accepts_context_parameter(self):
        """generate_skill should accept context parameter."""
        llm = MockLLM()
        pkg = llm.generate_skill("text echo", context="some log context")
        assert pkg.name == "text_echo"

    def test_context_does_not_affect_output(self):
        """Context should not change the output for MockLLM."""
        llm = MockLLM()
        pkg1 = llm.generate_skill("text echo", context="")
        pkg2 = llm.generate_skill("text echo", context="different context")
        assert pkg1.code == pkg2.code
        assert pkg1.manifest == pkg2.manifest
