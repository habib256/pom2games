#!/usr/bin/env python3
"""Silent AYS voices: independent register/state oracle and tick budgets.

All retained volume offsets -15..15, 3/6-voice players, a 3-voice song
under a 6-voice player, cached/fast periods and both CPUs. The unused
state is poisoned: an off voice must preserve it, output zero volume and
turn off tone/noise. The second chip of a 3-voice song remains untouched
except R13's documented per-tick sentinel. No AY hardware is needed;
ordered hardware writes are covered by test_aysong.py and test_mb_irq.py.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

SOURCE = '''AYSONG_VOICES = {voices}
AYSONG_FAST_PERIODS = {fast}
AYSONG_CPU65C02 = {c02}
{cpu}
.macro AYSONG_WRITE
.endmacro
.bss
guard_before: .res 1
.code
start: sei
done:  jmp done
irq_on:
       cli
       jmp checked_tick
irq_off:
       sei
checked_tick:
       php
       pla
       sta entry_p
       tsx
       stx entry_sp
       jsr ays_tick
       php
       pla
       sta exit_p
       tsx
       stx exit_sp
       rts
.include "aysong.asm"
.bss
guard_after: .res 1
entry_p: .res 1
exit_p: .res 1
entry_sp: .res 1
exit_sp: .res 1
.export start,done,irq_on,irq_off
'''


def build(work, voices, fast, c02):
    src = work / f'silent{voices}{fast}{c02}.s'
    src.write_text(SOURCE.format(voices=voices, fast=fast, c02=c02,
                                cpu='.setcpu "65C02"' if c02 else ''))
    obj, binary, labels = (src.with_suffix(ext) for ext in ('.o', '.bin', '.lbl'))
    subprocess.run(['ca65', '-g', '-I', str(ROOT / 'dev/lib/apple2'),
                    '-o', str(obj), str(src)], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'),
                    '-Ln', str(labels), '-o', str(binary), str(obj)], check=True)
    return binary, a2test.labels(labels)


def check(work, voices, nv, fast, c02):
    binary, labels = build(work, voices, fast, c02)
    first, end = labels['guard_before'], labels['guard_after'] + 1
    steps = a2test.bin_steps(binary, start=labels['start']) + [labels.until('done', 100)]
    expected = []
    for case, offset in enumerate(range(-15, 16)):
        for irq in (0, 1):
            state = bytearray((case * 7 + j * 19 + irq * 11) & 255 for j in range(end - first))

            def store(name, values):
                at = labels[name] - first
                values = [values] if isinstance(values, int) else values
                state[at:at + len(values)] = bytes(values)

            store('ays_play', 0)
            store('ays_nv', nv)
            store('ays_von', [0] * voices)
            store('ays_vvoff', [offset & 255] * voices)
            # The empty writer still maintains the player's shadow. Start it
            # equal to the frame so expected changes follow the public frame.
            regs = bytes(state[labels['ays_regs'] - first:labels['ays_regs'] - first + voices // 3 * 16])
            store('ays_out', regs)
            steps += a2test.pokes(first, state) + labels.poke('ays_zp', [0xA5, 0x5A, 0x39, 0xC6, 0x7E])
            steps += [f'call:{labels["irq_off" if irq else "irq_on"]:04X}:2',
                      f'peek:{first:04X}:{end - first}', labels.peek('ays_zp', 5),
                      labels.peek('entry_p', 4)]
            for chip in range(voices // 3):
                state[labels['ays_regs'] - first + 16 * chip + 13] = 255
                if chip < nv // 3:
                    for register, value in ((7, 63), (8, 0), (9, 0), (10, 0)):
                        for name in ('ays_regs', 'ays_out'):
                            state[labels[name] - first + 16 * chip + register] = value
            for voice in range(nv):
                state[labels['ays_vmix'] - first + voice] = 9
            expected.append((bytes(state), bytes([0xA5, 0x5A, 0x39, 0, 0]), irq))
    disk = a2test.build_disk(work, f'SILENT{voices}{fast}', binary) if c02 else None
    result = a2test.run(disk, steps, iie=bool(c02))
    assert len(result.dumps) == len(expected) * 3
    for index, (want, zp, irq) in enumerate(expected):
        got, got_zp, status = result.dumps[index * 3:index * 3 + 3]
        assert got == want, (voices, nv, fast, c02, index, 'frame, shadow, retained state or guard')
        assert got_zp == zp, (voices, nv, fast, c02, index, 'zero-page state')
        assert status[0] & 12 == status[1] & 12 == irq * 4, ('I/D', list(status))
        assert status[2] == status[3], ('hardware stack', list(status))
    cycles = [int(value) for value in re.findall(r'elapsed=(\d+)', result.out)]
    assert len(cycles) == len(expected)
    # Includes the status/stack wrapper and call overhead. The preceding
    # implementation spends at least 105 extra cycles on three off voices.
    budget = 600 if nv == 3 else 1100
    assert max(cycles) <= budget, (voices, nv, fast, c02, max(cycles), budget)
    return len(expected), min(cycles), max(cycles)


def main():
    cpus = [0]
    if a2test.have_a2shot('test_aysong_silent (65C02)'):
        cpus.append(1)
    with tempfile.TemporaryDirectory(prefix='aysong-silent-') as temp:
        work = Path(temp)
        for c02 in cpus:
            for voices, nv in ((3, 3), (6, 3), (6, 6)):
                for fast in (0, 1):
                    count, low, high = check(work, voices, nv, fast, c02)
                    print(f'PASS silent AYS {voices}-voice player/{nv}-voice song, '
                          f'{"65C02" if c02 else "NMOS"}, fast={fast}: {count} states, '
                          f'registers/shadow/retained state/guards/ZP/I/D/stack; {low}..{high} cycles')


if __name__ == '__main__':
    main()
