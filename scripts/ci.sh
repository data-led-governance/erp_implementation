#!/usr/bin/env bash
set -euo pipefail

# Minimal sanity checks that are safe in CI and on the VM.
python -m compileall -q erp_implementation

echo "CI checks passed."
