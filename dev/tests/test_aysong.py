#!/usr/bin/env python3
"""lib/apple2/aysong.asm in a2run against dev/tools/audio/aysong.py's
reference player, register for register: a fixture calls ays_tick N times
and logs the 14 registers of each chip after every tick (ays_regs) and
every AY write the player makes (a logging AYSONG_WRITE). Python plays the
same bytes and must give the same frames and the same writes (only the
registers that changed, R13 when not $FF). Songs: the demo (3 voices,
every effect, envelope, loop), a song that stops at its end, random songs
(3 and 6 voices, every effect, instrument loops, shared tracks, 1- to
64-row patterns), a 6-voice song under the 3-voice player, and a script
of ays_mute / ays_set_pos / ays_stop calls between ticks. Then encode /
decode round trips, the text import, the --asm emitter, the code size
and the cycles of one tick (a2run call:, mb_write to a slot-4 card)."""
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(ROOT / 'dev/tools/audio'))
import a2test  # noqa: E402
import aysong  # noqa: E402
from aysong import Cell, Instrument, Pattern, Song, Tick  # noqa: E402

FAST = 'FAST\n'                 # (check: the fast-period option)
FRAMES = 0x2000                 # frame log: the two HGR pages (16 KB)
WRITES = 0x1000                 # write log: (chip << 4 | register, value)
WRITES_END = 0x2000

SRC = '''{options}
.zeropage
lp:     .res 2
wp:     .res 2
.macro AYSONG_WRITE             ; log it: X kept
        pha
        tya
        asl a
        asl a
        asl a
        asl a
        stx ays_wx
        ora ays_wx
        ldy #0
        sta (wp),y
        pla
        iny
        sta (wp),y
        lda wp
        clc
        adc #2
        sta wp
        bcc :+
        inc wp+1
:       lda wp+1                ; full: the last pair again and again
        cmp #>{wend}
        bcc :+
        lda #<({wend}-2)
        sta wp
        lda #>({wend}-2)
        sta wp+1
:
.endmacro
.code
start:  lda #<song
        ldy #>song
        jsr ays_init
        lda #<{frames}
        sta lp
        lda #>{frames}
        sta lp+1
        lda #<{writes}
        sta wp
        lda #>{writes}
        sta wp+1
        lda #0
        sta tick
        sta tick+1
        sta sp
loop:   ldy sp                  ; the script's calls due before this tick
        lda script,y
        cmp tick
        bne @tick
        lda script+1,y
        cmp tick+1
        bne @tick
        lda script+3,y
        ldx script+4,y
        pha
        lda script+2,y
        tay
        pla
        dey
        bne :+
        jsr ays_mute
        jmp @next
:       dey
        bne :+
        jsr ays_set_pos
        jmp @next
:       jsr ays_stop
@next:  lda sp
        clc
        adc #5
        sta sp
        jmp loop
@tick:  jsr ays_tick
        ldy #13
:       lda ays_regs,y
        sta (lp),y
        dey
        bpl :-
.if FRAME = 28
        ldy #13
:       lda ays_regs+16,y
        pha
        tya
        clc
        adc #14
        tay
        pla
        sta (lp),y
        tya
        sec
        sbc #15
        tay
        bpl :-
.endif
        lda lp
        clc
        adc #FRAME
        sta lp
        bcc :+
        inc lp+1
:       inc tick
        bne :+
        inc tick+1
:       lda tick
        cmp #<NTICKS
        bne :+
        lda tick+1
        cmp #>NTICKS
        beq done
:       jmp loop
done:   jmp done
script: .byte {script}
song:   .byte {song}
.bss
tick:   .res 2
sp:     .res 1
.code
.include "aysong.asm"
.export start, done
'''

CYCLES_SRC = '''{options}
MB_FAST_WRITE = 1
.code
start:  lda #4                  ; a card in slot 4 for mb_write (fast: the
        sta mb_slot             ; operands are $C4xx as assembled)
        lda #<song
        ldy #>song
        jsr ays_init
done:   jmp done
        .word ays_tick          ; (referenced: assembled)
song:   .byte {song}
.include "aysong.asm"
.include "mockingboard.asm"
.export start, done
'''


