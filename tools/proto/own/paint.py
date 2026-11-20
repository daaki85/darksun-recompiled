"""The balls of rig.body() made into a game-size frame of SL palette numbers.

The style's rules, in the order they are applied:
  1. Seen from SL's steep three-quarter view (the camera PITCH degrees above level), so the tops of
     the head, hair and shoulders show.
  2. Drawn at Z times (4x) as smooth shapes: every sub-pixel keeps its surface's normal and depth.
  3. Light from the upper left and the front (low enough that the face is lit, not only the tops);
     the far side of the body is a little darker than the near side, so the far arm and leg sit
     back; hollows (between the pectorals, under an arm, between the legs: a surface deeper than
     the mean round it) are darker. The hair's locks each carry a small tone of their own, so the
     mass breaks into clumps.
  4. Reduced to 1x by blocks: a pixel is filled when enough of its block is, takes the block's main
     material and part, and the mean light of that material's
     sub-pixels. The light (given each material's contrast, TONE) is then cut into the material's
     3-5 shades in bands (CUTS: the darkest kept for deep shadow, the lightest for a small
     highlight), which is what keeps the clusters clean: no dither anywhere.
  5. Clean-up at 1x: one-pixel spurs and pinholes in the silhouette go, and a shade pixel with no
     neighbour of its own shade takes the shade most of its neighbours have.
  5b. Clean edges (lines.py): the silhouette and every shade boundary redrawn as straights and
     regular steps (1:1, 1:2, 1:3 and their turns); a staircase of uneven steps gets even ones.
  5c. Fewer, bigger shade shapes: on the skin and the trousers a patch of one shade under 4 pixels
     takes its neighbours' shade. The skin's lightest shade comes only from the marks' lights.
  6. Inner lines. Where one part passes in front of another (an arm over the chest, the near leg
     over the far one), the part behind gets a line: black where the near part is on its upper left
     (the shadow it casts), the material's darkest shade elsewhere. An arm or hand against the torso,
     a hand against anything, and leg against leg always get the line, however close in depth.
     Seams between materials: black under the sash, the darkest shade at a bracer's edges, and a brow
     shadow (a darker shade) on the skin under the hair.
  6c. Big dark areas, as SL's: black where the body is deep in a hollow (under the arms and the
     chin, between the legs, the crotch) and on the shadow side of a limb well behind the torso;
     the gold (sash, bracers) edged with black, as SL's wristbands are.
  6b. Marks: the rig's lines and dots on the body's surface (the eye line, sternum, the line under
     the pectorals; one-pixel lights on the pectorals, shoulders and nose; dark fold wedges from knee
     to cuff on the trousers),
     drawn where they show: on their own part and not hidden behind another.
  7. (OUTLINE 'outside', rounds 1-5) An outline one pixel outside the silhouette: black (254) on the shadow side (right and bottom),
     and on the lit edges (upper left) the material's second-darkest shade instead, a lighter line.
     7b. Its outer edge redrawn clean too, as in 5b.
  7'. (OUTLINE 'inside', round 6, SL's way: its figures have no outline ring) No ring; the
     edge pixels on the shadow side (right and bottom) take their material's darkest shade.
  8. A last pass for orphans: a pixel whose colour none of its eight neighbours has takes the
     neighbouring colour nearest it in its own ramp, or failing that the commonest one round it
     (the outline and the marks are left: a mark is meant to stand alone).
"""
import math
import numpy as np
import lines

PITCH = 32                       # degrees the camera looks down
Z = 4                            # drawn at Z times, then reduced
LIGHT = np.array([-0.65, -0.25, 0.72]); LIGHT = LIGHT / np.linalg.norm(LIGHT)   # x right, y down, z out

