#!/usr/bin/env python3
"""Keyboard ASM: byte/flag model, ordered strobe bus and real repeated keys.

All 16 C/I/V/D input combinations run on NMOS/65C02. The RAM-port model
checks full P; the hardware checks exclude only V, which BIT obtains from
an otherwise unspecified keyboard-strobe read value.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from test_hgr import DEV, run, a2test

KINDS = {
    'wait': ('wait_key',), 'poll': ('poll_key',),
    'both': ('wait_key', 'poll_key'), 'upper': ('kbd_upcase',), 'unused': (),
    'renamed': ('keyboard_wait', 'keyboard_poll'),
    'rename_wait': ('keyboard_wait',), 'rename_poll': ('keyboard_poll',),
}
KEYS = [('a',65), ('z',90), ('A',65), ('Z',90), ('0',48), ('~',126),
        (r'\e',27), (r'\r',13), (r'\<',8), (r'\>',21), (r'\^',11), (r'\v',10)]


def build(work, kernel, kind, ports=(0x9000,0x9001), prepare=False, idle=False):
    source = work / (kind + '.s')
    text = f'KBD=${ports[0]:04X}\nKBDSTRB=${ports[1]:04X}\n.code\n'
    text += 'idle:jmp idle\n' if idle else 'nop\n'
    if KINDS[kind]:
        text += '.addr ' + ','.join(KINDS[kind]) + '\n'
    if kind.startswith('rename'):
        text += '.define wait_key keyboard_wait\n.define poll_key keyboard_poll\n'
    text += kernel.read_text()
    if prepare:
        for flags in range(16):
            text += (f'\nprepare{flags}:' + ('sed\n' if flags & 8 else 'cld\n') +
                     ('sei\n' if flags & 2 else 'cli\n') + 'clv\n' +
                     ('bit $9002\n' if flags & 4 else '') +
                     ('sec\n' if flags & 1 else 'clc\n') + 'rts\n')
    source.write_text(text)
    obj, binary, labels = (source.with_suffix(suffix) for suffix in ('.o','.bin','.lbl'))
    config = work / 'test.cfg'
    config.write_text('MEMORY{RAM:start=$6000,size=$3000,type=rw,file=%O;}'
                      'SEGMENTS{CODE:load=RAM,type=ro;}')
    run(['ca65','--cpu','6502','-g','-o',obj,source])
    run(['ld65','-C',config,'-Ln',labels,'-o',binary,obj])
    return binary, a2test.labels(labels)


def model(work, kernel):
    results = {}
    disk = work / 'empty.dsk'; disk.write_bytes(bytes(143360))
    for kind in ('wait','poll','both','upper'):
        binary, labels = build(work,kernel,kind,prepare=True)
        functions = list(KINDS[kind])
        if kind == 'both': functions.append('kbd_upcase')
        for iie in (False,True):
            for flags in range(16):
                steps = [f'load:{binary}@6000', *a2test.pokes(0,bytes([0xA5])*256),
                         'poke:9001:40','poke:9002:40','hwstackwatch']
                cases = []
                for fn in functions:
                    for value in range(128 if fn == 'wait_key' else 256):
                        byte = value | 128 if fn == 'wait_key' else value
                        steps += [f'call:{labels["prepare"+str(flags)]:04X}:2',
                                  f'poke:9000:{byte:02X}',f'regs:{value:02X}:5A:A5',
                                  f'call:{labels[fn]:04X}:2']
                        cases.append((fn,byte))
                steps += ['peek:0000:256','hwstack']
                result = a2test.run(disk,steps,iie=iie)
                rows = re.findall(r'call ([0-9A-F]+) cycles=\d+ elapsed=(\d+) A=([0-9A-F]+) X=([0-9A-F]+) Y=([0-9A-F]+) P=([0-9A-F]+)',result.out)
                rows = [row for row in rows if int(row[0],16) != labels['prepare'+str(flags)]]
                assert len(rows) == len(cases) and result.data == bytes([0xA5])*256
                peak,available,overflow = map(int,re.search(r'hwstack peak=(\d+) available=(\d+) overflow=(\d+)',result.out).groups())
                assert not overflow and peak < available
                for (fn,value), row in zip(cases,rows):
                    _,cycles,a,x,y,p = row
                    a,x,y,p = (int(v,16) for v in (a,x,y,p))
                    pending = fn != 'kbd_upcase' and value >= 128
                    char = value if fn == 'kbd_upcase' else value & 127 if pending else 0
                    expected = char-32 if 97 <= char <= 122 else char
                    carry = 1 if pending or fn == 'kbd_upcase' else flags & 1
                    overflow = 64 if pending or flags & 4 else 0
                    expected_p = (32 + (8 if flags & 8 else 0) + (4 if flags & 2 else 0) +
                                  overflow + carry + (expected & 128) + (2 if expected == 0 else 0))
                    assert (a,x,y,p) == (expected,0x5A,0xA5,expected_p), (kind,iie,flags,fn,value,a,p,expected,expected_p)
                    name = f'{kind}_{"iie" if iie else "nmos"}_{flags:02x}_{fn}_{value:02x}'
                    results[name] = dict(cycles=int(cycles),binary_bytes=binary.stat().st_size,
                                         hardware_stack_peak_bytes=peak)
        print(f'Keyboard {kind}: both CPUs, all bytes and 16 C/I/V/D states, full A/X/Y/P, ZP/stack OK.')
    return results


def bus(work, kernel):
    host = work / 'bus'
    run(['cc','-std=c99','-O2','-I',DEV/'tools/a2run',DEV/'tests/kbd_bus.c',
         DEV/'tools/a2run/cpu6502.c','-o',host])
    artifacts = {}
    for kind in KINDS:
        binary,labels = build(work,kernel,kind,ports=(0xC000,0xC010))
        names = (('keyboard_wait','keyboard_poll','kbd_upcase') if kind.startswith('rename') else
                 ('wait_key','poll_key','kbd_upcase'))
        args = [f'{labels[fn]:04X}' if fn in labels else '0' for fn in names]
        message = run([host,binary,*args]).strip()
        count = int(re.match(r'(\d+) bus cases:',message).group(1))
        artifacts[kind] = dict(binary_bytes=binary.stat().st_size,
                               sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),cases=count)
    assert artifacts['unused']['binary_bytes'] == 1
    for alias,original in (('renamed','both'),('rename_wait','wait'),('rename_poll','poll')):
        assert artifacts[alias] == artifacts[original], (alias,'renaming changed generated code')
    print(f'Keyboard bus: {sum(v["cases"] for v in artifacts.values())} cases; exact read/strobe order, '
          'delayed wait, consumed key, full flags, ZP/stack, renamed/unused entries OK.')
    return artifacts


def hardware(work, kernel):
    observations = {}
    disk = work / 'empty.dsk'; disk.write_bytes(bytes(143360))
    for kind in ('both','renamed'):
        binary,labels = build(work,kernel,kind,ports=(0xC000,0xC010),prepare=True,idle=True)
        poll = 'keyboard_poll' if kind == 'renamed' else 'poll_key'
        wait = 'keyboard_wait' if kind == 'renamed' else 'wait_key'
        for iie in (False,True):
            steps = [f'load:{binary}@6000',f'go:{labels["idle"]:04X}',
                     f'call:{labels["prepare2"]:04X}:2','regs:77:5A:A5',f'call:{labels[poll]:04X}:2']
            expected = [(0,0)]
            for fn in (poll,wait,poll,wait):
                for token,value in KEYS:
                    steps += ['press:'+token]
                    if fn == poll: steps += ['wait:2']
                    steps += [f'call:{labels["prepare2"]:04X}:2','regs:77:5A:A5',
                              f'call:{labels[fn]:04X}:3',f'call:{labels[poll]:04X}:2']
                    expected += [(value,1),(0,1)]
            result = a2test.run(disk,steps,iie=iie)
            rows = re.findall(r'call ([0-9A-F]+) cycles=\d+ elapsed=\d+ A=([0-9A-F]+) X=([0-9A-F]+) Y=([0-9A-F]+) P=([0-9A-F]+)',result.out)
            rows = [row for row in rows if int(row[0],16) != labels['prepare2']]
            assert len(rows) == len(expected)
            observed = []
            for index,(row,(value,carry)) in enumerate(zip(rows,expected)):
                _,a,x,y,p = row; a,x,y,p = (int(v,16) for v in (a,x,y,p))
                expected_p = 32 + 4 + carry + (2 if value == 0 else 0)
                assert (a,x,y,p & ~64) == (value,0x5A,0xA5,expected_p), (kind,iie,index,a,x,y,p,value)
                observed.append((a,x,y,p & ~64))
            observations[kind+('_iie' if iie else '_nmos')] = observed
    print('Keyboard real II+/IIe: ordinary/renamed entries, 48 repeated keys each, '
          'delayed wait and immediate empty re-poll, X/Y/N/Z/C/I/D preserved.')
    return observations


def report(kernel, results, artifacts, observations):
    sys.path.insert(0,str(DEV/'bench'))
    import run as bench
    version = subprocess.run(['cl65','--version'],capture_output=True,text=True,check=True)
    host = subprocess.run(['cc','--version'],capture_output=True,text=True,check=True)
    digest = lambda path: dict(name=Path(path).name,sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
    return dict(schema=1,scope='direct calls on RAM key/strobe ports, excluding injected JSR overhead',
                source=digest(kernel),test_source=digest(__file__),
                support_sources=[digest(DEV/'tests/kbd_bus.c'),digest(DEV/'tools/a2run/cpu6502.h')],
                compiler=(version.stdout+version.stderr).strip(),flags='ca65 --cpu 6502 -g; ld65 $6000',
                host_compiler=host.stdout.strip(),host_flags='-std=c99 -O2',
                environments={name:bench.environment(name=='iie') for name in ('nmos','iie')},
                case_environments={name:'iie' if '_iie_' in name else 'nmos' for name in results},
                initial_flags=dict(C=[0,1],I=[0,1],V=[0,1],D=[0,1]),
                results=results,bus=artifacts,hardware=observations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,help='assemble this kbd.asm instead')
    parser.add_argument('--bench',action='store_true',help='report direct-call timings and code size')
    parser.add_argument('--out',type=Path,help='write measurements (requires --bench)')
    args = parser.parse_args()
    if args.out and not args.bench: parser.error('--out requires --bench')
    kernel = (args.reference or DEV/'lib/apple2/kbd.asm').resolve()
    with tempfile.TemporaryDirectory(prefix='kbd-test-') as directory:
        work = Path(directory)
        results = model(work,kernel)
        artifacts = bus(work,kernel)
        observations = hardware(work,kernel)
    if args.bench:
        measurement = report(kernel,results,artifacts,observations)
        print(f'{len(results)} direct-call measurements; both CPUs and all 16 flag states.')
        if args.out: args.out.write_text(json.dumps(measurement,indent=2)+'\n')


if __name__ == '__main__': main()
