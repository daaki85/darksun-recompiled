"""A weapon drawn into a dressed figure's hands with the Loader's own gear drawing
(obsidian-edition/dsloader/spritegear.armed), for Ravager's people who carry one the SL body
doesn't: "weapon": "pick" in a dress entry (the miners 3612 and 3613). The pick is a wooden haft
and a metal head across its end, its tips bent back, a shape of its own added to the Loader's.

The Loader finds the hands on the body as the game drew it (its own colours, before dressing), so
the weapon is drawn on the undressed frame and what it changed is copied onto the dressed one."""
import halfelf_dress as he

PICK, PICK_TYPE = 'pick', 999  # (an item type of its own: the Loader's numbers stop well short)
_ready = {}


def _setup(slpal):
    if _ready:
        return _ready['g']
    fg, g = he._loader(slpal)
    from dsloader import spriteparts as sp
    shape = g._shape

    def with_pick(s):
        if s == PICK:
            W = g.WOOD
            return [(st, [(0, W + 1)]) for st in range(-2, 7)] + [
                (5, [(-4, 0), (4, 0)]),
                (6, [(-4, 0), (-3, 1), (-2, 1), (-1, 1), (1, 1), (2, 1), (3, 1), (4, 0)]),
                (7, [(-3, 0), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (3, 0)])]
        return shape(s)
    g._shape = with_pick
    g.WEAPON_SHAPES[PICK_TYPE] = PICK
    g.HEADS[PICK] = 5
    g.TWO_HANDED = frozenset(set(g.TWO_HANDED) | {PICK})
    _ready.update(g=g, sp=sp)
    return g


def armed(raw, dressed, spic, frame, combat, slpal, pad=10):
    """DRESSED (one frame) with a pick in the hands found on RAW (the same frame undressed), padded
    by PAD as the Loader pads; SPIC: the body's walking picture (its model)."""
    g = _setup(slpal)
    sp = _ready['sp']
    if spic not in sp.MODELS:  # (an SL body that isn't the party's: its green wristbands as theirs)
        sp.MODELS[spic] = ('ravager person', frozenset({249, 250}), frozenset())
    a = g.armed([list(r) for r in raw], spic, frame, combat, {"right": (PICK_TYPE, 2)}, pad=pad)
    b, d = g.padded(raw, pad), g.padded(dressed, pad)
    return [[a[y][x] if a[y][x] != b[y][x] else d[y][x] for x in range(len(a[0]))] for y in range(len(a))]


def trim(groups, pad=10):
    """GROUPS (lists of padded frames) with the padding no frame uses taken off their left and top,
    the same for every frame, and how far each frame's picture moved right and down (DX, DY): the
    script's anchors move with it (shift)."""
    every = [f for g in groups for f in g]
    x0 = min(x for f in every for r in f for x, q in enumerate(r) if q is not None)
    y0 = min(y for f in every for y, r in enumerate(f) if any(q is not None for q in r))
    return [[[r[x0:] for r in f[y0:]] for f in g] for g in groups], (pad - x0, pad - y0)


def shift(script, dx, dy):
    """SCMD SCRIPT with every step's anchor (bytes 5 and 6) moved by DX, DY: its pictures grew by
    that on the left and top."""
    import sl_figures as s
    out = bytearray(script)
    for k in range((len(script) - s.SLOTS * 2) // s.STEP):
        at = s.SLOTS * 2 + s.STEP * k
        out[at + 5] = max(0, min(255, out[at + 5] + dx))
        out[at + 6] = max(0, min(255, out[at + 6] + dy))
    return bytes(out)
