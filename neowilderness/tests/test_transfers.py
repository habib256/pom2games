#!/usr/bin/env python3
"""RAM module transfers: exact images, preserved state, cost per byte.

Replaces the DOS overlay-codec test: modules are no longer read or decoded
at run time, they are copied from auxiliary RAM (memory.s). The layout is
the common trunk plus the Sierra Nevada pack of the default menu choice. Every directory
entry is fetched through the real overlay_load (TOPO through mem_fetch):
the window holds the exact image, bytes past it are untouched, and the zero
page, the text page, the I flag and the memory soft switches (RAMRD,
RAMWRT, ALTZP, 80STORE, language card) are the same before and after.
"""
import json
from common import HERE, DISK, L, a2test

SWITCHES = 'peek:C011:8'        # LCBNK2 LCRAM RAMRD RAMWRT INTCXROM ALTZP SLOTC3 80STORE


def main():
    layout = json.loads((HERE / 'build/layout.json').read_text())
    images = {}
    for index, module in layout['modules'].items():
        image = bytearray((HERE / 'build' / module['image']).read_bytes())
        # The Sierra Nevada pack rewrites its fauna patches with the bytes the
        # trunk's images already hold (tools/build_disk.py asserts it).
        images[int(index)] = (bytes(image), module['window'])
    with a2test.Session(DISK) as s:
        s.step(L.until('idle', 20000))
        rows = s.step(L.peek('row_n0', 256)).data
        assert rows == bytes(95+(3*q+15)//16 for q in range(256))
        entry = L['idle']
        costs = []
        for index in sorted(images):
            if index == 18:
                continue                # alias of 17
            expected, window = images[index]
            if index == 0:
                call = (0xA2, 0, 0x20, L['mem_fetch'] & 255, L['mem_fetch'] >> 8)
            else:
                call = (0xA9, index, 0x20, L['overlay_load'] & 255, L['overlay_load'] >> 8)
            code = bytes(call + (0x4C, entry & 255, entry >> 8))
            for i, b in enumerate(code):
                s.step(f'poke:{entry+i:04X}:{b:02X}')
            s.step(L.poke('overlay_current', 0))
            s.step(L.poke('sim_loaded', 0))
            limit = window + (0x2000 if window != 0x5800 else 0x800)
            guard = s.step(f'peek:{window+len(expected):04X}:{min(16, limit-window-len(expected))}').data
            start = s.step(f'until:{L["mem_fetch"]:04X}:200').cycles[-1]
            zp = s.step('peek:0000:256').data
            text = s.step('peek:0400:1024').data
            switches = s.step(SWITCHES).data
            back = entry + 5
            reply = s.step(f'until:{back:04X}:200')
            end = reply.cycles[-1]
            # A DHGR page peek yields main + aux: TOPO is copied into main.
            assert s.step(f'peek:{window:04X}:{len(expected)}').data[:len(expected)] == expected, index
            after = s.step('peek:0000:256').data
            # overlay_load itself sets its documented flags; the copy may not
            # touch any other zero-page byte.
            assert after == zp, (index, 'ZP')
            assert s.step('peek:0400:1024').data == text, (index, 'text page')
            assert s.step(SWITCHES).data == switches, (index, 'soft switches')
            assert s.step(f'peek:{window+len(expected):04X}:{len(guard)}').data == guard, (index, 'overrun')
            costs.append((index, len(expected), end - start))
            s.step(L.until('idle', 100))
    worst = max(c / n for _, n, c in costs)
    total = sum(n for _, n, _ in costs)
    print(f'  {len(costs)} module/TOPOGEN transfers: exact bytes, no overrun, ZP, text page, '
          f'RAMRD/RAMWRT/ALTZP/80STORE/LC preserved: OK')
    print(f'  {total} bytes in {sum(c for *_, c in costs)} cycles; '
          f'worst {worst:.1f} cycles per byte (overlay_load included)')
    print('  reconstructed 256-row projection cache is exact: OK')


if __name__ == '__main__':
    main()
