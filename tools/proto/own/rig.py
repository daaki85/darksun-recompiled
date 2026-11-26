"""The skeleton and the body on it: a pose (a dict of angles, poses.py) in, a list of balls out.

The rig is a small 2.5D one: joints chained by forward kinematics from authored angles, so one body
serves every facing (front, side, the walks) without being redrawn. Every body part is a sweep of
balls along its bone (radius tapering or swelling along it): limbs are tapered capsules, the trousers
balloon between the waist and the ankle cuffs, the torso is three rows of balls (shoulders, chest,
belly) so it is broad and flat, the hair a big mass of balls behind and above the head.

Beside the balls the body carries marks: lines and dots on its surface (the eye line, the sternum,
the line under the pectorals, a highlight on each pectoral and shoulder, the nose's light), drawn
crisp at 1x where they show (paint.py), since such details are smaller than the reduction keeps.

Units are game pixels at 1x. Body space: x the figure's own left, y up, z the way he faces.
"""
import math
from typing import NamedTuple
import numpy as np

# ---- the body's measures (game pixels) ----
SIZE = dict(
    hip_w=2.1,             # half the distance between the hip joints
    thigh=7.6, shin=7.6, ankle=1.1, foot=2.4,
    spine=7.0,             # pelvis to the line of the shoulders
    sh_w=4.6,              # half the distance between the shoulder joints
    upper=4.6, fore=4.6,
    neck=1.4, head_r=2.4,
    girth=0.8,             # how thick: every radius and sideways offset but the head's
    arm=0.86,              # the arms' thickness, on top of girth
    thigh_r=0.75,          # the trousers' thickness from the hip to the knee (round 7: slimmer, so the
    calf_r=0.85,           #   legs part as SL's man's do), and below the knee (the balloon)
)

# pose keys and their defaults (degrees; see poses.py for what each one does)
DEFAULT = dict(
    yaw=0, tilt=0, twist=0, roll=0,                  # the pelvis
    lean=12, spine_twist=0, bend=0,                   # the chest on the pelvis
    nod=-30, turn=0, cock=0,                          # the head on the chest (tipped up: the face shows)
    l_abd=28, l_fwd=10, l_elb=40, r_abd=28, r_fwd=10, r_elb=40,
    l_hip_abd=6, l_hip=12, l_knee=22, l_foot=0,
    r_hip_abd=6, r_hip=12, r_knee=22, r_foot=0,
    l_fist=1, r_fist=1,
)


def rx(a):
    a = math.radians(a); c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def ry(a):
    a = math.radians(a); c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rz(a):
    a = math.radians(a); c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


V = lambda *v: np.array(v, dtype=float)
DOWN = V(0, -1, 0)


def skeleton(pose):
    """Joint positions and frames for POSE (a dict over DEFAULT), in world space before grounding."""
    p = dict(DEFAULT, **pose); S = SIZE; J = {}
    yaw = ry(p['yaw'])
    # rx(+a) tips the up axis forward: tilt and lean are forward bends (of the pelvis, the chest)
    P = yaw @ rx(p['tilt']) @ ry(p['twist']) @ rz(p['roll'])
    J['pelvis'] = V(0, S['thigh'] + S['shin'] + S['ankle'], 0); J['P'] = P
    C = P @ rx(p['lean']) @ ry(p['spine_twist']) @ rz(p['bend'])
    J['C'] = C
    J['chest'] = J['pelvis'] + C @ V(0, S['spine'], 0)
    H = C @ rx(p['nod']) @ ry(p['turn']) @ rz(p['cock'])
    J['H'] = H
    J['neck'] = J['chest'] + C @ V(0, 0.2, 0.2)
    J['head'] = J['neck'] + H @ V(0, S['neck'] + S['head_r'] * 0.9, 1.0)
    for side, sg in (('l', 1), ('r', -1)):
        # arms: abduction out from the side, then a forward swing; the elbow bends forward
        sh = J['chest'] + C @ V(sg * S['sh_w'], -0.7, -0.2)
        U = C @ rz(sg * p[side + '_abd']) @ rx(-p[side + '_fwd'])
        el = sh + U @ (DOWN * S['upper'])
        F = U @ rx(-p[side + '_elb'])
        ha = el + F @ (DOWN * S['fore'])
        J[side + '_sh'], J[side + '_el'], J[side + '_ha'], J[side + 'U'], J[side + 'F'] = sh, el, ha, U, F
        # legs: abduction, then a forward swing at the hip; the knee bends back
        hp = J['pelvis'] + P @ V(sg * S['hip_w'], -0.6, 0)
        T = P @ rz(sg * p[side + '_hip_abd']) @ rx(-p[side + '_hip'])
        kn = hp + T @ (DOWN * S['thigh'])
        Sh = T @ rx(p[side + '_knee'])
        an = kn + Sh @ (DOWN * S['shin'])
        # the foot keeps to the ground's plane, turned out a little, tipped by *_foot (toe down +)
        Fo = yaw @ ry(sg * 12) @ rx(p[side + '_foot'])
        J[side + '_hip'], J[side + '_kn'], J[side + '_an'], J[side + 'T'], J[side + 'S'], J[side + 'Fo'] = \
            hp, kn, an, T, Sh, Fo
    J['pose'] = p
    return J


