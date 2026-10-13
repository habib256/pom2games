#!/usr/bin/env python3
"""dhgr_sprites.py: build-time DHGR conversion of the five original sprites.

Input: build/original_graphics/NAME.bin (tools/re_graphics.py, ignored by Git).
The engine draws one billboard view per asset (no heading or animation
frames); distance selects a power-of-two scale, shift 0..3, exactly as
src/sprites.s and tests/scene_ref.py sample it: scaled column j is original
column j << shift, and only rows with (base - y) % (1 << shift) == 0 are kept,
at up = (base - y) >> shift rows above the anchor. Each scale is converted
once, here, instead of being decimated by the 6502 at run time.

Output: build/dhgr/sprites/NAME_sS.bin (+ .png preview, 2x horizontally) and
manifest.json. Binary format (little endian), version 1:

  0  'D' 'S' 1      magic and version
  3  width          colour columns (= ray columns) of this scale
  4  height         highest up + 1 (rows above and including the anchor row)
  5  shift          0..3
  6  base           bottom opaque row of the original image (0..191)
  7  origin         local lift: 0 for the wreck, 10 for the other assets
  8  offsets        (width + 1) LE16 file offsets; column c = [off[c], off[c+1])
     runs           per column, top to bottom, 2 bytes each: up_top, then
                    (length - 1) << 4 | colour, length 1..16 (longer runs are
                    split). Rows up_top, up_top - 1, ... up_top - length + 1.
                    Absent rows are transparent: the runs are the mask.

Placement: distant billboard row = anchor - up; local (depth 0, shift 0)
row = base - origin - up. Colours are dhgr_palette.SPRITES[NAME][code].
"""
import argparse, hashlib, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
from re_graphics import decode, png  # noqa: E402
import dhgr_palette as P  # noqa: E402

NAMES = ('wreck', 'bear', 'cougar', 'rattlesnake', 'cabin')
SHIFTS = range(4)
MAGIC = b'DS\x01'


def original(name, src=None):
    src = Path(src or HERE / 'build/original_graphics')
    image, _ = decode((src / f'{name}.bin').read_bytes())
    return image


def convert(name, shift, image=None, colours=None):
    """Return the sprite as a dict with per-column {up: colour} maps."""
    image = image or original(name)
    width0 = len(image[0])
    base = max(y for y, row in enumerate(image) if any(c >= 0 for c in row))
    stride = 1 << shift
    width = (width0 + stride - 1) >> shift
    colours = colours or P.SPRITES[name]
    columns = []
    for j in range(width):
        x = j * stride
        col = {}
        for y in range(base + 1):
            code = image[y][x]
            if code < 0 or (base - y) % stride:
                continue
            col[(base - y) >> shift] = colours[code]
        columns.append(col)
    height = max((max(c) + 1 for c in columns if c), default=0)
    return dict(name=name, shift=shift, width=width, height=height, base=base,
                origin=0 if name == 'wreck' else 10, columns=columns)


def runs(col):
    """Top-to-bottom runs (up_top, length, colour) of one column."""
    out = []
    for up in sorted(col, reverse=True):
        c = col[up]
        if out and out[-1][0] - out[-1][1] == up and out[-1][2] == c:
            out[-1][1] += 1
        else:
            out.append([up, 1, c])
    return [tuple(r) for r in out]


def encode(s):
    head = MAGIC + bytes((s['width'], s['height'], s['shift'], s['base'], s['origin']))
    body = bytearray()
    offsets = []
    start = len(head) + 2 * (s['width'] + 1)
    for col in s['columns']:
        offsets.append(start + len(body))
        for top, length, c in runs(col):
            while length:
                k = min(length, 16)
                body += bytes((top, (k - 1) << 4 | c))
                top -= k
                length -= k
    offsets.append(start + len(body))
    return head + b''.join(o.to_bytes(2, 'little') for o in offsets) + bytes(body)


def parse(data):
    """Inverse of encode (round trip used by the tests and dhgr_ref)."""
    if data[:3] != MAGIC:
        raise ValueError('not a DHGR sprite')
    width, height, shift, base, origin = data[3:8]
    offs = [int.from_bytes(data[8 + 2*i:10 + 2*i], 'little') for i in range(width + 1)]
    columns = []
    for a, b in zip(offs, offs[1:]):
        col = {}
        for k in range(a, b, 2):
            top, packed = data[k:k + 2]
            for i in range((packed >> 4) + 1):
                col[top - i] = packed & 15
        columns.append(col)
    return dict(shift=shift, width=width, height=height, base=base, origin=origin, columns=columns)


def preview(path, s):
    w, h = s['width'], max(s['height'], 1)
    rgba = bytearray()
    for row in range(h):
        up = h - 1 - row
        for col in s['columns']:
            c = col.get(up)
            px = bytes((*P.RGB[c], 255)) if c is not None else b'\0\0\0\0'
            rgba += px * 2
    png(path, 2 * w, h, bytes(rgba))


_cache = {}


def load(name, shift, out=None):
    """Converted sprite from build/dhgr/sprites, else converted in memory."""
    key = (name, shift)
    if key not in _cache:
        path = Path(out or HERE / 'build/dhgr/sprites') / f'{name}_s{shift}.bin'
        if path.exists():
            s = parse(path.read_bytes())
        else:
            s = convert(name, shift)
        s['name'] = name
        _cache[key] = s
    return _cache[key]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--src', type=Path, default=HERE / 'build/original_graphics')
    ap.add_argument('--out', type=Path, default=HERE / 'build/dhgr/sprites')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name in NAMES:
        image = original(name, a.src)
        for shift in SHIFTS:
            s = convert(name, shift, image)
            data = encode(s)
            assert parse(data)['columns'] == s['columns']
            stem = a.out / f'{name}_s{shift}'
            stem.with_suffix('.bin').write_bytes(data)
            preview(stem.with_suffix('.png'), s)
            manifest[f'{name}_s{shift}'] = dict(width=s['width'], height=s['height'], base=s['base'],
                                                origin=s['origin'], bytes=len(data),
                                                runs=sum(len(runs(c)) for c in s['columns']),
                                                sha256=hashlib.sha256(data).hexdigest())
        print(f'{name}: ' + ', '.join(f"s{k} {manifest[f'{name}_s{k}']['bytes']} B" for k in SHIFTS))
    (a.out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
