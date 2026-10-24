#!/usr/bin/env python3
"""dsk2woz.py -- a 140K 5.25" image (.dsk / .do DOS order, .po ProDOS order)
as a WOZ 2 file with real 10-bit sync bytes.

    python3 dsk2woz.py IMAGE OUT.woz

Why: the MiSTer Apple-II core (2026-10 releases) turns a .dsk / .po into WOZ
itself (Main_MiSTer support/a2/iigs_fmt.cpp), but its tracks are the NIB bytes
laid end to end, 8 bits each, without one sync byte. Its flux-level drive
then reads DOS's own file loads, yet a program that reads sectors through
RWTS right after its BRUN (MICRO-SOKOBAN's loader, DIRTBIKE's TITLE) gets
errors -- seen on hardware 2026-10-24; the same disks as WOZ from this tool
run. Only a WOZ is written back to the SD card by the core, too (saves).

Each track: 64 sync bytes, then sectors 0..15 in physical order, each an
address field, 8 sync bytes, a data field and 16 sync bytes (about 50 000
bits, a real drive's track at 4 us a bit). Volume: the DOS VTOC's (track 17
sector 0 byte 6) when it holds one, else 254. The result is read back with a
self-syncing framer (like the Disk II's sequencer) and every sector must
decode to the image's bytes, or nothing is written.
"""
import struct
import sys
import zlib
from pathlib import Path

TRACKS, SECTORS, SECTOR = 35, 16, 256
IMAGE_SIZE = TRACKS * SECTORS * SECTOR
BLOCKS_PER_TRACK = 13                   # 6656 bytes: room for 53 248 bits
TRACK0_BLOCK = 3                        # header + INFO + TMAP, then TRKS dir

# physical sector -> sector index in the image file
DOS_ORDER = [0, 7, 14, 6, 13, 5, 12, 4, 11, 3, 10, 2, 9, 1, 8, 15]
PRODOS_ORDER = [0, 8, 1, 9, 2, 10, 3, 11, 4, 12, 5, 13, 6, 14, 7, 15]

GCR = bytes.fromhex(
    "96979a9b9d9e9fa6a7abacadaeafb2b3b4b5b6b7b9babbbcbdbebfcbcdcecfd3"
    "d6d7d9dadbdcdddedfe5e6e7e9eaebecedeeeff2f3f4f5f6f7f9fafbfcfdfeff")
UNGCR = {b: i for i, b in enumerate(GCR)}
GAP_START, GAP_ADDR_DATA, GAP_SECTOR = 64, 8, 16


def odd_even(v):
    return [((v >> 1) & 0x55) | 0xAA, (v & 0x55) | 0xAA]


