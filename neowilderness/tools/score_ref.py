#!/usr/bin/env python3
"""score_ref.py: Python reference of the journey score and of NEOWILD.HOF (lot 7, step 6).

The oracle of src/hof.s (end-of-game module wildhof.bin) and of the loader
fragment src/hof_menu.s: score formula with its exact integer order, the
512-byte file format, ranking and insertion, and the text screens both draw
(40 x 24 screen codes, byte for byte). docs/HOF.md describes the same rules.

Score (16-bit integers, no intermediate rounding):
    progress = clamp(DONE%, 0, 100)            STATUS "DONE=" (module_progress)
    health   = clamp(HEALTH%, 0, 100)          round(H / Hmax * 100), as STATUS
    hours    = INT(s_elap), clamped to 0..32767
    H        = health * 5                      if arrived
               floor(health * 5 * progress / 100)  otherwise
    base     = progress * 10 + (1000 if arrived) + H
               + (max(0, 720 - hours) if arrived)          <= 3220
    score    = floor(base * (10 + level) / 14)            level clamped 1..10
base * 20 <= 64 400 and health * 5 * progress <= 50 000 fit 16 bits: the
6502 multiplies, then divides once. Weighting the health of a journey that
did not arrive by its progress keeps QUIT at the first prompt (100 % health,
0 % progress) from scoring 500 points, more than most real deaths.

    score_ref.py --dump FILE.HOF     print a hall of fame file
"""
import sys
from pathlib import Path

SCENARIOS = 6
ENTRIES = 5
ENTRY_SIZE = 16
HEADER_SIZE = 32
FILE_SIZE = 512
MAGIC = ord('H')
VERSION = 1
NAME_LEN = 8
MAX_HOURS = 32767

ARRIVED, DIED, ABANDONED = 1, 2, 3
OUTCOMES = {ARRIVED: 'ARRIVED', DIED: 'DIED', ABANDONED: 'ABANDONED'}
LETTERS = {ARRIVED: 'A', DIED: 'D', ABANDONED: 'Q'}
REGION_NAMES = ['BRITISH COLUMBIA', 'SIERRA NEVADA', 'BURMA', 'NEW GUINEA', 'BOLIVIA', 'CHILE']
NAME_CHARS = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .-')

assert HEADER_SIZE + SCENARIOS * ENTRIES * ENTRY_SIZE == FILE_SIZE


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# score
def score(progress, health, hours, outcome, level):
    """Components of the score, as the module computes and displays them."""
    won = outcome == ARRIVED
    p = clamp(progress, 0, 100)
    h = clamp(health, 0, 100)
    hours = clamp(hours, 0, MAX_HOURS)
    lv = clamp(level, 1, 10)
    c = dict(progress=p, health=h, hours=hours, level=lv, outcome=outcome,
             p=p * 10, a=1000 if won else 0, h=h * 5 if won else h * 5 * p // 100,
             s=max(0, 720 - hours) if won else 0, mult=10 + lv)
    c['base'] = c['p'] + c['a'] + c['h'] + c['s']
    product = c['base'] * c['mult']
    assert product < 65536
    c['score'] = product // 14
    return c


def outcome_of(won, dead):
    """Outcome byte from the game flags: arrival wins over death."""
    return ARRIVED if won else DIED if dead else ABANDONED


# ---------------------------------------------------------------------------
# file
def empty_file():
    """What tools/genhof.py writes: header, then 30 empty entries."""
    data = bytearray(FILE_SIZE)
    data[0], data[1] = MAGIC, VERSION
    return bytes(data)


def encode_name(text):
    text = text.upper()[:NAME_LEN].ljust(NAME_LEN)
    assert set(text) <= NAME_CHARS, text
    return bytes(ord(c) | 0x80 for c in text)


def decode_name(raw):
    return ''.join(chr(b & 0x7F) for b in raw).rstrip()


def entry_bytes(name, score_, hours, level, outcome):
    return (encode_name(name) + score_.to_bytes(2, 'little') + hours.to_bytes(2, 'little')
            + bytes((level, outcome, 0, 0)))


