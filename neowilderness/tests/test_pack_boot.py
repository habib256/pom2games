#!/usr/bin/env python3
"""Minimum-size LZ parses, long windows and the ProDOS volume payload."""
from functools import lru_cache
from pathlib import Path
import random
import tempfile
from common import HERE, DISK
from pack_boot import compress, decompress
from build_disk import TABLE_SIZE
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


def replay(data, memory, claimed):
    """Replay a record file like NEOWILD.SYSTEM: (bank, address) -> byte.
    Returns the record order and whether a claim record was met."""
    pos, order, entry = TABLE_SIZE, [], 0
    while True:
        kind, address, length, stored = struct.unpack_from('<BHHH', data, entry)
        entry += 7
        if kind == 0:
            break
        if kind == 1:
            claimed = True
            continue
        bank = kind & 0x23              # + $20: main language card (lot 7)
        assert kind & 0x80 and bank in (0, 1, 2, 3, 0x22) and stored <= 0x2000 and length <= 0x2000
        assert claimed or bank == 0, 'auxiliary record before the claim'
        payload = data[pos:pos + stored]
        pos += stored
        chunk = decompress(payload, length) if kind & 0x40 else payload
        assert len(chunk) == length
        for i, byte in enumerate(chunk):
            memory[bank, address + i] = byte
        order.append((bank, address, length))
    assert pos == len(data), 'trailing bytes in a record file'
    return order, claimed


