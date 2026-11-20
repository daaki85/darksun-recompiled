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
animation scripts and their 36 slots all match, and so does the map grid (16×16 tiles, 98 rows of 128).
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

## A region's colours (phase 2)

`sl_figures.py regrade SL_DIR WR_DIR RGNxxx STRENGTH OUT.GFF` moves one region's colours toward
Shattered Lands' ground. Tried on Tyr (`RGN032`) at strength 1.0, in the game, 2026-11-20.

- **The target:** Shattered Lands' ground colours over all its regions, each tile counted as often
  as its map uses it. **SL draws region N in `GPLDATA.GFF`'s PAL N**: the slave pens (`RGN29`) in
  PAL 41, checked against a screenshot of the game. In Lab, SL's ground averages L 48, a 15, b 19
  (lighter and warmer than Tyr's L 26, a 5, b 10), with twice the spread.
- **Which colours can change:** Tyr's ground is 37% in the region's own entries 16-95 (which its
  scenery objects use too) and 63% in entries 176-255, which the interface and figures share. So
  entries 16-95 are graded in the palette, ground and scenery together. Ground pixels in shared
  colours are graded and clustered into the 16-95 entries that neither the tiles nor the region's
  objects use (its `ETAB`: 8 bytes an entity, the object negated at +6). **The game cycles
  entries 16-23 at run time** (torch and fire glow), overwriting the file's values there, so the
  spare entries come from 32-95 only: 8 in Tyr.
- **The grade:** lightness by a power curve that takes Tyr's mean to SL's and keeps white white (a
  straight shift blew the light sandstone out to white). The colour axes a and b by mean and
  spread, the spread's scale capped at 1.6. All of it blended by STRENGTH.
- **In play:** warm orange sandstone, tan floors, warm pale cobbles. The interface and figures
  are unchanged. Beside SL's slave pens, Tyr now reads warmer, but SL's ground is lighter and more
  muted, and Tyr's sandstone is more saturated. Strength and the cap are the knobs.

## Walls and objects (phase 4, started)

Decided 2026-11-20 after seeing Tyr regraded: the ground can stay regraded; the walls and other
objects need repainting in Shattered Lands' style. What the first look found:

- **WR's buildings are objects.** Tyr places 867 entities from 246 pictures (its `ETAB`): sandstone
  wall blocks and columns (64x64, 24x64, 18x64), plaster walls with doorways and windows, red-tiled
  roof edges, market stalls, furniture, rugs, sacks, barrels and pots, and some people as objects.
- **SL builds them differently.** Its placed scenery is almost all outdoor dressing (plants, cacti,
  bones, rocks, straw, pots). Its `WALL` chunks (`GPLDATA.GFF`, numbered region x 100 + piece) are
  mostly cliff and cave rock, in 16-pixel-wide shaped pieces; only 47 are full rectangles and 11 of
  those tile cleanly (among them brick 4100-4101, stucco 1306 and sandstone 4310/4313). **SL's
  built architecture is in its ground tiles**: the arena district (region 28) has its brick and
  pale ashlar walls in its tile set, and region 0E carved yellow sandstone.
- **A refill keeps WR's angle.** Filling WR's wall shapes with SL brick (outline, windows, roof
  tiles and shading kept) looks like SL's material, but WR draws walls as tall faces seen almost
  head-on, and SL from higher above (shorter faces, their tops showing). A true SL look means
  redrawing walls and items at SL's angle.
- **The angles, measured.** A known-square inset in SL (object 685) is 21 by 19 pixels: seen from
  about 65 degrees above the horizontal. WR's open barrel rims (2355, 2361) are 14 by 11: about
  50 degrees. SL's slave pens screenshot shows the rest: wall tops are big brick surfaces, front
  faces a short band of rubble, and walls cast long diagonal shadows on the floor.
- **SL's walls are tile arrangements.** Matching the pens screenshot back to region 41's tiles at
  every grid offset (59 blocks matched) gives the parts: 28 the floor, 26 shadowed floor, 70 the
  shadow's diagonal edge, 57/58 a rubble block's lit top over 61/62 its darker face, 25 a brick wall
  face, 96/97 brick column tops (with floor at their edge), 2-7 plain brick.
- **Piece by piece breaks the scene** (tried in the game, 2026-11-20). WR's wall block 330 rebuilt
  as an SL rubble block half as tall, its pillars 350 and 353 as brick columns, its table 516 as
  SL's bench 170 (each picture's size kept, its top clear, so its base stays: an object's record
  anchors its picture by +2 x and +4 y, the bottom centre). The game drew them, but WR's walls are
  several overlapping pictures that assume its angle: shortening one opened a hole where what was
  behind shows through. The angle can only change for all of a region's structures at once.
