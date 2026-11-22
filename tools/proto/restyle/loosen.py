"""The looser stand and fuller walks of the restyled creatures, built into the game's files.
build(pic) gives the restyled BMP, CBMP and SCMD chunks of PIC (as restyle.restyle) with:
- a looser standing frame toward and away (walk6: arms out a pixel, forearms out and up, feet a
  pixel apart), shown on every step that ends a sequence on the standing frame: standing still and
  coming to rest after a move or an attack;
- for the figures that walk on two stride frames with the standing frame between them
  ('a S b S': the soulshard), the six-beat walk of walk6 (a, half, stride, b, half, stride), the
  cycle's movement spread over the six steps;
- for the golems (golem4: 'A B A B'), passing frames between the strides (A, P1, B, P2).
The new frames go after the picture's own; each step's anchor (bytes 5, 6) is the frame's own,
scaled as restyle.script does."""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..'), os.path.join(HERE, '..', '..'), os.path.join(HERE, '..', 'own')]
import numpy as np
import moves as L, restyle as R, walk6 as W6, golem4 as G4, sl_figures as s

# Codex's painted walks (figure_walks.py: the skeletons, umber hulk, verini, thief, soulshard) and
# knights (knight_melee.py) replace this for their figures: only the golems still use it.
LOOSE = [693, 2394]
END, COMBAT = 0x02, 0x20
# the verini seen from behind are mostly tail: moving their 'legs' breaks it, so that view keeps
# Ravager's stand
TOWARD_ONLY = {2850, 2852, 2853, 2854, 2855, 2858, 2859, 2860, 2861, 2863}

def sb(v):
    return v - 256 if v > 127 else v

def runs(steps):
    """[(start, [step indices])]: the runs of steps, each ending on a step flagged END."""
    out, cur = [], []
    for i, st in enumerate(steps):
        cur.append(i)
        if st[2] & END:
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out

def build(pic):
    walk = [[[None if q < 0 else int(q) for q in r] for r in np.asarray(f)]
            for f in R.restyle_frames(None, pic, False)]
    comb = R.restyle_frames(None, pic, True)
    sc = R.B[('SCMD', pic)]
    slots = list(struct.unpack_from('<36H', sc, 0))
    steps = [bytearray(x) for x in s.steps(R.script(sc))]          # anchors scaled
    frames = list(walk); idx = {}
    def add(key, f, anchor):
        idx[key] = (len(frames), anchor); frames.append(f)
    # the loosened stands (walk6's, made the same way for every figure here)
    for stand, tag in ((0, 'ST'), (1, 'SA')):
        if stand == 1 and pic in TOWARD_ONLY:
            continue
        rg = W6.regions(walk[stand]); a0, a1, l0, l1 = rg['armL'][0], rg['armL'][1], rg['legL'][0], rg['legL'][1]
        mid = (a0 + a1) // 2
        o = [(a0, a1, *rg['armL'][2:], -1, 0), (mid, a1, rg['armL'][2] - 1, rg['armL'][3] - 1, -1, -1),
             (a0, a1, *rg['armR'][2:], 1, 0), (mid, a1, rg['armR'][2] + 1, rg['armR'][3] + 1, 1, -1),
             (l0, l1, *rg['legL'][2:], -1, 0), (l0, l1, *rg['legR'][2:], 1, 0)]
        add(stand, L.apply(walk[stand], o), None)
    stand_anchor = {}
    for st in steps:
        if not st[2] & COMBAT and st[0] in (0, 1):
            stand_anchor.setdefault(st[0], (st[5], st[6]))
    for k in idx.copy():
        i, _ = idx[k]; ax, ay = stand_anchor[k]; idx[k] = (i, (ax + L.P, ay + L.P))
    lay = W6.layout(pic)
    six = {}
    if pic in G4.LAYOUT:
        lay = None; d, new, an = G4.make(pic)
        for tag in ('T', 'A'):
            st0, a, b = G4.LAYOUT[pic][tag]; ax, ay = stand_anchor[st0]
            for key in ('P1', 'P2'):
                add(tag + key, new[tag + 'P' + key[1]], (ax + L.P, ay + L.P))
    elif lay:
        d, new, an, fixed, lay = W6.make(pic)
        for stand, tag in ((0, 'T'), (1, 'A')):
            ax, ay = stand_anchor[stand]
            for key in ('A1', 'A', 'B1', 'B'):
                add(tag + key, new[tag + key], (ax + L.P, ay + L.P))
    out = []
    remap = {}
    for run in runs(steps):
        remap[run[0]] = len(out)
        rs = [bytearray(steps[i]) for i in run]
        fr = [x[0] for x in rs]; walking = not any(x[2] & COMBAT for x in rs)
        if walking and lay and len(rs) == 4 and fr[1] == fr[3] and fr[1] in lay and (fr[0], fr[2]) == lay[fr[1]]:
            tag = 'T' if fr[1] == 0 else 'A'
            dx = sum(sb(x[3]) for x in rs); dy = sum(sb(x[4]) for x in rs)
            seq = [(fr[0], None), (tag + 'A1', 0), (tag + 'A', 0), (fr[2], None), (tag + 'B1', 0), (tag + 'B', 0)]
            new_rs = []
            for j, (f, _) in enumerate(seq):
                base = bytearray(rs[0] if j < 3 else rs[2]) if isinstance(f, int) else bytearray(rs[1])
                if not isinstance(f, int):
                    base[0], (base[5], base[6]) = idx[f][0], idx[f][1]
                # the movement spread evenly, the remainder on the first steps
                base[3] = (dx * (j + 1) // 6 - dx * j // 6) & 255
                base[4] = (dy * (j + 1) // 6 - dy * j // 6) & 255
                base[2] &= ~END
                new_rs.append(base)
            new_rs[-1][2] |= END
            rs = new_rs
        elif walking and pic in G4.LAYOUT and len(rs) == 4:
            for tag in ('T', 'A'):
                st0, a, b = G4.LAYOUT[pic][tag]
                if fr == [a, b, a, b]:
                    # the strides with passing frames between them: A P1 B P2
                    rs[2][0], rs[2][5], rs[2][6] = b, rs[1][5], rs[1][6]
                    for j, key in ((1, 'P1'), (3, 'P2')):
                        rs[j][0], (rs[j][5], rs[j][6]) = idx[tag + key][0], idx[tag + key][1]
        # standing at the end of a sequence: the looser stand
        last = rs[-1]
        if not last[2] & COMBAT and last[0] in (0, 1) and last[0] in idx:
            i, (ax, ay) = idx[last[0]]
            last[0], last[5], last[6] = i, ax, ay
        out += rs
    for k, v in enumerate(slots):
        if v != 0xFFFF:
            assert v in remap, (pic, k, v)
            slots[k] = remap[v]
    assert len(frames) < 256
    script = struct.pack('<36H', *slots) + b''.join(bytes(x) for x in out)
    return {('BMP ', pic): s.picture(frames), ('CBMP', pic): R.chunk(comb), ('SCMD', pic): script}
