import importlib.util
from pathlib import Path

import pytest


def test_progska_shim_requires_optional_backend():
    module_path = Path(__file__).resolve().parents[2] / "src" / "progska.py"
    spec = importlib.util.spec_from_file_location("test_progska_shim", module_path)
    module = importlib.util.module_from_spec(spec)

    with pytest.raises(ImportError, match="casperfpga-progska"):
        spec.loader.exec_module(module)


def test_upload_to_ram_progska_reports_missing_optional_backend(monkeypatch):
    from casperfpga import skarab_fileops

    monkeypatch.setattr(skarab_fileops, "progska", None)

    with pytest.raises(ImportError, match="casperfpga-progska"):
        skarab_fileops.upload_to_ram_progska("dummy.fpg", [], 1988)
