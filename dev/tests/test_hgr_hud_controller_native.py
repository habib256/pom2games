#!/usr/bin/env python3
"""HUD controller pointer lifetimes, independent pixels/cache and live IRQs.

Both HUD sizes run all widths, seven phases, both pages and bottom edges,
cache hits, decimal increments/carries, overflow, invalidation and NULL calls.
Caller-owned fields occupy low RAM, reserved ZP, HGR RAM disjoint from drawing,
and C-stack RAM; every invalid compact width byte is checked. Only the old
private two-byte field slot is normalized when it is removed.
Each return from a helper that preserves ptr3 is checked. The 16x16 cell
must borrow ptr3 and its caller must restore it. A real VIA IRQ saves,
borrows and restores all cc65 pointer/tmp scratch; exact saved-frame evidence
filters instructions deferred by the SDK's IRQ-plus-first-PHA step.
Separate/folded column tables and two code placements expose layout costs.
A first T1 interval 36..129 cycles followed by a 499-cycle latch exercises
the compact entry pointer in tmp1; each field location must be interrupted
inside that live range. P is exact without IRQs; under IRQs only the SDK
software B shadow is excluded, with all hardware flags still checked.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

from test_hgr import DEV, ROOT, compile_source, run

HGRC = DEV / 'lib/hgrc'
KERNEL = HGRC / 'hgr_hud_putu.inc'
PROBE = DEV / 'bench/hgr_hud_controller_probe.cpp'
MEMBERS = '''hgr_build_rows.s hgr_columns.s hgr_draw_page.s hgr_fixed_rows.s
hgr_font.c hgr_glyph_params.s hgr_glyph_shift.s hgr_hud.s hgr_hud8.s
hgr_hud8_asm.s hgr_hud8_digits.s hgr_hud8_putu.s hgr_hud_asm.s
hgr_hud_init.s hgr_hud_invalidate.s hgr_hud_putu.s hgr_lores_state.s
hgr_masks.s hgr_phases.s hgr_rows_asm.s hgr_set_draw_page.s hgr_state.c
hgr_text_addr.s hgr_utoa_asm.s'''.split()
STUB = '''.import _hgr_hud_putu,_hgr_hud8_putu,_hgr_hud_init,_hgr_hud8_init
.import _hgr_set_draw_page,_hgr_hud_invalidate,_hgr_build_columns,_hgr_build_masks,_hgr_build_phases
.export start
.code
start:rts
.rodata
.word _hgr_hud_putu,_hgr_hud8_putu,_hgr_hud_init,_hgr_hud8_init
.word _hgr_set_draw_page,_hgr_hud_invalidate,_hgr_build_columns,_hgr_build_masks,_hgr_build_phases
'''
CONFIG = '''MEMORY {{
 ZP:start=$50,size=$B0,type=rw;
 RAM:start=${base:X},size=$9000-${base:X},type=rw,file=%O;
 STATE:start=$9000,size=$2000,type=rw;
}}
SEGMENTS {{
 ZEROPAGE:load=ZP,type=zp,define=yes;
 CODE:load=RAM,type=ro;
 RODATA:load=RAM,type=ro;
 DATA:load=RAM,type=rw;
 BSS:load=STATE,type=bss,define=yes;
}}
'''


def library(folder, include, folded, overrides=None):
    folder.mkdir()
    objects = []
    overrides = overrides or {}
    for name in MEMBERS:
        source = HGRC / name
        obj = folder / ('hgrc__' + name + '.o')
        flags = ['-t', 'none', '-Oirs', '-I', HGRC,
                 '-I', DEV / 'lib/apple2c', '-I', DEV / 'lib/gfx',
                 '--asm-include-dir', HGRC, '--asm-include-dir', DEV / 'lib/apple2']
        if folded and name in ('hgr_columns.s', 'hgr_masks.s', 'hgr_phases.s'):
            flags += ['--asm-define', 'HGRC_X7_FOLDED=1']
        text = overrides.get(name)
        if text is None and name in ('hgr_hud_putu.s', 'hgr_hud8_putu.s'):
            text = (HGRC / name).read_text().replace('.include "hgr_hud_putu.inc"', include)
        if name == 'hgr_hud8_putu.s':
            # Zero-byte audit aliases; no extra production exports or bytes.
            saved = '        sta tmp1                ; transient pointer low; IRQs preserve scratch\n        txa'
            if saved in text:
                text = text.replace(saved, saved.replace('\n        txa', '\nhud8_audit_low_live:\n        txa'))
                text = text.replace('        lda tmp1\n        sta ptr3',
                                    '        lda tmp1\nhud8_audit_low_done:\n        sta ptr3')
                text += '\n.export hud8_audit_low_live,hud8_audit_low_done\n'
            text += '\n.export hud8_audit_value := value\n.ifdef field\n.export hud8_audit_field := field\n.endif\n'
        if text is not None:
            source = folder / name
            source.write_text(text)
        compile_source(source, obj, flags)
        objects.append(obj)
    archive = folder / 'hgrc.lib'
    run(['ar65', 'a', archive, *objects])
    return archive


def link(folder, archive, stub, base):
    config = folder / f'{base:x}.cfg'
    config.write_text(CONFIG.format(base=base))
    binary, labels = (folder / f'{base:x}{ext}' for ext in ('.bin', '.lbl'))
    run(['cl65', '-t', 'none', '-C', config, '-o', binary, '-Ln', labels,
         '-m', folder / f'{base:x}.map', stub, archive])
    return binary, labels


def command(executable, before, after, rom, base, cpu, irq):
    return [executable, *before, *after, rom, base, cpu, irq]


def parse_result(output):
    match = re.search(r'CPU=(\d) IRQ=(\d) base=([0-9A-F]+) calls/source=(\d+) '
        r'cycles=(\d+)->(\d+) faster/equal/slower=(\d+)/(\d+)/(\d+) maxdelta=(-?\d+); '
        r'large ptr3 borrows=(\d+); IRQs=(\d+)/(\d+); exact pixels/cache/ordered-stores/BSS/AXYP/'
        r'stack/C-stack/code/main/aux PASS', output)
    assert match, output
    groups = match.groups()
    result = dict(zip(('cpu', 'irq', 'calls_per_source', 'before_cycles', 'after_cycles',
        'faster_putu', 'equal_putu', 'slower_putu', 'maximum_cycle_delta',
        'large_cell_ptr3_borrows', 'before_irqs', 'after_irqs'),
        map(int, (*groups[:2], *groups[3:]))))
    result['code_base'] = int(groups[2], 16)
    result['preserved_helper_returns'] = [dict(address=int(address, 16), calls=int(count))
        for address, count in re.findall(r'preserved helper \$([0-9A-F]+): (\d+) returns', output)]
    slow = re.search(r'SLOW small=(\d+) large=(\d+) maximum_relative=([.\d]+)%', output)
    result.update(small_slower=int(slow[1]), large_slower=int(slow[2]),
                  maximum_relative_cycle_increase_percent=float(slow[3]))
    stores = re.search(r'ORDERED source stores: pixels=(\d+) cache=(\d+); IRQ deferrals=(\d+)/(\d+)', output)
    result.update(dict(zip(('pixel_stores', 'cache_stores', 'before_irq_deferrals',
                           'after_irq_deferrals'), map(int, stores.groups()))))
    live = re.search(r'ENTRY live-low IRQs=(\d+)', output)
    result['entry_live_low_irqs'] = int(live[1]) if live else 0
    result['entry_irqs_by_field'] = {address: int(count) for address, count in
        re.findall(r'ENTRY field=\$([0-9A-F]+) IRQs=(\d+)', output)}
    result['worst_calls'] = [line for line in output.splitlines() if line.startswith('WORST ')]
    return result


def negative_controls(work, executable, old, source, stub, rom):
    text = Path(source).read_text()
    large_old = '''        jsr cell_run
.if !HUD_SMALL
        jsr field_ptr           ; the 16x16 cell borrows ptr3 for masks/row
.endif'''
    entry_old = '        stx ptr3+1'
    assert large_old in text and entry_old in text
    mutations = (
        ('missing_large_restore', 'hgr_hud_putu.s', text.replace(large_old,
            '        jsr cell_run\n        ; deliberate missing large restore', 1)),
        ('wrong_compact_pointer_high', 'hgr_hud8_putu.s', text.replace(entry_old,
            '        sta ptr3+1', 1)),
    )
    results = []
    for name, member, include in mutations:
        wrapper = (HGRC / member).read_text().replace('.include "hgr_hud_putu.inc"', include)
        archive = library(work / name, text, 0, {member: wrapper})
        after = link(work / name, archive, stub, 0x6000)
        result = subprocess.run(list(map(str, command(executable, old, after, rom, 0x6000, 0, 0))),
                                capture_output=True, text=True, timeout=60)
        assert result.returncode and 'assert' in result.stderr.lower(), (name, result.stderr)
        print('HUD controller negative:', name, 'rejected', flush=True)
        results.append(dict(name=name, rejected=True))
    getter = (HGRC / 'hgr_draw_page.s').read_text().replace('.code', '.importzp ptr3\n.code')
    getter = getter.replace('        rts', '        inc ptr3\n        rts')
    name = 'helper_clobbers_ptr3'
    archive = library(work / name, text, 0, {'hgr_draw_page.s': getter})
    after = link(work / name, archive, stub, 0x6000)
    result = subprocess.run(list(map(str, command(executable, old, after, rom, 0x6000, 0, 0))),
                            capture_output=True, text=True, timeout=60)
    assert result.returncode and 'HELPER ptr3 REJECT' in result.stderr, result.stderr
    print('HUD controller negative:', name, 'rejected', flush=True)
    results.append(dict(name=name, rejected=True))
    name = 'irq_drops_ptr3_restore'
    bad = work / 'bad_irq.cpp'
    bad.write_text('#define HGRC_TEST_BAD_IRQ 1\n' + PROBE.read_text())
    bad_executable = work / 'bad_irq'
    run(['make', '-s', '-C', DEV / 'tools/a2shot', 'probe',
         'SRC=' + str(bad), 'OUT=' + str(bad_executable)])
    # Correct old/new kernels isolate the deliberately invalid IRQ contract.
    good = work / 'good_irq'
    archive = library(good, text, 0)
    after = link(good, archive, stub, 0x6000)
    result = subprocess.run(list(map(str, command(bad_executable, old, after, rom, 0x6000, 0, 1))),
                            capture_output=True, text=True, timeout=60)
    match = re.search(r'HELPER ptr3 REJECT actual_irqs=(\d+)', result.stderr)
    assert result.returncode and match and int(match[1]) > 0, result.stderr
    print('HUD controller negative:', name, 'rejected after', match[1], 'real IRQs', flush=True)
    results.append(dict(name=name, rejected=True, actual_irqs=int(match[1])))
    name = 'irq_drops_live_tmp1_restore'
    bad_low = work / 'bad_low.cpp'
    bad_source = '#define HGRC_TEST_BAD_LOW 1\n' + PROBE.read_text()
    bad_source = bad_source.replace('for (bool small:{false,true})', 'for (bool small:{true})')
    bad_low.write_text(bad_source)
    bad_executable = work / 'bad_low'
    run(['make', '-s', '-C', DEV / 'tools/a2shot', 'probe',
         'SRC=' + str(bad_low), 'OUT=' + str(bad_executable)])
    result = subprocess.run(list(map(str, command(bad_executable, old, after, rom, 0x6000, 0, 1))),
                            capture_output=True, text=True, timeout=60)
    fault = re.search(r'ENTRY TMP1 IRQ fault injected at actual IRQ entry (\d+)', result.stderr)
    assert result.returncode and fault and int(fault[1]) > 0, result.stderr
    assert 's.accumulator==expected' in result.stderr, result.stderr
    print('HUD controller negative:', name, 'rejected inside observed live range', flush=True)
    results.append(dict(name=name, rejected=True, observed_entry_irq=int(fault[1])))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--reference', help='compare a historical shared HUD source with production')
    group.add_argument('--source', type=Path, help='compare a private shared HUD include with production')
    parser.add_argument('--negative', action='store_true', help='validate pointer-lifetime fault detectors')
    parser.add_argument('--jobs', type=int, default=2, help='independent native matrices in parallel (default 2)')
    parser.add_argument('--out', type=Path, help='write measurements and exact source identities')
    args = parser.parse_args()
    assert args.jobs > 0
    report = dict(reference=args.reference, results=[], negative_controls=[])
    with tempfile.TemporaryDirectory(prefix='hgr-hud-controller-') as directory:
        work = Path(directory)
        before, after = KERNEL, args.source or KERNEL
        if args.reference:
            before = work / 'reference.inc'
            before.write_bytes(subprocess.check_output(['git', 'show',
                args.reference + ':dev/lib/hgrc/hgr_hud_putu.inc'], cwd=ROOT))
        stub = work / 'stub.s'
        stub.write_text(STUB)
        run(['ca65', '-t', 'none', '-o', work / 'stub.o', stub])
        stub = work / 'stub.o'
        rom = work / 'irq.rom'
        image = bytearray(8192)
        image[-2:] = bytes((0, 9))
        rom.write_bytes(image)
        executable = work / 'hud-controller-probe'
        run(['make', '-s', '-C', DEV / 'tools/a2shot', 'probe',
             'SRC=' + str(PROBE), 'OUT=' + str(executable)])
        fixtures = []
        for folded in (0, 1):
            old_folder, new_folder = work / f'before-{folded}', work / f'after-{folded}'
            old_lib = library(old_folder, before.read_text(), folded)
            new_lib = library(new_folder, after.read_text(), folded)
            for base in (0x6000, 0x60F1):
                old = link(old_folder, old_lib, stub, base)
                new = link(new_folder, new_lib, stub, base)
                for cpu in (0, 1):
                    for irq in (0, 1):
                        fixtures.append((folded, base, cpu, irq, old, new))
        def measure(fixture):
            folded, base, cpu, irq, old, new = fixture
            output = run(command(executable, old, new, rom, base, cpu, irq))
            result = parse_result(output)
            result.update(folded_tables=bool(folded), before_loaded_bytes=old[0].stat().st_size,
                          after_loaded_bytes=new[0].stat().st_size)
            return output, result
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for output, result in pool.map(measure, fixtures):
                print(output.strip(), flush=True)
                report['results'].append(result)
        if args.negative:
            old = next(f[4] for f in fixtures if f[:4] == (0, 0x6000, 0, 0))
            report['negative_controls'] = negative_controls(work, executable, old, after, stub, rom)
        report['kernel_sources'] = [dict(role=role, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                                    for role, path in (('before', before), ('after', after))]
        report['native_environment'] = dict(cpus=['NMOS6502', 'CMOS65C02'], iie_memory=True,
            timing='NTSC', decimal_flag=0, code_bases=[0x6000, 0x60F1],
            column_tables=['separate', 'HGRC_X7_FOLDED'], rom_sha256=hashlib.sha256(image).hexdigest(),
            irq='real VIA T1, first count36..129 then latch499; saved/restored A/X/Y and ptr1..4/tmp1..4; entry-frame evidence',
            status='full P without IRQ; under IRQ all bits except SDK software B shadow',
            bss='only the removed private HUD8 field slot normalized; all remaining state compared',
            fields=[0x1200, 0xA0, 0x2110, 0xB1F8])
    paths = [KERNEL, PROBE, Path(__file__).resolve(), *[HGRC / name for name in MEMBERS],
             DEV / 'lib/math/dec.asm', DEV / 'lib/font/bbfont_glyphs.inc', DEV / 'lib/font/bbfont_c.inc',
             DEV / 'tools/a2shot/probe.hpp', DEV / 'tools/a2shot/sdk/include/pom2/core.hpp',
             DEV / 'tools/a2shot/sdk.mk']
    paths += list(DEV.glob('tools/a2shot/sdk/lib/*/libpom2_core.a'))
    report['source_identities'] = [dict(path=str(path.relative_to(ROOT)),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in dict.fromkeys(paths)]
    if args.out:
        args.out.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
