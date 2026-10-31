#!/usr/bin/env python3
"""dev/tools/audio/pt3import.py (Vortex Tracker II .pt3 -> AYS v1) and its
reference PT3 player dev/tools/audio/pt3play.py.

1. pt3play's note and volume tables = the tables pt3_lib_init.s quotes in
   its comments (ST, ASM; the 3.3/3.4 and 3.5 volume tables).
2. pt3play against dev/lib/apple2/pt3 (pt3_lib) in a2run, register for
   register on every tick: the WARGALAGA II song, the synthetic songs and
   random modules (every command and effect, odd lengths, loops), also the
   zero-page build (PT3_USE_ZERO_PAGE) and PT3_FREQ_CONVERSION = 1.
   Skipped without ca65 / ld65 / a2run.
3. A synthetic song made of the features that map (looped samples,
   amplitude slides, noise offsets, an envelope, arpeggio and transposing
   ornaments, sample offset, a speed effect, two pattern lengths, a loop
   position whose state differs on the second pass): converted, AYS round
   trip, both players agree on 100 % of the heard volumes, mixer bits,
   noise and envelope registers, periods within the note mapping's error.
   A second one made of what does not map: the report lists each feature.
4. Random modules of mappable features: those whose report lists nothing
   approximated or lost agree 100 %.
5. The WARGALAGA II song (wargalagaii/tools/pt3.py into a temp dir):
   converted and compared; the CLI and aysong.py --import-pt3 agree."""
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(ROOT / 'dev/tools/audio'))
import a2test  # noqa: E402
import aysong  # noqa: E402
import pt3import  # noqa: E402
import pt3play  # noqa: E402

GROUPS = ('volume', 'mixer', 'noise', 'env_shape', 'env_period', 'period')
N = lambda n: 0x50 + n          # noqa: E731  (a PT3 note command)


# ---------------------------------------------------------------- modules
def stream(entries):
    """A channel stream: (lines, bytes of the line) entries, B1 lengths
    added when they change, the $00 end."""
    out, cur = [], None
    for n, b in entries:
        if n != cur:
            out += [0xB1, n]
            cur = n
        out += b
    return out + [0]


SAMPLES = {
    1: (2, [(0x01, 0x0F, 0), (0x01, 0x0D, 0), (0x01, 0x0C, 0), (0x01, 0x0A, 0)]),   # decay, loops 12, 10
    2: (1, [(0x05, 0x1F, 0), (0x03, 0x1C, 0), (0x01, 0x3A, 0), (0x01, 0x18, 0)]),   # drum: tone off, noise offsets + slide
    3: (0, [(0x00, 0x8F, 0)]),                                                       # the envelope
    4: (1, [(0x01, 0x8A, 0), (0xC1, 0x88, 0), (0xC1, 0x88, 0), (0x81, 0x8C, 0)]),    # amplitude slides up and down
}
ORNAMENTS = {1: (0, [0, 4, 7]), 3: (0, [5]), 4: (0, [-12, -8, -5])}


def song_mapped():
    p0 = (stream([(2, [0xD1, 0x41, N(48)]), (2, [N(50)]), (2, [0x40, N(52)]), (2, [0xC0]),
                  (4, [0xCA, 0x43, N(40)]), (2, [0xCF, 0x40, 0x03, N(45), 2]), (2, [0xD0])]),
          stream([(4, [0x1E, 0x02, 0x00, 2 * 3, N(36)]), (4, [N(38)]), (4, [0x10, 2 * 4, N(40)]),
                  (4, [0x09, N(43), 6])]),
          stream([(4, [0x2A, 0xD2, N(60)]), (4, [N(62)]), (8, [0xC0])]))
    p1 = (stream([(3, [0xD1, 0x41, N(55)]), (3, [0x44, N(57)]), (6, [0x40, N(59)]), (6, [0xC0]),
                  (6, [0xC8, N(60)])]),
          stream([(6, [0x09, 0xBE, 0x01, 0x00, 0xD3, N(30), 3]), (6, [0xD4, 0xB0, N(31)]), (12, [0xC0])]),
          stream([(2, [0x25, 0xD2, N(70)]), (2, [N(70)]), (4, [0xC0]), (8, [0x2C, N(72)]), (8, [0xC0])]))
    return pt3play.build(SAMPLES, ORNAMENTS, [p0, p1], [0, 1, 1], loop=1, speed=3, table=2, version=7,
                         title='synthetic A', author='test')


