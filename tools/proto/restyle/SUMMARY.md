# The restyle of Ravager's own art: what was done and decided (2026-11-20)

Written for the project thread that carries this work on (session_01MpsiU9vAnuVwCvH4i4ZrWC could not
reply to it directly).

## Softness

No fix aimed only at softness or blur was made. Sharpness was handled inside the restyle method
itself, and the owner's later objection to restyled people was about pose, not blur.

## The method (restyle.py, v2, the kept version)

- **Scale 0.82.** Each new pixel is the coverage-weighted Lab average of its block, so thin patterns
  blend rather than alias. Thin dark lines are detected and kept.
- **Tone** is pulled toward the Obsidian Edition party's lightness and chroma (party_target.json), by at
  most 15 L. Pale figures with little colour (bone, white) mostly keep their brightness.
- **Light:** a per-frame ramp, so light comes from the upper left, as on SL's figures.
- **Edges:** edges on the shadow side are darkened, the amount chosen per figure to bring its dark-edge
  share near the party's 41%.
- **Colours:** quantised into WR's steady colours with a 2x2 ordered dither fixed to the frame's anchor,
  so the dither doesn't crawl between frames.
- **Anchors:** the script's per-frame anchors are scaled with the frames.

Earlier versions (v1, v2a, v2b), the measuring and comparison scripts, the sheet and scene makers, the
in-game test's OBJEX maker and its log: `earlier/`.

## Verdicts

**The 45 figures with no SL equivalent** (golems, yuan-ti, verini, serpents, mind flayers, the
skeleton and others) were restyled with v2.
- **Verdict:** the owner saw them beside SL's party and approved ("I'm happy with this direction"). Kept.
- **In the game:** the yuan-ti and the magma golem were drawn over the opening ambush's Draxans. Their
  feet stayed on the ground and the dither didn't crawl.
- **Not tested:** the golem's attack frames and the verini.
- **Known weak spots, unfixed:**
  - The red verini reads orange-brown, and the red and orange variants sit close together.
  - The magma golem is a muted brown rather than bright orange.
  - The obsidian golem comes out greyer than WR's black: shrinking averages its black with its
    highlights.
  - Mind flayer 2889 gets a dark hat where the original has a purple head.
  - Mind flayer 2890 shows visible checker dither.
  - The OJFF +2/+4 anchors were not scaled, only the script anchors.

**People restyled the same way** (the jann, the revenant, the knights, the lord in black, then briefly
31 more):
- **Verdict:** rejected. The owner said "The humanoid figures look really bad in the ravager style", then
  "I just don't like the way Ravager has the 'stiff' humanoid look" (upright, square-on, arms hanging).
- **What stayed:** only the air and fire elementals (2405, 2557) stay restyled
  (`../people-restyle.json`).
- **What replaced the rest:** the others went back to SL bodies (`../people_dress.py`, `../dress/*.json`).
  That led to the jann drawn from scratch, in `../own/`.

## Pictures

- **Durable:** `docs/RAVAGER-FIGURES.md` (the "No SL equivalent" section). Its before-and-after
  pictures, once in `docs/img/ravager-figures/`, were taken out of git (bc423ac, 2026-11-21); this file
  was kept on the session branch `ccr-a74ac7db-d7yv2u` and brought here on 2026-11-26.
- **Container only, lost with it:**
  - `/tmp/playtest/art-review/restyle45_1-4.png` and `together-45.png`
  - the rejected restyled people: `dress/pick_1-3.png` and `dress/flagged_restyled.png` in that
    session's scratchpad
  - the game grabs, `/tmp/playtest/restyle-game-*.png`

## Building

Built file: `/tmp/playtest/restyle45_OBJEX.GFF`. Rebuild it with
`restyle.py --base /tmp/playtest/swap1_OBJEX.GFF --out OUT --all45`.

## Unfinished

- The weak spots above.
- The in-game tests of the verini and of the golem's attack.
- Scaling the OJFF anchors.
