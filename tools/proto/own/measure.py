"""How dark a figure is after conversion to WR colours: the share of its pixels near-black (L < 15)
and black (L < 10). Ours (the frames json) beside SL's party man's frames 0, 2 and 11.
    python3 measure.py FRAMES.json [FRAMES.json ...]"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import people_dress as pd

NAMES = ('standing front', 'standing side', 'walk side 1')


def shares(f, conv=None):
    px = [conv[q] if conv else q for r in f for q in r if q is not None]
    L = [pd.s._lab(pd.WRPAL[q])[0] for q in px]
    return sum(l < 15 for l in L) / len(L), sum(l < 10 for l in L) / len(L)


def main(paths):
    for path in paths:
        d = json.load(open(path))
        for n in NAMES:
            a, b = shares(d[n], pd.TABLE)
            print(f'{os.path.basename(path)} {n:15s} L<15 {a:.2f}  L<10 {b:.2f}')
    walk = pd.body(300)[0]
    for k in (0, 2, 11):
        a, b = shares(walk[k], pd.TABLE)
        print(f'SL man frame {k:2d}             L<15 {a:.2f}  L<10 {b:.2f}')


if __name__ == '__main__':
    main(sys.argv[1:])