def song_unmapped():
    s = dict(SAMPLES)
    s[5] = (0, [(0x01, 0x0E, 3), (0x01, 0x0E, -3)])          # tone offsets
    o = dict(ORNAMENTS)
    o[2] = (0, [0, 12])                                        # an octave trill
    p0 = (stream([(2, [0xD1, 0x01, N(48), 1, 4, 0]), (2, [0xC9, 0xD0]), (2, [0x42, N(50)]),
                  (2, [0x02, N(55), 1, 0, 0, 0x20, 0]), (4, [0x40, 0xD5, N(52)]), (4, [0x05, N(53), 2, 2])]),
          stream([(4, [0x1E, 0x00, 0x13, 2 * 3, N(36)]), (4, [0x08, N(38), 2, 1, 0]), (8, [0xBC, 0x01, 0x00, 0xD0])]),
          stream([(4, [0x2A, 0xD2, N(60)]), (4, [0x23, 0xD0]), (8, [0xC0])]))
    return pt3play.build(s, o, [p0], [0], loop=0, speed=4, table=0, version=5, title='synthetic B')


def random_module(rng):
    """Anything pt3_lib decodes: every command and effect, random samples
    and ornaments, 1- to 4-line notes, patterns of 4..64 lines."""
    nsam = rng.randint(1, 6)
    samples = {}
    for s in range(1, nsam + 1):
        n = rng.randint(1, 8)
        samples[s] = (rng.randrange(n), [(rng.randrange(256), rng.randrange(256),
                                          rng.randint(-40, 40) if rng.random() < .3 else 0) for _ in range(n)])
    orns = {0: (0, [0])}
    for o in rng.sample(range(1, 16), rng.randint(0, 4)):
        n = rng.randint(1, 6)
        orns[o] = (rng.randrange(n), [rng.randint(-12, 12) for _ in range(n)])
    pats = []
    for _ in range(rng.randint(1, 4)):
        lines = rng.choice([4, 8, 13, 16, 32, 64])
        chans = []
        for _k in range(3):
            out, i, cur = [], 0, None
            while i < lines:
                k = min(rng.choice([1, 1, 1, 2, 3, 4]), lines - i)
                if cur is None or rng.random() < .3:
                    out += [0xB1, k]
                    cur = k
                else:
                    k = min(cur, lines - i)
                    if k != cur:
                        out += [0xB1, k]
                        cur = k
                for _ in range(rng.choice([0, 0, 1, 1, 2, 3])):
                    x = rng.randrange(10)
                    if x == 0:
                        out.append(0xC0 + rng.randint(1, 15))
                    elif x == 1:
                        out.append(0xD0 + rng.randint(1, nsam))
                    elif x == 2:
                        out.append(0x40 + rng.choice(list(orns)))
                    elif x == 3:
                        out.append(0x20 + rng.randint(0, 31))
                    elif x == 4:
                        out += [0x10 + rng.randint(1, 15), rng.randint(0, 2), rng.randint(0, 255), 2 * rng.randint(1, nsam)]
                    elif x == 5:
                        out += [0x10, 2 * rng.randint(1, nsam)]
                    elif x == 6:
                        out += [0xB0 + rng.randint(2, 15), rng.randint(0, 2), rng.randint(0, 255)]
                    elif x == 7:
                        out.append(0xB0)
                    elif x == 8:
                        out += [0xF0 + rng.choice(list(orns)), 2 * rng.randint(1, nsam)]
                spec = rng.choice([0] * 6 + [1, 2, 3, 4, 5, 8, 9])
                if spec:
                    out.append(spec)
                t = rng.random()
                out.append(N(rng.randint(0, 95)) if t < .55 else (0xC0 if t < .65 else 0xD0))
                w = lambda v: list((v & 0xFFFF).to_bytes(2, 'little'))  # noqa: E731
                out += {1: lambda: [rng.randint(0, 3)] + w(rng.randint(-200, 200)),
                        2: lambda: [rng.randint(1, 3), 0, 0] + w(rng.randint(-300, 300)),
                        3: lambda: [rng.randint(0, 1)], 4: lambda: [0],
                        5: lambda: [rng.randint(0, 3), rng.randint(0, 3)],
                        8: lambda: [rng.randint(1, 3)] + w(rng.randint(-50, 50)),
                        9: lambda: [rng.randint(1, 5)]}.get(spec, lambda: [])()
                i += k
            chans.append(out + [0])
        pats.append(tuple(chans))
    pos = [rng.randrange(len(pats)) for _ in range(rng.randint(1, 5))]
    return pt3play.build(samples, orns, pats, pos, rng.randrange(len(pos)), rng.randint(1, 6),
                         rng.randint(0, 3), rng.choice([4, 5, 6, 7]))


