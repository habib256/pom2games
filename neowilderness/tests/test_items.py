#!/usr/bin/env python3
"""Exercise item transfers, qualifiers and ground locations in the emulator."""
import struct
import sys
from common import L, DISK, DISK140, a2test, fp, text_screen


def clothing_transfers():
    """Native rounded garment losses must change on every accepted removal.

    Only the clothing header/cache is made native: no travel is performed,
    so this exercises both distributed editions without a geography atlas.
    These twelve initial losses and WORN bits are ADVENTURE's Sierra seed.
    """
    from test_input import command, snapshot, screen

    def thermal(s):
        return (s.step('peek:7028:24').data,
                s.step(L.peek('s_insul', 5)).data,
                s.step(L.peek('clothing_cache', 3)).data)

    for disk in (DISK,):
        outcomes = []
        for verb, place, result in (('DROP', 0, 'GROUND: DOWN PARKA'),
                                     ('PACK', 2, 'PACK: DOWN PARKA'),
                                     ('GET', 2, 'PACK: DOWN PARKA'),
                                     ('TAKE', 3, 'HAND: DOWN PARKA'),
                                     ('CARRY', 3, 'HAND: DOWN PARKA')):
            with a2test.Session(disk) as s:
                s.step(L.until('idle', 20000))
                s.step('poke:7025:01')
                header = struct.pack('<12H', 500,42,46,97,70,54,2000,74,76,148,104,77)
                for k, byte in enumerate(header):
                    s.step(f'poke:{0x7028+k:04X}:{byte:02X}')
                for k, byte in enumerate((0x7E, 0x10, 0)):
                    s.step(L.poke('clothing_cache', byte, k))
                s.step(L.poke('clothing_cache_valid', 0))
                clock = s.step(L.peek('s_hour', 10)).data
                view = s.step('peek:2000:8192').data
                command(s, 'WEAR PARKA')
                worn = thermal(s)
                calls = s.step(L.peek('mli_calls', 2)).data
                assert int.from_bytes(worn[0][2:4], 'little') == 14
                assert fp(worn[1]) == 37
                # A full destination refuses the transfer before changing
                # the native clothing history or the cached insulation.
                if verb != 'DROP':
                    offset = 6 if place == 3 else 4
                    limit = s.step(L.peek('load_limits', 2, offset)).data
                    for k in range(2):
                        s.step(L.poke('load_limits', 0, offset+k))
                    before = snapshot(s)
                    command(s, verb + ' PARKA')
                    assert 'TRANSFER REFUSED' in screen(s)
                    assert snapshot(s) == before
                    assert thermal(s) == worn
                    for k, byte in enumerate(limit):
                        s.step(L.poke('load_limits', byte, offset+k))
                command(s, verb + ' PARKA')
                assert s.step(L.peek('it_place', 1, 2)).data == bytes((place,))
                assert result in screen(s), (verb, screen(s))
                after = thermal(s)
                assert int.from_bytes(after[0][2:4], 'little') == 47
                assert fp(after[1]) == 48
                outcomes.append(after)
                assert s.step(L.peek('mli_calls', 2)).data == calls
                assert s.step(L.peek('s_hour', 10)).data == clock
                assert s.step('peek:2000:8192').data == view
        assert all(value == outcomes[0] for value in outcomes), disk
    print('  both editions: PACK/GET/TAKE/CARRY remove parka protection like DROP; exact rounded losses, atomic load refusals, clock/view preserved')


