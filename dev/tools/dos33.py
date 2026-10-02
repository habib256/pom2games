#!/usr/bin/env python3
"""dos33.py — build a bootable DOS 3.3 5.25" disk image (.dsk, DOS order).

    dos33.py --out MICRO-SOKOBAN.dsk \
             --bin  MICRO-SOKOBAN=micro_sokoban.bin@0x4000 \
             --bas  HELLO=hello.bas \
             [--master dos33_system.bin] [--volume 254] [--catalog]

The DOS itself (tracks 0-2) comes from dos33_system.bin next to this script
(the system tracks of the Apple DOS 3.3 master, 12 288 bytes), or from any
DOS 3.3 disk given with --master;
everything else (VTOC, catalog, files) is written from scratch, so the output
contains only the files given on the command line.  The greeting program
name baked into that DOS image is what boots (the Apple DOS 3.3 master says
"HELLO").

File formats:
  --bin NAME=path@addr   binary file (type B): 2-byte load address, 2-byte
                         length, data.  BRUN NAME runs it at addr.
  --bas NAME=path        Applesoft program (type A) written as *text* with one
                         statement per line, tokenised here (small keyword
                         table — enough for a launcher).
  --txt NAME=path        sequential text file (type T), CR line ends, high bit set.
  --read-fast            T/S lists before data, POM2-measured sector allocation.
                         Put frequently read files early in the supplied order.
                         Normal DOS allocation remains the default.
"""
import argparse
import os
import struct
import sys

TRACKS, SECTORS, SEC_SIZE = 35, 16, 256
VTOC_T, VTOC_S = 17, 0

TYPE_T, TYPE_I, TYPE_A, TYPE_B = 0x00, 0x01, 0x02, 0x04

# Applesoft tokens (subset). Longest match first when scanning.
APPLESOFT_TOKENS = {
    "END": 0x80, "FOR": 0x81, "NEXT": 0x82, "DATA": 0x83, "INPUT": 0x84,
    "DEL": 0x85, "DIM": 0x86, "READ": 0x87, "GR": 0x88, "TEXT": 0x89,
    "PR#": 0x8A, "IN#": 0x8B, "CALL": 0x8C, "PLOT": 0x8D, "HLIN": 0x8E,
    "VLIN": 0x8F, "HGR2": 0x90, "HGR": 0x91, "HCOLOR=": 0x92, "HPLOT": 0x93,
    "DRAW": 0x94, "XDRAW": 0x95, "HTAB": 0x96, "HOME": 0x97, "ROT=": 0x98,
    "SCALE=": 0x99, "SHLOAD": 0x9A, "TRACE": 0x9B, "NOTRACE": 0x9C,
    "NORMAL": 0x9D, "INVERSE": 0x9E, "FLASH": 0x9F, "COLOR=": 0xA0,
    "POP": 0xA1, "VTAB": 0xA2, "HIMEM:": 0xA3, "LOMEM:": 0xA4, "ONERR": 0xA5,
    "RESUME": 0xA6, "RECALL": 0xA7, "STORE": 0xA8, "SPEED=": 0xA9, "LET": 0xAA,
    "GOTO": 0xAB, "RUN": 0xAC, "IF": 0xAD, "RESTORE": 0xAE, "&": 0xAF,
    "GOSUB": 0xB0, "RETURN": 0xB1, "REM": 0xB2, "STOP": 0xB3, "ON": 0xB4,
    "WAIT": 0xB5, "LOAD": 0xB6, "SAVE": 0xB7, "DEF": 0xB8, "POKE": 0xB9,
    "PRINT": 0xBA, "CONT": 0xBB, "LIST": 0xBC, "CLEAR": 0xBD, "GET": 0xBE,
    "NEW": 0xBF, "TAB(": 0xC0, "TO": 0xC1, "FN": 0xC2, "SPC(": 0xC3,
    "THEN": 0xC4, "AT": 0xC5, "NOT": 0xC6, "STEP": 0xC7, "+": 0xC8, "-": 0xC9,
    "*": 0xCA, "/": 0xCB, "^": 0xCC, "AND": 0xCD, "OR": 0xCE, ">": 0xCF,
    "=": 0xD0, "<": 0xD1, "SGN": 0xD2, "INT": 0xD3, "ABS": 0xD4, "USR": 0xD5,
    "FRE": 0xD6, "SCRN(": 0xD7, "PDL": 0xD8, "POS": 0xD9, "SQR": 0xDA,
    "RND": 0xDB, "LOG": 0xDC, "EXP": 0xDD, "COS": 0xDE, "SIN": 0xDF,
    "TAN": 0xE0, "ATN": 0xE1, "PEEK": 0xE2, "LEN": 0xE3, "STR$": 0xE4,
    "VAL": 0xE5, "ASC": 0xE6, "CHR$": 0xE7, "LEFT$": 0xE8, "RIGHT$": 0xE9,
    "MID$": 0xEA,
}
_TOKENS_BY_LEN = sorted(APPLESOFT_TOKENS.items(), key=lambda kv: -len(kv[0]))