def mappable_module(rng):
    """Random modules of the features pt3import maps exactly (notes on
    every channel at each pattern start, noise base there only, envelope
    sets on note lines, arpeggio / transposing ornaments, effects 3 and 9)."""
    samples = {}
    for s in (1, 2, 3):
        n = rng.randint(1, 6)
        ticks = []
        for _ in range(n):
            noise = rng.random() < (.6 if s == 3 else .1)
            b1 = rng.randrange(16) | (0x10 if rng.random() < .15 else 0) | (0 if noise else 0x80)
            b0 = rng.randrange(2) | (rng.choice([0, 0x80, 0xC0]) if rng.random() < .3 else 0)
            if noise:
                b0 |= rng.randrange(32) << 1 & 0x3E
                b1 |= 0x20 if rng.random() < .2 else 0
            ticks.append((b0, b1, 0))
        samples[s] = (rng.randrange(n), ticks)
    orns = {0: (0, [0]), 1: (0, [0, rng.randint(0, 7), rng.randint(0, 12)]), 2: (0, [rng.randint(-5, 5)])}
    pats = []
    for _ in range(rng.randint(1, 3)):
        lines = rng.choice([8, 12, 16, 24])
        chans = []
        for k in range(3):
            out, i, cur = [], 0, None
            while i < lines:
                n = min(rng.choice([1, 2, 2, 4]), lines - i)
                if n != cur:
                    out += [0xB1, n]
                    cur = n
                if i == 0 or rng.random() < .6:
                    if i == 0 and k == 2 and rng.random() < .5:
                        out.append(0x20 + rng.randrange(32))
                    if rng.random() < .3:
                        out.append(rng.choice([0xCF, 0xC9]))
                    if rng.random() < .4:
                        out.append(0xD0 + rng.randint(1, 3))
                    if rng.random() < .3:
                        out.append(0x40 + rng.randrange(3))
                    if rng.random() < .15:
                        out += [0x1E, rng.randint(0, 3), 0x00, 2 * rng.randint(1, 3)]
                    elif rng.random() < .1:
                        out.append(0xB0)
                    spec = rng.choice([0] * 8 + [3, 9])
                    if spec:
                        out.append(spec)
                    out.append(N(rng.randint(12, 80)) if rng.random() < .9 else 0xC0)
                    if spec:
                        out.append(0 if spec == 3 else rng.choice([2, 4]))
                else:
                    out.append(0xD0)
                i += n
            chans.append(out + [0])
        pats.append(tuple(chans))
    pos = [rng.randrange(len(pats)) for _ in range(rng.randint(1, 4))]
    return pt3play.build(samples, orns, pats, pos, rng.randrange(len(pos)), rng.choice([2, 4]),
                         rng.randint(0, 3), rng.choice([4, 6, 7]))