def entry_offset(scenario, rank):
    """scenario 1..6, rank 0..4."""
    return HEADER_SIZE + ((scenario - 1) * ENTRIES + rank) * ENTRY_SIZE


class Hof:
    """A parsed NEOWILD.HOF (keeps every byte, reserved ones included)."""

    def __init__(self, data=None):
        self.data = bytearray(empty_file() if data is None else data)
        assert len(self.data) == FILE_SIZE

    def valid(self):
        return self.data[0] == MAGIC and self.data[1] == VERSION

    @property
    def games(self):
        return int.from_bytes(self.data[2:4], 'little')

    def scenario_games(self, s):
        return int.from_bytes(self.data[4 + 2 * (s - 1):6 + 2 * (s - 1)], 'little')

    def entry(self, s, k):
        o = entry_offset(s, k)
        e = self.data[o:o + ENTRY_SIZE]
        return dict(name=decode_name(e[:8]), raw_name=bytes(e[:8]),
                    score=int.from_bytes(e[8:10], 'little'),
                    hours=int.from_bytes(e[10:12], 'little'),
                    level=e[12], outcome=e[13])

    def entries(self, s):
        return [self.entry(s, k) for k in range(ENTRIES)]

    def best(self, s):
        e = self.entry(s, 0)
        return e['score'] if e['outcome'] else None

    def rank(self, s, score_, hours):
        """Index where a new result goes, or None (not in the top 5; a
        score of 0 is never ranked)."""
        if score_ == 0:
            return None
        for k, e in enumerate(self.entries(s)):
            if (not e['outcome'] or score_ > e['score']
                    or (score_ == e['score'] and hours < e['hours'])):
                return k
        return None

    def count_game(self, s):
        """Both counters saturate at 65535."""
        for o in (2, 4 + 2 * (s - 1)):
            v = int.from_bytes(self.data[o:o + 2], 'little')
            self.data[o:o + 2] = min(v + 1, 0xFFFF).to_bytes(2, 'little')

    def insert(self, s, rank, raw):
        """Shift entries rank..3 down one place (the fifth is dropped)."""
        base = entry_offset(s, 0)
        rows = [bytes(self.data[base + k * ENTRY_SIZE:base + (k + 1) * ENTRY_SIZE])
                for k in range(ENTRIES)]
        rows.insert(rank, raw)
        self.data[base:base + ENTRIES * ENTRY_SIZE] = b''.join(rows[:ENTRIES])

    def sorted_ok(self):
        for s in range(1, SCENARIOS + 1):
            es = self.entries(s)
            seen_empty = False
            for a, b in zip(es, es[1:]):
                if not a['outcome']:
                    seen_empty = True
                if seen_empty and b['outcome']:
                    return False
                if a['outcome'] and b['outcome'] and (
                        (a['score'], -a['hours']) < (b['score'], -b['hours'])):
                    return False
        return True

    def bytes(self):
        return bytes(self.data)


def record(data, scenario, c, name):
    """The module's whole update of a valid file for one scenario journey.
    name None = ESC (not recorded) or not in the top 5. Returns (new bytes, rank)."""
    hof = Hof(data)
    hof.count_game(scenario)
    rank = hof.rank(scenario, c['score'], c['hours'])
    if rank is not None and name is not None:
        hof.insert(scenario, rank, entry_bytes(name, c['score'], c['hours'], c['level'], c['outcome']))
    return hof.bytes(), rank


# ---------------------------------------------------------------------------
# screens: 24 rows of 40 screen codes (text page 1, primary character set)
def code(ch, inverse=False):
    o = ord(ch)
    assert 0x20 <= o < 0x60, ch
    return o & 0x3F if inverse else o | 0x80


class Screen:
    def __init__(self):
        self.rows = [bytearray(code(' ') for _ in range(40)) for _ in range(24)]

    def put(self, row, col, text, inverse=False):
        assert col + len(text) <= 40, (row, col, text)
        for i, ch in enumerate(text):
            self.rows[row][col + i] = code(ch, inverse)

    def text(self):
        return [''.join(chr(b & 0x7F if b >= 0x80 else (b | 0x40 if b < 0x20 else b))
                        for b in row) for row in self.rows]

    def bytes(self):
        return b''.join(bytes(r) for r in self.rows)


