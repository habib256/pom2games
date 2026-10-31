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
No card: "NO MOCKINGBOARD", editing still works, ^P only says so."""
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
    for v in range(3):
        for c in song.patterns[p].tracks[v]:
            note = 0xFF if c.note is None else c.note
            fx = 0 if c.fx is None else c.fx + 1
            out += bytes([note, (c.ins or 0) | fx << 4, c.param])
    return bytes(out)


def bus(out):
    """The AY writes of a play: mb_hush's volumes first (play stops first)."""
    w = ay_writes(out)
    while w and w[0][1] in (8, 9, 10) and w[0][2] == 0 and w[0][0] == 0:
        w.pop(0)
    return w


def play_check(s, data, ticks, what):
    s.step('wait:80')                                   # the last audition over
    s.step('storewatch:C400:C4FF')
    out = s.step('key:\x10').out                        # ^P
    out += s.idle().out
    out += s.step(f'wait:{ticks * 6 // 5 + 10}').out
    s.step('unstorewatch')
    _, writes = test_aysong.model(data, ticks, (), 3)
    expected = [(cr >> 4, cr & 15, v) for cr, v in writes]
    got = bus(out)
    assert got[:len(expected)] == expected, f'{what}: AY writes {got[:6]} ... != model {expected[:6]} ...'
    s.keys(' ')
    return len(expected)


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
        run_iic(work)
        run_nocard(work)


if __name__ == '__main__':
    main()
