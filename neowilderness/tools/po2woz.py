#!/usr/bin/env python3
"""po2woz.py: a 140 KB ProDOS-order image (.po) as a WOZ 2 disk, optionally
write-protected.

Usage: po2woz.py IN.po OUT.woz [--write-protected]

POM2 (a2shot) honours the INFO write-protect flag of a WOZ image: ProDOS then
returns $2B on a WRITE, as with a covered notch. tests/test_hof.py uses it
for the hall of fame's write-protected disk. Tracks are standard 16-sector
6-and-2 encodings (volume 254, 10-bit self-sync gaps), physical sectors
mapped from ProDOS order.
"""
import argparse, struct, zlib
from pathlib import Path


WRITE = bytes.fromhex('96979A9B9D9E9FA6A7ABACADAEAFB2B3B4B5B6B7B9BABBBCBDBEBFCBCDCECFD3D6D7D9DADBDCDDDEDFE5E6E7E9EAEBECEDEEEFF2F3F4F5F6F7F9FAFBFCFDFEFF')
PO_TO_PHYS = [0, 2, 4, 6, 8, 10, 12, 14, 1, 3, 5, 7, 9, 11, 13, 15]


def enc62(data):
    aux = []
    for i in range(86):
        v = 0
        for j, idx in enumerate((i, i + 86, i + 172)):
            if idx < 256:
                b = data[idx]
                v |= (((b & 1) << 1) | ((b >> 1) & 1)) << (2 * j)
        aux.append(v)
    buf = aux + [b >> 2 for b in data]
    out, prev = [], 0
    for v in buf:
        out.append(WRITE[v ^ prev]); prev = v
    out.append(WRITE[prev])
    return bytes(out)


def fourfour(v):
    return bytes(((v >> 1) | 0xAA, v | 0xAA))


def track_bits(po, t, vol=254):
    bits = []
    def byte(b): bits.extend((b >> (7 - k)) & 1 for k in range(8))
    def sync(n):
        for _ in range(n): byte(0xFF); bits.extend((0, 0))
    sectors = {}
    for ls in range(16):
        sectors[PO_TO_PHYS[ls]] = po[t * 4096 + ls * 256:t * 4096 + ls * 256 + 256]
    sync(40)
    for ps in range(16):
        for b in b'\xD5\xAA\x96' + fourfour(vol) + fourfour(t) + fourfour(ps) + fourfour(vol ^ t ^ ps) + b'\xDE\xAA\xEB':
            byte(b)
        sync(6)
        for b in b'\xD5\xAA\xAD' + enc62(sectors[ps]) + b'\xDE\xAA\xEB':
            byte(b)
        sync(16)
    return bits


def po_to_woz(po, write_protected=True):
    assert len(po) == 143360, 'a 280-block volume'
    tracks = [track_bits(po, t) for t in range(35)]
    blocks_per_track = max((len(b) + 4095) // 4096 for b in tracks)
    info = bytearray(60)
    info[0] = 2; info[1] = 1; info[2] = 1 if write_protected else 0; info[3] = 0; info[4] = 1
    info[5:37] = b'neowilderness test_hof'.ljust(32)
    info[37] = 1; info[38] = 1; info[39] = 32
    struct.pack_into('<HHH', info, 40, 0, 0, blocks_per_track)
    tmap = bytearray([0xFF] * 160)
    for t in range(35):
        for q in (4 * t - 1, 4 * t, 4 * t + 1):
            if 0 <= q < 160: tmap[q] = t
    trks = bytearray(1280)
    data = bytearray()
    start = 3
    for t, bits in enumerate(tracks):
        raw = bytearray((len(bits) + 7) // 8)
        for i, b in enumerate(bits):
            if b: raw[i >> 3] |= 0x80 >> (i & 7)
        nblk = (len(raw) + 511) // 512
        struct.pack_into('<HHI', trks, 8 * t, start, nblk, len(bits))
        data += raw.ljust(nblk * 512, b'\0')
        start += nblk
    body = (b'INFO' + struct.pack('<I', 60) + info + b'TMAP' + struct.pack('<I', 160) + tmap
            + b'TRKS' + struct.pack('<I', 1280 + len(data)) + trks)
    # track data must start at block 3 (offset 1536): header 12 + chunks above = 12+68+168+8+1280 = 1536
    assert 12 + len(body) == 1536, 12 + len(body)
    body += data
    head = b'WOZ2\xFF\x0A\x0D\x0A'
    return head + struct.pack('<I', zlib.crc32(body)) + body


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--write-protected', action='store_true')
    a = ap.parse_args()
    a.out.write_bytes(po_to_woz(a.src.read_bytes(), a.write_protected))


if __name__ == '__main__':
    main()
