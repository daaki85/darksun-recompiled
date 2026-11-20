"""Clean pixel-art edges: a region's edges redrawn as straights and regular steps.

An edge is followed row by row (a left or right edge) or, on the transposed grid, column by column
(a top or bottom edge). Where it climbs steeply its x keeps for a run of rows and then moves one
pixel; the runs' lengths are its steps. A clean line has all its steps alike: 1 (1:1), 2 (1:2) or
3 (1:3); 4 and more is a straight with a jog. So within each staircase (a stretch of steps all
under 4, all leaning one way) the inner steps are made equal (their mean, rounded) and the last
step takes up the difference, the first left as it is; the shallow lines (2:1, 3:1) are the same staircases seen on the transposed
grid. A staircase of fewer than MIN_STEPS steps is left alone, so small features (a hand, the eye
line, a lock of hair) keep their shape, and an edge moves at most one pixel in any row.
"""
import numpy as np

MIN_STEPS = 2          # inner steps a staircase needs before it is regularised


def _runs(row):
    """(start, end) of each run of True in ROW, end exclusive."""
    out, x, n = [], 0, len(row)
    while x < n:
        if row[x]:
            a = x
            while x < n and row[x]:
                x += 1
            out.append((a, x))
        x += 1
    return out


def _chains(mask, side):
    """The left (side 0) or right (side 1) edges of MASK's runs, linked row to row into chains of
    (y, x): x the run's first pixel (left) or last (right)."""
    chains, open_ = [], {}
    for y, row in enumerate(mask):
        nxt = {}
        for a, b in _runs(row):
            link = next((k for k in open_ if k[0] < b and a < k[1]), None)
            ch = open_.pop(link) if link is not None else []
            ch.append((y, a if side == 0 else b - 1))
            nxt[(a, b)] = ch
        chains += open_.values()
        open_ = nxt
    chains += open_.values()
    return [c for c in chains if len(c) > 2]


def _regular(xs):
    """XS (an edge's x row by row) with each staircase's inner steps made equal."""
    xs = list(xs); N = len(xs)
    i = 0
    while i < N - 1:
        # a staircase: x never moves more than 1 a row, and always the same way
        sgn = 0; j = i
        while j < N - 1 and abs(xs[j + 1] - xs[j]) <= 1 and (xs[j + 1] - xs[j]) * sgn >= 0:
            if xs[j + 1] != xs[j]:
                sgn = xs[j + 1] - xs[j]
            j += 1
        if sgn:
            # its steps: lengths of the runs of equal x
            steps, k = [], i
            while k <= j:
                m = k
                while m + 1 <= j and xs[m + 1] == xs[k]:
                    m += 1
                steps.append((k, m - k + 1)); k = m + 1
            inner, last = steps[1:-1], steps[-1]
            if len(inner) >= MIN_STEPS and all(L < 4 for _, L in inner) and len({L for _, L in inner}) > 1:
                n = len(inner); total = sum(L for _, L in inner)
                span = total + last[1]                     # (the inner steps and the last one)
                fits = [T for T in (1, 2, 3) if n * T < span]       # (the last step keeps a row)
                T = min(fits, key=lambda T: abs(T - total / n)) if fits else 0
                if T:
                    y0 = inner[0][0]; x0 = xs[y0]
                    for t in range(span):
                        want = x0 + sgn * min(t // T, n)
                        if abs(want - xs[y0 + t]) <= 1:
                            xs[y0 + t] = want
        i = max(j, i + 1)
    return xs


def staircases(xs):
    """XS's staircases, each as its list of inner steps (lengths)."""
    out, n, i = [], len(xs), 0
    while i < n - 1:
        sgn = 0; j = i
        while j < n - 1 and abs(xs[j + 1] - xs[j]) <= 1 and (xs[j + 1] - xs[j]) * sgn >= 0:
            if xs[j + 1] != xs[j]:
                sgn = xs[j + 1] - xs[j]
            j += 1
        if sgn:
            steps, k = [], i
            while k <= j:
                m = k
                while m + 1 <= j and xs[m + 1] == xs[k]:
                    m += 1
                steps.append(m - k + 1); k = m + 1
            out.append(steps[1:-1])
        i = max(j, i + 1)
    return out


def irregular(mask):
    """How many of MASK's staircases (both ways round, MIN_STEPS inner steps or more) are uneven."""
    n = 0
    for grid in (mask, mask.T):
        for side in (0, 1):
            for ch in _chains(grid, side):
                n += sum(1 for st in staircases([x for _, x in ch])
                         if len(st) >= MIN_STEPS and all(L < 4 for L in st) and len(set(st)) > 1)
    return n


def regularise(mask, fill, clear):
    """Redraw MASK's edges clean (both ways round). FILL(y, x, from_x) is called for a pixel the
    region gains (FROM_X the edge pixel beside it in that row), CLEAR(y, x) for one it loses. Both
    work on the caller's grids; MASK is recomputed by the caller between the two passes."""
    for side in (0, 1):
        for ch in _chains(mask, side):
            ys = [y for y, _ in ch]; old = [x for _, x in ch]
            new = _regular(old)
            for y, a, b in zip(ys, old, new):
                if a == b:
                    continue
                outward = (b < a) if side == 0 else (b > a)
                if outward:
                    fill(y, b, a)
                else:
                    clear(y, a)
