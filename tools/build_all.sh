#!/bin/sh
# build_all.sh: the whole program from the game folders, as README.md's steps, with the
# entry-point lists the repository keeps (entries/, tools/entries.sh): Shattered Lands
# (game/ds1), Wake of the Ravager (game/ds2) and its character transfer utility, and the mod's
# build when the mod's folder is given ($MOD, or the first argument). Needs Python 3, a C
# compiler, CMake, Ninja and SDL2; the Windows build is tools/package_windows.sh.
set -e
cd "$(dirname "$0")/.."
MOD=${1:-$MOD}
[ -f game/ds1/DSUN.EXE ] || { echo "no game in game/ds1 (innoextract the GOG installer there)"; exit 1; }
[ -d third_party/pcrecomp/tools ] || git submodule update --init --recursive
tools/apply_patches.sh >/dev/null 2>&1 || true
python3 tools/build_image.py game/ds1/DSUN.EXE --out build/ds1 | tail -1
sh tools/entries.sh seed build/ds1
python3 tools/find_funcs.py build/ds1 | head -1
python3 tools/lift.py build/ds1 | tail -1
python3 tools/lift_drivers.py game/ds1/RESOURCE.GFF build/ds1 | tail -1
BUILDS="$PWD/build/ds1"
if [ -f game/ds2/DSUN.EXE ]; then
  python3 tools/build_image.py game/ds2/DSUN.EXE --out build/ds2 --args "-W0 -L" | tail -1
  sh tools/entries.sh seed build/ds2
  python3 tools/find_funcs.py build/ds2 | head -1
  python3 tools/lift.py build/ds2 | tail -1
  python3 tools/lift_drivers.py game/ds2/RESOURCE.GFF build/ds2 | tail -1
  BUILDS="$BUILDS;$PWD/build/ds2"
  if [ -f game/ds2/CHARTRAN.EXE ]; then
    mkdir -p build/chartran
    python3 tools/unlzexe.py game/ds2/CHARTRAN.EXE build/chartran/CHARTRAN.EXE | tail -1
    python3 tools/build_image.py build/chartran/CHARTRAN.EXE --out build/ct --original game/ds2/CHARTRAN.EXE | tail -1
    sh tools/entries.sh seed build/ct
    python3 tools/find_funcs.py build/ct | head -1
    python3 tools/lift.py build/ct | tail -1
    python3 tools/lift_drivers.py game/ds2/RESOURCE.GFF build/ct | tail -1
    BUILDS="$BUILDS;$PWD/build/ct"
  fi
fi
if [ -n "$MOD" ] && [ -f "$MOD/dsloader/launch.py" ]; then
  SKIP_CMAKE=1 sh tools/build_mod.sh "$MOD" | tail -2
  BUILDS="$BUILDS;$PWD/build/ds1o"
fi
cmake -S . -B build/cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DGAME_BUILDS="$BUILDS" >/dev/null
cmake --build build/cmake 2>&1 | grep -E "error|FAILED" || true
ls -la build/cmake/dsun && echo "built: build/cmake/dsun"
