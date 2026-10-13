#!/usr/bin/env python3
"""src/hof.s and src/hof_menu.s on the POM2 IIe core (a2shot --iie).

The bench src/hof_test.s (ProDOS, NEOHOF.SYSTEM) plays the game's part for
a list of case records (SCENE at $8000): it sets the resident state the
module reads, runs module_end (src/hof_load.inc, as INPUT does), which reads
NEOWILD.END (the module, linked at $9600) from the disk and enters it. The
harness answers the name prompt with keys, then checks at each step,
against tools/score_ref.py (tests/score.py):
  - the text page byte for byte: entry screen and final screen;
  - the module's components and score (hof_outcome .. hof_total);
  - the table it read and modified ($5800) and the MLI calls it made
    (logged by the bench's mli_call, with one-shot injected errors);
  - for the loader fragment: the menu with its BEST cells and the H screen.
One session plays every case on one volume, so the table builds up: entry,
sort, ties, the fifth entry dropped, ESC, not ranked, free journey, read and
write errors, the module file missing, level/progress/hours clamps. Then the
disk is ejected (POM2 writes the private copy back), the image is located
and NEOWILD.HOF is read with dev/tools/prodos/read_volume.py: it must equal
the reference, still one seedling block. Other runs: a WOZ copy with the
write-protect flag (real $2B, score kept on screen, disk unchanged), a file
with a bad header and a volume without NEOWILD.HOF.

  test_hof.py                    run the IIe tests
  test_hof.py --demo-po OUT.po   ProDOS demo disk for hof.mk
"""
import argparse, glob, math, os, secrets, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(ROOT / 'dev/tools/prodos'))
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(HERE / 'tests'))
import a2test  # noqa: E402
import score as R  # noqa: E402  (tools/score_ref.py)
from po2woz import po_to_woz  # noqa: E402
from read_volume import Image  # noqa: E402

BUILD = HERE / 'build/hof'
PRODOS = ROOT / 'dev/tools/prodos'
CASES, CASE_SIZE = 0x8000, 48
HOF_BUF = 0x5800
HMAX = 7.866609670221806        # f_hmax of the first journey (gamedata.inc)
OPEN, READ, WRITE, CLOSE = 0xC8, 0xCA, 0xCB, 0xCC
LOAD_MODULE = [(OPEN, 0), (READ, 0), (CLOSE, 0)]
VARS = 22                       # hof_outcome .. hof_total+1


def afloat(x):
    """Applesoft 5-byte float."""
    if x == 0:
        return bytes(5)
    m, e = math.frexp(abs(x))
    mant = round(m * 2 ** 32)
    if mant == 2 ** 32:
        mant, e = mant >> 1, e + 1
    b = mant.to_bytes(4, 'big')
    return bytes((e + 128, b[0] & 0x7F | (0x80 if x < 0 else 0))) + b[1:]


def unfloat(b):
    if b[0] == 0:
        return 0.0
    mant = int.from_bytes(bytes((b[1] | 0x80,)) + b[2:5], 'big')
    return (-1 if b[1] & 0x80 else 1) * mant / 2 ** 32 * 2.0 ** (b[0] - 128)


