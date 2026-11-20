# Shattered Lands figures in Wake of the Ravager

What it takes for *Wake of the Ravager* to draw *Shattered Lands*' figures (the on-map sprites of
the party and the people and creatures they meet): Phase 8 of [PLAN.md](PLAN.md). Examined
2026-11-18 from the GOG installs of both games (version 1.1 of each). `tools/sl_figures.py`
re-checks every finding below from the owner's own installs:

    python3 tools/sl_figures.py report SL_DIR WR_DIR          # the checks, printed
    python3 tools/sl_figures.py sheet  SL_DIR WR_DIR OUT.png  # the party: SL's, SL's in WR's colours, WR's
    python3 tools/sl_figures.py build  SL_DIR WR_DIR OUT.GFF  # WR's OBJEX.GFF with SL's party figures

`build` was played in the game on 2026-11-20 ([seen in the game](#seen-in-the-game)). The tool
holds no data from either game. Its pictures are made on the owner's machine and stay out of git.

## In short

The engine draws a figure the same way in both games. The objects, the frame format, the
animation scripts and their 36 slots all match, and so does the map grid (16×16 tiles, 112×112).
That leaves four differences, all in the data, each one mechanical to convert:

| | Shattered Lands (`SEGOBJEX.GFF`) | Wake of the Ravager (`OBJEX.GFF`) |
|---|---|---|
| walking picture | `BMP n` (OJFF +0Ch) | `BMP n` (OJFF +0Ch) |
| combat picture | `BMP n+1` | `CBMP n` (same number) |
| animation script | `SCMD` named by OJFF +0Eh (256 scripts, shared: the whole party uses 174) | `SCMD n`, one per picture |
| empty script slot | 0 | FFFFh |
| colours | GPLDATA's palette | the region's palette (each `RGNxxx.GFF` holds one) |

So a sequel figure can be swapped by changing three chunks: `BMP n` gets SL's walking picture,
`CBMP n` its combat picture and `SCMD n` its script. Colours are remapped and the script's empty
slots rewritten. The sequel's object records (`OJFF`), creature records (`RDFF`) and code stay
as they are. That works as a data patch in DOSBox (a copy of `OBJEX.GFF`, as the Obsidian Edition's
Loader does for Shattered Lands' `SEGOBJEX.GFF`), or in the recompiled client as an override of the
chunk read.

## The findings

**Objects.** Both games have 16-byte `OJFF` records with the walking picture's number at +0Ch.
SL keeps its script's number at +0Eh. WR leaves +0Eh-0Fh zero and lays +6 to +0Bh out differently.
The party is objects 300-313 in both, in the same order: 300 + the figure picked at creation.
That is human, dwarf, elf, half-elf, half-giant and halfling (man, then woman), then the mul and
the thri-kreen. `CHARTRAN.EXE` carries the figure number across, so the party maps one to one.

**Frames.** SL draws every frame in one run-length format (u16 width and height, then rows of
spans; `art.decode_frame` in the Obsidian Edition reads it). WR reads that format and two
packed-bit ones of its own: `PLNR`, which the Obsidian Edition decodes for WR's spell icons, and
`PLAN`. All 1,631 of WR's `CBMP` frames, and its party's walking frames, are in SL's format, so SL's
pictures need no re-encoding. 99 of WR's run-length pictures are SL's, unchanged in shape.

**Which picture a frame comes from.** WR's picture loader (DSUN.EXE file offset 2A568h) takes a
flag that picks the chunk type, `CBMP` or `BMP `. It caches either in the same table of 300 slots
that SL has (300 at 2A5E7h, slot +0Eh bit 4 for a `CBMP`). An animation step's flag 20h means
"a frame of the combat picture". In WR all 2,006 such steps name a frame inside `CBMP n` and the
other 6,584 one inside `BMP n`, with 6 out of range. In SL, 20h steps name frames of `BMP n+1`.

**Scripts.** An `SCMD` is 36 u16 slots, each the first step of one animation, followed by 8-byte
steps: frame, a byte (timing or sound: WR uses 5 at an attack's blow), flags (02h standing, 04h
mirrored, 20h combat picture), signed dx and dy, two bytes of the frame's anchor, then 0. The
slots mean the same in both games: 0 stands facing away (frame 1), 8 stands side-on (frame 2),
16 faces front (frame 0), 24 is side-on mirrored, 32 dies. A walk cycle moves 16 pixels, one tile,
in both (SL 4+4+4+4, WR 4+3+1+4+3+1). SL's script uses SL's frame numbers and anchors, so it goes
over together with SL's pictures, and the two stay consistent.

**Colours.** SL's figures use palette numbers whose colours in WR's palettes are unrelated (no
index within 6 RGB levels). They need remapping. WR's 20 region palettes come in 16 versions, and
135 of WR's colours stay within 40 RGB levels across all of them, leaving out 0-15 and 240-248 (the
cycled and system colours). SL's party colours mapped to the nearest of those come out at a mean
distance of 17 (0-441); the worst are the purples and deep blues of some clothing, at 77. Side by
side, the remapped party can't be told from SL's own (`sheet`).

**Size.** WR's figures are larger. The party's middle frame height is 1.2 to 1.5 times SL's: a
human 27 pixels in SL against 35 in WR, a half-giant 39 against 53. On the same 16-pixel grid, an
SL figure would stand a fifth to a third shorter than the sequel's figures around it. The choices:
- Draw them at their own size (simplest, and true to SL's look).
- Scale them up about 1.3× (blurry at this resolution, so it needs a hand-made or upscaled set).
- In the client, scale the drawn figure, not the data.

**Picture store.** WR keeps SL's limit of 300 picture slots in a fixed store. SL's figures are
smaller than WR's (the party's 28 picture chunks are 187 KB against WR's 246 KB), so a swap uses
less store.

## Beyond the party: a mapping table

The party maps by number. Every other figure needs a table from WR picture number to SL picture
number (plus SL's script), made by hand:

- **By name.** 19 creature names appear in both games' `RDFF`s: the four elementals, defiler, dust
  devil, gladiator, guard, templar, slave, prisoner, villager, warrior, zombie, shadow, psurlon,
  caravan master, Notaku and Nnamdi. These are the first candidates.
- **Already shared.** Of WR's 486 animated pictures, 64 have an SL picture's exact frame-0 shape.
  They need no entry, or only a colour fix.
- **No equivalent.** Sequel-only creatures (the Ravager's own, and most of WR's people) keep WR's figure.

A table entry needs only the two picture numbers: SL's script comes from the SL object that uses
that picture (+0Eh).

## Two ways to deliver it

1. **A data patch, in DOSBox, today.** `sl_figures.py build` writes WR's `OBJEX.GFF` with the
   party's three chunks per figure appended and the file's index pointed at them (the game reads a
   chunk's place and length there, as SL does). The mapping table would extend it to other
   figures. In the Obsidian Edition's Loader, this would sit beside `wotrart.py`, the same art
   carried the other way.
2. **The recompiled client (Phase 8 as planned).** It would override WR's chunk read (the loader's
   call at 2A61Eh, `28FF:05B5`, by type and id). When the owner's preference is on and the table has
   an entry, it would serve SL's converted chunk. The same conversions (remap, script slots) run
   once at start-up or are cached. It can also scale the figure as it draws (the size question).

## Seen in the game

2026-11-20, in DOSBox (the Obsidian Edition's playtest kit: `ravstart.sh`, its test log
`playtest/logs/2026-11-20-ravager-sl-figures.md`). The sequel loaded the `build` copy of
`OBJEX.GFF` and drew the opening party in Tyr as Shattered Lands' figures: the elf woman, the human
man, the thri-kreen and the half-giant. In the Draxans' ambush they stood, walked (SL's stride
frames, facing the way they went), swung (SL's side attack: wind-up, lunge, recovery), took hits
and fell (SL's dead frames), all on one ground line. Ravager's program needed no change.

- **Anchors:** right. SL's script places SL's frames correctly in the sequel.
- **Shadows:** neither game drew one for these figures here; nothing to carry.
- **Size:** SL's figures are a fifth to a third shorter than the sequel's Draxans beside them,
  as the data said. Decided (2026-11-20): they keep their own size.

## The interface (phase 1)

`sl_figures.py build-ui SL_DIR WR_DIR OUT.GFF` writes WR's `RESOURCE.GFF` with Shattered Lands'
interface pictures and icons. Seen in the game 2026-11-20 (the same test log).

- **Pictures:** 45 `BMP` chunks that are the same drawing at the same size and frame count
  (`UI_PICTURES`, checked by eye). WR's are SL's art re-encoded in fewer colours. Left out:
  11000 and 20029 (SL's are cut away on one side: the screens are laid out otherwise), 13005 (a
  second frame in WR), 20125 and 20126-20134 (other pictures), 12000 and 20000-20013 (other sizes:
  WR's portrait frame and creation figures are larger).
- **Icons:** matched by look, not number, since WR renumbered part of its spell list. Each WR icon
  takes the SL icon of the same size whose pixels are nearest, within a mean RGB distance of 36.5
  (set by eye: 36.2 the same drawing, 36.7 another symbol). 221 icons, 130 of them from another
  number. The MORE and scroll buttons (12100-12102) stay WR's: they sit on WR's own talk boxes,
  and SL's dimmed frame showed there as a lavender ghost.
- **Colours:** SL's interface palette (`RESOURCE.GFF` PAL 1000) into the 92 WR colours that are
  the same in WR's PAL 1000 and in every region's palette, since the interface is drawn over the
  map in the region's palette. Mean distance 16 (0-441).
- **WR's other two frame formats:** `PLNR` (packed codes with run escapes) and `PLAN`, which is
  `PLNR` without the escapes: u16 width and height, FFh, `PLAN`, u8 bits a pixel, a colour map of
  2^bits palette numbers, then one code a pixel, highest bits first. 0 bits means every pixel is
  map entry 0. `decode_any` reads all three. WR draws SL's run-length frames among its own.
- **In play:** the USE screen, the END menu, the status box and the inventory draw SL's art in
  place. The change is subtle: smoother and a little bluer than WR's. Where SL's pieces meet WR's
  own (its talk boxes), SL's bluer stone shows against WR's neutral grey. The character sheet
  wasn't reached in the test.

## Still open

- **Flag 40h.** `build` sets it on every step, as the sequel does for its own figures, and
  nothing went wrong. Whether it is needed was not tried.
- **The step's second byte.** The swing's pace looked like the sequel's own. The test ran with
  sound off, so whether the byte plays a sound is still open.
- **Recolouring.** Nothing seen changed a party figure's colours at run time.
- **The Obsidian Edition's dressed figures** (gear drawn on the party: `spritegear.py`) are SL's
  Loader at run time. In WR they would need that code carried over too.
