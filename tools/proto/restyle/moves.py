"""Move rectangles of a frame's pixels: ops (y0, y1, x0, x1, dx, dy) on a copy padded by P; the moved
pixels leave clear behind them unless something else lands there."""
P = 3
def pad(f):
    W = len(f[0]) + 2 * P
    return [[None] * W for _ in range(P)] + [[None] * P + r + [None] * P for r in f] + [[None] * W for _ in range(P)]
def apply(f, ops):
    g = pad(f)
    for y0, y1, x0, x1, dx, dy in ops:
        pts = [(y + P, x + P, g[y + P][x + P]) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if g[y + P][x + P] is not None]
        for y, x, q in pts: g[y][x] = None
        for y, x, q in pts: g[y + dy][x + dx] = q
    return g

def fill_holes(g):
    """A clear pixel with filled pixels above and below (left by a moved part) takes the one above."""
    for _ in range(2):
        for y in range(1, len(g) - 1):
            for x in range(len(g[0])):
                if g[y][x] is None and g[y - 1][x] is not None and any(
                        y + k < len(g) and g[y + k][x] is not None for k in (1, 2)):
                    g[y][x] = g[y - 1][x]
    return g

def crop(f):
    ys = [y for y, r in enumerate(f) if any(q is not None for q in r)]
    xs = [x for r in f for x, q in enumerate(r) if q is not None]
    return [r[min(xs):max(xs) + 1] for r in f[min(ys):max(ys) + 1]]

def low(f, x0, x1):
    """The lowest filled row in columns X0..X1."""
    return max(y for y, r in enumerate(f) for x, q in enumerate(r) if q is not None and x0 <= x <= x1)

def lean(f, by=3, hip=0.55):
    """F with its upper body leaned forward (to the right) BY pixels at the crown, nothing below the
    hips (HIP of the height from the top) moved: SL's profiles walk with the head ahead of the hips.
    Padded by P, as apply."""
    g = pad(f)
    ys = [y for y, r in enumerate(g) if any(q is not None for q in r)]; top, bot = min(ys), max(ys)
    h = top + round(hip * (bot - top + 1))
    for y in range(top, h):
        k = round(by * (h - y) / (h - top))
        if k:
            g[y] = [None] * k + g[y][:-k]
    return g