class Case:
    """One module run (mode 1) or loader check (mode 2)."""

    def __init__(self, label, mode=1, region=2, outcome=R.ARRIVED, level=4, progress=100,
                 health=100, hours=0, kind=0, keys=(), fault=(0, 0, 0), elap=None, demo=False):
        self.label, self.mode, self.region, self.outcome = label, mode, region, outcome
        self.level, self.progress, self.kind, self.keys, self.fault = level, progress, kind, keys, fault
        self.demo = demo
        self.elap = hours + 0.3 if elap is None else elap
        # H such that round(H / Hmax * 100) = health, away from .5
        self.s_health = afloat(HMAX if health >= 100 else (health + 0.2) / 100 * HMAX)
        h = unfloat(self.s_health) / unfloat(afloat(HMAX)) * 100
        assert int(h + 0.5) == health, (label, h)
        self.health = health
        self.hours = min(int(unfloat(afloat(self.elap))), R.MAX_HOURS)

    def record(self):
        won, dead = self.outcome == R.ARRIVED, self.outcome == R.DIED
        name = R.REGION_NAMES[self.region - 1] if 1 <= self.region <= 6 else ''
        rec = (bytes((self.mode, won, dead, self.level, self.region, self.kind, self.progress))
               + afloat(self.elap) + self.s_health + afloat(HMAX) + bytes(self.fault)
               + name.encode().ljust(16, b'\0') + bytes((self.demo,)))
        return rec.ljust(CASE_SIZE, b'\0')

    def components(self):
        return R.score(self.progress, self.health, self.hours, self.outcome, self.level)

    def typed(self):
        """The name the keys leave, or None for ESC (tools/score_ref rules)."""
        name = ''
        for k in self.keys:
            if k == '\x1b':
                return None
            if k == '\r':
                return name
            if k in ('\\<', '\x7f'):
                name = name[:-1]
                continue
            c = k.upper()
            if c in R.NAME_CHARS and len(name) < R.NAME_LEN and not (c == ' ' and not name):
                name += c
        raise AssertionError('keys must end with RETURN or ESC')


def scene(cases):
    data = b''.join(c.record() for c in cases) + bytes(CASE_SIZE)
    assert CASES + len(data) <= 0x9600
    return data


def stage_volume(stage, cases, hof=b'', nonce=b''):
    stage = Path(stage)
    (stage / 'PRODOS#FF0000').write_bytes((PRODOS / 'PRODOS').read_bytes())
    (stage / 'NEOHOF.SYSTEM#FF2000').write_bytes((BUILD / 'NEOHOF.SYSTEM').read_bytes())
    (stage / 'HOFTEST#064000').write_bytes((BUILD / 'hof_test.bin').read_bytes())
    (stage / f'SCENE#06{CASES:04X}').write_bytes(scene(cases))
    (stage / 'NEOWILD.END#069600').write_bytes((BUILD / 'NEOWILD.END').read_bytes())
    if hof is not None:
        (stage / 'NEOWILD.HOF#060000').write_bytes(hof or R.empty_file())
    if nonce:
        (stage / 'NONCE#060000').write_bytes(nonce)


def build_po(out, cases, hof=b'', nonce=b'', volume='NEOHOF'):
    with tempfile.TemporaryDirectory(prefix='hof-stage-') as stage:
        stage_volume(stage, cases, hof, nonce)
        subprocess.run(['python3', str(PRODOS / 'build_volume.py'), stage, str(out),
                        '--volume', volume, '--boot', str(PRODOS / 'boot.bin'), '--blocks', '280'],
                       check=True, capture_output=True)
    return Path(out)


def screen(mem):
    """24 x 40 screen codes of text page 1 from a $0400 1 KB dump."""
    return b''.join(mem[0x80 * (r & 7) + 40 * (r >> 3):][:40] for r in range(24))


def show(codes):
    return '\n'.join(''.join(chr(b & 0x7F if b >= 0x80 else (b | 0x40 if b < 0x20 else b))
                             for b in codes[r * 40:r * 40 + 40]) for r in range(24))


def same_screen(label, got, want):
    if got != want:
        rows = [r for r in range(24) if got[r * 40:r * 40 + 40] != want[r * 40:r * 40 + 40]]
        raise AssertionError(f'{label}: rows {rows} differ\n--- got\n{show(got)}\n--- want\n{show(want)}')


def log_pairs(raw, n):
    return [(raw[i], raw[i + 1]) for i in range(0, n, 2)]


