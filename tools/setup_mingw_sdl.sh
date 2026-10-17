#!/bin/sh
# Fetch SDL2's MinGW development package and install it under
# /usr/x86_64-w64-mingw32, where cmake/mingw-w64-x86_64.cmake looks for it.
set -e
V=2.30.0
T=$(mktemp -d)
curl -sSL -o "$T/sdl2.tar.gz" "https://github.com/libsdl-org/SDL/releases/download/release-$V/SDL2-devel-$V-mingw.tar.gz"
tar xzf "$T/sdl2.tar.gz" -C "$T"
cp -r "$T/SDL2-$V/x86_64-w64-mingw32/"* /usr/x86_64-w64-mingw32/
mkdir -p third_party/licenses && cp "$T/SDL2-$V/COPYING.txt" third_party/licenses/SDL2.txt
rm -rf "$T"
echo "SDL2 $V for x86_64-w64-mingw32 installed"
