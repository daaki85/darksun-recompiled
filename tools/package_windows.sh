#!/bin/sh
# Build the Windows program with MinGW-w64 and put it in a zip with SDL2.dll.
# Needs the SDL2 MinGW development package installed under
# /usr/x86_64-w64-mingw32 (tools/setup_mingw_sdl.sh fetches it).
#
#   tools/package_windows.sh [build/ds1]   -> build/darksun-recompiled-windows-x64.zip
#
# The zip holds no game data: the player points the program at their own
# GOG folder (--game) and at the build folder with image.bin (--build), or
# puts both next to the program as game/ds1 and build/ds1.
set -e
B=${1:-build/ds1}
cd "$(dirname "$0")/.."
cmake -S . -B build/win -G Ninja -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_TOOLCHAIN_FILE=cmake/mingw-w64-x86_64.cmake -DGAME_BUILD="$PWD/$B" >/dev/null
cmake --build build/win
OUT=build/package/windows
rm -rf "$OUT" && mkdir -p "$OUT"
cp build/win/dsun.exe "$OUT/"
cp /usr/x86_64-w64-mingw32/bin/SDL2.dll "$OUT/"
cp README.md "$OUT/README.md"
cp third_party/nuked-opl3/LICENSE "$OUT/LICENSE-nuked-opl3.txt"
cp third_party/licenses/SDL2.txt "$OUT/LICENSE-SDL2.txt"
# The memory image made from the owner's own DSUN.EXE, for the owner's own
# use: it is the game's code, as the program itself is.
mkdir -p "$OUT/build/ds1" && cp "$B/image.bin" "$OUT/build/ds1/image.bin"
printf '@echo off\r\nrem Usage: run.bat "C:\\GOG Games\\Dark Sun Shattered Lands"\r\nif "%%~1"=="" (echo Give the folder of your GOG Dark Sun Shattered Lands install as the argument.& pause & exit /b 1)\r\ndsun.exe --game "%%~1" --build build\\ds1\r\n' > "$OUT/run.bat"
(cd build/package && rm -f ../darksun-recompiled-windows-x64.zip && zip -qr ../darksun-recompiled-windows-x64.zip windows)
ls -la build/darksun-recompiled-windows-x64.zip
