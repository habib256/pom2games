#!/usr/bin/env python3
"""tools/score_ref.py (tests/score.py), tools/genhof.py and tools/po2woz.py,
pure Python (no emulator).

Score: the worked examples of docs/HOF.md, the 16-bit bounds over every
input, the clamps and the order of the integer operations. Hall of fame:
the 512-byte layout of an empty file, entry encoding round trip, ranking
(empty entries, higher score, equal score with fewer hours, full ties after
the old entry), insertion dropping the fifth entry, saturating counters, a
long random sequence keeping every table sorted. Screens: 40 columns, the
fixed rows of each path. WOZ: a track decodes back to the .po sectors and
the INFO chunk carries the write-protect flag.
"""
import random, struct, subprocess, sys, tempfile, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(HERE / 'tests'))
import score as R  # noqa: E402  (tools/score_ref.py)
import po2woz  # noqa: E402

W, D, Q = R.ARRIVED, R.DIED, R.ABANDONED


def test_worked_examples():
    """The examples of docs/HOF.md, component by component."""
    c = R.score(100, 62, 312, W, 4)
    assert (c['p'], c['a'], c['h'], c['s'], c['base'], c['score']) == (1000, 1000, 310, 408, 2718, 2718)
    c = R.score(100, 100, 0, W, 10)
    assert (c['base'], c['mult'], c['score']) == (3220, 20, 4600)      # the maximum
    c = R.score(37, 21, 150, D, 4)
    assert (c['p'], c['a'], c['h'], c['s'], c['score']) == (370, 0, 38, 0, 408)   # 105 * 37 // 100
    c = R.score(0, 100, 0, Q, 4)
    assert c['score'] == 0, 'QUIT at the first prompt scores nothing'
    c = R.score(50, 80, 100, Q, 4)
    assert (c['h'], c['score']) == (200, 700)
    c = R.score(5, 4, 12, D, 1)
    assert (c['base'], c['mult'], c['score']) == (51, 11, 40)          # 51 * 11 = 561 / 14 = 40.07
    c = R.score(100, 70, 400, W, 7)
    assert (c['base'], c['score']) == (2670, 3242)                     # 2670 * 17 = 45390 / 14
    c = R.score(100, 50, 900, W, 4)
    assert c['s'] == 0 and c['score'] == 2250, 'no speed bonus after 720 hours'


def test_bounds_and_clamps():
    worst = 0
    for outcome in (W, D, Q):
        for level in range(1, 11):
            for p in range(0, 101):
                for h in range(0, 101, 5):
                    for hours in (0, 1, 719, 720, 32767):
                        c = R.score(p, h, hours, outcome, level)
                        assert 0 <= c['score'] <= 4600
                        assert c['base'] * c['mult'] < 65536
                        assert h * 5 * p < 65536
                        worst = max(worst, c['score'])
    assert worst == 4600
    assert R.score(150, 120, 99999, W, 12) == R.score(100, 100, R.MAX_HOURS, W, 10)
    assert R.score(10, 10, -5, D, 0)['level'] == 1
    assert R.outcome_of(won=1, dead=1) == W and R.outcome_of(0, 1) == D and R.outcome_of(0, 0) == Q
    # floor at each division, in this order
    c = R.score(33, 33, 10, D, 3)
    assert c['h'] == 165 * 33 // 100 and c['score'] == (330 + c['h']) * 13 // 14


def test_empty_file_and_genhof():
    data = R.empty_file()
    assert len(data) == 512 and data[:2] == b'H\x01' and not any(data[2:])
    with tempfile.TemporaryDirectory() as work:
        out = Path(work) / 'NEOWILD.HOF'
        subprocess.run([sys.executable, str(HERE / 'tools/genhof.py'), str(out)], check=True)
        assert out.read_bytes() == data
    hof = R.Hof(data)
    assert hof.valid() and hof.games == 0
    assert all(hof.best(s) is None for s in range(1, 7))
    assert R.entry_offset(1, 0) == 32 and R.entry_offset(6, 4) == 496


def test_entry_round_trip():
    raw = R.entry_bytes('Alice', 2718, 312, 4, W)
    assert len(raw) == 16
    assert raw[:8] == bytes(b | 0x80 for b in b'ALICE   ')
    assert raw[8:] == bytes((2718 & 255, 2718 >> 8, 312 & 255, 312 >> 8, 4, W, 0, 0))
    hof = R.Hof()
    hof.insert(2, 0, raw)
    e = hof.entry(2, 0)
    assert (e['name'], e['score'], e['hours'], e['level'], e['outcome']) == ('ALICE', 2718, 312, 4, W)
    assert R.Hof(hof.bytes()).entry(2, 0) == e
    assert hof.best(2) == 2718 and hof.best(1) is None