# each material's shades, SL palette numbers dark to light (all colours SL's own figures use)
RAMPS = {
    'skin':  [158, 159, 176, 177, 161],          # violet, lit blue (WR 150, 148, 172, 171, 27)
    'hair':  [208, 207, 205],                    # black, brown-grey streaks (WR 231, 230, 200)
    'cloth': [129, 136, 138, 140, 142],          # orange trousers (WR 223, 199, 198, 196, 205)
    'sash':  [64, 183, 167],                     # gold sash (WR 206, 18, 100)
    'gold':  [64, 183, 167],                     # bracers (WR 206, 18, 100: bronze, gold, yellow)
    'leather': [208, 207, 205],                  # short boots (WR 231, 230, 200)
}
MATS = list(RAMPS)
PARTS = ['torso', 'head', 'hair', 'arm_l', 'arm_r', 'hand_l', 'hand_r', 'leg_l', 'leg_r']
BLACK = 254
COVER = 7                        # sub-pixels of Z*Z a pixel needs to be filled
SHADE = dict(ambient=0.15, diffuse=0.85, depth=0.03, hollow=0.5, hollow_r=1.5)
# where the light (0 dark .. 1 full) crosses into each next shade, by the number of shades: the
# darkest shade is kept for deep shadow and the lightest for a small highlight
CUTS = {1: [], 3: [0.35, 0.8], 4: [0.3, 0.6, 0.92], 5: [0.3, 0.5, 0.75, 0.97]}
# the skin's own: the shadow side one flat shade (159: the near-black is kept for the black areas,
# rule 6c, and lines), two lit shades; its lightest only in the marks' one-pixel lights
CUTS_OF = {'skin': [0.0, 0.5, 0.8, 9]}
LINE_GAP = 1.4                   # depth gap (1x pixels) between parts that earns a line (rule 6)
ALWAYS = {frozenset(pair) for pair in (('arm_l', 'torso'), ('arm_r', 'torso'), ('hand_l', 'torso'),
          ('hand_r', 'torso'), ('leg_l', 'leg_r'), ('head', 'torso'), ('hand_l', 'arm_l'), ('hand_r', 'arm_r'),
          ('hand_l', 'leg_l'), ('hand_l', 'leg_r'), ('hand_r', 'leg_l'), ('hand_r', 'leg_r'))}
# (material above, material below): the role the pixel below takes (rule 6's seams)
SEAMS = {('hair', 'skin'): 'darker'}
# the gold sits on black, as SL's wristbands do: these materials' pixels touching it go black
EDGED = {'gold': {'skin'}, 'sash': {'skin', 'cloth'}}
MERGED = ('skin', 'cloth')       # the materials rule 5c merges small patches in
HOLLOW_BLACK = 0.6               # a pixel this deep in a hollow (1x pixels) is black (rule 6c)
FAR_BLACK = 1.5                  # a limb this far behind the torso (1x pixels) has its shadow black
OUTLINE = 'inside'               # rule 7: 'outside' (a ring round the figure, rounds 1-5), 'inside'
                                 # (SL's way: no ring; the shadow-side edge pixels take their material's
                                 # darkest shade) or 'none'
MARK_TOL = 1.2                   # how far (1x pixels) a mark may sit behind the surface and still show
# a material's light before it is cut into shades: (contrast, offset); the hair is dark and its
# locks need more contrast to break into clumps at 1x, skin and cloth a little more than the light
TONE = {'hair': (1.6, -0.7), 'skin': (1.3, 0.02), 'cloth': (1.3, 0)}
JOINED = {frozenset(('head', 'hair'))}                     # parts that never get a line between them

# the frame: a fixed canvas, so frames line up; (0, 0, 0) of the world lands on ORIGIN
W1, H1 = 48, 40
ORIGIN = (24, 34)


def project(rows):
    """World balls to screen (Z times): x, y (down), depth (toward the viewer), r."""
    c, s = math.cos(math.radians(PITCH)), math.sin(math.radians(PITCH))
    x, y, z, r = rows[:, :4].T
    return np.stack([(x + ORIGIN[0]) * Z, (-y * c + z * s + ORIGIN[1]) * Z, (z * c + y * s) * Z, r * Z], 1)


