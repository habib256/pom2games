#!/usr/bin/env python3
"""lib/apple2/tune.asm in a2run, from the speaker log: tune_play of a
3-note tune (two notes around a rest) toggles the speaker exactly
(ticks - 1) * toggles times per note at tone's period (12 + 5 * X cycles),
lasts its ticks at ~1/60 s each, and returns; tune_start loops the tune
under repeated tune_tick until tune_stop; TUNE_MUTE = a zero byte keeps
the tempo without a single toggle."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

NOTES = [(4, 0x40, 51), (3, 0, 0), (5, 0x80, 26)]      # ticks, half period, toggles
TICK = 17030                                            # a video frame

SRC = '''.include "apple2.inc"
{options}
.code
        JSR     tune_stop
        LDA     #0
        STA     muted
start:  LDA     #<tune
        LDY     #>tune
        JSR     tune_play
played: LDA     #<tune
        LDY     #>tune
        JSR     tune_start
        LDA     #30                     ; 30 ticks: two passes and a bit
        STA     n
@t:     JSR     tune_tick
        DEC     n
        BNE     @t
looped: JSR     tune_stop
        JSR     tune_tick
        JSR     tune_tick
done:   JMP     done
tune:   .byte   {tune}, 0
.bss
n:      .res 1
muted:  .res 1
.code
.include "tune.asm"
.include "sound.asm"
.export start, played, looped, done
'''


def build(work, name, options):
    src = work / (name + '.s')
    src.write_text(SRC.format(options=options, tune=', '.join(str(b) for note in NOTES for b in note)))
    obj, binary, lbl = (src.with_suffix(e) for e in ('.o', '.bin', '.lbl'))
    subprocess.run(['ca65', '-I', str(ROOT / 'dev/lib/apple2'), '-o', str(obj), str(src)], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(lbl),
                    '-o', str(binary), str(obj)], check=True)
    return binary, a2test.labels(lbl)


def run(work, name, options):
    binary, L = build(work, name, options)
    log = work / (name + '.spk')
    r = a2test.run(None, a2test.bin_steps(binary) + [f'spklog:{log}', L.until('start', 10), 'spk', L.until('played', 100), 'spk',
                                                     L.until('looped', 100), 'spk', L.until('done', 100), 'spk'])
    return r, [int(c) for c in log.read_text().split()]


def main():
    once = sum((t - 1) * f for t, _, f in NOTES)
    ticks = sum(t for t, _, _ in NOTES)
    with tempfile.TemporaryDirectory(prefix='tune-') as tmp:
        work = Path(tmp)
        r, log = run(work, 'plain', '')
        _, played, looped, stopped = r.spk
        start, end_play = r.cycles[0], r.cycles[1]
        log = [c for c in log if c < end_play]          # tune_play's toggles
        assert played == once, f'tune_play: {played} toggles, expected {once}'
        # pitch: the first note's flips are 12 + 5 * X cycles apart
        gaps = {b - a for a, b in zip(log[:NOTES[0][2]], log[1:NOTES[0][2]])}
        assert gaps == {12 + 5 * NOTES[0][1]}, f'first note period {gaps}'
        gaps = {b - a for a, b in zip(log[-NOTES[2][2]:], log[-NOTES[2][2] + 1:])}
        assert gaps == {12 + 5 * NOTES[2][1]}, f'last note period {gaps}'
        length = end_play - start
        assert 0.9 * ticks * TICK < length < 1.15 * ticks * TICK, f'tune_play lasted {length} cycles'
        # 30 ticks of a 12-tick loop: two passes (24 ticks), then 4 ticks of
        # the first note again and 2 of the rest
        assert looped == 2 * once + 3 * NOTES[0][2], f'tune_start loop: {looped} toggles'
        assert stopped == 0, 'tune_stop: still playing'
        r, log = run(work, 'mute', 'TUNE_MUTE = muted')
        assert r.spk[1:] == [0, 0, 0], f'TUNE_MUTE: {r.spk}'
        length = r.cycles[1] - r.cycles[0]
        assert 0.9 * ticks * TICK < length < 1.15 * ticks * TICK, f'muted tune lasted {length} cycles'
    print(f'tune: tune_play {once} toggles at both pitches in ~{ticks} ticks, tune_start loops, '
          'tune_stop silences, TUNE_MUTE keeps the tempo silently.')


if __name__ == '__main__':
    main()
