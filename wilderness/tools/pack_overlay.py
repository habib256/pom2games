#!/usr/bin/env python3
"""Backward LZ modules, decoded in place with a protected 128-byte prefix."""
import struct
from pack_boot import compress, decompress

MAGIC = b'\x00W'
PREFIX = 128
HEADER = 6


def safe_in_place(packed, length):
    # Interpret the forward token stream of the reversed tail. The resident
    # decoder reads it backward from its reversed on-disk representation.
    source, dest = HEADER + len(packed), length
    pos = 0
    while dest > PREFIX:
        flags = packed[pos]
        pos += 1
        source -= 1
        for bit in range(8):
            if flags & (1 << bit):
                count = (packed[pos + 1] & 15) + 3
                pos += 2
                source -= 2
                if count == 18:
                    count += packed[pos]
                    pos += 1
                    source -= 1
                dest -= count
                if dest < source:
                    return False
            else:
                pos += 1
                source -= 1
                dest -= 1
                if dest < source:
                    return False
            if dest == PREFIX:
                return pos == len(packed)
    return False


def pack(data):
    assert not data.startswith(MAGIC), 'unpacked module collides with compression marker'
    if len(data) <= PREFIX:
        return data
    encoded = compress(data[PREFIX:][::-1])
    if HEADER + len(encoded) + PREFIX >= len(data) or not safe_in_place(encoded, len(data)):
        return data
    result = MAGIC + struct.pack('<HH', len(data), len(encoded)) + encoded[::-1] + data[:PREFIX]
    # DOS transfers whole 256-byte sectors, including its four-byte header.
    # Small savings do not repay decoding and can change rotational timing.
    if (len(data) + 259) // 256 - (len(result) + 259) // 256 < 2:
        return data
    assert unpack(result) == data
    return result


def unpack(data):
    if not data.startswith(MAGIC):
        return data
    length, packed = struct.unpack_from('<HH', data, 2)
    assert len(data) == HEADER + packed + PREFIX
    return data[-PREFIX:] + decompress(data[HEADER:HEADER + packed][::-1], length - PREFIX)[::-1]