- Matching surfaces by colour alone picks sand and grass, not masonry: textures have to be chosen
  by material.

## Tyr from SL's angle: the whole-region squash

`sl_figures.py squash WR_DIR RGN032 0.66 OUT_DIR` shows a region's structures and furniture as
seen from SL's steeper angle (faces shrink by cos 65 / cos 50, about 0.66). Tried on Tyr in the
game, 2026-11-20, over the regraded ground, in four runs:

1. **Every picture squashed:** furniture and walls lower, the scene intact, but the walls running
   north-south broke into pieces. They are stacks of thin pictures whose height is mostly the
   wall's top receding into the distance, not upright face.
2. **Only the bottom 48 rows (WR's face height) squashed, the rest moved down:** still gaps.
3. **Structures (24 wide or less, or 56 tall or more) moved down 16 rows and cut by 16 at the
   bottom, furniture squashed:** the walls joined, except pieces stacked on top of walls (entity
   height 64), which came down twice.
4. **Pieces only ever placed on top of something keep their picture and come down by 16 through
   their entity height:** continuous walls, a flatter table, a lower bottom wall. Nothing broken.

The animated pictures (people, doors, curtains) and the rugs are left alone. Every picture keeps
its size, so its anchor still holds. **`ETAB` x is in the camera's units** (DS:1408h), not halved.
The change is moderate at this factor. SL's wall tops (brick or rubble) and its cast shadows,
which carry much of its look, are not added yet.

## Wall tops and shadows (prototypes, 2026-11-20)

On top of the squash, in the game (scripts in `tools/proto/`, as they ran):

- **Tops:** each structure's top refilled with SL's ashlar, the arena district's tiles 5 and 43 (its
  tiles 54 and 55 have floor at their edges), aligned on 16, with a darker edge line. On a thin
  piece (24 wide or less: a wall running away from the camera) the whole picture is wall top; on a
  wide one only the band above its face. Roofed walls keep their roofs. In play: Tyr's walls read
  as SL's ashlar walls.
- **Shadows:** baked into each structure's own picture, its outline offset 10 right and 6 down in a
  near-black checkerboard (SL's light comes from the upper left). The canvas grows right and down,
  so the anchor holds; nearer walls and objects, drawn later, cover what falls on them. In play: a
  dark band right of each wall. First each picture had its own checkerboard phase, and where two
  pictures' shadows overlapped out of step they came out solid. Fixed by **one global phase** (a
  shadow pixel only where screen x + y is even): 71 of the 137 pictures are placed at both
  parities, so each gets a copy with the other phase (BMP 5001 on), and its odd placements a copy of
  their object pointing at it (81 objects, OJFF 32100 on, set in the `ETAB`). Over all of Tyr,
  solid 2x2 patches of the shadow colour went from 5,546 to 484, of which the walls' own dark details
  make 446 with no shadows at all. Seen in the game: clean checkerboards.
- **WR's ground:** worked out below ([how WR draws its ground](#how-wr-draws-its-ground)).
  `tools/proto/gffw.py` adds chunks to a plain-index GFF (a new index after the data).

## How WR draws its ground

Worked out 2026-11-20 from the game (Tyr, the opening ambush) and its region loader.

