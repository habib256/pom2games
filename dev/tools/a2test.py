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
import queue
import threading
import tempfile
import time
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
        self.dumps = []           # consecutive lines form one dump
        # "ADDR: XX XX ..." lines picked without a regex (a multiline one cost
        # ~1 s per 64 page dumps); the other lines alone go to the regexes.
        other = []
        dump, end = None, -1
        for line in out.split('\n'):
            if len(line) > 7 and line[4] == ':' and line[5] == ' ' and line[:4].isalnum():
                try:
                    addr, data = int(line[:4], 16), bytes.fromhex(line[6:])
                except ValueError:
                    other.append(line)
                    continue
                self.rows.append((addr, data))
                if addr != end:
                    dump = bytearray()
                    self.dumps.append(dump)
                dump += data
                end = addr + len(data)
            else:
                other.append(line)
        self.dumps = [bytes(d) for d in self.dumps]
        other = '\n'.join(other)
        self.cycles = [int(c) for c in re.findall(r'cycles=(\d+)', other)]
        self.spk = [int(c) for c in re.findall(r'^spk (\d+)$', other, re.M)]

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


def have_a2shot(what=None):
    """True when a2shot is built. It links a POM2 core vendored for macOS
    arm64 and Linux x86_64 only, so on other hosts the //e parts of a test
    are skipped: give `what` to print the SKIP line."""
    if A2SHOT.exists():
        return True
    if what:
        print(f'SKIP {what}: needs a2shot (macOS arm64 or Linux x86_64: make -C dev/tools/a2shot)')
    return False


def run(disk, steps, emulator=None, iie=False, wp=False, timeout=120, check=True,
        pad_until=False, cwd=None, pal=False, mockingboard=False):
    """Boot `disk` and play `steps`. emulator defaults to a2run (a2shot when
    iie). disk=None (a2run): no boot card, the machine waits at the Applesoft
    prompt after 8 frames; start test code with bin_steps(). pad_until inserts `wait:1` before every until: (a2shot needs a
    frame between a key and the next breakpoint). pal: 50 Hz video, mockingboard:
    a card in slot 4 (a2shot)."""
    emulator = Path(emulator or (A2SHOT if iie else A2RUN))
    args = [str(emulator)] + (['--iie'] if iie else []) + (['--pal'] if pal else []) \
        + (['--mockingboard'] if mockingboard else []) + (['--disk', str(disk)] if disk else [])
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


class Session:
    """Live a2shot driver: inspect a reply before supplying the next step.

    Same script language as run(), private disks and deterministic guest
    execution. iie=True boots an enhanced //e (128 KB, ProDOS volumes). Use as a context manager; failed steps and timeouts raise.
    """

    def __init__(self, disk, cwd=None, timeout=120, iie=False):
        self.timeout = timeout
        self.stderr = tempfile.TemporaryFile(mode='w+t')
        try:
            self.process = subprocess.Popen([str(A2SHOT)] + (['--iie'] if iie else [])
                                            + ['--disk', str(disk), '--stdin'],
                                            cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=self.stderr, text=True, bufsize=1)
        except Exception:
            self.stderr.close()
            raise
        self.replies = queue.Queue()
        self.out = ''

        def read():
            for line in self.process.stdout:
                self.replies.put(line)
            self.replies.put(None)

        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()

    def step(self, step):
        step = escape([step])[0]
        if '\n' in step:
            raise ValueError('a session step must occupy one line')
        self.process.stdin.write(step + '\n')
        self.process.stdin.flush()
        lines = []
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                line = self.replies.get(timeout=max(0, deadline-time.monotonic()))
            except queue.Empty:
                self.process.kill()
                self.process.wait()
                self.out += ''.join(lines)
                raise TimeoutError(f'a2shot timed out: {step}') from None
            if line is None:
                code = self.process.wait()
                self.stderr.seek(0)
                self.out += ''.join(lines)
                raise RuntimeError(f'a2shot exit {code}: {step}\n' + ''.join(lines)
                                   + self.stderr.read())
            if line == 'a2shot:done\n':
                reply = ''.join(lines)
                self.out += reply
                return Result(reply)
            lines.append(line)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.process.poll() is None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.reader.join(timeout=5)
        if not self.process.stdin.closed:
            self.process.stdin.close()
        self.process.stdout.close()
        self.stderr.close()


def hgr_visible(page):
    """The 192 x 40 displayed bytes of an 8 KB page dump, row by row."""
    return b''.join(page[hgr_offset(y):hgr_offset(y) + 40] for y in range(192))


def page_dump(block):
    """Join the [2345]xxx: lines of a 16 KB `peek:2000:16384` into bytes."""
    return bytes.fromhex(' '.join(re.findall(r'(?m)^[2345][0-9A-Fa-f]{3}: ([0-9A-Fa-f ]+)$', block)))


def bin_steps(binary, load=0x6000, start=None):
    """a2run steps that put `binary` in RAM at `load` and jump to `start`
    (default: `load`), the diskless stand-in for build_disk() + BRUN."""
    return [f'load:{binary}@{load:04X}', f'go:{load if start is None else start:04X}']


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
