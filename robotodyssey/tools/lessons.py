#!/usr/bin/env python3
"""lessons.py [NAME...]: dump the rooms and texts of the training worlds.

Reads the extracted segments (build/files/<side>/BBB_AAAA.bin) through
memimg.py. World tables used (world loaded at $6000):
  $6300+obj        object room (object 0 = the player)
  $6EC0/$6F00/$6F40/$6F80+room  room above / below / right / left
                   (the room itself = no exit)
  $7880+t room, $7900+t X, $7980+t Y, $7A00+t style (2 = large),
  $7A80+t font, $7B00+t colour, $7B80+t / $7C00+t text address (lo/hi):
  128 texts, room $3F = unused (same layout as docs/logic/world.md)
Texts are high-bit ASCII, $8D new line, $00 end.
Rooms are listed in breadth-first order from the player's room.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memimg  # noqa: E402

DIRS = (('haut', 0x6EC0), ('bas', 0x6F00), ('droite', 0x6F40), ('gauche', 0x6F80))


def text(m, a, limit=2000):
    out = []
    while m[a] and len(out) < limit:
        out.append('/' if m[a] == 0x8D else chr(m[a] & 0x7F))
        a += 1
    return ''.join(out)


def world(m):
    texts = {}
    for t in range(128):
        room = m[0x7880 + t]
        ptr = m[0x7B80 + t] | m[0x7C00 + t] << 8
        if room == 0x3F or ptr < 0x6000:
            continue
        texts.setdefault(room, []).append(
            (t, m[0x7900 + t], m[0x7980 + t], m[0x7A00 + t], m[0x7A80 + t], m[0x7B00 + t], ptr, text(m, ptr)))
    start = m[0x6300]
    order, seen, queue = [], {start}, [start]
    while queue:
        r = queue.pop(0)
        order.append(r)
        for _, base in DIRS:
            n = m[base + r]
            if n < 0x40 and n not in seen:
                seen.add(n)
                queue.append(n)
    for r in sorted(texts):
        if r not in seen:
            order.append(r)
    return start, order, texts


def dump(name):
    side, segs = memimg.LESSONS[name]
    m = memimg.build(side, segs)
    start, order, texts = world(m)
    print('# %s (%s) : salle de départ $%02X' % (name, side, start))
    for r in order:
        ex = ' '.join('%s=$%02X' % (d, m[b + r]) for d, b in DIRS if m[b + r] != r)
        print('\n## salle $%02X  [%s]' % (r, ex))
        for t, x, y, st, fo, co, ptr, s in texts.get(r, []):
            print('  t%02X x=%02X y=%02X style=%X police=%X coul=%X $%04X  %s' % (t, x, y, st, fo, co, ptr, s))


def main():
    names = sys.argv[1:] or [n for n in memimg.LESSONS]
    for n in names:
        dump(n)
        print()


if __name__ == '__main__':
    main()
