#!/usr/bin/env python3
"""ROGUE.TMS with a Mockingboard (a2shot: POM2's card in slot 4, its VIA
timer interrupts emulated; the E-Z Color card in slot 5).

Checked: the card is found (snd_mb = 4) and mb_irq.asm's service runs on the
ROM's $03FE vector at 50 Hz of emulated time; the title tune is the AYS
song ays_title (the AY's channel A plays one of its periods, heard); a
sound of the game (the demon's room, B at the title) is its AYS song and
the speaker stays silent; S mutes the three voices and S again lets them
play; 200 keys of play with the interrupts keep every VDP access inside the
card's window (vdp_dropped == 0); ESC then Y, and Ctrl-RESET, leave to DOS
with the service off (no more ticks, the old $03FE vector back, the AY's
volumes 0). Without a Mockingboard: snd_mb = 0 and the speaker sounds.

ROGUE.DHGR (a2shot --iie and --iic with --mockingboard, the //c's being its
4c in slot 4): found, $03FE, 50 Hz at the title and over nine moves of play,
and test_dhgr's oracle: both DHGR pages, main and auxiliary banks, equal to
the model of the virtual screen (the interrupt never lands in a wrong bank);
without the card snd_mb = 0.
"""
import random
import subprocess
import sys
import tempfile
from pathlib import Path

GAME = Path(__file__).resolve().parents[1]
ROOT = GAME.parent
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(ROOT / 'dev/tools/audio'))
import a2test  # noqa: E402
import aysong  # noqa: E402
sys.path.insert(0, str(GAME / 'tests'))
import test_dhgr as TD  # noqa: E402

DISK = ROOT / 'dist/ROGUE.dsk'
L = a2test.labels(GAME / 'build/rogue_tms.lbl')
BOOT = [L.until('music_title', 3000), 'wait:30']    # the title, its tune on
START = BOOT + ['key:X', 'wait:30', 'key:X', 'wait:60']
MB_SLOT, EZ_SLOT = 4, 5
fails = 0


def check(cond, what):
    global fails
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        fails += 1
    return cond


def run(steps, mockingboard=True, check=True):
    return a2test.run(DISK, steps, emulator=a2test.A2SHOT, ezcolor=EZ_SLOT, mockingboard=mockingboard,
                      check=check)


def speaker(steps, frames, mockingboard=True):
    """True if sound.asm's tone (the speaker) runs within `frames` after steps
    (a2shot has no speaker count: its until: on tone, which fails if never)."""
    r = run(steps + [L.until('tone', frames)], mockingboard=mockingboard, check=False)
    return f'PC={L["tone"]:04X}' in r.out     # (until prints its line on a miss too)


def word(b):
    return b[0] | b[1] << 8


def song_bytes(label, end_label):
    """The song's bytes, read back from the running program."""
    r = run(BOOT + [L.peek(label, L[end_label] - L[label])])
    return r.dumps[-1]


def periods(data, ticks=400):
    """Channel A periods the model plays while its volume is up."""
    p, out = aysong.Player(data), set()
    for _ in range(ticks):
        f = p.tick()
        if f[8] & 0x0F:
            out.add(f[0] | f[1] << 8)
    return out


def shadow(r, i=-1):
    return r.dumps[i]


