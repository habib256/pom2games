#!/usr/bin/env python3
"""joy.asm stick_key / joy_buttons in a2run. A loop logs every key that
stick_key returns (caller's STICK_KEYS table) and every newly pressed
button of joy_buttons ($80 + bits). Checks: one event per deflection or
press, each on its own edge (releasing a button under a held direction
fires nothing), centring rearms, button 0 over button 1 over a direction,
a direct change of direction fires, no stick (both axes open) reads no
button; STICK_KEY_REPEAT repeats a held event every n calls and
STICK_KEY_FAST samples with read_stick_fast; without STICK_KEYS A = X =
the event number."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

SRC = '''.include "apple2.inc"
{options}
.code
        LDA     #0
        STA     stick_key_last
        STA     joy_btn_last
        STA     log_ix
        STA     calls
loop:   INC     calls
        JSR     stick_key
        BEQ     @btn
        JSR     put
@btn:   JSR     joy_buttons
        TXA
        BEQ     loop
        ORA     #$80
        JSR     put
        JMP     loop
put:    LDY     log_ix
        STA     log,Y
        INY
        TYA
        AND     #63
        STA     log_ix
        RTS
keys:   .byte   "UDLR01"
.bss
log_ix: .res 1
calls:  .res 1
log:    .res 64
.code
.include "joy.asm"
.export loop, log, log_ix
'''


def build(work, name, options):
    src = work / (name + '.s')
    src.write_text(SRC.format(options=options))
    obj, binary, lbl = (src.with_suffix(e) for e in ('.o', '.bin', '.lbl'))
    subprocess.run(['ca65', '-I', str(ROOT / 'dev/lib/apple2'), '-l', str(src.with_suffix('.lst')),
                    '-o', str(obj), str(src)], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(lbl),
                    '-o', str(binary), str(obj)], check=True)
    return binary, a2test.labels(lbl)


def events(binary, L, script):
    steps = [L.until('loop', 4000), 'joy:0,0', 'btn:0,0', 'btn:1,0', 'wait:10']
    for s in script:
        steps += [s, 'wait:10']
    steps += [L.peek('log_ix'), L.peek('log', 64)]
    r = a2test.run(None, a2test.bin_steps(binary) + steps)
    n = r.dumps[-2][0]
    return r.dumps[-1][:n]


SCRIPT = ['joy:0,-1', 'joy:0,0', 'joy:0,-1', 'joy:0,0', 'joy:1,0', 'joy:0,0',
          'btn:0,1', 'btn:1,1', 'btn:0,0', 'btn:1,0',
          'joy:-1,0', 'joy:0,1', 'joy:0,0',
          'joy:9,9', 'btn:0,1', 'btn:0,0']
# U, rearm, U, R, B0 (+ joy_buttons bit 0), B1 pressed under B0: its own
# edge, B1 fires (+ joy_buttons bit 1); releases: nothing; L, D without
# centring; unplugged: button 0 is no stick event, joy_buttons still sees
# it (no replug afterwards: a2run changing an open axis mid-read is a
# deflection).
EXPECTED = b'UUR0\x811\x82LD\x81'

# Regression (chess): a button pressed and released while a direction is
# held must not fire that direction again; a held button does not block a
# new direction; centring then deflecting fires.
HELD = ['joy:0,-1', 'btn:0,1', 'btn:0,0', 'btn:1,1', 'joy:1,0', 'btn:1,0',
        'joy:0,0', 'joy:1,0']
HELD_EXPECTED = b'U0\x811\x82RR'


def main():
    with tempfile.TemporaryDirectory(prefix='stick-key-') as tmp:
        work = Path(tmp)
        binary, L = build(work, 'k', 'STICK_KEYS = keys')
        got = events(binary, L, SCRIPT)
        assert got == EXPECTED, f'stick_key/joy_buttons events {got!r}, expected {EXPECTED!r}'
        got = events(binary, L, HELD)
        assert got == HELD_EXPECTED, f'button under a held direction {got!r}, expected {HELD_EXPECTED!r}'

        binary, L = build(work, 'n', '')
        got = events(binary, L, ['joy:0,-1', 'joy:0,0', 'btn:1,1', 'btn:1,0', 'joy:1,0'])
        assert got == b'\x01\x06\x82\x04', f'without STICK_KEYS: {got!r}'

        binary, L = build(work, 'f', 'STICK_KEYS = keys\nSTICK_KEY_FAST = 1\nJOY_LO = 15\nJOY_HI = 65')
        got = events(binary, L, ['joy:0,-1', 'joy:0,0', 'joy:-1,0', 'joy:0,0', 'joy:0,1'])
        assert got == b'ULD', f'STICK_KEY_FAST: {got!r}'

        binary, L = build(work, 'r', 'STICK_KEYS = keys\nSTICK_KEY_REPEAT = 4')
        got = events(binary, L, ['joy:0,-1', 'joy:0,0', 'joy:1,0'])
        # 10 frames ~ 170,000 cycles ~ 26 read_stick calls: the first U, then
        # one every 4 calls while held, nothing while centred.
        ups, rights = got.count(b'U'), got.count(b'R')
        assert got == b'U' * ups + b'R' * rights and 4 <= ups <= 9 and 4 <= rights <= 9, \
            f'STICK_KEY_REPEAT {got!r}'
    print('stick_key: one event per deflection/press, rearm, button priority, no direction refire on a button release, no stick reads no button; '
          'joy_buttons edges; table-less events, STICK_KEY_FAST, STICK_KEY_REPEAT OK.')


if __name__ == '__main__':
    main()
