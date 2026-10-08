#!/usr/bin/env python3
"""a2test.py — the shared harness of the headless emulator tests.

Every game and library test drives a2run (portable) or a2shot (POM2 core)
with the same script language and reads back the same `ADDR: bytes` dumps.
This module holds what they all re-implemented: the ld65 label file, the
peek/poke/until step builders, the emulator call, the dump decoder, the HGR
row layout and the one-file DOS 3.3 test disk.

    import sys; sys.path.insert(0, str(ROOT / 'dev/tools'))
    import a2test
    L = a2test.labels(GAME / 'build/game.lbl')
    r = a2test.run(disk, ['wait:1100', L.peek('score', 5), 'key: '])
    r.dumps[0]            # bytes of the first peek
    r.mem(0x2000, 8192)   # any dumped range, by address
"""
from pathlib import Path
import re
import subprocess
from hgr_tables import hgr_offset

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / 'dev'
A2RUN = DEV / 'tools/a2run/a2run'
A2SHOT = DEV / 'tools/a2shot/a2shot'
CPU_HZ = 1_020_484          # Apple II average clock (65 x 14.318 MHz / 14 ... )

_LABEL = re.compile(r'^al ([0-9A-Fa-f]+) \.(\w+)$', re.M)


class Labels(dict):
    """{name: address} from an ld65 -Ln file, plus the step builders."""

    def peek(self, name, length=1, offset=0):
        return f'peek:{self[name] + offset:04X}:{length}'

    def poke(self, name, value, offset=0):
        return f'poke:{self[name] + offset:04X}:{value & 0xFF:02X}'

    def until(self, name, limit=3000):
        return f'until:{self[name]:04X}:{limit}'


def labels(path, strip=False, prefix=''):
    """Read an ld65 label file. strip=True also registers C symbols without
    their leading underscore; prefix keeps only names starting with it."""
    out = Labels()
    for addr, name in _LABEL.findall(Path(path).read_text()):
        if not name.startswith(prefix):
            continue
        out[name] = int(addr, 16)
        if strip and name.startswith('_'):
            out[name[1:]] = out[name]
    return out


def escape(steps):
    """Raw control characters -> a2shot escapes (a2run accepts both)."""
    return [s.replace('\x1b', '\\e').replace('\r', '\\r').replace('\n', '\\n')
            if isinstance(s, str) else s for s in steps]


class Result:
    """The emulator's output, decoded."""

    def __init__(self, out):
        self.out = out
        self.rows = []            # (address, bytes) per dump line, in order
        for addr, values in re.findall(r'^([0-9A-Fa-f]{4}): ((?:[0-9A-Fa-f]{2} ?)+)$', out, re.M):
            self.rows.append((int(addr, 16), bytes.fromhex(values)))
        # consecutive lines form one dump
        self.dumps = []
        for addr, data in self.rows:
            if self.dumps and self.dumps[-1][0] + len(self.dumps[-1][1]) == addr:
                self.dumps[-1][1] += data
            else:
                self.dumps.append([addr, bytearray(data)])
        self.dumps = [bytes(d) for _, d in self.dumps]
        self.cycles = [int(c) for c in re.findall(r'cycles=(\d+)', out)]
        self.spk = [int(c) for c in re.findall(r'^spk (\d+)$', out, re.M)]

    @property
    def data(self):
        """Every dumped byte, in order (what most scripts slice)."""
        return b''.join(data for _, data in self.rows)

    def lines(self):
        """Dump lines as bytes objects (one per 16-byte output row)."""
        return [data for _, data in self.rows]

    def mem(self, address, length, occurrence=0):
        """The `length` bytes dumped from `address` (occurrence-th time)."""
        seen = 0
        for i, (addr, _) in enumerate(self.rows):
            if addr != address:
                continue
            if seen < occurrence:
                seen += 1
                continue
            out = bytearray()
            for a, data in self.rows[i:]:
                if a != address + len(out):
                    break
                out += data
                if len(out) >= length:
                    return bytes(out[:length])
            break
        raise AssertionError(f'missing dump at {address:04X}')

    def text_screens(self):
        """The 40x24 screens printed by a2run's `text` step."""
        return re.findall(r'(?:^\|.{40}\|\n){24}', self.out, re.M)


def run(disk, steps, emulator=None, iie=False, wp=False, timeout=120, check=True,
        pad_until=False, cwd=None):
    """Boot `disk` and play `steps`. emulator defaults to a2run (a2shot when
    iie). pad_until inserts `wait:1` before every until: (a2shot needs a
    frame between a key and the next breakpoint)."""
    emulator = Path(emulator or (A2SHOT if iie else A2RUN))
    args = [str(emulator)] + (['--iie'] if iie else []) + ['--disk', str(disk)]
    if wp:
        args.append('--wp')
    steps = [str(s) for s in steps]
    if emulator.name == 'a2shot':
        steps = escape(steps)
    if pad_until:
        steps = [s for step in steps for s in (['wait:1', step] if step.startswith('until:') else [step])]
    result = subprocess.run(args + steps, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    if check and result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return Result(result.stdout)


def hgr_visible(page):
    """The 192 x 40 displayed bytes of an 8 KB page dump, row by row."""
    return b''.join(page[hgr_offset(y):hgr_offset(y) + 40] for y in range(192))


def page_dump(block):
    """Join the [2345]xxx: lines of a 16 KB `peek:2000:16384` into bytes."""
    return bytes.fromhex(' '.join(re.findall(r'(?m)^[2345][0-9A-Fa-f]{3}: ([0-9A-Fa-f ]+)$', block)))


def build_disk(work, name, binary, load=0x6000, extra=()):
    """A bootable DOS 3.3 disk that BRUNs `binary` as NAME (test programs)."""
    work = Path(work)
    hello = work / 'hello.bas'
    hello.write_text(f'10 PRINT CHR$(4);"BRUN {name}"\n')
    disk = work / f'{name}.dsk'
    args = ['python3', str(DEV / 'tools/dos33.py'), '--master', str(DEV / 'tools/dos33_system.bin'),
            '--out', str(disk), '--bas', f'HELLO={hello}', '--bin', f'{name}={binary}@0x{load:04X}']
    for spec in extra:
        args += ['--bin', spec]
    subprocess.run(args, check=True, capture_output=True, text=True)
    return disk
