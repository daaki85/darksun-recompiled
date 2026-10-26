#!/bin/sh
# The same scripted arena fight in DOSBox and in the recompiled program, with
# the Obsidian Edition mod loaded in both so its dice log can be read from
# each, and the clocks pinned to the same second (the game seeds its dice from
# the time of day once, at the main menu). The two logs should agree roll for
# roll (docs/STATUS.md, "Checks").
#
#   R=<this repo> MOD=<mod>/obsidian-edition OUT=<folder> tools/dosbox_compare.sh
#
# Needs dosbox (0.74), xvfb-run, xdotool, bc, the mod's Loader (python3) with
# its DSUNLOG.EXE prepared in <mod>/dos, and the mod build of the program
# (build/cmake-mod26/dsun with build/ds1mod26, as tools/build_mod.sh makes it;
# BIN and BUILD name others). DOSBox takes the computer's clock; the program
# gets the same second through DS_CLOCK, plus the offsets in OFFSETS (DOSBox
# takes a moment to boot, so the game may ask the time a second or two later).
set -e
R=${R:-$(cd "$(dirname "$0")/.." && pwd)}
MOD=${MOD:-$R/../daaki85/darksun-obsidian-edition/obsidian-edition}
OUT=${OUT:-/tmp/dosbox-compare}
BIN=${BIN:-$R/build/cmake-mod26/dsun}
BUILD=${BUILD:-$R/build/ds1mod26}
OFFSETS=${OFFSETS:-0 1 2 3}
SCRIPT="20:key=ESC 24:key=ESC 28:key=ESC 32:key=ESC 40:move=160,76 41:click=160,76 90:click=160,40 100:click=160,160"
mkdir -p "$OUT/dosbox/capture"
cat > "$OUT/dosbox/ds1mod.conf" <<EOF
[sdl]
fullscreen=false
output=surface
windowresolution=original
autolock=false
waitonerror=false
[dosbox]
machine=svga_s3
memsize=16
captures=$OUT/dosbox/capture
[render]
scaler=normal2x
aspect=false
[cpu]
core=normal
cputype=auto
cycles=fixed 20000
[mixer]
nosound=false
rate=22050
[sblaster]
sbtype=sb16
sbbase=220
irq=5
dma=1
hdma=5
oplmode=auto
oplrate=22050
[midi]
mpu401=intelligent
mididevice=none
[dos]
xms=true
ems=false
umb=true
[autoexec]
@echo off
mount c "$R/game/ds1"
mount d "$MOD/dos"
c:
lh d:\dsclog.exe
d:\dsunlog.exe
exit
EOF
T=$(date +%s)
echo "T=$T"
cd "$OUT/dosbox"
export SDL_AUDIODRIVER=dummy
xvfb-run -a -s "-screen 0 1024x768x24" sh -c '
  dosbox -conf ds1mod.conf > dosbox_run.log 2>&1 &
  DB=$!
  for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do W=$(xdotool search --name DOSBox 2>/dev/null | tail -1); [ -n "$W" ] && break; sleep 1; done
  eval $(xdotool getwindowgeometry --shell $W)
  echo "window $W at $X,$Y $WIDTH x $HEIGHT"
  xdotool mousemove $((X + 50)) $((Y + 50))              # (focus follows the pointer under Xvfb)
  (cd "'"$MOD"'" && timeout 100 python3 -u -m dsloader dicelog --pid $(pgrep -x dosbox) > "'"$OUT"'/dicelog_dosbox.txt" 2>&1 &)
  t0=$(date +%s.%N)
  at() { now=$(date +%s.%N); d=$(echo "$1 - ($now - $t0)" | bc); [ "$(echo "$d > 0" | bc)" = 1 ] && sleep $d; }
  for t in 20 24 28 32; do at $t; xdotool key Escape; done
  at 40; xdotool mousemove $((X + 320)) $((Y + 152)); at 41; xdotool click 1
  at 90; xdotool mousemove $((X + 320)) $((Y + 80)); xdotool click 1
  at 95; import -window root db95.png 2>/dev/null || true
  at 100; xdotool mousemove $((X + 320)) $((Y + 320)); xdotool click 1
  at 130; kill $DB 2>/dev/null; wait $DB 2>/dev/null'
echo "DOSBox done: $(grep -c 'saving throw' "$OUT/dicelog_dosbox.txt") saving throws logged"
for off in $OFFSETS; do
  (cd "$R" && DS_CLOCK=$((T + off)) timeout 200 "$BIN" --game game/ds1 --build "$BUILD" --cd "$MOD/dos" --headless --seconds 125 --input "$SCRIPT" > "$OUT/ours_$off.log" 2>&1 &)
  sleep 25
  (cd "$MOD" && timeout 105 python3 -u -m dsloader dicelog --pid $(pgrep -x dsun) > "$OUT/dicelog_ours_$off.txt" 2>&1) || true
  sleep 8
  echo "offset $off: $(grep 'saving throw' "$OUT/dicelog_ours_$off.txt" | sed 's/.*d20 \(total \|= \)\([0-9]*\).*/\2/' | tr '\n' ' ')"
done
echo "DOSBox : $(grep 'saving throw' "$OUT/dicelog_dosbox.txt" | sed 's/.*d20 \(total \|= \)\([0-9]*\).*/\2/' | tr '\n' ' ')"
echo "logs in $OUT"
