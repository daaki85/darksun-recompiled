# Plan of action

The order: make Shattered Lands fully playable, prove it plays exactly like the
original, sound, something players can install, the Obsidian Edition, Wake of
the Ravager, both games in one program. Each phase ends with a test it must
pass. STATUS.md says where the work stands.

## Phase 0: Prototype (done)

Overlays loaded at build time, function finder, translator driver, emulated PC
(DOS, BIOS, VGA, timer, mouse, XMS); the Miles sound drivers translated too;
the intro plays (SSI logo, AD&D screen).

## Phase 1: Shattered Lands playable

- Past the intro to the title menu, character creation, loading a save, the
  slave pens and arena in Draj.
- Close the gaps in the found code: misses are logged; only real entry points
  among them are kept.
- Routines that need special treatment, as they turn up.
- Keyboard, the mouse cursor, palette fades, saving.
- Scripted runs (keys and clicks on a timeline) for each step, kept as
  regression tests (`tests/`).
- **Done when:** a scripted run creates a party, walks out of the pens, fights
  the first arena battle, saves and reloads.

## Phase 2: Prove it is faithful

- pcrecomp's difference tester over the translated instructions (every flag and
  register against a CPU emulator), with attention to the 32-bit forms.
- A whole playthrough with the stack audit (`--spcheck`) reporting nothing.
- The same scripted inputs on the original in DOSBox and here; screens and game
  memory compared at checkpoints. The Obsidian Edition's dice log is the
  strongest check: the random-roll sequences must be identical.
- Every region in a checklist.
- **Done when:** a whole-game playthrough matches DOSBox and nothing unexplained
  is logged.

## Phase 3: Sound

- FM music: the register writes the translated music driver already makes go to
  an OPL3 emulator (Nuked OPL3; Exhume's MIT audio layer is the model), timed
  by the game's 120 Hz sound timer.
- Digital sound: the Sound Blaster DSP, DMA and IRQ 5, so the translated
  digital driver runs for real.
- Optional: MT-32 (the player's own ROMs, Munt) and General MIDI.
- **Done when:** music and effects play in sync, and the intro is timed by real
  playback.

## Phase 4: Something players can install

- Windows build (MinGW cross-compile) and Linux build.
- 4:3 integer scaling, fullscreen, optional CRT filter, a settings file, save
  folder handling.
- Distribution per the owner's decision (prebuilt programs containing translated
  code, or a builder that translates the player's own GOG files), plus CI.
- **Done when:** a player with the GOG game is running it on Windows in a few
  clicks.

## Phase 5: The Obsidian Edition

- Route A (fastest, the mod unchanged): apply its patches to DSUN.EXE before
  the build. They are byte replacements at file offsets (`Patch(name, offset,
  original, replacement)` in `gamepatch.py`, applied by `patched()`), so
  `build_image.py` takes the patched file as it is, overlays included; the
  `INT nn` instructions they plant go through the runtime's vector table to
  whatever handles them. DSCLOG.EXE (the helper, a DOS program) is translated
  as a second image, loaded above the game as DOS would, and its install code
  run first, so its hooks are in the vector table when the game starts. The
  memory pressure that shaped the helper goes away, since the overlays no
  longer use conventional memory.
- The Loader: replace DOSBox memory scanning (`process.py`, `guestmem.py`)
  with direct access to the runtime's memory; the window stays.
- Route B (later): each patch becomes a C hook.
- **Done when:** the mod's test suite passes and its dice log matches a DOSBox
  run of the mod.

## Phase 6: Wake of the Ravager

- `build_image.py` and the finder take its DSUN.EXE as they are; the native
  stand-ins for its overlay manager use OpenDS's addresses.
- The CD: the files in `game.gog` through an emulated MSCDEX; the 40 CD audio
  tracks from GOG's OGG files.
- Voice and effects through the Phase 3 Sound Blaster.
- Functions matched between the two games to carry names and fixes across.
- **Done when:** Phase 1 and 2's tests pass for Wake of the Ravager.

## Phase 7: One client

- One program and launcher with both games, one runtime.
- Party transfer (`CHARTRAN.EXE`, translated or reimplemented), including the
  mod's additions. (Translated: built in as `ct`, started with
  `--transfer`; the mod's additions are not covered.)
- The mod's rules shared, an address table per game.

## Phase 8: Shattered Lands figures in Wake of the Ravager

A resource-override layer between the game and its GFF files, a table mapping
each sequel figure to its Shattered Lands equivalent, and handling of the size
difference (the sequel's figures are larger).

## Phase 9: Optional improvements

Higher frame rates where the engine allows, upscaled art, quality-of-life
features through the C hooks.

## Risks

- Subtle translation bugs across ~180,000 instructions (Phase 2).
- Timing-dependent code (waits on the music, loops that count port reads).
- DSCLOG relies on exact real-mode behaviour (the stack frames it rewrites
  around the overlay manager); some of it becomes unnecessary and needs
  adjusting.
- Distribution law: the owner's decision.
