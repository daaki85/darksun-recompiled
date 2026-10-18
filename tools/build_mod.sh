#!/bin/sh
# Shattered Lands with the Obsidian Edition mod: the mod's patched DSUN.EXE
# (DSUNLOG.EXE) and its resident helper (DSCLOG.EXE) in one image, lifted
# together, built into their own program.
#   tools/build_mod.sh [path to the mod's obsidian-edition folder]
# The mod's Loader prepares DSUNLOG.EXE and its copies of the game's data
# files in <mod>/dos first; the program then runs with that folder as D:.
set -e
cd "$(dirname "$0")/.."
MOD=${1:-../daaki85/darksun-obsidian-edition/obsidian-edition}
MOD=$(cd "$MOD" && pwd)
python3 -c "
import sys; sys.path.insert(0, '$MOD')
from dsloader import launch
r = launch.prepare_patched_game('$PWD/game/ds1')
sys.exit(r or 0)"
python3 tools/build_image.py "$MOD/dos/DSUNLOG.EXE" --out build/ds1mod --tsr "$MOD/dos/DSCLOG.EXE" --mod "$MOD"
[ -f build/ds1mod/misses.txt ] || cp build/ds1/misses.txt build/ds1mod/misses.txt 2>/dev/null || true
python3 tools/find_funcs.py build/ds1mod | head -1
python3 tools/lift.py build/ds1mod | cut -c1-120
python3 tools/lift_drivers.py game/ds1/RESOURCE.GFF build/ds1mod | cut -c1-60
cmake -S . -B build/cmake-mod -G Ninja -DCMAKE_BUILD_TYPE=Release -DGAME_BUILDS="$PWD/build/ds1mod" >/dev/null
cmake --build build/cmake-mod 2>&1 | grep -E "error|FAILED" || true
echo "run: build/cmake-mod/dsun --game game/ds1 --build build/ds1mod --cd $MOD/dos"
