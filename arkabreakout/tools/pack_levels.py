#!/usr/bin/env python3
"""Validate 60 named 12x8 boards and write six DOS-loadable 580-byte packs.

Each pack contains ten records: 48 bytes (low nibble first, 15=steel),
then ten ASCII name bytes padded on the right. All hit tiles must be reachable
from below through non-steel cells; boards and names must be distinct.
"""
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1]
VALUES = {'.': 0, '1': 1, '2': 2, '3': 3, '#': 255}

def load(path=root / 'src' / 'levels.txt'):
    lines = [l.rstrip() for l in path.read_text().split('\n') if not l.startswith(';')]
    levels, i = [], 0
    while i < len(lines):
        if not lines[i]:
            i += 1
            continue
        name, rows = lines[i], lines[i + 1:i + 9]
        assert name.isalpha() and name.isupper() and len(name) <= 10, name
        assert len(rows) == 8 and all(len(r) == 12 and set(r) <= set(VALUES) for r in rows), name
        levels.append((name, [VALUES[c] for r in rows for c in r]))
        i += 9
    return levels

def count():
    return 60

def check(levels):
    n = count()
    assert len(levels) == n, len(levels)
    assert len({name for name, _ in levels}) == n and len({tuple(b) for _, b in levels}) == n
    for name, board in levels:
        assert any(0 < v < 255 for v in board), name
        seen = {i for i in range(84, 96) if board[i] != 255}
        pending = list(seen)
        while pending:
            i = pending.pop(); x, y = i % 12, i // 12
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                n = ny * 12 + nx
                if 0 <= nx < 12 and 0 <= ny < 8 and n not in seen and board[n] != 255:
                    seen.add(n); pending.append(n)
        sealed = [i for i, v in enumerate(board) if 0 < v < 255 and i not in seen]
        assert not sealed, (name, 'steel seals', sealed)

if __name__ == '__main__':
    levels = load(); check(levels)
    nib = lambda v: 15 if v == 255 else v
    out = Path(sys.argv[1]) if len(sys.argv)>1 else root / 'build'
    out.mkdir(parents=True, exist_ok=True)
    for pack in range(6):
        data = bytearray()
        for name, board in levels[pack*10:pack*10+10]:
            data += bytes(nib(board[i]) | nib(board[i+1]) << 4 for i in range(0,96,2))
            data += name.ljust(10).encode('ascii')
        (out / f'levels{pack+1}.bin').write_bytes(data)
