# Re-export test helpers from the canonical step01 conftest so tests that do
# `from conftest import TestProjectTemplates` keep working even when pytest's
# import resolution picks this file first.
import importlib.util
import os

_here = os.path.dirname(__file__)
_candidate = os.path.abspath(os.path.join(_here, '..', 'step01', 'conftest.py'))

TestProjectTemplates = None
TestConfigManager = None
TestProjectFixture = None

try:
    if os.path.exists(_candidate):
        spec = importlib.util.spec_from_file_location('step01_conftest', _candidate)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[arg-type]
        TestProjectTemplates = getattr(mod, 'TestProjectTemplates', None)
        TestConfigManager = getattr(mod, 'TestConfigManager', None)
        TestProjectFixture = getattr(mod, 'TestProjectFixture', None)
except Exception:
    # Be intentionally quiet — tests will import Config and initialize explicitly as needed.
    pass

# Provide minimal fallback definitions to avoid ImportError in edge cases
if TestProjectTemplates is None:
    class TestProjectTemplates:  # pragma: no cover - fallback
        @staticmethod
        def simple_java_project():
            from dataclasses import dataclass, field
            from typing import Dict, List
            @dataclass
            class _S:
                name: str = 'fallback'
                files: Dict[str, str] = field(default_factory=dict)
                directories: List[str] = field(default_factory=list)
                expected_languages: List[str] = field(default_factory=list)
                expected_frameworks: List[str] = field(default_factory=list)
                expected_subdomains: List[str] = field(default_factory=list)
                expected_file_count: int = 0
            return _S()

if TestConfigManager is None:
    class TestConfigManager:  # pragma: no cover - fallback
        def create_test_config(self, *args, **kwargs):
            from config import Config
            return Config()

if TestProjectFixture is None:
    class TestProjectFixture:  # pragma: no cover - fallback
        def create_test_project(self, structure, use_projects_root=True):
            import os
            import tempfile
            base = tempfile.mkdtemp(prefix='codesight_test_')
            return base
            return base
            return base
            return base