def main():
    clothing_transfers()
    steps = [L.until('idle', 20000)]
    cases = []
    fields = ('it_place', 'it_pack_lo', 'it_pack_hi', 'it_gnd_lo', 'it_gnd_hi',
              'it_x', 'it_y')

    def command(cmd, **expected):
        steps.extend([f'key:{cmd}\r', 'wait:1', L.until('idle', 6000)])
        steps.extend(L.peek(n, 76) for n in fields)
        steps.extend([L.peek('s_elap', 5), 'peek:0400:1024'])
        cases.append((cmd, expected))

    command('WEAR PARKA', place=(2, 1))
    command('PACK PARKA', place=(2, 2))
    command('CARRY PARKA', place=(2, 3))
    command('REMOVE PARKA', place=(2, 0))
    command('GET PARKA', place=(2, 2))
    command('WEAR COTTON SOCKS', place=(18, 1), other=(6, 1))
    command('DROP COTTON SOCKS', place=(18, 0), other=(6, 1))
    command('WEAR AXE', place=(58, 2), message="CAN'T WEAR")
    command('WEAR SHOES', place=(17, 255), message='NOT ACCESSIBLE HERE')
    command('CARRY HAT', place=(19, 3))
    command('USE COMPASS', message='OK, WHAT NEXT?')
    command('DROP COMPASS', place=(53, 0))
    command('GET COMPASS', place=(53, 2))
    command('GET SNAKEBITE KIT', place=(42, 2), other=(41, 255))
    command('GET SALT TABLETS', place=(48, 2))
    command('GET SEWING KIT', place=(65, 255), other=(41, 255))
    command('DROP AXE', place=(58, 0))
    command('DROP APPLES', place=(37, 0), pack=(37, 0), ground=(37, 80))
    command('GET APPLES', place=(37, 2), pack=(37, 80), ground=(37, 0))
    # A different cell: existing cheese ground stock must stay at the crash.
    steps.extend([L.poke('px', 10, 1), L.poke('py', 10, 1)])
    command('DROP CHEESE', place=(28, 4), pack=(28, 32), ground=(28, 16),
            message='COLLECT THE OTHER GROUND STOCK FIRST')
    command('DROP APPLES', place=(37, 0), pack=(37, 0), ground=(37, 80), cell=(37, 10, 10))
    command('REMOVE HAT', place=(19, 0), cell=(19, 10, 10))
    steps.append(L.poke('px', 11, 1))
    command('GET HAT', place=(19, 0), message='NOT ACCESSIBLE HERE')
    command('GET APPLES', place=(37, 0), pack=(37, 0), ground=(37, 80), message='NOT ACCESSIBLE HERE')
    command('EAT APPLES', ground=(37, 80), message="NOT ACCESSIBLE HERE")
    steps.append(L.poke('px', 10, 1))
    command('GET HAT', place=(19, 2))
    command('CARRY APPLES', place=(37, 2), pack=(37, 80), ground=(37, 0))
    command('DROP', message="NAME AN ITEM")
    command('WEAR BODY', message='NOT IN THIS VERSION')

    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=1800)
    failures = []
    for i, (cmd, expected) in enumerate(cases):
        data = {n: r.mem(L[n], 76, i) for n in fields}
        for key, want in expected.items():
            if key in ('place', 'other'):
                item, value = want
                got = data['it_place'][item]
                ok = got == value
            elif key in ('pack', 'ground'):
                item, value = want
                prefix = 'it_pack' if key == 'pack' else 'it_gnd'
                got = data[prefix + '_lo'][item] | data[prefix + '_hi'][item] << 8
                ok = got == value
            elif key == 'cell':
                item, x, y = want
                got = (data['it_x'][item], data['it_y'][item])
                ok = got == (x, y)
            else:
                got = '\n'.join(text_screen(r.mem(0x400, 1024, i)))
                ok = want in got
            if not ok:
                failures.append(f'{cmd}: {key} expected {want}, got {got}')
        if fp(r.mem(L['s_elap'], 5, i)) != 0:
            failures.append(f'{cmd}: item command advanced time')
    # Consume a ground stock away from the crash.
    steps = [L.until('idle', 20000), 'key:DROP AXE\r', 'wait:1', L.until('idle'),
             'key:GET APPLES\r', 'wait:1', L.until('idle'),
             L.poke('px', 10, 1), L.poke('py', 10, 1),
             'key:DROP APPLES\r', 'wait:1', L.until('idle'),
             'key:EAT APPLES', 'press:\r', L.until('number_idle', 6000), 'key:8\r', 'wait:1', L.until('idle', 6000),
             L.peek('it_gnd_lo', 76), L.peek('it_oz_lo', 76), L.peek('it_pack_lo', 76)]
    consumed = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=1800)
    if (consumed.mem(L['it_gnd_lo'], 76)[37], consumed.mem(L['it_oz_lo'], 76)[37],
            consumed.mem(L['it_pack_lo'], 76)[37]) != (72, 72, 0):
        failures.append('EAT APPLES: did not consume the dropped ground stock')

    # An item left on another cell must disappear from the inventory screen.
    steps = [L.until('idle', 20000), 'key:CARRY HAT\r', 'wait:1', L.until('idle'),
             L.poke('px', 10, 1), L.poke('py', 10, 1),
             'key:DROP HAT\r', 'wait:1', L.until('idle'), L.poke('px', 11, 1),
             'key:INVENTORY\r', 'wait:1', L.until('inventory_key'),
             'key:3', 'wait:1', L.until('inventory_key'), 'peek:0400:1024']
    inventory = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=1800)
    screen = '\n'.join(text_screen(inventory.mem(0x400, 1024)))
    if 'HAT' in screen or 'DOWN PARKA' not in screen:
        failures.append('INVENTORY: incorrect accessibility of ground equipment')

    for failure in failures:
        print(f'FAIL {failure}')
    print(f'{len(cases)} item commands: {"FAIL" if failures else "OK"}')
    sys.exit(bool(failures))


if __name__ == '__main__':
    main()