class Balls:
    """The body as balls: rows of (x, y, z, r, tone, material, part); TONE is added to the ball's light
    (the hair's locks alternate, so they read as clumps). And marks: (points, role, part), ROLE one of
    paint.MARK's."""
    def __init__(self):
        self.rows, self.marks = [], []

    def ball(self, c, r, mat, part, tone=0.0):
        self.rows.append((c[0], c[1], c[2], r, tone, mat, part))

    def sweep(self, path, mat, part, step=0.3, tone=0.0):
        """Balls along PATH, a list of (point, radius), the radius eased linearly between points."""
        for (a, ra), (b, rb) in zip(path, path[1:]):
            n = max(1, int(np.linalg.norm(b - a) / step))
            for i in range(n + 1):
                t = i / n
                self.ball(a + (b - a) * t, ra + (rb - ra) * t, mat, part, tone)

    def mark(self, points, role, part, mat='skin'):
        self.marks.append((np.array(points, dtype=float), role, part, mat))


class Body(NamedTuple):
    rows: np.ndarray        # balls: x, y, z, r, tone (grounded: the lowest point on y=0)
    mats: list
    parts: list
    marks: list             # (points N x 3, role, part, material), grounded the same way
    J: dict                 # the skeleton


def _hair():
    """The hair, on a head of radius 2.45 centred on the origin, as (path, tone) sweeps: a dark core
    behind and above the skull, and locks rooted over the crown and the back, each a tapered strand
    drooping back, with tones in turn so the lit side breaks into streaks. Three long locks break
    the outline. Nothing lies on the forehead or the face: the hairline sits above the brow, and
    side on the face and the front of the skull are clear."""
    core = [([(V(0, 0.8, -1.2), 2.3), (V(0, -0.2, -1.7), 1.9)], 0.0)]
    locks, k = [], 0
    centre = V(0, 0.7, -0.7)
    for el, n in ((66, 4), (32, 6), (-4, 6)):
        for i in range(n):
            az = 360 * i / n + 30 * (el < 0)
            e, a = math.radians(el), math.radians(az)
            d = V(math.cos(e) * math.sin(a), math.sin(e), math.cos(e) * math.cos(a))
            root = centre + d * V(2.4, 1.5, 2.1)
            if root[2] > -0.4:
                continue                                       # (the forehead and the face)
            long = k % 4 == 1                                  # (a lock that breaks the outline)
            tip = root + d * (2.4 if long else 1.2) + V(0, -0.8, -0.9)
            r0 = 1.6 if k % 2 else 1.35
            locks.append(([(root, r0), (tip, 0.7 if long else 0.75)], (0.5, -0.3, 0.25, -0.4)[k % 4]))
            k += 1
    return core + locks


