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

## Plans recorded so far

- **Sound.** The Miles AIL 2.x drivers (`*.ADV`) are loaded from
  `RESOURCE.GFF` at run time and called through far pointers. Either the
  hardware they drive is emulated (OPL, Sound Blaster DSP, MPU-401) and the
  drivers are translated as separate small binaries, or the AIL driver
  interface is answered natively.
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
