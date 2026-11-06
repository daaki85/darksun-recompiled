# Making a release

What a release of Dark Sun Recompiled is, and the steps, so that a build becomes something
others can run and report on. Nothing here is automatic yet; the checklist is the release.

## What is shipped

- `darksun-recompiled-windows-x64.zip` (tools/package_windows.sh): `dsun.exe`, `SDL2.dll`, the
  memory images (`build/<game>/image.bin`, one per program built in), the licences of what is
  linked in (SDL2, Nuked OPL3, stb_vorbis, Spleen), `README.md`, `PLAYING.md`, `run.bat`.
- The source, tagged. Linux users build it (README.md, `tools/build_all.sh`).

The images are made from the games' own DSUN.EXE and CHARTRAN.EXE, and carry their code
rearranged: a release ships SSI's code, as a DOSBox save ships it. The licence under which this
project's own files go out, and whether the images may be shipped at all or must be built by
each player from a GOG copy, is the owner's decision and is not made here.

## Before tagging

1. `python3 tests/run.py` passes alone (not beside a compile: the cases are timed).
2. The mod's build is lifted from the mod release the zip is meant for (`tools/build_mod.sh`,
   `tools/converge_mod.sh`, `tools/entries.sh save build/ds1o`, the lists committed).
3. The Windows zip rebuilt after the last change (`tools/package_windows.sh`), and run once under
   Wine (the window, the pointer at three sizes, a game started).
4. docs/STATUS.md says what was played through on this build, and what was not.
5. CHANGELOG.md has the release's section.

## Tagging

```sh
git tag -a vX.Y -m "Dark Sun Recompiled X.Y"
git push origin vX.Y
```

Then a GitHub release on the tag, with the zip attached and the changelog section as its text.

## Numbering

`0.Y` while the games are not played through on it; `1.0` when both games have been finished
on the program by someone other than its scripts.
