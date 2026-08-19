# Offline Install Bundle

This bundle is intended for environments that cannot reliably reach PyPI or
GitHub during installation.

Contents:

- `wheelhouse/`: local wheel files for `casperfpga`, `tftpy`, the optional
  `casperfpga-progska` extension, and the full runtime dependency set required
  by `casperfpga`
- `install_offline.sh`: installs from the local wheelhouse without contacting
  package indexes

Usage:

```bash
./install_offline.sh
```

Install the optional `progska` extension when a matching wheel is present:

```bash
./install_offline.sh --with-progska
```

Notes:

- Use a Python version that matches the wheels included in this bundle.
- Create and activate the target virtual environment before running the script.
- The bundle is platform-specific because some dependencies and the optional
  `progska` extension are platform-dependent.
