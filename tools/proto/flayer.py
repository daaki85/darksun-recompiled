"""A mind flayer's face tentacles, drawn on a dressed figure (people_dress.py's "tentacles": RAMP).

The figure's face is the lighter half of the skin RAMP in the head's rows (the top HEAD rows that
hold any of it; hands lower down are left alone). Below the face's lowest row, every face column
gets a strand hanging down over the chest: alternate columns 3 and 2 pixels long, the ramp's middle
shade with its darkest at the tip, only over the figure (never outside its outline). Frames that
show no face (the back view, the hood turned away) get nothing."""

HEAD = 12


def tentacles(frames, ramp):
    light = set(ramp[len(ramp) // 2:])
    mid, dark = ramp[len(ramp) * 2 // 3], ramp[1]
    out = []
    for f in frames:
        f = [r[:] for r in f]
        rows = [y for y, r in enumerate(f) if any(q is not None for q in r)]
        if not rows:
            out.append(f); continue
        top = rows[0]
        face = [(y, x) for y in range(top, min(top + HEAD, len(f))) for x, q in enumerate(f[y]) if q in light]
        if len(face) >= 3:
            low = max(y for y, _ in face)
            cols = sorted({x for y, x in face if y >= low - 1})
            for k, x in enumerate(cols):
                n = 3 if k % 2 == 0 else 2
                for i in range(1, n + 1):
                    y = low + i
                    if y < len(f) and f[y][x] is not None:
                        f[y][x] = dark if i == n else mid
        out.append(f)
    return out
