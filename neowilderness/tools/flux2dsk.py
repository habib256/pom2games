#!/usr/bin/env python3
"""flux2dsk.py: decode a WOZ2 or A2R2 image to a DOS-order .dsk.

Only standard 16-sector 6&2 tracks (D5 AA 96 / D5 AA AD) are decoded.
Every capture of a track is tried; sectors whose checksum fails are skipped.

Usage: flux2dsk.py IMAGE.{woz,a2r} OUT.dsk
"""
import sys

DOS_L2P = [0, 13, 11, 9, 7, 5, 3, 1, 14, 12, 10, 8, 6, 4, 2, 15]
WRITE = [0x96, 0x97, 0x9A, 0x9B, 0x9D, 0x9E, 0x9F, 0xA6, 0xA7, 0xAB, 0xAC, 0xAD,
         0xAE, 0xAF, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB9, 0xBA, 0xBB, 0xBC,
         0xBD, 0xBE, 0xBF, 0xCB, 0xCD, 0xCE, 0xCF, 0xD3, 0xD6, 0xD7, 0xD9, 0xDA,
         0xDB, 0xDC, 0xDD, 0xDE, 0xDF, 0xE5, 0xE6, 0xE7, 0xE9, 0xEA, 0xEB, 0xEC,
         0xED, 0xEE, 0xEF, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF9, 0xFA, 0xFB,
         0xFC, 0xFD, 0xFE, 0xFF]
READ = {n: i for i, n in enumerate(WRITE)}


def chunks(d, start):
    i = start
    while i + 8 <= len(d):
        n = int.from_bytes(d[i + 4:i + 8], 'little')
        yield d[i:i + 4], d[i + 8:i + 8 + n]
        i += 8 + n


def unpack(raw, nbits):
    return [(raw[k >> 3] >> (7 - (k & 7))) & 1 for k in range(nbits)]


def woz_tracks(d):
    c = dict(chunks(d, 12))
    tmap, trks = c[b'TMAP'], c[b'TRKS']
    for t in range(35):
        e = tmap[t * 4]
        if e == 0xFF:
            continue
        sb = int.from_bytes(trks[e * 8:e * 8 + 2], 'little')
        bc = int.from_bytes(trks[e * 8 + 4:e * 8 + 8], 'little')
        yield t, unpack(d[sb * 512:sb * 512 + (bc + 7) // 8], bc)


def a2r_tracks(d):
    strm = dict(chunks(d, 8))[b'STRM']
    i = 0
    while i < len(strm) and strm[i] != 0xFF:
        loc, kind = strm[i], strm[i + 1]
        n = int.from_bytes(strm[i + 2:i + 6], 'little')
        data = strm[i + 10:i + 10 + n]
        i += 10 + n
        if loc % 4 or kind not in (1, 3):
            continue
        bits, acc = [], 0
        for b in data:
            acc += b
            if b == 0xFF:
                continue
            cells = max(1, round(acc / 32))
            bits += [0] * (cells - 1) + [1]
            acc = 0
        yield loc // 4, bits


def nibbles(bits):
    out, sr = [], 0
    for x in bits:
        sr = (sr << 1 | x) & 0xFF
        if sr & 0x80:
            out.append(sr)
            sr = 0
    return out


def decode62(n):
    try:
        v = [READ[x] for x in n[:343]]
    except KeyError:
        return None
    acc, buf = 0, []
    for x in v:
        acc ^= x
        buf.append(acc)
    if buf[342] != 0:
        return None
    aux, main = buf[:86], buf[86:342]
    out = bytearray(256)
    for k in range(256):
        a = aux[k % 86] >> (2 * (k // 86))
        out[k] = (main[k] << 2) | ((a & 1) << 1) | ((a >> 1) & 1)
    return bytes(out)


def sectors(bits):
    n = nibbles(bits + bits[:4000])  # wrap so a sector split at the index decodes
    for k in range(len(n) - 360):
        if n[k:k + 3] != [0xD5, 0xAA, 0x96]:
            continue
        f = [((n[k + 3 + 2 * j] << 1) | 1) & n[k + 4 + 2 * j] for j in range(4)]
        vol, trk, sec, chk = f
        if vol ^ trk ^ sec != chk or sec > 15:
            continue
        for m in range(k + 11, k + 60):
            if n[m:m + 3] == [0xD5, 0xAA, 0xAD]:
                data = decode62(n[m + 3:m + 346])
                if data:
                    yield trk, sec, data
                break


def main():
    src, dst = sys.argv[1:3]
    d = open(src, 'rb').read()
    tracks = woz_tracks(d) if d[:4] == b'WOZ2' else a2r_tracks(d)
    img = bytearray(35 * 16 * 256)
    got = {}
    for t, bits in tracks:
        for trk, sec, data in sectors(bits):
            if trk != t:
                continue
            got.setdefault(t, set()).add(sec)
            o = (t * 16 + DOS_L2P.index(sec)) * 256
            img[o:o + 256] = data
    open(dst, 'wb').write(img)
    for t in range(35):
        s = got.get(t, set())
        if len(s) != 16:
            print(f'track {t:2d}: {len(s)}/16 sectors', file=sys.stderr)
    print(f'{sum(len(s) for s in got.values())}/560 sectors -> {dst}')


if __name__ == '__main__':
    main()
