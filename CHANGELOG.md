# Changelog

What changed, newest first. The dates are the commits'.

## Unreleased (October to November 2026)

**The program**
- Shattered Lands, Wake of the Ravager and the character transfer utility run as one native
  program on Linux and Windows: the games' code lifted to C (pcrecomp's lifter, with this
  project's finder, overlay handling and runtime), SDL2 for the window, sound through an OPL3
  emulation and the games' own AIL drivers, Wake's CD from its GOG image.
- Saves identical to DOSBox's; the transfer utility's CHARSAVE.GFF byte for byte DOSBox's.
- A choice box at start when more than one program can run; the games found where GOG put them;
  `dsun.ini` remembers the folders, the mod's folder, the window's size and full screen
  (`window=`, `fullscreen=`, `scale=`).
- The Obsidian Edition mod built in (`build/ds1o`): the mod's patched game and its resident
  helper lifted together; its Loader starts the program and reads it; its dice match DOSBox's.
- The mouse: SDL's logical coordinates, a queue with a 60 ms hold for the games' polling, the
  middle button for the mod's map drag; keys; F11 for full screen.
- A text error screen that waits for a key; `dsun.log` beside the program; a crash handler that
  writes the call chain and the addresses for the next build.

**Faults found and fixed along the way** (docs/STATUS.md has each)
- Interrupts and the mouse polled on time in loops the lifter's tick points miss.
- The mod's helper spans the text screen; the text-mode support no longer clears it.
- The helper's jumps into the middle of a routine (RECALL) enter it there; the call sites it
  reads return addresses from push real ones (the party in view after a fight).
- Windows: files opened in binary mode, a temp file where tmpfile() fails, the mouse not scaled
  twice.

**Tooling**
- `tools/build_all.sh`, `tools/entries.sh` (the converged entry lists kept per build and per
  helper release), `tools/converge_mod.sh`, `tools/package_windows.sh`, a regression suite
  (`tests/run.py`, twelve cases, the mod's included) and a GitHub workflow for it.
