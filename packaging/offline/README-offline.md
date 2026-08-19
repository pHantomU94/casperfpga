# Offline Install Bundle

This bundle is intended for environments that cannot reliably reach PyPI or GitHub
during installation.

Contents:

- `wheelhouse/`: local wheel files for `casperfpga`, `tftpy`, and optional
  `casperfpga-progska`
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

The script uses the current Python interpreter. Create and activate the target
virtual environment before running it if needed.
