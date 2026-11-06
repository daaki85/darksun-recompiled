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
# The entry-point lists depend on the helper's release (the helper and the overlays above the
# video memory move with it): what a run found is kept above the video memory only for the same
# helper (entries/ds1o-<md5>, tools/entries.sh), and the plain game's list below it is merged in
# (its code is the same; a routine the plain game reached is one the mod's game will).
python3 -c "
import os, hashlib
m='build/ds1o/misses.txt'; i='build/ds1o/inside.txt'
keep=set(x for x in open(m).read().split() if int(x,16) < 0xA0000) if os.path.exists(m) else set()
if os.path.exists('build/ds1/misses.txt'): keep |= set(x for x in open('build/ds1/misses.txt').read().split() if int(x,16) < 0xA0000)
open(m,'w').write('\n'.join(sorted(keep, key=lambda x: int(x, 16)))+'\n')
if os.path.exists(i):
    lines=[l for l in open(i).read().splitlines() if l.split() and int(l.split()[0],16) < 0xA0000]
    open(i,'w').write(''.join(l+'\n' for l in lines))"
sh tools/entries.sh seed build/ds1o "$MOD"
python3 tools/find_funcs.py build/ds1o | head -1
python3 tools/lift.py build/ds1o | cut -c1-120
python3 tools/lift_drivers.py game/ds1/RESOURCE.GFF build/ds1o | cut -c1-60
[ -n "$SKIP_CMAKE" ] && exit 0                      # (tools/build_all.sh configures and compiles itself)
BUILDS="$PWD/build/ds1;$PWD/build/ds1o"
[ -d build/ds2/gen ] && BUILDS="$BUILDS;$PWD/build/ds2"
[ -d build/ct/gen ] && BUILDS="$BUILDS;$PWD/build/ct"
cmake -S . -B build/cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DGAME_BUILDS="$BUILDS" >/dev/null
cmake --build build/cmake 2>&1 | grep -E "error|FAILED" || true
echo "run: build/cmake/dsun --mod $MOD   (or --game game/ds1 --build build/ds1o --cd $MOD/dos)"
