# How it works

## The pipeline

1. **`tools/build_image.py`** builds the guest's memory as DOS would leave it
   at the program's first instruction: the PSP at 0800, the resident image at
   0810 with its 4,853 MZ relocations applied, and **every overlay module
   loaded at once**, from C000 up (52 modules, 247 KB, ending at FDE3). For each
   module it does what Borland's overlay manager (VROOMM) does when it loads
   one: copy the code, apply the module's relocation table (segment-table byte
   offsets replaced by the segments they name), and rewrite each of its entry
   stubs from `INT 3Fh` to `JMP FAR entry:segment`. From then on an overlay
   call is a far call to a stub that jumps into code that never moves, and the
   overlay manager is never entered for it. The format is the one OpenDS
   documents (`docs/overlay-formats.md` there).

   The overlays go above the video memory because DOS never hands that out,
   so they cost the game no conventional memory. That is free because the
   game is given XMS and no EMS (whose page frame would sit there), the
   configuration the Obsidian Edition's launcher already uses.

2. **`tools/find_funcs.py`** finds the functions: recursive descent from the
   entry point, every overlay entry, Borland's `_INIT_` table, every call
   target, every `push bp / mov bp, sp`, and the addresses earlier runs
   reported as misses. Code segments are exact, from the Borland segment table
   in the EXE, so every function knows its CS. Jump tables (Borland's switch)
   are followed.

3. **`tools/lift.py`** translates each function to C with pcrecomp's lift16.
   Each function is decoded against its code segment's base, so instruction
   addresses are IPs and near branches wrap at 64 KB as on the CPU. A far call
   to an overlay stub calls the stub's target directly.

4. **`runtime/`** is the PC the C runs on:
   - `bios.c`: the interrupt vector table, BIOS services, PIC and PIT, port
     I/O, the mouse driver (INT 33h) and an XMS driver (16 MB). Every vector
     starts out pointing at a native handler; when the game installs its own,
     interrupts through that vector run the game's code with a real
     FLAGS/CS/IP frame, and its `call far [old]` reaches the native one.
   - `dos.c`: INT 21h, files in the game folder (case-insensitive), memory as
     real MCB chains.
   - `vga.c`: a VGA at register level: the four planes, write modes, latches,
     Map Mask and CRTC start address that Mode X uses, the DAC, and a 70 Hz
     retrace.
   - `host.c`: SDL2 window, keyboard and mouse, scripted input for headless
     runs; the game runs on its own thread with a 256 MB stack.
   - `dispatch.c`: calls through addresses known only at run time, by linear
     address; misses are written out for the next build.

### Both games in one program

`tools/lift.py` names every function with its game's tag (`ds1_fn_08100`)
and ends `recomp_dispatch.c` with a `GameDesc`: title, EXE name and size,
load segment, entry point, stack, the dispatch table, the drivers
(`lift_drivers.py` writes `drv_table.c` with `ds1_drivers`), and whether
the game has a CD. CMake collects every `build/<tag>/gen` it finds
(`GAME_BUILDS`) and writes `games.c` with the table of them; the runtime
only ever looks at `g_game`. A game folder is recognised by the size of its
`DSUN.EXE`, so `--game` is all a player gives; without it the program
looks for `game/ds1` and `game/ds2` beside itself and asks when both are
there (SDL's message box, which needs no drawing code of our own).

## Things the game does that needed handling

- **The overlay manager** still has its init in Borland's `_INIT_` table and
  two routines the game calls to cache overlays in EMS/XMS; all three are
  answered natively (`NATIVE` in `tools/lift.py`), so the manager never
  installs INT 3Fh.
- **`_setargv`** pops its own return address and later jumps to it. Under
  the lifter that address is the sentinel FFFF every call site pushes, so a
  jump to offset FFFF is a return to the C caller (`runtime/dispatch.c`).
- **Code that jumps into the middle of an instruction** (Borland's start-up)
  gives two overlapping decodings; `lift.py` makes the fall-through of such an
  instruction an explicit jump.
- **The intro waits on the music.** A cutscene advances when the XMIDI
  sequence sends callback value 7Fh, so the music driver has to really run.
  The AIL drivers are translated (`tools/lift_drivers.py`) against a code
  segment that is a variable, and `runtime/aildrv.c` recognises a loaded
  driver by its bytes. The FM chip (`runtime/opl.c`) keeps its own clock, a
  microsecond per port access as on the ISA bus, because the drivers time its
  timers with loops of port reads.

- **Borland's switches** come in three shapes: a dense table bounded by
  `cmp bx, N`; a sparse list of word values followed by the arms; and the same
  with dword values (`mov eax, cs:[bx]` / `add bx, 4` / `add cx, cx` /
  `add bx, cx`), whose arms start 4N bytes into the list. The finder must know
  the shape to find the arms; a wrong shape sends real arms to the dispatcher
  as misses, and a miss seeded as a function is entered as one, with the
  stack of a function it is not.
- **The GPL interpreter's opcode handlers** are reached only through a table
  of near pointers in DGROUP (`NEAR_TABLES` in the finder); most have
  Borland's frameless prologue (`cmp [stack_base], sp / ja / call overflow`),
  which the finder also scans for.

- **`mov bx, imm / call bx`**: Borland's run-time picks helper routines
  that way (the huge-pointer arithmetic in segment 1D69). An immediate loaded
  into a register in a function that calls or jumps through a register is
  seeded as an entry when it decodes as code.
- **DOS files** are raw descriptors, not stdio: the game interleaves reads
  and writes on one handle without seeking, which stdio does not allow.

## The mod (Obsidian Edition)

The mod is three things: a patched `DSUN.EXE` (`DSUNLOG.EXE`: 253 small
changes, most replacing a few bytes of code with an `INT` the helper
answers), the helper `DSCLOG.EXE` (a resident DOS program, source in
`dos/dsclog.asm`, that answers those interrupts, hooks DOS's file opens,
the keyboard and the mouse, and keeps a ring of dice rolls), and the
Python Loader, which prepares the files, starts DOSBox and reads the
ring out of its memory. `tools/build_mod.sh` turns the first two into a
program of their own:

- The Loader's own `prepare_patched_game` writes `DSUNLOG.EXE` and the
  mod's copies of the data files into `<mod>/dos`, exactly as it does
  before starting DOSBox.
- `tools/build_image.py --mod <mod> --tsr <mod>/dos/DSCLOG.EXE` builds the
  image from the patched EXE and loads the helper at `B000` the way DOS's
  `lh` would (PSP, environment, image at PSP+10h); `B000-BFFF` is free in
  mode 13h. The runtime runs the helper's entry first; its `INT 21h AH=31h`
  (stay resident) comes back to the host through a `longjmp`, and the game
  starts. The helper links upper memory in and asks for two blocks "high
  only, best fit": its ring and its combat-log panel. The image lays the
  helper's environment right above its install stack and the overlays
  right above that, and what the overlays leave below the BIOS area (whose
  interrupt stubs and XMS entry sit at the top of `F000`, from `FE00`) is
  the first block the runtime's DOS gives out; the HMA (`FFFF:0000`) is the
  second. The blocks are in the layout (`umb`) and the `GameDesc`; the ring
  fits the first best, the panel takes the HMA.
- The patched code's `INT`s go through the interrupt vector table to the
  helper's lifted handlers like any other. Two things about them need the
  lifter's help. Some sites carry data after the `INT` (a site number the
  handler steps over, or the segment of a far call it replaced), so
  `build_image.py` records those sites from `gamepatch.PATCHES` and the
  decoder lengthens the `INT` by that much. And a handler may send the game
  on elsewhere by changing the return address in the interrupt frame, so
  the frame carries the real `CS:IP` (the lifter sets them before each such
  `INT`), the lifted `iret` pops them back into `cpu->cs:ip`, and the code
  after the `INT` compares: when they differ it jumps there through a
  switch over the function's labels, or dispatches outside it. A handler
  that jumps straight into the middle of the game's code instead (one
  does, after a far call it replaced) finds no function there; inside an
  interrupt handler dispatch takes that as the same thing and only moves
  `CS:IP`.
- `--cd <mod>/dos` makes that folder drive D:, where the helper's DOS hook
  sends the opens of the data files it replaced.
- The helper's `SEG_MOVE`: at the game's first file open it points two
  entries of the game's segment table (a small stack, the monster kinds'
  table) at a block of its own and copies them there, so the new spells'
  records can take the old place; under DOS every overlay loaded after that
  is relocated with the changed table. The overlays here are relocated at
  build time, so `build_image.py` gives those two selectors the helper's
  segments from the start (the copy still happens at run time).
