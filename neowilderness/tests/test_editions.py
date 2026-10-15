#!/usr/bin/env python3
"""The two editions (14 October 2026, tools/build_disk.py EDITIONS):

- Neowilderness, dist/NEOWILDERNESS.po: a 140 KB 5.25-inch ProDOS volume
  (Disk II), the Sierra Nevada alone: NEOWILD.DAT without the five other
  packs, the start menu with one scenario (key 1; 2-6 refused; the free
  journey and the preparation ask no region), the hall of fame with the
  Sierra's block only, the five saved games;
- NeoWildernessXL, dist/NEOWILDERNESSXL.po: an 800 KB 3.5-inch volume (the
  SmartPort card of slot 5 in a2shot), the six scenarios.

Same game, same loader: src/boot.s ld_regions (1 or 6, written by
build_disk) picks the menu parts of tools/genmenu.py and bounds the hall
of fame (src/hof_menu.s hm_regions; NEOWILD.END has its own copy).
Docs/MEMORY.md 14: XL reads CAMP, MEDVIEW, TREE and ORIENT by block from
NEOWILD.BLK (directory bank BANK_DISK). Since lot 4 (docs/MEMORY.md 16) both
editions have NEOWILD.BLK: the FORAGE module (31, the SIM window) on both,
TREE and ORIENT on the 140 KB edition too. A copy whose NEOWILD.BLK moved
(a file-by-file copy) is refused by the loader with a message.

Lot 4 on both editions (forage_play): small game caught with the bait and
the trap, cooked on a fire, eaten (docs/FORAGE.md); the read of the FORAGE
module timed from the gate to its first instruction.
"""
import json
import struct
import sys
import tempfile
from pathlib import Path
from common import HERE, L, DISK, DISK140, a2test, text_screen

sys.path.insert(0, str(HERE.parent / 'dev/tools/prodos'))
from read_volume import Image   # noqa: E402

LIMIT = 40000
XL_DISK = (0, 4, 9, 16, 18, 19, 20, 26, 31)    # build_disk.py EDITIONS + ALWAYS_DISK (16: STATUS, XL)
SMALL_DISK = (0, 9, 18, 19, 20, 26, 31)    # (0: TOPOGEN, 9: CRAFT, 18: the campfire, 31: FORAGE)


def files(disk):
    img = Image(disk.read_bytes())
    return img, {bytes(e[1:1 + (e[0] & 15)]).decode('ascii'): e for e in img.entries(2) if e[0] & 15}


def screen(s):
    return text_screen(s.step('peek:0400:1024').data)


def volume_checks():
    small, big = DISK140.read_bytes(), DISK.read_bytes()
    assert len(small) == 280 * 512 and len(big) == 1600 * 512, (len(small), len(big))
    _, f140 = files(DISK140)
    _, fxl = files(DISK)
    for names in (f140, fxl):
        assert {'PRODOS', 'NEOWILD.SYSTEM', 'NEOWILD.DAT', 'NEOWILD.END', 'NEOWILD.HOF',
                'NEOWILD.SAV'} <= set(names), sorted(names)
        assert {f'NEOWILD.S{g}' for g in range(1, 6)} <= set(names), 'five saved games'
    assert 'NEOWILD.BLK' in fxl and 'NEOWILD.BLK' in f140, 'NEOWILD.BLK on both'
    sys.path.insert(0, str(HERE / 'tools'))
    import build_disk
    for name, disk_modules in (('layout.json', XL_DISK), ('layout-140.json', SMALL_DISK)):
        layout = json.loads((HERE / 'build' / name).read_text())
        assert sorted(map(int, layout['disk']['modules'])) == list(disk_modules), name
        for index in (4, 16, 19, 20, 26):
            on_disk = layout['trunk_modules'][str(index)]['bank'] == 'disk'
            assert on_disk == (index in disk_modules), (name, index)
    for disk, disk_modules in ((DISK, XL_DISK), (DISK140, SMALL_DISK)):
        img, names = files(disk)
        data = img.read(names['NEOWILD.DAT'])
        # The trunk's directory (RESIDENT record at $B600, memory.s module_dir).
        memory = {}
        import test_pack_boot
        test_pack_boot.replay(data[:json.loads((HERE / 'build' / (
            'layout.json' if disk == DISK else 'layout-140.json')).read_text())['dat_file']['marks'][0]],
            memory, False)
        directory = bytes(memory[0, L['module_dir'] + i] for i in range(build_disk.DIR_ENTRIES * 7))
        banks = {i: struct.unpack_from('<BHHH', directory, i * 7)[0] for i in (4, 16, 18, 19, 20, 26, 31)}
        assert all((b == build_disk.BANK_DISK) == (i in disk_modules) for i, b in banks.items()), banks
    size = lambda e: int.from_bytes(e[0x15:0x18], 'little')
    assert size(f140['NEOWILD.DAT']) < size(fxl['NEOWILD.DAT']) - 30000, 'five packs fewer'
    print(f'  volumes: 140 KB ({size(f140["NEOWILD.DAT"])} bytes of NEOWILD.DAT) and 800 KB '
          f'({size(fxl["NEOWILD.DAT"])}), the five saved games on both; NEOWILD.BLK '
          f'and the BANK_DISK entries: XL {XL_DISK}, 140 KB {SMALL_DISK} (the campfire on '
          f'both, tests/test_fire.py): OK')