- **The map is 98 rows of 128 tiles,** not 112 x 112: 12,544 bytes either way. WR's region loader
  (DSUN.EXE file offset 2B5xxh; SL's at 26Exxh) reads `TILE`, then `RMAP` into the far pointer at
  DS:29EFh, or `MAP ` there if the region has no `RMAP` (Tyr hasn't; SL's regions have `RMAP`, WR's
  `MAP `), then `GMAP` into DS:0538h, then walks `GMAP` as 98 rows of 128 bytes (`shl ax,7`),
  clearing bit 20h of each. `RMAP`/`MAP ` hold tile numbers (`TILE` chunks, 16 x 16); `GMAP` holds
  per-cell flags (0, 64, 192 seen in Tyr).
- **Placement:** tile (c, r) is drawn at map pixel (16c, 16r); the screen shows map pixels minus
  the camera (DS:1408h, x and y), exactly. Entities use the same map pixels: an object's anchor
  (OJFF +2, +4) sits at its `ETAB` (x, y), raised by its height. (An earlier note here gave
  "(x - 896, y + 24)": that came from reading the map 112 wide, and was wrong.)
- **Checked:** the game's frame, rebuilt exactly from a grab (DOSBox shows the 320 x 200 frame
  with every pixel doubled across and rows repeated 2 or 3 times in a fixed pattern, so the first
  row of each repeat is exact; every pixel then matched a palette colour, a 6-bit value v shown as
  v x 4 + v / 16), matched Tyr's tiles at 103 of 103 blocks, with the screen's top-left at map
  column 63, row 85.5 for camera (1008, 1368). Tyr drawn offline from these rules (ground from
  `MAP `, objects from the `ETAB` in rising y) matches the game's frame wall for wall; only the
  people the scripts place at run time and the interface are missing. SL's slave pens drawn from
  `RMAP` as 128 x 98 come out as their maze of cells.
- **The frame isn't in guest memory** as a 320 x 200 buffer the kit can read (no run of its
  bytes found in the 16 MB); the grab is the way to an exact frame.
- **What it opens:** SL-style shadows drawn into the ground, by giving the cells beside walls
  darkened copies of their tiles in `MAP ` (tile numbers up to 255; Tyr has 94). Whether anything
  in the game reads a cell's tile number for its own purposes isn't known yet.

## Shadows in the ground (2026-11-20)

`tools/proto/groundshadow.py` draws the shadows into Tyr's ground as SL does, replacing the
checkerboards baked into the wall pictures:

- **Safe to change a cell's tile:** only two places in WR's code read the ground map's tile numbers
  (DSUN.EXE 2B8A4h and 2BA19h), both the ground drawing (a cell's tile number, its picture looked up
  by the routine at 2B58Ah, a 16 x 16 drawn); the three other uses of the map's pointer free it when a
  region is left. Walking is decided by `GMAP`, untouched.
- **The shadow:** every structure's outline cast 12 right and 8 down; what any object covers is left
  out. A shadowed cell gets a copy of its tile with those pixels darkened as SL's shadowed floor is
  (the pens' tile 26 against the floor's 28: lightness x 0.73, a + 11, b x 0.82: darker and warmer).
- **The tile limit:** 2,554 ground cells are shadowed, in 1,895 different (tile, shadow) pairs, and a
  region's tile numbers stop at 255 (Tyr has 94: 162 free). At 8-pixel blocks 275 pairs are left; the
  162 most common get tiles, which covers 1,642 of 1,710 cells exactly; 34 take the nearest shape on
  the same tile and 34 stay unshadowed. The blocks show as small steps along some shadow edges.
- **In play:** solid, warm dark bands right of the walls across the street and the rooms, moving with
  the ground as the camera scrolls; Ar'Anda walked into a wall's shadow as before.

## A second comparison: what actually differs (2026-11-20)

Asked for by the owner after the shadow work: a wider comparison, now that both games' maps can be
drawn whole (ground from `RMAP`/`MAP `, objects from the `ETAB`). Every region of both games was
measured the same way (32 of SL's, each in its own palette; WR's 20), and screen-size views of
built-up places compared: SL's slave pens (`RGN29`), arena district (`RGN28`) and city (`RGN2B`)
against WR's Tyr (`RGN032`) and the Veiled Alliance's headquarters (`RGN033`).

