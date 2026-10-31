#!/usr/bin/env python3
"""WARGALAGA II sound: speaker and Mockingboard back-ends (a2shot).

Speaker: toggles are `STA $C030` (one toggle each, seen by storewatch). They
must come only from timing.s's wait loops (an effect never delays a frame),
none without an effect, none when muted (S).
Mockingboard (slot 4): AY register writes are decoded from the VIA stores
(ORA = value or register number, ORB 7 = latch, 6 = write): music on chip 1
(the PT3 song of tools/pt3.py: its first melody note, played from aux
memory), effects on chip 2, silence on S and on exit; the game keeps its
cadence with the card.
"""
import argparse
import collections
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'wargalagaii'
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(GAME / 'tools'))
import a2test
from boot import boot
import pt3
import sound

# The value written is the register the opcode stores (STA, STX or STY): an
# I/O address reads back as something else, so a2shot's old>new is no use.
STORE = re.compile(r'^store ([0-9A-F]{4}) ([0-9A-F]{4}) \S+ A=([0-9A-F]{2}) X=([0-9A-F]{2}) '
                   r'Y=([0-9A-F]{2}) .* op=([0-9A-F]{2})[0-9A-F]* cycles=(\d+)$', re.M)
REGISTER = {0x8E: 1, 0x96: 1, 0x86: 1, 0x8C: 2, 0x94: 2, 0x84: 2}   # STX, STY; else A


def stores(out):
    """[(pc, address, value, cycle)]"""
    out_ = []
    for pc, addr, a, x, y, op, c in STORE.findall(out):
        value = (int(a, 16), int(x, 16), int(y, 16))[REGISTER.get(int(op, 16), 0)]
        out_.append((int(pc, 16), int(addr, 16), value, int(c)))
    return out_


def ay_writes(out, slot=4):
    """[(cycle, chip, register, value)] from the VIA stores."""
    base = 0xC000 + slot * 0x100
    ora, reg, out_ = {}, {}, []
    for pc, a, v, c in stores(out):
        chip = (a - base) >> 7
        port = (a - base) & 0x7F
        if port == 1:
            ora[chip] = v
        elif port == 0 and v == 7:
            reg[chip] = ora.get(chip)
        elif port == 0 and v == 6:
            out_.append((c, chip, reg.get(chip), ora.get(chip)))
    return out_


def fire(L, n):
    return [L.until('logic_step', 10), L.poke('fire_req', 0x80), L.until('logic_done', 10)] * n


def speaker(disk, L):
    lo, hi = L['next_edge'], L['ne_edge']          # //e wait loop
    lo2, hi2 = L['wait_irq'], L['wi_count']        # //c wait loop
    r = a2test.run(disk, [*boot(L), 'storewatch:C030:C030', 'wait:200',
                          L.peek('step_count', 2)] + fire(L, 1) + ['wait:30', L.peek('step_count', 2),
                          'key:S', 'wait:4'] + fire(L, 1) + ['wait:30', L.peek('music_on')],
                   iie=True, timeout=300)
    toggles = [s for s in stores(r.out) if s[1] == 0xC030]
    assert r.mem(L['music_on'], 1)[0] == 0
    # before the first shot: nothing; then the shot effect; the music off
    # (S, 2026-10-30): the effects still play
    first_fire = int(re.search(r'until [0-9A-F]+ cycles=(\d+) PC=' + f'{L["logic_step"]:04X}', r.out)[1])
    mute = int(re.findall(r'until [0-9A-F]+ cycles=(\d+) PC=' + f'{L["logic_step"]:04X}', r.out)[1])
    before = [t for t in toggles if t[3] < first_fire]
    shot = [t for t in toggles if first_fire <= t[3] < mute]
    after = [t for t in toggles if t[3] >= mute]
    assert not before, f'{len(before)} toggles without an effect'
    assert len(shot) > 20, f'shot effect: {len(shot)} toggles'
    assert len(after) > 20, f'shot effect with the music off: {len(after)} toggles'
    assert all(lo <= pc < hi or lo2 <= pc < hi2 for pc, *_ in shot), \
        sorted({hex(pc) for pc, *_ in shot})
    # pitch: a half-period of n turns is n * SPK_TURN cycles (+ a constant)
    # (bug hunt 5: an atomic timing_scan made turns 72 cycles, 63 assumed:
    # every effect ~13 % flat, and //e and //c no longer alike; bug hunt 6
    # made the common scan cheap again: 63)
    gaps = collections.Counter(b[3] - a[3] for a, b in zip(shot, shot[1:]))
    common = sorted(d for d, n in gaps.items() if n >= 5)
    turns = sorted({sound.spk_turns(f) for f, _, _ in sound.SFX[-1][1]})
    steps = [b - a for a, b in zip(common, common[1:])]
    assert all(abs(s - sound.SPK_TURN * round(s / sound.SPK_TURN)) <= 2 for s in steps) and \
        abs(common[0] - turns[0] * sound.SPK_TURN) <= 12, (common, turns, sound.SPK_TURN)
    print(f'PASS speaker: no toggle without an effect, {len(shot)} for a shot, all in the '
          f'wait loops (never delaying a frame), still there with the music off (S); turns of {sound.SPK_TURN} cycles '
          f'(half-periods {common[:4]}...)')


