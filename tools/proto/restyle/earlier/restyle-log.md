# Restyled creatures in Wake of the Ravager: game test (2026-11-20)

Under test: `/tmp/playtest/restyle45_OBJEX.GFF` (the 45 WR figures with no SL equivalent, restyled to
SL's look, on top of swap1: the SL party and creature batch 1). Copy: `/tmp/playtest/ravrs`
(`cp -a` of rav). Test-only edit in the copy's OBJEX.GFF: the ambush's Draxans drawn as restyled
creatures: object 202 -> picture 693 (magma golem), 206 -> 2843 (yuan-ti), 207 -> 2850 (verini),
each with the anchor (+2, +4) of the creature's own object (414, 434, 53).

## Steps
1. First start: the Draxans of the ambush aren't objects 202/206/207. `ravcreatures.py` in the fight:
   the four that join it (+17h = 07) are objects 204 (three: id FF34h) and 200 (one: FF38h), both
   "Draxan". Stopped my DOSBox (by pid), remapped instead: 200 -> 693 (magma golem, anchor of object
   414), 204 -> 2843 (yuan-ti, anchor of 434); run files put back from `__support/save`.
2. Second start (`sh ravstart.sh /tmp/playtest/ravrs`, talk 3/Return x4, `ravclick.py 160 45`): the
   ambush has three yuan-ti (2843) in the street and the magma golem (693) on the rug in the house
   left; `restyle-game-2.png`.
3. Two rounds passed with `ravfight.py end` while `ravburst.sh` grabbed (rs-turn1: 471 grabs, rs-turn2:
   393; sheets `/tmp/playtest/burst/rs-turn{1,2}.png`). The serpents slither up (walking frames) and
   attack Gerakis and the others in their combat frames (rising coil, blade): hits land, yellow hit
   splash. The golem walks out of the house into the street (side frames). Grabs:
   `restyle-game-b250.png`, `-b400.png` (serpents attacking), `-c300.png` (golem walking beside
   the serpents' attack), `-still.png` (golem standing).
4. Anchors: feet on the street in every grab looked at; no jump between walking and combat frames,
   no figure floating or sunk. Animation: walking and the attack play through, no missing frame.
5. Dither: the golem standing, 21 consecutive grabs (370-391): 0 pixels changed in its box. The
   2x2 dither is anchored to each frame's anchor, so it doesn't crawl while a figure stands.
6. Stopped my DOSBox (by pid), lock released. Nothing saved.

## Not covered
- The verini wasn't in the fight: the ambush has only two Draxan objects (204 x3, 200), so two
  pictures; a verini run would remap 204 again.
- The golem never attacked on screen in these two rounds (its combat frames unseen in the game).