HAIR = _hair()
FOLDS = (-55, 5, 60)             # the trouser folds' places round the leg (degrees, 0 to the front, + outward)


def _on(c, r, d):
    """The point on the ball (C, R) in direction D."""
    return c + r * d / np.linalg.norm(d)


def body(pose):
    """The jann in POSE as a Body. GIRTH scales every radius and sideways offset but the head's."""
    J = skeleton(pose); S = SIZE; B = Balls(); C, P, H = J['C'], J['P'], J['H']
    p, g = J['pose'], S['girth']
    a = g * S['arm']
    X = lambda x, y, z: V(x * g, y, z)                  # a body-space offset, its width scaled
    # torso: shoulders, chest, belly rows (broad, flat), pectorals, then the hips under the sash
    ch, pv = J['chest'], J['pelvis']
    B.sweep([(J['l_sh'] + C @ X(-0.4, 0.2, 0), 1.9 * g), (ch + C @ V(0, 0.3, -0.3), 2.1 * g),
             (J['r_sh'] + C @ X(0.4, 0.2, 0), 1.9 * g)], 'skin', 'torso')
    B.sweep([(ch + C @ X(3.2, -2.2, 0.1), 2.6 * g), (ch + C @ X(-3.2, -2.2, 0.1), 2.6 * g)], 'skin', 'torso')
    pecs = [(ch + C @ X(sg * 1.7, -2.1, 1.1), 1.9 * g) for sg in (1, -1)]
    for c, r in pecs:
        B.ball(c, r, 'skin', 'torso')
    B.sweep([(ch + C @ X(1.4, -5.0, 0.1), 2.0 * g), (ch + C @ X(-1.4, -5.0, 0.1), 2.0 * g)], 'skin', 'torso')
    for sg in (1, -1):              # the flanks: straight from the armpit to the sash (the V)
        B.sweep([(ch + C @ X(sg * 3.0, -1.8, 0), 2.2 * g), (ch + C @ X(sg * 1.5, -6.2, 0.1), 2.0 * g)],
                'skin', 'torso')
    belly = (ch + C @ V(0, -4.0, 0.8), 1.8 * g)
    B.ball(*belly, 'skin', 'torso')
    B.sweep([(pv + P @ X(1.5, 0.0, 0), 2.25 * g), (pv + P @ X(-1.5, 0.0, 0), 2.25 * g)], 'cloth', 'torso')
    B.sweep([(pv + P @ X(1.5, 1.2, 0.1), 2.45 * g), (pv + P @ X(-1.5, 1.2, 0.1), 2.45 * g)], 'sash', 'torso')
    # torso marks: the sternum, a light on each pectoral (a line under the pectorals and one down
    # the belly were tried: they don't read at 1x)
    fwd = C @ V(0, 0, 1)
    top = ch + C @ V(0, -0.9, 0); B.mark([_on(top, 1.6 * g + 0.5, fwd), _on(ch + C @ V(0, -3.0, 0), 2.2, fwd)],
                                         'dark', 'torso')
    for c, r in pecs:
        B.mark([_on(c, r, C @ V(0, 0.6, 1))], 'light', 'torso')
    # neck, head, face, hair (laid out on a head of radius 2.45, scaled by k)
    B.sweep([(J['neck'], 1.7 * g), (J['head'] + H @ V(0, -0.8, -0.3), 1.5)], 'skin', 'torso')   # neck
    hd, k = J['head'], S['head_r'] / 2.45
    B.ball(hd, S['head_r'], 'skin', 'head')
    for c, r in ((V(0.8, -1.2, 0.5), 1.05), (V(-0.8, -1.2, 0.5), 1.05), (V(0, -1.55, 1.0), 0.95)):
        B.ball(hd + H @ c * k, r * k, 'skin', 'head')                          # a square jaw and chin
    nose = hd + H @ V(0, -0.15, 2.05) * k
    B.ball(nose, 0.55 * k, 'skin', 'head')
    for path, tone in HAIR:
        B.sweep([(hd + H @ c * k, r * k) for c, r in path], 'hair', 'hair', tone=tone)
    face = lambda x, y: _on(hd, S['head_r'], H @ V(x, y, 2.1))
    B.mark([face(x, 0.25) for x in (-1.15, -0.6, 0, 0.6, 1.15)], 'dark', 'head')          # the eyes
    B.mark([_on(nose, 0.55 * k, H @ V(0, 0.3, 1))], 'light', 'head')
    # arms: deltoid (flat-topped: a short level run across the shoulder; its light), upper arm,
    # forearm (tapering straight), bracer, fist
    for side, sg in (('l', 1), ('r', -1)):
        sh, el, ha, U, F = (J[side + k] for k in ('_sh', '_el', '_ha', 'U', 'F'))
        part = 'arm_' + side
        delt = (sh + U @ V(0, -0.5, 0), 2.0 * a)
        B.sweep([(sh + C @ V(-sg * 0.7, 0.1, 0), 1.85 * a), (sh + C @ V(sg * 0.5, -0.1, 0), 1.85 * a)], 'skin', part)
        B.ball(*delt, 'skin', part)
        B.mark([_on(*delt, C @ V(0, 1, 0.5))], 'light', part)
        B.sweep([(sh, 1.9 * a), (sh + (el - sh) * 0.45, 2.0 * a), (el, 1.45 * a)], 'skin', part)
        B.sweep([(el, 1.6 * a), (ha, 1.1 * a)], 'skin', part)
        B.sweep([(el + (ha - el) * 0.86, 1.45 * a), (ha, 1.4 * a)], 'gold', part)
        B.ball(ha + F @ V(0, -1.0, 0.1), (1.8 if p[side + '_fist'] else 1.6) * a, 'skin', 'hand_' + side)
    # legs: trousers balloon from the hip to below the knee, gathered at the cuff, with folds (dark
    # wedges from the knee to the cuff, around the leg); short boots
    for side, sg in (('l', 1), ('r', -1)):
        hp, kn, an, Fo, Sh = (J[side + k] for k in ('_hip', '_kn', '_an', 'Fo', 'S'))
        part = 'leg_' + side
        cuff = an + (kn - an) * 0.16
        tr, cr = S['thigh_r'] * g, S['calf_r'] * g
        B.sweep([(hp, 2.0 * tr), (hp + (kn - hp) * 0.5, 1.95 * tr), (kn, 2.1 * (tr + cr) / 2),
                 (kn + (an - kn) * 0.5, 2.5 * cr), (cuff + (kn - an) * 0.1, 2.3 * cr), (cuff, 1.55 * g)],
                'cloth', part)
        r_at = lambda t: cr * (2.1 + 0.8 * t if t < 0.5 else 2.5 - 1.6 * (t - 0.5))     # (the sweep's radius)
        on = lambda t, th: kn + (cuff - kn) * t + Sh @ V(math.sin(math.radians(th)), 0,
                                                         math.cos(math.radians(th))) * r_at(t) * 0.95
        for th in FOLDS:
            th *= sg
            B.mark([on(t, th) for t in (0.05, 0.5, 0.92)], 'dark', part, 'cloth')
            B.mark([on(t, th + 14 * sg) for t in (0.5, 0.92)], 'black', part, 'cloth')     # (the wedge widens)
        B.sweep([(cuff, 1.15 * g), (an, 1.1 * g)], 'leather', part)
        heel = an + Fo @ V(0, -0.55, -0.4)
        toe = an + Fo @ V(0, -0.75, S['foot'])
        B.sweep([(heel, 0.95), (an + Fo @ V(0, -0.5, 0.8), 1.05), (toe, 0.85)], 'leather', part)
    rows = np.array([r[:5] for r in B.rows], dtype=float)
    lift = (rows[:, 1] - rows[:, 3]).min()
    rows[:, 1] -= lift
    marks = [(pts - V(0, lift, 0), role, part, mat) for pts, role, part, mat in B.marks]
    return Body(rows, [r[5] for r in B.rows], [r[6] for r in B.rows], marks, J)
