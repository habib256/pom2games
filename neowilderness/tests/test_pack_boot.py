#!/usr/bin/env python3
"""Minimum-size LZ parses, long windows and the ProDOS volume payload."""
from functools import lru_cache
from pathlib import Path
import random
import tempfile
from common import HERE, DISK, edition_image
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
        # Docs/MEMORY.md 15: the loader puts ProDOS's QUIT code ($D100-$D3FF
        # of the main card's bank 2) aside at the claim, before any record
        # replaces it.
        assert claimed or not (bank == 0x22 and address < 0xD400 and address + length > 0xD100), \
            'the QUIT code replaced before the claim'
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
    layout = json.loads((HERE / 'build/layout.json').read_text())
    # Lot 9 (docs/SAVE.md): NEOWILD.SAV and the saved games that fit on the
    # volume (five on 800 KB, fewer or none on the 140 KB image).
    saves = ['/NEOWILD.SAV'] + ['/' + n for n in layout['save_games']['files']]
    # Docs/MEMORY.md 14: NEOWILD.BLK on NeoWildernessXL (the modules read by block).
    blk = ['/NEOWILD.BLK'] if layout['disk']['bytes'] else []
    assert sorted(files) == sorted(['/NEOWILD.DAT', '/NEOWILD.SYSTEM', '/PRODOS',
                                    '/NEOWILD.END', '/NEOWILD.HOF'] + saves + blk), sorted(files)
    lbl = build_disk.labels(HERE / 'build')
    # NEOWILD.DAT holds the trunk, the six packs and the preparation (docs/MEMORY.md
    # 13); NEOWILD.SYSTEM carries their marks (src/boot.s ld_marks).
    whole = image.read(files['/NEOWILD.DAT'])
    marks = layout['dat_file']['marks']
    assert len(whole) == layout['dat_file']['bytes'] and len(marks) == 7
    # NEOWILD.SYSTEM: the stub, then the loader LZ-packed (src/boot.s SYSSTUB).
    system = image.read(files['/NEOWILD.SYSTEM'])
    at = lbl['__LOADER_LOAD__'] - 0x2000
    built = (HERE / 'build/NEOWILD-xl.SYSTEM').read_bytes()     # (XL: docs/MENUS.md 9)
    loader = build_disk.unpack_stream(system[at:])
    mark = lbl['ld_marks'] - lbl['__LOADER_RUN__']
    assert system[:at] == built[:at] and len(system) < len(built)
    assert loader[:mark] == built[at:at + mark] and loader[mark + 34:] == built[at + mark + 34:]
    # ld_regions follows the marks: the scenarios of the edition (XL: 6);
    # then ld_blk, NEOWILD.BLK's first block and its first 6 bytes (docs/MEMORY.md 14).
    assert lbl['ld_regions'] == lbl['ld_marks'] + 23 and loader[mark + 23] == 6
    assert lbl['ld_blk'] == lbl['ld_regions'] + 1
    # Docs/MEMORY.md 15: ld_exit, the auxiliary address of the exit state
    # (directory entry 2), just below the packs' sprite area.
    assert lbl['ld_exit'] == lbl['ld_blk'] + 8
    exit_state = layout['exit_state']
    assert loader[mark + 32:mark + 34] == exit_state['address'].to_bytes(2, 'little')
    assert exit_state['address'] + exit_state['length'] == layout['pack_area']['start']
    disk = layout['disk']
    if blk:
        data = image.read(files['/NEOWILD.BLK'])
        assert len(data) == disk['bytes'] and data[:4] == b'NWBK'
        assert loader[mark + 24:mark + 32] == disk['first_block'].to_bytes(2, 'little') + data[:6]
        # Index block 7, data from block 8 (build_disk.BLK_FIRST): what the
        # directory's block numbers assume.
        assert files['/NEOWILD.BLK'][0] >> 4 == 2
        key = int.from_bytes(files['/NEOWILD.BLK'][0x11:0x13], 'little')
        index = image.block(key)
        assert [index[n] | index[256 + n] << 8 for n in range(len(data) // 512)] == \
            list(range(disk['first_block'], disk['first_block'] + len(data) // 512))
        for i, where in disk['modules'].items():
            module = layout['trunk_modules'][i]
            raw = build_disk.module_image(HERE / 'build', module)
            at_blk = (where['block'] - disk['first_block']) * 512
            assert module['bank'] == 'disk' and module['block'] == where['block']
            assert where['blocks'] == -(-len(raw) // 512) and \
                module['window'] == build_disk.MODULES[int(i)][1]      # lot 4: FORAGE at $9600
            assert data[at_blk:at_blk + where['blocks'] * 512] == raw + bytes(where['blocks'] * 512 - len(raw)), i
    else:
        assert loader[mark + 24:mark + 32] == bytes(8) and not disk['modules']
    assert loader[mark:mark + 23] == b''.join(m.to_bytes(3, 'little') for m in marks) + \
        (len(whole) - marks[6]).to_bytes(2, 'little')
    assert files['/NEOWILD.SYSTEM'][0x10] == 0xFF and files['/NEOWILD.SYSTEM'][0x1F:0x21] == b'\x00\x20'
    # Fidelity lot 1: the journey preparation, LZ-packed, decoded to $2000 (src/prepare.s).
    from pack_boot import decompress
    pre = (HERE / 'build/wildpre.bin').read_bytes()
    packed = whole[marks[6]:]
    assert len(packed) <= 0x1000 and decompress(packed, len(pre)) == pre
    # Lot 7 step 6 (docs/HOF.md): the end module, read at $9600, and the
    # empty hall of fame, a one-block seedling file rewritten in place.
    assert files['/NEOWILD.END'][0x10] == 0x06 and files['/NEOWILD.END'][0x1F:0x21] == b'\x00\x96'
    assert image.read(files['/NEOWILD.END']) == (HERE / 'build/wildhof-xl.bin').read_bytes()
    assert files['/NEOWILD.HOF'][0x10] == 0x06 and files['/NEOWILD.HOF'][0] >> 4 == 1, 'seedling'
    assert image.read(files['/NEOWILD.HOF']) == (HERE / 'build/NEOWILD.HOF').read_bytes()
    data = whole[:marks[0]]
    trunk_size = len(data)
    trunk = {}
    order, claimed = replay(data, trunk, False)
    assert claimed, 'the trunk claims the auxiliary memory'
    trunk_records = len(order)
    assert order[0][:2] == (0, 0x6000), 'video.s (in WILDERNESS) must precede the claim'
    assert not any(bank == 0 and address <= 0x7000 < address + length
                   for bank, address, length in order), 'the map belongs to the packs'

    def region(memory, bank, address, size):
        return bytes(memory[bank, address + i] for i in range(size))
    for name, address in (('wild.bin', 0x6000), ('wildgame.bin', 0x4000), ('wildlo.bin', 0x1000),
                          ('wildpg.bin', 0x0200),
                          ('wildtxt.bin', 0x0A00), ('wildforest.bin', 0x0926)):
        linked = edition_image(name, True).read_bytes()      # (DISK: XL's, docs/MENUS.md 9)
        assert region(trunk, 0, address, len(linked)) == linked, name
    banks = {'aux': 1, 'lc2': 2, 'lc1': 3, 'mlc2': 0x22}
    # Lot 7 step 5: the star drawing code runs in place in the main card.
    code = layout['star_code']
    assert region(trunk, banks[code['bank']], code['address'], code['length']) == \
        (HERE / 'build/wildskylc.bin').read_bytes()
    # Direction 3: the unrolled DHGR rows run in place in the main card too.
    rows = layout['dhgr_rows']
    assert rows['address'] == 0xD400 and region(trunk, banks[rows['bank']], rows['address'], rows['length']) == \
        (HERE / 'build/wilddrows.bin').read_bytes()
    # Docs/MEMORY.md 14: the LZ decoder runs in place at $D001-$D0FF; nothing
    # touches $D000 (ProDOS's bank signature). Docs/MEMORY.md 15: the QUIT
    # code area $D100-$D3FF receives the bank 2 code of the view, nothing else.
    decoder = layout['lz_decoder']
    assert (decoder['bank'], decoder['address']) == ('mlc2', 0xD001) and decoder['length'] <= 0xFF
    assert region(trunk, banks['mlc2'], 0xD001, decoder['length']) == \
        (HERE / 'build/wildlzlc.bin').read_bytes()
    assert all(not (bank == 0x22 and a == 0xD000) for bank, a in trunk), \
        'records write the ProDOS signature of the main card'
    b2 = layout['bank2_code']
    assert (b2['bank'], b2['address']) == ('mlc2', 0xD100) and b2['length'] <= 0x300
    assert region(trunk, banks['mlc2'], 0xD100, b2['length']) == (HERE / 'build/wildb2.bin').read_bytes()
    assert all(not (bank == 0x22 and 0xD100 + b2['length'] <= a < 0xD400) for bank, a in trunk), \
        'records write the main card past the bank 2 code'
    assert layout['exit_state']['length'] == lbl['EX_STATE'] + 0x300, 'the exit state keeps the QUIT code'
    for index, module in layout['trunk_modules'].items():
        if module['bank'] == 'disk':
            continue                # NEOWILD.BLK (checked above)
        expected = build_disk.stored_bytes(HERE / 'build', module)
        actual = region(trunk, banks[module['bank']], module['address'], module['stored'])
        assert actual == expected, (index, module['image'])
        if 'lz' in module:          # decoded in place, as memory.s lz_unpack
            assert build_disk.lz_unpack(expected, module['lz']['copy'], module['length']) == \
                (HERE / 'build' / module['image']).read_bytes(), (index, 'LZ')
    sizes = []
    for r in range(1, 7):
        info = layout['packs'][str(r)]
        pack = whole[marks[r - 1]:marks[r]]
        assert len(pack) == info['file'] and info['mark'] == marks[r - 1], r
        memory = dict(trunk)
        order, _ = replay(pack, memory, True)
        assert order[-1][:2] == (0, 0x7000) or order[-2][:2] == (0, 0x7000), \
            'the map comes last (auxiliary LZ records decode through $7000)'
        for index, module in info['modules'].items():     # animals, LZ when shorter
            expected = build_disk.stored_bytes(HERE / 'build', module)
            assert region(memory, banks[module['bank']], module['address'], module['stored']) == expected
            if 'lz' in module:
                assert build_disk.lz_unpack(expected, module['lz']['copy'], module['length']) == \
                    (HERE / 'build' / module['image']).read_bytes(), (r, index, 'LZ')
        for index, module in info['empty_slots'].items():   # two-species regions
            assert region(memory, banks[module['bank']], module['address'], 1) == b'\0'
        # Directory: every entry points at its image; no two images overlap.
        directory = region(memory, 0, lbl['module_dir'], build_disk.DIR_ENTRIES * 7)
        spans = []
        for index in range(build_disk.DIR_ENTRIES):
            bank, source, length, window = struct.unpack_from('<BHHH', directory, index * 7)
            if not length:
                continue
            if index in (build_disk.TB_FETCH, build_disk.ZP_ENTRY):
                continue                    # text_fetch's scratch entry, ProDOS's zero page
            if index == build_disk.EXIT_ENTRY:  # the exit state (docs/MEMORY.md 15): written
                exit_state = layout['exit_state']   # by the loader, never by a record
                assert (bank, source, length, window) == (0, exit_state['address'], exit_state['length'],
                                                          build_disk.EXIT_BUF), (r, 'exit state')
                assert not any(b == 1 and source <= a < source + length for (b, a) in memory), \
                    (r, 'a record writes the exit state')
                spans.append((bank, source, source + length))
                continue
            module = (info['modules'].get(str(index)) or info['empty_slots'].get(str(index))
                      or layout['trunk_modules'][str(index)])
            if module['bank'] == 'disk':    # BANK_DISK: first block, raw length, window
                assert (bank, source, length, window) == \
                    (build_disk.BANK_DISK, module['block'], module.get('fetch', module['length']),
                     build_disk.MODULES[int(index)][1]), (r, index)
                continue
            assert (source, length) == (module['address'], module.get('stored', module['length'])), (r, index)
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
        sizes.append(f'R{r} {info["file"]}')
    free = image.free_blocks()
    print(f'  ProDOS volume: PRODOS, NEOWILD.SYSTEM, NEOWILD.DAT ({trunk_size} bytes, '
          f'{trunk_records} records), packs ({", ".join(sizes)} bytes); records rebuild '
          f'every image, directory, fauna patches and colours; {free} of 280 blocks free: OK')


if __name__ == '__main__':
    main()