def raster(rows, mats, parts):
    """Z-buffered balls: depth, normal (3), material, part, tone per sub-pixel; -inf depth where empty."""
    H, W = H1 * Z, W1 * Z
    dep = np.full((H, W), -np.inf); nrm = np.zeros((H, W, 3)); mat = np.zeros((H, W), int); prt = np.zeros((H, W), int)
    ton = np.zeros((H, W))
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    for (cx, cy, cd, r), t, m, p in zip(project(rows), rows[:, 4], mats, parts):
        x0, x1 = max(0, int(cx - r)), min(W, int(cx + r) + 1)
        y0, y1 = max(0, int(cy - r)), min(H, int(cy + r) + 1)
        if x0 >= x1 or y0 >= y1:
            continue
        dx, dy = xx[y0:y1, x0:x1] - cx, yy[y0:y1, x0:x1] - cy
        h2 = r * r - dx * dx - dy * dy
        h = np.sqrt(np.maximum(h2, 0)); d = cd + h
        win = (h2 > 0) & (d > dep[y0:y1, x0:x1])
        dep[y0:y1, x0:x1][win] = d[win]
        nrm[y0:y1, x0:x1][win] = np.stack([dx, dy, h], -1)[win] / r
        mat[y0:y1, x0:x1][win] = MATS.index(m); prt[y0:y1, x0:x1][win] = PARTS.index(p)
        ton[y0:y1, x0:x1][win] = t
    return dep, nrm, mat, prt, ton


def box(a, r):
    """The sum of A over the (2r+1)-square around each element."""
    c = np.pad(a, (r + 1, r)).cumsum(0).cumsum(1)
    n = 2 * r + 1
    return c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]


def light(dep, nrm, ton, centre):
    """Rule 3 per sub-pixel: the light, less where the surface is in a hollow (between the pectorals,
    under an arm, between the legs): deeper than the mean of what is round it."""
    full = np.isfinite(dep); d = np.where(full, dep, 0)
    r = int(SHADE['hollow_r'] * Z)
    mean = box(d, r) / np.maximum(box(full.astype(float), r), 1)
    hollow = np.clip((mean - d) / Z, 0, 2)
    v = SHADE['ambient'] + SHADE['diffuse'] * np.maximum(0, nrm @ LIGHT)
    return v + SHADE['depth'] * (dep - centre) / Z - SHADE['hollow'] * hollow + ton, hollow


def reduce(dep, nrm, mat, prt, ton, centre):
    """Rule 4: (material, light, part, depth, hollow) per 1x pixel; material -1 where empty."""
    v, hol = light(dep, nrm, ton, centre)
    full = np.isfinite(dep)
    blk = lambda a: a.reshape(H1, Z, W1, Z).swapaxes(1, 2).reshape(H1, W1, Z * Z)
    F, M, P, Vb, D, Hb = blk(full), blk(mat), blk(prt), blk(v), blk(np.where(full, dep, 0)), blk(hol)
    cover = F.sum(-1)
    out_m = np.full((H1, W1), -1); out_v = np.zeros((H1, W1)); out_p = np.zeros((H1, W1), int)
    out_d = np.zeros((H1, W1)); out_h = np.zeros((H1, W1))
    for j in range(H1):
        for i in range(W1):
            if cover[j, i] < COVER:
                continue
            f = F[j, i]
            m = int(np.bincount(M[j, i][f], minlength=len(MATS)).argmax())
            sel = f & (M[j, i] == m)
            out_m[j, i] = m; out_v[j, i] = Vb[j, i][sel].mean()
            out_p[j, i] = np.bincount(P[j, i][f]).argmax(); out_d[j, i] = D[j, i][f].mean() / Z
            out_h[j, i] = Hb[j, i][f].mean()
    return out_m, out_v, out_p, out_d, out_h


def bands(m, v):
    """Light into each material's shade index (rule 4)."""
    s = np.zeros(m.shape, int)
    for k, name in enumerate(MATS):
        sel = m == k
        gain, off = TONE.get(name, (1, 0))
        cuts = CUTS_OF.get(name, CUTS[len(RAMPS[name])])
        s[sel] = np.searchsorted(cuts, (v[sel] - 0.5) * gain + 0.5 + off)
    return s


