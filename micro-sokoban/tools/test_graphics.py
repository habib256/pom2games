#!/usr/bin/env python3
"""Check real displayed pages, hidden-page drawing and screen round trips."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'micro-sokoban'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--a2run', type=Path, default=ROOT / 'dev/tools/a2run/a2run')
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/MICRO-SOKOBAN.dsk')
    args = ap.parse_args()
    labels = {n: int(a, 16) for a, n in re.findall(
        r'^al ([0-9A-F]+) \.(\w+)$', (GAME / 'build/micro_sokoban.lbl').read_text(), re.M)}

    def peek(name, count=1):
        return f'peek:{labels[name]:04X}:{count}'

    boot = ['wait:1800']
    play = boot + ['key:G', 'wait:90', 'key:\r', 'wait:600']
    lesson = boot + ['key: ', 'wait:180']
    menu = ['key:\x1b', 'wait:180']
    back = ['key:\x1b', 'wait:180']

    with tempfile.TemporaryDirectory(prefix='micro-graphics-') as directory:
        tmp = Path(directory)

        def run(steps):
            result = subprocess.run([str(args.a2run), '--disk', str(args.disk), *steps],
                                    check=True, text=True, capture_output=True, timeout=60)
            return b''.join(bytes.fromhex(row) for row in re.findall(
                r'^[0-9A-F]{4}: (.+)$', result.stdout, re.M))

        def screen(steps):
            # Compare the actual hardware display with both forced pages. This
            # detects a soft-switch disagreement even if front_page looks right.
            actual, page1, page2 = (tmp / name for name in ('actual.png', 'page1.png', 'page2.png'))
            raw = run(steps + [peek('front_page'), peek('draw_page'), peek('hgr_hi', 192),
                              'peek:2000:16384', peek('STATE_GRID', 240),
                              'shot:' + str(actual), 'peek:C054:1', 'shot:' + str(page1),
                              'peek:C055:1', 'shot:' + str(page2)])
            front, draw = raw[:2]
            assert front in (0, 0x60) and draw == front, (front, draw)
            expected_hi = bytes(((0x2000 + (y & 7) * 0x400 +
                                 ((y >> 3) & 7) * 0x80 + (y >> 6) * 0x28) >> 8) ^ front
                                for y in range(192))
            assert raw[2:194] == expected_hi, 'HGR row addresses disagree with displayed page'
            assert actual.read_bytes() == (page2 if front else page1).read_bytes(), 'wrong hardware page'
            offset = 194 + (8192 if front else 0)
            # Only visible bytes: unused HGR holes may contain disk scratch.
            page = raw[offset:offset+8192]
            pixels = b''.join(page[(y & 7)*0x400 + ((y >> 3)&7)*0x80 + (y >> 6)*0x28:
                                  (y & 7)*0x400 + ((y >> 3)&7)*0x80 + (y >> 6)*0x28 + 40]
                              for y in range(192))
            return pixels, raw[194+16384:194+16384+240]

        # A mono display loses bit 7's palette selection. Every gameplay tile
        # must still have a different shape, especially BOX / BOX ON TARGET.
        tiles = run(boot + [peek('tile_bitmaps', 7 * 32)])
        silhouettes = {bytes(b & 0x7F for b in tiles[i:i+32])
                       for i in range(0, len(tiles), 32)}
        assert len(silhouettes) == 7, 'gameplay tiles differ only by colour'
        print('All seven tile silhouettes remain distinct without colour: ok')

        # Canceling a title grid must return to the title without a live game.
        for prefix in (boot, boot + menu):
            raw = run(prefix + ['key:G', 'wait:90'] + back +
                      [peek('game_active'), peek('title_phase')])
            assert raw[0] == 0 and raw[1] > 0, 'title grid cancel started gameplay'
        print('Canceling the level grid from title and title menu returns to the title: ok')

        baseline = screen(play)
        assert screen(boot + menu + ['key:G', 'wait:90', 'key:\r', 'wait:600']) == baseline
        for name, path in [('menu', menu + back), ('help', ['key:H', 'wait:180'] + back + back),
                           ('options', menu + ['key:O', 'wait:180'] + back + back),
                           ('ranking', menu + ['key:F', 'wait:180'] + back + back),
                           ('profiles', menu + ['key:V', 'wait:180'] + back + back),
                           ('grid cancel', ['key:G', 'wait:180'] + back),
                           ('repeated menus', (menu + back) * 3)]:
            assert screen(play + path) == baseline, name
        assert screen(lesson + ['key:G', 'wait:90'] + back) == screen(lesson), 'lesson lost on grid cancel'
        print('Displayed page, all 192 HGR row pointers and exact screen restoration through menus/grid: ok')

        # Stop before begin_screen and at show_screen, while the next page has
        # been drawn but not yet displayed. The front page must stay intact.
        def pending_capture():
            return [peek('front_page'), peek('draw_page'), 'peek:2000:16384']
        parities = set()
        for prefix in (play, play + ['key:H', 'wait:180'] + back + back):
            raw = run(prefix + ['press:\x1b', f'until:{labels["begin_screen"]:04X}:180',
                                *pending_capture(), f'until:{labels["show_screen"]:04X}:180',
                                *pending_capture()])
            size = 2 + 16384
            before, pending = raw[:size], raw[size:]
            parities.add(before[0])
            assert before[0] == pending[0] and pending[1] == (pending[0] ^ 0x60)
            offset = 2 + (8192 if before[0] else 0)
            assert before[offset:offset+8192] == pending[offset:offset+8192], 'drawing changed the front page'
        assert parities == {0, 0x60}
        print('Full-screen rendering preserves either displayed page until show_screen: ok')

        cheat = [f'poke:{labels["hof_buf"]+88:04X}:09']
        solution = menu + ['key:I', 'wait:40', 'key:\r', 'wait:200',
                           'key:\x1b', 'wait:600']  # interrupt playback
        assert screen(play + cheat + solution) == baseline, 'game display after solution'
        # Playback overlays the cached pack with executable code. Starting a
        # game from the title afterwards must reload the level data.
        title_solution = boot + cheat + solution + ['key:G', 'wait:90', 'key:\r', 'wait:600']
        assert screen(title_solution) == baseline, 'title solution corrupted the next level'
        # Repeat to exercise both cache and HGR page parities.
        assert screen(play + cheat + solution + solution) == baseline
        print('Solution interruption and repeated playback restore the board on either page: ok')

        # O also works while the cursor is on SOLUTION. Disabling cheat mode
        # must move that cursor onto a remaining, visible menu entry.
        options = ['key:O', 'wait:180']
        disable = ['key:K', 'wait:30'] * 4 + ['key:\r', 'wait:30']
        expected_menu = screen(play + menu + options + back)
        assert screen(play + cheat + menu + ['key:I', 'wait:40'] +
                      options + disable + back) == expected_menu, 'cursor on hidden SOLUTION'
        print('Disabling cheat mode from SOLUTION returns the cursor to visible OPTIONS: ok')


if __name__ == '__main__':
    main()
