#!/usr/bin/env python3
"""Extract a GOG CD image (game.gog: one raw MODE2/2352 data track) to a folder.

Each 2,352-byte sector carries 2,048 bytes of data at offset 24 (12 sync, 4
header, 8 subheader). The data sectors make a plain ISO 9660 image, which 7z
unpacks.    python3 tools/cd_extract.py game/ds2/game.gog game/ds2/cd
"""
import os
import subprocess
import sys


def main():
    src, out = sys.argv[1], sys.argv[2]
    iso = os.path.join(os.path.dirname(out) or '.', 'cd.iso')
    with open(src, 'rb') as f, open(iso, 'wb') as o:
        n = 0
        while True:
            s = f.read(2352)
            if len(s) < 2352:
                break
            o.write(s[24:24 + 2048])
            n += 1
    print(f'{n} sectors -> {iso}')
    os.makedirs(out, exist_ok=True)
    subprocess.run(['7z', 'x', '-y', f'-o{out}', iso], check=True, stdout=subprocess.DEVNULL)
    os.remove(iso)
    print(f'extracted to {out}')


if __name__ == '__main__':
    main()