N4 = ((0, -1), (-1, 0), (1, 0), (0, 1))
N8 = N4 + ((-1, -1), (1, -1), (-1, 1), (1, 1))


def at(a, x, y, empty=-1):
    return a[y, x] if 0 <= x < a.shape[1] and 0 <= y < a.shape[0] else empty


def tidy_silhouette(m, s, p, d):
    """Rule 5, the shape: spurs (a pixel with at most one filled neighbour) go, pinholes fill."""
    for _ in range(2):
        for y in range(H1):
            for x in range(W1):
                nb = [(x + dx, y + dy) for dx, dy in N4 if at(m, x + dx, y + dy) >= 0]
                if m[y, x] >= 0 and len(nb) <= 1:
                    m[y, x] = -1
                elif m[y, x] < 0 and len(nb) >= 3:
                    src = nb[0]
                    m[y, x], s[y, x], p[y, x], d[y, x] = m[src[1], src[0]], s[src[1], src[0]], p[src[1], src[0]], d[src[1], src[0]]


def tidy_shades(m, s):
    """Rule 5, the shading: a lone shade pixel takes the shade its same-material neighbours share."""
    for _ in range(3):
        changed = 0
        for y in range(H1):
            for x in range(W1):
                if m[y, x] < 0:
                    continue
                same4 = [s[y + dy, x + dx] for dx, dy in N4 if at(m, x + dx, y + dy) == m[y, x]]
                if len(same4) < 2 or s[y, x] in same4:
                    continue
                same8 = [s[y + dy, x + dx] for dx, dy in N8 if at(m, x + dx, y + dy) == m[y, x]]
                s[y, x] = max(set(same8), key=lambda q: (same8.count(q), -abs(q - s[y, x])))
                changed += 1
        if not changed:
            break



def clean_edges(m, s, p, d):
    """Rule 5b: the silhouette's edges, then each material's shade boundaries, redrawn as clean
    lines (lines.py), each both ways round (rows, then columns)."""
    def both(get_mask, fill, clear):
        lines.regularise(get_mask(), fill, clear)
        lines.regularise(get_mask().T, lambda y, x, f: fill(x, y, f, True), lambda y, x: clear(x, y))

    def copy(y, x, sy, sx):
        m[y, x], s[y, x], p[y, x], d[y, x] = m[sy, sx], s[sy, sx], p[sy, sx], d[sy, sx]

    def sil_fill(y, x, f, t=False):
        if m[y, x] < 0:
            copy(y, x, *((f, x) if t else (y, f)))

    def sil_clear(y, x):
        m[y, x] = -1
    both(lambda: m >= 0, sil_fill, sil_clear)
    for k, name in enumerate(MATS):
        for level in range(1, len(RAMPS[name])):
            def fill(y, x, f, t=False):
                if m[y, x] == k and s[y, x] < level:
                    s[y, x] = level

            def clear(y, x):
                if m[y, x] == k and s[y, x] >= level:
                    s[y, x] = level - 1
            both(lambda: (m == k) & (s >= level), fill, clear)


def merge_small(m, s, p, least=4):
    """Rule 5c: a patch of one shade (within one material and part) under LEAST pixels takes the
    shade most of its neighbours in that material have: fewer, bigger shade shapes. Only on the big
    materials (MERGED): the hair's streaks, the sash and the bracers are small on purpose."""
    seen = np.zeros(m.shape, bool)
    for y0 in range(H1):
        for x0 in range(W1):
            if m[y0, x0] < 0 or seen[y0, x0] or MATS[m[y0, x0]] not in MERGED:
                continue
            key = (m[y0, x0], s[y0, x0], p[y0, x0]); patch = [(x0, y0)]; seen[y0, x0] = True
            for x, y in patch:
                for dx, dy in N4:
                    X, Y = x + dx, y + dy
                    if 0 <= X < W1 and 0 <= Y < H1 and not seen[Y, X] and (m[Y, X], s[Y, X], p[Y, X]) == key:
                        seen[Y, X] = True; patch.append((X, Y))
            if len(patch) >= least:
                continue
            nb = [s[y + dy, x + dx] for x, y in patch for dx, dy in N4
                  if at(m, x + dx, y + dy) == key[0] and (x + dx, y + dy) not in patch]
            if nb:
                for x, y in patch:
                    s[y, x] = max(set(nb), key=nb.count)


