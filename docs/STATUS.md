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

## Next

- Through the first fight, out of the pens; character creation; saving and
  loading.
- Listen to the output on a machine with a sound device; compare timing
  against DOSBox.
- Clean up misses.txt handling (only real entry points should be kept).
- Run the Windows build on a Windows machine (it cross-compiles; untested
  there).

## Wake of the Ravager

Not started.
