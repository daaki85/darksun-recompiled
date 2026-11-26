"""Build picture 2424's single 27-pose bank using the dressed 2408 counterpart."""
import numpy as np
from PIL import Image

# 2424 interleaves the two original 2408 banks. These are the corresponding
# Shattered Lands poses in that order. A negative attack number mirrors it.
# The fallen pose and three bow poses have no equivalent on body 11.
POSES = (
    ('walk', 0), ('walk', 1), ('walk', 2),
    ('attack', 0), ('attack', 1), ('attack', 2),
    ('attack', 3), ('attack', 4), ('attack', 5),
    ('attack', 6), ('attack', 7), ('attack', 8),
    ('walk', 3), ('walk', 5), ('walk', 7), ('walk', 9),
    ('walk', 11), ('walk', 12), ('walk', 13), ('walk', 14),
    ('attack', -6), ('attack', -7), ('attack', -8),
    None, None, None, None,
)


def picture(walk, attack, original, encode):
    banks = {'walk': walk, 'attack': attack}
    output = []
    for source, pose in zip(original, POSES, strict=True):
        native = np.array([[-1 if q is None else q for q in row] for row in source], dtype='int32')
        height, width = native.shape
        if pose is None:
            # Keep the bow, string and fall silhouette at the counterpart's scale.
            size = (max(1, round(width * .82)), max(1, round(height * .82)))
            frame = np.asarray(Image.fromarray(native).resize(size, Image.Resampling.NEAREST))
        else:
            kind, index = pose
            frame = np.array([[-1 if q is None else q for q in row]
                              for row in banks[kind][abs(index)]], dtype='int32')
            if index < 0:
                frame = frame[:, ::-1].copy()
            # Map the native sash into the posed body, preserving its purple ramp.
            sash = np.where((native >= 149) & (native <= 151), native, -1)
            sash = np.asarray(Image.fromarray(sash).resize(frame.shape[::-1], Image.Resampling.NEAREST))
            cloth = (frame >= 0) & (sash >= 0)
            frame[cloth] = sash[cloth]

        h, w = frame.shape
        canvas = np.full((max(height, h), max(width, w)), -1, dtype=int)
        left = (canvas.shape[1] - w) // 2
        canvas[-h:, left:left + w] = frame
        output.append([[None if q < 0 else int(q) for q in row] for row in canvas])
    return encode(output)