def darks(body, m, s, p, h):
    """Rule 6c: SL's big dark areas. Black where the body is deep in a hollow (under the arms and
    the chin, between the legs, the crotch), and the shadow side of a limb well behind the torso
    (by its balls' mean distance from the viewer, so height doesn't count)."""
    dark = (m >= 0) & (h > HOLLOW_BLACK)
    z = lambda part: np.mean([r[2] for r, q in zip(body.rows, body.parts) if q == part])
    for part in ('arm_l', 'arm_r', 'hand_l', 'hand_r', 'leg_l', 'leg_r'):
        if z(part) < z('torso') - FAR_BLACK:
            dark |= (m >= 0) & (p == PARTS.index(part)) & (s == 0)
    hair = m == MATS.index('hair')
    return dark & ~hair

def role(name, mat, shade):
    """The colour a line, seam or mark of role NAME takes on a pixel of MAT at SHADE."""
    ramp = RAMPS[MATS[mat]]
    return {'black': BLACK, 'dark': ramp[0], 'shadow': ramp[min(1, shade)], 'darker': ramp[max(0, shade - 1)],
            'light': ramp[-1]}[name]


def lined(m, p, d, x, y):
    """Rule 6: the line role pixel (X, Y) takes for a nearer part beside it, or None."""
    for dx, dy in N4:
        q = at(m, x + dx, y + dy)
        if q < 0 or p[y + dy, x + dx] == p[y, x]:
            continue
        pair = frozenset((PARTS[p[y + dy, x + dx]], PARTS[p[y, x]]))
        gap = d[y + dy, x + dx] - d[y, x]
        if gap <= 0 or (gap < LINE_GAP and pair not in ALWAYS):
            continue
        if pair in JOINED or ('torso' in pair and q == m[y, x] and pair not in ALWAYS):
            continue                  # a joint, or the hips running into a trouser leg
        return 'black' if dx < 0 or dy < 0 else 'dark'     # the nearer part up or left: its shadow
    return None


def colours(m, s, p, d, dark):
    """Rules 6 and 7: SL palette numbers, None where clear (DARK: rule 6c's black areas)."""
    out = [[None if m[y, x] < 0 else RAMPS[MATS[m[y, x]]][s[y, x]] for x in range(W1)] for y in range(H1)]
    for y in range(H1):
        for x in range(W1):
            if m[y, x] < 0:
                continue
            r = lined(m, p, d, x, y)
            if r is None and y > 0 and m[y - 1, x] >= 0:
                r = SEAMS.get((MATS[m[y - 1, x]], MATS[m[y, x]]))
            if r is None and any(MATS[m[y, x]] in EDGED.get(MATS[q], ()) for q in
                                 (at(m, x + dx, y + dy) for dx, dy in N4) if q >= 0):
                r = 'black'
            if r is None and dark[y, x]:
                r = 'black'
            if r:
                out[y][x] = role(r, m[y, x], s[y, x])
    if OUTLINE == 'inside':
        for y in range(H1):
            for x in range(W1):
                if m[y, x] >= 0 and out[y][x] != BLACK and any(at(m, x + dx, y + dy) < 0 for dx, dy in ((1, 0), (0, 1))):
                    out[y][x] = RAMPS[MATS[m[y, x]]][0]
    for y in range(H1):
        for x in range(W1):
            if m[y, x] >= 0 or OUTLINE != 'outside':
                continue
            nb = [(dx, dy) for dx, dy in N4 if at(m, x + dx, y + dy) >= 0]
            if not nb:
                continue
            if all(dx > 0 or dy > 0 for dx, dy in nb):         # the body is right of / below it: lit edge
                dx, dy = nb[0]
                ramp = RAMPS[MATS[m[y + dy, x + dx]]]
                out[y][x] = ramp[min(1, len(ramp) - 1)]
            else:
                out[y][x] = BLACK
    return out