def tokenize_applesoft(text, base=0x0801):
    """Tokenise Applesoft source text into the in-memory program image."""
    out = bytearray()
    addr = base
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        num_s, _, rest = line.partition(" ")
        if not num_s.isdigit():
            raise SystemExit(f"applesoft: line without number: {raw!r}")
        body = bytearray()
        i, s = 0, rest
        in_str = False
        in_data = False                          # after DATA: as typed, up to ':'
        while i < len(s):
            c = s[i]
            if in_str:
                body.append(ord(c))
                if c == '"':
                    in_str = False
                i += 1
                continue
            if c == '"':
                in_str = True
                body.append(ord(c))
                i += 1
                continue
            if in_data:                          # Applesoft neither crunches nor
                if c == ":":                     # tokenizes DATA items
                    in_data = False
                body.append(ord(c))
                i += 1
                continue
            if c == " ":
                i += 1
                continue
            if c == "?":                         # PRINT shorthand
                body.append(APPLESOFT_TOKENS["PRINT"])
                i += 1
                continue
            up = s[i:].upper()
            for kw, tok in _TOKENS_BY_LEN:
                if up.startswith(kw):
                    body.append(tok)
                    i += len(kw)
                    if tok == 0xB2:              # REM: rest of line verbatim
                        body.extend(s[i:].encode("ascii"))
                        i = len(s)
                    elif tok == 0x83:            # DATA
                        in_data = True
                    break
            else:
                body.append(ord(c.upper()))
                i += 1
        rec = struct.pack("<H", int(num_s)) + bytes(body) + b"\x00"
        addr += 2 + len(rec)
        out += struct.pack("<H", addr) + rec
    out += b"\x00\x00"
    return bytes(out)


