"""Ravager plate knight profiles, facing right in foot-aligned 40x32 cells."""
from pathlib import Path
import struct

import numpy as np
from PIL import Image

PICTURES = (3605, 3606)


# The original idle and four side walk frames are also used by the diagonal walks
# and by the final, non-combat step of a side attack.
PROFILE_FRAMES = (2, 8, 9, 10, 11)
PROFILE_ANCHOR = (11, 31)


def install_profiles(pic, frames, script):
    with Image.open(Path(__file__).with_name('knights') / 'profile.png') as sheet:
        if sheet.mode != 'P' or sheet.size != (200, 32):
            raise ValueError('Invalid indexed knight profile sheet')
        pixels = np.array(sheet, dtype=int)
    if pic == 3606:
        silver = [252, 251, 250, 249, 248, 246, 244, 242, 241]
        black = [239, 238, 238, 252, 251, 237, 250, 236, 235]
        table = np.arange(256)
        table[silver] = black
        pixels = table[pixels]
    pixels[pixels == 0] = -1
    for index, pose in zip(PROFILE_FRAMES, np.hsplit(pixels, 5), strict=True):
        frames[index] = pose

    out = bytearray(script)
    for at in range(72, len(out), 8):
        if not out[at + 2] & 0x20 and out[at] in PROFILE_FRAMES:
            out[at + 5:at + 7] = bytes(PROFILE_ANCHOR)
    # Each stride has a second contact beat before the passing pose.
    for slot in (7, 9, 15, 23, 25, 31):
        start, = struct.unpack_from('<H', out, slot * 2)
        for i, index in enumerate((8, 8, 9, 10, 10, 11)):
            out[72 + 8 * (start + i)] = index
    return bytes(out)


def attack_frames(pic):
    with Image.open(Path(__file__).with_name('knights') / f'{pic}.png') as sheet:
        if sheet.mode != 'P' or sheet.size != (160, 32):
            raise ValueError(f'Invalid indexed melee sheet for knight {pic}')
        pixels = np.array(sheet, dtype=int)
    pixels[pixels == 0] = -1
    return np.hsplit(pixels, 4)


def side_attacks(script, first_frame):
    """Append two melee sequences. Other slot offsets and their action flags stay intact."""
    out = bytearray(script)
    for slot, mirror in ((12, 0), (28, 4)):
        start, = struct.unpack_from('<H', script, 2 * slot)
        steps = script[72 + start * 8:]
        # Preserve the game's return-to-standing step, including its original anchor.
        end = next(i for i in range(0, len(steps), 8) if steps[i + 2] & 2)
        struct.pack_into('<H', out, 2 * slot, (len(out) - 72) // 8)
        for i in range(4):
            out.extend((first_frame + i, 0, 0x60 | mirror, 0, 0, 11, 31, 0))
        out.extend(steps[end:end + 8])
    return bytes(out)
