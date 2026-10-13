#!/usr/bin/env python3
"""Zero disk access after the preload; RAM transfers counted and exact.

Two independent observations cover every disk path of ordinary play:
the MLI counters of memory.s (every call made through mli_call, including
the loader's) and an a2shot watch on the ProDOS MLI entry $BF00, which also
catches a call that would bypass the counters. DOS 3.3 is absent: no code
of the link refers to its entry points, and RWTS/BLOAD/$03D0 never run.
"""
import re
import sys
from common import HERE, L, DISK, a2test, text_screen
from scenario import SCRIPT, play

COUNTERS = (('mli_calls', 2), ('mli_reads', 2), ('mli_bytes', 3),
            ('xfer_count', 2), ('xfer_bytes', 3), ('overlay_reads', 2))


def counters(session):
    return {name: int.from_bytes(session.step(L.peek(name, size)).data, 'little')
            for name, size in COUNTERS}


DOS_TARGETS = {0x03D0 + k for k in range(0x20)} | {0xB7B5, 0xA56E}
OPCODES = {0x20, 0x4C, 0x6C, 0xAD, 0x8D, 0x2C}


def static_check():
    """No DOS 3.3 entry, RWTS call or BLOAD command survives in the link.

    Every assembled instruction of build/wild.lst and build/boot.lst is
    decoded from the listing: an absolute JSR/JMP/LDA/STA/BIT operand may
    not reach the DOS vectors $03D0-$03EF, RWTS $B7B5 or BLOAD $A56E.
    """
    for name in ('wild', 'boot'):
        for line in (HERE / f'build/{name}.lst').read_text().splitlines():
            m = re.match(r'^[0-9A-F]{6}r \d+\s+((?:[0-9A-Fr]{2} ){3})', line)
            if not m:
                continue
            fields = m.group(1).split()
            if 'rr' in fields[1:] or not all(re.fullmatch('[0-9A-F]{2}', f) for f in fields):
                continue
            opcode, lo, hi = (int(f, 16) for f in fields)
            assert not (opcode in OPCODES and lo | hi << 8 in DOS_TARGETS), line
    for path in [HERE / 'build/wild.bin', HERE / 'build/NEOWILD.SYSTEM'] + sorted(
            (HERE / 'build').glob('wild*.bin')):
        assert b'BLOAD' not in path.read_bytes(), path
    names = (HERE / 'build/wild.lbl').read_text()
    assert 'dos_cmd' not in names and 'apple2_zp_save' not in names


def main():
    static_check()
    print('  no DOS 3.3 entry, RWTS, BLOAD or command buffer left in the link: OK')
    with a2test.Session(DISK, timeout=900) as s:
        s.step(L.until('idle', 40000))
        boot = counters(s)
        assert boot['xfer_count'] >= 1
        # Watch the ProDOS entry for the rest of the run.
        s.step(f'watch:BF00')
        rows = []
        state = dict(before=counters(s))

        def each(step):
            after = counters(s)
            before = state['before']
            rows.append((step[0], {k: after[k] - before[k] for k in after}))
            state['before'] = after

        out_before = len(s.out)
        play(s, L, SCRIPT, each)
        watched = s.out[out_before:].count('watch BF00')
        final = counters(s)
    print(f'  boot: {boot["mli_calls"]} MLI calls, {boot["mli_reads"]} reads, '
          f'{boot["mli_bytes"]} bytes read; {boot["xfer_count"]} RAM transfers')
    failures = 0
    for keys, delta in rows:
        label = keys.replace('\r', '').replace('\\', '')
        ok = delta['mli_calls'] == 0 and delta['mli_reads'] == 0 and delta['mli_bytes'] == 0
        failures += not ok
        print(f'  {label:18} disk calls {delta["mli_calls"]}, module loads '
              f'{delta["overlay_reads"]:2}, RAM transfers {delta["xfer_count"]:2} '
              f'({delta["xfer_bytes"]:6} bytes): {"OK" if ok else "FAIL"}')
    assert final['xfer_count'] - boot['xfer_count'] == sum(d['xfer_count'] for _, d in rows)
    print(f'  ProDOS MLI entry $BF00 reached {watched} times after the preload')
    if failures or watched or final['mli_calls'] != boot['mli_calls']:
        print('FAIL: disk access during ordinary play')
        sys.exit(1)
    print('Zero disk reads after the preload: OK')


if __name__ == '__main__':
    main()
