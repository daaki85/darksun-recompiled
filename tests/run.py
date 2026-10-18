#!/usr/bin/env python3
"""Scripted runs of the recompiled game, kept as regression tests.

Each test in tests/cases/*.toml names a script of keys and clicks on a
timeline, how long to run, and what must be true at the end: the screen must
have changed since a given second, a screenshot must be close to a reference
(tests/ref/<name>.png, written with --update), and the log must not report
misses, stack faults or unhandled calls.

    python3 tests/run.py             # every case
    python3 tests/run.py intro       # one
    python3 tests/run.py --update    # write the references from this run

Headless, so it runs in CI. The game's files are read from game/ds1 and the
program is build/cmake/dsun (or $DSUN).
"""
import argparse
import glob
import os
import subprocess
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DSUN = os.environ.get('DSUN', os.path.join(ROOT, 'build', 'cmake', 'dsun'))
# A case with `game = "ds2"` is Wake of the Ravager: its own program (built
# with -DGAME_BUILD=build/ds2 into build/cmake-ds2, or $DSUN2), data, and CD.
DSUN2 = os.environ.get('DSUN2', os.path.join(ROOT, 'build', 'cmake-ds2', 'dsun'))


def colours(path):
    from PIL import Image
    c = Image.open(path).getcolors(70000)
    return len(c) if c else 70000


def differs(a, b, tolerance):
    """Share of pixels that differ between two screenshots."""
    from PIL import Image, ImageChops
    ia, ib = Image.open(a).convert('RGB'), Image.open(b).convert('RGB')
    if ia.size != ib.size:
        return 1.0
    d = ImageChops.difference(ia, ib).convert('L').point(lambda v: 255 if v > 24 else 0)
    n = d.histogram()[255]
    return n / (ia.size[0] * ia.size[1])


def run_case(path, update):
    case = tomllib.load(open(path, 'rb'))
    name = os.path.splitext(os.path.basename(path))[0]
    shots = os.path.join(ROOT, 'build', 'tests', name)
    os.makedirs(shots, exist_ok=True)
    for f in glob.glob(os.path.join(shots, '*')):
        os.remove(f)
    cmd = [DSUN, '--headless', '--seconds', str(case['seconds']), '--shots', shots]
    if case.get('game') == 'ds2':
        cmd[0] = DSUN2
        cmd += ['--game', 'game/ds2', '--build', 'build/ds2', '--cd', 'game/ds2/cd']
    if case.get('input'):
        cmd += ['--input', case['input']]
    env = dict(os.environ, DS_QUIET='')
    log = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=case['seconds'] + 60).stderr
    open(os.path.join(shots, 'log.txt'), 'w').write(log)
    problems = []
    for bad in ('no function at', '[sp]', 'unhandled', 'fatal:', 'is not code'):
        n = log.count(bad)
        if n and bad not in case.get('allow', []):
            problems.append(f'{n} x "{bad}" in the log')
    for chk in case.get('screen', []):
        shot = os.path.join(shots, f'shot_{chk["at"]:03d}.bmp')
        if not os.path.exists(shot):
            problems.append(f'no screenshot at {chk["at"]} s')
            continue
        if 'min_colours' in chk and colours(shot) < chk['min_colours']:
            problems.append(f'{chk["at"]} s: {colours(shot)} colours, wanted {chk["min_colours"]}')
        if 'ref' in chk:
            ref = os.path.join(ROOT, 'tests', 'ref', f'{name}-{chk["ref"]}.png')
            if update:
                from PIL import Image
                os.makedirs(os.path.dirname(ref), exist_ok=True)
                Image.open(shot).save(ref)
            elif not os.path.exists(ref):
                problems.append(f'no reference {ref} (run with --update)')
            else:
                d = differs(shot, ref, 24)
                if d > chk.get('tolerance', 0.02):
                    problems.append(f'{chk["at"]} s: {d:.1%} of the screen differs from {os.path.basename(ref)}')
    return name, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('names', nargs='*')
    ap.add_argument('--update', action='store_true')
    a = ap.parse_args()
    cases = sorted(glob.glob(os.path.join(ROOT, 'tests', 'cases', '*.toml')))
    if a.names:
        cases = [c for c in cases if os.path.splitext(os.path.basename(c))[0] in a.names]
    failed = 0
    for c in cases:
        name, problems = run_case(c, a.update)
        print(f'{"FAIL" if problems else "ok  "} {name}')
        for p in problems:
            print(f'       {p}')
        failed += bool(problems)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
