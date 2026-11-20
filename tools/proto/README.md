# Prototypes: Shattered Lands' wall tops and shadows in Tyr

Scripts from the 2026-11-20 trials (docs/FIGURES.md, "Wall tops and shadows"), kept as they ran.
They read the owner's installs at fixed paths (`/tmp/playtest/inst`, `/tmp/playtest/rav`, the
test copy `/tmp/playtest/ravsl`) and take `tools/` on their path for `sl_figures`. Not yet folded
into `sl_figures.py`.

- `tops.py`: refills a wall picture's top with SL tiles (ashlar: the arena district's tiles 5
  and 43), aligned on 16; thin pieces (24 wide or less) are all top; roofed walls are left alone.
- `build_tops.py SRC_DIR OUT_DIR [nosquash]`: applies it to every structure Tyr places, after
  `sl_figures.py squash` (SRC_DIR is the squash's output), or at full height with `nosquash`.
- `bakeshadow2.py OBJEX_IN RGN_IN OBJEX_OUT RGN_OUT`: bakes each structure's cast shadow into its own
  picture (its outline offset 10 right, 6 down, near-black) in **one global checkerboard**: a
  shadow pixel only where its screen x + y is even. A picture placed at both pixel parities gets a
  copy with the other phase (BMP 5001 on) and its odd placements a copy of their object (OJFF 32100
  on), set in the region's ETAB. Use after `build_tops.py`, with the squash's region file.
- `bakeshadow.py`: the first version (each picture its own phase): overlapping shadows came out
  solid. Superseded by `bakeshadow2.py`.
- `gffr.py`: rewrites a GFF whose index is ranged (OBJEX.GFF): chunks re-pointed or added (new ids
  after the last of their type, as a new run; the type's offset table in its GFFI chunk rewritten).
  Checked: an unchanged rewrite reads back the same; adding changes only the two offset tables.
- `gffw.py`: rewrites a GFF with chunks added (a new index after the data); checked to read back
  unchanged with no changes.
- `shadows.py`: **don't use**: it read the map 112 wide (it is 128 wide, 98 rows: docs/FIGURES.md)
  and wrote shadow tiles into `GMAP`, which turned out to be per-cell
  flags (0, 64, 192), not the drawn tile map. The ground is `MAP `: docs/FIGURES.md, "How WR draws its ground".
- `frame.py`: `exact_frame` rebuilds the 320x200 frame, as palette numbers, from a DOSBox grab.
- `groundshadow.py OBJEX RGN OUT_RGN [DX DY]`: **the shadows SL's way**, drawn into the region's
  ground map: each structure's outline cast 12 right and 8 down, what any object covers left out, each
  shadowed cell given a darkened copy of its tile (SL's shadowed floor: lightness x 0.73, a + 11,
  b x 0.82) in 8-pixel blocks. The 255-tile limit decides: the most common (tile, shadow) pairs get
  tiles, others take the nearest shape of the same tile or stay unshadowed. Use with `build_tops.py`'s
  OBJEX (no baked shadows) and the squash's region file. Supersedes `bakeshadow2.py` for Tyr.
- `region.py`: `draw(game, region, box)` draws any region of either game, ground and objects.
- `metrics.py`: the per-region measurements of the second comparison (docs/FIGURES.md).
- `thickwalls.py RGN_IN RGN_OUT [sl | wr:PIC:X:Y]`: **thick walls, SL's way**: every wall cell (`GMAP` 192: two cells
  wide, though WR draws its walls as thin strips) gets an SL ashlar top tile (the arena district's 5
  and 43), with a darker edge line where the wall meets open ground; 31 new tiles for Tyr. Use on the
  regrade's region file with `build_tops.py ... nosquash`'s OBJEX (heights as WR's). `wr:PIC:X:Y` takes
  the tops from WR's own art instead: a 16x16 square of picture PIC (Tyr: `wr:343:0:17`, a wall piece's
  top with no ornament).
- `cellshadow.py RGN_IN RGN_OUT [DX DY]`: **shadows along the wall cells**: each wall cell's square
  cast 12 right and 8 down onto the open cells beside it, darkened as SL's shadowed floor. A cell's
  shadow depends only on its west, north and north-west neighbours, so the edges are straight. Tyr:
  1,540 cells, 131 tiles (to 255); 12 cells go without for want of tile numbers.
