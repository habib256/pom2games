#!/usr/bin/env python3
"""DHGR state ABI, optional RAM groups and explicit source-family clients.

Compile public dhgr_internal.h references individually and together. Check the
initial values and unique volatile writes/readback on NMOS/65C02; a tail guard
also catches undersized storage. All mutable symbols remain independently
addressable. No scalar address or ordering is assumed. --reference replaces
only state definitions with the named revision for exact footprint comparison.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import test_hgr
from test_hgr import DEV, ROOT, a2test

GUARD_SIZE = 16
STATE_FILES = ('dhgr_state.c', 'dhgr_transfer_params.c', 'dhgr_address_state.s',
               'dhgr_pattern_state.s', 'dhgr_span_state.s', 'dhgr_legacy_params.s',
               'dhgr_sprite_mask_state.s')
FIELDS = {
    'dhgr_addr': (2, 0, 'address'), 'dhgr_aux': (1, 0, 'address'),
    'dhgr_mask': (1, 0, 'legacy'), 'dhgr_bits': (1, 0, 'legacy'),
    'dhgr_base': (1, 0x20, 'mode'), 'dhgr_display': (1, 0, 'mode'),
    'dhgr_pattern': (4, 0, 'pattern'), 'dhgr_first': (1, 0, 'span'),
    'dhgr_last': (1, 0, 'span'), 'dhgr_first_mask': (1, 0, 'span'),
    'dhgr_last_mask': (1, 0, 'span'), 'dhgr_buffer': (2, 0, 'transfer'),
    'dhgr_count': (1, 0, 'transfer'), 'dhgr_sprite_mask': (2, 0, 'masked'),
}
GROUPS = {
    'mode': (1, 'dhgr_state.o'), 'address': (3, 'dhgr_address_state.o'),
    'legacy': (2, 'dhgr_legacy_params.o'), 'pattern': (4, 'dhgr_pattern_state.o'),
    'span': (4, 'dhgr_span_state.o'), 'transfer': (3, 'dhgr_transfer_params.o'),
    'masked': (2, 'dhgr_sprite_mask_state.o'),
}
CASES = {field: (field,) for field in FIELDS}
CASES.update(all=tuple(FIELDS), mode=('dhgr_base', 'dhgr_display'),
             transfer=('dhgr_addr', 'dhgr_aux', 'dhgr_buffer', 'dhgr_count'),
             masked=('dhgr_addr', 'dhgr_aux', 'dhgr_buffer', 'dhgr_count', 'dhgr_sprite_mask'),
             span=('dhgr_base', 'dhgr_pattern', 'dhgr_first', 'dhgr_last',
                   'dhgr_first_mask', 'dhgr_last_mask'))


def segments(path):
    import re
    text = Path(path).read_text().split('Segment list:')[1].split('Exports list')[0]
    return {name: int(size, 16) for name, size in re.findall(
        r'(?m)^(\w+)\s+[0-9A-F]+\s+[0-9A-F]+\s+([0-9A-F]+)', text)}


@contextmanager
def historical_state(work, reference):
    if not reference:
        yield
        return
    files = {}
    for name in STATE_FILES:
        result = subprocess.run(['git', 'show', reference + ':dev/lib/hgrc/' + name],
                                cwd=ROOT, capture_output=True, check=False)
        if result.returncode:
            assert name not in STATE_FILES[:2], result.stderr.decode()
            continue
        path = work / name
        path.write_bytes(result.stdout)
        files[name] = path
    original_run, original_compile = test_hgr.run, test_hgr.compile_source

    def command(args, **kwargs):
        result = original_run(args, **kwargs)
        if str(args[0]) == 'make' and str(args[-1]) == 'print':
            result = ' '.join(member for member in result.split()
                              if Path(member).name not in STATE_FILES
                              or Path(member).name in files) + '\n'
        return result

    def compile_member(source, obj, flags):
        return original_compile(files.get(Path(source).name, source), obj, flags)

    test_hgr.run, test_hgr.compile_source = command, compile_member
    try:
        yield
    finally:
        test_hgr.run, test_hgr.compile_source = original_run, original_compile


def client_source(fields):
    initial, writes, final = [], [], []
    offset = 0
    for field, (size, default, _) in FIELDS.items():
        values = tuple(range(0x31 + offset, 0x31 + offset + size))
        offset += size
        if field not in fields:
            continue
        initial.append(f'if(sizeof({field})-{size})result=0;')
        for index, value in enumerate(values):
            byte = f'((volatile unsigned char*)&{field})[{index}]'
            initial.append(f'if({byte}!={(default >> (index*8)) & 255})result=0;')
            writes.append(f'{byte}={value};')
            final.append(f'if({byte}!={value})result=0;')
    guard_set = ''.join(f'guard[{index}]={0xD0+index};' for index in range(GUARD_SIZE))
    guard_check = ''.join(f'if(guard[{index}]!={0xD0+index})result=0;'
                          for index in range(GUARD_SIZE))
    return ('#include "dhgr_internal.h"\n#define result (*(volatile unsigned char*)0x1000)\n'
            'void done(void);extern volatile unsigned char guard[16];\n'
            + '\nint main(void){result=1;' + guard_set
            + ''.join(initial + writes + final) + guard_check
            + 'done();for(;;){}return 0;}\n')


def compile_client(work, name, fields):
    source, obj = work / (name + '.c'), work / (name + '.o')
    source.write_text(client_source(fields))
    test_hgr.compile_source(source, obj, ['-t', 'none', '-Oirs', '-I', DEV / 'lib/hgrc'])
    return obj


def link_client(work, name, obj, inputs):
    binary, mapfile, labels = (work / (name + suffix) for suffix in ('.bin', '.map', '.lbl'))
    # The guard object follows all state objects/archive members in BSS.
    test_hgr.run(['cl65', '-t', 'none', '-C', DEV / 'cc65/apple2_hgr_c.cfg',
                  '-o', binary, '-m', mapfile, '-Ln', labels, work / 'crt0_apple2.o',
                  obj, *inputs, work / 'guard.o'])
    points = a2test.labels(labels)
    assert points['_guard'] + GUARD_SIZE == points['__BSS_RUN__'] + points['__BSS_SIZE__'], name
    return binary, mapfile, points


def check_client(work, name, fields, inputs, limits=True, cpus=(False, True), expect=1):
    obj = compile_client(work, name, fields)
    binary, mapfile, points = link_client(work, name, obj, inputs)
    disk = a2test.build_disk(work, 'STATE', binary)
    for iie in cpus:
        result = a2test.run(disk, [points.until('_done'), 'peek:1000:1'], iie=iie)
        assert result.dumps == [bytes((expect,))], (name, iie, result.out[-1000:])
    sizes = segments(mapfile)
    groups = {FIELDS[field][2] for field in fields}
    if limits:
        assert sizes.get('BSS', 0) <= GUARD_SIZE + sum(GROUPS[group][0] for group in groups), name
        linked = mapfile.read_text().split('Segment list:')[0]
        for group, (_, member) in GROUPS.items():
            if group not in groups:
                assert member not in linked, (name, 'unused state member', member)
    return dict(sizes, binary_bytes=binary.stat().st_size, fields=fields)


def explicit_families(work):
    results = {}
    for transfer in (False, True):
        name = 'family_transfer' if transfer else 'family_state'
        mk = work / (name + '.mk')
        mk.write_text(f'HGRC:={DEV}/lib/hgrc\nGFX:={DEV}/lib/gfx\ninclude $(HGRC)/hgrc.mk\n'
                      'print:\n\t@echo $(HGRC_DHGR_STATE_SRCS)'
                      + (' $(HGRC_DHGR_TRANSFER_SRCS)' if transfer else '') + '\n')
        sources = test_hgr.run(['make', '-s', '-f', mk, 'print']).split()
        objects = []
        for index, source in enumerate(map(Path, sources)):
            obj = work / (name + '_' + str(index) + '_' + source.stem + '.o')
            test_hgr.compile_source(source, obj, ['-t', 'none', '-Oirs', '-I', DEV / 'lib/hgrc',
                                                  '--asm-include-dir', DEV / 'lib/apple2'])
            objects.append(obj)
        fields = tuple(FIELDS) if transfer else tuple(
            field for field, (_, _, group) in FIELDS.items() if group not in ('transfer', 'masked'))
        results[name] = check_client(work, name, fields, objects, limits=False)
    return results


def negative_controls(work):
    mutations = (
        ('base_initial', 'dhgr_state.c', '= 0x20', '= 0x00'),
        ('legacy_alias', 'dhgr_legacy_params.s', '_dhgr_bits: .res 1', '_dhgr_bits = _dhgr_mask'),
        ('short_pointer', 'dhgr_sprite_mask_state.s', '_dhgr_sprite_mask: .res 2',
         '_dhgr_sprite_mask: .res 1'),
    )
    for name, member, old, new in mutations:
        target = work / name
        target.mkdir()
        source = target / member
        text = (DEV / 'lib/hgrc' / member).read_text()
        assert old in text, name
        source.write_text(text.replace(old, new, 1))
        obj = source.with_suffix('.o')
        test_hgr.compile_source(source, obj, ['-t', 'none', '-Oirs', '-I', DEV / 'lib/hgrc'])
        archive = target / 'mutant.lib'
        archive.write_bytes((work / 'hgrc.lib').read_bytes())
        test_hgr.run(['ar65', 'a', archive, obj])
        check_client(work, 'negative_' + name, tuple(FIELDS), [archive],
                     limits=False, cpus=(False,), expect=0)
        print('DHGR state negative control:', name, 'rejected', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', help='historical state definitions for footprint comparison')
    parser.add_argument('--negative', action='store_true', help='prove init/alias/allocation faults fail')
    parser.add_argument('--out', type=Path, help='write exact source identities and measurements')
    args = parser.parse_args()
    report = dict(reference=args.reference, results={})
    with tempfile.TemporaryDirectory(prefix='dhgr-state-') as directory:
        parent = Path(directory)
        variants = [('before', args.reference), ('after', None)] if args.reference else [('after', None)]
        for name, reference in variants:
            work = parent / name
            work.mkdir()
            with historical_state(work, reference):
                empty = work / 'empty.c'
                empty.write_text('int main(void){return 0;}\n')
                test_hgr.build(work, empty)
                guard = work / 'guard.s'
                guard.write_text('.export _done,_guard\n.code\n_done:rts\n.bss\n_guard:.res 16\n')
                test_hgr.compile_source(guard, work / 'guard.o', ['-t', 'none'])
                measurements = {
                    case: check_client(work, case, fields, [work / 'hgrc.lib'], limits=not reference)
                    for case, fields in CASES.items()
                }
                measurements.update(explicit_families(work))
                report['results'][name] = measurements
                print(f'DHGR state {name}: 19 header clients +2 explicit source families x2 CPUs; '
                      'defaults, sizes, unique byte writes, tail guards and optional RAM groups PASS',
                      flush=True)
                if name == 'after' and args.negative:
                    negative_controls(work)
    paths = [DEV / 'lib/hgrc' / name for name in STATE_FILES]
    paths += [DEV / 'lib/hgrc/dhgr_internal.h', DEV / 'lib/hgrc/hgrc.mk', Path(__file__).resolve()]
    report['source_identities'] = [dict(path=str(path.relative_to(ROOT)),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths]
    if args.out:
        args.out.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