class Bench:
    """A live a2shot session on a bench volume, one step per case."""

    def __init__(self, session, labels):
        self.s, self.L = session, labels

    def peek(self, name, n, offset=0):
        return self.s.step(self.L.peek(name, n, offset)).dumps[0]

    def text(self):
        return screen(self.s.step('peek:0400:1024').dumps[0])

    def checkpoint(self):
        self.s.step(self.L.until('checkpoint', 3000))
        flag = self.peek('bench_flag', 1)[0]
        n = self.peek('mli_n', 1)[0]
        log = log_pairs(self.peek('mli_log', 64), n)
        return flag, log

    def resume(self):
        self.s.step(self.L.poke('dt_go', 1))
        self.s.step(self.L.until('cp_resume', 100))

    def module(self, c, state, read_err=0, write_err=0):
        """Play module case c on a disk whose NEOWILD.HOF is `state` (None:
        missing). Returns the file the disk holds afterwards."""
        comp = c.components()
        free = c.kind != 0 or not 1 <= c.region <= 6
        name = c.typed() if c.keys else None
        if c.fault[0] == OPEN and c.fault[2] == 0:          # module_end fails
            flag, log = self.checkpoint()
            assert flag == 2 and log == [(OPEN, c.fault[1])], (c.label, flag, log)
            self.resume()
            print(f'  {c.label}: module_end -> module_restart, no score')
            return state
        self.s.step(self.L.until('hof_key_wait', 4000))
        if c.keys:
            want, _ = R.end_screen(comp, c.region, R.REGION_NAMES[c.region - 1], free, state, '',
                                   read_err, write_err, phase='entry')
            same_screen(c.label + ' (name entry)', self.text(), want.bytes())
            for k in c.keys:            # one key at a time: a refusal beeps
                self.s.step('key:' + k)
                self.s.step(self.L.until('hof_key_wait', 4000))
        want, new = R.end_screen(comp, c.region, R.REGION_NAMES[c.region - 1] if 1 <= c.region <= 6 else '',
                                 free, state, name, read_err, write_err)
        same_screen(c.label, self.text(), want.bytes())
        v = self.peek('hof_outcome', VARS)
        u16 = lambda o: v[o] | v[o + 1] << 8  # noqa: E731
        got = dict(outcome=v[0], level=v[1], region=v[2], kind=v[3], progress=v[4], health=v[5],
                   hours=u16(6), mult=v[8], p=u16(10), a=u16(12), h=u16(14), s=u16(16),
                   base=u16(18), score=u16(20))
        for k, val in got.items():
            if k in comp:
                assert comp[k] == val, (c.label, k, val, comp[k])
        self.s.step('key: ')
        flag, log = self.checkpoint()
        buf = self.s.step(f'peek:{HOF_BUF:04X}:512').dumps[0]
        overlay = self.peek('last_overlay', 1)[0]
        self.resume()
        assert flag == 1 and overlay == 13, (c.label, flag, overlay)
        expect = list(LOAD_MODULE)
        if not free:
            if read_err == 0x46:                        # no file: OPEN fails
                expect += [(OPEN, 0x46)]
            else:
                expect += [(OPEN, 0), (READ, read_err), (CLOSE, 0)]
            if new is not None:
                expect += [(OPEN, 0), (WRITE, write_err), (CLOSE, 0)]
                assert buf == new, (c.label, 'table in memory')
        assert log == expect, (c.label, log, expect)
        kept = new if (new is not None and write_err == 0) else state
        print(f"  {c.label}: score {comp['score']} (base {comp['base']} x {comp['mult']}/14)"
              + (f', name {name!r}' if name else '') + ': OK')
        return kept

    def loader(self, c, state, read_err=0):
        flag, log = self.checkpoint()
        menu = self.text()
        self.resume()
        flag2, _ = self.checkpoint()
        hall = self.text()
        self.resume()
        want = R.Screen()
        for s in range(1, 7):
            want.put(3 * s - 1, 0, f'{s} {R.REGION_NAMES[s - 1]}')
            want.put(3 * s - 1, 33, 'BEST -')
        valid = state is not None and not read_err and R.Hof(state).valid()
        cells = R.menu_best_cells(state) if valid else {}
        for (row, col), text in cells.items():
            want.put(row, col, text)
        same_screen(c.label + ' (menu BEST)', menu, want.bytes())
        same_screen(c.label + ' (H screen)', hall, R.hall_screen(state if valid else None,
                                                                 read_err if read_err else
                                                                 (0 if valid else R.INVALID)).bytes())
        expect = [(OPEN, 0x46)] if read_err == 0x46 else [(OPEN, 0), (READ, read_err), (CLOSE, 0)]
        assert flag == 1 and flag2 == 1 and log == expect, (c.label, flag, log)
        print(f'  {c.label}: BEST {len(cells)} scenario(s), H screen: OK')


