#!/usr/bin/env python3
"""Independent Mockingboard reload/patch oracles, including IRQ scratch aliases.

Every 16-bit reload is exercised in active/inactive sessions and both I
states. An injected IRQ borrows the shared scratch while preserving CPU
registers. All 256 link phases check both AY patch halves in every valid
slot, all C/I/V/D states, ordered VIA writes and stack/guards. The SDK's
65C02 additionally verifies every reload against the actual VIA model.
"""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / 'dev'
sys.path.insert(0, str(DEV / 'tools'))
import a2test  # noqa: E402

CFG = '''MEMORY {{ ZP:start=$50,size=$B0,type=rw; RAM:start=${start:04X},size=$3000,file=%O; }}
SEGMENTS {{ ZEROPAGE:load=ZP,type=zp; CODE:load=RAM,type=ro; BSS:load=RAM,type=bss; }}
'''


def run(args, **kwargs):
    return subprocess.run([str(arg) for arg in args], check=True, **kwargs)


def build(work, kernel, fast, absolute):
    folder = work / f'kernel{fast}{absolute}'
    folder.mkdir()
    (folder / 'mockingboard.asm').write_bytes(kernel.read_bytes())
    source = folder / 'fixture.s'
    text = ('mb_probe_old=$3000\n' if absolute else '') + f'MB_FAST_WRITE={fast}\n.code\n'
    text += '.include "mockingboard.asm"\n.export mb_probe_old\n'
    if fast:
        text += '.export ' + ','.join(f'mb_fast{i}' for i in range(12)) + '\n'
    source.write_text(text)
    obj = folder / 'fixture.o'
    run(['ca65', '-g', '-I', folder, '-o', obj, source])
    return folder, obj


def link(folder, obj, origin=0):
    config = folder / 'fixture.cfg'
    config.write_text(CFG.format(start=0x6000 + origin))
    binary, labels = folder / 'fixture.bin', folder / 'fixture.lbl'
    run(['ld65', '-C', config, '-Ln', labels, '-o', binary, obj])
    return binary, labels, a2test.labels(labels)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, help='assemble this mockingboard.asm instead')
    args = parser.parse_args()
    kernel = (args.reference or DEV / 'lib/apple2/mockingboard.asm').resolve()
    with tempfile.TemporaryDirectory(prefix='mockingboard-native-') as temp:
        work = Path(temp)
        timer, init = work / 'timer_bus', work / 'init_bus'
        for source, output in (('mb_timer_bus.c', timer), ('mb_init_bus.c', init)):
            run(['cc', '-O2', '-I', DEV / 'tools/a2run', Path(__file__).with_name(source),
                 DEV / 'tools/a2run/cpu6502.c', '-o', output])
        native = work / 'timer_native'
        have_native = a2test.have_a2shot('test_mockingboard_native (65C02)')
        if have_native:
            run(['make', '-s', '-C', DEV / 'tools/a2shot', 'probe',
                 f'SRC={Path(__file__).with_name("mb_timer_native.cpp")}', f'OUT={native}'])
        for fast in (0, 1):
            for absolute in (0, 1):
                folder, obj = build(work, kernel, fast, absolute)
                binary, labels, symbols = link(folder, obj)
                names = ('mb_timer_start', 'mb_slot', 'mb_timer_active', 'mb_old_acr',
                         'mb_old_ier', 'mb_ptr', 'mb_probe_old')
                values = [symbols[name] for name in names]
                # The optional reference is the preceding two-byte BSS form.
                period = symbols.get('mb_period', 0)
                values += [period, 2 if period else 0]
                print(f'MB_FAST_WRITE={fast}, scratch={"absolute" if absolute else "ZP"}:', flush=True)
                run([timer, binary, *[f'{value:x}' for value in values]])
                if have_native:
                    run([native, binary, labels, DEV / 'tools/a2shot/roms/apple2e.rom'])
                if fast and not absolute:
                    low, high = 1 << 60, 0
                    for origin in range(256):
                        binary, _, symbols = link(folder, obj, origin)
                        names = ('mb_init', 'mb_slot', 'mb_chip', 'mb_timer_active', 'mb_ptr')
                        values = [0x6000 + origin, *[symbols[name] for name in names],
                                  *[symbols[f'mb_fast{i}'] for i in range(12)]]
                        output = run([init, binary, *[f'{value:x}' for value in values]],
                                     capture_output=True, text=True).stdout
                        rows = [tuple(map(int, line.split())) for line in output.splitlines()]
                        assert len(rows) == 96
                        low = min(low, *(row[2] for row in rows))
                        high = max(high, *(row[2] for row in rows))
                    print(f'PASS init patches: 24,576 slot/flag/link-phase cases, both AY halves, '
                          f'exact VIA protocol/guards/stack; {low}..{high} cycles', flush=True)


if __name__ == '__main__':
    main()
