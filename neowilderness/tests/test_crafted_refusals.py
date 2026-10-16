#!/usr/bin/env python3
"""Crafted transfers report every failing limit without changing stock."""
from common import L, DISK, a2test, text_screen
from test_object_actions import command, IDLE


def word(s, name, offset=0):
    return int.from_bytes(s.step(L.peek(name, 2, offset)).data, 'little')


def limit(s, offset, free):
    value = word(s, 'load_used', offset) + free
    s.step(L.poke('load_limits', value & 255, offset))
    s.step(L.poke('load_limits', value >> 8, offset + 1))


def result(s):
    return ' '.join(' '.join(r[:39].split()) for r in
                    text_screen(s.step('peek:0400:1024').data)[20:23])


def main():
    with a2test.Session(DISK) as s:
        s.step(IDLE)
        limit(s, 6, 50)
        command(s, 'CARRY ROCK')
        text = result(s)
        assert 'WEIGHT: NEED 100 OZ. FREE 43 OZ.' in text, text
        assert 'HANDS: NEED 100 IN3. FREE 50 IN3.' in text, text
        assert s.step(L.peek('cr_b1', 1, 3)).data == b'\0'
        limit(s, 0, 200)
        limit(s, 4, 99)
        command(s, 'PACK ROCK')
        text = result(s)
        assert 'PACK: NEED 100 IN3. FREE 99 IN3.' in text, text
        assert 'WEIGHT:' not in text, text
        assert s.step(L.peek('cr_b1', 1, 3)).data == b'\0'
    print('Crafted refusals: simultaneous weight/hands limits and PACK-only limit, stock preserved: OK')


if __name__ == '__main__':
    main()