def marks(out, body, m, s, p, d):
    """Rule 6b: the body's marks drawn into OUT where they show; the pixels drawn, as a set."""
    done = set()
    for pts, name, part, mat in body.marks:
        pts = np.hstack([pts, np.zeros((len(pts), 2))])
        sx, sy, sd, _ = (project(pts) / Z).T
        path = [(sx[0], sy[0], sd[0])]
        for i in range(1, len(pts)):
            n = int(max(abs(sx[i] - sx[i - 1]), abs(sy[i] - sy[i - 1])) * 2) + 1
            path += [(sx[i - 1] + (sx[i] - sx[i - 1]) * t / n, sy[i - 1] + (sy[i] - sy[i - 1]) * t / n,
                      sd[i - 1] + (sd[i] - sd[i - 1]) * t / n) for t in range(1, n + 1)]
        for fx, fy, fd in path:
            x, y = int(fx), int(fy)
            if (x, y) in done or at(m, x, y) < 0 or PARTS[p[y, x]] != part or fd < d[y, x] - MARK_TOL:
                continue
            if MATS[m[y, x]] != mat:
                continue                      # (a mark is on its own material: not over the sash or a bracer)
            if out[y][x] == BLACK:
                continue                      # (an inner line or the outline is there already)
            out[y][x] = role(name, m[y, x], s[y, x]); done.add((x, y))
    return done


def frame(body):
    """A Body (rig.body) to a frame: rows of SL palette numbers or None, W1 x H1."""
    dep, nrm, mat, prt, ton = raster(body.rows, body.mats, body.parts)
    centre = np.median(project(body.rows)[:, 2])
    m, v, p, d, h = reduce(dep, nrm, mat, prt, ton, centre)
    s = bands(m, v)
    tidy_silhouette(m, s, p, d)
    tidy_shades(m, s)
    clean_edges(m, s, p, d)
    merge_small(m, s, p)
    out = colours(m, s, p, d, darks(body, m, s, p, h))
    clean_outline(out)
    return orphans(out, marks(out, body, m, s, p, d))


def clean_outline(out):
    """Rule 7b: the outer edge (the outline's) redrawn clean as well (lines.py): a pixel gained
    takes the colour of the edge pixel beside it."""
    def mask():
        return np.array([[q is not None for q in r] for r in out])

    def fill(y, x, f, t=False):
        if out[y][x] is None:
            out[y][x] = out[f][x] if t else out[y][f]

    def clear(y, x):
        out[y][x] = None
    lines.regularise(mask(), fill, clear)
    lines.regularise(mask().T, lambda y, x, f: fill(x, y, f, True), lambda y, x: clear(x, y))


def orphans(out, keep=()):
    """Rule 8 (the pixels in KEEP are left)."""
    ramp_of = {q: r for r in RAMPS.values() for q in r}
    for _ in range(3):
        changed = 0
        for y in range(H1):
            for x in range(W1):
                q = out[y][x]
                if q is None or (x, y) in keep:
                    continue
                nb = [out[y + dy][x + dx] if 0 <= x + dx < W1 and 0 <= y + dy < H1 else None for dx, dy in N8]
                if q == BLACK and None in nb:
                    continue                  # (the outline)
                nb = [c for c in nb if c is not None]
                if q in nb or not nb:
                    continue
                ramp = ramp_of.get(q, [q]); kin = [c for c in nb if c in ramp]
                if kin:
                    out[y][x] = min(kin, key=lambda c: (abs(ramp.index(c) - ramp.index(q)), -nb.count(c)))
                else:
                    out[y][x] = max(set(nb), key=nb.count)
                changed += 1
        if not changed:
            break
    return out


def crop(frames):
    """FRAMES cut to the box that holds all of them (keeps them aligned with each other)."""
    ys = [y for f in frames for y, r in enumerate(f) if any(q is not None for q in r)]
    xs = [x for f in frames for r in f for x, q in enumerate(r) if q is not None]
    return [[r[min(xs):max(xs) + 1] for r in f[min(ys):max(ys) + 1]] for f in frames]
