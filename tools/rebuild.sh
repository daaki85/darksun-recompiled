#!/bin/sh
# Re-run the function finder (it reads build/<game>/misses.txt), the lifter
# and the compiler. Usage: tools/rebuild.sh [build/ds1]
set -e
B=${1:-build/ds1}
cd "$(dirname "$0")/.."
python3 tools/find_funcs.py "$B"
python3 tools/lift.py "$B"
python3 tools/lift_drivers.py "${GAME:-game/ds1}/RESOURCE.GFF" "$B"
cmake -S . -B build/cmake >/dev/null   # the generated file list may have changed
cmake --build build/cmake 2>&1 | grep -E "error|FAILED" || true
