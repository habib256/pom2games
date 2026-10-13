#!/usr/bin/env python3
"""Minimum-size LZ parses, long windows and the ProDOS volume payload."""
from functools import lru_cache
from pathlib import Path
import random
import tempfile
from common import HERE, DISK
from pack_boot import compress, decompress
import struct
import sys


def minimum_size(data):
    # Independent exhaustive token enumeration, including overlapping copies.
    @lru_cache(None)
    def visit(pos, phase):
        if pos == len(data):
            return 0
        following = (phase + 1) % 8
        cost = 1 + visit(pos + 1, following)
        for previous in range(max(0, pos - 4095), pos):
            length = 0
            while length < min(255, len(data) - pos) and data[previous + length] == data[pos + length]:
                length += 1
            for count in range(3, length + 1):
                cost = min(cost, 2 + (count >= 18) + visit(pos + count, following))
        return cost + (phase == 0)
    return visit(0, 0)


def main():
    cases = 0
    for length in range(10):
        for value in range(1 << length):
            data = bytes((value >> bit) & 1 for bit in range(length))
            packed = compress(data)
            assert len(packed) == minimum_size(data), (length, value)
            assert decompress(packed, length) == data
            cases += 1
    for length, size in ((17, 4), (18, 4), (19, 5), (255, 5), (256, 5)):
        assert len(compress(bytes(length))) == size, length
    rng = random.Random(4095)
    prefix = rng.randbytes(4095)
    for data in (prefix + prefix[:255], prefix + b'x' + prefix[:255],
                 rng.randbytes(9472), bytes(9472), bytes(range(256)) * 37):
        assert decompress(compress(data), len(data)) == data
    print(f'  {cases} exhaustive shortest parses; flag, length and 4 KB window boundaries: OK')

    volume_check()


def volume_check():
    """The ProDOS volume: files, records and the memory they rebuild."""
    sys.path.insert(0, str(HERE.parent / 'dev/tools/prodos'))
    from read_volume import Image
    import json
    image = Image(DISK.read_bytes())
    files = {path: entry for path, entry in
             ((f'/{e[1:1 + (e[0] & 15)].decode()}', e) for e in image.entries(2))}
    assert sorted(files) == ['/NEOWILD.DAT', '/NEOWILD.SYSTEM', '/PRODOS'], sorted(files)
    assert files['/NEOWILD.SYSTEM'][0x10] == 0xFF and files['/NEOWILD.SYSTEM'][0x1F:0x21] == b'\x00\x20'
    assert image.read(files['/NEOWILD.SYSTEM']) == (HERE / 'build/NEOWILD.SYSTEM').read_bytes()
    data = image.read(files['/NEOWILD.DAT'])
    # Replay the records like NEOWILD.SYSTEM: (bank, address) -> bytes.
    memory, pos, claimed, order = {}, 128, False, []
    entry = 0
    while True:
        kind, address, length, stored = struct.unpack_from('<BHHH', data, entry)
        entry += 7
        if kind == 0:
            break
        if kind == 1:
            claimed = True
            continue
        bank = kind & 3
        assert kind & 0x80 and stored <= 0x2000 and length <= 0x2000
        assert claimed or bank == 0, 'auxiliary record before the claim'
        payload = data[pos:pos + stored]
        pos += stored
        chunk = decompress(payload, length) if kind & 0x40 else payload
        assert len(chunk) == length
        for i, byte in enumerate(chunk):
            memory[bank, address + i] = byte
        order.append((bank, address))
    assert pos == len(data), 'trailing bytes in NEOWILD.DAT'
    assert order[0] == (0, 0x6000), 'video.s (in WILDERNESS) must precede the claim'

    def region(bank, address, size):
        return bytes(memory[bank, address + i] for i in range(size))
    for name, address in (('wild.bin', 0x6000), ('wildgame.bin', 0x4000), ('wildlo.bin', 0x1000),
                          ('wildtxt.bin', 0x0A00), ('wildforest.bin', 0x0926)):
        assert region(0, address, len((HERE / 'build' / name).read_bytes())) == \
            (HERE / 'build' / name).read_bytes(), name
    layout = json.loads((HERE / 'build/layout.json').read_text())
    banks = {'aux': 1, 'lc2': 2, 'lc1': 3}
    for index, module in layout['modules'].items():
        expected = (HERE / 'build' / module['image']).read_bytes()
        actual = region(banks[module['bank']], module['address'], module['length'])
        assert actual == expected, (index, module['image'])
        if module['bank'] == 'aux':
            assert not (module['address'] < 0x0800 or 0x2000 <= module['address'] < 0x4000
                        or module['address'] + module['length'] > 0xC000), 'reserved aux'
            assert module['address'] + module['length'] <= 0x2000 or module['address'] >= 0x4000
    reserved = [a for (bank, a) in memory if bank == 1 and (a < 0x0800 or 0x2000 <= a < 0x4000)]
    assert not reserved, 'records write reserved auxiliary RAM'
    free = image.free_blocks()
    print(f'  ProDOS volume: PRODOS, NEOWILD.SYSTEM, NEOWILD.DAT ({len(data)} bytes, '
          f'{len(order)} records); records rebuild every image; {free} of 280 blocks free: OK')


if __name__ == '__main__':
    main()
