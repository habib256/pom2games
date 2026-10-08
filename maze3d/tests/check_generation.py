#!/usr/bin/env python3
"""Exercise real Maze3D generation in the Apple II emulator across seeds."""

import argparse
from collections import Counter
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev/tools"))
import a2test  # noqa: E402
DISK = ROOT / "dist/MAZE3D.dsk"


def neighbours(grid: list[int], cell: int) -> list[int]:
    x, y = cell % 11, cell // 11
    result = []
    if y and grid[cell] & 1:
        result.append(cell - 11)
    if x < 10 and grid[cell] & 2:
        result.append(cell + 1)
    if y < 6 and grid[cell + 11] & 1:
        result.append(cell + 11)
    if x and grid[cell - 1] & 2:
        result.append(cell - 1)
    return result


def verify(grid: list[int], mobs: list[int]) -> None:
    assert len(grid) == 77 and len(mobs) == 32
    assert [i for i, cell in enumerate(grid) if cell & 0x80] == [0]
    relics = [i for i, cell in enumerate(grid) if cell & 8]
    chests = [i for i, cell in enumerate(grid) if cell & 4]
    room = [i for i, cell in enumerate(grid) if cell & 16]
    assert len(relics) == 1 and len(chests) == 3 and len(room) == 4
    top = min(room)
    assert set(room) == {top, top + 1, top + 11, top + 12}
    assert relics == [top + 12]
    assert grid[top] & 2 and grid[top + 11] & 3 == 3 and grid[top + 12] & 1
    assert not ({0, 76} & (set(relics) | set(chests)))
    edges = 0
    for cell, flags in enumerate(grid):
        x, y = cell % 11, cell // 11
        assert not (x == 10 and flags & 2)
        assert not (y == 0 and flags & 1)
        edges += bool(flags & 1) + bool(flags & 2)
    assert edges >= 79, f"only {edges} passages, expected at least three extra loops"
    reached = {0}
    frontier = [0]
    for cell in frontier:
        for other in neighbours(grid, cell):
            if other not in reached:
                reached.add(other)
                frontier.append(other)
    assert len(reached) == 77
    stacks = Counter(zip(mobs[:8], mobs[8:16]))
    assert max(stacks.values()) <= 3, "more than three monsters on one cell"
    for index in range(8):
        x, y = mobs[index], mobs[index + 8]
        assert 0 <= x < 11 and 0 <= y < 7
        cell = 11 * y + x
        assert cell not in {0, 76, *relics, *chests}
        assert mobs[index + 16] in (0, 1, 2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--disk", type=Path, default=DISK)
    parser.add_argument("--a2shot", type=Path, default=a2test.A2SHOT,
                        help="a2run (portable) works too")
    args = parser.parse_args()
    for index in range(args.samples):
        low = (index * 73 + 11) & 255
        high = (index * 29 + 37) & 255
        steps = [
            "wait:2200", f"poke:0056:{low:02x}", f"poke:0057:{high:02x}",
            "key:X", "wait:700", "peek:1000:77", "peek:10a0:32",
        ]
        run = a2test.run(args.disk, steps, emulator=args.a2shot, timeout=20)
        try:
            verify(list(run.mem(0x1000, 77)), list(run.mem(0x10A0, 32)))
        except AssertionError as error:
            raise AssertionError(f"seed {index} ({high:02X}{low:02X}): {error}") from error
    print(f"{args.samples} generated floors: connected, keyed, three caches, valid monsters")


if __name__ == "__main__":
    main()
