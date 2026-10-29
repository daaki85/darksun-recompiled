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
  the `mov r, cs` probe artefact. The same over Wake of the Ravager's 127
  segments: nothing but that artefact (a stray `lar` decoded from data in
  two segments needed a stub in the harness to let them build).
- The stack audit (`tools/lift.py --spcheck`, built into its own program:
  `DSUN=build/cmake-sp/dsun python3 tests/run.py`) over the Shattered
  Lands cases: intro, menu, start and the load report nothing. The fight,
  the walk and the save report one family of entries: forty points inside
  the map blitter at `1CAE` that data points at, which the finder made
  entries of, so a jump to one from the routine around it is lifted as a
  tail call; each ends in that routine's epilogue and so leaves the stack
  as the routine would, which the audit sees as the callee moving SP. The
  same for `17B4E` on the creation screen. The idiom is sound (the caller
  returns right after the tail call, which is where it was going), not a
  translation fault.
- The dice against DOSBox: the same scripted arena fight in DOSBox 0.74
  (the mod loaded, the Loader attached, driven by xdotool under Xvfb) and
  in this program with `DS_CLOCK` pinned to the second DOSBox started: the
  same saving throws (7, 5, 7, 10), the same damage, the same deaths, roll
  for roll. The game seeds its dice from the time of day once, at the main
  menu; the runs differ when the clocks do. `tools/dosbox_compare.sh` runs
  it. The Loader's log from this build lacks the lines it works out from
  the address `rand()` was called from (the lifter pushes a sentinel return
  address): see docs/DESIGN.md, "The mod".
- The stack audit over Wake of the Ravager's two cases: the sequel's
  Borland run-time at the same addresses as Shattered Lands' (the
  struct-by-value push, the start-up's argv builders) is the only thing it
  reports, and is on the audit's known-good list for both games.
- The character transfer against DOSBox: the same Shattered Lands save
  (the arena party of four, `tests/ref/arena.sav`) carried into the
  sequel's roster by the translated CHARTRAN.EXE and by the original under
  DOSBox 0.74 gives the same `CHARSAVE.GFF`, byte for byte, and the same
  exit code (211, the utility's own).
- Ten scripted regression tests (`tests/run.py`): intro, menu, start, walk,
  create (a character rolled on CREATE CHARACTERS, kept, and the game started
  with it),
  save1-write and save2-load (Esc at the arena opens "Exit: save game?";
  the save is named and written, the game exits to DOS; the next run
  loads it from the title menu and is back at the arena), the two
  Wake of the Ravager cases, and transfer (the utility carries the arena
  party into the sequel's roster, its three screens checked against
  references).

## Next

- Out of the pens: the way out is story (the pens' tasks after the arena),
  not a walk; a scripted route or a save from later in the game is needed
  to exercise it. Seven minutes of wandering the arena, with the Effects
  and inventory screens and the figure's menu opened, found no misses.
- Listen to the output on a machine with a sound device; compare timing
  against DOSBox.
- Clean up misses.txt handling (only real entry points should be kept).
- Windows: the build runs on the owner's machine now (both games found
  where GOG Galaxy put them, the mod's folder found beside the program).
  Its first runs found three faults no Linux run could: files opened in
  text mode (a GFF read stopped at a Ctrl-Z), `tmpfile()` wanting the
  drive's root (the runtime's SOUND.CFG stand-in failed and the game
  looked for an MT-32), and the mouse scaled twice (SDL's renderer
  already rewrites mouse events into its logical size). All three fixed;
  the mouse fix awaits the owner's confirmation. Sound through a real
  device is still unheard; the audio callback path, run here through
  SDL's disk driver, gives continuous music.
- Wake of the Ravager: further into Tyr; CD volume through the mixer.

Character creation turned up a mouse-driver bug: INT 33h functions 5 and 6
(button press and release information) answered with the button state
where the function number was tested, so the roster's pop-up menu (a
right click on a slot: NEW / ADD / CANCEL) never saw a click. They now
answer with the count and the position of the last press or release, as
the driver does. The input script gained `rclick=` and `rdrag=`.

## One program

Both games are built into the one `dsun`: every generated symbol carries
its game's tag (`ds1_fn_...`, `ds2_drv01_...`), each game is described by
a `GameDesc` (entry point, dispatch table, drivers, whether it has a CD) and
CMake writes the table of the games it found lifts for. The program
recognises a game folder by the size of its `DSUN.EXE`, finds `game/ds1`
and `game/ds2` on its own, and asks with a message box when both are
there. The Windows zip now carries both memory images.

