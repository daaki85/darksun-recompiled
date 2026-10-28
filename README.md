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

**Players:** [docs/PLAYING.md](docs/PLAYING.md) is the how-to: what you
need, installing on Windows or Linux, starting each game, the window and
the keys, saves, sound, the mod, and what to do when something goes wrong.

**This repository contains no game data or code.** You need the GOG release of
the game; everything made from it (the memory image, the generated C, the
program built from it) is made on your machine and stays out of git.

## Building

Needs Python 3, GCC (or MinGW-w64 for Windows), CMake, Ninja and SDL2.

```sh
git clone --recursive https://github.com/daaki85/darksun-recompiled
cd darksun-recompiled
tools/apply_patches.sh        # this project's fixes to pcrecomp (patches/pcrecomp)
# the game: innoextract the GOG installer, or copy an installed game folder
innoextract -s -d game/ds1 setup_dark_sun_shattered_lands_1.1_cs_\(28043\).exe
python3 tools/build_image.py game/ds1/DSUN.EXE --out build/ds1
python3 tools/find_funcs.py build/ds1
python3 tools/lift.py build/ds1
python3 tools/lift_drivers.py game/ds1/RESOURCE.GFF build/ds1
cmake -S . -B build/cmake -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/cmake
./build/cmake/dsun                      # finds game/ds1 (and game/ds2) itself
```

**Wake of the Ravager** goes through the same steps with `game/ds2` and
`build/ds2`, plus its command line and its CD: GOG starts it as `DSUN -W0 -L`,
and its data CD is `game.gog`, a raw MODE2/2352 track (2,048 data bytes at
offset 24 of each 2,352-byte sector). The program unpacks it into
`game/ds2/cd` the first time it starts the game (`runtime/iso.c`) and uses
that folder as drive D:; `tools/cd_extract.py` does the same by hand.

```sh
python3 tools/build_image.py game/ds2/DSUN.EXE --out build/ds2 --args "-W0 -L"
tools/converge.sh build/ds2 build/cmake game/ds2 60
```

**The character transfer utility** (`CHARTRAN.EXE`, in Wake of the Ravager's
folder, which carries a Shattered Lands party into the sequel's roster) is
built in as a third program, tag `ct`. It is LZEXE-packed; `tools/unlzexe.py`
unpacks it, and `build_image.py` takes the plain program (no overlays: its
code segments come from its relocations). It is a text-mode program, so the
runtime draws text mode too (`runtime/vga.c`, with Spleen's 8x16 font from
`third_party/spleen`) and answers the BIOS and DOS console services. Started
with `--transfer`, the program finds both games (or takes `--ds1` and
`--ds2`) and mounts them as the `C:\DSUN` and `C:\RAVAGER` the utility
expects.

```sh
python3 tools/unlzexe.py game/ds2/CHARTRAN.EXE build/chartran/CHARTRAN.EXE
python3 tools/build_image.py build/chartran/CHARTRAN.EXE --out build/ct --original game/ds2/CHARTRAN.EXE
tools/converge.sh build/ct build/cmake game/ds2 12 --transfer --ds1 game/ds1 --ds2 game/ds2 --input "3:key=RET 7:key=A"
```

**One program, both games.** CMake builds every game whose `build/<tag>/gen`
exists into the one `dsun` (the list is `GAME_BUILDS`; each game's symbols
carry its tag, `ds1_`, `ds2_` or `ct_`). The program recognises a game folder by
the size of its `DSUN.EXE`: `--game <folder>` names one; without it, the
program looks for `game/ds1` and `game/ds2` beside the current folder and
beside itself, then in `dsun.ini` beside itself, then in GOG's usual
install folders, and last asks with a folder picker (remembering the
answer in `dsun.ini`); it asks with a message box when it finds both games
(or takes `DS_GAME=ds1|ds2`). `--build` defaults to `build/<tag>` beside
the current folder or the program.

Its music is CD audio, read from GOG's `MUSIC/TrackNN.ogg` files in the
game folder through an emulated MSCDEX drive (`runtime/cd.c`).

Its regression cases (`tests/cases/wotr-*.toml`) run with the rest under
`python3 tests/run.py`.

**The Obsidian Edition mod.** `tools/build_mod.sh <mod>/obsidian-edition`
builds Shattered Lands with the mod's patched EXE and its resident helper
into `build/cmake-mod/dsun` (see docs/DESIGN.md, "The mod"); run it with
`--game game/ds1 --build build/ds1mod --cd <mod>/obsidian-edition/dos`.
The mod's Loader can start it instead of DOSBox (`dsloader launch
--recompiled <path to dsun>`; its `recompiled` branch (on top of 2.12.1), also
docs/loader-recompiled.patch) and attaches its dice log and window to it.

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
