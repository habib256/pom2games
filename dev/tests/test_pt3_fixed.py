#!/usr/bin/env python3
"""Fixed PT3 note tables: compatibility, model playback and fail-silent guard.

Default/explicit -1 must emit identical bytes. Every fixed table is played
against the independent PT3 model, with both CPUs/storage/conversion modes.
All 256 header bytes exercise init carry, silent output, JSR/RTS patching,
no-op ticks and matching reinitialization. The immutable WARGALAGA producer
must reject a header that differs from its player's compiled table.
"""
import importlib.util
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'dev/tests'), str(ROOT / 'dev/tools'), str(ROOT / 'dev/tools/audio')]
import a2test  # noqa: E402
import pt3play  # noqa: E402
import test_pt3_import as reference  # noqa: E402

LIBRARY = ROOT / 'dev/lib/apple2'
GENERATOR = ROOT / 'wargalagaii/tools/pt3.py'
SIMPLE = 'PT3_ZP=$50\nPT3_LOC=$4000\n.code\n.include "pt3/pt3.s"\n'
GUARD = '''PT3_ZP=$60
PT3_FIXED_NOTE_TABLE={table}
.code
entry: sei
done: jmp done
init_i0: cli
        jmp pt3_init_song
init_i1: sei
        jmp pt3_init_song
.include "pt3/pt3.s"
.segment "AUDIOCODE"
PT3_LOC:
.incbin "song.pt3"
.res 256,0
.export entry,done,init_i0,init_i1
'''


def build(work, name, source, defines=(), cpu='6502'):
    src = work / (name + '.s')
    src.write_text(source)
    obj, binary, labels = (src.with_suffix(ext) for ext in ('.o', '.bin', '.lbl'))
    args = ['ca65', '-g', '--cpu', cpu, '-I', str(LIBRARY), '--bin-include-dir', str(work)]
    for define in defines:
        args += ['-D', define]
    subprocess.run([*args, '-o', str(obj), str(src)], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'),
                    '-Ln', str(labels), '-o', str(binary), str(obj)], check=True)
    return binary, a2test.labels(labels)


def defaults(work):
    for cpu in ('6502', '65c02'):
        for zp in (0, 1):
            for convert in (0, 1):
                defs = [f'PT3_FREQ_CONVERSION={convert}'] + (['PT3_USE_ZERO_PAGE=1'] if zp else [])
                name = f'default{cpu}{zp}{convert}'
                a, _ = build(work, name, SIMPLE, defs, cpu)
                b, _ = build(work, name + 'explicit', SIMPLE, defs + ['PT3_FIXED_NOTE_TABLE=-1'], cpu)
                assert a.read_bytes() == b.read_bytes(), name
    src = work / 'invalid.s'
    src.write_text(SIMPLE)
    for value in (-2, 4, 255):
        result = subprocess.run(['ca65', '-I', str(LIBRARY), '-D', f'PT3_FIXED_NOTE_TABLE={value}',
                                 '-o', str(work / 'invalid.o'), str(src)], capture_output=True, text=True)
        assert result.returncode and 'PT3_FIXED_NOTE_TABLE: -1 or 0..3' in result.stderr
    print('PASS PT3 fixed table: default = explicit -1 in all 8 CPU/ZP/conversion configurations; invalid values rejected')


def producer(work):
    sys.path.insert(0, str(GENERATOR.parent))
    spec = importlib.util.spec_from_file_location('fixed_pt3_producer', GENERATOR)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    data = gen.module()             # validates the actual src/music.s declaration
    assert data[0x63] == gen.validate_player_table(data) == 1
    for table in range(4):
        source = work / 'music.s'
        source.write_text(f'PT3_FIXED_NOTE_TABLE = {table} ; fixture\n')
        for header in range(4):
            changed = bytearray(data)
            changed[0x63] = header
            try:
                got = gen.validate_player_table(changed, source)
            except ValueError:
                assert header != table
            else:
                assert header == table and got == table
    source.write_text('PT3_FIXED_NOTE_TABLE = -1\n')
    try:
        gen.validate_player_table(data, source)
    except ValueError:
        pass
    else:
        raise AssertionError('the immutable producer accepted a dynamic player declaration')
    print('PASS WARGALAGA immutable producer: compiled table/header agree; mismatches and a dynamic declaration rejected')
    return data