class Dos33Image:
    def __init__(self, master, volume=254, read_fast=False):
        self.data = bytearray(TRACKS * SECTORS * SEC_SIZE)
        m = open(master, "rb").read()
        system = 3 * SECTORS * SEC_SIZE
        if len(m) not in (system, len(self.data)):
            raise SystemExit(f"--master must be a {system}-byte tracks 0-2 image "
                             f"or a {len(self.data)}-byte DOS 3.3 disk")
        # Tracks 0-2: the DOS image (boot sector, RWTS, DOS proper).
        self.data[:system] = m[:system]
        self.free = {(t, s): True for t in range(TRACKS) for s in range(SECTORS)}
        for t in range(3):
            for s in range(SECTORS):
                self.free[(t, s)] = False
        for s in range(SECTORS):
            self.free[(VTOC_T, s)] = False
        self.volume = volume
        self.read_fast = read_fast
        self.next_track = VTOC_T + 1
        self.catalog = []          # list of (t, s, type, name, nsectors)
        self._init_catalog()

    # --- sector helpers ---------------------------------------------------
    def off(self, t, s):
        return (t * SECTORS + s) * SEC_SIZE

    def sector(self, t, s):
        o = self.off(t, s)
        return memoryview(self.data)[o:o + SEC_SIZE]

    def alloc(self):
        """Allocate one sector, DOS style: track 18 upward, then 16 downward,
        highest sector first, or the optional measured read-fast permutation."""
        order = list(range(VTOC_T + 1, TRACKS)) + list(range(VTOC_T - 1, 2, -1))
        for t in order:
            sectors = ([15, 11, 7, 10, 6, 9, 5, 8, 4, 0, 3, 14, 2, 13, 1, 12]
                       if self.read_fast else range(SECTORS - 1, -1, -1))
            for s in sectors:
                if self.free[(t, s)]:
                    self.free[(t, s)] = False
                    return t, s
        raise SystemExit("disk full")

    # --- catalog / VTOC ---------------------------------------------------
    def _init_catalog(self):
        # Catalog sectors T17 S15 .. S1, each linking to the next lower one.
        for s in range(15, 0, -1):
            sec = self.sector(VTOC_T, s)
            sec[:] = b"\x00" * SEC_SIZE
            if s > 1:
                sec[1], sec[2] = VTOC_T, s - 1

    def add_file(self, name, ftype, payload, locked=False):
        name = name.upper()
        if len(name) > 30:
            raise SystemExit(f"name too long: {name}")
        # Data sectors.
        chunks = [payload[i:i + SEC_SIZE] for i in range(0, len(payload), SEC_SIZE)] or [b""]
        # Read the T/S list before streaming data, without seeking back from
        # a large file's final track. Default allocation remains DOS style.
        reserved_lists = ([self.alloc() for _ in range((len(chunks) + 121) // 122)]
                          if self.read_fast else None)
        data_ts = []
        for chunk in chunks:
            t, s = self.alloc()
            sec = self.sector(t, s)
            sec[:] = b"\x00" * SEC_SIZE
            sec[:len(chunk)] = chunk
            data_ts.append((t, s))
        # Track/sector list sectors (122 pairs each).
        ts_lists = []
        for i in range(0, len(data_ts), 122):
            listing = reserved_lists[i // 122] if reserved_lists else self.alloc()
            ts_lists.append((listing, data_ts[i:i + 122], i))
        for n, ((t, s), pairs, first) in enumerate(ts_lists):
            sec = self.sector(t, s)
            sec[:] = b"\x00" * SEC_SIZE
            if n + 1 < len(ts_lists):
                nt, ns = ts_lists[n + 1][0]
                sec[1], sec[2] = nt, ns
            sec[5:7] = struct.pack("<H", first)
            for k, (dt, ds) in enumerate(pairs):
                sec[0x0C + 2 * k], sec[0x0D + 2 * k] = dt, ds
        nsect = len(data_ts) + len(ts_lists)
        tl, sl = ts_lists[0][0]
        self._catalog_entry(tl, sl, ftype | (0x80 if locked else 0), name, nsect)
        return nsect

    def _catalog_entry(self, tl, sl, ftype, name, nsect):
        idx = len(self.catalog)
        if idx >= 15 * 7:
            raise SystemExit("catalog full")
        s = 15 - idx // 7
        sec = self.sector(VTOC_T, s)
        e = 0x0B + (idx % 7) * 35
        sec[e], sec[e + 1], sec[e + 2] = tl, sl, ftype
        padded = name.ljust(30)
        sec[e + 3:e + 33] = bytes(ord(c) | 0x80 for c in padded)
        sec[e + 33:e + 35] = struct.pack("<H", nsect)
        self.catalog.append((tl, sl, ftype, name, nsect))

    def write_vtoc(self):
        v = self.sector(VTOC_T, VTOC_S)
        v[:] = b"\x00" * SEC_SIZE
        v[0] = 0x04
        v[1], v[2] = VTOC_T, 15            # first catalog sector
        v[3] = 3                           # DOS release
        v[6] = self.volume
        v[0x27] = 122                      # T/S pairs per list sector
        v[0x30] = self.next_track          # last track allocated (hint)
        v[0x31] = 0x01                     # allocation direction
        v[0x34], v[0x35] = TRACKS, SECTORS
        v[0x36:0x38] = struct.pack("<H", SEC_SIZE)
        for t in range(TRACKS):
            bits = 0
            for s in range(SECTORS):
                if self.free[(t, s)]:
                    bits |= 1 << s
            # DOS order: byte 0 = sectors 15..8, byte 1 = sectors 7..0 (big-endian).
            v[0x38 + 4 * t:0x38 + 4 * t + 4] = struct.pack(">H", bits) + b"\x00\x00"

    def save(self, path):
        self.write_vtoc()
        open(path, "wb").write(self.data)

    def free_sectors(self):
        return sum(1 for f in self.free.values() if f)


def parse_spec(spec, want_addr):
    name, _, rest = spec.partition("=")
    if not rest:
        raise SystemExit(f"bad spec {spec!r} (NAME=path[@addr])")
    path, _, addr = rest.partition("@")
    if want_addr and not addr:
        raise SystemExit(f"binary spec needs @addr: {spec!r}")
    return name, path, int(addr, 0) if addr else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--master", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                     "dos33_system.bin"),
                    help="DOS 3.3 tracks 0-2 image or whole disk (default: dos33_system.bin)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--volume", type=int, default=254)
    ap.add_argument("--bin", action="append", default=[], help="NAME=path@addr")
    ap.add_argument("--bas", action="append", default=[], help="NAME=path (Applesoft text)")
    ap.add_argument("--txt", action="append", default=[], help="NAME=path (text file)")
    ap.add_argument("--catalog", action="store_true", help="print the catalog afterwards")
    ap.add_argument("--read-fast", action="store_true",
                    help="allocate T/S lists first and use the POM2-measured faster sector order")
    a = ap.parse_args()

    img = Dos33Image(a.master, a.volume, read_fast=a.read_fast)
    for spec in a.bas:
        name, path, _ = parse_spec(spec, False)
        prog = tokenize_applesoft(open(path).read())
        img.add_file(name, TYPE_A, struct.pack("<H", len(prog)) + prog)
    for spec in a.bin:
        name, path, addr = parse_spec(spec, True)
        blob = open(path, "rb").read()
        img.add_file(name, TYPE_B, struct.pack("<HH", addr, len(blob)) + blob)
    for spec in a.txt:
        name, path, _ = parse_spec(spec, False)
        text = open(path).read().replace("\n", "\r")
        img.add_file(name, TYPE_T, bytes(ord(c) | 0x80 for c in text) + b"\x00")
    img.save(a.out)

    if a.catalog:
        print(f"DISK VOLUME {img.volume:03d}\n")
        for tl, sl, ft, name, n in img.catalog:
            lock = "*" if ft & 0x80 else " "
            letter = {TYPE_T: "T", TYPE_I: "I", TYPE_A: "A", TYPE_B: "B"}.get(ft & 0x7F, "?")
            print(f"{lock}{letter} {n:03d} {name}")
        print(f"\n{img.free_sectors()} sectors free  ->  {a.out}")


if __name__ == "__main__":
    main()