- Where the helper keeps the routines the builder has to know about (the
  three below, and `seg_space`) comes from its source: `build_image.py`
  assembles `dsclog.asm` with nasm and reads the listing
  (`tools/helper_symbols.py`), after checking the assembled bytes equal the
  EXE, so a new helper moves nothing out from under the build; without nasm
  it falls back to a built-in table (helper 2.5.0's offsets).
- Three of the helper's routines are called as `call X / db ARG`: they read
  the byte after the call through their return address and return past it,
  and one recognises its caller by that address. The decoder lengthens
  such calls by the argument (not the one call the recognised caller makes,
  which has none), and every near call in the helper pushes its real return
  address instead of the lifter's sentinel. The helper's lifted `ret` pops
  that address into `cpu->ip`, and the code after the call compares it with
  the one it expects, the way the code after an `INT` does: one routine
  (`text_enter`) pops its return address, saves registers and jumps back
  through it, so the rest of its caller has already run (to the `iret` at
  its end) by the time the C call returns, and must not run again.
- An `INT` standing in for `mov cx, N` (the creation screen's click routine,
  whose handler does the mov itself) hides the size of the Borland switch
  that follows it from the finder, which then lifts the `jmp cs:[bx+table]`
  as a dispatch instead of a switch. The layout carries the bytes every
  mod `INT` replaced (`int_originals`) and the finder reads the `mov cx`
  from there.
- A far return to an address that is not a function's entry goes through
  `recomp_return`: inside an interrupt handler, into the middle of lifted
  game code (below the video memory or in an overlay), it is the helper
  sending the game on, and only CS:IP move; anywhere else it is a miss. The
  resume check follows every one of the mod's INTs, since any handler may
  move the return address. `DS_TRACE_INT=all` prints the registers around
  every user-vector interrupt, which is how a handler that leaves the stack
  off is found.

The helper's ring buffer is what the Loader reads; the runtime plants
DOSBox's BIOS date at `F000:FFF5`, which the Loader's memory search looks
for, so the same Loader can read this program once it accepts its process
name.

## Checking the translation

`tools/difftest.py` runs pcrecomp's `difftest16` over every code segment of
the built image: each distinct instruction is lifted alone, compiled, run on
random registers and memory, and compared with Unicorn's x86 on the eight
registers, the five arithmetic flags and a hash of memory. (`mov r, cs` is
reported because the probe has no code segment; in a real build CS is a
per-function constant.)

## Debugging aids

- `--headless --seconds N --shots DIR` and scripted `--input`.
- `tools/lift.py --spcheck`: every function reports a stack or BP it leaves
  unbalanced.
- `DS_WATCH=<linear>`: every write to an address, with the call chain.
- A miss prints the call chain and the bytes at the address; a timeout prints
  the last functions entered and where the game is.
- `DS_TRACE_XMS`, `DS_TRACE_OPL`; `DS_DUMP=<linear>:<n>` prints memory at each
  miss; `DS_SITES=1` prints the host frames of a miss, for
  `gdb -batch -ex "info line *(fn_XXXXX+0xNN)" build/cmake/dsun`, which names
  the generated line. A lifted function that ends in a dispatch is a tail
  call and does not appear in backtraces: the frame shown is its caller.

## References

- [OpenDS](https://github.com/VirInvictus/opends): the overlay format,
  symbols for both games, the GPL script VM, file formats.
- [Exhume / Underworld Exhumed](https://github.com/abedegno/Exhume) (MIT):
  Borland/VROOMM ports of Ultima Underworld 1 and 2, with AIL 2's drivers in C
  from Miles' public-domain source, Nuked OPL3 and libmt32emu behind them.
  The likely source of the synthesiser side.
- [soloscuro](https://gitea.com/paulofthewest/soloscuro): an engine
  reimplementation of Dark Sun (stalled 2023); formats and scripts.
- [DeSt](https://github.com/NancySadkov/dest) (CC0): SSI's Stronghold, also
  Borland with FBOV overlays; its `mzap` flattens such an EXE for Ghidra.

## Sound

The Miles AIL 2 drivers (`ADV` chunks in `RESOURCE.GFF`) are translated like
the game (`tools/lift_drivers.py`), each against a code segment that is a
variable, and `runtime/aildrv.c` recognises a loaded driver by its first 256
bytes and runs the translated function at the offset called. Below them is
the card:

- `opl.c`: the FM chip's ports (AdLib and Sound Blaster addresses), its two
  timers and status (the drivers time the timers with loops of port reads, so
  the chip's clock advances a microsecond per access), and the SB Pro mixer.
  Every register write is timestamped and handed to `audio.c`.
- `sb.c`: the DSP (reset, version 3.02, speaker, time constant, single-cycle
  and auto-init 8-bit DMA, F2h's interrupt), the 8237's registers, IRQ 5, and
  the DMA stream read from guest memory as the audio clock consumes it.
- `audio.c`: Nuked OPL3 rendered in order of the writes' times, a little
  behind real time, mixed with the DMA stream; out through SDL, or to a WAV
  (`--wav`), and always rendered even without a device, since the DMA clock
  and its interrupts live in that rendering.

- `cd.c`: the CD-ROM's audio side for Wake of the Ravager. MSCDEX's "send
  device request" (INT 2Fh AX=1510h) arrives with a device request block;
  IOCTL reads answer the table of contents (built from the lengths of GOG's
  `MUSIC/TrackNN.ogg`, with the data image as track 1 and the two-second
  Red Book offset), the Q-channel position and the audio status; PLAY,
  STOP and RESUME drive a stb_vorbis decoder whose output `audio.c` mixes in
  at the OPL's rate. HSG sector numbers count from the data, Red Book
  addresses from two seconds before it. `DS_TRACE_CD` prints every request.

`DS_OPL_LOG=file` writes every FM register write with its time, and a replay
through the chip offline tells whether a problem is in the stream or in the
rendering.

## Plans recorded so far

- **Wake of the Ravager** uses the same Borland overlay format and engine;
  `build_image.py` and the finder take its DSUN.EXE as they are. Its CD audio
  becomes playing the OGG tracks GOG ships.
- **Figures.** Where *Wake of the Ravager* has an equivalent of a figure (a
  character's on-map sprite) from *Shattered Lands*, the client should be able
  to draw the *Shattered Lands* figure in its place, per the owner's
  preference. The sequel's figures are larger, so this needs a mapping table
  (sprite id to sprite id) and handling of the size difference; it belongs to
  the resource-loading layer, once both games run.
- **The Obsidian Edition** patches DSUN.EXE in 185 places with `INT nn`
  instructions its DOS helper (DSCLOG) answers. The first route is to
  translate the patched EXE and the helper together; the second is to move
  each patch into a C hook, shared between the two games where their data
  structures agree.
