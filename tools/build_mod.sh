#!/bin/sh
# Shattered Lands with the Obsidian Edition mod: the mod's patched DSUN.EXE
# (DSUNLOG.EXE) and its resident helper (DSCLOG.EXE) in one image, lifted
# together, built into the one program as its own entry (tag ds1o).
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
python3 tools/build_image.py "$MOD/dos/DSUNLOG.EXE" --out build/ds1o --tsr "$MOD/dos/DSCLOG.EXE" --mod "$MOD"
# The misses list carries over only below the video memory: the helper and
# the overlays above it move with every helper release, so entries up there
# from an earlier release point at nothing (the lifter skips those it can
# see are stale; converge finds the new ones).
if [ -f build/ds1o/misses.txt ]; then
    python3 -c "
m='build/ds1o/misses.txt'; keep=[x for x in open(m).read().split() if int(x,16) < 0xA0000]
open(m,'w').write('\n'.join(keep)+'\n')"
else
    cp build/ds1/misses.txt build/ds1o/misses.txt 2>/dev/null || true
fi
python3 tools/find_funcs.py build/ds1o | head -1
python3 tools/lift.py build/ds1o | cut -c1-120
python3 tools/lift_drivers.py game/ds1/RESOURCE.GFF build/ds1o | cut -c1-60
cmake -S . -B build/cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DGAME_BUILDS="$PWD/build/ds1;$PWD/build/ds1o;$PWD/build/ds2;$PWD/build/ct" >/dev/null
cmake --build build/cmake 2>&1 | grep -E "error|FAILED" || true
echo "run: build/cmake/dsun --mod $MOD   (or --game game/ds1 --build build/ds1o --cd $MOD/dos)"
