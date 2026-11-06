#!/bin/sh
# converge_mod.sh [MOD]: the mod's build converged: the creation screen's RECALL, the arena's
# start and (with the playtest kit's save pens-kurzak-door, $PENS_SAVE) the pens' USE screen are
# run headless, the first miss each run finds is kept (the ones after it are the stack gone
# wrong), the build is relifted, until a run finds none. Then `tools/entries.sh save build/ds1o`
# keeps the lists in the repository.
R=$(cd "$(dirname "$0")/.." && pwd); MOD=${1:-$R/../daaki85/darksun-obsidian-edition/obsidian-edition}
S=$R/build/converge; mkdir -p $S; cd $R
RECALL="20:key=ESC 24:key=ESC 28:key=ESC 32:key=ESC 40:move=160,90 41:click=160,90 50:rclick=65,55 53:move=130,57 55:click=130,57 64:click=113,192 66:click=155,96 70:click=172,192"
ARENA="20:key=ESC 24:key=ESC 28:key=ESC 32:key=ESC 40:move=160,76 41:click=160,76 90:click=160,40 100:click=160,160 115:click=160,170 130:click=170,150"
run() {  # NAME SECONDS SCRIPT -> 0 when clean
  cp build/ds1o/misses.txt $S/before.txt
  timeout $(( $2 + 60 )) build/cmake/dsun --mod $MOD --game game/ds1 --headless --seconds $2 --input "$3" > $S/$1.log 2>&1
  cp game/ds1/CHARSAVE.GFF.keep game/ds1/CHARSAVE.GFF 2>/dev/null
  first=$(grep -o "no function at [0-9A-F]*" $S/$1.log | head -1 | awk '{print $4}')
  S=$S python3 - "$first" <<'EOF'
import sys, os
first = sys.argv[1]
before = set(open(os.environ["S"] + "/before.txt").read().split())
now = open('build/ds1o/misses.txt').read().split()
keep = [m for m in now if m in before or m == first]
open('build/ds1o/misses.txt', 'w').write('\n'.join(keep) + '\n')
EOF
  echo "$1: first miss '${first:-none}', $(grep -c 'Stack overflow' $S/$1.log) overflows"
  [ -z "$first" ]
}
PENS="20:key=ESC 24:key=ESC 28:key=ESC 32:key=ESC 40:move=160,106 41:click=160,106 50:click=130,55 56:click=250,48 90:key=u 93:click=60,125 96:click=180,60 99:click=160,104 102:key=ESC 105:click=160,104 110:key=u 114:key=ESC 117:click=157,92 121:key=u"
SAVE=${PENS_SAVE:-$MOD/../playtest/saves/pens-kurzak-door}
cp game/ds1/CHARSAVE.GFF game/ds1/CHARSAVE.GFF.keep
for round in 1 2 3 4 5 6; do
  clean=1
  run recall 80 "$RECALL" || clean=0
  run arena 150 "$ARENA" || clean=0
  if [ -f "$SAVE/SAVE01.SAV" ]; then
    cp $SAVE/SAVE01.SAV $SAVE/DARKSAVE.GFF game/ds1/; cp $SAVE/CHARSAVE.GFF game/ds1/CHARSAVE.GFF
    run pens 125 "$PENS" || clean=0
    rm -f game/ds1/SAVE01.SAV; cp game/ds1/CHARSAVE.GFF.keep game/ds1/CHARSAVE.GFF
  fi
  [ $clean = 1 ] && { echo "clean after round $round"; break; }
  python3 tools/find_funcs.py build/ds1o | head -1
  python3 tools/lift.py build/ds1o 2>&1 | grep -v "no instr" | tail -1
  cmake -S . -B build/cmake >/dev/null && cmake --build build/cmake 2>&1 | grep -E "error|FAILED"
  echo "round $round relifted"
done
rm -f game/ds1/CHARSAVE.GFF.keep
echo CONVERGE_DONE