def main_cases():
    W, D, Q = R.ARRIVED, R.DIED, R.ABANDONED
    ret = '\r'
    return [
        Case('menu, empty hall of fame', mode=2),
        Case('Sierra arrived L4 312 h, name with edits', outcome=W, health=62, hours=312,
             keys=(' ', 'a', 'l', 'x', '\\<', 'i', '!', 'c', 'e', ret)),
        Case('Sierra died L4: second', outcome=D, progress=37, health=21, hours=150,
             keys=('B', 'O', 'B', ret)),
        Case('Sierra arrived L10: first', outcome=W, level=10, health=99, hours=50,
             keys=('C', 'A', 'R', 'O', 'L', ret)),
        Case('Sierra abandoned 100 h', outcome=Q, progress=50, health=80, hours=100,
             keys=('D', 'A', 'N', ret)),
        Case('same score, fewer hours: before', outcome=Q, progress=50, health=80, hours=80,
             keys=('E', 'V', 'E', ret)),
        Case('same score and hours: after, fifth dropped', outcome=Q, progress=50, health=80,
             hours=100, keys=('F', 'R', 'E', 'D', ret)),
        Case('not in the top 5: counted, written', outcome=D, level=1, progress=5, health=4,
             hours=12),
        Case('ranked, ESC: not recorded', outcome=W, health=50, hours=700,
             keys=('X', 'Y', '\x1b')),
        Case('free journey: not ranked, no file access', kind=1, outcome=W, health=90, hours=300),
        Case('Burma arrived L7, DELETE key', region=3, outcome=W, level=7, health=70, hours=400,
             keys=('Z', 'E', 'Q', '\x7f', 'D', ret)),
        Case('read error $27: no write', outcome=W, health=90, hours=200, fault=(READ, 0x27, 1)),
        Case('write error $27: score kept', region=6, outcome=D, progress=80, health=40, hours=90,
             keys=('W', 'E', 'S', ret), fault=(WRITE, 0x27, 0)),
        Case('write-protected ($2B injected)', region=4, outcome=W, health=60, hours=500,
             keys=('N', 'G', ret), fault=(WRITE, 0x2B, 0)),
        Case('NEOWILD.END missing: back to the menu', fault=(OPEN, 0x46, 0)),
        Case('Bolivia L0 -> 1, 40000 h -> 32767', region=5, outcome=D, level=0, progress=12,
             health=25, elap=40000.0, keys=('M', 'A', 'X', ret)),
        Case('British Columbia L12 -> 10, progress 150 -> 100', region=1, outcome=W, level=12,
             progress=150, health=100, hours=0, keys=('T', 'O', 'P', ret)),
        Case('QUIT at once: score 0, never ranked', region=6, outcome=Q, progress=0, health=100,
             hours=0),
        Case('menu, filled hall of fame', mode=2),
    ]


def find_copy(nonce, since):
    """The a2shot private copy holding `nonce` (other runs may be live)."""
    for path in glob.glob('/tmp/a2shot-*.po'):
        try:
            if os.path.getmtime(path) >= since - 2 and nonce in Path(path).read_bytes():
                return Path(path)
        except OSError:
            continue
    raise AssertionError('private copy of the bench disk not found')


def hof_entry(img):
    return next(e for e in img.entries(2) if e[1:1 + (e[0] & 15)] == b'NEOWILD.HOF')


