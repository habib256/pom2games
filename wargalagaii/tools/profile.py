#!/usr/bin/env python3
"""Profile WARGALAGA II frames on a2shot: render and logic, by routine.

    tools/profile.py [--wait N] [--frames N] [--shots N]

Boots dist/WARGALAGAII.po on an enhanced //e, plays N refreshes (default
1200: formation seated, divers out), then measures --frames frames: cycles
from render to render_done (each one, worst and mean) and from logic_step
to logic_done, with the routines that spent them. --shots N raises the shot
limit to N and keeps firing (the bench scene of TODO.md lot 2: 40 aliens,
6 divers, 10 shots).
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2profile
import a2test

BUDGET = 28060


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wait', type=int, default=1200)
    ap.add_argument('--frames', type=int, default=30)
    ap.add_argument('--shots', type=int, default=0)
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/WARGALAGAII.po')
    ap.add_argument('--labels', type=Path, default=ROOT / 'wargalagaii/build/game.lbl')
    a = ap.parse_args()
    L = a2test.labels(a.labels, strip=True)
    steps = [L.until('game_tick', 3000)]
    if a.shots:
        steps.append(L.poke('shot_limit', a.shots))
    # Firing: poke fire_req at each logic step through the waiting time.
    fire = [L.until('logic_step', 10), L.poke('fire_req', 0x80), L.until('logic_done', 10)] if a.shots else []
    for _ in range(a.wait // 2):
        steps += fire or ['wait:2']
    steps += [L.peek('late_count', 2), L.peek('frame_count', 2)]
    for _ in range(a.frames):
        steps += fire + [L.until('render', 10), f'pcprof:{L["render_done"]:04X}:5',
                         L.until('logic_step', 10), f'pcprof:{L["logic_done"]:04X}:5']
    steps += [L.peek('late_count', 2), L.peek('frame_count', 2)]
    run = a2test.run(a.disk, steps, iie=True, timeout=900)
    out = run.out
    word = lambda name, k: int.from_bytes(run.mem(L[name], 2, k), 'little')
    late = word('late_count', 1) - word('late_count', 0)
    frames = word('frame_count', 1) - word('frame_count', 0)
    chunks = out.split('pcprof ')[1:]
    render = [c for k, c in enumerate(chunks) if k % 2 == 0]
    logic = [c for k, c in enumerate(chunks) if k % 2 == 1]
    for name, parts in (('render', render), ('logic', logic)):
        totals = [a2profile.total('pcprof ' + c) for c in parts]
        prof = {}
        for c in parts:
            for pc, cyc in a2profile.pcs(c).items():
                prof[pc] = prof.get(pc, 0) + cyc
        per = a2profile.by_label(prof, a.labels)
        print(f'{name}: mean {sum(totals) // len(totals)}, worst {max(totals)}, '
              f'best {min(totals)} cycles ({len(totals)} frames; budget {BUDGET} all included)')
        print('  sorted:', sorted(totals)[::-1][:8], '...')
        a2profile.report(per, sum(totals), unit=len(totals), top=14)
        print()
    print(f'{late} late frames out of {frames}')


if __name__ == '__main__':
    main()