| Median over all regions | SL | WR |
|---|---|---|
| Black void round the playable areas | 0% | 35% |
| Ground lightness (Lab L, void left out) | 48 | 30 |
| Ground colourfulness (chroma) | 25 | 21 |
| Ground texture contrast (lightness step between neighbours) | 5.5 | 3.6 |
| Share of the map covered by placed objects | 5% | 21% |
| Placed objects per region | 331 | 649 |
| Median object size (pixels) | 630 | 1,196 |
| Colours used; ground tiles | 187; 195 | 191; 174 |

What the numbers and views say:

- **How places are built.** SL builds its places in the ground tiles: thick walls (two tiles and
  more across) whose big tops and faces are tiles, with few placed objects (mostly plants, bones,
  rocks). WR builds them from placed objects: thin wall pieces, and rooms full of furniture. That is
  most of the 4-to-1 difference in object cover.
- **How a map is laid out.** An SL region is one continuous place filling its 128 x 98 map: a maze
  of cells, a district, a stretch of desert. A WR map holds several separate pieces (buildings,
  rooms, cave chambers, floating rock) set in black void.
- **The ground.** SL's is much lighter and bolder: sand with big waves, brick with clear courses,
  pastel floors. WR's is darker and finer: grey cobbles, dark earth, fine dithered noise. Both use
  checker dithering about as much (18% and 17% of pixels).
- **Shadows.** SL draws cast shadows into some of its tiles (the pens' floor, the diagonal shadows
  of the city in `RGN2B`) but not everywhere (none in the arena). WR draws none.
- **The angle: not established.** Re-measured on more objects of known shape, neither game is
  drawn to one angle: SL's brazier bowl (806) is 17 x 8 (about 28 degrees above the horizontal),
  its gold rings (33) 13 x 10 (about 50), its square inset (685) 21 x 19 (about 65); WR's barrels and
  round table come out at 44 to 52. And SL's arena district stands its brick walls three or four
  tiles high, as tall as WR's. So the earlier "SL at 65, WR at 50" rested on too little, and the
  squash (which shortened WR's walls by a third on that basis) is in doubt. The visible difference
  is more likely the walls' **thickness** (SL's big tops) than the camera.
- **Already known:** SL's figures are 20-35% shorter on the same tiles; the interface is the same
  art (WR's in fewer colours).

## Thick walls, heights restored (2026-11-20)

After the second comparison: the squash undone (WR's own wall heights back), and Tyr's walls made
thick SL's way.

- **`GMAP` marks the walls:** 192 on wall cells, 64 on cells next to walls and furniture, 0 open
  (128 on 38 cells, meaning unknown). Overlaid on the opening street, the 192 cells are two cells
  (32 pixels) wide where WR draws its walls as 18-pixel strips: every wall already blocks a band
  twice as wide as it looks.
- **The trial** (`tools/proto/thickwalls.py`): every wall cell gets an SL ashlar top tile with a
  darker edge line where it meets open ground, so the walls fill their blocked bands, as SL's thick
  walls do; the wall pictures keep their ashlar tops (`build_tops.py nosquash`). 2,331 cells, 31 new
  tiles. Nothing walkable is covered.
- **In the game:** the street's walls are wide ashlar bands, the sandstone faces at full height, the
  fight unaffected. Mixed spots remain where WR's own wall art meets the new tops (the red-tiled
  roof column inside a band of ashlar).
- **Next:** shadows can follow the same cells: the open cells just right of and below wall cells,
  darkened, with straight cell-aligned edges, which needs few tiles.

## Still open

- **Flag 40h.** `build` sets it on every step, as the sequel does for its own figures, and
  nothing went wrong. Whether it is needed was not tried.
- **The step's second byte.** The swing's pace looked like the sequel's own. The test ran with
  sound off, so whether the byte plays a sound is still open.
- **Recolouring.** Nothing seen changed a party figure's colours at run time.
- **The Obsidian Edition's dressed figures** (gear drawn on the party: `spritegear.py`) are SL's
  Loader at run time. In WR they would need that code carried over too.
