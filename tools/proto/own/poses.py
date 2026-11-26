"""The test's poses, as angles over rig.DEFAULT (degrees).

What the keys do (body space: the figure's own left and right):
  yaw            which way he faces: 0 toward the viewer, 90 to the right (the side frames use a little
                 less, so a sliver of chest shows, as SL's side frames do)
  tilt, twist,   the pelvis tipped forward, turned, tipped sideways
  roll
  lean, bend,    the chest bent forward on the pelvis, sideways, turned
  spine_twist
  nod, turn, cock  the head on the chest
  *_abd, *_fwd   an arm out from the side, swung forward (negative: back); *_elb the elbow's bend
  *_hip_abd      a leg out from the side; *_hip swung forward; *_knee the knee's bend; *_foot the
                 toe tipped down
"""

SIDE_YAW = 68
SIDE_LOOK = -24                  # the head turned toward the viewer in side frames: the face shows

STAND = dict(lean=10, twist=-6,
             l_abd=52, l_fwd=14, l_elb=66, r_abd=48, r_fwd=8, r_elb=58,
             l_hip_abd=17, l_hip=14, l_knee=26, r_hip_abd=17, r_hip=4, r_knee=20)

# one stride: the legs and arms of frame k; frames 2 and 3 are 0 and 1 with the sides swapped
STRIDE = [
    # contact: left heel strikes ahead, right leg trails on its toe; the arms swing against the legs
    dict(l_hip=22, l_knee=12, l_foot=-10, r_hip=-14, r_knee=22, r_foot=20,
         l_fwd=-36, l_elb=36, r_fwd=40, r_elb=60, twist=-8, spine_twist=10, lean=28, roll=-3),
    # passing: the left leg carries the weight, the right swings through, knee high
    dict(l_hip=4, l_knee=16, l_foot=0, r_hip=26, r_knee=58, r_foot=18,
         l_fwd=-14, l_elb=40, r_fwd=38, r_elb=62, twist=-3, spine_twist=4, lean=26, roll=3),
]


def mirror(p):
    """P with the figure's left and right swapped (twists and rolls change sign)."""
    out = {}
    for k, v in p.items():
        if k[:2] in ('l_', 'r_'):
            out[('r_' if k[0] == 'l' else 'l_') + k[2:]] = v
        elif k in ('twist', 'spine_twist', 'roll', 'bend', 'turn', 'cock'):
            out[k] = -v
        else:
            out[k] = v
    return out


def walk(yaw, legs_out=6, stride=1.0, lift=1.0, look=0, arms_out=30, lean=None):
    """The four walking frames facing YAW: legs LEGS_OUT degrees apart and arms ARMS_OUT out from the
    sides (seen side on, arms held out read as one arm ahead and one behind), the swing scaled by STRIDE and
    the knees' bend by LIFT (toward the viewer both are kept small, so the feet stay near one row
    and the figure's height steady); the head turned back against the hips and chest, so it looks
    where he goes, then turned LOOK more (toward the viewer: negative). LEAN, if given, replaces the
    stride's own lean (toward the viewer a deep lean hides the face)."""
    base = dict(STAND, l_hip_abd=legs_out, r_hip_abd=legs_out, l_abd=arms_out, r_abd=arms_out)
    out = []
    for f in STRIDE + [mirror(f) for f in STRIDE]:
        f = dict(f, **{k: f[k] * stride for k in ('l_hip', 'r_hip') if k in f})
        f = dict(f, **{k: f[k] * lift for k in ('l_knee', 'r_knee') if k in f})
        if lean is not None:
            f = dict(f, lean=lean)
        out.append(dict(base, yaw=yaw, turn=look - f.get('twist', 0) - f.get('spine_twist', 0), **f))
    return out


# the attack, to the side: a lunge, the near (right) fist driven forward, the far arm drawn back
ATTACK = dict(yaw=SIDE_YAW, lean=22, spine_twist=24, twist=10, turn=SIDE_LOOK - 34,
              r_abd=8, r_fwd=88, r_elb=6, l_abd=20, l_fwd=-36, l_elb=80,
              l_hip=44, l_knee=40, l_foot=-6, r_hip=-26, r_knee=14, r_foot=26)

# side on, the far (left) foot ahead and the near one back, as SL's men stand
STAND_SIDE = dict(STAND, yaw=SIDE_YAW, l_hip=24, l_knee=28, r_hip=-8, r_knee=24, r_foot=8, lean=18,
                  l_hip_abd=-4, r_hip_abd=-4,
                  l_abd=14, l_fwd=12, l_elb=40, r_abd=10, r_fwd=22, r_elb=64, turn=SIDE_LOOK + 6)

FRAMES = ([('standing front', dict(STAND, yaw=0)), ('standing side', STAND_SIDE)]
          + [(f'walk side {k + 1}', p) for k, p in enumerate(walk(SIDE_YAW, legs_out=-4, look=SIDE_LOOK, arms_out=12))]
          + [(f'walk front {k + 1}', p) for k, p in enumerate(walk(0, legs_out=13, stride=0.35, lift=0.8, lean=14))]
          + [('attack side', ATTACK)])
