#!/usr/bin/env python3
"""pcrecomp's difftest16 over the built image: every distinct instruction,
lifted alone, against Unicorn, for each code segment (or one range).

    python3 tools/difftest.py build/ds1              # every code segment
    python3 tools/difftest.py build/ds1 0x8100 0x8000

The upstream script hashes guest memory in an `unsigned long`, 32 bits where
it was written and 64 here, so its C template is patched in memory first.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsimage                                   # noqa: E402  (pcrecomp paths)
import difftest16                                # noqa: E402

difftest16.TAIL = (difftest16.TAIL
                   .replace('unsigned long crc = 0;', 'unsigned int crc = 0;')
                   .replace('unsigned long w = *(uint32_t *)(g_mem + i);', 'unsigned int w = *(uint32_t *)(g_mem + i);')
                   .replace('crc = crc * 16777619ul ^ w;', 'crc = crc * 16777619u ^ w;')
                   .replace('%08lX', '%08X'))


def main():
    build = sys.argv[1] if len(sys.argv) > 1 else 'build/ds1'
    img = os.path.join(build, 'image.bin')
    if len(sys.argv) > 3:
        ranges = [(int(sys.argv[2], 0), int(sys.argv[3], 0))]
    else:
        lay = json.load(open(os.path.join(build, 'layout.json')))
        ranges = [(s['seg'] * 16, s['size']) for s in sorted(lay['code_segments'], key=lambda s: s['seg']) if s['size'] > 64]
    for off, ln in ranges:
        print(f'=== {off:05X} +{ln:X}', flush=True)
        sys.argv = ['difftest16', '--raw', img, '--offset', str(off), '--length', str(ln), '--vectors', '2']
        try:
            difftest16.main()
        except SystemExit as e:
            if e.code not in (0, None):
                print(f'(exit {e.code})')


if __name__ == '__main__':
    main()
