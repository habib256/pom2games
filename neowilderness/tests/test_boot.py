#!/usr/bin/env python3
"""NEOWILD.SYSTEM must restore every resident main-RAM byte before start:
the common trunk NEOWILD.DAT, then the Sierra Nevada pack NEOWILD.R2 chosen
in the start menu (map with its level, woods, texts, directory).

Auxiliary RAM is checked through the transfers in test_overlay_codec.py.
A little-compressible map exercises raw records, LZ literals and the
chunking of the map into several records.
"""
import random
import tempfile
from common import HERE, L, DISK, a2test, disk_with


def expected_map(mapbin, level=4, region=2, free=0):
    """The map as the loader leaves it: region byte (+32, legacy maps), the
    chosen level (+22) and the journey kind (+33)."""
    from mkmap import MAP_BYTES
    m = bytearray(mapbin[:MAP_BYTES])
    if not m[32]:
        m[32] = region
    m[22], m[33] = level, free
    return bytes(m)


def check(disk, mapbin):
    import build_disk
    regions = [('wildforest.bin', 0x0926), ('wildtxt.bin', 0x0A00), ('wildlo.bin', 0x1000),
               ('wildgame.bin', 0x4000), ('wild.bin', 0x6000)]
    expected = [(address, (HERE / 'build' / name).read_bytes()) for name, address in regions]
    from mkmap import MAP_BYTES, FOREST_BYTES
    expected.append((0x7000, expected_map(mapbin)))
    mask = mapbin[MAP_BYTES:MAP_BYTES+FOREST_BYTES] if mapbin[26] else b''
    expected.append((0x0800, mask if len(mask)==FOREST_BYTES else bytes(FOREST_BYTES)))
    # Region texts of the Sierra Nevada pack (memory.s REGIONTEXT).
    data = build_disk.region_data(HERE / 'build', 2)
    expected.append((L['region_name'], build_disk.region_texts(data['entry'], data['header'])))
    # RESIDENT: the module directory is filled in by tools/build_disk.py
    # (trunk), then rewritten whole by the region pack.
    resident = bytearray((HERE / 'build/wildres.bin').read_bytes())
    start = L['module_dir'] - 0xB600
    entries = build_disk.DIR_ENTRIES
    directory = slice(start, start + entries * 7)
    steps = [L.until('start', 20000)]
    steps += [f'peek:{address:04X}:{len(data)}' for address, data in expected]
    steps += [f'peek:B600:{len(resident)}']
    # Lot 7 step 5: bank 2 of the MAIN language card, read through $C080
    # (RAM bank 2, write-protected), then the ROM again.
    steps += ['peek:C080', 'peek:D000:4096', 'peek:C082']
    result = a2test.run(disk, steps, timeout=900)
    memory = {address + i: byte for address, row in result.rows
              for i, byte in enumerate(row)}
    for address, data in expected:
        actual = bytes(memory[address + i] for i in range(len(data)))
        assert actual == data, f'resident bytes differ at ${address:04X}'
    actual = bytearray(memory[0xB600 + i] for i in range(len(resident)))
    loaded_directory = bytes(actual[directory])
    actual[directory] = resident[directory]
    assert actual == resident, 'RESIDENT image differs'
    for index in range(entries):
        bank, source, length, window = (loaded_directory[index*7],
            int.from_bytes(loaded_directory[index*7+1:index*7+3], 'little'),
            int.from_bytes(loaded_directory[index*7+3:index*7+5], 'little'),
            int.from_bytes(loaded_directory[index*7+5:index*7+7], 'little'))
        if index == 23:
            assert loaded_directory[index*7:index*7+7] == bytes(7), index   # empty entry
            continue
        if bank & build_disk.BANK_LZ:      # LZ image: window = where its copy lands
            bank &= 0x7F
            assert 0x5800 <= window < 0x6000 or 0x9600 <= window < 0xA200, index
        else:
            assert window in (0x2000, 0x5800, 0x9600, 0x97CE), index
        assert bank in (0, 1, 2, 3) and 0 < length <= 0x2000, index
        assert bank or not (0x2000 <= source < 0x4000 or source < 0x0800), (index, 'reserved aux')
    import json
    layout = json.loads((HERE / 'build/layout.json').read_text())
    card = [(m['address'], build_disk.stored_bytes(HERE / 'build', m))
            for m in layout['trunk_modules'].values() if m['bank'] == 'mlc2']
    code = layout['star_code']
    card.append((code['address'], (HERE / 'build/wildskylc.bin').read_bytes()))
    assert card and all(0xD400 <= a and a + len(d) <= 0xE000 for a, d in card)
    for address, data in card:
        actual = bytes(memory[address + i] for i in range(len(data)))
        assert actual == data, f'main language card differs at ${address:04X}'
    quit_code = bytes(memory[0xD100 + i] for i in range(0x300))
    assert len(set(quit_code)) > 16, 'ProDOS QUIT code expected in $D100-$D3FF of bank 2'
    print(f'  {disk.name}: every resident byte restored, directory sane, '
          f'main language card bank 2 holds {len(card)} images beside the ProDOS QUIT code, '
          f'{result.cycles[-1] / a2test.CPU_HZ:.2f} s to start (menu answered)')


def main():
    mapbin = (HERE / 'build/map.bin').read_bytes()
    check(DISK, mapbin)
    noise = bytearray(mapbin)
    noise[64:] = random.Random(9408).randbytes(len(mapbin) - 64)
    with tempfile.TemporaryDirectory() as tmp:
        check(disk_with(tmp, noise), bytes(noise))
    print('ProDOS preload: OK')


if __name__ == '__main__':
    main()
