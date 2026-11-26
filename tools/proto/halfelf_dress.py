"""Ravager's people on the Obsidian Edition's half-elves (people_dress.py's bodies "halfelf-man" and
"halfelf-woman"). The Loader makes its half-elves from the game's own pictures (obsidian-edition/
dsloader/figures.py): the man is the elf man a column wider below the neck, in a shirt, jerkin,
trousers and boots, with short hair; the woman is the human woman a column slimmer, her hair up in a
bun, her cloak kept. Here the same makers run with each person's colours put in:

  the man:   "hair", "jerkin", "sleeve" (the shirt), "legs", "boots": each a ramp of SL palette
             numbers, dark to light, fed to the maker in place of the half-elf's own (its shading,
             dither, collar and belt kept); "skin": a ramp the elf's skin (128-153) is spread over.
  the woman: "hair" (her bun and hair, the half-elf's golden browns), "cloak" (her cloak's purples:
             a robe or dress over the back), "skin": ramps the same way.

The makers live in the obsidian-edition repository, checked out beside this one (OBSIDIAN overrides
where)."""
import os, sys

OBSIDIAN = os.environ.get('OBSIDIAN', os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                   '..', '..', '..', 'darksun-obsidian-edition', 'obsidian-edition'))
BODIES = {'halfelf-man': 304, 'halfelf-woman': 301}  # (the SL party bodies they are made from)
SKIN = frozenset(range(128, 154)) - {128, 129}
HAIR = (180, 181, 182, 200, 65)  # (the half-elf woman's golden browns, her bun's too)
CLOAK = (174, 175, 176, 177)
_cache = {}


def _loader(slpal):
    if 'fg' not in _cache:
        sys.path.insert(0, os.path.abspath(OBSIDIAN))
        from dsloader import figures, spritegear
        spritegear.set_palette([tuple(c) for c in slpal])
        _cache['fg'], _cache['sg'] = figures, spritegear
    return _cache['fg'], _cache['sg']


def _spread(frames, colours, ramp, light):
    cs = sorted(colours, key=light)
    m = {c: ramp[min(len(ramp) - 1, i * len(ramp) // len(cs))] for i, c in enumerate(cs)}
    return [[[None if q is None else m.get(q, q) for q in r] for r in f] for f in frames]


def dressed(d, body, slpal):
    """(walking frames, combat frames) of dress entry D on its half-elf; BODY: people_dress.body."""
    fg, sg = _loader(slpal)
    light = lambda c: sg._LIGHT[c]
    walk, combat, spic, script = body(BODIES[d['body']])
    if d['body'] == 'halfelf-man':
        old = fg.MAN_RAMPS
        fg.MAN_RAMPS = {k: d[k] if k in d else v for k, v in old.items()}
        try:
            o = fg.HalfElfMan(walk, combat)
            w, c = o.frames(False), o.frames(True)
        finally:
            fg.MAN_RAMPS = old
        swaps = [(SKIN, d['skin'])] if 'skin' in d else []
    else:
        o = fg.HalfElfWoman(walk, combat)
        w, c = o.frames(False), o.frames(True)
        swaps = [(cols, d[k]) for cols, k in ((SKIN, 'skin'), (HAIR, 'hair'), (CLOAK, 'cloak')) if k in d]
    for cols, ramp in swaps:
        w, c = _spread(w, cols, ramp, light), _spread(c, cols, ramp, light)
    return w, c, walk, combat, script
