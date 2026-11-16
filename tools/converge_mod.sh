#!/bin/sh
# converge_mod.sh [MOD]: the mod's build converged: the creation screen's RECALL, the arena's
# start and (with the playtest kit's save pens-kurzak-door, $PENS_SAVE) the pens' USE screen are
# run headless, side by side, each on its own copy of the game folder and of the build's lists;
# every address in the helper's segment a run found no function at is kept (a screen's handlers
# come one after another: a miss ends the handler early, not the run), an address in the game's
# code only when it is a run's first, and nothing from a run once its stack has gone; then one
# relift and build, until a round finds none. Then `tools/entries.sh save build/ds1o` keeps the
# lists in the repository. (Up to 2.16 the runs went one after another and kept each run's first
# miss only: one to three addresses in eight minutes; 2.17.1's helper needed 170.)
R=$(cd "$(dirname "$0")/.." && pwd); MOD=${1:-$R/../daaki85/darksun-obsidian-edition/obsidian-edition}
MOD=$(cd "$MOD" && pwd)
S=$R/build/converge; mkdir -p $S; cd $R
RECALL="20:key=ESC 24:key=ESC 28:key=ESC 32:key=ESC 40:move=160,90 41:click=160,90 50:rclick=65,55 53:move=130,57 55:click=130,57 64:click=113,192 66:click=155,96 70:click=172,192"
ARENA="20:key=ESC 24:key=ESC 28:key=ESC 32:key=ESC 40:move=160,76 41:click=160,76 90:click=160,40 100:click=160,160 115:click=160,170 130:click=170,150"
PENS="20:key=ESC 24:key=ESC 28:key=ESC 32:key=ESC 40:move=160,106 41:click=160,106 50:click=130,55 56:click=250,48 90:key=u 93:click=60,125 96:click=180,60 99:click=160,104 102:key=ESC 105:click=160,104 110:key=u 114:key=ESC 117:click=157,92 121:key=u"
SAVE=${PENS_SAVE:-$MOD/../playtest/saves/pens-kurzak-door}
prep() {  # NAME: a copy of the game and of the build's lists for one run
  rm -rf $S/g_$1 $S/b_$1; cp -r game/ds1 $S/g_$1; mkdir -p $S/b_$1; rm -f $S/g_$1/SAVE01.SAV
  cp build/ds1o/image.bin build/ds1o/layout.json build/ds1o/functions.json build/ds1o/misses.txt $S/b_$1/
  cp build/ds1o/inside.txt $S/b_$1/ 2>/dev/null
}
run() {  # NAME SECONDS SCRIPT, in the background
  timeout $(( $2 + 60 )) build/cmake/dsun --mod $MOD --game $S/g_$1 --build $S/b_$1 --headless --seconds $2 --input "$3" > $S/$1.log 2>&1 &
}
for round in $(seq 1 40); do
  prep recall; prep arena; run recall 80 "$RECALL"; run arena 150 "$ARENA"
  if [ -f "$SAVE/SAVE01.SAV" ]; then
    prep pens; cp $SAVE/SAVE01.SAV $SAVE/DARKSAVE.GFF $SAVE/CHARSAVE.GFF $S/g_pens/; run pens 125 "$PENS"
  fi
  wait
  S=$S python3 - <<'PY'
import os, re
S = os.environ['S']
before = open('build/ds1o/misses.txt').read().split(); known = set(before)
new = []
for n in ('recall', 'arena', 'pens'):
    if not os.path.exists(f'{S}/{n}.log'): continue
    log = open(f'{S}/{n}.log', errors='replace').read()
    found = [(a, int(sp, 16)) for a, sp in
             re.findall(r'no function at ([0-9A-F]{5}) \(ds=[0-9A-F]+ ss:sp=[0-9A-F]+:([0-9A-F]+)\)', log)]
    keep = []
    for i, (a, sp) in enumerate(found):
        if sp < 0x1000: break                        # the stack gone: nothing after this is real
        if a in known or a in new or a in keep: continue
        if 0xA0000 <= int(a, 16) < 0xC0000 or (i == 0 and int(a, 16) < 0xA0000): keep.append(a)
    new += keep
    at = re.search(r'([0-9.]+) \[dispatch\] no function at ' + found[0][0], log).group(1) if found else '-'
    print(f"{n}: {len(found)} miss(es), kept {keep}, {log.count('Stack overflow')} overflows, first at {at}")
    ip = f'{S}/b_{n}/inside.txt'                      # entries in the middle of functions, merged
    if os.path.exists(ip):
        have = open('build/ds1o/inside.txt').read().splitlines() if os.path.exists('build/ds1o/inside.txt') else []
        keys = {l.split()[0] for l in have if l.split()}
        add = [l for l in open(ip).read().splitlines() if l.split() and l.split()[0] not in keys]
        if add:
            open('build/ds1o/inside.txt', 'a').write(''.join(l + '\n' for l in add)); print(f"  {n}: {len(add)} interior")
open('build/ds1o/misses.txt', 'w').write('\n'.join(before + new) + '\n')
print('new', len(new), new)
open(f'{S}/newcount', 'w').write(str(len(new)))
PY
  [ "$(cat $S/newcount)" = 0 ] && { echo "clean after round $round"; break; }
  python3 tools/find_funcs.py build/ds1o | head -1
  python3 tools/lift.py build/ds1o 2>&1 | grep -v "no instr" | tail -1
  cmake -S . -B build/cmake >/dev/null && cmake --build build/cmake 2>&1 | grep -E "error|FAILED"
  echo "round $round relifted"
done
echo CONVERGE_DONE
