"""Ravager walk cycles. Indexed sheets are foot-aligned, with the profile facing right."""
from pathlib import Path
import struct

import numpy as np
from PIL import Image


VERINI = (2850, 2852, 2853, 2854, 2855, 2858, 2859, 2860, 2861, 2863)
DEPTH_WALKS = (2411, 2539)
PICTURES = (1753, 1754, 2555) + DEPTH_WALKS + VERINI
SIDE_SLOTS = (7, 9, 15, 23, 25, 31)


def sequence(script, slot):
    start, = struct.unpack_from('<H', script, slot * 2)
    steps = []
    for at in range(72 + 8 * start, len(script), 8):
        step = script[at:at + 8]
        steps.append(step)
        if step[2] & 2:
            return steps
    raise ValueError(f'No final step in walk slot {slot}')


def verini_palette(pic, tan, variant):
    """Match the tan pixels to the same positions in a shipped colour variant."""
    counts = np.zeros((256, 256), dtype=int)
    for src, dst in zip(tan, variant, strict=True):
        mask = src >= 0
        if not np.array_equal(mask, dst >= 0):
            raise ValueError('Verini palette source has a different silhouette')
        np.add.at(counts, (src[mask], dst[mask]), 1)
    palette = counts.argmax(axis=1)
    # Give the brow and near shoulder a separate highlight on the two darkest hides.
    if pic == 2853:
        palette[[196, 205, 204]] = [180, 179, 178]
    elif pic == 2863:
        palette[[196, 205, 204]] = [217, 216, 214]
    return palette


def painted_poses(pic, palette):
    sheet_id = 2850 if pic in VERINI else pic
    with Image.open(Path(__file__).with_name('walks') / f'{sheet_id}.png') as sheet:
        if sheet.mode != 'P' or sheet.size != (288, 52 if pic in DEPTH_WALKS else 156):
            raise ValueError(f'Invalid walk sheet {sheet_id}')
        pixels = np.asarray(sheet, dtype=int)
    poses = {}
    rows = ('side',) if pic in DEPTH_WALKS else ('toward', 'side', 'away')
    for name, row in zip(rows, np.vsplit(pixels, len(rows)), strict=True):
        poses[name] = []
        for cell in np.hsplit(row, 4):
            y, x = np.where(cell != 0)
            crop = cell[y.min():y.max() + 1, x.min():x.max() + 1]
            frame = np.where(crop == 0, -1, palette[crop] if palette is not None else crop)
            baseline = 44 if pic in DEPTH_WALKS else 48
            poses[name].append((frame, (36 - x.min(), baseline - y.min())))
    return poses


def depth_poses(frames, anchors, script):
    from walk6 import make_from_frames

    original = [[[None if q < 0 else int(q) for q in row] for row in frame] for frame in frames]
    layout = {}
    for stand, slot in ((0, 17), (1, 1)):
        lift_a, _, lift_b, _ = sequence(script, slot)
        layout[stand] = (lift_a[0], lift_b[0])
    _, new, _, fixed, _ = make_from_frames(original, anchors, 2, layout)
    poses = {}
    for stand, name, tag in ((0, 'toward', 'T'), (1, 'away', 'A')):
        a, b = layout[stand]
        poses[name] = []
        for key in (a, tag + 'A1', tag + 'A', b, tag + 'B1', tag + 'B'):
            frame = frames[key] if isinstance(key, int) else np.array(
                [[-1 if q is None else q for q in row] for row in new[key]])
            poses[name].append((frame, fixed[key]))
    return poses


def six_depth_steps(steps):
    """Split each half-stride into three beats while retaining its total signed displacement."""
    expanded = []
    for lift, contact in (steps[:2], steps[2:]):
        mid = bytearray(contact)
        mid[1] = 0
        mid[2] &= ~2
        half = [bytearray(lift), mid, bytearray(contact)]
        for axis in (3, 4):
            total = sum(int.from_bytes(st[axis:axis+1], 'little', signed=True) for st in (lift, contact))
            for i, st in enumerate(half):
                st[axis] = (round(total * (i + 1) / 3) - round(total * i / 3)) & 255
        expanded.extend(half)
    return expanded


def install(pic, frames, script, anchors, palette=None):
    poses = painted_poses(pic, palette)
    if pic in DEPTH_WALKS:
        poses.update(depth_poses(frames, anchors, script))
    refs = {}
    for name, cycle in poses.items():
        refs[name] = []
        for frame, anchor in cycle:
            refs[name].append((len(frames), anchor))
            frames.append(frame)

    out = bytearray(script)
    if pic == 2539:
        # Side idle and the last step of side melee share non-combat frame 2.
        with Image.open(Path(__file__).with_name('walks') / '2539-standing.png') as sheet:
            standing = np.array(sheet, dtype=int)
        frames[2] = np.where(standing == 0, -1, standing)
        for at in range(72, len(out), 8):
            if out[at] == 2 and not out[at + 2] & 0x20:
                out[at + 5:at + 7] = bytes((standing.shape[1] // 2 - 1, standing.shape[0] - 1))
    for slot in (1, 17, *SIDE_SLOTS):
        name = {1: 'away', 17: 'toward'}.get(slot, 'side')
        steps = sequence(script, slot)
        cycle = refs[name]
        if len(cycle) == 6:
            steps = six_depth_steps(steps)
        # Hold the two contacts in a six-beat cycle, or the first in the hulk's five.
        order = {(4, 6): (0, 0, 1, 2, 2, 3), (4, 5): (0, 0, 1, 2, 3)}.get(
            (len(cycle), len(steps)), range(len(cycle)))
        struct.pack_into('<H', out, slot * 2, (len(out) - 72) // 8)
        for source, index in zip(steps, order, strict=True):
            step = bytearray(source)
            step[0], (step[5], step[6]) = cycle[index]
            step[2] = (step[2] & ~4) | (4 if slot in (23, 25, 31) else 0)
            out.extend(step)
    return bytes(out)
