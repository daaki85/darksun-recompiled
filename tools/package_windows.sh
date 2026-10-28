#!/bin/sh
# Build the Windows program with MinGW-w64 and put it in a zip with SDL2.dll.
# Needs the SDL2 MinGW development package installed under
# /usr/x86_64-w64-mingw32 (tools/setup_mingw_sdl.sh fetches it).
#
#   tools/package_windows.sh   -> build/darksun-recompiled-windows-x64.zip (both games)
#
# The zip holds no game data: the player points the program at their own
# GOG folder (--game) and at the build folder with image.bin (--build), or
# puts both next to the program as game/ds1 and build/ds1.
set -e
cd "$(dirname "$0")/.."
# GAME_BUILDS is given outright: a build/win configured before the list grew
# would keep its cached, shorter list.
cmake -S . -B build/win -G Ninja -DCMAKE_BUILD_TYPE=Release \
      -DGAME_BUILDS="$PWD/build/ds1;$PWD/build/ds1o;$PWD/build/ds2;$PWD/build/ct" \
      -DCMAKE_TOOLCHAIN_FILE=cmake/mingw-w64-x86_64.cmake >/dev/null
cmake --build build/win
OUT=build/package/windows
rm -rf "$OUT" && mkdir -p "$OUT"
cp build/win/dsun.exe "$OUT/"
cp /usr/x86_64-w64-mingw32/bin/SDL2.dll "$OUT/"
cp README.md "$OUT/README.md"
cp docs/PLAYING.md "$OUT/PLAYING.md"       # the players' how-to
cp third_party/nuked-opl3/LICENSE "$OUT/LICENSE-nuked-opl3.txt"
cp third_party/licenses/SDL2.txt "$OUT/LICENSE-SDL2.txt"
cp third_party/licenses/stb_vorbis.txt "$OUT/LICENSE-stb_vorbis.txt"
cp third_party/spleen/LICENSE "$OUT/LICENSE-spleen.txt"      # the text-mode font
# The memory images made from the owner's own DSUN.EXEs, for the owner's own
# use: they are the games' code, as the program itself is.
for T in ds1 ds1o ds2 ct; do
    [ -f "build/$T/image.bin" ] && mkdir -p "$OUT/build/$T" && cp "build/$T/image.bin" "$OUT/build/$T/image.bin"
done
printf '@echo off\r\nrem Usage: run.bat "C:\\GOG Games\\Dark Sun Shattered Lands"  (or the Wake of the Ravager folder)\r\nif "%%~1"=="" (echo Give the folder of your GOG Dark Sun install as the argument.& pause & exit /b 1)\r\ndsun.exe --game "%%~1"\r\n' > "$OUT/run.bat"
(cd build/package && rm -f ../darksun-recompiled-windows-x64.zip && zip -qr ../darksun-recompiled-windows-x64.zip windows)
ls -la build/darksun-recompiled-windows-x64.zip
