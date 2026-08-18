import os
import re
import subprocess
from datetime import datetime

try:
    from importlib import metadata as importlib_metadata
except ImportError:  # pragma: no cover
    import importlib_metadata  # type: ignore


DEFAULT_BASE_VERSION = "0.2.0"
DEFAULT_DEV_VERSION = DEFAULT_BASE_VERSION + ".dev0"

_PEP440_RE = re.compile(
    r"^"
    r"\d+(?:\.\d+)*"
    r"(?:(?:a|b|rc)\d+)?"
    r"(?:\.post\d+)?"
    r"(?:\.dev\d+)?"
    r"(?:\+[a-zA-Z0-9]+(?:[-_.][a-zA-Z0-9]+)*)?"
    r"$"
)


def normalize_version(value):
    if not value:
        return None
    version = value.strip()
    if version.startswith("refs/tags/"):
        version = version[len("refs/tags/"):]
    if version.startswith("v") and len(version) > 1 and version[1].isdigit():
        version = version[1:]
    if not _PEP440_RE.match(version):
        return None
    return version


def build_dev_version(base_version, timestamp=None):
    stamp = timestamp or datetime.utcnow().strftime("%Y%m%d%H%M")
    return "{}.dev{}".format(base_version, stamp)


def resolve_version_from_env(default=None):
    env_candidates = [
        os.environ.get("CASPERFPGA_BUILD_VERSION"),
        os.environ.get("GITHUB_REF") if os.environ.get("GITHUB_REF", "").startswith("refs/tags/") else None,
        os.environ.get("GITHUB_REF_NAME") if os.environ.get("GITHUB_REF_TYPE") == "tag" else None,
        os.environ.get("CI_COMMIT_TAG"),
    ]
    for candidate in env_candidates:
        version = normalize_version(candidate)
        if version:
            return version
    return default


def _run_git(args):
    try:
        output = subprocess.check_output(
            ["git"] + list(args),
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return output.decode("utf-8").strip()


def resolve_version_from_git(default=None):
    exact_tag = normalize_version(_run_git(["describe", "--tags", "--exact-match"]))
    if exact_tag:
        return exact_tag

    nearest_tag = normalize_version(_run_git(["describe", "--tags", "--abbrev=0"]))
    if nearest_tag:
        return build_dev_version(nearest_tag)

    base_version = normalize_version(default) or DEFAULT_BASE_VERSION
    return build_dev_version(base_version)


def resolve_installed_version(package_name="casperfpga"):
    try:
        return importlib_metadata.version(package_name)
    except importlib_metadata.PackageNotFoundError:
        return None


def get_build_version(default=None):
    env_version = resolve_version_from_env(default=None)
    if env_version:
        return env_version
    return resolve_version_from_git(default=default or DEFAULT_BASE_VERSION)


def get_runtime_version(package_name="casperfpga", default=None):
    env_version = resolve_version_from_env(default=None)
    if env_version:
        return env_version
    installed_version = resolve_installed_version(package_name=package_name)
    if installed_version:
        return installed_version
    return resolve_version_from_git(default=default or DEFAULT_BASE_VERSION)
