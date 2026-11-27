"""Nine Wake of the Ravager people drawn new, in Shattered Lands' pixel-art style, on the Obsidian
Edition's SL party bodies (people_dress.py's A: the mod's SEGOBJEX), for the ones for whom neither
an SL figure dressed (people_dress.py) nor Ravager's own art restyled would do.

Only the costume and the colours come from the Ravager figures; the stance and the animation are
SL's (the party bodies' crouched, weight-forward, arms-out poses, all 15 walking and 14 combat
frames), never straightened to Ravager's upright, square-on look.

How a figure is made, frame by frame, on the body's own pixels (as the Obsidian Edition draws worn
gear: obsidian-edition/dsloader/spritegear.py, with spriteparts.py's head, hair, shoulders, hands,
waist and feet in each frame):
  - each pixel is given a role (outline, skin, hair, clothing, wristband, the bow of the bow
    frames) and a place (head, chest, legs, feet);
  - each role is recoloured shade for shade into a ramp of SL palette colours (dark to light) that
    SL's figures use and that convert well to Ravager's palette, the artist's shading kept;
  - where the costume is a new shape, it is drawn on: plate is the body's shape shaded anew, light
    from the upper left, a dark edge on the shadow side (bevel()), with the artist's lines kept as
    the plates' seams; a closed helm the head and hair, with a visor slit; baggy trousers the legs
    widened a pixel each side down to a cuff at the ankle; a jann's hair a cap and locks down the
    back; a cloak (spritegear.draw_cloak: the SL woman's own cloak, frame by frame) let down to
    the ground; a revenant's chest bare and ribbed, its eyes sunken;
  - a sword where the knight or the lord would carry one (spritegear.armed: in the hand in a fight,
    at the belt walking).

The jann are drawn on the mul (bald, broad: the party body 312), the rest on the human man (300),
so a human-sized figure stays SL's human size (27 rows walking).

    draw_people.py sheet OUT.png [WR ...]        WR | drawn (front, side, combat) at 3x, a party
                                                 figure for scale
    draw_people.py frames OUT.png WR             every walking and combat frame of one figure
    draw_people.py zoom OUT.png WR ...           front, side, back, combat side, big
    draw_people.py build BASE_OBJEX OUT_OBJEX    the nine into BASE (after people_dress build)
    draw_people.py check OBJEX                   every frame of the nine decodes
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
EDITION = '/home/user/darksun-obsidian-edition/obsidian-edition'
sys.path.insert(0, EDITION)

import people_dress as pd  # noqa: E402
import sl_figures as s  # noqa: E402
from dsloader import spriteparts as sp, spritegear as sg  # noqa: E402

sg.set_palette([tuple(c) for c in pd.SLPAL])

PAD = 10  # (the working canvas round the body's own frame)
WALK_PAD = (6, 2, 0)  # the mod's copies of the party bodies: (each side, top, bottom) walking,
COMBAT_PAD = (10, 10, 10)  # and in a fight (people_dress.body() reads those copies)

MAN, MUL, WOMAN = 2095, 2093, 2099  # (spriteparts' models: the original pictures)
PARTY = {MAN: 300, MUL: 312}  # (their party objects, for the script)

# The bow frames hide the head in the bow: where it is, by hand (top, left, right, neck row)
for _m in (MAN, MUL):
    sp.HEADS.setdefault((_m, True, 10), (1, 7, 12, 7))
    sp.HEADS.setdefault((_m, True, 11), (3, 5, 11, 10))
BOW = frozenset((179, 180, 181, 182, 183))  # (the bow's colours, in combat frames 9-11)

SKIN = {MAN: frozenset(range(128, 158)), MUL: frozenset(range(128, 158))}
BANDS = frozenset((249, 250))
OUTLINE = 254

# Ramps: SL palette numbers, dark to light (colours SL's figures use; each converts to Ravager's
# palette within a few units, but for the blue skin's middle shades, Ravager's jann blue)
JANN_SKIN = (174, 175, 38, 160, 39, 161)  # (purple in the shadows, blue in the light: Ravager's)
# ... and the violet each blue is checkered with where SL's checker was (violet-blue from afar)
VIOLET = {160: 176, 39: 177, 161: 39, 38: 175}
OCHRE = (204, 94, 64, 65, 183)
ORANGE = (203, 179, 180, 201, 99, 100)
PALE = (18, 21, 24, 27, 29, 31)
GREEN = (188, 189, 190, 191, 192)
GOLD = (179, 64, 65, 183)
BLACK_HAIR = (254, 208, 209, 210)
MAROON_HAIR = (254, 174, 16, 175, 195)
SILVER = (208, 209, 210, 211, 212, 214, 253)
BLUE_BLACK = (254, 208, 17, 18, 19, 22, 24)
DARK_STEEL = (254, 208, 209, 210, 211, 212)
CLOAK_BLACK = (254, 208, 17, 209, 18, 210)
GHOST = (17, 19, 21, 23, 25, 27, 29, 31)
RAGS = (208, 209, 210, 211, 212)

SL_L = pd.SL_L


def L(q):
    return SL_L[q][0]


# ---------------------------------------------------------------------------------------------
# reading a frame


def blank(w, h):
    return [[None] * w for _ in range(h)]


def padded(rows, pad=PAD):
    w = len(rows[0]) + 2 * pad
    return [[None] * w for _ in range(pad)] + [[None] * pad + list(r) + [None] * pad for r in rows] + \
        [[None] * w for _ in range(pad)]


def crop(rows, src_w, src_h, pads):
    """The working canvas (PAD round a SRC_W x SRC_H frame) cut to PADS (side, top, bottom)."""
    side, top, bottom = pads
    return [r[PAD - side:PAD + src_w + side] for r in rows[PAD - top:PAD + src_h + bottom]]


def inside(rows, x, y):
    return 0 <= y < len(rows) and 0 <= x < len(rows[y]) and rows[y][x] is not None


def is_outline(rows, x, y):
    """Black at the edge of the figure (the outline, not a dark of the clothes)."""
    return rows[y][x] == OUTLINE and any(not inside(rows, x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))


def black_kind(rows, x, y):
    """An inner black pixel: 'area' (in a 2x2 of black: a black garment), 'dither' (SL's black and
    colour checker: shading), or 'line' (a line the artist drew between parts)."""
    b = lambda a, c: inside(rows, a, c) and rows[c][a] == OUTLINE
    for dx in (-1, 0):
        for dy in (-1, 0):
            if all(b(x + dx + i, y + dy + j) for i in (0, 1) for j in (0, 1)):
                return 'area'
    orth = sum(b(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    diag = sum(b(x + dx, y + dy) for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)))
    return 'dither' if orth == 0 and diag >= 1 else 'line'


def bevel(rows, solid=None):
    """Each pixel's light as a rounded shape lit from the upper left: about +1 on the upper-left
    edges, -1 on the lower-right ones, 0 within (from the slope of the blurred silhouette, or of
    SOLID(x, y): the parts between the artist's lines, each rounded of its own)."""
    h, w = len(rows), len(rows[0])
    solid = solid or (lambda x, y: rows[y][x] is not None)
    m = [[1.0 if solid(x, y) else 0.0 for x in range(w)] for y in range(h)]
    k = [1, 2, 3, 2, 1]
    def blur(a):
        t = [[sum(k[i + 2] * a[y][x + i] for i in range(-2, 3) if 0 <= x + i < w) / 9 for x in range(w)] for y in range(h)]
        return [[sum(k[i + 2] * t[y + i][x] for i in range(-2, 3) if 0 <= y + i < h) / 9 for x in range(w)] for y in range(h)]
    b = blur(m)
    g = lambda x, y: b[y][x] if 0 <= y < h and 0 <= x < w else 0.0
    out = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if rows[y][x] is None:
                continue
            gx = g(x + 1, y) - g(x - 1, y)
            gy = g(x, y + 1) - g(x, y - 1)
            out[y][x] = max(-1.0, min(1.0, (gx + gy) * 1.6))
    return out


class Frame:
    """One frame of a body (its own picture, unpadded) and where its parts are."""

    def __init__(self, model, frame, combat, rows):
        self.model, self.frame, self.combat = model, frame, combat
        self.rows = rows
        self.parts = sp.parts(rows, model, frame, combat)
        self.h, self.w = len(rows), len(rows[0])
        filled = [y for y, r in enumerate(rows) if any(q is not None for q in r)]
        self.top, self.bottom = filled[0], filled[-1]
        P = self.parts
        self.neck = P.shoulders[0] if P.shoulders else (P.head.top + 5 if P.head else self.top + 5)
        self.waist = P.waist if P.waist is not None else self.top + (self.bottom - self.top) // 2
        self.bow = combat and frame in sp.BOW_FRAMES
        self.light = bevel(rows)
        skin = SKIN[model]
        ls = sorted({q for r in rows for q in r if q in skin}, key=L)
        self.skin_rank = {q: i / max(1, len(ls) - 1) for i, q in enumerate(ls)}
        self.role = [[self._role(x, y) for x in range(self.w)] for y in range(self.h)]
        self.parts_light = bevel(rows, lambda x, y: self.role[y][x] not in (None, 'outline', 'black-line'))

    def _role(self, x, y):
        q = self.rows[y][x]
        if q is None:
            return None
        if self.bow and q in BOW:
            return 'bow'
        if is_outline(self.rows, x, y):
            return 'outline'
        if (x, y) in self.parts.hair:
            return 'hair'
        if q in BANDS:
            return 'band'
        if q in SKIN[self.model]:
            return 'skin'
        if q == OUTLINE:
            return 'black-' + black_kind(self.rows, x, y)
        return 'cloth'

    def place(self, x, y):
        """'head' (to the shoulders), 'chest' (to the waist), 'legs', 'feet' (the lowest 2 rows)."""
        P = self.parts
        if P.head and y < self.neck and P.head.left - 1 <= x <= P.head.right + 1:
            return 'head'
        if y > self.bottom - 2:
            return 'feet'
        if y > self.waist and not self.by_hand(x, y):
            return 'legs'
        return 'chest'

    def by_hand(self, x, y, r=2):
        return any(abs(x - hx) <= r and hy - 4 <= y <= hy + 2 for hx, hy in self.parts.hands.values())

    def in_head(self, x, y):
        P = self.parts
        return P.head is not None and P.head.top <= y < self.neck and P.head.left <= x <= P.head.right


def pick(ramp, t):
    """RAMP's shade at T (0 dark .. 1 light)."""
    return ramp[max(0, min(len(ramp) - 1, int(t * (len(ramp) - 1) + 0.5)))]


def orig_t(f, x, y):
    """A pixel's own lightness, 0 to 1 (skin by its rank among the skin's shades)."""
    q = f.rows[y][x]
    if q in f.skin_rank:
        return f.skin_rank[q]
    return min(1.0, L(q) / 80)


# ---------------------------------------------------------------------------------------------
# the costumes


def jann(f, out, skin, trousers, hair=None):
    """A jann on the mul: skin SKIN, baggy TROUSERS from the waist to a cuff at the ankle, bare
    blue feet, gold wristbands and sash; HAIR (a ramp) a cap and locks down the back, or bald."""
    P = f.parts
    for y in range(f.h):
        for x in range(f.w):
            role = f.role[y][x]
            if role in (None, 'outline', 'bow'):
                continue
            place = f.place(x, y)
            q = f.rows[y][x]
            if place == 'legs' and y < f.bottom - 2:
                t = orig_t(f, x, y) if role == 'skin' else 0.25
                if role.startswith('black'):
                    t = 0.0 if role == 'black-line' else 0.3
                t = 0.55 * t + 0.35 + 0.3 * f.light[y][x]
                out[y + PAD][x + PAD] = pick(trousers, t)
            elif role == 'band':
                out[y + PAD][x + PAD] = pick(GOLD, 0.35 + 0.5 * (L(q) - 40) / 30)
            elif role == 'skin' or (role == 'cloth' and place == 'feet'):
                t = orig_t(f, x, y) if role == 'skin' else 0.3
                out[y + PAD][x + PAD] = pick(skin, min(0.95, 0.65 * t + 0.38 + 0.15 * f.light[y][x]))
            elif role == 'black-line':
                out[y + PAD][x + PAD] = skin[0]
            elif role == 'cloth':  # (the mul's grey belt and bracers: a sash and the skin)
                if y >= f.waist - 1:
                    out[y + PAD][x + PAD] = pick(trousers, 0.1 + 0.4 * min(1, L(q) / 90))
                else:
                    out[y + PAD][x + PAD] = pick(skin, 0.5 + 0.2 * f.light[y][x])
    # SL's black-and-colour checker on the skin: a shade or two below the skin round it (the
    # mul's dark skin shading, now purple amid the blue, as Ravager's jann are shaded)
    rank = {c: i for i, c in enumerate(skin)}
    for y in range(f.h):
        for x in range(f.w):
            if f.role[y][x] in ('black-dither', 'black-area') and f.place(x, y) not in ('legs',):
                near = [rank[out[y + dy + PAD][x + dx + PAD]] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                        if out[y + dy + PAD][x + dx + PAD] in rank]
                if near:
                    out[y + PAD][x + PAD] = skin[max(1, round(sum(near) / len(near)) - (0 if f.role[y][x] == 'black-dither' else 1))]
                else:
                    out[y + PAD][x + PAD] = skin[1]
    # softened: each shade of the skin halfway to the shades round it (the mul's skin is a busy
    # checker; Ravager's jann are smooth)
    soft = {}
    for y in range(f.h):
        for x in range(f.w):
            q = out[y + PAD][x + PAD]
            if q not in rank or f.role[y][x] in ('outline', 'black-line'):
                continue
            near = [rank[out[y + dy + PAD][x + dx + PAD]] for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    if (dx or dy) and out[y + dy + PAD][x + dx + PAD] in rank]
            if len(near) >= 4:
                soft[(x, y)] = skin[max(1, round(0.4 * rank[q] + 0.6 * sum(near) / len(near)))]
    for (x, y), q in soft.items():
        out[y + PAD][x + PAD] = q
    if skin == JANN_SKIN:
        for y in range(f.h):
            for x in range(f.w):
                if f.role[y][x] == 'black-dither' and f.place(x, y) != 'legs':
                    out[y + PAD][x + PAD] = VIOLET.get(out[y + PAD][x + PAD], out[y + PAD][x + PAD])
    baggy(f, out, trousers)
    if hair:
        jann_hair(f, out, hair)


def baggy(f, out, trousers):
    """The trousers ballooning: the legs widened outward (a pixel at the thigh, two at the calf,
    the outline moved out), gathered into a dark cuff at the ankle."""
    hem = f.bottom - 2
    knee = f.waist + (hem - f.waist) // 2
    for y in range(f.waist + 2, hem):
        Y = y + PAD
        row = out[Y]
        runs = [(a, b) for a, b in sp._runs(row) if b - a >= 1]
        extra = 2 if knee <= y < hem - 1 else 1
        for k, (a, b) in enumerate(runs):
            for edge, step in ((a, -1), (b, 1)):
                outer = (k == 0 and step < 0) or (k == len(runs) - 1 and step > 0)
                n = extra if outer else 1
                if not outer:  # (between the legs: only into a gap of 3 or more)
                    gap = 0
                    while 0 <= edge + step * (gap + 1) < len(row) and row[edge + step * (gap + 1)] is None:
                        gap += 1
                    if gap < 3 or gap >= len(row):
                        continue
                if f.by_hand(edge - PAD, y, 3) or not (0 <= edge - PAD < f.w) or f.rows[y][edge - PAD] is None:
                    continue
                if f.role[y][edge - PAD] == 'bow':
                    continue
                if not all(0 <= edge + step * i < len(row) and row[edge + step * i] is None for i in range(1, n + 1)):
                    n = 1
                    if not (0 <= edge + step < len(row)) or row[edge + step] is not None:
                        continue
                lit = step < 0  # (the left side to the light)
                for i in range(0, n):
                    row[edge + step * i] = pick(trousers, (0.75 if lit else 0.3) - 0.1 * i)
                row[edge + step * n] = OUTLINE
    # the cuff: the hem row a dark band
    for x in range(f.w):
        if f.role[hem][x] not in (None, 'outline'):
            out[hem + PAD][x + PAD] = trousers[0] if f.role[hem][x] != 'skin' else trousers[1]


def jann_hair(f, out, hair):
    """A jann's hair: a mass round the head (out past it a pixel each side, as Ravager's thick
    locks are), the crown and the back of the head, and locks hanging down the back."""
    P = f.parts
    if not P.head or P.facing is None:
        return
    h = P.head
    mid = (h.left + h.right) // 2
    cells = set()
    for y in range(h.top, f.neck + 1):
        for x in range(h.left - 1, h.right + 2):
            if P.facing == sp.BACK:
                ok = True
            elif P.facing == sp.SIDE:
                ok = y <= h.top + 1 or x <= mid
            else:
                ok = y <= h.top + 1 or x in (h.left - 1, h.left, h.right, h.right + 1) or \
                    (y == h.top + 2 and h.left + 1 <= x <= h.right - 1)
            corner = y == h.top and (x <= h.left or x >= h.right)
            if ok and not corner and (inside(f.rows, x, y) or x in (h.left - 1, h.right + 1) and y > h.top + 1):
                cells.add((x, y))
    # the locks: from behind, down the middle of the back; from the side, behind the neck; from
    # the front, over the shoulders
    if P.facing == sp.BACK:
        spots = [(x, y) for y in range(f.neck, f.neck + 5) for x in range(mid - 2 + (y - f.neck) // 3, mid + 3 - (y - f.neck) // 3)]
    elif P.facing == sp.SIDE:
        spots = [(x, y) for y in range(f.neck, f.neck + 4) for x in range(h.left - 1, h.left + 2)]
    else:
        spots = [(x, y) for y in range(f.neck, f.neck + 3) for x in (h.left - 1, h.left, h.right, h.right + 1)]
    cells |= {(x, y) for x, y in spots if inside(f.rows, x, y) and not f.by_hand(x, y)}
    if P.facing == sp.FRONT:  # (the face: not hair)
        cells -= {(x, y) for y in range(h.top + 3, f.neck + 1) for x in range(h.left + 1, h.right)}
    lo = min(y for _, y in cells)
    hi = max(y for _, y in cells)
    for x, y in cells:
        X, Y = x + PAD, y + PAD
        t = 0.75 - 0.45 * (y - lo) / max(1, hi - lo) + 0.4 * (f.light[y][x] if 0 <= x < f.w and 0 <= y < f.h else 0.3)
        if (x + (y // 2)) % 3 == 0:  # (strands)
            t -= 0.4
        out[Y][X] = pick(hair[1:], t)
    # the outline round the hair where it stands out past the head
    for x, y in cells:
        if inside(f.rows, x, y):
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, -1), (0, 1)):
            X, Y = x + dx + PAD, y + dy + PAD
            if (x + dx, y + dy) not in cells and 0 <= Y < len(out) and 0 <= X < len(out[0]) and out[Y][X] is None:
                out[Y][X] = OUTLINE


def plate(f, out, metal, helm_metal=None, visor=True, seams=True, lift=0.0):
    """Full plate: each part of the body (between the artist's lines) shaded anew in METAL as a
    rounded piece lit from the upper left, the lines kept as the plates' seams; a closed helm over
    the head (HELM_METAL), a highlight on its dome and a visor slit; the long hair's mane off it."""
    helm_metal = helm_metal or metal
    for y in range(f.h):
        for x in range(f.w):
            role = f.role[y][x]
            if role in (None, 'outline', 'bow'):
                continue
            lt = 0.65 * f.parts_light[y][x] + 0.35 * f.light[y][x]
            head = f.in_head(x, y) or role == 'hair'
            own = {'black-line': 0.0, 'black-dither': 0.3, 'black-area': 0.35}.get(role)
            own = orig_t(f, x, y) if own is None else own
            t = 0.42 + lift + 0.6 * lt + 0.25 * (own - 0.5)
            if role == 'black-line':
                t = 0.08
            if head:
                t = 0.5 + lift + 0.6 * f.light[y][x] + (0.0 if role != 'black-line' else -0.25)
            out[y + PAD][x + PAD] = pick(helm_metal if head else metal, t)
    P = f.parts
    if seams and P.facing is not None:
        # a dark seam at the waist (the cuirass's lower edge), and the lit tops of the knee cops
        for x in range(f.w):
            if f.role[f.waist][x] not in (None, 'outline', 'bow') and not f.by_hand(x, f.waist):
                out[f.waist + PAD][x + PAD] = metal[1]
        knee = f.waist + (f.bottom - f.waist) // 2
        for x in range(f.w):
            if f.role[knee][x] not in (None, 'outline', 'bow', 'black-line') and not f.by_hand(x, knee):
                out[knee + PAD][x + PAD] = pick(metal, 0.7 + lift + 0.3 * f.light[knee][x])
    if P.head and P.facing is not None:  # (the dome's highlight)
        h = P.head
        hx = h.left + 2 if P.facing != sp.SIDE else (h.left + h.right) // 2 + 1
        for x, y in ((hx, h.top + 1), (hx + 1, h.top + 1)):
            if inside(f.rows, x, y) and f.role[y][x] != 'outline':
                out[y + PAD][x + PAD] = helm_metal[-1]
    pauldrons(f, out, metal, lift)
    if visor:
        visor_slit(f, out, helm_metal)
    trim_mane(f, out)


def trim_mane(f, out):
    """From the side, the man's long hair sweeps his head's outline back over his neck: under a
    helm that would be a hood, so behind a helm's breadth (HELM_DEEP pixels back from the face)
    the hair and its outline are taken off, and the helm's back given an outline."""
    P = f.parts
    if P.facing != sp.SIDE or not P.head:
        return
    h = P.head
    front = max(x for y in range(h.top, f.neck) for x in range(f.w) if f.rows[y][x] is not None)
    back = front - HELM_DEEP
    for y in range(h.top, f.neck):
        cut = False
        for x in range(0, back):
            if f.role[y][x] in ('hair', 'outline') or (x, y) in P.hair or f.rows[y][x] == OUTLINE:
                if out[y + PAD][x + PAD] is not None:
                    out[y + PAD][x + PAD] = None
                    cut = True
        if cut and out[y + PAD][back + PAD] is not None:
            out[y + PAD][back + PAD] = OUTLINE


HELM_DEEP = 7


def pauldrons(f, out, metal, lift=0.0):
    """Round plates on the shoulders: lit on top, a dark rim under, a pixel proud of the arm."""
    P = f.parts
    if not P.shoulders or not P.head or P.facing is None:
        return
    sy, sa, sb = P.shoulders
    if P.facing == sp.SIDE:
        centres = [((sa + sb) // 2, sy + 1)]
    else:
        centres = [(sa + 2, sy + 1), (sb - 2, sy + 1)]
    for cx, cy in centres:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                x, y = cx + dx, cy + dy
                if f.in_head(x, y) or (x, y) in P.hair and dy < 0:
                    continue
                if not (0 <= x < f.w and 0 <= y < f.h):
                    continue
                if f.rows[y][x] is None and dy > -1:
                    continue
                c = metal[-1] if (dx, dy) == (-1, -1) else pick(metal, 0.75 + lift) if dy < 0 else \
                    pick(metal, 0.5 + lift - 0.15 * dx) if dy == 0 else metal[1]
                out[y + PAD][x + PAD] = c
        # outline proud of the arm
        for dx in (-2, -1, 0, 1, 2):
            x, y = cx + dx, cy - 2
            if 0 <= x < f.w and 0 <= y < f.h and out[y + PAD][x + PAD] is None and out[y + 1 + PAD][x + PAD] is not None:
                out[y + PAD][x + PAD] = OUTLINE


def visor_slit(f, out, metal):
    P = f.parts
    if not P.head or P.facing is None:
        return
    h = P.head
    y = h.brow + 1
    if P.facing == sp.FRONT:
        xs = range(h.left + 1, h.right)
    elif P.facing == sp.SIDE:
        xs = range(h.right - 2, h.right + 1)
    else:
        return
    for x in xs:
        if inside(f.rows, x, y) and f.role[y][x] != 'outline':
            out[y + PAD][x + PAD] = OUTLINE
    # the breaths below the slit (from the front, a dark line down the faceplate's middle)
    if P.facing == sp.FRONT:
        mx = (h.left + h.right + 1) // 2
        for yy in (y + 2,):
            if inside(f.rows, mx, yy) and yy < f.neck:
                out[yy + PAD][mx + PAD] = metal[1]


def revenant(f, out):
    """A revenant: grey-lavender dead skin, the chest bare and ribbed, sunken eyes, grey wisps of
    hair and grey rags at the loins and feet."""
    P = f.parts
    for y in range(f.h):
        for x in range(f.w):
            role = f.role[y][x]
            if role in (None, 'outline', 'bow'):
                continue
            place = f.place(x, y)
            lt = f.light[y][x]
            if role == 'skin':
                t = 0.15 + 0.75 * orig_t(f, x, y) + 0.2 * lt
                out[y + PAD][x + PAD] = pick(GHOST, t)
            elif role == 'hair' and f.in_head(x, y) and P.facing != sp.BACK:  # (a bald skull)
                out[y + PAD][x + PAD] = pick(GHOST, 0.45 + 0.45 * lt)
            elif role == 'hair':  # (the long hair: thin grey wisps)
                out[y + PAD][x + PAD] = pick(RAGS, 0.2 + 0.35 * orig_t(f, x, y) + 0.2 * lt)
            elif role == 'band':
                out[y + PAD][x + PAD] = pick(RAGS, 0.4)
            elif place == 'chest' and not f.in_head(x, y):
                # the bare chest: ribs, every other row a shade darker, and the sternum
                t = 0.5 + 0.4 * lt
                mid = (P.head.left + P.head.right) / 2 if P.head else x
                if P.facing == sp.SIDE and P.head:
                    mid = P.head.right - 2
                ribs = P.facing in (sp.FRONT, sp.SIDE) and abs(x - mid) <= 3 and f.neck < y < f.waist - 1 \
                    and not f.by_hand(x, y, 3)
                spine = P.facing == sp.BACK and abs(x - mid) < 1 and f.neck < y < f.waist
                if role == 'black-line':
                    t = 0.12
                elif ribs and (y - f.neck) % 2 == 0:
                    t -= 0.35
                elif spine:
                    t -= 0.3
                out[y + PAD][x + PAD] = pick(GHOST, t)
            else:  # rags: the loincloth, the leg wrappings, the feet
                t = 0.25 + 0.4 * (orig_t(f, x, y) if role == 'cloth' else 0.2) + 0.3 * lt
                if role == 'black-line':
                    t = 0.0
                out[y + PAD][x + PAD] = pick(RAGS, t)
    # the eyes: two dark hollows below the brow; the cheeks hollow
    if P.head and P.facing in (sp.FRONT, sp.SIDE):
        h = P.head
        y = h.brow + 1
        xs = (h.left + 1, h.right - 1) if P.facing == sp.FRONT else (h.right - 1,)
        for x in xs:
            if inside(f.rows, x, y):
                out[y + PAD][x + PAD] = 208
        for x in ((h.left + 1, h.right - 1) if P.facing == sp.FRONT else (h.right - 2,)):
            if inside(f.rows, x, y + 2) and y + 2 < f.neck:
                out[y + 2 + PAD][x + PAD] = GHOST[1]


def drape(f, out, shades):
    """A long cloak from the shoulders to the ground, drawn on the (padded) canvas OUT: from behind
    over the back and legs; from the front and the side hanging behind the body, seen around it
    and between the legs; widening a pixel every few rows, its folds running down it, lit from
    the upper left, a dark hem on the ground and the outline round what it adds."""
    P = f.parts
    if not P.shoulders or not P.head or P.facing is None:
        return
    sy, sa, sb = P.shoulders
    ground = f.bottom
    before = [list(r) for r in out]
    hands = list(P.hands.values())
    keep = lambda x, y: f.in_head(x, y) or (x, y) in P.hair and P.facing != sp.BACK or \
        any(abs(x - hx) <= 1 and abs(y - hy) <= 2 for hx, hy in hands)
    cells = {}
    for y in range(sy, ground + 1):
        k = (y - sy) / max(1, ground - sy)
        if P.facing == sp.SIDE:  # (facing right: it hangs from the back of the shoulders)
            back = sa + 1
            a, b = back - 3 - int(k * 6), back + 2 + int(k * 2)
        else:
            mid, half = (sa + sb) / 2, (sb - sa) * 0.36
            a, b = int(mid - half - k * 3), int(round(mid + half + k * 3))
        for x in range(a, b + 1):
            if f.rows[y][x] is not None if 0 <= x < f.w else False:
                over = P.facing == sp.BACK or P.facing == sp.SIDE and x <= sa + 1 and y > sy
                if not over or keep(x, y) or f.role[y][x] == 'bow':
                    continue  # (behind the body, or the hands and head over it; from the side
                    # it hangs over the back of the shoulders)
            u = (x - a) / max(1, b - a)
            fold = (x - a) % 3 == 2
            tone = 0.75 - 0.6 * u - (0.35 if fold else 0) - 0.15 * k
            cells[(x, y)] = pick(shades[1:], tone)
    for (x, y), c in cells.items():
        out[y + PAD][x + PAD] = c
    # the hem, and the outline round what was added outside the body
    for (x, y) in cells:
        if y == ground:
            out[y + PAD][x + PAD] = shades[0] if (x + 1, y) in cells and (x - 1, y) in cells else OUTLINE
    for (x, y) in list(cells):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            X, Y = n[0] + PAD, n[1] + PAD
            if n not in cells and 0 <= Y < len(out) and 0 <= X < len(out[0]) and out[Y][X] is None and n[1] <= ground:
                out[Y][X] = OUTLINE


def lord(f, out, woman):
    """The lord in black: dark grey plate and closed helm, a long black cloak to the ground, gold
    clasps at the shoulders."""
    plate(f, out, DARK_STEEL, DARK_STEEL, visor=True, seams=True)
    template = sg.cloak_template(woman, WOMAN, f.frame, f.combat) if woman is not None else None
    if template is None or f.parts.facing is None:
        return
    sg.CLOAK_COLOURS[LORD_CLOAK] = CLOAK_BLACK
    sg.draw_cloak(out, [list(r) for r in out], MAN, f.parts, LORD_CLOAK, PAD, template)
    drape(f, out, CLOAK_BLACK)
    P = f.parts
    if P.shoulders and P.head and P.facing == sp.FRONT:
        sy, sa, sb = P.shoulders
        for x in (P.head.left, P.head.right):
            if inside(f.rows, x, sy):
                out[sy + PAD][x + PAD] = 183


LORD_CLOAK = 9001  # (an item type of our own for spritegear's cloak colours)

SWORD = 45  # (a long sword: spritegear's WEAPON_SHAPES)
METAL = 4


def with_sword(f, out):
    """A sword in the hand in a fight, at the belt walking (spritegear.armed)."""
    own = sg.Own(parts=f.parts, source=f.rows, source_parts=f.parts, at=lambda x, y: x)
    unpadded = [r[PAD:len(r) - PAD] for r in out[PAD:len(out) - PAD]]
    return sg.armed(unpadded, f.model, f.frame, f.combat, {"right": (SWORD, METAL)}, pad=PAD, own=own)


# Each figure: (body, how it is drawn, what it is)
FIGURES = {
    2413: (MUL, lambda f, o, w: jann(f, o, JANN_SKIN, OCHRE), 'jann, bald, yellow-ochre trousers'),
    2457: (MUL, lambda f, o, w: jann(f, o, JANN_SKIN, OCHRE), 'jann, bald, yellow-ochre trousers'),
    2458: (MUL, lambda f, o, w: jann(f, o, JANN_SKIN, ORANGE, BLACK_HAIR), 'jann, black hair, orange trousers'),
    2459: (MUL, lambda f, o, w: jann(f, o, JANN_SKIN, PALE), 'jann, bald, pale grey trousers'),
    2460: (MUL, lambda f, o, w: jann(f, o, JANN_SKIN, GREEN, MAROON_HAIR), 'jann, maroon hair, green trousers'),
    2536: (MAN, lambda f, o, w: revenant(f, o), 'revenant: grey-lavender, gaunt'),
    3605: (MAN, lambda f, o, w: plate(f, o, SILVER, lift=0.08), 'white knight: silver plate, closed helm'),
    3606: (MAN, lambda f, o, w: plate(f, o, BLUE_BLACK), 'black knight: blue-black plate, closed helm'),
    2575: (MAN, lambda f, o, w: lord(f, o, w), 'lord in black: cloak to the ground, dark plate, helm'),
}
ARMED = {3605, 3606, 2575}


def draw(wpic):
    """(walking frames, combat frames, SL script) of WR picture WPIC, in SL palette numbers, the
    frames the size of the mod's party bodies' (people_dress.body)."""
    model, how, _ = FIGURES[int(wpic)]
    script = pd.body(PARTY[model])[3]
    out = []
    for combat, pads in ((False, WALK_PAD), (True, COMBAT_PAD)):
        frames = pd.frames_of(pd.A, 'BMP ', model + combat)
        women = pd.frames_of(pd.A, 'BMP ', WOMAN + combat)
        done = []
        for i, rows in enumerate(frames):
            f = Frame(model, i, combat, rows)
            canvas = padded(rows)
            how(f, canvas, women[i] if i < len(women) else None)
            if int(wpic) in ARMED and f.parts.facing is not None:
                canvas = with_sword(f, canvas)
            done.append(crop(canvas, f.w, f.h, pads))
        out.append(done)
    return out[0], out[1], script


# ---------------------------------------------------------------------------------------------
# pictures for the eye


def _show(frames, pal, conv=None):
    return [pd.img(f, pal, conv) for f in frames]


def sheet(out, pics, Z=3):
    """WR | drawn (front, side, combat), with a party figure (the human man) for scale."""
    from PIL import Image, ImageDraw
    pics = [int(p) for p in pics] or list(FIGURES)
    man_w, _, _, _ = pd.body(300)
    man_c = pd.frames_of(pd.A, 'BMP ', 2451)
    party = pd.strip(_show([man_w[0], man_w[2], man_c[6]], pd.WRPAL, pd.TABLE))
    rows = []
    for wp in pics:
        w, c, _ = draw(wp)
        wf = pd.frames_of(pd.B, 'BMP ', wp)
        wc = pd.frames_of(pd.B, 'CBMP', wp) if ('CBMP', wp) in pd.B else None
        ims = [pd.strip(_show(pd.pick(wf, wc), pd.WRPAL)),
               pd.strip(_show([w[0], w[2], c[6], w[1], c[0]], pd.WRPAL, pd.TABLE)), party]
        ims = [i.resize((i.width * Z, i.height * Z), Image.NEAREST) for i in ims]
        rows.append((f'WR {wp}: {FIGURES[wp][2]}', ims))
    cw = [max(r[1][k].width for r in rows) + 16 for k in range(3)]
    H = sum(max(i.height for i in r[1]) + 20 for r in rows) + 24
    sh = Image.new('RGB', (sum(cw) + 8, H), (52, 52, 52))
    d = ImageDraw.Draw(sh)
    d.text((4, 4), 'Ravager | drawn: front, side, combat, back, combat front | the SL man for scale', fill=(255, 255, 255))
    y = 24
    for label, ims in rows:
        d.line([(0, y), (sh.width, y)], fill=(90, 90, 90))
        d.text((4, y + 3), label, fill=(255, 255, 0))
        x = 4
        h = max(i.height for i in ims)
        for k, im in enumerate(ims):
            sh.paste(im, (x, y + 18 + h - im.height), im)
            x += cw[k]
        y += h + 20
    sh.save(out)
    print(out)


def frames_sheet(out, wpic, Z=3):
    """Every walking frame (a row) and every combat frame (a row) of WPIC, in Ravager's colours."""
    from PIL import Image, ImageDraw
    w, c, _ = draw(int(wpic))
    a = pd.strip(_show(w, pd.WRPAL, pd.TABLE))
    b = pd.strip(_show(c, pd.WRPAL, pd.TABLE))
    a, b = [i.resize((i.width * Z, i.height * Z), Image.NEAREST) for i in (a, b)]
    sh = Image.new('RGB', (max(a.width, b.width) + 8, a.height + b.height + 50), (52, 52, 52))
    d = ImageDraw.Draw(sh)
    d.text((4, 2), f'WR {wpic}: {FIGURES[int(wpic)][2]}: walking 0-14, combat 0-13', fill=(255, 255, 0))
    sh.paste(a, (4, 18), a)
    sh.paste(b, (4, 30 + a.height), b)
    sh.save(out)
    print(out)


def build(base, out):
    """The nine into BASE as OUT: BMP (walking), CBMP (combat) and SCMD (SL's script for WR), as
    people_dress.build writes its dressed figures."""
    new = {}
    conv = lambda fs: [[[None if q is None else pd.TABLE[q] for q in r] for r in f] for f in fs]
    for wp in FIGURES:
        w, c, script = draw(wp)
        new[('BMP ', wp)] = s.picture(conv(w))
        new[('CBMP', wp)] = s.picture(conv(c))
        wr_like = pd.B.get(('SCMD', wp), b'')
        new[('SCMD', wp)] = s.sl_script_for_wr(script, wr_like or b'\0' * (s.SLOTS * 2))
    s.write_ranged(base, new, out)
    print(out, len(FIGURES), 'figures drawn')


def check(path):
    """Every frame of the nine in PATH decodes, and its script's steps name frames it has."""
    C = s.load(path)[1]
    bad = 0
    for wp in FIGURES:
        for t in ('BMP ', 'CBMP'):
            c = C[(t, wp)]
            n = s.frames(c)[0]
            for i in range(n):
                try:
                    s.decode_any(c, i)
                except Exception as e:  # noqa: BLE001
                    bad += 1
                    print(wp, t, i, 'fails:', e)
            print(wp, t, n, 'frames')
        print(wp, 'SCMD', len(C[('SCMD', wp)]), 'bytes')
    print('all decode' if not bad else f'{bad} fail')


def zoom(out, pics, Z=10, which=((False, 0), (False, 2), (False, 1), (True, 6))):
    """A few frames of each of PICS big, in Ravager's colours (to look at pixel by pixel)."""
    from PIL import Image
    rows = []
    for wp in pics:
        w, c, _ = draw(int(wp))
        fs = [(c if comb else w)[i] for comb, i in which]
        rows.append(pd.strip(_show(fs, pd.WRPAL, pd.TABLE), gap=2))
    W = max(r.width for r in rows)
    H = sum(r.height + 2 for r in rows)
    sh = Image.new('RGB', (W, H), (52, 52, 52))
    y = 0
    for r in rows:
        sh.paste(r, (0, y), r)
        y += r.height + 2
    sh.resize((W * Z, H * Z), Image.NEAREST).save(out)
    print(out)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'sheet':
        sheet(sys.argv[2], sys.argv[3:])
    elif cmd == 'frames':
        frames_sheet(sys.argv[2], sys.argv[3])
    elif cmd == 'zoom':
        zoom(sys.argv[2], sys.argv[3:])
    elif cmd == 'build':
        build(sys.argv[2], sys.argv[3])
    elif cmd == 'check':
        check(sys.argv[2])
