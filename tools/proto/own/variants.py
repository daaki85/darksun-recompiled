"""For the eye: the same frames under other skin ramps, side by side (WR colours, 8x).
    python3 variants.py OUT.png"""
import sys
import paint, sheet, people_dress as pd

SKINS = [[158, 159, 176, 177, 178], [158, 159, 160, 161], [158, 159, 177, 161], [158, 159, 176, 177, 161],
         [158, 159, 160, 161, 162]]


def main(out, names=('standing front', 'standing side', 'walk side 1')):
    keep = paint.RAMPS['skin']; ims = []
    for skin in SKINS:
        paint.RAMPS['skin'] = skin
        fr = dict(sheet.jann())
        ims.append(sheet.row([fr[n] for n in names], pd.WRPAL, pd.TABLE, 3))
    paint.RAMPS['skin'] = keep
    sheet.on_grey(pd.strip(ims, 10), 6).save(out); print(out)


if __name__ == '__main__':
    main(sys.argv[1])