def volume_check():
    """The ProDOS volume: files, records and the memory they rebuild (the
    common trunk, then each region pack as after its menu choice)."""
    sys.path.insert(0, str(HERE.parent / 'dev/tools/prodos'))
    from read_volume import Image
    import json
    import build_disk
    image = Image(DISK.read_bytes())
    files = {path: entry for path, entry in
             ((f'/{e[1:1 + (e[0] & 15)].decode()}', e) for e in image.entries(2))}
    packs = [f'/NEOWILD.R{r}' for r in range(1, 7)]
    assert sorted(files) == sorted(['/NEOWILD.DAT', '/NEOWILD.SYSTEM', '/PRODOS',
                                    '/NEOWILD.END', '/NEOWILD.HOF'] + packs), sorted(files)
    assert files['/NEOWILD.SYSTEM'][0x10] == 0xFF and files['/NEOWILD.SYSTEM'][0x1F:0x21] == b'\x00\x20'
    assert image.read(files['/NEOWILD.SYSTEM']) == (HERE / 'build/NEOWILD.SYSTEM').read_bytes()
    # Lot 7 step 6 (docs/HOF.md): the end module, read at $9600, and the
    # empty hall of fame, a one-block seedling file rewritten in place.
    assert files['/NEOWILD.END'][0x10] == 0x06 and files['/NEOWILD.END'][0x1F:0x21] == b'\x00\x96'
    assert image.read(files['/NEOWILD.END']) == (HERE / 'build/wildhof.bin').read_bytes()
    assert files['/NEOWILD.HOF'][0x10] == 0x06 and files['/NEOWILD.HOF'][0] >> 4 == 1, 'seedling'
    assert image.read(files['/NEOWILD.HOF']) == (HERE / 'build/NEOWILD.HOF').read_bytes()
    data = image.read(files['/NEOWILD.DAT'])
    trunk_size = len(data)
    trunk = {}
    order, claimed = replay(data, trunk, False)
    assert claimed, 'the trunk claims the auxiliary memory'
    trunk_records = len(order)
    assert order[0][:2] == (0, 0x6000), 'video.s (in WILDERNESS) must precede the claim'
    assert not any(bank == 0 and address <= 0x7000 < address + length
                   for bank, address, length in order), 'the map belongs to the packs'
    layout = json.loads((HERE / 'build/layout.json').read_text())
    lbl = build_disk.labels(HERE / 'build')

    def region(memory, bank, address, size):
        return bytes(memory[bank, address + i] for i in range(size))
    for name, address in (('wild.bin', 0x6000), ('wildgame.bin', 0x4000), ('wildlo.bin', 0x1000),
                          ('wildpg.bin', 0x0200),
                          ('wildtxt.bin', 0x0A00), ('wildforest.bin', 0x0926)):
        assert region(trunk, 0, address, len((HERE / 'build' / name).read_bytes())) == \
            (HERE / 'build' / name).read_bytes(), name
    banks = {'aux': 1, 'lc2': 2, 'lc1': 3, 'mlc2': 0x22}
    # Lot 7 step 5: the star drawing code runs in place in the main card.
    code = layout['star_code']
    assert region(trunk, banks[code['bank']], code['address'], code['length']) == \
        (HERE / 'build/wildskylc.bin').read_bytes()
    # Direction 3: the unrolled DHGR rows run in place in the main card too.
    rows = layout['dhgr_rows']
    assert rows['address'] == 0xD400 and region(trunk, banks[rows['bank']], rows['address'], rows['length']) == \
        (HERE / 'build/wilddrows.bin').read_bytes()
    assert all(not (bank == 0x22 and a < 0xD400) for bank, a in trunk), \
        'records write the ProDOS QUIT code of the main card'
    for index, module in layout['trunk_modules'].items():
        expected = bytearray((HERE / 'build' / module['image']).read_bytes())
        actual = region(trunk, banks[module['bank']], module['address'], module['length'])
        assert actual == expected, (index, module['image'])
    sizes = []
    for r in range(1, 7):
        info = layout['packs'][str(r)]
        pack = image.read(files[f'/NEOWILD.R{r}'])
        assert len(pack) == info['file'] and info['blocks'] <= 20, (r, info['blocks'])
        memory = dict(trunk)
        order, _ = replay(pack, memory, True)
        assert order[-1][:2] == (0, 0x7000) or order[-2][:2] == (0, 0x7000), \
            'the map comes last (auxiliary LZ records decode through $7000)'
        for index, module in info['modules'].items():
            expected = (HERE / 'build' / module['image']).read_bytes()
            assert region(memory, banks[module['bank']], module['address'], module['length']) == expected
        for index, module in info['empty_slots'].items():   # two-species regions
            assert region(memory, banks[module['bank']], module['address'], 1) == b'\0'
        # Directory: every entry points at its image; no two images overlap.
        directory = region(memory, 0, lbl['module_dir'], build_disk.DIR_ENTRIES * 7)
        spans = []
        for index in range(build_disk.DIR_ENTRIES):
            bank, source, length, window = struct.unpack_from('<BHHH', directory, index * 7)
            if not length:
                continue
            module = (info['modules'].get(str(index)) or info['empty_slots'].get(str(index))
                      or layout['trunk_modules'][str(index)])
            assert (source, length) == (module['address'], module['length']), (r, index)
            if index != 18:
                spans.append((bank, source, source + length))
        spans.sort()
        for (b1, s1, e1), (b2, s2, e2) in zip(spans, spans[1:]):
            assert b1 != b2 or e1 <= s2, (r, 'overlapping images', hex(s1), hex(s2))
        # Lot 7 step 4: the region's patches of TRAVEL, SITES, OUTDOOR,
        # PROJECT and SUMMARY, and its DHGR colour tables.
        for symbol, patch in info['patches'].items():
            module = layout['trunk_modules'][str(patch['module'])]
            data = bytes.fromhex(patch['data'])
            assert patch['address'] == module['address'] + lbl[symbol] - 0x5800, (r, symbol)
            assert region(memory, banks[module['bank']], patch['address'], len(data)) == data, (r, symbol)
        tables = (HERE / f'build/dhgr/dhgr_tables_r{r}.bin').read_bytes()
        assert region(memory, 0, lbl['dhgr_moods'], len(tables)) == tables, (r, 'colours')
        assert region(memory, 0, 0x7000, 64)[32] == r, (r, 'map region byte')
        texts = region(memory, 0, lbl['__REGIONTEXT_RUN__'], 128)
        assert texts[104] == r and texts[:16].rstrip(b'\0').decode() == info['name']
        reserved = [a for (bank, a) in memory if bank == 1 and (a < 0x0800 or 0x2000 <= a < 0x4000)]
        assert not reserved, 'records write reserved auxiliary RAM'
        # The language card keeps the compressed snapshot of the view under
        # TOPO (src/topo_dhgr.s): bank 1 and $E000-$F0FF of the common area
        # (docs/MEMORY.md section 12); the store has bank 2 and $F100-$FFF9.
        snapshot = [(bank, a) for (bank, a) in memory
                    if bank == 3 or (bank == 2 and 0xE000 <= a < build_disk.SNAP_END)
                    or a >= 0xFFFA]
        assert not snapshot, 'records write the TOPO snapshot area'
        sizes.append(f'R{r} {info["blocks"]}')
    free = image.free_blocks()
    print(f'  ProDOS volume: PRODOS, NEOWILD.SYSTEM, NEOWILD.DAT ({trunk_size} bytes, '
          f'{trunk_records} records), packs ({", ".join(sizes)} blocks, <= 20); records rebuild '
          f'every image, directory, fauna patches and colours; {free} of 280 blocks free: OK')


if __name__ == '__main__':
    main()
