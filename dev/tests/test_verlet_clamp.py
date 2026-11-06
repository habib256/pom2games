#!/usr/bin/env python3
"""Velocity clamps: exhaustive signed words, legacy limits, public entry matrix.

Every positive whole-pixel limit and representative fractional/legacy limits
is checked independently, including -32768, core guards and X/Y/I/D/HWSP.
A/NZCV are scratch. The public matrix checks direct/exported entries in both
orders, equal/different limits, unused undefined parameters and caller aliases.
--bench also runs isolated exact-layout game/model/cadence/budget checks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from test_hgr import DEV, a2test
from test_verlet_contact_all import CONFIG as BASE_CONFIG
from test_verlet_ground_probes import identity, metadata
from verlet import harness

ROOT = DEV.parent
CONFIG = BASE_CONFIG.replace('CODE: load=MAIN, type=ro;',
                             'CODE: load=MAIN, type=ro, align=$100;')
LIMITS = [*range(256, 32768, 256), 0, 1, 0x7F, 0x80, 0xFF, 0x101, 0x17F,
          0x180, 0x1FF, 0x7F80, 0x7FFF, 0x8000, 0x8001, 0xFFFF, 0x10000, -1, -32768]
PAIRS = ((0x600, 0x600), (0x1200, 0x800), (0x601, 0x601), (0x601, 0x581), (0, 0), (0x8000, 0x8000))
MODES = ('x', 'y', 'xy', 'yx', 'export_x', 'export_y', 'export_xy', 'export_yx')


def domain(include, iie):
    variant = include.name
    report = {}
    for limit in LIMITS:
        guarded = ('vl_vx', 'vl_vx+1', 'vl_w0', 'vl_w1', 'vl_w2')
        seed = (166, 195, 93, 114, 185)
        fields = ('vl_val', 'vl_val+1', 'returned_x', 'returned_y', 'returned_flags', 'stack_delta', *guarded)
        setup = ''.join((f' lda #{v}\n sta {f}\n' for f, v in zip(guarded, seed)))
        copy = ''.join((f' lda {field}\n sta results+{plane * 256},x\n' for plane, field in enumerate(fields)))
        source = '''.macpack longbranch
MUL_TABLES=$0800
.include "math.inc"
VL_NPOINTS=1
.include "verlet.inc"
.zeropage
input: .res 2
saved_hw: .res 1
returned_x: .res 1
returned_y: .res 1
returned_flags: .res 1
stack_delta: .res 1
.code
 cld
 lda #0
 sta input
 sta input+1
''' + setup + '''loop:
 tsx
 stx saved_hw
 lda input
 and #1
 asl
 asl
 ora #$71
 pha
 plp
 ldx input
 ldy #$a5
 lda input
 sta vl_val
 lda input+1
 sta vl_val+1
 jsr kernel_start
 stx returned_x
 sty returned_y
 php
 pla
 and #$0c
 sta returned_flags
 tsx
 txa
 sec
 sbc saved_hw
 sta stack_delta
 ldx input
''' + copy + ''' inc input
 jne loop
page_done: nop
resume:
 inc input+1
 jeq done
 jmp loop
done: jmp done
.align 256
kernel_start:
''' + f' VL_CLAMP_VAL {limit}\n' + '''kernel_end:
.segment "SNAPS"
results: .res ''' + str(len(fields) * 256) + '''
.export page_done,resume,done,results,kernel_start,kernel_end
'''
        with tempfile.TemporaryDirectory(prefix='clamp-domain-') as d:
            work = Path(d)
            cfg = work / 'fixture.cfg'
            cfg.write_text(CONFIG)
            labels, binary = harness.build(work, source, includes=(include,), cfg=cfg)
            disk = a2test.build_disk(work, 'TEST', binary) if iie else None
            steps = a2test.bin_steps(binary)
            for _ in range(256):
                steps += [labels.until('page_done'), labels.peek('results', len(fields) * 256), labels.until('resume')]
            steps += [labels.until('done'), labels.peek('kernel_start', labels['kernel_end'] - labels['kernel_start'])]
            result = a2test.run(disk, steps, iie=iie, timeout=180)
            for high in range(256):
                values = []
                for low in range(256):
                    bits = high * 256 + low
                    signed = bits - 65536 if high & 128 else bits
                    if 0 < limit < 32768:
                        clamped = max(-limit, min(signed, limit)) & 65535
                    else:
                        bound = (limit if signed >= 0 else -limit) & 65535
                        clamped = min(bits, bound) if signed >= 0 else max(bits, bound)
                    values.append((clamped & 255, clamped >> 8, low, 165, (low & 1) << 2, 0, *seed))
                expected = bytes((value[plane] for plane in range(len(fields)) for value in values))
                assert result.dumps[high] == expected, (iie, variant, limit, high)
            report[str(limit)] = dict(cases=65536, bytes=labels['kernel_end'] - labels['kernel_start'], snapshot_sha256=hashlib.sha256(b''.join(result.dumps[:-1])).hexdigest(), code_sha256=hashlib.sha256(result.dumps[-1]).hexdigest())
    return report


def api_matrix(include, iie):
    variant = include.name
    report = {}
    for layout in ('default', 'zp_alias', 'absolute_alias'):
        for mx, my in PAIRS:
            for mode in MODES:
                refs = mode.removeprefix('export_')
                exports = mode.startswith('export_')
                key = f'{layout}_{mx}_{my}_{mode}'
                source = '''MUL_TABLES=$0800
.include "math.inc"
VL_NPOINTS=1
'''
                if layout != 'default':
                    source += f"vl_val=${(16 if layout == 'zp_alias' else 16384):04x}\n"
                if 'x' in refs:
                    source += f'VL_VMAX_X={mx}\n'
                if 'y' in refs:
                    source += f'VL_VMAX_Y={my}\n'
                source += '''.include "verlet.inc"
.code
 cld
 jmp ready
references:
'''
                for char in refs:
                    source += ('.export ' if exports else ' jsr ') + f'vl_clamp_v{char}\n'
                source += ''' rts
.align 256
kernel_start:
.include "verlet.asm"
kernel_end:
ready: jmp ready
.export ready,kernel_start,kernel_end
.export vl_val
'''
                for char in ('x', 'y'):
                    source += f'.if .defined(vl_clamp_v{char})\n.export vl_clamp_v{char}\n.endif\n'
                with tempfile.TemporaryDirectory(prefix='clamp-link-') as d:
                    work = Path(d)
                    cfg = work / 'fixture.cfg'
                    cfg.write_text(CONFIG)
                    labels, binary = harness.build(work, source, includes=(include,), cfg=cfg)
                    for char in ('x', 'y'):
                        assert (f'vl_clamp_v{char}' in labels) == (char in refs), (variant, key, char, 'emission')
                    if 'x' in refs and 'y' in refs:
                        assert mx == my or labels['vl_clamp_vx'] != labels['vl_clamp_vy'], (variant, key, 'entry aliases')
                    steps = a2test.bin_steps(binary) + [labels.until('ready')]
                    expected = []
                    for char in refs:
                        limit = mx if char == 'x' else my
                        for value in (0, 1, 255, 256, limit - 1, limit, limit + 1, -limit - 1, -limit, -limit + 1, 32767, -32768, -1):
                            bits = value & 65535
                            signed = bits - 65536 if bits & 32768 else bits
                            if 0 < limit < 32768:
                                result = max(-limit, min(signed, limit)) & 65535
                            else:
                                bound = (limit if signed >= 0 else -limit) & 65535
                                result = min(bits, bound) if signed >= 0 else max(bits, bound)
                            expected.append(result.to_bytes(2, 'little'))
                            steps += a2test.pokes(labels['vl_val'], bits.to_bytes(2, 'little'))
                            steps += [f"call:{labels['vl_clamp_v' + char]:04X}:2", labels.peek('vl_val', 2)]
                    disk = a2test.build_disk(work, 'TEST', binary) if iie else None
                    actual = a2test.run(disk, steps, iie=iie)
                    assert actual.dumps == expected, (variant, iie, key, 'public result')
                    report[key] = dict(cases=len(expected), kernel_bytes=labels['kernel_end'] - labels['kernel_start'], snapshot_sha256=hashlib.sha256(actual.data).hexdigest())
    source = '''MUL_TABLES=$0800
.include "math.inc"
VL_NPOINTS=1
.include "verlet.inc"
.code
start:jmp start
kernel_start:
.include "verlet.asm"
kernel_end:
.assert .not .defined(vl_clamp_vx),error,"unused vx emitted"
.assert .not .defined(vl_clamp_vy),error,"unused vy emitted"
.export kernel_start,kernel_end
'''
    with tempfile.TemporaryDirectory(prefix='clamp-unused-') as d:
        work = Path(d)
        labels, binary = harness.build(work, source, includes=(include,))
        assert labels['kernel_start'] == labels['kernel_end']
    return report


def costs(include, iie):
    values = (0, 1, 1535, 1536, 1537, 3072, 32767, -1537, -1536, -1535, -1, -32768)
    source = '''MUL_TABLES=$0800
.include "math.inc"
VL_NPOINTS=1
.include "verlet.inc"
.code
 cld
'''
    for index, value in enumerate(values):
        source += (f' lda #{value&255}\n sta vl_val\n lda #{value>>8&255}\n sta vl_val+1\n'
                   f'start{index}: jsr kernel_start\nend{index}: nop\n'
                   f'.export start{index},end{index}\n')
    source += '''done: jmp done
.align 256
kernel_start: VL_CLAMP_VAL $600
kernel_end:
.export done,kernel_start,kernel_end
'''
    with tempfile.TemporaryDirectory(prefix='clamp-costs-') as directory:
        work = Path(directory)
        cfg = work / 'fixture.cfg'
        cfg.write_text(CONFIG)
        labels, binary = harness.build(work, source, includes=(include,), cfg=cfg)
        disk = a2test.build_disk(work, 'TEST', binary) if iie else None
        steps = a2test.bin_steps(binary)
        for index in range(len(values)):
            steps += [labels.until(f'start{index}'), labels.until(f'end{index}')]
        steps.append(labels.until('done'))
        result = a2test.run(disk, steps, iie=iie)
        return dict(bytes=labels['kernel_end']-labels['kernel_start'],
                    scope='JSR/RTS; page-contained branches',
                    cycles={str(value): result.cycles[2*index+1]-result.cycles[2*index]
                            for index, value in enumerate(values)})


def budget_sources():
    games = [ROOT / 'cutrope', ROOT / 'dirtbike',
             *(DEV / 'examples' / name for name in ('catapult', 'lander', 'rope', 'halfpipe'))]
    folders = [*(game / part for game in games for part in ('src', 'tests', 'tools')),
               *(DEV / 'lib' / part for part in ('apple2', 'hgr', 'font', 'math', 'physics')),
               DEV / 'tools/verlet']
    paths = {path for folder in folders for path in folder.rglob('*')
             if path.suffix in ('.s', '.asm', '.inc', '.cfg', '.bas', '.py')}
    paths.add(DEV / 'cc65/apple2_hgr.cfg')
    # Existing generated assets are read only; private linking/disk packaging
    # writes its own main/menu/title output and all sector patches.
    paths.update(ROOT / 'dirtbike/build' / name for name in (
        'tune.bin', 'pages.bin', 'title.lz4', 'hof.bin', 'tracks/menu_data.inc'))
    paths.update(ROOT / 'dirtbike/build/tracks' / f'T{index:02}.bin' for index in range(1, 31))
    return [dict(path=str(path.relative_to(ROOT)), **identity(path)) for path in sorted(paths)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path,
                        help='directory containing saved verlet.inc and verlet.asm')
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--bench', action='store_true', help='also run six isolated real clients')
    parser.add_argument('--only', choices=('domain', 'api', 'clients'))
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    selected = args.reference or DEV / 'lib/physics'
    if selected.is_file():
        selected = selected.parent
    with tempfile.TemporaryDirectory(prefix='verlet-clamp-') as directory:
        work = Path(directory)
        include = work / 'selected'
        include.mkdir()
        for name in ('verlet.inc', 'verlet.asm'):
            (include / name).write_bytes((selected / name).read_bytes())
        report = dict(cpu='65C02' if args.iie else 'NMOS6502', reference=bool(args.reference))
        if args.only in (None, 'domain'):
            report['domain'] = domain(include, args.iie)
            print(f'{report["cpu"]}: {len(LIMITS)} limits × 65,536 values; clamp/state/guards exact.', flush=True)
        if args.only in (None, 'api'):
            report['api'] = api_matrix(include, args.iie)
            print(f'{len(report["api"])} public link/export/order/alias configurations exact.', flush=True)
        if args.only != 'clients':
            report['costs'] = costs(include, args.iie)
        if args.bench or args.only == 'clients':
            from verlet_clamp_clients import check_clients
            sources = budget_sources()
            report['games'] = check_clients(work, include)
            assert sources == budget_sources(), 'client source/asset changed during private builds'
            report['budget_sources'] = sources
            report['budget_runner'] = identity(DEV / 'tools/a2run/a2run')
            report['budget_environment'] = metadata(selected / 'verlet.inc', False)['environment']
            report['budget_flags'] = 'ca65 -t none -g; normal game linker layouts'
        report.update(metadata(selected / 'verlet.inc', args.iie))
        report['asm_source'] = identity(selected / 'verlet.asm')
        report['test_sha256'] = identity(__file__)['sha256']
        report['fixture_config_sha256'] = hashlib.sha256(CONFIG.encode()).hexdigest()
        del report['probe_config_sha256']
        report['test_dependencies'] = [identity(DEV / 'tests' / name) for name in (
            'test_verlet_contact_all.py', 'test_verlet_ground_probes.py',
            'test_verlet_integrate_all.py', 'verlet_clamp_clients.py')]
        report['support_sources'] = [identity(path) for path in (
            DEV / 'lib/math/math.inc', DEV / 'tools/verlet/harness.py',
            DEV / 'cc65/apple2_hgr.cfg')]
        if args.out:
            args.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
