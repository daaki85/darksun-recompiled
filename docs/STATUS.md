# Status

## Shattered Lands (GOG 1.10, DSUN.EXE 611,408 bytes)

**The game is in play.** The intro (SSI logo, AD&D screen, title card,
cinematic, scroll; Esc skips it), the main menu, START GAME, the decree and
the gladiators' cinematic, the first scene in the arena of Draj with its
dialogue, the scripted fight of Celgor the defiler against the rampager (the
combat view, turn by turn), and the party at the gate waiting to be moved: all
with no misses and no stack faults.

Clicking on the sand walks the party into the arena, the map scrolling with
it. CREATE CHARACTERS opens the roster (VIEW CHARACTER).

![The scripted fight](img/arena-fight.png)
![Walking into the arena](img/arena-walk.png)

![The arena's opening scene](img/arena-opening.png)
![The main menu](img/main-menu.png)

- Image: 52 overlay modules loaded, 935 stubs patched; Borland's overlay
  manager is kept from starting (its three entry points are native no-ops).
- Functions: ~2,370 found, ~178,000 instructions, 134 jump tables; all lift
  with no unhandled instructions.
- Start-up: Borland's run-time, SSI's VMEM on XMS, the GFF files, the save
  copy (DARKSAVE.GFF to DARKRUN.GFF), mode 13h, the keyboard and mouse hooks.
- Sound: the 16 Miles AIL 2 drivers in RESOURCE.GFF are translated too and run
  where the game loads them. Music: the Sound Blaster Pro FM driver runs
  against an emulated FM chip at its 120 Hz, and its register writes go to
  Nuked OPL3 and out through SDL (or to a file with `--wav`); the note log
  shows a drum intro and then the theme's melody and bass (not yet checked by
  ear). Digital sound: the Sound Blaster Pro digital driver runs against an
  emulated DSP, DMA channel 1 and IRQ 5, and streams the game's 8 kHz speech
  and effects into the mix.
- The runtime supplies its own SOUND.CFG (GOG's selects an MT-32, whose
  instrument file GOG does not ship).

## Checks

- `tools/difftest.py` over all 128 code segments: 28,894 distinct
  instructions, each lifted alone and run against Unicorn's x86 on two
  random register sets. One real disagreement (`imul r32, imm` with a
  sign-extended immediate), fixed by `patches/pcrecomp/0001`; the rest are
  the `mov r, cs` probe artefact.
- Four scripted regression tests (`tests/run.py`): intro, menu, start, walk.

## Next

- Through the first fight, out of the pens; character creation; saving and
  loading.
- Listen to the output on a machine with a sound device; compare timing
  against DOSBox.
- Clean up misses.txt handling (only real entry points should be kept).
- Run the Windows build on a Windows machine (it cross-compiles; untested
  there).
- Wake of the Ravager: further into Tyr; CD volume through the mixer.

## Wake of the Ravager (GOG 1.1, DSUN.EXE 634,416 bytes)

The same pipeline, pointed at `game/ds2` with `--args "-W0 -L"` and the CD
folder from `tools/cd_extract.py` on `D:`. 49 overlay modules, ~2,540
functions, 16 Miles drivers. It plays: SSI logo, title, the opening
cinematic from `1.FLI`, the main menu, START GAME, the narrated cinematic,
and the first scene in Tyr with its opening conversation, the speech
streaming through the Sound Blaster. Holding Shift skips the intro (the
game polls the BIOS shift state), so the menu is reachable in 8 seconds.
Its music is CD audio: `runtime/cd.c` answers MSCDEX's device requests
(table of contents from the lengths of GOG's `MUSIC/TrackNN.ogg`, PLAY,
STOP, RESUME, Q-channel position) and decodes the track being played
with stb_vorbis into the mix. A recording of the title screen matches
the decoded track 37 sample for sample (correlation 0.99).

![title](img/wotr-title.png) ![intro](img/wotr-intro.png)
![menu](img/wotr-menu.png) ![Tyr](img/wotr-tyr.png)

What it needed beyond Shattered Lands:

- Its `int86x` builds its interrupt stub on the stack in more shapes
  (`push bp / int / pop bp / retf`, `mov bp,[bp+d8] / int / retf n`);
  dispatch recognises all of them and no longer records stack addresses
  as missing functions.
- Its timer and keyboard handlers (installed through registers, not
  immediates) and a few pointer-called helpers were only found by the
  run-time miss list; four converge rounds in all.
- The BIOS keyboard handler keeps the shift state at 0040:0017.
- Its own `_INIT_` table, GPL handler table (DGROUP:30A) and overlay
  manager addresses in `tools/find_funcs.py` and `tools/lift.py`.

Two regression cases: `wotr-intro` (logo, title, cinematic, menu) and
`wotr-start` (Shift, START GAME, Tyr).

Not yet: play beyond the first conversation; the save-game folder (it writes `darkrun.gff` and reads
`CHARSAVE.GFF` in the game folder, as DOS did).
