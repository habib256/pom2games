#!/usr/bin/env python3
"""Pack resident memory into <=8 KB DOS files for the transient boot loader.

Each block has a destination/length header, then groups of eight LZ tokens.
A set flag bit is a 12-bit backward distance and four-bit length minus three;
length nibble 15 adds an extension byte (length minus 18). Otherwise the token
is one literal. Destination $FFFF continues with the next file;
destination zero ends loading. No output overlaps the $2000 input buffer or
the $5800 loader. Every generated block is independently round-trip checked.
"""
from collections import defaultdict, deque
from pathlib import Path
import struct
import sys


def compress(data):
    # Keep the complete 12-bit window, including across the old 4 KB splits.
    # A shorter first match can enable a cheaper next match. Account for the
    # flag byte every eight tokens when choosing the minimum-size parse.
    history = defaultdict(deque)
    matches = []
    size = len(data)
    for pos in range(size):
        key = data[pos:pos + 3]
        best, distance = 2, 0
        limit = min(255, size - pos)
        if len(key) == 3:
            candidates = history[key]
            while candidates and pos - candidates[0] > 4095:
                candidates.popleft()
            for prev in reversed(candidates):
                length = 3
                while length < limit and data[prev + length] == data[pos + length]:
                    length += 1
                if length > best:
                    best, distance = length, pos - prev
                if best == limit:
                    break
            candidates.append(pos)
        matches.append((best, distance))
    costs = [[0] * (size + 1) for _ in range(8)]
    choices = [[1] * size for _ in range(8)]
    for pos in range(size - 1, -1, -1):
        longest, distance = matches[pos]
        for phase in range(8):
            future = costs[(phase + 1) % 8]
            best, count = 1 + future[pos + 1], 1
            for low, high, token_size in ((3, min(17, longest), 2), (18, longest, 3)):
                if not distance or high < low:
                    continue
                cost = min(future[pos + low:pos + high + 1]) + token_size
                if cost < best:
                    best = cost
                    count = future.index(cost - token_size, pos + low, pos + high + 1) - pos
            costs[phase][pos] = best + (phase == 0)
            choices[phase][pos] = count
    tokens = []
    pos, phase = 0, 0
    while pos < size:
        count = choices[phase][pos]
        distance = matches[pos][1]
        if count != 1:
            assert distance <= 4095
            token = bytes((distance & 255, (distance >> 8) << 4 | min(count - 3, 15)))
            if count >= 18:
                token += bytes((count - 18,))
        else:
            token = data[pos:pos + 1]
        tokens.append((count != 1, token))
        pos += count
        phase = (phase + 1) % 8
    packed = bytearray()
    for index in range(0, len(tokens), 8):
        group = tokens[index:index + 8]
        packed.append(sum(match << bit for bit, (match, _) in enumerate(group)))
        for _, token in group:
            packed.extend(token)
    assert len(packed) == costs[0][0]
    assert decompress(packed, size) == data
    return bytes(packed)


def decompress(packed, length):
    out = bytearray()
    pos = 0
    while len(out) < length:
        flags = packed[pos]
        pos += 1
        for bit in range(8):
            if flags & (1 << bit):
                distance = packed[pos] | (packed[pos + 1] >> 4) << 8
                count = (packed[pos + 1] & 15) + 3
                pos += 2
                if count == 18:
                    count += packed[pos]
                    pos += 1
                assert 0 < distance <= len(out) and count >= 3
                for _ in range(count):
                    out.append(out[-distance])
            else:
                out.append(packed[pos])
                pos += 1
            if len(out) >= length:
                break
    assert len(out) == length and pos == len(packed)
    return bytes(out)


def write_packages(build, out, mapbin=None):
    build, out = Path(build), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    mapdata = bytes(mapbin) if mapbin is not None else (build / 'map.bin').read_bytes()
    from mkmap import MAP_BYTES, FOREST_BYTES
    mask = mapdata[MAP_BYTES:MAP_BYTES+FOREST_BYTES] if mapdata[26] else b''
    if len(mask) != FOREST_BYTES: mask = bytes(FOREST_BYTES)
    inputs = [(0x0926, (build / 'wildforest.bin').read_bytes()),
              (0x0800, mask), (0x0A00, (build / 'wildtxt.bin').read_bytes()),
              (0x1000, (build / 'wildlo.bin').read_bytes()),
              (0x4000, (build / 'wildgame.bin').read_bytes()),
              (0x6000, (build / 'wild.bin').read_bytes()),
              (0x7000, mapdata[:MAP_BYTES])]
    groups = [bytearray()]
    raw_size = 0
    limits = {0x0800: 0x0926, 0x0926: 0x0A00, 0x0A00: 0x1000, 0x1000: 0x2000, 0x4000: 0x5800,
              0x6000: 0x7000, 0x7000: 0x9500}
    # Share the dictionary across neighboring resident regions. Small linker
    # gaps are unused game RAM and can be restored as zero; never bridge HGR
    # or the transient loader. This avoids paying for independent dictionaries.
    merged = []
    for address, data in sorted(inputs):
        assert data and address + len(data) <= limits[address]
        if merged:
            previous, payload = merged[-1]
            gap = address - previous - len(payload)
            if 0 <= gap <= 64:
                merged[-1] = (previous, payload + bytes(gap) + data)
                continue
        merged.append((address, data))
    for address, data in merged:
        raw_size += len(data)
        offset = 0
        while offset < len(data):
            chunk = data[offset:]
            block = struct.pack('<HH', address + offset, len(chunk)) + compress(chunk)
            if len(groups[-1]) + len(block) + 2 > 8192:
                # Fit a shorter block into the current file instead of leaving
                # a gap of several KB and paying for another DOS read.
                available = 8192 - len(groups[-1]) - 2
                low, high = 1, len(chunk) - 1
                fitted = None
                while low <= high:
                    size = (low + high) // 2
                    candidate = struct.pack('<HH', address + offset, size) + compress(chunk[:size])
                    if len(candidate) <= available:
                        fitted = (size, candidate)
                        low = size + 1
                    else:
                        high = size - 1
                if fitted:
                    size, block = fitted
                    chunk = chunk[:size]
                else:
                    groups.append(bytearray())
            groups[-1].extend(block)
            offset += len(chunk)
    assert len(groups) <= 9
    paths = []
    for index, group in enumerate(groups, 1):
        group.extend(struct.pack('<H', 0 if index == len(groups) else 0xFFFF))
        path = out / f'boot{index}.bin'
        path.write_bytes(group)
        paths.append(path)
    print(f'Boot: {raw_size} -> {sum(len(group) for group in groups)} bytes, {len(groups)} files')
    return paths


if __name__ == '__main__':
    write_packages(sys.argv[1], sys.argv[2])
