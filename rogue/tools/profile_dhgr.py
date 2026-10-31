#!/usr/bin/env python3
"""Where a ROGUE.DHGR turn goes: a2shot pcprof over test_dhgr.py's game.

    python3 tools/profile_dhgr.py [--bin BIN] [--seed N] [--top N] [--detail N]

Plays tests/test_dhgr.py's scripted //e game (same 100 moves, same
checkpoints and checks, the PRNG pinned after the briefing: every build plays
the same dungeons; --seed for others) but runs each turn (key read -> next
key wait) under a2shot's pcprof: prints the cycles per back-end stage / the
core / the sound, summed over every turn and per turn, the routines, then
the split of the slowest, median and 3/4 turns (--detail N: their N first
routines); vid_put's call count (its PHP: 3 cycles a call). --bin an older
build to compare (its labels file next to it).
"""
import argparse
import re
import sys
from pathlib import Path

GAME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GAME / 'tests'))
sys.path.insert(0, str(GAME.parent / 'dev/tools'))
import a2profile  # noqa: E402
import a2test  # noqa: E402
import test_dhgr  # noqa: E402

GROUPS = [                          # (this back-end and the ones before it)
    ('vid_put', ('vid_put', 'dg_cmp', 'dg_sta', 'dg_vp_')),
    ('x2 frame (camera, keys)', ('x2_frame',)),
    ('x2 page compare', ('x2_idle', 'x2_current', 'x2_draw_page')),
    ('x2 compose (sprites)', ('x2_zero', 'x2_sprite', 'x2_overlay')),
    ('x2 cell setup', ('x2_cell', 'x2_lines')),
    ('x2 write', ('x2_w',)),
    ('flip (VBL wait)', ('x2_flip',)),
    ('page switch', ('dg_use_page',)),
    ('vid_addr', ('vid_addr',)),
    ('name diff', ('dg_name_diff',)),
    ('sprite diff + boxes', ('dg_sat_diff', 'dg_mark_')),
    ('dirty scan', ('dg_flush', 'dg_bit', 'dg_dirty_row', 'dg_do_row')),
    ('sprites', ('dg_strip_sprites', 'dg_spr', 'dg_line_sprites')),
    ('run setup', ('dg_strip', 'dg_row_sprites')),
    ('characters', ('dg_ph', 'dg_bl', 'dg_nx', 'dg_line_chars', 'dg_lc', 'dg_k')),
    ('pack', ('dg_line_pack',)),
    ('write', ('dg_write', 'dg_wc', 'dg_w', 'dg_v', 'dg_line_write')),
    ('back-end other', ('dg_', 'vid_')),
    ('sound', ('tone', 'sfx', 'snd', 'tune', 'play_')),
    ('throw delay', ('delay_throw_frame',)),
]


def pct(ts):
    """'median M, p90 P, mean A, max X' of a list of cycle counts."""
    ts = sorted(ts)
    n = len(ts)
    return f'median {ts[n // 2]}, p90 {ts[n * 9 // 10]}, mean {sum(ts) // n}, max {ts[-1]}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bin', type=Path, default=GAME / 'build/rogue_dhgr.bin')
    ap.add_argument('--top', type=int, default=30)
    ap.add_argument('--seed', type=lambda v: int(v, 0), default=test_dhgr.SEED,
                    help='PRNG state after the briefing (test_dhgr.SEED)')
    ap.add_argument('--detail', type=int, default=0, help='labels shown for each listed turn')
    ap.add_argument('--list', action='store_true', help='every turn: cycles, sound, throw delay, core')
    args = ap.parse_args()
    test_dhgr.BIN = args.bin
    test_dhgr.SEED = args.seed
    test_dhgr.LBL = args.bin.with_suffix('.lbl')
    L = a2test.labels(test_dhgr.LBL)
    labels = {n: int(a, 16) for a, n in
              re.findall(r'^al ([0-9A-F]+) \.(\S+)$', test_dhgr.LBL.read_text(), re.M)
              if 'MACRO' not in n}
    wk = L['wait_key'] + 3
    turns = []                       # (cycles, {pc: cycles})
    orig = a2test.Session.step

    def step(self, st):
        if st == f'until:{wk:04X}:900' and getattr(self, 'armed', False):
            self.armed = False
            r = orig(self, f'pcprof:{wk:04X}:900')
            turns.append((a2profile.total(r.out), a2profile.pcs(r.out)))
            return a2test.Result(r.out + orig(self, f'until:{wk:04X}:1').out)
        r = orig(self, st)
        if st == f'until:{wk + 5:04X}:300':
            self.armed = True        # play(): the key was read, the turn runs next
        return r
    a2test.Session.step = step
    test_dhgr.MEASURE = False        # one until per turn: the profiled one
    stats = test_dhgr.test_iie(None)
    total = sum(t for t, _ in turns)
    prof = {}
    for _, p in turns:
        for pc, c in p.items():
            prof[pc] = prof.get(pc, 0) + c
    per = a2profile.by_label(prof, labels, rom=0xF800)
    n = len(turns)
    vp = prof.get(labels['vid_put'], 0) // 3
    ts = sorted(t for t, _ in turns)
    print(f'{n} turns, {total} cycles, mean {total // n}, median {ts[n // 2]}, '
          f'p90 {ts[n * 9 // 10]}, max {ts[-1]}; vid_put {vp} calls ({vp // n} a turn); '
          f'full redraw {stats["full"]}, flash {stats["flash"]}; failures {test_dhgr.FAIL}')
    quiet = []                       # each turn without its sound / its throw delays
    for t, p in turns:
        g = a2profile.grouped(a2profile.by_label(p, labels, rom=0xF800), GROUPS + [('core', ('',))])
        quiet.append((t - g.get('sound', 0), t - g.get('sound', 0) - g.get('throw delay', 0)))
        if args.list:
            print(f'turn {len(quiet) - 1:3d}: {t:7d} cycles, sound {g.get("sound", 0):6d}, '
                  f'throw delay {g.get("throw delay", 0):6d}, core {g.get("core", 0):6d}')
    print('without the sound (the picture comes first): ' + pct([q for q, _ in quiet]))
    print('without the sound and the throw delays:      ' + pct([q for _, q in quiet]))
    calls = {name: prof.get(labels[name], 0) // c for name, c in
             (('dg_do_row', 4), ('dg_strip', 3)) if name in labels}
    if calls:
        print('per turn: ' + ', '.join(f'{k} {v / n:.1f}' for k, v in calls.items())
              + ' (a run = groups of a text row, 8 lines)')
    a2profile.report(a2profile.grouped(per, GROUPS + [('core', ('',))]), total, n,
                     brackets=True)
    print()
    a2profile.report(per, total, n, top=args.top)
    order = sorted(turns, key=lambda tp: -tp[0])
    for t, p in order[:3] + [order[n // 2], order[n * 3 // 4]]:
        print(f'\nturn of {t} cycles:')
        a2profile.report(a2profile.grouped(a2profile.by_label(p, labels, rom=0xF800),
                                           GROUPS + [('core', ('',))]), t, brackets=True)
        if args.detail:
            a2profile.report(a2profile.by_label(p, labels, rom=0xF800), t, top=args.detail)


if __name__ == '__main__':
    main()
