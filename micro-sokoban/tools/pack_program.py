#!/usr/bin/env python3
"""Lossless boot-only LZ stream; independently decode and compare before writing."""
import argparse
from pathlib import Path


def pack(data):
    result, literals = bytearray(), bytearray()
    positions = {}
    def flush():
        if literals:
            result.append(len(literals))
            result.extend(literals)
            literals.clear()
    i = 0
    while i < len(data):
        key = data[i:i+3]
        best, distance = 0, 0
        for prev in reversed(positions.get(key, [])[-128:]):
            size = 3
            while size < 130 and i + size < len(data) and data[prev+size] == data[i+size]:
                size += 1
            if size > best:
                best, distance = size, i - prev
        if best >= 4:
            flush()
            result.extend((128 + best - 3, distance & 255, distance >> 8))
            size = best
        else:
            literals.append(data[i])
            if len(literals) == 127:
                flush()
            size = 1
        for pos in range(i, i+size):
            positions.setdefault(data[pos:pos+3], []).append(pos)
        i += size
    flush()
    result.append(0)
    return result


def unpack(data):
    result = bytearray()
    i = 0
    while data[i]:
        token = data[i]
        i += 1
        if token < 128:
            result.extend(data[i:i+token])
            i += token
        else:
            distance = int.from_bytes(data[i:i+2], 'little')
            i += 2
            for _ in range((token & 127) + 3):
                result.append(result[-distance])
    assert i == len(data)-1
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('program', type=Path)
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    program = args.program.read_bytes()
    encoded = pack(program)
    assert unpack(encoded) == program
    boot = b'MSL1' + encoded
    assert len(boot) + 0x800 < 0x6000, 'compressed input overlaps destination'
    args.output.write_bytes(boot)
    print(f'Boot program: {len(program)} -> {len(boot)} bytes (compressed stream)')