def moved_blk():
    """A copy whose NEOWILD.BLK header block holds something else."""
    for disk, name in ((DISK, 'layout.json'), (DISK140, 'layout-140.json')):
        layout = json.loads((HERE / 'build' / name).read_text())
        first = layout['disk']['first_block']
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / 'moved.po'
            image = bytearray(disk.read_bytes())
            image[first * 512:first * 512 + 512] = bytes(512)
            copy.write_bytes(image)
            with a2test.Session(copy) as s:
                s.step(L.until('ld_wait', LIMIT))
                text = '\n'.join(screen(s))
        assert 'NEOWILD.BLK HAS MOVED' in text, (disk.name, text)
    print('  both editions with NEOWILD.BLK moved: refused at boot with a message: OK')


def forage_play():
    """Lot 4 on both editions: small game here, USE BAIT, USE TRAP, CATCH
    GAME 2 h (the first draw imposed under p = .084), MAKE FIRE, COOK GAME
    from the ground 1 h (cooked: 77 h), EAT GAME 4 oz (300 kcal, salt).
    The FORAGE module's read is timed (cycles from forage_gate to $9600)."""
    import re
    from test_forage import Port, run, seed_for
    for disk in (DISK, DISK140):
        with a2test.Session(disk) as s:
            s.step(L.until('idle', LIMIT))
            port = Port(s)
            port.poke('nature_frequency', 0)
            port.reset()
            port.poke('fg_b2', 0, 4)        # small game sighted here
            port.poke('resource_seen', 1)
            for line in ('USE BAIT', 'USE TRAP'):
                _, text, _, _ = run(port, line)
                assert 'OK, WHAT NEXT?' in text, (disk.name, line, text)
            seed = seed_for(.05, 1)
            for i in range(4):
                s.step(L.poke('weather_seed', seed >> 8 * i & 255, i))
            s.step('key:CATCH GAME')
            s.step('press:\\r')
            a = int(re.search(r'cycles=(\d+)', s.step(L.until('forage_gate', LIMIT)).out)[1])
            b = int(re.search(r'cycles=(\d+)', s.step(f'until:9600:{LIMIT}').out)[1])
            reads = port.bytes('mli_reads', 2)
            s.step(L.until('keyboard_wait', LIMIT))
            s.step('key:2')
            s.step('press:\\r')
            s.step(L.until('idle', 60000))
            caught = port.pile(4)
            assert port.byte('fg_b2', 4) == 1 and caught['w7'] >= 4, (disk.name, caught)
            assert port.counter(11 + 4) > 0, 'its ground counter'
            for line in ('USE MATCHES', 'MAKE FIRE'):
                run(port, line)
            assert port.byte('fire_on') == 1, disk.name
            before = port.pile(4)['w7']
            _, text, _, _ = run(port, 'COOK GAME', [str(before), '1'])  # > 15 + .6 oz minutes
            assert 'OK, WHAT NEXT?' in text and port.counter(11 + 4) >= 70, (disk.name, text)
            eaten, salt = port.float('s_eaten'), port.bytes('exposure_counter', 2)
            run(port, 'EAT GAME', ['4'])
            assert port.pile(4)['w7'] == before - 4, (disk.name, port.pile(4))
            assert abs(port.float('s_eaten') - eaten - 300) < 1e-6, disk.name
            salt2 = port.bytes('exposure_counter', 2)
            salt, salt2 = (int.from_bytes(v, 'little', signed=True) for v in (salt, salt2))
            assert salt - salt2 == 200, (salt, salt2)
            print(f'  {disk.name}: caught {caught["w7"]} oz of game, cooked {before} oz, ate 4 '
                  f'(+300 kcal, salt -200); FORAGE read in {b - a} cycles '
                  f'({(b - a) / a2test.CPU_HZ:.3f} s emulated): OK')


