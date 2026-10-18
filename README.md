# Dark Sun Recompiled

A static recompilation of SSI's *Dark Sun: Shattered Lands* (1993) for modern
Windows and Linux: the game's own 16-bit DOS code, translated once to C and
compiled natively, on a small emulated PC (DOS, BIOS, VGA, timer, mouse, XMS)
instead of DOSBox. *Wake of the Ravager* (1994) runs on the same engine and is
planned for the same program, and the
[Obsidian Edition](https://github.com/daaki85/darksun-obsidian-edition) mod is
to be carried over.

**Status: prototype, in play.** The intro, the main menu, START GAME, the
first scene in the arena of Draj with its scripted fight, and walking the
party run, with FM music and digital speech from the game's own translated
sound drivers. See [docs/STATUS.md](docs/STATUS.md).

![The arena's opening scene, drawn by the recompiled game](docs/img/arena-opening.png)
 See [docs/DESIGN.md](docs/DESIGN.md) for how it works and
[docs/STATUS.md](docs/STATUS.md) for where it stands.

**This repository contains no game data or code.** You need the GOG release of
the game; everything made from it (the memory image, the generated C, the
program built from it) is made on your machine and stays out of git.

## Building

Needs Python 3, GCC (or MinGW-w64 for Windows), CMake, Ninja and SDL2.

```sh
git clone --recursive https://github.com/daaki85/darksun-recompiled
cd darksun-recompiled
# the game: innoextract the GOG installer, or copy an installed game folder
innoextract -s -d game/ds1 setup_dark_sun_shattered_lands_1.1_cs_\(28043\).exe
python3 tools/build_image.py game/ds1/DSUN.EXE --out build/ds1
python3 tools/find_funcs.py build/ds1
python3 tools/lift.py build/ds1
python3 tools/lift_drivers.py game/ds1/RESOURCE.GFF build/ds1
cmake -S . -B build/cmake -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/cmake
./build/cmake/dsun --game game/ds1 --build build/ds1
```

**Windows** (cross-built from Linux): `tools/setup_mingw_sdl.sh` once, then
`tools/package_windows.sh` makes `build/darksun-recompiled-windows-x64.zip`
with `dsun.exe` and `SDL2.dll`. The translated code is the same; only the
runtime is compiled for Windows.

`--headless --seconds 20 --shots build/shots` runs it without a window and
saves the screen once a second; `--input "3:key=ESC 5:click=160,100"`
scripts keys and clicks. Addresses the game reached that no translated
function covered are written to `build/ds1/misses.txt`; `tools/rebuild.sh`
feeds them back in.

## Credits

- [pcrecomp](https://github.com/sp00nznet/pcrecomp) (MIT): the x86-16
  decoder, the lifter and the CPU model the generated code runs on.
- [OpenDS](https://github.com/VirInvictus/opends) (MIT): the documentation of
  DSUN.EXE's Borland overlay format that `build_image.py` follows.

Fan project, not affiliated with or endorsed by SSI, Wizards of the Coast or GOG.
