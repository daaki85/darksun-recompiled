#!/bin/sh
# Rebuild with the misses of the last run, run again, until a run finds no new
# address (or ROUNDS rounds). Usage:
#   tools/converge.sh <build dir> <cmake dir> <game dir> [seconds] [extra dsun args...]
set -e
B=$1; C=$2; G=$3; S=${4:-45}; shift 4 2>/dev/null || shift $#
cd "$(dirname "$0")/.."
for round in 1 2 3 4 5 6; do
    python3 tools/find_funcs.py "$B" | head -1
    python3 tools/lift.py "$B" | cut -c1-60
    python3 tools/lift_drivers.py "$G/RESOURCE.GFF" "$B" | cut -c1-40
    cmake -S . -B "$C" >/dev/null
    cmake --build "$C" 2>&1 | grep -E "error|FAILED" || true
    timeout $((S + 30)) "$C/dsun" --game "$G" --build "$B" --headless --seconds "$S" "$@" > "$B/converge.log" 2>&1 || true
    new=$(grep -c "new address" "$B/converge.log" || true)
    echo "round $round: $(grep -c 'no function at' "$B/converge.log") misses; $(grep -o '[0-9]* new address' "$B/converge.log" || echo 'no new address')"
    [ "$new" = "0" ] && break
done
grep -v "^\s*fn_\|(x\|AH=0B\|resize\|stdpatch\|ADV .* +\|ALSA" "$B/converge.log" | tail -25
