#!/usr/bin/env python3
"""MB TRACKER on a2shot: //e enhanced and //c with a Mockingboard in slot 4
(the //c's 4c woken by mb_detect), and a //e without one.

//e: the editor boots (title bar, grid, the card's slot read on the text
pages, aux columns through PAGE2); notes, a note off, an effect and its
parameter typed on the piano keys, an instrument edited in the instrument
editor, the speed lowered: the grid bytes are the cells typed and the AYS
bytes the tracker encodes for ^P are aysong.encode() of the same song built
in Python; the AY writes decoded from the slot's VIA stores are the Python
Player's (test_aysong.model) tick for tick; ^S writes TEST.AYS on the disk,
read back from the image with read_volume.py and decoded by aysong.py; ^L
lists DEMO.AYS and loads it: the buffer is the shipped file, and once the
song is encoded again (an edit and its undo) still the same bytes, played
as the model plays them.
//c: the same notes and play, on the bus.
No card: "NO MOCKINGBOARD", editing still works, ^P only says so.

The mouse (a2shot `mouse:` steps: the X clamp 0-159 = two pixels a column,
8 a row; hops of 40 pixels at most, the button held 8 frames): on a //e
with the card in slot 4 and an AppleMouse in slot 2, a click on a field
moves the cursor there, a note typed lands in it; the instrument panel
(a click selects, a second one opens the editor, where a click on a tick's
field and a typed digit edit it, the bar's ESC BACK returns); a drag
marks a block (two voices, five rows), ^C, a click elsewhere, ^V pastes
it; ^B and the arrows mark another one, ' and " transpose it, ^Z undoes
the last one and ^Z again redoes it, ^X cuts it; the bar's PLAY plays
(the AY writes = the Python Player) and STOP stops; ORD gives the keys to
the order list (I inserts a new pattern, C clones it, a click picks an
entry, D deletes a pattern and its entries); LOAD and two clicks on
DEMO.AYS load it; HELP shows both help pages. Every grid is compared with
the same song built in Python. 6 voices (//e and //c with the card): ^N
then Y, notes on both chips, played = the Player with max_voices 6. The
//c with a 4c: the 4c answers $C400-$C4FF over the mouse firmware once
woken (POM2, as the real card): no mouse there, the keyboard does it all;
the //c without a card: its own mouse clicks a cell and the bar."""
import glob
import os
import queue
import secrets
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'mbtracker'
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(ROOT / 'dev/tools/audio'))
sys.path.insert(0, str(ROOT / 'dev/tests'))
import a2test  # noqa: E402
import aysong  # noqa: E402
from aysong import Cell, Instrument, Pattern, Song, Tick, OFF  # noqa: E402
import test_aysong  # noqa: E402
from test_mb_irq import ay_writes  # noqa: E402

DISK = ROOT / 'dist/MBTRACKER.po'
L = a2test.labels(GAME / 'build/mbt.lbl', strip=True)
UP, DOWN, LEFT, RIGHT, RET, ESC, DEL = '\x0b', '\x0a', '\x08', '\x15', '\r', '\x1b', '\x7f'


def ctrl(c):
    return chr(ord(c) & 0x1F)


