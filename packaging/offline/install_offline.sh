#!/usr/bin/env sh

set -eu

WITH_PROGSKA=0
if [ "${1:-}" = "--with-progska" ]; then
  WITH_PROGSKA=1
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WHEELHOUSE="$SCRIPT_DIR/wheelhouse"

CASPER_WHEEL=$(find "$WHEELHOUSE" -maxdepth 1 -name 'casperfpga-*.whl' | head -n 1)
TFTPY_WHEEL=$(find "$WHEELHOUSE" -maxdepth 1 -name 'tftpy-*.whl' | head -n 1)

if [ -z "${CASPER_WHEEL}" ] || [ -z "${TFTPY_WHEEL}" ]; then
  echo "Required wheels are missing from $WHEELHOUSE" >&2
  exit 1
fi

python -m pip install --no-index --find-links "$WHEELHOUSE" "$TFTPY_WHEEL"
python -m pip install --no-index --find-links "$WHEELHOUSE" --no-deps "$CASPER_WHEEL"

if [ "$WITH_PROGSKA" -eq 1 ]; then
  PROGSKA_WHEEL=$(find "$WHEELHOUSE" -maxdepth 1 -name 'casperfpga_progska-*.whl' | head -n 1 || true)
  if [ -z "${PROGSKA_WHEEL}" ]; then
    echo "No local casperfpga-progska wheel found for this bundle." >&2
    exit 1
  fi
  python -m pip install --no-index --find-links "$WHEELHOUSE" --no-deps "$PROGSKA_WHEEL"
fi

echo "Offline installation completed."
