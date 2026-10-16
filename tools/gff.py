"""Read SSI GFF archives (the layout OpenDS documents in docs/file-formats.md)."""
import struct


def chunks(path):
    """{(fourcc, id): (offset, length)} for every chunk in a GFF file."""
    d = open(path, 'rb').read()
    if d[:4] != b'GFFI':
        raise ValueError(f'{path}: not a GFF')
    toc = struct.unpack_from('<I', d, 12)[0]
    types_off = struct.unpack_from('<I', d, toc)[0]
    p = toc + types_off
    ntypes = struct.unpack_from('<H', d, p)[0]; p += 2
    out, gffi, segmented = {}, [], []
    for _ in range(ntypes):
        fourcc = d[p:p + 4].decode('latin1'); cnt = struct.unpack_from('<I', d, p + 4)[0]; p += 8
        if cnt & 0x80000000:
            _segc, loc, nruns = struct.unpack_from('<iiI', d, p); p += 12
            runs = [struct.unpack_from('<ii', d, p + 8 * i) for i in range(nruns)]; p += 8 * nruns
            segmented.append((fourcc, loc, runs))
            continue
        for i in range(cnt):
            cid, off, ln = struct.unpack_from('<iII', d, p); p += 12
            out[(fourcc, cid)] = (off, ln)
            if fourcc == 'GFFI':
                gffi.append((off, ln))
    for fourcc, loc, runs in segmented:
        off, _ = gffi[loc]
        n = struct.unpack_from('<I', d, off)[0]
        ids = [first + k for first, num in runs for k in range(num)]
        for i in range(n):
            o, ln = struct.unpack_from('<II', d, off + 4 + 8 * i)
            out[(fourcc, ids[i])] = (o, ln)
    return out


def read(path, fourcc, cid):
    off, ln = chunks(path)[(fourcc, cid)]
    with open(path, 'rb') as f:
        f.seek(off)
        return f.read(ln)