class Session(a2test.Session):
    """a2test.Session with any a2shot flags (--mockingboard, --iic)."""

    def __init__(self, disk, flags, timeout=180):
        self.timeout = timeout
        self.stderr = tempfile.TemporaryFile(mode='w+t')
        self.process = subprocess.Popen([str(a2test.A2SHOT), *flags, '--disk', str(disk), '--stdin'],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr,
                                        text=True, bufsize=1)
        self.replies = queue.Queue()
        self.out = ''

        def read():
            for line in self.process.stdout:
                self.replies.put(line)
            self.replies.put(None)

        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()

    mpos = (70, 96)                   # (dev/lib/mouse: the start position)
    sync = True                       # //e: read once a refresh (main.c event())

    def mouse_to(self, x, y, b=0):
        """In hops of 40 pixels at most, 6 frames each. a2shot's mouse: step
        corrects the card once a frame from what the program last read; the
        //e reads it once a refresh: the run first stops just after a read,
        so that the card has a whole frame to take each correction (else the
        loop may chase a stale position and never settle)."""
        if self.sync:
            self.idle()
            self.step(f'until:{L["mouse_read_done"]:04X}:30')
        cx, cy = self.mpos
        while (cx, cy) != (x, y):
            cx += max(-HOP, min(HOP, x - cx))
            cy += max(-HOP, min(HOP, y - cy))
            try:
                self.step(f'mouse:{cx},{cy},{b}')
            except RuntimeError as e:
                raise AssertionError(f'{e}: the program read {self.peek("mouse_x", 2)[0]},'
                                     f'{self.peek("mouse_x", 2)[1]}, from {self.mpos}') from None
            self.step('wait:6')
        self.mpos = (x, y)

    def click(self, col, row, frames=300):
        """Press and release on the text cell (col, row)."""
        x, y = col * 2 + 1, row * 8 + 4
        self.mouse_to(x, y)
        for _ in range(2):
            self.step(f'mouse:{x},{y},0')
            self.step('wait:6')
        out = self.step(f'mouse:{x},{y},1').out
        out += self.step('wait:8').out
        out += self.step(f'mouse:{x},{y},0').out
        out += self.step('wait:6').out
        out += self.idle(frames).out         # (kbd_get comes first in event():
        out += self.step('wait:30').out      # the press may be handled after it)
        return out + self.idle(frames).out

    def drag(self, c0, r0, c1, r1):
        """Pressed on (c0, r0), held cell by cell to (c1, r1), released."""
        x, y = c0 * 2 + 1, r0 * 8 + 4
        self.mouse_to(x, y)
        self.step(f'mouse:{x},{y},0')
        self.step('wait:6')
        self.step(f'mouse:{x},{y},1')
        self.step('wait:8')
        while (c0, r0) != (c1, r1):
            c0 += (c1 > c0) - (c1 < c0)
            r0 += (r1 > r0) - (r1 < r0)
            x, y = c0 * 2 + 1, r0 * 8 + 4
            self.step(f'mouse:{x},{y},1')
            self.step('wait:6')
        self.step(f'mouse:{x},{y},0')
        self.step('wait:6')
        self.mpos = (x, y)
        self.idle()
        self.step('wait:30')
        self.idle()

    def b(self, name):
        return self.peek(name, 1)[0]

    def idle(self, frames=300):
        return self.step(f'until:{L["kbd_idle"]:04X}:{frames}')

    def keys(self, text, frames=300):
        """One key at a time, each handled and drawn (kbd_idle) before the next."""
        for c in text:
            k = {'\r': '\\r', '\x1b': '\\e', '\x08': '\\<', '\x15': '\\>', '\x0b': '\\^',
                 '\x0a': '\\v', '\\': '\\\\'}.get(c, c)   # (other control codes: raw)
            self.step('key:' + k)
            self.idle(frames)

    def peek(self, name, n):
        return a2test.Result(self.step(f'peek:{L[name]:04X}:{n}').out).mem(L[name], n)

    def word(self, name):
        b = self.peek(name, 2)
        return b[0] | b[1] << 8

    def screen(self):
        """The 80 x 24 text: odd columns in main $0400, even ones in aux (PAGE2)."""
        main = a2test.Result(self.step('peek:0400:1024').out).mem(0x400, 1024)
        self.step('poke:C055:00')
        aux = a2test.Result(self.step('peek:0400:1024').out).mem(0x400, 1024)
        self.step('poke:C054:00')
        rows = []
        for y in range(24):
            b = (y % 8) * 128 + (y // 8) * 40
            s = ''
            for i in range(40):
                for c in (aux[b + i], main[b + i]):
                    c &= 0x7F
                    s += chr(c) if c >= 0x20 else chr(c + 0x40)
            rows.append(s)
        return rows


# ---------------------------------------------------------------- the song typed
TYPED = ('Z' 'E' '1' '-' 'C'                    # voice 1: C-4, E-5, off, (octave 3) E-3
         + RIGHT + RIGHT + 'A' + UP + RIGHT + '4' + UP + RIGHT + '7'   # row 4: effect A47
         + RIGHT + '[' + '>' + 'Z'              # voice 2, row 0: C-3 with instrument 2
         + ctrl('E') + 'A' + RIGHT + RIGHT + ' ' + RIGHT + RIGHT + '0' + RIGHT + '5' + 'L'
         + UP + '8' + RIGHT + RIGHT + '3' + ESC  # instrument 2: tick 0 vol A + noise, NP 05,
         + '_')                                 # loop 0, shape 8 period 3; speed 5


def default_ins():
    return Instrument([Tick(v) for v in range(15, 7, -1)])


def typed_song():
    tracks = [[Cell() for _ in range(64)] for _ in range(3)]
    t = tracks[0]
    t[0] = Cell(48, 1)
    t[1] = Cell(64, 1)
    t[2] = Cell(OFF)
    t[3] = Cell(40, 1)
    t[4] = Cell(None, None, 1, 0x47)
    tracks[1][0] = Cell(36, 2)
    ins2 = default_ins()
    ins2.ticks[0] = Tick(10, True, True, False, 5)
    ins2.loop = 0
    ins2.env_shape, ins2.env_period = 8, 3
    return Song([Pattern(tracks)], [default_ins(), ins2], [0], speed=5)


def grid_bytes(song, p=0):
    out = bytearray()
    for v in range(song.voices):
        for c in song.patterns[p].tracks[v]:
            note = 0xFF if c.note is None else c.note
            fx = 0 if c.fx is None else c.fx + 1
            out += bytes([note, (c.ins or 0) | fx << 4, c.param])
    return bytes(out)


def bus(out):
    """The AY writes of a play: mb_hush's volumes first, both chips (play
    stops first)."""
    w = ay_writes(out)
    while w and w[0][1] in (8, 9, 10) and w[0][2] == 0:
        w.pop(0)
    return w


def play_check(s, data, ticks, what, start=None):
    """^P (or start(): a click) plays the song: the AY writes on the bus =
    the Python Player's (the tracker's player: AYSONG_VOICES = 6)."""
    s.step('wait:80')                                   # the last audition over
    s.step('storewatch:C400:C4FF')
    if start:
        out = start()
    else:
        out = s.step('key:\x10').out                    # ^P
        out += s.idle().out
    out += s.step(f'wait:{ticks * 6 // 5 + 10}').out
    s.step('unstorewatch')
    _, writes = test_aysong.model(data, ticks, (), 6)
    expected = [(cr >> 4, cr & 15, v) for cr, v in writes]
    got = bus(out)
    assert got[:len(expected)] == expected, f'{what}: AY writes {got[:6]} ... != model {expected[:6]} ...'
    s.keys(' ')
    return len(expected)


GRID_Y, KEYS_Y = 3, 23
HOP = 24                        # pixels a mouse: hop (the card takes ~32 a frame)
MAIN_BAR = ' ^P PLAY  ^R LOOP  SPC STOP  PAT  TAB ORD  ^E INS  ^L LOAD  ^S SAVE  ? HELP'
INS_BAR = ' RETURN LISTEN  ESC BACK  < PREV  > NEXT  ^T NAME  ^O ^Y TICK'


def empty_song(voices=3):
    return Song([Pattern([[Cell() for _ in range(64)] for _ in range(voices)])], [default_ins()], [0],
                voices=voices)


def check_grid(s, song, what, p=0):
    n = song.voices * 192
    got = s.peek('grid', n)
    want = grid_bytes(song, p)
    if got != want:
        bad = next(i for i in range(n) if got[i] != want[i])
        raise AssertionError(f'{what}: grid byte {bad} (voice {bad // 192}, row {bad % 192 // 3}): '
                             f'{got[bad - bad % 3:bad - bad % 3 + 3].hex()} != {want[bad - bad % 3:bad - bad % 3 + 3].hex()}')


def tick_cost(s, n=150):
    """mbt_tick (the interrupt's tick: mbt_asm.s + aysong.asm, 6 voices,
    MB_FAST_WRITE) called n times from the main loop on a fresh snd_play of
    the song encoded (the gate closed: the interrupt only counts): the
    cycles of each call, any interrupt that hit it included."""
    s.idle()
    s.step(f'call:{L["_snd_play"]:04X}:5')
    s.step(f'poke:{L["snd_gate"]:04X}:00')
    cost = []
    for _ in range(n):
        out = s.step(f'call:{L["mbt_tick"]:04X}:5').out
        cost.append(int(out.split('elapsed=')[1].split()[0]))
    s.keys(' ')
    return cost


def six_voices(s, what):
    """^N, Y, Y: a 6-voice song; notes on both chips; the grid, the play."""
    o = s.b('octave')
    s.keys(ctrl('N') + 'YY' + ('=' * (4 - o) if o < 4 else '-' * (o - 4)))
    assert s.b('s_voices') == 6 and s.b('octave') == 4, what
    scr = s.screen()
    assert scr[2].startswith('RW V1 ') and 'V6' in scr[2], scr[2]
    s.keys('Z' + UP + RIGHT * 20 + 'E' + UP + RIGHT * 2 + 'A' + UP + RIGHT + '4' + UP + RIGHT + '7'
           + RIGHT + ']' + '=' + 'Q' + '-')          # voice 6, row 17: C-6
    song = empty_song(6)
    t = song.patterns[0].tracks
    t[0][0] = Cell(48, 1)
    t[4][0] = Cell(64, 1, 1, 0x47)
    t[5][17] = Cell(72, 1)
    check_grid(s, song, what)
    scr = s.screen()
    assert scr[3].startswith('00 C-41...') and 'E-51A47' in scr[3], scr[3]
    data = aysong.encode(song)
    n = play_check(s, data, 120, what)
    assert s.peek('song_buf', len(data)) == data
    return data, n


def run_mouse(work):
    """//e, the card in slot 4, an AppleMouse in slot 2."""
    demo = aysong.encode(aysong.demo())
    with Session(DISK, ['--iie', '--mockingboard', '--mouse', '--mouse-slot=2']) as s:
        s.idle(1500)
        assert s.b('mouse_slot') == 2 and s.b('slot') == 4
        song = empty_song()
        t = song.patterns[0].tracks
        s.click(16, GRID_Y + 4)                         # voice 2, its note, row 4
        assert (s.b('cur_v'), s.b('cur_f'), s.b('cur_row')) == (1, 0, 4)
        s.keys('Z')
        t[1][4] = Cell(48, 1)
        s.click(8, GRID_Y)                              # voice 1's instrument, row 0
        assert (s.b('cur_v'), s.b('cur_f'), s.b('cur_row')) == (0, 1, 0)
        s.keys('2')
        t[0][0] = Cell(None, 2)
        song.instruments.append(default_ins())
        check_grid(s, song, 'clicks')
        print('PASS //e mouse (AppleMouse slot 2, the card in slot 4): a click on a field puts the cursor '
              'there, the note / instrument typed lands in it')

        s.click(56, GRID_Y + 1)                         # instrument 2
        assert s.b('cur_ins') == 2
        s.click(56, GRID_Y + 1)                         # again: its editor
        assert 'INSTRUMENT EDITOR' in s.screen()[0]
        s.click(7, 6 + 2)                               # tick 2's volume
        s.keys('9')
        s.click(INS_BAR.index('ESC'), KEYS_Y)
        scr = s.screen()
        assert 'INSTRUMENT EDITOR' not in scr[0] and '>2' in scr[GRID_Y + 1], scr[GRID_Y + 1]
        song.instruments[1].ticks[2].vol = 9
        assert s.peek('s_ins', 148 * 2)[148 + 4 + 2] == 0x19
        print('PASS //e mouse: instrument 2 clicked (selected), clicked again (its editor), a tick\'s '
              'volume clicked and typed, the bar\'s ESC BACK')

        s.drag(4, GRID_Y, 16, GRID_Y + 4)               # voices 1-2, rows 0-4
        got = (s.b('sel_on'), s.b('sel_v'), s.b('sel_r'), s.b('cur_v'), s.b('cur_row'))
        assert got == (1, 0, 0, 1, 4), got
        s.keys(ctrl('C'))
        assert (s.b('clip_v'), s.b('clip_r')) == (2, 5)
        s.click(16, GRID_Y + 10)                        # voice 2, row 10
        assert (s.b('sel_on'), s.b('cur_v'), s.b('cur_row')) == (0, 1, 10)
        s.keys(ctrl('V'))
        for v in range(2):
            for r in range(5):
                t[1 + v][10 + r] = Cell(**vars(t[v][r]))
        check_grid(s, song, 'drag, ^C, click, ^V')
        s.keys(ctrl('B') + DOWN * 4 + RIGHT * 5 + "'")   # voices 2-3, rows 10-14: + 1
        t[2][14] = Cell(49, 1)
        check_grid(s, song, "^B, ' (+1)")
        s.keys('"')
        t[2][14] = Cell(61, 1)
        check_grid(s, song, '" (+12)')
        s.keys(ctrl('Z'))
        t[2][14] = Cell(49, 1)
        check_grid(s, song, '^Z')
        s.keys(ctrl('Z'))
        t[2][14] = Cell(61, 1)
        check_grid(s, song, '^Z again (redo)')
        s.keys(ctrl('X'))
        saved = [[Cell(**vars(t[v][r])) for r in range(10, 15)] for v in (1, 2)]
        for v in (1, 2):
            for r in range(10, 15):
                t[v][r] = Cell()
        check_grid(s, song, '^X')
        s.keys(ctrl('Z') + ESC)
        for v in (1, 2):
            for r in range(10, 15):
                t[v][r] = saved[v - 1][r - 10]
        check_grid(s, song, '^X undone')
        assert s.b('sel_on') == 0
        print('PASS //e mouse blocks: a drag marks voices 1-2 rows 0-4, ^C, a click, ^V pastes it; ^B + '
              'arrows mark a block, \' and " transpose it, ^Z undoes, ^Z redoes, ^X cuts, ^Z: the grids = '
              'the Python song')

        data = aysong.encode(song)
        n = play_check(s, data, 60, 'mouse PLAY', start=lambda: s.click(MAIN_BAR.index('PLAY'), KEYS_Y))
        s.click(MAIN_BAR.index('PLAY'), KEYS_Y)
        assert s.b('playing') == 1
        s.click(MAIN_BAR.index('STOP'), KEYS_Y)
        assert s.b('playing') == 0
        print(f'PASS //e mouse bar: PLAY ({n} AY writes of 60 ticks = the Python Player), STOP')

        s.click(MAIN_BAR.index('ORD'), KEYS_Y)
        assert s.b('focus') == 1
        s.keys('I')
        assert (s.b('s_npat'), s.b('s_nord'), s.peek('s_order', 2), s.b('ord_cur')) == (2, 2, b'\0\1', 1)
        s.keys('C')
        assert (s.b('s_npat'), s.peek('s_order', 2)) == (3, b'\0\2')
        s.click(43, GRID_Y)                             # entry 0
        assert (s.b('ord_cur'), s.b('cur_pat')) == (0, 0)
        check_grid(s, song, 'entry 0 clicked: pattern 0')
        s.click(43, GRID_Y + 1)
        s.keys('DY')                                    # pattern 2 and its entry out
        assert (s.b('s_npat'), s.b('s_nord'), s.b('s_order'), s.b('ord_cur')) == (2, 1, 0, 0)
        s.click(MAIN_BAR.index('PAT'), KEYS_Y)
        assert s.b('focus') == 0
        check_grid(s, song, 'after D')
        print('PASS //e mouse order list: ORD, I (a new pattern inserted), C (cloned), entries clicked, '
              'D Y (the pattern and its entry deleted), PAT')

        s.click(MAIN_BAR.index('HELP'), KEYS_Y)
        assert 'HELP 1/2' in s.screen()[0]
        s.keys(' ')
        scr = s.screen()
        assert 'HELP 2/2' in scr[0] and scr[2].startswith('BLOCKS'), scr[:3]
        s.keys(' ')
        assert '(untitled)' in s.screen()[0] and 'HELP' not in s.screen()[0]
        s.click(MAIN_BAR.index('LOAD'), KEYS_Y)
        s.keys('Y')
        assert 'DEMO.AYS' in s.screen()[2]
        s.click(3, 2, 600)                             # the first name: chosen, loaded
        assert s.word('song_len') == len(demo) and s.peek('song_buf', len(demo)) == demo, 'DEMO.AYS loaded'
        print('PASS //e mouse: HELP (both pages), LOAD and a click on DEMO.AYS (loaded)')


def find_copy(nonce, since):
    for path in glob.glob('/tmp/a2shot-*.po'):
        try:
            if os.path.getmtime(path) >= since - 2 and nonce in Path(path).read_bytes():
                return Path(path)
        except OSError:
            continue
    raise AssertionError('the private copy of the disk was not found')


def run_iie(work):
    nonce = secrets.token_bytes(32)
    disk = work / 'mbt.po'
    a2test.prodos_variant(DISK, disk, replace={'NONCE#060000': nonce})
    other = work / 'other.po'
    a2test.prodos_variant(DISK, other, drop=('DEMO.AYS',), volume='OTHER')
    demo = aysong.encode(aysong.demo())
    shipped = a2test.prodos_files(DISK)['DEMO.AYS'][2]
    assert shipped == demo, 'DEMO.AYS is aysong.py --demo'
    t0 = time.time()
    with Session(disk, ['--iie', '--mockingboard']) as s:
        s.idle(1500)
        scr = s.screen()
        assert 'MB TRACKER' in scr[0] and 'MOCKINGBOARD S4' in scr[0], scr[0]
        assert 'VOICE 1' in scr[2] and 'ORDER' in scr[2] and scr[3].startswith('00  --- . ...'), scr[2:4]
        print('PASS //e boot: title bar, Mockingboard in slot 4, the grid on both text pages')

        s.keys(TYPED)
        song = typed_song()
        assert s.peek('grid', 576) == grid_bytes(song), 'the grid holds the cells typed'
        scr = s.screen()
        assert scr[3].startswith('00  C-4 1 ... | C-3 2 ...') and scr[7].startswith('04  --- . A47'), scr[3:8]
        data = aysong.encode(song)
        n = play_check(s, data, 60, '//e typed song')
        assert s.word('song_len') == len(data) and s.peek('song_buf', len(data)) == data, \
            'the AYS bytes are aysong.encode() of the same song'
        print(f'PASS //e editing: piano keys, note off, effect A47, instrument editor, speed: grid and '
              f'{len(data)} AYS bytes = aysong.encode(); ^P: {n} AY writes of 60 ticks = the Python Player')

        s.keys(ctrl('S') + DEL * 8 + 'test' + RET)
        assert 'SAVED TEST.AYS' in s.screen()[22]
        s.step('insert:' + str(other))                   # POM2 writes the image back
        image = find_copy(nonce, t0)
        files = a2test.prodos_files(image.read_bytes())
        saved = files['TEST.AYS'][2]
        assert files['TEST.AYS'][0] == 0x06, 'a BIN file'
        assert saved == data and aysong.encode(aysong.decode(saved)) == saved, 'TEST.AYS round trip'
        print(f'PASS //e ^S: TEST.AYS on the disk ({len(saved)} bytes) decoded by aysong.py = the song')

        s.step('insert:' + str(disk))
        s.keys(ctrl('L'))
        scr = s.screen()
        assert 'DEMO.AYS' in scr[2], scr[2]
        s.keys(RET, 600)
        assert s.word('song_len') == len(demo) and s.peek('song_buf', len(demo)) == demo, 'DEMO.AYS loaded'
        scr = s.screen()
        assert 'AYS demo' in scr[0] and 'LOADED DEMO.AYS' in scr[22], (scr[0], scr[22])
        assert scr[3].startswith('00  C-4 1 ...'), scr[3]
        s.keys('_+')                                     # an edit and its undo: encoded again
        assert s.word('song_len') == 0
        n = play_check(s, demo, 150, '//e DEMO.AYS')
        assert s.peek('song_buf', len(demo)) == demo, 'DEMO.AYS encoded again: the same bytes'
        print(f'PASS //e ^L: DEMO.AYS listed and loaded (the shipped bytes), encoded again identical, '
              f'{n} AY writes of 150 ticks = the Python Player')


def run_iic(work):
    with Session(DISK, ['--iic', '--mockingboard']) as s:
        s.idle(1500)
        scr = s.screen()
        assert 'MOCKINGBOARD S4' in scr[0], scr[0]
        s.keys(TYPED)
        song = typed_song()
        assert s.peek('grid', 576) == grid_bytes(song)
        data = aysong.encode(song)
        n = play_check(s, data, 60, '//c typed song')
        assert s.peek('song_buf', len(data)) == data
        print(f'PASS //c with the Mockingboard 4c: the same song typed, encoded, {n} AY writes = the model')
        assert s.b('mouse_slot') == 0, 'the 4c hides the //c mouse firmware'
        data, n = six_voices(s, '//c 6 voices')
        print(f'PASS //c 6 voices (both chips of the 4c): ^N Y Y, notes on voices 1, 5 (A47), 6, the grid; '
              f'{n} AY writes of 120 ticks = the Player (max_voices 6); no mouse (the 4c answers $C400)')


def run_six(work):
    """//e with the card: a 6-voice song typed and played; the tick's cost."""
    with Session(DISK, ['--iie', '--mockingboard']) as s:
        s.idle(1500)
        data, n = six_voices(s, '//e 6 voices')
        cost = tick_cost(s)
        assert max(cost) <= 5600, max(cost)
        wg = a2test.prodos_files(DISK)['WG.AYS'][2]
        s.keys(ctrl('N') + 'YN' + ctrl('L') + DOWN + RET, 600)
        assert s.word('song_len') == len(wg) and s.peek('song_buf', len(wg)) == wg, 'WG.AYS loaded'
        assert 'LOADED WG.AYS' in s.screen()[22]
        m = play_check(s, wg, 200, 'WG.AYS')
        print(f'PASS //e 6 voices: the grid, {n} AY writes of 120 ticks = the Player (max_voices 6); '
              f'mbt_tick (6-voice player, fast writes): first {cost[0]} cycles, then max {max(cost[1:])}, '
              f'mean {sum(cost) // len(cost)}; WG.AYS (pt3import.py of WARGALAGA II\'s PT3) loaded, '
              f'{m} AY writes of 200 ticks = the Player')


def run_iic_mouse(work):
    """//c without a card: its own mouse."""
    with Session(DISK, ['--iic']) as s:
        s.sync = False                      # (the //c reads it on every pass)
        s.idle(1500)
        assert s.b('mouse_slot') == 4 and s.b('slot') == 0
        s.click(28, GRID_Y + 6)                         # voice 3, note, row 6
        assert (s.b('cur_v'), s.b('cur_f'), s.b('cur_row')) == (2, 0, 6)
        s.keys('Q')
        song = empty_song()
        song.patterns[0].tracks[2][6] = Cell(60, 1)
        check_grid(s, song, '//c click')
        s.click(MAIN_BAR.index('HELP'), KEYS_Y)
        assert 'HELP 1/2' in s.screen()[0]
        s.keys('  ')
        s.click(MAIN_BAR.index('ORD'), KEYS_Y)
        assert s.b('focus') == 1
        print('PASS //c without a card, its own mouse: a click on a cell, a note typed there; HELP, ORD')


def run_nocard(work):
    with Session(DISK, ['--iie']) as s:
        s.idle(1500)
        scr = s.screen()
        assert 'NO MOCKINGBOARD' in scr[0] and 'NO MOCKINGBOARD' in scr[22], (scr[0], scr[22])
        s.keys('Z' + ctrl('P'))
        assert s.peek('grid', 3) == bytes([48, 1, 0])
        assert 'PLAYBACK IS OFF' in s.screen()[22]
        s.keys('\t=' + ctrl('O') + '-L\t')       # order list: a new pattern, an entry, the loop
        assert s.peek('s_order', 2) == b'\x01\x00' and s.peek('s_nord', 1)[0] == 2
        assert s.peek('s_loop', 1)[0] == 1 and s.peek('s_npat', 1)[0] == 2
        assert s.peek('grid', 3) == bytes([48, 1, 0]), 'the grid shows entry 1: pattern 0, its note'
        s.keys(ctrl('Q'))
        s.step('press:y')
        s.step(f'until:{L["prodos_quit"]:04X}:300')    # crt0's exit, /RAM rebuilt
        print('PASS //e without a card: NO MOCKINGBOARD, a note typed, ^P only says so; order list: '
              'new pattern, inserted entry, pattern number, loop; ^Q Y: back to ProDOS\'s QUIT')


def main():
    if not a2test.have_a2shot('test_mbt (MB TRACKER)'):
        return
    with tempfile.TemporaryDirectory(prefix='mbt-') as tmp:
        work = Path(tmp)
        run_iie(work)
        run_mouse(work)
        run_six(work)
        run_iic(work)
        run_iic_mouse(work)
        run_nocard(work)


if __name__ == '__main__':
    main()