def encode_data(sec):
    """256 bytes -> 343 disk bytes (6-and-2, checksum last)."""
    aux = [0] * 86
    for i, b in enumerate(sec):
        aux[i % 86] |= (((b & 1) << 1) | ((b & 2) >> 1)) << (2 * (i // 86))
    six = aux + [b >> 2 for b in sec]
    out, prev = [], 0
    for v in six:
        out.append(GCR[v ^ prev])
        prev = v
    out.append(GCR[prev])
    return out


def decode_data(nib):
    """343 disk bytes -> 256 bytes, or None (bad nibble / checksum)."""
    vals, prev = [], 0
    for b in nib:
        if b not in UNGCR:
            return None
        prev ^= UNGCR[b]
        vals.append(prev)
    if vals[-1] != 0:
        return None
    aux, six = vals[:86], vals[86:342]
    return bytes((six[i] << 2)
                 | (((aux[i % 86] >> (2 * (i // 86))) & 1) << 1)
                 | ((aux[i % 86] >> (2 * (i // 86) + 1)) & 1)
                 for i in range(256))


def track_bits(image, track, order, volume):
    bits = []

    def put(b, width=8):
        bits.extend((b >> k) & 1 for k in range(7, -1, -1))
        bits.extend([0] * (width - 8))

    def sync(n):
        for _ in range(n):
            put(0xFF, 10)

    sync(GAP_START)
    for phys in range(SECTORS):
        for b in ([0xD5, 0xAA, 0x96] + odd_even(volume) + odd_even(track)
                  + odd_even(phys) + odd_even(volume ^ track ^ phys)
                  + [0xDE, 0xAA, 0xEB]):
            put(b)
        sync(GAP_ADDR_DATA)
        off = (track * SECTORS + order[phys]) * SECTOR
        for b in [0xD5, 0xAA, 0xAD] + encode_data(image[off:off + SECTOR]) + [0xDE, 0xAA, 0xEB]:
            put(b)
        sync(GAP_SECTOR)
    return bits


def frame(bits):
    """Disk bytes as the Disk II sequencer frames them (two turns, so a
    byte across the track's end is whole)."""
    out, reg = [], 0
    for b in bits + bits:
        if reg == 0 and not b:
            continue
        reg = (reg << 1) | b
        if reg & 0x80:
            out.append(reg)
            reg = 0
    return out


def check_track(bits, image, track, order):
    d, found = frame(bits), {}
    for i in range(len(d) - 360):
        if d[i:i + 3] != [0xD5, 0xAA, 0x96]:
            continue
        t = ((d[i + 5] << 1) | 1) & d[i + 6]
        s = ((d[i + 7] << 1) | 1) & d[i + 8]
        j = d.index(0xD5, i + 14)
        if t != track or s >= SECTORS or d[j:j + 3] != [0xD5, 0xAA, 0xAD]:
            continue
        data = decode_data(d[j + 3:j + 346])
        if data is not None:
            found.setdefault(s, data)
    for phys in range(SECTORS):
        off = (track * SECTORS + order[phys]) * SECTOR
        if found.get(phys) != image[off:off + SECTOR]:
            sys.exit(f"dsk2woz: track {track} sector {phys} does not read back")


def build(image, order, volume):
    info = bytearray(60)
    info[0] = 2                                 # INFO version
    info[1] = 1                                 # 5.25"
    info[5:37] = b"pom2games dsk2woz".ljust(32)
    info[37] = 1                                # sides
    info[38] = 1                                # 16-sector boot
    info[39] = 32                               # 4 us a bit
    struct.pack_into("<H", info, 44, BLOCKS_PER_TRACK)
    tmap = bytearray([0xFF] * 160)              # quarter tracks
    for t in range(TRACKS):
        for q in (t * 4 - 1, t * 4, t * 4 + 1):
            if 0 <= q < 160:
                tmap[q] = t
    trk_dir, data = bytearray(1280), bytearray()
    for t in range(TRACKS):
        bits = track_bits(image, t, order, volume)
        assert len(bits) <= BLOCKS_PER_TRACK * 4096
        check_track(bits, image, t, order)
        raw = bytearray(BLOCKS_PER_TRACK * 512)
        for i, b in enumerate(bits):
            if b:
                raw[i >> 3] |= 0x80 >> (i & 7)
        struct.pack_into("<HHI", trk_dir, t * 8,
                         TRACK0_BLOCK + t * BLOCKS_PER_TRACK, BLOCKS_PER_TRACK, len(bits))
        data += raw
    body = (b"INFO" + struct.pack("<I", len(info)) + info
            + b"TMAP" + struct.pack("<I", len(tmap)) + tmap
            + b"TRKS" + struct.pack("<I", len(trk_dir) + len(data)) + trk_dir + data)
    return b"WOZ2\xff\n\r\n" + struct.pack("<I", zlib.crc32(body)) + body


def main(argv):
    if len(argv) != 2:
        sys.exit("usage: dsk2woz.py IMAGE.dsk|.do|.po OUT.woz")
    src, dst = Path(argv[0]), Path(argv[1])
    image = src.read_bytes()
    if len(image) != IMAGE_SIZE:
        sys.exit(f"dsk2woz: {src}: not a 140K 5.25\" image")
    order = PRODOS_ORDER if src.suffix.lower() == ".po" else DOS_ORDER
    volume = 254
    vtoc = 17 * SECTORS * SECTOR
    if order is DOS_ORDER and image[vtoc + 1] == 17 and image[vtoc + 3] == 3 and image[vtoc + 6]:
        volume = image[vtoc + 6]
    dst.write_bytes(build(image, order, volume))


if __name__ == "__main__":
    main(sys.argv[1:])