def wg_song(work):
    out = work / 'song.pt3'
    subprocess.run([sys.executable, 'pt3.py', str(out)], cwd=ROOT / 'wargalagaii/tools', check=True)
    return out.read_bytes()


# ---------------------------------------------------------------- 1. tables
def comment_table(name, rows):
    text = (ROOT / 'dev/lib/apple2/pt3/pt3_lib_init.s').read_text()
    at = text.index(';' + name + ':')
    vals = []
    for line in text[at:].splitlines()[1:rows + 1]:
        vals += [int(v, 16) for v in re.findall(r'\$([0-9A-Fa-f]+)', line)]
    return vals


def check_tables():
    for n, name in ((1, 'PT3NoteTable_ST'), (2, 'PT3NoteTable_ASM_34_35')):
        hi, lo = comment_table(name + '_high', 12), comment_table(name + '_low', 12)
        assert pt3play.note_table(n) == [h << 8 | v for h, v in zip(hi, lo)], name
    assert pt3play.volume_table(False) == comment_table('PT3VolumeTable_33_34', 16)
    assert pt3play.volume_table(True) == comment_table('PT3VolumeTable_35', 16)
    print('PASS pt3play tables = pt3_lib_init.s: note tables 1 (ST) and 2 (ASM), volume tables 3.3/3.4 and 3.5')


# ---------------------------------------------------------------- 2. the asm
ASM = '''PT3_ZP = {zp}
{options}
NTICKS = {n}
.zeropage
lp:     .res 2
cnt:    .res 2
.code
start:  jsr pt3_init_song
        lda #<$2000
        sta lp
        lda #>$2000
        sta lp+1
        lda #<NTICKS
        sta cnt
        lda #>NTICKS
        sta cnt+1
loop:   jsr pt3_tick
        ldy #13
:       lda AY_REGISTERS,y
        sta (lp),y
        dey
        bpl :-
        lda lp
        clc
        adc #14
        sta lp
        bcc :+
        inc lp+1
:       lda cnt
        bne :+
        dec cnt+1
:       dec cnt
        lda cnt
        ora cnt+1
        bne loop
done:   jmp done
.include "pt3/pt3.s"
.segment "AUDIOCODE"            ; (page aligned)
PT3_LOC:
.incbin "song.pt3"
.res 256, 0                     ; (what a sample read past the module meets)
.export start, done
'''


def have_tools():
    return shutil.which('ca65') and shutil.which('ld65') and a2test.A2RUN.exists()


def asm_frames(work, name, data, n, options=''):
    """pt3_init_song then n pt3_tick in a2run: the 14 registers of each tick."""
    d = work / name
    d.mkdir()
    (d / 'song.pt3').write_bytes(data)
    zp = '$58' if 'ZERO_PAGE' in options else '$C0'     # (the note structs take $80-$F7)
    (d / 'f.s').write_text(ASM.format(zp=zp, options=options, n=n))
    subprocess.run(['ca65', '-g', '-I', str(ROOT / 'dev/lib/apple2'), '-I', str(ROOT / 'dev/lib/apple2/pt3'),
                    '--bin-include-dir', str(d), '-o', str(d / 'f.o'), str(d / 'f.s')], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(d / 'f.lbl'),
                    '-o', str(d / 'f.bin'), str(d / 'f.o')], check=True)
    L = a2test.labels(d / 'f.lbl')
    r = a2test.run(None, a2test.bin_steps(d / 'f.bin', start=L['start']) + [L.until('done', 3000),
                   f'peek:2000:{14 * n}'])
    g = r.mem(0x2000, 14 * n)
    return [list(g[14 * k:14 * k + 14]) for k in range(n)]