def test_rank_rules():
    hof = R.Hof()
    s = 3
    assert hof.rank(s, 1, 0) == 0, 'an empty entry takes any result'
    assert hof.rank(s, 0, 0) is None, 'a score of 0 is never ranked'
    for k, (score_, hours) in enumerate([(900, 50), (700, 100), (700, 200)]):
        hof.insert(s, k, R.entry_bytes(f'P{k}', score_, hours, 4, Q))
    assert hof.rank(s, 901, 999) == 0
    assert hof.rank(s, 700, 99) == 1, 'equal score, fewer hours: before'
    assert hof.rank(s, 700, 100) == 2, 'full tie: after the old entry'
    assert hof.rank(s, 700, 200) == 3
    assert hof.rank(s, 1, 0) == 3, 'empty entries come last'
    hof.insert(s, 3, R.entry_bytes('P3', 600, 1, 4, D))
    hof.insert(s, 4, R.entry_bytes('P4', 500, 1, 4, D))
    assert hof.rank(s, 499, 0) is None
    hof.insert(s, 0, R.entry_bytes('NEW', 1000, 1, 4, W))
    names = [e['name'] for e in hof.entries(s)]
    assert names == ['NEW', 'P0', 'P1', 'P2', 'P3'], 'the fifth dropped'
    assert all(hof.entry(o, 0)['outcome'] == 0 for o in (1, 2, 4, 5, 6)), 'other scenarios untouched'


def test_counters_saturate():
    data = bytearray(R.empty_file())
    data[2:4] = (0xFFFE).to_bytes(2, 'little')
    data[4 + 2 * 4:6 + 2 * 4] = (0xFFFF).to_bytes(2, 'little')
    hof = R.Hof(data)
    hof.count_game(5)
    hof.count_game(5)
    assert hof.games == 0xFFFF and hof.scenario_games(5) == 0xFFFF


def test_random_sequence():
    rnd = random.Random(1985)
    data = R.empty_file()
    played = {s: [] for s in range(1, 7)}
    for _ in range(400):
        s = rnd.randint(1, 6)
        outcome = rnd.choice((W, D, Q))
        c = R.score(rnd.randint(0, 100), rnd.randint(0, 100), rnd.randint(0, 900), outcome,
                    rnd.randint(1, 10))
        name = None if rnd.random() < 0.1 else rnd.choice(['A', 'BOB', 'CAROL.J', 'D-E', 'X Y'])
        data, rank = R.record(data, s, c, name)
        if rank is not None and name is not None:
            played[s].append((c['score'], -c['hours']))
    hof = R.Hof(data)
    assert hof.sorted_ok() and hof.games == 400
    for s in range(1, 7):
        kept = [(e['score'], -e['hours']) for e in hof.entries(s) if e['outcome']]
        assert kept == sorted(played[s], reverse=True)[:5]


def test_screens():
    c = R.score(100, 62, 312, W, 4)
    scr, new = R.end_screen(c, 2, 'SIERRA NEVADA', False, R.empty_file(), 'ALICE')
    t = scr.text()
    assert t[0].strip() == 'JOURNEY SCORE' and t[0].index('J') == 13
    assert t[12].startswith('SCORE') and t[12][28:33] == ' 2718'
    assert scr.rows[12][28] == 0x20, 'score in inverse'
    assert t[15].startswith('1 ALICE     2718   312H L4  ARRIVED')
    assert t[22].startswith(R.MSG_SAVED) and t[23].startswith(R.MSG_KEY)
    assert R.Hof(new).entry(2, 0)['name'] == 'ALICE' and R.Hof(new).games == 1
    scr, new = R.end_screen(c, 2, 'SIERRA NEVADA', True, R.empty_file(), None)
    assert new is None and scr.text()[21].startswith(R.MSG_FREE) and '(FREE)' in scr.text()[2]
    scr, new = R.end_screen(c, 2, 'SIERRA NEVADA', False, None, None, read_err=0x46)
    assert new is None and scr.text()[21].startswith('HALL OF FAME UNREADABLE, ERROR $46.')
    bad = bytearray(R.empty_file())
    bad[1] = 2
    scr, new = R.end_screen(c, 2, 'SIERRA NEVADA', False, bytes(bad), 'X')
    assert new is None and scr.text()[21].startswith(R.MSG_INVALID)
    scr, _ = R.end_screen(c, 2, 'SIERRA NEVADA', False, R.empty_file(), 'AB', write_err=0x2B)
    assert scr.text()[22].startswith(R.MSG_PROTECTED)
    scr, _ = R.end_screen(c, 2, 'SIERRA NEVADA', False, R.empty_file(), 'AB', write_err=0x27)
    assert scr.text()[22].startswith('DISK ERROR $27: NOT SAVED.')
    scr, _ = R.end_screen(c, 2, 'SIERRA NEVADA', False, R.empty_file(), 'AB', phase='entry')
    assert scr.rows[15][4] == 0x20 and scr.text()[15][2:4] == 'AB', 'cursor after the name'
    d = R.score(37, 21, 150, D, 4)
    assert R.end_screen(d, 2, 'SIERRA NEVADA', True, None, None)[0].text()[7].startswith(
        'HEALTH     21% X 5 X 37%')
    full = R.empty_file()
    for s in range(1, 7):
        for k in range(5):
            full, _ = R.record(full, s, R.score(100, 100, k * 10, W, 10), 'WWWWWWWW')
    for scr in (R.hall_screen(full), R.end_screen(R.score(100, 100, 32767, W, 10), 1,
                                                  'BRITISH COLUMBIA', False, full, None)[0]):
        assert len(scr.bytes()) == 960
    hall = R.hall_screen(full).text()
    assert hall[2].startswith('1 SIERRA NEVADA') and hall[2][20:].startswith('2 BRITISH COLUMBIA')
    assert hall[3] == '1 WWWWWWWW  4600    1 WWWWWWWW  4600    '
    assert hall[22].startswith('SCENARIO JOURNEYS: 30')
    cells = R.menu_best_cells(full)
    assert cells[(2, 35)] == ' 4600' and len(cells) == 6
    assert R.menu_best_cells(bytes(bad)) == {}
    assert R.hall_screen(None, 0x46).text()[22].startswith('HALL OF FAME UNREADABLE, ERROR $46.')


