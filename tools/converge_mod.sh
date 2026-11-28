#!/bin/sh
# converge_mod.sh [MOD]: the mod's build converged: the creation screen's RECALL and its DONE
# (the weapon window, the psionic picks), the arena's start, the scripted bout to its end (the suite's
# mod-spread; 2.19's helper had entries no other run reached) and (with the playtest kit's save pens-kurzak-door, $PENS_SAVE) the pens' USE screen are
# run headless, side by side, each on its own copy of the game folder and of the build's lists;
# every address in the helper's segment (B0000-BFFFF) a run found no function at is kept (a screen's handlers
# come one after another: a miss ends the handler early, not the run), an address in the game's
# code only when it is a run's first, and nothing from a run once its stack has gone; then one
# relift and build, until a round finds none. Then `tools/entries.sh save build/ds1o` keeps the
# lists in the repository. (Up to 2.16 the runs went one after another and kept each run's first
# miss only: one to three addresses in eight minutes; 2.17.1's helper needed 170.)
#
# RAVAGER=1 (or "ravager" after MOD): Wake of the Ravager's mod build (build/ds2o) instead, with its
# own scripts (START GAME to Tyr's opening talk, CREATE CHARACTERS), each on a copy of game/ds2 whose
# roster and saves the mod's Loader has widened (its sheets 48h bytes: dsloader.ravager.widen_files),
# the big files (the CD image, its files, the music, the films) linked, not copied. Its helper's
# segment and tail run past C0000h.
R=$(cd "$(dirname "$0")/.." && pwd); MOD=${1:-$R/../daaki85/darksun-obsidian-edition/obsidian-edition}
MOD=$(cd "$MOD" && pwd)
[ "$2" = ravager ] && RAVAGER=1
S=$R/build/converge; [ -n "$RAVAGER" ] && S=$R/build/converge2
mkdir -p $S; cd $R
G=ds1; B=ds1o; RUNS="recall arena done spread pens"
[ -n "$RAVAGER" ] && { G=ds2; B=ds2o; RUNS="start create"; }
# (the helper's code that stays: its segment and its tail, whose routines run with CS the tail's
# segment, past C0000h; the layout has where it ends)
HLO=0xB0000; HHI=$(python3 -c "import json; t=json.load(open('build/$B/layout.json'))['tsr']; print(hex(t.get('end') or 0xC0000))")
START2="6:key=LSHIFT/500 12:move=150,75 13:click=150,75 80:click=160,150 84:click=160,150 88:click=160,150"   # (Tyr: the talk's boxes clicked on)
CREATE2="6:key=LSHIFT/500 12:move=150,90 13:click=150,90 24:rclick=65,55 27:move=130,57 29:click=130,57 38:click=270,182 44:click=72,46 50:click=123,62"
RECALL="20:key=ESC 24:key=ESC 28:key=ESC 32:key=ESC 40:move=160,90 41:click=160,90 50:rclick=65,55 53:move=130,57 55:click=130,57 64:click=113,192 66:click=155,96 70:click=172,192"
ARENA="20:key=ESC 24:key=ESC 28:key=ESC 32:key=ESC 40:move=160,76 41:click=160,76 90:click=160,40 100:click=160,160 115:click=160,170 130:click=170,150"
DONE="20:key=ESC 24:key=ESC 28:key=ESC 32:key=ESC 40:move=160,90 41:click=160,90 50:rclick=65,55 53:move=130,57 55:click=130,57 64:click=270,182 70:click=72,46 76:click=123,62 80:click=123,62 84:click=123,62 88:click=123,62"   # (2.17: DONE, the weapon window, PICK A PSIONIC POWER's four picks)
SPREAD="20:key=ESC 24:key=ESC 28:key=ESC 32:key=ESC 40:move=160,76 41:click=160,76 90:click=160,40 100:click=160,20 104:click=160,20 108:click=160,20 124:mdrag=160,60,160,150"   # (the suite's mod-spread: the announcer's box clicked away, the scripted bout to its end, the gate)
PENS="20:key=ESC 24:key=ESC 28:key=ESC 32:key=ESC 40:move=160,106 41:click=160,106 50:click=130,55 56:click=250,48 90:key=u 93:click=60,125 96:click=180,60 99:click=160,104 102:key=ESC 105:click=160,104 110:key=u 114:key=ESC 117:click=157,92 121:key=u"
SAVE=${PENS_SAVE:-$MOD/../playtest/saves/pens-kurzak-door}
# The mod's rule switches as its Loader would set them (its defaults, or the settings beside it):
# without them the helper's rule-gated code (the creation screen's weapon window and psionic
# picks among it) never runs, and no run would find its entries (DS_RULES, runtime/main.c).
[ -n "$DS_RULES" ] || DS_RULES=$(cd "$MOD" && python3 -c "from dsloader import game, launch; print('%08X' % game.rules_from_settings(launch.load_settings()))")
# (the sequel's helper takes the rules ported to it: ravager.RULES_PORTED, as the Loader masks them)
[ -n "$RAVAGER" ] && DS_RULES=$(cd "$MOD" && python3 -c "from dsloader import ravager; print('%08X' % (0x$DS_RULES & ravager.RULES_PORTED))")
export DS_RULES; echo "rules $DS_RULES"
DSUN=${DSUN:-build/cmake/dsun}
copy_game() {  # FOLDER: a copy of game/$G to write to, the big files linked
  mkdir -p $1
  for f in game/$G/*; do
    case "$(basename "$f")" in
      game.gog|MUSIC|cd|*.FLI) ln -s "$R/$f" "$1/";;
      *) cp -r "$f" "$1/";;
    esac
  done
}
if [ -n "$RAVAGER" ] && [ ! -d $S/master ]; then   # (the Loader's widened roster and saves, once)
  copy_game $S/master
  (cd "$MOD" && python3 -c "from dsloader import ravager; print('widened:', ravager.widen_files('$S/master'))")
fi
prep() {  # NAME: a copy of the game and of the build's lists for one run
  rm -rf $S/g_$1 $S/b_$1; mkdir -p $S/b_$1
  if [ -n "$RAVAGER" ]; then cp -P -r $S/master $S/g_$1; else cp -r game/ds1 $S/g_$1; rm -f $S/g_$1/SAVE01.SAV; fi
  cp build/$B/image.bin build/$B/layout.json build/$B/functions.json build/$B/misses.txt $S/b_$1/
  cp build/$B/inside.txt $S/b_$1/ 2>/dev/null
}
run() {  # NAME SECONDS SCRIPT, in the background
  if [ -n "$RAVAGER" ]; then
    timeout $(( $2 + 60 )) $DSUN --game $S/g_$1 --cd $MOD/dos --build $S/b_$1 --headless --seconds $2 --input "$3" > $S/$1.log 2>&1 &
  else
    timeout $(( $2 + 60 )) $DSUN --mod $MOD --game $S/g_$1 --build $S/b_$1 --headless --seconds $2 --input "$3" > $S/$1.log 2>&1 &
  fi
}
for round in $(seq 1 40); do
  rm -f $S/*.log
  if [ -n "$RAVAGER" ]; then
    prep start; prep create; run start 100 "$START2"; run create 70 "$CREATE2"
  else
  prep recall; prep arena; prep done; prep spread; run recall 80 "$RECALL"; run arena 150 "$ARENA"; run done 96 "$DONE"; run spread 134 "$SPREAD"
  if [ -f "$SAVE/SAVE01.SAV" ]; then
    prep pens; cp $SAVE/SAVE01.SAV $SAVE/DARKSAVE.GFF $SAVE/CHARSAVE.GFF $S/g_pens/; run pens 125 "$PENS"
  fi
  fi
  wait
  S=$S B=$B HLO=$HLO HHI=$HHI RUNS="$RUNS" python3 - <<'PY'
import os, re
S, B = os.environ['S'], os.environ['B']
HLO, HHI = int(os.environ['HLO'], 16), int(os.environ['HHI'], 16)
before = open(f'build/{B}/misses.txt').read().split(); known = set(before)
new = []; seen = 0
for n in os.environ['RUNS'].split():
    if not os.path.exists(f'{S}/{n}.log'): continue
    log = open(f'{S}/{n}.log', errors='replace').read()
    found = [(a, int(sp, 16)) for a, sp in
             re.findall(r'no function at ([0-9A-F]{5}) \(ds=[0-9A-F]+ ss:sp=[0-9A-F]+:([0-9A-F]+)\)', log)]
    keep = []
    for i, (a, sp) in enumerate(found):
        if sp < 0x1000: break
        seen += 1                        # the stack gone: nothing after this is real
        if a in known or a in new or a in keep: continue
        # (the helper's segment and tail, B0000 to the layout's end; a miss in the video memory below it is a run gone astray)
        if HLO <= int(a, 16) < HHI or (i == 0 and int(a, 16) < 0xA0000): keep.append(a)
    new += keep
    at = re.search(r'([0-9.]+) \[dispatch\] no function at ' + found[0][0], log).group(1) if found else '-'
    print(f"{n}: {len(found)} miss(es), kept {keep}, {log.count('Stack overflow')} overflows, first at {at}")
    ip = f'{S}/b_{n}/inside.txt'                      # entries in the middle of functions, merged
    if os.path.exists(ip):
        have = open(f'build/{B}/inside.txt').read().splitlines() if os.path.exists(f'build/{B}/inside.txt') else []
        keys = {l.split()[0] for l in have if l.split()}
        add = [l for l in open(ip).read().splitlines() if l.split() and l.split()[0] not in keys]
        if add:
            open(f'build/{B}/inside.txt', 'a').write(''.join(l + '\n' for l in add)); print(f"  {n}: {len(add)} interior")
open(f'build/{B}/misses.txt', 'w').write('\n'.join(before + new) + '\n')
print('new', len(new), new, '' if not seen else f'({seen} miss(es) in all: a relift)')
open(f'{S}/newcount', 'w').write(str(seen))     # (a miss already on the list, noted by a run outside this loop, still wants the relift)
PY
  [ "$(cat $S/newcount)" = 0 ] && { echo "clean after round $round"; break; }
  # (one relift and build at a time: the two games' convergences may share the program's build)
  CM=$(dirname $DSUN)
  flock build/.relift.lock sh -c "python3 tools/find_funcs.py build/$B | sed -n 1p
    python3 tools/lift.py build/$B 2>&1 | grep -v 'no instr' | tail -1
    cmake -S . -B $CM >/dev/null && cmake --build $CM 2>&1 | grep -E 'error|FAILED'"
  echo "round $round relifted"
done
echo CONVERGE_DONE
