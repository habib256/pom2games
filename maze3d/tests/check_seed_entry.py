#!/usr/bin/env python3
"""Drive the real title/seed editor and compare generated dungeon state."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev/tools"))
import a2test
from check_generation import verify

L = a2test.labels(ROOT / "maze3d/build/maze3d.lbl")
DISK = ROOT / "dist/MAZE3D.dsk"


def keys(text):
    # A redraw takes longer than a2shot's default three frames per key.
    return [step for char in text for step in (f"key:{char}", "wait:20")]


def run(steps):
    return a2test.run(DISK, ["wait:2200", *steps], emulator=a2test.A2SHOT)


def dungeon(text, seed):
    result = run([*keys("S" + text), "wait:700", L.peek("p_seed_lo", 2),
                  "peek:1000:77", "peek:10a0:32"])
    assert result.mem(L["p_seed_lo"], 2) == seed.to_bytes(2, "little")
    grid, mobs = result.mem(0x1000, 77), result.mem(0x10a0, 32)
    verify(list(grid), list(mobs))
    return grid, mobs


def main():
    title = run([L.peek("front_page"), "peek:2000:16384"])
    page = int(title.mem(L["front_page"], 1)[0] != 0)
    actual = title.mem(0x2000, 16384)[page * 8192:(page + 1) * 8192]
    original_art = (ROOT / "maze3d/assets/title.hgr").read_bytes()
    assert a2test.hgr_visible(actual)[:168 * 40] == a2test.hgr_visible(original_art)[:168 * 40]
    # Digits must actually appear on the visible HGR page, not only in RAM.
    screens = []
    for spelling in ("SBE", "SBF"):
        editor = run([*keys(spelling), L.peek("front_page"), "peek:2000:16384"])
        page = int(editor.mem(L["front_page"], 1)[0] != 0)
        screens.append(a2test.hgr_visible(editor.mem(0x2000, 16384)[page * 8192:(page + 1) * 8192]))
    assert screens[0] != screens[1], "edited digits are missing from the display"
    original = dungeon("BEEF\r", 0xBEEF)
    assert dungeon("beef\r", 0xBEEF) == original
    assert dungeon("BZEE0\x08F9\r", 0xBEEF) == original  # invalid, erase, excess digit
    assert dungeon("\x08BEE0\x7fF\r", 0xBEEF) == original  # empty erase and DELETE
    assert dungeon("BE\rEF\r", 0xBEEF) == original  # premature RETURN
    assert dungeon("0001\r", 1) != original
    dungeon("FFFF\r", 0xFFFF)
    # Zero stays editable; deleting one digit allows correction to 0001.
    assert dungeon("0000\r\x081\r", 1) == dungeon("0001\r", 1)
    cancelled = run([*keys("S12\x1b"), L.peek("quit_flag"), L.peek("seed_count"),
                     *keys("R\x08\x08BEEF\r"), "wait:700", L.peek("p_seed_lo", 2)])
    assert cancelled.mem(L["quit_flag"], 1) == b"\0"
    assert cancelled.mem(L["p_seed_lo"], 2) == b"\xef\xbe"
    # A stored record must reconstruct the same floor as manual entry.
    checksum = 99 ^ 0xEF ^ 0xBE ^ 0xA5
    record = run(["poke:1f04:63", "poke:1f05:ef", "poke:1f06:be",
                  f"poke:1f07:{checksum:02x}", *keys("R"), "wait:700",
                  "peek:1000:77", "peek:10a0:32"])
    assert (record.mem(0x1000, 77), record.mem(0x10a0, 32)) == original
    print("seed entry: repeatable, case insensitive, editable, cancellable, matches record replay")


if __name__ == "__main__":
    main()