def main():
    # --- found, the service on $03FE at 50 Hz --------------------------------
    r = run(BOOT + [L.peek('snd_mb'), L.peek('mb_irq_n'), 'peek:03FE:2', L.peek('mb_irq_ticks'),
                    'wait:120', L.peek('mb_irq_ticks')])
    d = r.dumps[-5:]
    check(d[0][0] == MB_SLOT, f'Mockingboard found in slot {d[0][0]} (E-Z Color in {EZ_SLOT})')
    check(d[1][0] != 0 and word(d[2]) == L['mb_irq_handler'],
          f'service installed, $03FE = mb_irq_handler (${word(d[2]):04X})')
    ticks = (d[4][0] - d[3][0]) & 0xFF
    want = 120 * 17030 / (1020484 / 50)            # 120 NTSC frames of ticks
    check(abs(ticks - want) <= 2, f'50 Hz: {ticks} ticks in 120 frames (model {want:.1f})')

    # --- the title tune: ays_title on channel A, heard, speaker silent --------
    title = periods(song_bytes('ays_title', 'ays_death'))
    r = run(BOOT + [L.peek('ays_base', 2), L.peek('mb_shadow', 16)])
    base, sh = word(r.dumps[-2]), r.dumps[-1]
    check(base == L['ays_title'], 'title: the AYS title song plays')
    check((sh[0] | sh[1] << 8) in title and sh[8] & 0x0F,
          f'title: channel A on a period of the tune (${sh[0] | sh[1] << 8:03X}), volume {sh[8]}')
    check(not speaker([L.until('music_title', 3000)], 200), 'title: speaker silent')

    # --- the demon's room (B at the title): its sound, then S mutes -----------
    boss = BOOT + ['key:B', 'wait:30', 'key:X', 'wait:20', L.peek('ays_base', 2)]
    r = run(boss + ['wait:40', 'key:S', 'wait:10', L.peek('ays_mutem'), L.peek('mb_shadow', 16),
                    'key:S', 'wait:10', L.peek('ays_mutem')] + a2test.VDP_SHOT_STEPS)
    check(b'DEPTH 013' in r.vram[0x1A80:0x1AA0], 'B at the title: depth 13')
    check(word(r.dumps[-4]) == L['ays_sfx_boss'], "the demon's room: its AYS sound plays")
    check(not speaker(BOOT + ['key:B', 'wait:30', 'key:X'], 120), "the demon's room: speaker silent")
    sh = r.dumps[-2]
    check(r.dumps[-3][0] == 7 and not any(sh[8 + v] & 0x0F for v in range(3)),
          f'S: voices muted (mask {r.dumps[-3][0]}, volumes {list(sh[8:11])})')
    check(r.dumps[-1][0] == 0, 'S again: voices heard')

    # --- 200 keys of play with the interrupts: the VDP window holds -----------
    rnd = random.Random(1982)
    keys = []
    while len(keys) < 200:
        x = rnd.random()
        keys += ([rnd.choice('IJKL')] if x < 0.8 else ['.'] if x < 0.88 else
                 ['T', rnd.choice('IJKL')] if x < 0.95 else ['S', 'S'])
    r = run(START + [s for k in keys for s in (f'key:{k}', 'wait:2')]
            + [L.peek('mb_irq_ticks'), 'wait:10', L.peek('mb_irq_ticks'), 'vregs'])
    check(r.vdp_dropped == 0, f'200 keys of play: vdp_dropped == {r.vdp_dropped}')
    check(r.dumps[-1][0] != r.dumps[-2][0], '200 keys of play: the service still ticks')

    # --- leaving: ESC then Y, and Ctrl-RESET -----------------------------------
    for name, out in (('ESC then Y', ['key:\x1b', 'key:Y', 'wait:60']), ('Ctrl-RESET', ['reset', 'wait:60'])):
        r = run(START + ['wait:20', L.peek('mb_irq_old', 2)] + out
                + ['text', L.peek('mb_irq_ticks'), 'wait:30', L.peek('mb_irq_ticks'), 'peek:03FE:2',
                   L.peek('mb_shadow', 16)])
        old, t0, t1, vec, sh = word(r.dumps[-5]), r.dumps[-4][0], r.dumps[-3][0], word(r.dumps[-2]), r.dumps[-1]
        prompt = any(row.startswith('|]') for row in r.text_screens()[-1].split('\n'))
        check(prompt and t0 == t1 and vec == old and not any(sh[8 + v] & 0x0F for v in range(3)),
              f'{name}: DOS prompt, no more ticks, $03FE = ${vec:04X} (was ${old:04X}), volumes {list(sh[8:11])}')

    # --- no Mockingboard: the speaker ---------------------------------------------
    r = run(BOOT + [L.peek('snd_mb')], mockingboard=False)
    check(r.dumps[-1][0] == 0 and speaker(BOOT + ['key:B', 'wait:30', 'key:X'], 120, mockingboard=False),
          "no Mockingboard: snd_mb = 0, the demon's room on the speaker")

    # --- ROGUE.DHGR on the //e and the //c --------------------------------------
    D = a2test.labels(GAME / 'build/rogue_dhgr.lbl')
    wk = D['wait_key'] + 3
    for machine in ('iie', 'iic'):
        steps = [D.until('music_title', 3000), 'wait:30', D.peek('snd_mb'), 'peek:03FE:2',
                 D.peek('mb_irq_ticks'), 'wait:120', D.peek('mb_irq_ticks'),
                 'key: ', 'wait:200', 'key: ', f'until:{wk:04X}:900', D.peek('mb_irq_ticks')]
        for k in 'LLKKJJII.':
            steps += [f'press:{k}', 'wait:2', f'until:{wk:04X}:900']
        steps += [D.peek('mb_irq_ticks')] + TD.screen_steps(D)
        with tempfile.TemporaryDirectory(prefix='rogue-mb-') as work:
            disk = a2test.build_disk(work, 'ROGUE.DHGR', TD.BIN, load=D['entry'])
            p = subprocess.run([str(a2test.A2SHOT), f'--{machine}', '--mockingboard', '--disk', str(disk)]
                               + steps, capture_output=True, text=True, timeout=300)
            nomb = subprocess.run([str(a2test.A2SHOT), f'--{machine}', '--disk', str(disk),
                                   D.until('music_title', 3000), D.peek('snd_mb')],
                                  capture_output=True, text=True, timeout=300)
        tag = '//e' if machine == 'iie' else '//c'
        if not check(p.returncode == 0, f'DHGR {tag}: runs' + ('' if p.returncode == 0 else f' (exit {p.returncode}: {p.stderr[-200:]})')):
            continue
        r = a2test.Result(p.stdout)
        d = [r.mem(D['snd_mb'], 1)[0], word(r.mem(0x03FE, 2))] + \
            [r.mem(D['mb_irq_ticks'], 1, i)[0] for i in range(4)]
        check(d[0] == MB_SLOT and d[1] == D['mb_irq_handler'],
              f'DHGR {tag}: Mockingboard in slot {d[0]}, $03FE = ${d[1]:04X}')
        title = (d[3] - d[2]) & 0xFF
        play = (d[5] - d[4]) & 0xFF
        check(abs(title - want) <= 2, f'DHGR {tag}: {title} ticks in 120 frames at the title (model {want:.1f})')
        check(play > 0 and p.stdout.count(f'PC={wk:04X}') == 10,
              f'DHGR {tag}: nine moves played, the service ticking ({play} ticks)')
        before = len(TD.FAIL)
        TD.oracle(p.stdout, D, f'mb_{machine}', record=False)
        check(len(TD.FAIL) == before, f'DHGR {tag}: both pages, main and aux, = the model under the interrupts')
        rn = a2test.Result(nomb.stdout)
        check(nomb.returncode == 0 and rn.mem(D['snd_mb'], 1)[0] == 0, f'DHGR {tag} without the card: snd_mb = 0')

    print('rogue (Mockingboard): ' + ('PASS' if not fails else f'{fails} FAILED'))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
