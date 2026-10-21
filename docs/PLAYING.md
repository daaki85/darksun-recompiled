# Playing Dark Sun Recompiled

A how-to for players. It covers what you need, how to install and start the
program, how it behaves while you play, the Obsidian Edition mod, and what
to do when something goes wrong. How the program works inside is in
[DESIGN.md](DESIGN.md); where the project stands is in [STATUS.md](STATUS.md).

**Read this first.** The project is a prototype. What has been played
through on it is the start of each game: the intro, the menus, character
creation, the first fight in the arena of Draj with saving and loading, and
the opening of *Wake of the Ravager* in Tyr. Everything past that is
untested and may stop with an error. Keep your DOSBox installation; your
saves work in both (see [Saving and loading](#saving-and-loading)).

## Contents

- [What it is](#what-it-is)
- [What you need](#what-you-need)
- [Installing on Windows](#installing-on-windows)
- [Installing on Linux](#installing-on-linux)
- [Starting a game](#starting-a-game)
- [Wake of the Ravager's CD](#wake-of-the-ravagers-cd)
- [While you play](#while-you-play)
- [Saving and loading](#saving-and-loading)
- [Sound](#sound)
- [The Obsidian Edition mod](#the-obsidian-edition-mod)
- [When something goes wrong](#when-something-goes-wrong)
- [What is not there yet](#what-is-not-there-yet)

## What it is

*Dark Sun: Shattered Lands* (1993) and *Dark Sun: Wake of the Ravager*
(1994) are DOS games. GOG ships them with DOSBox, which runs a whole PC in
software and runs the game's code on it instruction by instruction.

Dark Sun Recompiled does something else: the game's own code has been
translated, once, into a native program. What remains emulated is the
small world around the game (DOS, the BIOS, the VGA, the timer, the mouse,
the sound card), not the game itself. The game plays its own rules, with its
own dice; nothing of the game has been rewritten.

One program, `dsun`, holds both games. It reads your own copy of the game's
data files, from your GOG installation.

## What you need

- **The games from GOG**: *Dark Sun: Shattered Lands* and/or *Dark Sun:
  Wake of the Ravager*, installed, or their installers unpacked. The program
  contains none of the games' data. Each game is recognised by the size of
  its `DSUN.EXE` (611,408 bytes for Shattered Lands, 634,416 for Wake of the
  Ravager, GOG's versions).
- **Windows 10 or 11, 64-bit**, or a Linux with SDL2. There is no macOS
  build.
- A mouse. The games are played with the mouse and a few keys.

For *Wake of the Ravager* you also need its CD's files unpacked once, see
[Wake of the Ravager's CD](#wake-of-the-ravagers-cd).

## Installing on Windows

1. Download `darksun-recompiled-windows-x64.zip` and unzip it anywhere, for
   example `C:\Games\DarkSunRecompiled`. It holds:
   - `dsun.exe`, the program, and `SDL2.dll`, which it needs beside it;
   - `build\ds1\image.bin` and `build\ds2\image.bin`, the games' memory
     images, one per game;
   - `run.bat`, a starter that takes your game folder as its argument;
   - this guide and the licences of the libraries used.
2. Find your GOG game folder: the one with `DSUN.EXE` in it, such as
   `C:\GOG Games\Dark Sun Shattered Lands` or
   `C:\Program Files (x86)\GOG Galaxy\Games\Dark Sun Shattered Lands`.
3. Start the game one of these ways:
   - Drag the game folder onto `run.bat`.
   - Open a command prompt in the unzipped folder and run
     `dsun.exe --game "C:\GOG Games\Dark Sun Shattered Lands"`.
   - Make a shortcut to `dsun.exe` and add
     ` --game "C:\GOG Games\Dark Sun Shattered Lands"` to its target, after
     the closing quote of the program's path.
   - Or copy (or link) your game folder to `game\ds1` (Shattered Lands) or
     `game\ds2` (Wake of the Ravager) beside `dsun.exe`; then `dsun.exe`
     needs no argument. With both there, it asks which to start.

Windows may warn that the program is unsigned ("Windows protected your
PC"). Click **More info**, then **Run anyway**. The zip is not signed.

## Installing on Linux

There is no prebuilt Linux program: the program is built from your own copy
of the game, which takes about an hour the first time. The steps are in the
[README](../README.md#building); in short: clone the repository, unpack the
GOG installer with `innoextract` into `game/ds1`, run the four tools that
make the memory image and the translated code, and build with CMake. You
need Python 3, GCC, CMake, Ninja, SDL2's development package, and
`innoextract`. The result is `build/cmake/dsun`, started as on Windows:

```sh
./build/cmake/dsun --game ~/GOG\ Games/Dark\ Sun\ Shattered\ Lands
```

## Starting a game

`dsun --game <folder>` starts the game in that folder. Without `--game`,
the program looks for `game/ds1` and `game/ds2` beside itself and beside the
folder it was started from, and asks with a message box when both are
there (or takes the environment variable `DS_GAME=ds1` or `ds2`).

Each game needs its memory image, `build/ds1/image.bin` or
`build/ds2/image.bin`, found the same way (beside the program or the
current folder) or named with `--build <folder>`. The Windows zip has both.

The program writes a log of what it does to its standard error. To keep
it, start it from a command prompt and redirect:

```
dsun.exe --game "C:\GOG Games\Dark Sun Shattered Lands" 2> log.txt
```

## Wake of the Ravager's CD

*Wake of the Ravager* reads its data from a CD. GOG ships the CD as
`game.gog` in the game folder, a raw disc image, and the music as
`MUSIC\TrackNN.ogg`. The program plays the music from the OGG files as the
game asks for its CD audio tracks, but the data files have to be unpacked
from `game.gog` once, into a folder called `cd` inside the game folder:

```sh
python3 tools/cd_extract.py "C:\GOG Games\Dark Sun Wake of the Ravager\game.gog" "C:\GOG Games\Dark Sun Wake of the Ravager\cd"
```

This needs Python 3 and `7z` (7-Zip's command line) on the path. The
program then uses that folder as the game's drive D:. Without it the game
cannot start, and the log says so:
`no .../cd: the CD's files are missing (tools/cd_extract.py)`.

## While you play

- **The window** opens at three times the game's size and can be resized;
  the picture keeps its 4:3 shape. **F11** or **Alt+Enter** switches to full
  screen and back. Closing the window ends the game at once, without saving.
- **The mouse** is the game's: the pointer is the game's own pointer, drawn
  by the game. The right button opens the games' pop-up menus (on the
  character roster, a right click on a slot gives NEW / ADD / CANCEL).
- **The keys** are the games' own: Escape for the menus, the games' letter
  shortcuts (such as E for Effects) and so on, as in the manuals. Holding
  **Shift** during the intro of *Wake of the Ravager* skips it, as the game
  itself allows.
- **Speed**: the game runs at the pace of the original's timers (its 18.2 Hz
  clock and the music's 120 Hz timer), not as fast as the computer can.

## Saving and loading

The games save where they always did: `SAVE01.SAV` to `SAVE10.SAV` in the
game folder, with `CHARSAVE.GFF` (the roster of characters). These are the
same files DOSBox writes, so a game saved here loads in DOSBox and the other
way round. Saving in *Shattered Lands* is in its exit menu: Escape opens
"Exit: save game?", SAVE names a slot and writes it, and the game then
exits to DOS, which here closes the program. Load from the title menu's
LOAD SAVED GAME.

Back your saves up now and then. The program is a prototype and an error
past the tested part of the game could leave a half-written file.

## Sound

Music plays through the game's own translated AdLib driver on an emulated
OPL3 chip, and speech and effects through an emulated Sound Blaster, as the
game would with that hardware. *Wake of the Ravager*'s music is CD audio,
played from GOG's OGG files. There are no sound settings: the game's own
`SOUND.CFG` is ignored and AdLib plus Sound Blaster are always chosen (GOG's
Shattered Lands copy selects an MT-32 whose instrument file GOG does not
ship, which is why). MT-32 and General MIDI are not supported.

On Linux, ALSA may print a few configuration errors at start when no sound
device is configured; they are harmless.

## The Obsidian Edition mod

[Obsidian Edition](https://github.com/daaki85/darksun-obsidian-edition) is a
mod for *Shattered Lands*, run through its Loader. It patches the game's
program and adds a resident helper that answers the patched code; the
Loader reads the helper's records to show a dice log and a combat log.

The mod can be built into a program of its own, with the patched game and
the helper translated together (see the README, "The Obsidian Edition
mod"). That build needs the mod's repository, `nasm` (to read where the
helper keeps its routines), and the same tools as the plain build. Its
program is started with the game folder and the mod's `dos` folder:

```
dsun --game "C:\GOG Games\Dark Sun Shattered Lands" --cd <mod>\obsidian-edition\dos
```

The Loader can start that program for you instead of DOSBox, once told where
it is, with its dice log and window attached as usual:

```
dsloader launch --recompiled "C:\path\to\dsun.exe"
dsloader launch --dosbox        (back to DOSBox)
```

That part of the Loader is on the mod repository's `item-reports` branch,
not yet in a release. The mod's combat-log panel on screen is not yet
verified in this build; its dice log is.

## When something goes wrong

- **"No game found"**: the program did not find a `DSUN.EXE` of a known size
  in the folder it was given or beside itself. Give the GOG game folder
  with `--game`. A `DSUN.EXE` of another size (another release, or a
  patched one) is not recognised.
- **"cannot find build/ds1 (the folder with image.bin ...)"**: the memory
  image is missing. On Windows, keep the `build` folder from the zip beside
  `dsun.exe`, or give it with `--build`.
- **The CD's files are missing** (Wake of the Ravager): unpack `game.gog`,
  see [Wake of the Ravager's CD](#wake-of-the-ravagers-cd).
- **The game stops or the screen goes wrong**: start the program with its
  log redirected to a file (see [Starting a game](#starting-a-game)) and
  do what you did again. Lines saying `no function at ...` mean the game
  reached code that has not been translated yet; the addresses are also
  written to `misses.txt` in the build folder, and the next build of the
  program includes them. Report the log, what you were doing, and which
  game, in the project's issue tracker.
- **No sound**: the program uses the system's default sound device through
  SDL. On Linux, `SDL_AUDIODRIVER=pulseaudio` (or `alsa`) can pick a driver
  when the default fails.
- **The pointer does not match the mouse**: the game's pointer follows the
  mouse scaled to the picture; with the window resized to an unusual shape,
  the black bars around the picture are outside the game.

## What is not there yet

- Play past the opening of either game: untested. Expect errors and report
  them.
- A settings file, scaling filters, a CRT look: none. Window or full screen
  is the only choice.
- MT-32 or General MIDI music.
- Party transfer from *Shattered Lands* to *Wake of the Ravager*
  (`CHARTRAN.EXE`).
- The mod's combat-log panel seen on screen in the recompiled build.
