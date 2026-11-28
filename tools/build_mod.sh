#!/bin/sh
# Shattered Lands with the Obsidian Edition mod: the mod's patched DSUN.EXE
# (DSUNLOG.EXE) and its resident helper (DSCLOG.EXE) in one image, lifted
# together, built into the one program as its own entry (tag ds1o).
#   tools/build_mod.sh [path to the mod's obsidian-edition folder] [ravager]
# With "ravager" (or RAVAGER=1), Wake of the Ravager with the mod instead: its
# patched copy DSUNLOG2.EXE and its helper DSCLOG2.EXE, from game/ds2 (tag ds2o).
# The mod's Loader prepares the patched game and its copies of the game's data
# files in <mod>/dos (this script has it do so); the program then runs with
# that folder as D:.
set -e
cd "$(dirname "$0")/.."
MOD=${1:-../daaki85/darksun-obsidian-edition/obsidian-edition}
MOD=$(cd "$MOD" && pwd)
[ "$2" = ravager ] && RAVAGER=1
if [ -n "$RAVAGER" ]; then
  G=ds2; B=ds2o; EXE=DSUNLOG2.EXE; HELPER=DSCLOG2.EXE; ARGS="-W0 -L"
  # (Wake of the Ravager's copies: the mod's new items' pictures come from Shattered Lands' folder)
  python3 -c "
import sys; sys.path.insert(0, '$MOD')
from dsloader import launch, ravager
r = ravager.prepare('$PWD/game/ds2', '$MOD/dos', launch.load_settings(), '$PWD/game/ds1')
print(r) if r else None
sys.exit(1 if r else 0)"
else
  G=ds1; B=ds1o; EXE=DSUNLOG.EXE; HELPER=DSCLOG.EXE; ARGS=""
  python3 -c "
import sys; sys.path.insert(0, '$MOD')
from dsloader import launch
r = launch.prepare_patched_game('$PWD/game/ds1')
sys.exit(r or 0)"
fi
python3 tools/build_image.py "$MOD/dos/$EXE" --out build/$B --args "$ARGS" --tsr "$MOD/dos/$HELPER" --mod "$MOD"
# The entry-point lists depend on the helper's release (the helper and the overlays above the
# video memory move with it): what a run found is kept above the video memory only for the same
# helper (entries/<build>-<md5>, tools/entries.sh), and the plain game's list below it is merged in
# (its code is the same; a routine the plain game reached is one the mod's game will).
python3 -c "
import os, hashlib
m='build/$B/misses.txt'; i='build/$B/inside.txt'
keep=set(x for x in open(m).read().split() if int(x,16) < 0xA0000) if os.path.exists(m) else set()
if os.path.exists('build/$G/misses.txt'): keep |= set(x for x in open('build/$G/misses.txt').read().split() if int(x,16) < 0xA0000)
open(m,'w').write('\n'.join(sorted(keep, key=lambda x: int(x, 16)))+'\n')
if os.path.exists(i):
    lines=[l for l in open(i).read().splitlines() if l.split() and int(l.split()[0],16) < 0xA0000]
    open(i,'w').write(''.join(l+'\n' for l in lines))"
# ... and its overlays' entries too, moved to where the mod's build has each module (the helper
# before them moves them up; one of Wake of the Ravager's goes below the video memory)
python3 - "$G" "$B" <<'PY'
import json, os, sys
g, b = sys.argv[1:]
if os.path.exists(f'build/{g}/misses.txt') and os.path.exists(f'build/{g}/layout.json'):
    mods = {m['index']: m for m in json.load(open(f'build/{g}/layout.json'))['modules'] if m['seg'] is not None}
    ours = {m['index']: m for m in json.load(open(f'build/{b}/layout.json'))['modules'] if m['seg'] is not None}
    have = open(f'build/{b}/misses.txt').read().split()
    add = []
    for x in open(f'build/{g}/misses.txt').read().split():
        a = int(x, 16)
        for i, m in mods.items():
            if m['seg'] * 16 <= a < m['seg'] * 16 + m['size'] and i in ours:
                add.append(f"{a - m['seg'] * 16 + ours[i]['seg'] * 16:05X}")
    open(f'build/{b}/misses.txt', 'a').write(''.join(x + '\n' for x in add if x not in have))
PY
sh tools/entries.sh seed build/$B "$MOD"
# The helper's routines the finder can't follow to (DSCLOG2's install reaches them through a segment
# it works out; both helpers' handlers go into the vectors at run time, and their tails' code is
# reached through TAIL_CALL and PL_CALL): their labels (tools/helper_symbols.py, code_labels) are
# seeds, as entries a run would have found.
python3 - "$MOD/dos/$HELPER" "$B" <<'PY'
import sys, os
sys.path.insert(0, 'tools')
import helper_symbols, json
exe, b = sys.argv[1:]
asm = os.path.join(os.path.dirname(exe), os.path.basename(exe).lower().replace('.exe', '.asm'))
offs = helper_symbols.code_labels(asm, exe) if os.path.exists(asm) else None
if offs is None:
    print(f'(the helper\'s routines were not read from {asm}: nasm is needed; the runs will find them)')
    sys.exit(0)
load = json.load(open(f'build/{b}/layout.json'))['tsr']['load']
have = set(open(f'build/{b}/misses.txt').read().split())
new = [f'{load * 16 + o:05X}' for o in offs]
open(f'build/{b}/misses.txt', 'a').write(''.join(x + '\n' for x in new if x not in have))
print(f'{len(offs)} of the helper\'s routines seeded')
PY
python3 tools/find_funcs.py build/$B | sed -n 1p
python3 tools/lift.py build/$B | cut -c1-120
python3 tools/lift_drivers.py game/$G/RESOURCE.GFF build/$B | cut -c1-60
[ -n "$SKIP_CMAKE" ] && exit 0                      # (tools/build_all.sh configures and compiles itself)
BUILDS="$PWD/build/ds1"
for b in ds1o ds2 ds2o ct; do [ -d build/$b/gen ] && BUILDS="$BUILDS;$PWD/build/$b"; done
cmake -S . -B build/cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DGAME_BUILDS="$BUILDS" >/dev/null
cmake --build build/cmake 2>&1 | grep -E "error|FAILED" || true
if [ -n "$RAVAGER" ]; then
  echo "run: build/cmake/dsun --mod $MOD --game game/ds2   (or --game game/ds2 --build build/ds2o --cd $MOD/dos)"
else
  echo "run: build/cmake/dsun --mod $MOD   (or --game game/ds1 --build build/ds1o --cd $MOD/dos)"
fi
