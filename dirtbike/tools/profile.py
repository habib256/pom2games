#!/usr/bin/env python3
"""Where the frame goes: a2shot pcprof attributed to the nearest label.

    python3 tools/profile.py [frames] [keys] [skip] [track]
Boots dist/DIRTBIKE.dsk, types keys (default: full throttle), then profiles
`frames` video frames and prints cycles per routine and per game frame.
"""
from pathlib import Path
import re
import subprocess
import sys

GAME = Path(__file__).resolve().parents[1]
A2SHOT = GAME.parent / 'dev/tools/a2shot/a2shot'
sys.path.insert(0, str(GAME.parent / 'dev/tools'))
import a2profile  # noqa: E402


GROUPS = [
    ('physics', ('vl_', 'mul', 'constrain', 'ground_contact', 'quarter_abs', 'integrate', 'add_', 'sub_',
                 'delta_ab', 'clamp_v', 'phys_', 'do_lean', 'neg_prod', 'tptr', 'spin_damp', 'sd_shift',
                 'heavy', 'con_pass', 'vt_less')),
    ('ground', ('rg_', 'render_ground', 'write_rows', 'wr_', 'fill', 'hgr_hi_site0', 'hgr_hi_site1', 'hgr_hi_site2',
                'part_lda', 'sky_rows', 'compute_col', 'camera', 'pa_lda', 'pb_lda', 'rs_lda',
                'ls_lda', 'sa_sta', 'sb_')),
    ('bike', ('line', 'hgr_line8', 'hl_', 'hgr_hi_site', 'draw_bike', 'draw_wheel', 'draw_sprite', 'ds_',
              'mark', 'asr3')),
    ('hud', ('hgr_putc8', 'hgr_puts8', 'draw_hud', 'hud_')),
    ('input', ('read_', 'lean_level', 'kbd')),
]


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    keys = sys.argv[2] if len(sys.argv) > 2 else 'A' * 8
    skip = int(sys.argv[3]) if len(sys.argv) > 3 else 0   # frames before profiling
    trk = int(sys.argv[4]) if len(sys.argv) > 4 else 1     # track from the menu
    menu = ([] if trk <= 15 else ['L']) + ['K'] * ((trk - 1) % 15)
    labels = {n: int(a, 16) for a, n in re.findall(r'^al ([0-9A-F]+) \.(\w+)$', (GAME / 'build/dirtbike.lbl').read_text(), re.M)}
    exit_addr = labels['reset']                     # never reached: profile the whole window
    fr = labels['frames']
    steps = ['wait:1300', 'key: ', 'wait:60'] + [s for k in menu for s in (f'key:{k}', 'wait:3')] + ['key:\r', 'wait:150'] + [s for k in keys for s in (f'key:{k}', 'wait:4')] + ([f'wait:{skip}'] if skip else []) + [f'peek:{fr:04X}:2', f'pcprof:{exit_addr:04X}:{frames}', f'peek:{fr:04X}:2']
    out = subprocess.run([str(A2SHOT), '--disk', str(GAME.parent / 'dist/DIRTBIKE.dsk')] + steps,
                         capture_output=True, text=True, check=True).stdout
    total = a2profile.total(out)
    f0, f1 = [int(b, 16) + 256 * int(c, 16) for b, c in re.findall(r'^[0-9A-F]{4}: ([0-9A-F]{2}) ([0-9A-F]{2})', out, re.M)]
    games = (f1 - f0) & 0xFFFF
    per = a2profile.by_label(a2profile.pcs(out), labels)
    print(f'{total} cycles over {frames} video frames: {games} game frames, '
          f'{total // max(games, 1)} cycles each, {games * 60 / frames:.1f} fps')
    a2profile.report(a2profile.grouped(per, GROUPS), total, games, brackets=True)
    print()
    a2profile.report(per, total, games)

if __name__ == '__main__':
    main()
