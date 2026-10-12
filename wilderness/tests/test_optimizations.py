#!/usr/bin/env python3
"""Native arithmetic and nighttime redraw optimization contracts."""
import re
from common import HERE, DISK, L, a2test


def division():
    entry = L['idle']
    address = L['smalldiv']
    # Execute actual resident code; capture A and the preserved X/Y registers.
    code = bytes((0xA9, 0, 0xA2, 0x5A, 0xA0, 0xA5,
                  0x20, address & 255, address >> 8,
                  0x8D, 0, 0x95, 0x8E, 1, 0x95, 0x8C, 2, 0x95,
                  0x4C, entry & 255, entry >> 8))
    count = 0
    for first in range(1, 129, 16):
        cases = [(n, r) for n in range(first, first + 16) for r in range(n)]
        steps = [L.until('idle', 20000)]
        steps += [f'poke:{entry+i:04X}:{b:02X}' for i, b in enumerate(code)]
        for n, r in cases:
            steps += [f'poke:{entry+1:04X}:{r:02X}', L.poke('divisor', n),
                      L.poke('qlo', 0xA7), f'until:{entry+18:04X}:100',
                      'peek:9500:3', L.peek('qlo'), L.until('idle', 100)]
        result = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=180)
        for i, (n, r) in enumerate(cases):
            expected = r * 256 // n
            assert result.mem(0x9500, 3, i) == bytes((expected, 0x5A, 0xA5)), (n, r)
            assert result.mem(L['qlo'], 1, i) == bytes((expected,)), (n, r, 'qlo')
        count += len(cases)
    print(f'  {count} native divisions: exact quotient, qlo and preserved X/Y: OK')


def boot_copies():
    boot = a2test.labels(HERE / 'build/boot.lbl')
    entry = L['idle']
    code = (HERE / 'build/boot.bin').read_bytes()
    # Restore the transient loader after boot and enter its real copy loop.
    # Stop at check, then return to the fixture without parsing another token.
    steps = [L.until('idle', 20000)]
    steps += [f'poke:{0x5800+i:04X}:{b:02X}' for i, b in enumerate(code)]
    stub = bytes((0xA2, 0, 0xA0, 0, 0x4C, boot['copy'] & 255, boot['copy'] >> 8))
    steps += [f'poke:{entry+i:04X}:{b:02X}' for i, b in enumerate(stub)]
    steps += [f'poke:{boot["check"]+i:04X}:{b:02X}' for i, b in
              enumerate((0x4C, entry & 255, entry >> 8))]
    cases = []
    for dest in (0x8100, 0x81FD):
        for distance in (1, 2, 17, 256, 4095):
            for count in (3, 17, 18, 255):
                match = dest - distance
                seed = bytes((i * 37 + 19) & 255 for i in range(min(distance, count)))
                expected = bytes(seed[i % distance] for i in range(count))
                steps += [f'poke:{match+i:04X}:{b:02X}' for i, b in enumerate(seed)]
                for name, value in (('match', match), ('dest', dest), ('remain', 0x203)):
                    steps += [boot.poke(name, value), boot.poke(name, value >> 8, 1)]
                steps += [f'poke:{entry+1:04X}:{count:02X}',
                          boot.until('check', 100), f'peek:{dest:04X}:{count}',
                          boot.peek('dest', 2), boot.peek('remain', 2), L.until('idle', 100)]
                cases.append((bytes(expected), dest + count, 0x203 - count))
    result = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=180)
    for i, (expected, dest, remain) in enumerate(cases):
        assert result.dumps[3*i] == expected, (i, 'copied bytes')
        assert result.mem(boot['dest'], 2, i) == dest.to_bytes(2, 'little'), i
        assert result.mem(boot['remain'], 2, i) == remain.to_bytes(2, 'little'), i
    print('  40 native boot copies: overlap, page crossings, 255 bytes and 4 KB distance: OK')


def night_redraw():
    with a2test.Session(DISK) as s:
        s.step(L.until('idle', 20000))
        s.step(L.poke('nature_frequency', 0))
        s.step('key:REST 16 H')
        s.step('press:\\r')
        s.step(L.until('do_command', 20000))
        s.step(L.until('idle', 20000))
        assert s.step(L.peek('night')).data == b'\x01'
        s.step('key:DRINK 1 OZ')
        s.step('press:\\r')
        s.step(L.until('do_command', 20000))
        result = s.step(f'pcprof:{L["idle"]:04X}:20000')
        pcs = {int(a, 16): int(c) for a, c in
               re.findall(r'^pc ([0-9A-F]{4}) (\d+)$', result.out, re.M)}
        # Entry LDX immediate takes two cycles. One clear suffices even when
        # a command restores its picture through finish_simulation.
        assert pcs.get(L['clear_rows'], 0) == 2, 'night picture cleared twice'
    print('  nighttime DRINK restores its picture with one terrain clear: OK')


if __name__ == '__main__':
    division()
    boot_copies()
    night_redraw()