def render(work, cpus):
    count = 0
    for cpu in cpus:
        for table in range(4):
            data = bytearray(reference.random_module(random.Random(40 + table)))
            data[0x63] = table
            for zp in (0, 1):
                for convert in (0, 1):
                    folder = work / f'render{cpu}{table}{zp}{convert}'
                    folder.mkdir()
                    (folder / 'song.pt3').write_bytes(data)
                    options = f'PT3_FIXED_NOTE_TABLE={table}\nPT3_FREQ_CONVERSION={convert}\n'
                    options += 'PT3_USE_ZERO_PAGE=1\n' if zp else ''
                    source = reference.ASM.format(zp='$58' if zp else '$C0', options=options, n=512)
                    binary, labels = build(folder, 'render', source)
                    disk = a2test.build_disk(folder, 'FIXED', binary) if cpu else None
                    result = a2test.run(disk, a2test.bin_steps(binary, start=labels['start']) +
                                       [labels.until('done', 3000), 'peek:2000:7168'], iie=bool(cpu))
                    expected = pt3play.render(data, 512, zp=bool(zp), convert=bool(convert))
                    assert result.mem(0x2000, 7168) == bytes(x for frame in expected for x in frame), \
                        (cpu, table, zp, convert, 'model frames')
                    count += 512
    print(f'PASS fixed PT3 playback: {count} model frames, all 4 tables, both storage/conversion modes and available CPUs')


def guard(work, cpus, module):
    total = 0
    for cpu in cpus:
        for table in range(4):
            folder = work / f'guard{cpu}{table}'
            folder.mkdir()
            data = bytearray(module)
            data[0x63] = table
            (folder / 'song.pt3').write_bytes(data)
            binary, labels = build(folder, 'guard', GUARD.format(table=table))
            steps = a2test.bin_steps(binary, start=labels['entry']) + [labels.until('done', 100)]
            expected, cases = [], []
            for header in [*range(256), table]:
                for irq in (0, 1):
                    steps += [f'poke:{labels["PT3_LOC"] + 0x63:04X}:{header:02X}']
                    steps += a2test.pokes(0x70, bytes([0xA5]) * 14)
                    steps += [f'call:{labels["init_i1" if irq else "init_i0"]:04X}:100',
                              labels.peek('pt3_tick'), 'peek:0069:1']
                    good = header == table
                    expected += [bytes([0x20 if good else 0x60]), bytes([0 if good else 1])]
                    silent = bytes([0] * 7 + [63] + [0] * 5 + [255])
                    frames = [bytes(frame) for frame in pt3play.render(data, 2)] if good else [silent] * 2
                    for frame in frames:
                        steps += [f'call:{labels["pt3_tick"]:04X}:10', 'peek:0070:14']
                        expected.append(frame)
                    cases.append((good, irq))
            disk = a2test.build_disk(folder, 'GUARD', binary) if cpu else None
            result = a2test.run(disk, steps, iie=bool(cpu))
            assert result.dumps == expected, (cpu, table, 'opcode/DONE/silence/recovery frames')
            calls = re.findall(r'elapsed=(\d+) A=([0-9A-F]{2}) X=([0-9A-F]{2}) '
                               r'Y=([0-9A-F]{2}) P=([0-9A-F]{2})', result.out)
            assert len(calls) == len(cases) * 3
            for index, (good, irq) in enumerate(cases):
                group = calls[index * 3:index * 3 + 3]
                assert int(group[0][4], 16) & 13 == irq * 4 + int(not good), (cpu, table, index)
                assert all((int(call[4], 16) & 12) == irq * 4 for call in group)
                if not good:
                    assert [int(call[0]) for call in group[1:]] == [6, 6]
                    assert group[0][1:] == group[1][1:] == group[2][1:], 'a rejected tick changed registers/flags'
            total += len(cases)
    print(f'PASS fixed PT3 guard: {total} init cases, all 256 header bytes, I/D/C, JSR/RTS patch, '
          'silent frames, 6-cycle no-op ticks and matching reinitialization')


def main():
    cpus = [0, 1] if a2test.have_a2shot('test_pt3_fixed (65C02)') else [0]
    with tempfile.TemporaryDirectory(prefix='pt3-fixed-') as temp:
        work = Path(temp)
        defaults(work)
        module = producer(work)
        render(work, cpus)
        guard(work, cpus, module)


if __name__ == '__main__':
    main()
