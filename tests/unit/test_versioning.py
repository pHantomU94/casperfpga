import importlib

from _casperfpga_version import (
    DEFAULT_BASE_VERSION,
    build_dev_version,
    get_build_version,
    get_runtime_version,
    normalize_version,
    resolve_version_from_git,
    resolve_version_from_env,
)


def test_normalize_version_accepts_pep440_and_tag_refs():
    assert normalize_version("refs/tags/v1.2.3") == "1.2.3"
    assert normalize_version("v2.0.0rc1") == "2.0.0rc1"
    assert normalize_version("1.2.3.dev4+abc") == "1.2.3.dev4+abc"


def test_normalize_version_rejects_invalid_values():
    assert normalize_version("release-1.2.3") is None
    assert normalize_version("refs/heads/main") is None


def test_resolve_version_from_env_prefers_explicit_build_version(monkeypatch):
    monkeypatch.setenv("CASPERFPGA_BUILD_VERSION", "v3.4.5")
    monkeypatch.setenv("GITHUB_REF", "refs/tags/v9.9.9")
    assert resolve_version_from_env() == "3.4.5"


def test_resolve_version_from_env_uses_github_tag_context(monkeypatch):
    monkeypatch.delenv("CASPERFPGA_BUILD_VERSION", raising=False)
    monkeypatch.delenv("GITHUB_REF", raising=False)
    monkeypatch.setenv("GITHUB_REF_TYPE", "tag")
    monkeypatch.setenv("GITHUB_REF_NAME", "v1.7.0")
    assert get_build_version() == "1.7.0"


def test_resolve_version_from_env_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("CASPERFPGA_BUILD_VERSION", raising=False)
    monkeypatch.delenv("GITHUB_REF", raising=False)
    monkeypatch.delenv("GITHUB_REF_TYPE", raising=False)
    monkeypatch.delenv("GITHUB_REF_NAME", raising=False)
    monkeypatch.delenv("CI_COMMIT_TAG", raising=False)
    assert resolve_version_from_env() is None
    assert resolve_version_from_env(default="1.2.3") == "1.2.3"


def test_get_runtime_version_prefers_installed_metadata(monkeypatch):
    module = importlib.import_module("_casperfpga_version")
    monkeypatch.setattr(module, "resolve_version_from_env", lambda default=None: None)
    monkeypatch.setattr(module, "resolve_installed_version", lambda package_name="casperfpga": "5.6.7")
    assert get_runtime_version() == "5.6.7"


def test_get_runtime_version_prefers_explicit_env(monkeypatch):
    module = importlib.import_module("_casperfpga_version")
    monkeypatch.setattr(module, "resolve_version_from_env", lambda default=None: "7.8.9")
    monkeypatch.setattr(module, "resolve_installed_version", lambda package_name="casperfpga": "5.6.7")
    assert get_runtime_version() == "7.8.9"


def test_build_dev_version_uses_timestamp():
    assert build_dev_version("1.2.3", timestamp="202608181530") == "1.2.3.dev202608181530"


def test_resolve_version_from_git_prefers_exact_tag(monkeypatch):
    module = importlib.import_module("_casperfpga_version")

    def fake_run_git(args):
        if args == ["describe", "--tags", "--exact-match"]:
            return "v1.2.3"
        return None

    monkeypatch.setattr(module, "_run_git", fake_run_git)
    assert resolve_version_from_git() == "1.2.3"


def test_resolve_version_from_git_uses_nearest_tag_with_timestamp(monkeypatch):
    module = importlib.import_module("_casperfpga_version")

    def fake_run_git(args):
        if args == ["describe", "--tags", "--exact-match"]:
            return None
        if args == ["describe", "--tags", "--abbrev=0"]:
            return "v2.4.6"
        return None

    monkeypatch.setattr(module, "_run_git", fake_run_git)
    monkeypatch.setattr(module, "build_dev_version", lambda base_version, timestamp=None: base_version + ".devSTAMP")
    assert resolve_version_from_git() == "2.4.6.devSTAMP"


def test_resolve_version_from_git_falls_back_to_default_base(monkeypatch):
    module = importlib.import_module("_casperfpga_version")
    monkeypatch.setattr(module, "_run_git", lambda args: None)
    monkeypatch.setattr(module, "build_dev_version", lambda base_version, timestamp=None: base_version + ".devSTAMP")
    assert resolve_version_from_git() == DEFAULT_BASE_VERSION + ".devSTAMP"
