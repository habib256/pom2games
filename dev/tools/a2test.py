#!/usr/bin/env python3
"""a2test.py — the shared harness of the headless emulator tests.

Every game and library test drives a2run (portable) or a2shot (POM2 core)
with the same script language and reads back the same `ADDR: bytes` dumps.
This module holds what they all re-implemented: the ld65 label file, the
peek/poke/until step builders, the emulator call, the dump decoder, the HGR
row layout, the one-file DOS 3.3 test disk and in-process ProDOS volumes
(prodos_files / prodos_volume / prodos_variant, byte-identical to the
stage directory + build_volume.py subprocess they replace).

    import sys; sys.path.insert(0, str(ROOT / 'dev/tools'))
    import a2test
    L = a2test.labels(GAME / 'build/game.lbl')
    r = a2test.run(disk, ['wait:1100', L.peek('score', 5), 'key: '])
    r.dumps[0]            # bytes of the first peek
    r.mem(0x2000, 8192)   # any dumped range, by address
    a2test.prodos_files(disk)['HIGHSCORES']      # (type, aux, bytes)
    a2test.prodos_variant(disk, tmp / 'save.po', replace={'RSS.SAVE#060000': data})
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
        # E-Z Color (a2run --ezcolor): "VADDR: XX ..." VRAM dumps (the last
        # one wins per byte), "vregs ..." lines and the fast-access total.
        self.vram = bytearray(0x4000)
        self.vram_seen = bytearray(0x4000)
        self.vregs = None           # [R0..R7] of the last vregs step
        self.vstatus = None
        self.vdp_fast = None        # vdp_fast_writes=N printed at the end
        # a2shot --ezcolor (POM2's TMS9918, silicon-strict): accesses the
        # chip dropped (vdp_dropped=N at the end; dropped= in each vregs
        # line, the last one in vregs_dropped) and /INT (virq).
        self.vdp_dropped = None
        self.vregs_dropped = None
        self.virq = None
        rest = []
        for line in other:
            if len(line) > 7 and line[0] == 'V' and line[5] == ':':
                try:
                    addr, data = int(line[1:5], 16), bytes.fromhex(line[7:])
                except ValueError:
                    rest.append(line)
                    continue
                for k, v in enumerate(data):
                    self.vram[(addr + k) & 0x3FFF] = v
                    self.vram_seen[(addr + k) & 0x3FFF] = 1
            elif line.startswith('vregs '):
                f = line.split()
                self.vregs = [int(x, 16) for x in f[1:9]]
                self.vstatus = int(f[9].split('=')[1], 16)
                kv = dict(x.split('=', 1) for x in f[10:] if '=' in x)
                if 'dropped' in kv:
                    self.vregs_dropped = int(kv['dropped'])
                if 'irq' in kv:
                    self.virq = int(kv['irq'])
                rest.append(line)
            elif line.startswith('vdp_fast_writes='):
                self.vdp_fast = int(line.split('=')[1])
            elif line.startswith('vdp_dropped='):
                self.vdp_dropped = int(line.split('=')[1])
            else:
                rest.append(line)
        other = rest
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

    def vmem(self, address, length):
        """`length` VRAM bytes from a vpeek dump (all must have been dumped)."""
        sl = [(address + k) & 0x3FFF for k in range(length)]
        if not all(self.vram_seen[a] for a in sl):
            raise AssertionError(f'missing VRAM dump at {address:04X}')
        return bytes(self.vram[a] for a in sl)

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
        pad_until=False, cwd=None, pal=False, mockingboard=False, ezcolor=None,
        ezcolor_lax=False):
    """Boot `disk` and play `steps`. emulator defaults to a2run (a2shot when
    iie). disk=None (a2run): no boot card, the machine waits at the Applesoft
    prompt after 8 frames; start test code with bin_steps(). pad_until inserts `wait:1` before every until: (a2shot needs a
    frame between a key and the next breakpoint). pal: 50 Hz video, mockingboard:
    a card in slot 4 (a2shot), ezcolor: slot of an E-Z Color TMS9918A card
    (a2run --ezcolor=N; read back with vpeek:/vregs, see vdp_shot). With
    emulator=A2SHOT the card is POM2's (silicon-strict access window: count
    in Result.vdp_dropped; vshot:FILE.png renders its monitor); ezcolor_lax
    (a2shot only) turns that window off."""
    emulator = Path(emulator or (A2SHOT if iie else A2RUN))
    args = [str(emulator)] + (['--iie'] if iie else []) + (['--pal'] if pal else []) \
        + (['--mockingboard'] if mockingboard else []) \
        + ([f'--ezcolor={ezcolor}'] if ezcolor else []) + (['--ezcolor-lax'] if ezcolor_lax else []) \
        + (['--disk', str(disk)] if disk else [])
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

    def __init__(self, disk, cwd=None, timeout=120, iie=False, ezcolor=None):
        self.timeout = timeout
        self.stderr = tempfile.TemporaryFile(mode='w+t')
        try:
            self.process = subprocess.Popen([str(A2SHOT)] + (['--iie'] if iie else [])
                                            + ([f'--ezcolor={ezcolor}'] if ezcolor else [])
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


VDP_SHOT_STEPS = ['vpeek:0:16384', 'vregs']     # what vdp_shot() needs


def vdp_shot(result, path, scale=2, border=False):
    """Render the E-Z Color picture of a run that ended its steps with
    VDP_SHOT_STEPS (whole VRAM + registers) to a PNG (dev/tools/tms9918.py).
    Returns the RGB rows."""
    import tms9918
    if result.vregs is None or not all(result.vram_seen):
        raise AssertionError('vdp_shot needs vpeek:0:16384 and vregs')
    rows = tms9918.render(result.vram, result.vregs, border)
    import apple2img
    apple2img.png_write(Path(path), rows, scale=scale)
    return rows


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


# ---------------------------------------------------------------- ProDOS volumes
# In-process stand-ins for the stage directory + build_volume.py subprocess
# that the ProDOS game tests rebuilt by hand: same allocator, same entries,
# same fixed date, so the images are byte-identical to the subprocess ones.
PRODOS_TOOLS = DEV / 'tools/prodos'
PRODOS_DATE = '2026-09-07T12:00'      # build_volume.py --date default


def _prodos_module(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(f'_a2test_{name}', PRODOS_TOOLS / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prodos_image(disk):
    reader = _prodos_module('read_volume')
    data = disk if isinstance(disk, (bytes, bytearray)) else Path(disk).read_bytes()
    return reader.Image(bytes(data))


def prodos_files(disk):
    """{name: (type, aux, bytes)} of the root directory of a ProDOS image
    (path or bytes), in catalogue order. A subdirectory maps to
    (0x0F, 0, None)."""
    image = _prodos_image(disk)
    out = {}
    for e in image.entries(2):
        name = e[1:1 + (e[0] & 15)].decode('ascii')
        if e[0] >> 4 == 0xD:
            out[name] = (0x0F, 0, None)
        else:
            out[name] = (e[0x10], int.from_bytes(e[0x1F:0x21], 'little'), image.read(e))
    return out


def _prodos_write(out, items, volume, blocks, boot, date):
    """Flat root directory, `items` [(name, type, aux, bytes)] in this order,
    written with build_volume.Volume exactly as its write_dir does."""
    bv = _prodos_module('build_volume')

    class Flat(bv.Volume):
        def write_dir(self, entries, dir_blocks, header_entry):
            for i, b in enumerate(dir_blocks):
                blk = self.block(b)
                blk[0:2] = (dir_blocks[i - 1] if i else 0).to_bytes(2, 'little')
                blk[2:4] = (dir_blocks[i + 1] if i + 1 < len(dir_blocks) else 0).to_bytes(2, 'little')
            self.block(dir_blocks[0])[4:4 + bv.ENTRY_LEN] = header_entry
            slots = [(b, k) for i, b in enumerate(dir_blocks)
                     for k in range(bv.ENTRIES_PER_BLOCK) if i or k]
            if len(entries) > len(slots):
                raise ValueError(f'{len(entries)} files for {len(slots)} root entries')
            for (blk_no, k), (name, ftype, aux, data) in zip(slots, entries):
                storage, key, used = self.write_file(data)
                e = self.entry(storage, name, ftype, key, used, len(data), aux, dir_blocks[0])
                self.block(blk_no)[4 + k * bv.ENTRY_LEN:4 + (k + 1) * bv.ENTRY_LEN] = e
            return len(entries)

    names = [i[0] for i in items]
    if len(set(names)) != len(names):
        raise ValueError(f'duplicate ProDOS names in {names}')
    boot = bytes(boot)[:1024].ljust(1024, b'\0') if boot else b''
    vol = Flat(volume, blocks, boot, bv.prodos_date(date))
    vol.build(items)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(bytes(vol.image))
    return Path(out)


def _prodos_item(host, value, known=None):
    """('NAME#TTAAAA' or 'NAME', bytes or (type, aux, bytes)) -> (name, type, aux, bytes).
    A bare NAME keeps the type/aux of `known` (an existing file) if any."""
    bv = _prodos_module('build_volume')
    if isinstance(value, tuple):
        ftype, aux, data = value
        return host.upper(), ftype, aux, bytes(data)
    name, ftype, aux = bv.prodos_name(host)
    if '#' not in host and known is not None:
        ftype, aux = known[0], known[1]
    return name, ftype, aux, bytes(value)


def prodos_volume(out, files, volume, blocks=280, boot=True, date=PRODOS_DATE):
    """Build a ProDOS image in-process, as build_volume.py does from a stage
    directory holding `files` {host name: bytes} (host names as in a stage:
    'NAME#TTAAAA', or NAME.SYS/.BIN/... ; a value may also be (type, aux,
    bytes)). Entries follow build_volume's order (host names, case folded),
    so the image is byte-identical to the subprocess build. boot: True =
    dev/tools/prodos/boot.bin, False = none, or the boot bytes."""
    if boot is True:
        boot = (PRODOS_TOOLS / 'boot.bin').read_bytes()
    items = [_prodos_item(host, files[host]) for host in sorted(files, key=str.upper)]
    return _prodos_write(out, items, volume, blocks, boot, date)


def prodos_variant(disk, out, replace=None, drop=(), volume=None, blocks=None, date=PRODOS_DATE):
    """Rebuild a flat ProDOS image with some files replaced, added or dropped.

    replace {host name: bytes or (type, aux, bytes)}: 'RSS.SAVE#060000'
    sets the type/aux, a bare existing 'NAME' keeps them. drop: names to
    remove. volume / blocks default to the source's; the boot blocks are
    the source's. Kept files stay in catalogue order; a new file goes to
    its alphabetical place if the source catalogue is alphabetical (what a
    build_volume.py stage gives, hence a byte-identical image), else last."""
    src = prodos_files(disk)
    if any(v[2] is None for k, v in src.items() if k not in drop):
        raise ValueError('prodos_variant: subdirectories are not supported')
    image = _prodos_image(disk)
    header = image.header()
    items = [(name, t, a, d) for name, (t, a, d) in src.items() if name not in drop]
    alphabetical = [i[0] for i in items] == sorted(i[0] for i in items)
    for host, value in (replace or {}).items():
        bare = host.upper() if isinstance(value, tuple) else \
            _prodos_module('build_volume').prodos_name(host)[0]
        item = _prodos_item(host, value, src.get(bare))
        at = next((k for k, i in enumerate(items) if i[0] == item[0]), None)
        if at is not None:
            items[at] = item
        elif alphabetical:
            items.insert(sum(1 for i in items if i[0] < item[0]), item)
        else:
            items.append(item)
    return _prodos_write(out, items, volume or header['name'], blocks or header['blocks'],
                         image.d[:1024], date)
