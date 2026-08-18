"""Optional compatibility shim for the external progska extension package."""

try:
    from casperfpga_progska.progska import *  # noqa: F401,F403
except ImportError as exc:
    raise ImportError(
        "casperfpga-progska is not installed. Install the optional extension "
        "package to enable progska uploads."
    ) from exc
