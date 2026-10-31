#!/usr/bin/env bash
# Regenerate RESULTS.md from the result files in results/. No arguments.
#
#   ./run.sh
#
# This folder is a set of results, not a probe: the measurements were taken on
# a board with the upstream runner. To take new ones, see "Reproducing" in the
# README; drop the new _results.json files into results/ and run this again.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
python3 crossref.py results/esp32_bytecode.json results/esp32_native_via_mpy.json \
    --baseline results/unix_v1.29.0_baseline.json \
    --title 'Upstream test suite (master 321fba0d1) on an ESP32 running v1.29.0' > RESULTS.md
echo "wrote $HERE/RESULTS.md"
head -12 RESULTS.md