def check_asm(work, name, data, n=1100, options='', **kw):
    got = asm_frames(work, name, data, n, options)
    want = pt3play.render(data, n, **kw)
    for t in range(n):
        assert got[t] == want[t], (f'{name}: tick {t}\n asm    ' + ' '.join(f'{x:02X}' for x in got[t])
                                   + '\n python ' + ' '.join(f'{x:02X}' for x in want[t]))
    return n


# ---------------------------------------------------------------- 3-5. conversion
def summary(rep):
    v = rep.validation
    return ', '.join(f"{k} {v[k]['ok']}/{v[k]['n']}" for k in GROUPS) + \
        f" (periods within {v['tolerance']:.1f} cents, worst {v['period']['worst']:.1f})"


def all_agree(rep):
    v = rep.validation
    return all(v[k]['ok'] == v[k]['n'] for k in GROUPS)


def check_mapped():
    song, rep = pt3import.convert(song_mapped())
    data = aysong.encode(song)
    assert aysong.decode(data) == song, 'decode(encode(song)) == song'
    assert aysong.from_json(aysong.to_json(song)) == song
    assert not rep.lost and not rep.approx and not rep.limits, rep
    v = rep.validation
    assert all_agree(rep), summary(rep)
    assert all(v[k]['n'] for k in GROUPS), 'every register group heard: ' + summary(rep)
    assert rep.info['passes'] == 2, 'the loop pass differs (volume 8 carried over): pass 0 + pass 1'
    assert set(rep.exact) >= {'ornament -> arpeggio', 'ornament -> transposition', 'envelope shape + period',
                              'sample position (effect 3) -> instrument start', 'speed (effect 9) -> timing'}
    print(f'PASS synthetic mapped song: {len(data)} B, {len(song.patterns)} patterns of {song.rows} rows, '
          f'{len(song.instruments)} instruments, speed {song.speed}; round trip; over {v["ticks"]} ticks: '
          + summary(rep))
    return rep


def check_unmapped():
    song, rep = pt3import.convert(song_unmapped())
    aysong.encode(song)
    want_lost = {'vibrato (effect 5)', 'envelope slide (effect 8)', 'portamento (-> the target note at once)',
                 'volume change mid-note', 'ornament not an arpeggio (first offset kept)',
                 'sample tone offsets (instruments)', 'noise base change mid-note'}
    want_approx = {'tone slide -> slide (a tick early)', 'envelope period rounded to R12 (R11 = 0)',
                   'envelope set without a note (restarts at the next envelope note)'}
    assert want_lost <= set(rep.lost), set(rep.lost) ^ want_lost
    assert want_approx <= set(rep.approx), set(rep.approx) ^ want_approx
    text = str(rep)
    assert all(k in text for k in want_lost | want_approx)
    print(f'PASS synthetic unmapped song: the report lists {len(rep.lost)} lost and {len(rep.approx)} approximated '
          f'features; agreement {summary(rep)}')


def check_mappable_random(seeds):
    clean = 0
    for seed in seeds:
        song, rep = pt3import.convert(mappable_module(random.Random(seed)))
        data = aysong.encode(song)
        assert aysong.decode(data) == song
        if rep.lost or rep.approx:
            continue
        assert all_agree(rep), f'seed {seed}: {summary(rep)}'
        clean += 1
    assert clean >= len(seeds) // 2, clean
    print(f'PASS {len(seeds)} random mappable modules: the {clean} reporting nothing approximated or lost '
          f'agree 100 % (volume, mixer, noise, envelope, pitch)')


def check_random_convert(seeds):
    for seed in seeds:
        song, rep = pt3import.convert(random_module(random.Random(seed)))
        data = aysong.encode(song)
        assert aysong.encode(aysong.decode(data)) == data
        str(rep)
    print(f'PASS {len(seeds)} random modules (every command and effect) convert and encode')