def menus():
    with a2test.Session(DISK) as s:
        s.step(L.until('menu_key', LIMIT))
        rows = screen(s)
        assert 'NEOWILDERNESS XL' in rows[0] and rows[7].startswith('6 CHILE'), rows[:12]
        assert rows[9].startswith('7 FREE JOURNEY    ANY REGION'), rows[9]
    with a2test.Session(DISK140) as s:
        s.step(L.until('menu_key', LIMIT))
        rows = screen(s)
        assert rows[0].startswith(' NEOWILDERNESS - CHOOSE') and 'XL' not in rows[0], rows[0]
        assert rows[2].startswith('1 SIERRA NEVADA') and not rows[3].strip(), rows[:6]
        assert rows[4].rstrip() == '7 FREE JOURNEY    NOT RANKED', rows[4]
        assert rows[12].startswith('CHOICE (RETURN = 1, 1/7, P, H, Q)?'), rows[12]
        # 2..6 are refused (a bell, the same prompt); 7 asks the level at once.
        s.step('key:3')
        s.step(L.until('menu_key', LIMIT))
        assert s.step(L.peek('ld_region')).data[0] == 0
        s.step('key:7')
        s.step(L.until('menu_key', LIMIT))
        assert 'LEVEL 1-10' in screen(s)[12], screen(s)[12]
        assert s.step(L.peek('ld_region')).data[0] == 2 and s.step(L.peek('ld_free')).data[0] == 1
        s.step('key:\r')
        s.step(L.until('idle', LIMIT))
        assert s.step(L.peek('region_number')).data[0] == 2
    print('  menus: XL six scenarios; 140 KB the Sierra alone, 2-6 refused, '
          'free journey without a region question, then the journey: OK')


def hall():
    for disk, blocks in ((DISK, 6), (DISK140, 1)):
        with a2test.Session(disk) as s:
            s.step(L.until('menu_key', LIMIT))
            s.step('key:H')
            s.step(L.until('menu_key', LIMIT))
            text = '\n'.join(screen(s))
            shown = sum(f'{k} ' in text and name in text for k, name in
                        ((1, 'SIERRA NEVADA'), (2, 'BRITISH COLUMBIA'), (3, 'BURMA'),
                         (4, 'NEW GUINEA'), (5, 'BOLIVIA'), (6, 'CHILE')))
            assert shown == blocks, (disk.name, shown, text)
    print('  hall of fame: six blocks on XL, the Sierra alone on 140 KB: OK')


def pages():
    """Docs/MENUS.md 9 (decision of 15 October 2026): the MouseText pages are
    NeoWildernessXL's; the 140 KB edition keeps its plain 80-column pages
    and its primary character set out of CRAFT."""
    from common import text_screen, is_status
    idle = L.until('idle', LIMIT)
    for disk, xl in ((DISK, True), (DISK140, False)):
        with a2test.Session(disk) as s:
            s.step(idle)
            altchar = s.step('peek:C01E').data[0] >> 7
            s.step('key:STATUS\\r')
            s.step(L.until('status_key', LIMIT))
            s.step('wait:2')
            rows = text_screen(s.step('peek:0400:1024').data)
            if xl:
                assert altchar == 1 and is_status(rows), (altchar, rows)
                # The values of the shared page in their post-its: the body
                # temperature by BODY, the felt one in LOCAL.
                from common import fp
                import re
                body = fp(s.step(L.peek('s_body', 5)).data)
                felt = int.from_bytes(s.step(L.peek('felt_temp', 2)).data, 'little', signed=True)
                assert re.match(rf'\u258fBODY    {body:.1f}F', rows[7]), rows[7]
                assert re.search(rf' FEELS  {felt}F', rows[4]), rows[4]
                # Docs/MENUS.md 9.3: every page's post-its, from the raw
                # screen codes, the six pages in their cycle (RIGHT).
                from common import PAGES, postit_errors, page_frame
                for k, page in enumerate(PAGES):
                    if k:
                        s.step('key:\\>')
                        s.step('wait:2')
                        s.step(L.until('keyboard_wait', LIMIT))
                    mem = s.step('peek:0400:1024').data
                    rows = text_screen(mem)
                    assert page_frame(rows, page) and not postit_errors(mem, page), \
                        (page, postit_errors(mem, page), rows)
                s.step('key:\\e')
            else:
                assert altchar == 0 and is_status(rows, False), rows[:3]
                assert rows[23].startswith('T TOPO') and rows[23].rstrip().endswith('ESC/DOWN: VIEW'), rows[23]
                # The plain pages keep no MouseText cell ($40-$5F) at all
                # (but CRAFT, whose glyphs both editions show, ALTCHARSET on).
                for k in range(6):
                    if k:
                        s.step('key:\\>')
                        s.step('wait:2')
                        s.step(L.until('keyboard_wait', LIMIT))
                    mem = s.step('peek:0400:1024').data
                    page = mem[:1024] + mem[1024:2048]
                    assert k == 2 or not any(0x40 <= c < 0x60 for c in page), k
                s.step('key:\\e')
    print('  pages: MouseText post-its on the six XL pages (ALTCHARSET on), the plain pages on 140 KB: OK')


def main():
    volume_checks()
    moved_blk()
    pages()
    menus()
    hall()
    forage_play()
    print('Editions (Neowilderness 140 KB, NeoWildernessXL 800 KB): OK')


if __name__ == '__main__':
    main()