**The character transfer** (Phase 7's party transfer) is the third program
built in: SSI's `CHARTRAN.EXE` from Wake of the Ravager's folder,
unpacked from LZEXE (`tools/unlzexe.py`), translated like the games (303
functions; plain program, no overlays) and started with `--transfer`, or
from the message box when both games are found. It runs in text mode,
which the runtime now draws (80x25 from B800:0000, Spleen's 8x16 font,
the BIOS cursor), with the BIOS character services and DOS console input
and output answered, and both game folders mounted as the `C:\DSUN` and
`C:\RAVAGER` it expects. The arena party goes into the sequel's roster
with the same bytes DOSBox produces (Checks above). What it does not
cover: a party with the Obsidian Edition's own items (the utility is the
original's).

## Shattered Lands with the Obsidian Edition mod

`tools/build_mod.sh` builds the mod's patched game (`DSUNLOG.EXE`) and its
resident helper (`DSCLOG.EXE`) into `build/ds1o`, an entry of the one
`dsun` beside the plain game (tag `ds1o`), run with `--mod
<mod>/obsidian-edition`, or chosen from the box of buttons when the
program finds the mod's folder in or beside its own (docs/DESIGN.md, "The
mod"). The helper loads
and stays resident, hooks DOS, the keyboard and the mouse, and answers the
patched game's interrupts; the game boots with the mod's data files
through its DOS hook, plays its intro, shows the menu, and START GAME
reaches the arena, where the scripted fight plays out and the party walks
in afterwards (the plain build's `walk` script). The converge loop finds
no missing functions over that 150-second run.

What it took is in the design notes: the frames of the mod's interrupts
carry the real return address and the code after each interrupt follows
where the handler sent the game; the helper's segment-table move is done
to the overlays at build time; its argument-byte calls and its stack-built
far jumps and returns back into the game are recognised; its near calls
check where the callee came back to, as one routine pops its return
address and jumps back through it later. Most of the time went on six ways
the frame's or a return address could be off, each of which sent the game
into the wrong code with a stack that no longer matched.

The mod's Loader reads this program: with the change made for it (the
mod repository's pull request 78, merged into its main branch after
2.12.3) it
finds the memory by the mark at F000:FFC0, attaches to the helper's ring,
and its dice log prints what the helper records: attached to a headless
run during the arena fight (`python3 -m dsloader dicelog --pid $(pgrep -x
dsun)`), it printed the announcer's lines, the party's kit lines, and the
fight's saving throws, damage and hit points as they happened.

The creation screen works in this build too (the mod's STORE and RECALL
probe stands in for the `mov cx` that sizes the click routine's switch; the
finder now reads it from the bytes the INT replaced). The walk and the
creation scripts run with no misses.

The mod's releases 2.6.0, 2.12.1 and 2.12.2 (84, 189 and then more commits past the
version first built here) build and run the same way: `tools/helper_symbols.py`
reads where each helper keeps the routines the builder must know about from
its source, so the moved code needs no table change. 2.12.1 keeps its big
buffers in the HMA through XMS, which the runtime now grants, and intercepts
the C library's heap calls; its 33 KB overlay-buffer reserve is refused
here, as there is no room for it above the overlays, and the helper falls
back to the game's heap as before (the runtime's DOS gives the game 608 KB,
more than DOSBox does, so nothing is lost). Its scene-player check turned
up a runtime fault: a loop closed through an interrupt whose handler keeps
interrupts off never let the timer through, and the screen stayed black;
pending interrupts are now delivered as soon as a handler's iret has them
on again. The 2.12.1 Loader attaches to the running program and reads the
whole fight, with the same dice as DOSBox rolls for the same clock. The
finder now follows the jumps the mod's INTs stand in for (`or ax,ax / jnz`
sites), whose targets its handlers reach by moving the return address.

The helper gets both its upper memory blocks (the ring below the BIOS area,
the panel in the HMA), so the combat-log panel can be drawn once the Loader
asks for it.