READ_TABLE = {b: i for i, b in enumerate(po2woz.WRITE)}


def decode62(nibbles):
    vals, prev = [], 0
    for n in nibbles[:342]:
        prev ^= READ_TABLE[n]
        vals.append(prev)
    assert READ_TABLE[nibbles[342]] == prev, 'checksum'
    aux, hi = vals[:86], vals[86:]
    out = bytearray(256)
    for i in range(256):
        a = (aux[i % 86] >> (2 * (i // 86))) & 3
        out[i] = (hi[i] << 2) | ((a & 1) << 1) | (a >> 1)
    return bytes(out)


def bytes_of(bits):
    """Read nibbles like the Disk II: skip zeros until a set bit."""
    out, i = [], 0
    while i + 8 <= len(bits):
        if not bits[i]:
            i += 1
            continue
        v = 0
        for k in range(8):
            v = v << 1 | bits[i + k]
        out.append(v)
        i += 8
    return out


def test_po2woz():
    rnd = random.Random(7)
    po = bytes(rnd.getrandbits(8) for _ in range(143360))
    woz = po2woz.po_to_woz(po, write_protected=True)
    assert woz[:8] == b'WOZ2\xFF\x0A\x0D\x0A'
    assert struct.unpack('<I', woz[8:12])[0] == zlib.crc32(woz[12:])
    assert woz[12:16] == b'INFO' and woz[20] == 2 and woz[22] == 1, 'version 2, write-protected'
    assert po2woz.po_to_woz(po, write_protected=False)[22] == 0
    tmap = woz[80 + 8:80 + 8 + 160]
    assert tmap[0] == 0 and tmap[4] == 1 and tmap[136] == 34 and tmap[140] == 0xFF
    trks = 248 + 8
    for t in (0, 17, 34):
        start, count, nbits = struct.unpack('<HHI', woz[trks + 8 * t:trks + 8 * t + 8])
        raw = woz[start * 512:start * 512 + (nbits + 7) // 8]
        bits = [(raw[i >> 3] >> (7 - (i & 7))) & 1 for i in range(nbits)]
        nib = bytes_of(bits)
        found = {}
        for i in range(len(nib) - 3):
            if nib[i:i + 3] == [0xD5, 0xAA, 0x96]:
                f = lambda k: ((nib[i + 3 + 2 * k] << 1) | 1) & nib[i + 4 + 2 * k]  # noqa: E731
                trk, sec = f(1), f(2)
                assert trk == t
                j = nib.index(0xAD, i + 11) + 1
                assert nib[j - 3:j] == [0xD5, 0xAA, 0xAD]
                found[sec] = decode62(nib[j:j + 343])
        assert len(found) == 16
        for ls in range(16):
            assert found[po2woz.PO_TO_PHYS[ls]] == po[t * 4096 + ls * 256:t * 4096 + ls * 256 + 256]


def main():
    tests = [v for k, v in globals().items() if k.startswith('test_')]
    for t in tests:
        t()
        print(f'  {t.__name__}: OK')
    print(f'Score and hall of fame reference: {len(tests)} tests OK')


if __name__ == '__main__':
    main()