def mockingboard(disk, L):
    a4 = pt3.note_table()[pt3.pt3_note(sound.MELODY[0][0])]
    shot = sound.ay_period(sound.SFX[-1][1][0][0])
    steps = [*boot(L), L.peek('audio_slot'), 'storewatch:C030:C4FF', 'wait:120']
    steps += fire(L, 1) + ['wait:20', 'key:S', 'wait:30'] + fire(L, 1) + ['wait:20', L.peek('music_on'),
                                                                     'key:\\e', 'wait:200']
    r = a2test.run(disk, steps, iie=True, mockingboard=True, timeout=300)
    assert r.mem(L['audio_slot'], 1)[0] == 4, 'Mockingboard found in slot 4'
    w = ay_writes(r.out)
    fire_at = int(re.search(r'until [0-9A-F]+ cycles=(\d+) PC=' + f'{L["logic_step"]:04X}', r.out)[1])
    mute_at = [c for c, *_ in w if c > fire_at]
    music = [(reg, v) for c, chip, reg, v in w if chip == 0 and c < fire_at]
    assert (0, a4 & 255) in music and (1, a4 >> 8) in music and (8, 15) in music, music[:12]
    notes = {v for reg, v in music if reg == 0}
    assert len(notes) >= 4, f'the melody moves: {sorted(notes)}'
    bass = pt3.note_table()[pt3.pt3_note(sound.BASS[0][0])]
    assert (2, bass & 255) in music and (3, bass >> 8) in music, 'the bass on voice B'
    effect = [(reg, v) for c, chip, reg, v in w if chip == 1 and c >= fire_at]
    assert (0, shot & 255) in effect and (8, 11) in effect, effect[:10]
    # S: the music's chip silent from then on, the next shot still heard on chip 2
    assert r.mem(L['music_on'], 1)[0] == 0
    fire2 = int(re.findall(r'until [0-9A-F]+ cycles=(\d+) PC=' + f'{L["logic_step"]:04X}', r.out)[1])
    late = [(chip, reg, v) for c, chip, reg, v in w if c >= fire2]
    assert all(v == 0 for chip, reg, v in late if chip == 0), [x for x in late if x[0] == 0][:10]
    assert (1, 0, shot & 255) in late and (1, 8, 11) in late, late[:10]
    # music off (S), then ESC: the last volume written is 0 (music's 3 voices, effects' voice A)
    last = {}
    for c, chip, reg, v in w:
        if reg in (8, 9, 10):
            last[chip, reg] = v
    assert all(v == 0 for v in last.values()) and {(0, 8), (0, 9), (0, 10), (1, 8)} <= set(last), last
    # with a card, the speaker stays quiet (effects played twice before)
    assert not [s for s in stores(r.out) if s[1] == 0xC030], 'speaker toggles with a Mockingboard'
    print(f'PASS Mockingboard slot 4: PT3 music on chip 1 (A4 period {a4}, bass, {len(notes)} notes in 2 s), '
          f'shot effect on chip 2 (period {shot}), S: the music silent, the effects still on')


def unmute(disk, L):
    """S twice with the card: the music comes back (its registers rewritten)."""
    r = a2test.run(disk, [*boot(L), 'wait:60', 'key:S', 'wait:30',
                          'storewatch:C400:C4FF', 'key:S', 'wait:60'], iie=True, mockingboard=True)
    vols = [v for c, chip, reg, v in ay_writes(r.out) if chip == 0 and reg in (8, 9)]
    assert vols and max(vols) > 0, vols
    print('PASS S, S: the music comes back')