def title(scr, text):
    """Row 0: inverse band, text at column (40 - len) // 2."""
    scr.put(0, 0, ' ' * 40, inverse=True)
    scr.put(0, (40 - len(text)) // 2, text, inverse=True)


def num(v, width=5):
    return f'{v:>{width}}'


VALUE_COL = 28                  # five-digit values end at column 32


def breakdown(scr, c, region_name, free):
    """Rows 0..12 of the end-of-game screen."""
    title(scr, 'JOURNEY SCORE')
    scr.put(2, 0, f"{region_name}, LEVEL {c['level']}" + (' (FREE)' if free else ''))
    scr.put(3, 0, f"{OUTCOMES[c['outcome']]} AFTER {c['hours']} HOURS")
    won = c['outcome'] == ARRIVED
    lines = [
        (5, f"PROGRESS  {c['progress']:>3}% X 10", c['p']),
        (6, 'ARRIVAL   ' + ('YES' if won else 'NO'), c['a']),
        (7, f"HEALTH    {c['health']:>3}% X 5" + ('' if won else f" X {c['progress']}%"), c['h']),
        (8, 'SPEED     ' + (f"720 - {c['hours']}" if won else 'NO'), c['s']),
        (10, 'TOTAL', c['base']),
        (11, f"LEVEL     {c['level']:>3} X {c['mult']}/14", c['score']),
    ]
    for row, label, value in lines:
        scr.put(row, 0, label)
        scr.put(row, VALUE_COL, num(value))
    scr.put(9, VALUE_COL, '-----')
    scr.put(12, 0, 'POINTS')
    scr.put(12, VALUE_COL, num(c['score']), inverse=True)


def table_line(k, e):
    """One ranked line of the end-of-game table (row 15 + k)."""
    if not e['outcome']:
        return f'{k + 1} -'
    return (f"{k + 1} {e['name']:<8} {e['score']:>5} {e['hours']:>5}H "
            f"L{e['level']:<2} {OUTCOMES.get(e['outcome'], '?')}")


def table(scr, hof, s):
    scr.put(14, 0, f'{REGION_NAMES[s - 1]} - TOP 5')
    for k, e in enumerate(hof.entries(s)):
        scr.put(15 + k, 0, ' ' * 40)
        scr.put(15 + k, 0, table_line(k, e))


MSG_FREE = 'FREE JOURNEY: NOT RANKED.'
MSG_INVALID = 'HALL OF FAME FILE NOT RECOGNISED.'
MSG_NOT_TOP = 'NOT IN THE TOP 5.'
MSG_SKIPPED = 'NOT RECORDED.'
MSG_HELP = 'UP/DN LETTER > NEXT RET SAVE ESC SKIP'
MSG_SAVED = 'HALL OF FAME SAVED.'
MSG_PROTECTED = 'DISK WRITE-PROTECTED: NOT SAVED.'
MSG_KEY = 'PRESS A KEY FOR THE MENU.'


INVALID = 0x01                  # status of a short or unknown file (not an MLI code)


def msg_unreadable(err):
    if err == INVALID:
        return MSG_INVALID
    return f'HALL OF FAME UNREADABLE, ERROR ${err:02X}.'


def msg_rank(rank):
    return f'NEW RECORD: RANK {rank + 1}. TYPE YOUR NAME.'


def msg_write(err):
    if err == 0:
        return MSG_SAVED
    if err == 0x2B:
        return MSG_PROTECTED
    return f'DISK ERROR ${err:02X}: NOT SAVED.'


def end_screen(c, region, region_name, free, file_data, name, read_err=0, write_err=0,
               phase='final'):
    """The module's screen. file_data: NEOWILD.HOF as read (None if not read).
    name: the entered name, None for ESC. phase 'entry' = while typing (name
    so far: '' at the first key), 'final' = at "PRESS A KEY FOR THE MENU".
    Returns (Screen, new file bytes or None when nothing is written)."""
    scr = Screen()
    breakdown(scr, c, region_name, free)
    if free or not 1 <= region <= SCENARIOS:
        scr.put(21, 0, MSG_FREE)
        scr.put(23, 0, MSG_KEY)
        return scr, None
    if not read_err and not Hof(file_data).valid():
        read_err = INVALID
    if read_err:
        scr.put(21, 0, msg_unreadable(read_err))
        scr.put(23, 0, MSG_KEY)
        return scr, None
    hof = Hof(file_data)
    hof.count_game(region)
    rank = hof.rank(region, c['score'], c['hours'])
    if rank is None:
        table(scr, hof, region)
        scr.put(21, 0, MSG_NOT_TOP)
    elif phase == 'entry':
        typed = name or ''
        hof.insert(region, rank, entry_bytes(typed, c['score'], c['hours'], c['level'], c['outcome']))
        table(scr, hof, region)
        if len(typed) < NAME_LEN:
            scr.put(15 + rank, 2 + len(typed), ' ', inverse=True)
        scr.put(21, 0, msg_rank(rank))
        scr.put(22, 0, MSG_HELP)
        return scr, None
    elif name is None:
        table(scr, hof, region)
        scr.put(21, 0, MSG_SKIPPED)
    else:
        hof.insert(region, rank, entry_bytes(name, c['score'], c['hours'], c['level'], c['outcome']))
        table(scr, hof, region)
        scr.put(21, 0, msg_rank(rank))
    scr.put(22, 0, msg_write(write_err))
    scr.put(23, 0, MSG_KEY)
    return scr, hof.bytes()


# ---------------------------------------------------------------------------
# loader side (src/hof_menu.s)
BEST_ROW0, BEST_COL = 2, 35                   # the score at columns 35..39 of the scenario's row


def menu_best_cells(file_data):
    """{(row, col): text} written over the menu's 'BEST -' placeholders."""
    hof = Hof(file_data)
    out = {}
    if not hof.valid():
        return out
    for s in range(1, SCENARIOS + 1):
        b = hof.best(s)
        if b is not None:
            out[(BEST_ROW0 + MENU_ORDER.index(s), BEST_COL)] = f'{b:>5}'
    return out


MENU_ORDER = (2, 1, 3, 4, 5, 6)   # tools/genmenu.py MENU_ORDER: regions by menu key


def hall_block(s):
    """(row, col) of the header of menu key s on the H screen."""
    return 2 + 7 * ((s - 1) // 2), 0 if s % 2 else 20


def hall_screen(file_data, read_err=0):
    """The H screen of the start menu. read_err: MLI error of the menu's
    read (0: read). An unreadable or unknown file shows empty tables."""
    scr = Screen()
    hof = Hof(file_data if file_data is not None and not read_err else None)
    if not hof.valid():
        hof, read_err = Hof(), read_err or INVALID
    title(scr, 'HALL OF FAME')
    for key, s in enumerate(MENU_ORDER, 1):      # blocks in menu order
        r, col = hall_block(key)
        scr.put(r, col, f'{key} {REGION_NAMES[s - 1]}'[:19], inverse=True)
        for k, e in enumerate(hof.entries(s)):
            line = f"{k + 1} {e['name']:<8} {e['score']:>5}" if e['outcome'] else f'{k + 1} -'
            scr.put(r + 1 + k, col, line)
    if read_err:
        scr.put(22, 0, msg_unreadable(read_err))
    else:
        scr.put(22, 0, f'SCENARIO JOURNEYS: {hof.games}')
    scr.put(23, 0, MSG_KEY)
    return scr


def dump(data):
    hof = Hof(data)
    print(f"magic {data[0]:02X} version {data[1]} games {hof.games} valid {hof.valid()}")
    for s in range(1, SCENARIOS + 1):
        print(f'{s} {REGION_NAMES[s - 1]} ({hof.scenario_games(s)} journeys)')
        for k, e in enumerate(hof.entries(s)):
            print('   ' + table_line(k, e))


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--dump':
        dump(Path(sys.argv[2]).read_bytes())
        return
    sys.exit(__doc__)


if __name__ == '__main__':
    main()