def check_wg(work, wg):
    song, rep = pt3import.convert(wg)
    data = aysong.encode(song)
    v = rep.validation
    assert v['volume']['ok'] == v['volume']['n'] and v['mixer']['ok'] == v['mixer']['n']
    assert v['period']['ok'] == v['period']['n'] and v['period']['worst'] < 60
    assert not rep.lost and not rep.approx and not rep.limits
    assert rep.info['shift'] == 0, 'PT3 note n sounds MIDI n + 12 = AYS note n'
    out = work / 'WG.AYS'
    pt3import.main([str(work / 'song.pt3'), '-o', str(out)])
    aysong.main(['--import-pt3', str(work / 'song.pt3'), '-o', str(work / 'WG2.AYS'), '--asm', str(work / 'wg.inc')])
    assert out.read_bytes() == (work / 'WG2.AYS').read_bytes() == data
    native, nrep = pt3import.convert(wg, clock='native')
    print(f'PASS WARGALAGA II song: {len(data)} B, {len(song.patterns)} pattern of {song.rows} rows, '
          f'{len(song.instruments)} instruments, speed {song.speed}; {summary(rep)}, mean '
          f'{v["period"]["mean"]:.1f} cents (pt3_lib plays table 1 at 1.02 MHz: ~40 cents sharp); '
          f'--clock native: shift {nrep.info["shift"]:+d}, worst {nrep.info["worst_cents"]:.1f} cents; '
          f'the CLI and aysong.py --import-pt3 write the same bytes')


def check_retime(wg):
    """--to-50hz (MB TRACKER's WG.AYS): the 25 Hz song with speed and
    instrument ticks doubled = each 25 Hz frame played twice at 50 Hz."""
    slow, _ = pt3import.convert(wg, rate=25)
    fast = pt3import.retime(pt3import.convert(wg, rate=25)[0], 2)
    assert fast.speed == 2 * slow.speed and fast.rate == 50
    pa, pb = aysong.Player(aysong.encode(slow)), aysong.Player(aysong.encode(fast))
    for t in range(600):
        fa = pa.tick()
        for k in range(2):
            fb = pb.tick()
            assert fa[:13] == fb[:13], (t, k, fa, fb)
    print(f'PASS --to-50hz: the WG song at 50 Hz (speed {fast.speed}, instrument ticks doubled) = each '
          f'25 Hz frame twice, 600 frames, R0-R12')


def main():
    t0 = time.time()
    check_tables()
    with tempfile.TemporaryDirectory(prefix='pt3imp-') as tmp:
        work = Path(tmp)
        wg = wg_song(work)
        if have_tools():
            n = check_asm(work, 'wg', wg)
            n += check_asm(work, 'mapped', song_mapped())
            n += check_asm(work, 'unmapped', song_unmapped())
            print(f'PASS pt3play = pt3_lib in a2run: the WG song, the two synthetic songs, {n} ticks, every register')
            k = 0
            for seed in range(24):
                k += check_asm(work, f'r{seed}', random_module(random.Random(seed)))
            for seed in range(24, 28):
                k += check_asm(work, f'z{seed}', random_module(random.Random(seed)), options='PT3_USE_ZERO_PAGE = 1',
                               zp=True)
            for seed in range(28, 32):
                k += check_asm(work, f'c{seed}', random_module(random.Random(seed)), options='PT3_FREQ_CONVERSION = 1',
                               convert=True)
            for seed in range(4):
                k += check_asm(work, f'm{seed}', mappable_module(random.Random(seed)))
            print(f'PASS pt3play = pt3_lib in a2run: 24 random modules (every command and effect), 4 in the '
                  f'zero-page build, 4 with PT3_FREQ_CONVERSION, 4 mappable: {k} ticks, every register')
        else:
            print('SKIP pt3play vs pt3_lib: needs ca65, ld65 and dev/tools/a2run/a2run (make -C dev/tools/a2run)')
        check_mapped()
        check_unmapped()
        check_mappable_random(range(16))
        check_random_convert(range(6))
        check_wg(work, wg)
        check_retime(wg)
    print(f'PASS test_pt3_import in {time.time() - t0:.1f} s')


if __name__ == '__main__':
    main()