def build(work, name, text):
    src = work / (name + '.s')
    src.write_text(text)
    obj, binary, lbl = (src.with_suffix(e) for e in ('.o', '.bin', '.lbl'))
    subprocess.run(['ca65', '-g', '-I', str(ROOT / 'dev/lib/apple2'), '-o', str(obj), str(src)], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(lbl),
                    '-o', str(binary), str(obj)], check=True)
    return binary, a2test.labels(lbl)


def model(data, nticks, script, max_voices):
    p = aysong.Player(data, max_voices)
    frames, writes = [], []
    shadow = [[0xFF] * 14 for _ in range(p.chips)]
    for t in range(nticks):
        for when, action, a, x in script:
            if when == t:
                if action == 1:
                    p.mute = a
                elif action == 2:
                    p.set_pos(a, x)
                else:
                    p.stop()
        f = p.tick()
        frames.append(f)
        for c in range(p.chips):
            regs = f[14 * c:14 * c + 14]
            for r in range(12, -1, -1):
                if regs[r] != shadow[c][r]:
                    shadow[c][r] = regs[r]
                    writes.append((c << 4 | r, regs[r]))
            if regs[13] != 0xFF:
                writes.append((c << 4 | 13, regs[13]))
    return frames, writes


def check(work, name, data, nticks, script=(), voices=3, options='', song_voices=3):
    frame = 14 * (min(voices, song_voices) // 3)
    assert nticks * frame <= 0x4000
    sc = []
    for when, action, a, x in script:
        sc += [when & 255, when >> 8, action, a, x]
    sc += [255, 255, 0, 0, 0]
    opts = f'AYSONG_VOICES = {voices}\nFRAME = {frame}\nNTICKS = {nticks}\n' + options
    opts = opts.replace('FAST', 'AYSONG_FAST_PERIODS = 1')
    binary, L = build(work, name, SRC.format(options=opts, frames=FRAMES, writes=WRITES, wend=WRITES_END,
                                             script=', '.join(map(str, sc)),
                                             song=', '.join(map(str, data))))
    r = a2test.run(None, a2test.bin_steps(binary, start=L['start']) + [L.until('done', 600),
                   f'peek:{FRAMES:04X}:{nticks * frame}', f'peek:{WRITES:04X}:{WRITES_END - WRITES}'])
    got = r.mem(FRAMES, nticks * frame)
    wlog = r.mem(WRITES, WRITES_END - WRITES)
    frames, writes = model(data, nticks, script, voices)
    for t, f in enumerate(frames):
        g = list(got[t * frame:(t + 1) * frame])
        assert g == f, (f'{name}: tick {t}\n asm    ' + ' '.join(f'{x:02X}' for x in g)
                        + '\n python ' + ' '.join(f'{x:02X}' for x in f))
    n = min(len(writes), (WRITES_END - WRITES) // 2 - 1)
    assert n > 50, f'{name}: {n} writes only'
    gw = [(wlog[2 * k], wlog[2 * k + 1]) for k in range(n)]
    assert gw == writes[:n], f'{name}: AY writes differ at #{next(k for k in range(n) if gw[k] != writes[k])}'
    return n


def rand_song(rng, voices, npat=4, rows=None):
    ins = []
    for _ in range(rng.randint(1, 15)):
        ticks = []
        for _ in range(rng.randint(1, 12)):
            ticks.append(Tick(rng.randint(0, 15), rng.random() < .8, rng.random() < .3, rng.random() < .1,
                              rng.randint(0, 31) if rng.random() < .2 else None))
        loop = rng.choice([None, rng.randrange(len(ticks))])
        shape = rng.choice([None, None, rng.randint(0, 15)])
        ins.append(Instrument(ticks, loop, shape, rng.randint(0, 255)))
    rows = rows or rng.choice([1, 2, 7, 16, 32, 64])
    pats = []
    shared = None
    for _ in range(npat):
        tracks = []
        for _v in range(voices):
            if shared and rng.random() < .2:
                tracks.append(shared)
                continue
            t = []
            for _r in range(rows):
                c = Cell()
                x = rng.random()
                if x < .35:
                    c.note = rng.randint(0, 95)
                elif x < .42:
                    c.note = aysong.OFF
                if rng.random() < .25:
                    c.ins = rng.randint(1, len(ins))
                if rng.random() < .3:
                    c.fx = rng.randint(0, 7)
                    c.param = rng.randint(1, 255) if c.fx in (4, 5) else rng.randint(0, 255)
                    if c.fx in (4, 5) and rng.random() < .7:
                        c.param = rng.randint(1, 4)
                t.append(c)
            tracks.append(t)
            shared = t
        pats.append(Pattern(tracks))
    order = [rng.randrange(npat) for _ in range(rng.randint(1, 6))]
    return Song(pats, ins, order, voices, rows, rng.randint(1, 4), 50,
                rng.choice([None, rng.randrange(len(order))]))


def code_size(work):
    src = '''.code
start:  lda #<0
        ldy #>0
        jsr ays_init
        jsr ays_tick
        jsr ays_stop
        jsr ays_mute
        jsr ays_pos
        jsr ays_set_pos
first:
.include "aysong.asm"
last:
.include "mockingboard.asm"
.export first, last
'''
    out = {}
    for voices in (3, 6):
        for c02 in (0, 1):
            for fast in (0, 1):
                opts = f'AYSONG_VOICES = {voices}\nAYSONG_CPU65C02 = {c02}\nAYSONG_FAST_PERIODS = {fast}\n' + \
                    ('.setcpu "65C02"\n' if c02 else '')
                _, L = build(work, f'size{voices}{c02}{fast}', opts + src)
                out[voices, c02, fast] = L['last'] - L['first']
    return out


def option_values(work):
    """Each switch: = default assembles the bytes of no definition, the
    other value differs (ABI.md: options are values)."""
    prog = '''{opts}
MB_IRQ_TICK = ays_tick
.code
        jsr mb_irq_start
        jsr mb_irq_stop
        jsr mb_put
        jsr mb_hush
        lda #0
        tay
        jsr ays_init
        jsr ays_tick
.include "mb_irq.asm"
.include "aysong.asm"
.include "mockingboard.asm"
_a2_vbl_scan: rts               ; (apple2vbl.s's, for MB_IRQ_SCAN)
'''
    def image(opts, k=[0]):
        k[0] += 1
        b, _ = build(work, f'opt{k[0]}', prog.format(opts=opts))
        return b.read_bytes()
    base = image('')
    switches = [('MB_IRQ_PRODOS', 1, 0), ('MB_IRQ_SCAN', 0, 1), ('MB_IRQ_HUSH_BOTH', 0, 1), ('MB_IRQ_SPLIT', 0, 1),
                ('AYSONG_VOICES', 3, 6), ('AYSONG_FAST_PERIODS', 0, 1)]
    for name, default, other in switches:
        assert image(f'{name} = {default}') == base, f'{name} = {default} is not the default'
        if name != 'MB_IRQ_SPLIT':   # (placement only: the same bytes here)
            assert image(f'{name} = {other}') != base, f'{name} = {other} changes nothing'
    c02 = '.setcpu "65C02"\n'
    assert image(c02 + 'AYSONG_CPU65C02 = 0') == image(c02) != image(c02 + 'AYSONG_CPU65C02 = 1')
    return [n for n, _, _ in switches] + ['AYSONG_CPU65C02']


def cycles(work, data, voices, ticks, extra=''):
    binary, L = build(work, f'cycles{voices}', CYCLES_SRC.format(options=f'AYSONG_VOICES = {voices}\n{extra}',
                                                                 song=', '.join(map(str, data))))
    steps = a2test.bin_steps(binary, start=L['start']) + [L.until('done', 100)]
    steps += [f'call:{L["ays_tick"]:04X}:2'] * ticks
    r = a2test.run(None, steps)
    import re
    return [int(e) for e in re.findall(r'elapsed=(\d+)', r.out)]


def main():
    demo = aysong.encode(aysong.demo())
    assert len(demo) <= 2048
    with tempfile.TemporaryDirectory(prefix='aysong-') as tmp:
        work = Path(tmp)
        n = check(work, 'demo', demo, 600)
        print(f'PASS demo song ({len(demo)} B): 600 ticks (past its loop), every frame and {n} AY writes as the model')
        stop = aysong.demo()
        stop.loop = None
        stop.order = [0, 2]
        sdata = aysong.encode(stop)
        check(work, 'stop', sdata, 260)
        f, _ = model(sdata, 260, (), 3)
        assert all(x[8:11] == [0, 0, 0] for x in f[-40:]), 'silence after the end'
        print('PASS a song without loop: plays its 2 entries then stops, silent (frames and writes as the model)')
        script = [(30, 1, 0b101, 0), (60, 1, 0, 0), (90, 2, 2, 3), (95, 2, 1, 15), (130, 3, 0, 0),
                  (150, 2, 0, 0), (170, 2, 4, 2), (171, 1, 2, 0)]
        check(work, 'script', demo, 300, script)
        print('PASS ays_mute / ays_set_pos (mid-pattern, last row, again next tick) / ays_stop / restart: as the model')
        check(work, 'demo_fast', demo, 600, options=FAST)
        print('PASS AYSONG_FAST_PERIODS = 1 (the 96-note table): the demo as the model')
        rng = random.Random(1983)
        kinds = [(3, 3, ''), (3, 3, ''), (3, 3, FAST), (6, 6, ''), (6, 6, FAST), (6, 3, ''), (3, 6, '')]
        for k, (voices, player, opt) in enumerate(kinds):
            song = rand_song(rng, voices, rows=64 if k == 1 else None)
            data = aysong.encode(song)
            assert aysong.encode(aysong.decode(data)) == data
            nt = 1100 if player == 3 else 560
            check(work, f'random{k}', data, nt, voices=player, options=opt, song_voices=voices)
            print(f'PASS random song {k}: {voices} voices under the {player}-voice player{" (fast periods)" if opt else ""}, '
                  f'{len(song.patterns[0].tracks[0])} rows, speed {song.speed}, {len(song.instruments)} instruments, '
                  f'loop {song.loop}: {nt} ticks as the model')
        # round trips, the text import, the emitter
        song = aysong.demo()
        assert aysong.decode(demo) == song, 'decode(encode(demo)) == demo'
        assert aysong.from_json(aysong.to_json(song)) == song
        inc = work / 'demo.inc'
        aysong.main(['--demo', '--asm', str(inc), '--label', 'demo_song', '-o', str(work / 'DEMO.AYS')])
        assert (work / 'DEMO.AYS').read_bytes() == demo
        text = inc.read_text()
        emitted = [int(x) for line in text.splitlines() if line.startswith('.byte')
                   for x in line[5:].split(',')]
        assert 'demo_song:' in text and bytes(emitted) == demo, 'the --asm rows hold the song'
        big = Song([Pattern([[Cell(note=(r * 7 + v * 5 + p) % 96 if r % 2 == 0 else None,
                                   ins=1 + (r % 3) if r % 8 == 0 else None, fx=1 if r % 16 == 0 else None, param=0x37)
                              for r in range(64)] for v in range(3)]) for p in range(8)],
                   [Instrument([Tick(15 - k) for k in range(8)], 4) for _ in range(3)], list(range(8)))
        size = len(aysong.encode(big))
        assert size <= 2048, size
        print(f'PASS encode/decode/JSON round trips, the --asm emitter; a 3-voice 8-pattern 64-row song with a note '
              f'every 2 rows: {size} B (budget 2048)')
        names = option_values(work)
        print('PASS options are values: ' + ', '.join(names) + ' at their default = undefined, byte for byte')
        sizes = code_size(work)
        print('PASS code size (+ data tables): ' + ', '.join(f'{v} voices{" 65C02" if c else ""}{" fast" if f else ""} {s} B'
                                                           for (v, c, f), s in sizes.items()))
        six = aysong.encode(rand_song(random.Random(7), 6))
        for fast in ('', 'AYSONG_FAST_PERIODS = 1'):
            c3 = cycles(work, demo, 3, 400, fast)
            c6 = cycles(work, six, 6, 300, fast)
            print(f'PASS cycles per ays_tick{" (fast periods)" if fast else ""}, mb_write to a card: 3 voices (demo) '
                  f'first tick (13 writes) {c3[0]}, then max {max(c3[1:])}, mean {sum(c3) // len(c3)}; '
                  f'6 voices (random) first {c6[0]}, then max {max(c6[1:])}, mean {sum(c6) // len(c6)}')


if __name__ == '__main__':
    main()
