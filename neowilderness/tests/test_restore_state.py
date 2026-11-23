#!/usr/bin/env python3
"""RESTORE rebuilds the load used by travel and requires a complete slot."""
import tempfile
from pathlib import Path

from test_save import DISK, Game, Image, L, LIMIT, STATE, SV_HEAD, a2test, entry, patch_file


def main():
    size = SV_HEAD + STATE
    with tempfile.TemporaryDirectory() as tmp:
        disk = Path(tmp) / 'restore.po'
        image = bytearray(DISK.read_bytes())
        disk.write_bytes(image)
        with a2test.Session(disk) as s:
            g = Game(s)
            s.step(L.until('idle', LIMIT))
            load = g.peek(L['load_used'], 8)
            s.step('key:SAVE 1\r')
            s.step(L.until('sv_gather', LIMIT))
            s.step(L.until('sv_close_file', LIMIT))
            slot = g.peek(0x9C00, size)
            s.step(L.until('idle', LIMIT))
            g.type('DROP CHEESE')
            assert g.peek(L['load_used'], 8) != load
            g.type('RESTORE 1')
            assert g.result().startswith('GAME 1 RESTORED.'), g.result()
            assert g.peek(L['load_used'], 8) == load

        patch_file(image, 'NEOWILD.S1', 0, slot)
        at = image.index(entry(Image(bytes(image)), 'NEOWILD.S1'))
        image[at + 0x15:at + 0x18] = (size - 1).to_bytes(3, 'little')
        disk.write_bytes(image)
        with a2test.Session(disk) as s:
            g = Game(s)
            s.step(L.until('idle', LIMIT))
            g.type('DROP CHEESE')
            before = g.state()
            s.step('key:RESTORE 1\r')
            s.step(L.until('sv_restore', LIMIT))
            # The unread tail already matches the saved byte in memory.
            s.step(f'poke:{0x9C00 + size - 1:04X}:{slot[-1]:02X}')
            s.step(L.until('idle', LIMIT))
            assert g.result().startswith('GAME 1 IS DAMAGED.'), g.result()
            assert g.state() == before
    print('RESTORE: travel load rebuilt and truncated slot rejected with journey intact')


if __name__ == '__main__':
    main()