The Loader starts this program instead of DOSBox when it finds it, unzipped
into or beside the mod's folder, or once told where it is (`dsloader
launch --recompiled <path to dsun>`; both in the mod's main branch
since pull request 78): `launch`, `play` and the window's "Start the game"
run it with the game's folder and the mod's `dos` folder, and attach as
they do to DOSBox. The program expects its memory image at `build/ds1o`
beside itself, as the zip lays it out. The program started on its own
picks the mod's build when its `--cd` folder holds `DSUNLOG.EXE` (the
Loader's command line), with `--mod`, or from the choice box.

Seen working through the Loader's own window, started by `dsloader launch`
with the program (under a virtual display, driven by xdotool): the Loader
attaches to the program's memory, its party panel shows the characters,
its dice log fills with the arena fight's rolls, and L on the map opens
the mod's combat log in the game, drawn by the helper, and L again hides
it. That session also caught a mouse fault: a click whose press and
release fell between two polls of the mouse driver was lost; button
changes are queued now.

Every feature of the Loader, tried against the program the same way
(the change for it, then on 2.12.1): its unit tests, 1,272 of them, pass
under both Pythons here (the helper's emulated tests under the one with
Unicorn, the window's under a display); two that read the machine's own
settings are pinned to their own now. In the window: Characters, All
fields, Spells, Dialogue (the Announcer's lines captured from the game),
Dice log with details and text size, Memory tools (locate by name, record
bytes), Options, Freeze report (a zip with the memory image and the
report, in crash-logs), Reconnect. On the command line against the live
process: processes, find-text, dump, search and next (a value search
narrowed twice), dicelog; and save (a save file's party) and checks
(the scripts' skill checks) on their own. In the game: the combat log
on L. When the game is killed under the Loader it writes its crash
report, as it would for DOSBox closed from outside.

**A fault found by the feature tests, now fixed:** the helper is loaded at
B000 and, at 50-60 KB, spans B8000, the colour text screen, which the
text-mode support (the transfer utility's) cleared at start-up: that wiped
the helper's table of the data files it swaps for the mod's copies, so
every mod run before 29 October ran on the game's own GPLDATA, SEGOBJEX
and RESOURCE files, without the mod's icons, scripts, new people and
items, and the Loader never dressed the party's figures. With a resident
helper the text screen is now a buffer of the runtime's own. After the
fix the helper opens its copies (the log shows `D:\SEGOBJEX.GFF`), the
party's figures carry their gear (Gerakis's long sword at the belt, the
gythka over the shoulder, on the map, in fights and in the screens'
portraits), and the mod's game still converges clean on the arena
script. What was verified before the fix (the window, the dice log, the
combat log, the screens' numbers) did not depend on the copies.

The mod's features in the game itself, through the Loader, at the arena:
the names over the figures (Fireball and Fear float over their casters in
the scripted fight, with the mod's monster boxes), View Character with
the five saves, MOVE and THAC0, the inventory screen with THAC0, the
saves, REAC, DEF and each weapon's THAC0 (the Loader's numbers; the
game's own come back without it, as the mod says), the USE screen's
SPELLS LEFT line on the preserver's list and none on the psionic lists,
and the Effects screen's kit and weapon-spec lines (WILD FIGHTING,
SPECIALIZED IN LONG SWORD, GYTHKA; KIT: ARCANIST), and, after the fix
above, what the party wears drawn on their figures. Not reachable at the
arena, so not tried: the Look box (the party's first fight is later), a
charged item's box and a scroll (the party has none yet), the manual
check (the sewers), and the rule changes that show only in play.

The creation screen's features, through the Loader (29 October): the
screen opens from the roster's NEW with the mod's SUM line; the die
rerolls, one roll a click, and the dice log shows each score as "best of
four 4d4 (...) +4", the prime requisite raised, the six scores' sum and
the hit points and PSP; STORE keeps a roll and RECALL brings it back
after a reroll (the log shows the scores going back, the HP and PSP
with them); KITS opens the class's kit page (NO KIT, MYRMIDON, SENTINEL,
RAVAGER for a fighter); DONE opens the mod's PICK A WEAPON SPECIALTY
window, and the character made starts with the fuller gear (the log:
"starts with more gear: Sling"), which the Loader's Characters tab lists
with THAC0 by weapon, saves, move, attacks and the gear worn. The
class list works as in DOSBox: a human's one class is clicked off before
another is clicked on (checked against DOSBox 0.74 with the same clicks).

**A second fault found by these tests, now fixed:** RECALL ended the
program with "Stack overflow!". The helper restores the stored roll and
then jumps far into the middle of the die routine, with a frame it built
itself, to have the game show the hit points, PSP, AC and damage as
after a roll. A lifted function could only be entered at its start, so
the jump was left for the resume block of the click routine, which could
not continue there either, and the game went on with the helper's frame
still on the stack. Now a resume block that cannot continue notes the
address (`inside.txt` beside `misses.txt`, with the lifted functions on
the way there), and the lifter gives such an address an entry of its own
(`recomp_enter_ip`, a switch at the top of the function's body); an
address a caller on the way owns is left to that caller's resume block.

In play, after the arena: the party walks out spread (the mod's whole
party in view, four figures), the figures dressed and with shadows;
the save window has the Loader's PAGE 1 to PAGE 4 buttons, PgDn and
PgUp turn its pages and the page shown is greyed; the inventory shows
each member's weapons with the mod's lines (the thri-kreen's chatkcha
with its three damage lines); the Effects screen shows the kit and
weapon-spec lines. Still untried: a fight the player controls (Tab,
Enter and the ring; the Look box on a monster), talking to the new
people (Kalzith), a shop, a charged item, a scroll, thief skills in play.

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