def tempo(disk, L):
    """The music runs on timer 1 at MUS_HZ: that many PT3 ticks per CPU second
    whatever the frame rate (entry waves, seated) and the video standard.
    (Stepped once a frame, its rhythm wobbled with the frame rate: the user
    heard it, 2026-10-23.) A tick = one store into mus_ticks."""
    ml = L['mus_ticks']
    for name, pal, start in (('entry waves', False, 200), ('seated', False, 1300), ('PAL', True, 1100)):
        r = a2test.run(disk, [*boot(L), f'wait:{start}', f'storewatch:{ml:04X}:{ml:04X}',
                              'wait:600'], iie=True, mockingboard=True, pal=pal)
        stamps = [c for pc, a, v, c in stores(r.out)]
        seconds = (stamps[-1] - stamps[0]) / 1020484
        per_second = (len(stamps) - 1) / seconds
        assert abs(per_second - sound.MUS_HZ) <= 0.5, (name, per_second)
        print(f'PASS tempo, {name}: {per_second:.2f} PT3 ticks a second')


def joystick(disk, L):
    """The paddle is counted while the music interrupt can fire: a tick in
    the middle of the count stopped X but not the paddle timer, and the
    stick read low (bug hunt 5: a stick held right read as left about one
    frame in 15). Held right with the card: every reading the same."""
    jx = L['joy_x']
    for pos, name in ((1, 'right'), (0, 'centre')):
        r = a2test.run(disk, [*boot(L), 'key:\t', f'joy:{pos},0', 'wait:60',
                              f'storewatch:{jx:04X}:{jx:04X}', 'wait:1200'], iie=True, mockingboard=True)
        values = [v for pc, a, v, c in stores(r.out)]
        assert len(values) > 300 and max(values) - min(values) <= 2, (name, collections.Counter(values))
        print(f'PASS joystick {name} with the music: {len(values)} readings, {min(values)}..{max(values)}')


def cadence(disk, L):
    names = ('frame_count', 'step_count', 'late_count')
    peeks = [L.peek(n, 2) for n in names]
    r = a2test.run(disk, [*boot(L), L.poke('lives', 9), 'wait:1200', *peeks, 'wait:2000', *peeks],
                   iie=True, mockingboard=True)   # (9 lives: GAME OVER would go to the title)
    w = lambda n, k: int.from_bytes(r.mem(L[n], 2, k), 'little')
    frames, steps, late = (w(n, 1) - w(n, 0) for n in names)
    assert late == 0 and abs(frames - 1000) <= 1 and abs(steps - 1000) <= 1, (frames, steps, late)
    print(f'PASS cadence with the Mockingboard: {frames} frames, {steps} steps in 2000 refreshes, '
          'none late')


def steadiness(disk, L):
    """2026-10-30 (« vérifie la stabilité de la lecture de la musique »): in
    play every tick lands within 3 000 cycles of its period (a death, GAME
    OVER, the title, the demo on the way); at power on, the HIGHSCORES read
    masks interrupts ~0.8 s (ProDOS's Disk II driver): the music's chip is
    silent by then (mus_hush), no note held."""
    ml, period = L['mus_ticks'], 1020484 / sound.MUS_HZ
    r = a2test.run(disk, [*boot(L), f'storewatch:{ml:04X}:{ml:04X}', 'wait:4000'],
                   iie=True, mockingboard=True, timeout=600)
    st = [c for pc, a, v, c in stores(r.out)]
    worst = max(abs(b - a - period) for a, b in zip(st, st[1:]))
    assert len(st) > 1500 and worst < 3000, (len(st), worst)
    ack = L['irq_ack']                 # (one storewatch at a time: the ticks by their PC)
    r = a2test.run(disk, [f'watch:{ack:04X}', 'storewatch:C400:C4FF', L.until('fr_loop', 3000)],
                   iie=True, mockingboard=True, timeout=600)
    w = ay_writes(r.out)
    st = [int(c) for c in re.findall(rf'^watch {ack:04X} .*cycles=(\d+)', r.out, re.M)]
    gaps = [(a, b) for a, b in zip(st, st[1:]) if b - a > 4 * period]
    assert gaps, 'the HIGHSCORES read held the interrupts back'
    for a, b in gaps:
        vol = {}
        for c, chip, reg, v in w:
            if chip == 0 and reg in (8, 9, 10) and c < b:
                vol[reg] = v
        assert vol and all(v == 0 for v in vol.values()), (a, b, vol)
    print(f'PASS music steady: in play every tick within {worst:.0f} cycles of {period:.0f}; '
          f'{len(gaps)} disk pause(s) at the title, the music silent through them')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/WARGALAGAII.po')
    ap.add_argument('--labels', type=Path, default=GAME / 'build/game.lbl')
    a = ap.parse_args()
    if not a2test.have_a2shot('sound'):
        return
    L = a2test.labels(a.labels, strip=True)
    speaker(a.disk, L)
    mockingboard(a.disk, L)
    unmute(a.disk, L)
    steadiness(a.disk, L)
    tempo(a.disk, L)
    joystick(a.disk, L)
    cadence(a.disk, L)


if __name__ == '__main__':
    main()