def run_main(L):
    cases = main_cases()
    nonce = secrets.token_bytes(32)
    state = R.empty_file()
    with tempfile.TemporaryDirectory(prefix='hof-') as work:
        work = Path(work)
        disk = build_po(work / 'bench.po', cases, nonce=nonce)
        before = Image(disk.read_bytes())
        other = build_po(work / 'other.po', [], volume='OTHER')
        t0 = time.time()
        with a2test.Session(disk, iie=True, timeout=600) as s:
            b = Bench(s, L)
            for c in cases:
                if c.mode == 2:
                    b.loader(c, state)
                    continue
                read_err = c.fault[1] if c.fault[0] == READ else 0
                write_err = c.fault[1] if c.fault[0] == WRITE else 0
                state = b.module(c, state, read_err, write_err)
            flag, _ = b.checkpoint()
            assert flag == 3
            s.step('insert:' + str(other))      # eject: POM2 writes the image back
            image = find_copy(nonce, t0).read_bytes()
    img = Image(image)
    e = hof_entry(img)
    data = img.read(e)
    assert data == state, 'NEOWILD.HOF on the disk differs from tools/score_ref.py'
    assert e[0] >> 4 == 1 and int.from_bytes(e[0x13:0x15], 'little') == 1, 'still one seedling block'
    assert int.from_bytes(e[0x15:0x18], 'little') == 512
    assert img.free_blocks() == before.free_blocks(), 'no block allocated'
    hof = R.Hof(data)
    assert hof.sorted_ok()
    print(f'  disk image re-read with read_volume.py: NEOWILD.HOF = reference, {hof.games} journeys '
          f'counted, seedling 1 block, {img.free_blocks()} free blocks unchanged: OK')
    return state


def run_protected(L):
    """WOZ with the write-protect flag: ProDOS answers $2B for real."""
    cases = [Case('WOZ write-protected disk: $2B, score kept', outcome=R.ARRIVED, health=75,
                  hours=260, keys=('W', 'P', '\r')),
             Case('menu after it: nothing was written', mode=2)]
    with tempfile.TemporaryDirectory(prefix='hof-wp-') as work:
        po = build_po(Path(work) / 'wp.po', cases)
        woz = Path(work) / 'wp.woz'
        woz.write_bytes(po_to_woz(po.read_bytes(), write_protected=True))
        with a2test.Session(woz, iie=True, timeout=600) as s:
            b = Bench(s, L)
            b.module(cases[0], R.empty_file(), write_err=0x2B)
            b.loader(cases[1], R.empty_file())


def run_bad_file(L):
    bad = bytearray(R.empty_file())
    bad[0] = ord('X')
    cases = [Case('file with a bad header: not recognised', outcome=R.DIED, progress=40, health=30,
                  hours=120),
             Case('menu: bad header', mode=2)]
    with tempfile.TemporaryDirectory(prefix='hof-bad-') as work:
        disk = build_po(Path(work) / 'bad.po', cases, hof=bytes(bad))
        with a2test.Session(disk, iie=True, timeout=600) as s:
            b = Bench(s, L)
            b.module(cases[0], bytes(bad))
            b.loader(cases[1], bytes(bad))


def run_missing(L):
    cases = [Case('NEOWILD.HOF missing: error $46', outcome=R.DIED, progress=40, health=30,
                  hours=120),
             Case('menu: file missing', mode=2)]
    with tempfile.TemporaryDirectory(prefix='hof-none-') as work:
        disk = build_po(Path(work) / 'none.po', cases, hof=None)
        with a2test.Session(disk, iie=True, timeout=600) as s:
            b = Bench(s, L)
            b.module(cases[0], None, read_err=0x46)
            b.loader(cases[1], None, read_err=0x46)


def demo_cases():
    """Type a name at each prompt; any key goes on at the checkpoints."""
    return [Case('demo: Sierra arrived', outcome=R.ARRIVED, health=62, hours=312, demo=True),
            Case('demo: Burma died', region=3, outcome=R.DIED, progress=45, health=20, hours=90,
                 demo=True),
            Case('demo: free journey', kind=1, outcome=R.ABANDONED, progress=20, health=70,
                 hours=30, demo=True),
            Case('demo: menu BEST, then H', mode=2, demo=True)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--demo-po', type=Path, help='build the ProDOS demo disk and exit')
    a = ap.parse_args()
    if a.demo_po:
        build_po(a.demo_po, demo_cases())
        return
    if sys.platform != 'darwin' or not a2test.A2SHOT.exists():
        print('SKIP: a2shot (IIe POM2 core) is required')
        return
    L = a2test.labels(BUILD / 'hof_test.lbl')
    run_main(L)
    run_protected(L)
    run_bad_file(L)
    run_missing(L)
    mod = (BUILD / 'NEOWILD.END').stat().st_size
    print(f'  module NEOWILD.END (bench build): {mod} bytes')
    print('Hall of fame bench: OK')


if __name__ == '__main__':
    main()
