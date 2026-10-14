#!/usr/bin/env python3
"""SAVE and RESTORE (lot 9, src/save.s, docs/SAVE.md) on the POM2 IIe core.

Main session, on a private copy of dist/NEOWILDERNESS.po (a nonce in the
unused tail of NEOWILD.S5 finds it again after ejection):
  - a Sierra journey (walk, eat, drink, get and drop an item, rest into the
    night), then SAVE 1 (empty game: no question): message, MLI calls (the
    module read, then OPEN, READ of the header, SET_MARK, WRITE, CLOSE),
    ProDOS bitmap, RESET vector and the I flag unchanged;
  - the journey continues (sleep, walk, eat): reference continuation;
  - SAVE 1 again: the question names the game, N keeps it (nothing written);
  - RESTORE 1: every byte of the saved ranges (src/save.s sv_ranges: the
    journey) equals the dump taken right after SAVE, the DHGR view (both
    banks, logical rows 0-159: landscape, sky, HUD) equals the view at SAVE,
    then the same continuation gives the same state, byte for byte;
  - refusals that change nothing: game 3 empty, game 9, ESC;
  - QUIT, the Burma: RESTORE 1 answers "GAME 1: SIERRA NEVADA ONLY.";
  - QUIT, the Sierra again: RESTORE 1 across the restart = the dump at SAVE;
  - ejection: NEOWILD.S1 read back from the image with read_volume.py:
    header, Fletcher-16, state = the dump at SAVE; still a sapling, no block
    allocated, free blocks unchanged.
Faults, each on its own volume (copies of the image above): a damaged game
(one state byte changed), another build (header build id), NEOWILD.S4 and
NEOWILD.SAV missing (directory entries renamed), and the write-protected WOZ
(tools/po2woz.py: ProDOS answers a real $2B). None changes the journey.
A daytime SAVE/RESTORE compares the landscape too.
Coverage: every label of GDATA is in a saved range or in the documented
exclusions (module cache, parser line, constant tables), and the constant
tables equal build/wildgame.bin.
Finally test_prodos.exit_state runs with SAVE 1 and RESTORE 1 played before
QUIT: zero page, bitmap and RESET vector equal to the loader entry at the
MLI QUIT.
"""
import glob
import os
import re
import secrets
import sys
import tempfile
import time
from pathlib import Path

from common import HERE, L, DISK, MENU_SKIP, a2test, text_screen, dhgr_view, result_text, fp

sys.path.insert(0, str(HERE.parent / 'dev/tools/prodos'))
from read_volume import Image  # noqa: E402
from po2woz import po_to_woz    # noqa: E402

LIMIT = 40000
STOP = f'until:{L["idle"]:04X},{L["keyboard_wait"]:04X}:{LIMIT}'
CPU_HZ = a2test.CPU_HZ
OPEN, READ, WRITE, CLOSE, SET_MARK = 0xC8, 0xCA, 0xCB, 0xCC, 0xCE
GAMES = 5
SV_HEAD = 32

# GDATA labels left out of the saved image (src/save.s sv_ranges): the module
# cache bookkeeping, the parser's line and the tables the game never writes.
VOLATILE = {'overlay_current', 'overlay_wanted', 'overlay_reads', 'sim_loaded', 'sim_quiet',
            'inbuf', 'nounbuf'}
CONSTANT = {'it_kcal', 'verbs', 'verb_lo', 'verb_hi', 'card_lo', 'card_hi', 'cdef_lo',
            'cdef_hi', 'ctol_lo', 'ctol_hi', 'm_dead_travel', 'm_goal_travel', 'm_weak_travel'}


# Saved, but rewritten by the redraw that follows RESTORE (show_view): the
# floating point scratch of the last computation and the scene bookkeeping
# of the last picture. The continuation after RESTORE compares them too.
DERIVED = {'t1', 't2', 't3', 't4', 't5', 'scene_drawn', 'scene_cache_valid', 'scene_cache_pos',
           'scene_cache_animal', 'scene_cache_drawn', 'scene_cache_asset'}


def segments():
    text = (HERE / 'build/wild.map').read_text()
    return {n: (int(a, 16), int(b, 16) + 1) for n, a, b in
            re.findall(r'^(\w+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+[0-9A-F]{6}', text, re.M)}


SEG = segments()


def ranges():
    """sv_ranges of the module: [(address, length)], read from wildsav.bin."""
    module = (HERE / 'build/wildsav.bin').read_bytes()
    at, out = L['sv_ranges'] - 0x9600, []
    while True:
        address = int.from_bytes(module[at:at + 2], 'little')
        if not address:
            return out
        out.append((address, int.from_bytes(module[at + 2:at + 4], 'little')))
        at += 4


RANGES = ranges()
STATE = sum(n for _, n in RANGES)


def coverage():
    lo, hi = SEG['GDATA']
    names = sorted((a, n) for n, a in L.items() if lo <= a < hi and not n.startswith('__'))
    covered = lambda a: any(s <= a < s + n for s, n in RANGES)
    missing = [n for a, n in names if not covered(a) and n not in VOLATILE | CONSTANT]
    assert not missing, f'GDATA labels neither saved nor excluded: {missing}'
    stray = [n for a, n in names if covered(a) and n in VOLATILE | CONSTANT]
    assert not stray, stray
    image = (HERE / 'build/wildgame.bin').read_bytes()
    spans = []
    for k, (a, n) in enumerate(names):
        if n in CONSTANT:
            end = names[k + 1][0] if k + 1 < len(names) else hi
            spans.append((n, a, end - a, image[a - 0x4000:end - 0x4000]))
    covered_bytes = sum(n for a, n in RANGES if lo <= a < hi)
    print(f'  {len(names)} GDATA labels: {covered_bytes} bytes saved, '
          f'{len(VOLATILE)} volatile and {len(CONSTANT)} constant labels left out; '
          f'slot image {SV_HEAD} + {STATE} bytes')
    return spans


class Game:
    def __init__(self, s):
        self.s = s

    def peek(self, address, n):
        return self.s.step(f'peek:{address:04X}:{n}').dumps[0]

    def word(self, name):
        d = self.peek(L[name], 2)
        return d[0] | d[1] << 8

    def cycles(self):
        out = self.s.step(STOP).out
        return int(re.findall(r'cycles=(\d+)', out)[-1]), out.rstrip().endswith(f'PC={L["keyboard_wait"]:04X}')

    def type(self, line, answer=None):
        """Type a command; answer the Y/N question or the number prompt with
        `answer`; acknowledge other key waits. Returns (seconds, MLI calls)."""
        calls = self.word('mli_calls')
        self.s.step(f'key:{line}')
        self.s.step('press:\\r')
        out = self.s.step(L.until('do_command', LIMIT)).out
        start = int(re.findall(r'cycles=(\d+)', out)[-1])
        while True:
            now, waiting = self.cycles()
            if not waiting:
                break
            if answer is not None:
                self.s.step(f'key:{answer}')
                answer = None
                continue
            else:
                self.s.step('press: ')
                self.s.step('wait:1')
        return (now - start) / CPU_HZ, self.word('mli_calls') - calls

    def ask(self, line):
        """Type a command and stop at its question (keyboard wait)."""
        self.s.step(f'key:{line}')
        self.s.step('press:\\r')
        self.s.step(L.until('do_command', LIMIT))
        _, waiting = self.cycles()
        assert waiting, f'{line}: no question'
        return self.result()

    def answer(self, key):
        self.s.step(f'press:{key}')
        self.s.step('wait:1')
        while True:
            _, waiting = self.cycles()
            if not waiting:
                return
            # Let the end module read the key and reach its next wait (the
            # ranked journey of a scenario asks for a name, then saves):
            # a shorter wait finds the same wait loop again, for ever.
            self.s.step('press: ')
            self.s.step('wait:400')

    def result(self):
        text = result_text(text_screen(self.s.step('peek:0400:1024').texts[0]))
        return '\n'.join(row.rstrip() for row in text.split('\n'))

    def state(self):
        return b''.join(self.peek(a, n) for a, n in RANGES)

    def view(self):
        return dhgr_view(self.s.step('peek:2000:8192').dumps[0])

    def guards(self):
        return self.peek(0xBF58, 24) + self.peek(0x03F2, 3)

    def menu(self, region):
        """QUIT (the score screen: ESC, a key), then the start menu: region."""
        self.s.step('key:QUIT\\r')
        self.s.step('wait:30')
        self.s.step('key:Y')
        out = self.s.step(f'until:{L["hof_key_wait"]:04X},{L["menu_key"]:04X}:{LIMIT}').out
        if out.rstrip().endswith(f'PC={L["hof_key_wait"]:04X}'):
            # A ranked scenario journey asks for a name: ESC = "NOT RECORDED",
            # then any key restarts the loader (as tests/test_hof_game.py does
            # with key:, one key per keyboard wait); a free journey goes
            # straight to its key wait. Without NEOWILD.END (the copy of
            # main()), QUIT goes straight to the menu.
            self.s.step('key:\x1b')
            out = self.s.step(f'until:{L["hof_key_wait"]:04X},{L["menu_key"]:04X}:{LIMIT}').out
            if out.rstrip().endswith(f'PC={L["hof_key_wait"]:04X}'):
                self.s.step('key: ')
                self.s.step(L.until('menu_key', LIMIT))
        self.s.step(f'key:{ {"2": "1", "3": "3"}[region] }\\r')
        self.s.step(L.until('idle', LIMIT))
        assert self.peek(L['region_number'], 1)[0] == int(region)


def label_spans(names):
    lo, hi = SEG['GDATA']
    found = sorted((a, n) for n, a in L.items() if lo <= a < hi and not n.startswith('__'))
    spans = set()
    for k, (a, n) in enumerate(found):
        if n in names:
            end = found[k + 1][0] if k + 1 < len(found) else hi
            spans |= set(range(a, end))
    return spans


DERIVED_BYTES = label_spans(DERIVED)


def differing(a, b, skip=frozenset()):
    out, k = [], 0
    for address, n in RANGES:
        for i in range(n):
            if a[k + i] != b[k + i] and address + i not in skip:
                out.append(address + i)
        k += n
    return out


def diff(a, b, skip=frozenset()):
    return [f'{x:04X}' for x in differing(a, b, skip)[:12]]


def fletcher16(data):
    """src/save.s sv_checksum: two 8-bit sums, each with an end-around carry."""
    s1 = s2 = 0
    for b in data:
        t = s1 + b
        s1 = (t & 255) + (t >> 8)
        s1 &= 255
        t = s1 + s2
        s2 = ((t & 255) + (t >> 8)) & 255
    return s1, s2


def present(img):
    return {bytes(e[1:1 + (e[0] & 15)]).decode('ascii') for e in img.entries(2) if e[0] & 15}


def entry(img, name):
    return next(e for e in img.entries(2) if e[1:1 + (e[0] & 15)] == name.encode())


def find_copy(nonce, since):
    for path in glob.glob('/tmp/a2shot-*.po'):
        try:
            if os.path.getmtime(path) >= since - 2 and nonce in Path(path).read_bytes():
                return Path(path)
        except OSError:
            continue
    raise AssertionError('private copy of the volume not found')


def file_blocks(img, e):
    """Data blocks of a seedling or sapling file, in order."""
    key = int.from_bytes(e[0x11:0x13], 'little')
    if e[0] >> 4 == 1:
        return [key]
    index = img.block(key)
    eof = int.from_bytes(e[0x15:0x18], 'little')
    return [index[n] | index[256 + n] << 8 for n in range(-(-eof // 512))]


def patch_file(image, name, offset, data):
    img = Image(bytes(image))
    blocks = file_blocks(img, entry(img, name))
    for i, byte in enumerate(data):
        at = blocks[(offset + i) // 512] * 512 + (offset + i) % 512
        image[at] = byte


def rename(image, old, new):
    img = Image(bytes(image))
    e = entry(img, old)
    at = bytes(image).index(e)
    assert len(new) == len(old)
    image[at + 1:at + 1 + len(new)] = new.encode()


def main_session(work, constants):
    base = bytearray(DISK.read_bytes())
    nonce = secrets.token_bytes(32)
    # The last game that fits on the volume (S5 on 800 KB, S3 on the 140 KB
    # image: build/layout.json) stays empty: no magic, a nonce in its tail.
    last = max(n for n in present(Image(bytes(base))) if n.startswith('NEOWILD.S') and n[9:].isdigit())
    patch_file(base, last, 200, nonce)
    disk = work / 'save.po'
    disk.write_bytes(base)
    before = Image(bytes(base))
    t0 = time.time()
    timings = {}
    with a2test.Session(disk, timeout=900) as s:
        g = Game(s)
        s.step(L.until('idle', LIMIT))
        assert g.peek(L['region_number'], 1)[0] == 2
        guards = g.guards()
        journey = ['WALK 1 H', 'EAT CHEESE 4 OZ', 'DRINK WATER 4 OZ', 'GET KNIFE', 'WALK 1 H',
                   'DROP CHEESE', 'REST 9 H', 'WAIT 4 H']
        for line in journey:
            _, calls = g.type(line)
            assert calls == 0, (line, 'MLI call outside SAVE/RESTORE')
        hour = fp(g.peek(L['s_hour'], 5))
        night = g.peek(L['night'], 1)[0]
        assert night, ('the save is taken at night', hour)
        knife = g.state()
        seconds, calls = g.type('SAVE', answer='1\\r')
        timings['SAVE (prompt, empty game)'] = seconds
        assert g.result().startswith('GAME 1 SAVED.'), g.result()
        assert calls == 3 + 5, ('SAVE: NEOWILD.SAV, then OPEN READ SET_MARK WRITE CLOSE', calls)
        assert g.guards() == guards, 'bitmap and RESET vector restored after SAVE'
        saved, view = g.state(), g.view()
        assert saved == knife, ('SAVE changed the journey', diff(knife, saved))
        print(f'  journey to {hour:.2f} h (night), SAVE 1: "GAME 1 SAVED.", {calls} MLI calls, '
              f'{seconds:.2f} s; bitmap and RESET vector unchanged: OK')

        later = ['SLEEP 8 H', 'WALK 1 H', 'EAT CHEESE 2 OZ', 'LOOK R']
        for line in later:
            assert g.type(line)[1] == 0
        reference = g.state()
        assert reference != saved

        question = g.ask('SAVE 1')
        hours = int(fp(saved[sum(n for a, n in RANGES[:2]) + (L['s_elap'] - L['s_hour']):][:5]))
        want = f'GAME 1: SIERRA NEVADA, {hours} H.\nREPLACE IT? Y: YES   N/ESC: NO'
        assert question.startswith(want), (question, want)
        g.answer('N')
        assert g.result().startswith('GAME 1 KEPT. NOT SAVED.'), g.result()
        assert g.state() == reference
        print(f'  SAVE 1 again: "{want.splitlines()[0]}" + question, N keeps it: OK')

        seconds, calls = g.type('RESTORE 1')
        timings['RESTORE 1 (view rebuilt)'] = seconds
        assert g.result().startswith('GAME 1 RESTORED.'), g.result()
        assert calls == 3 + 3, ('RESTORE: NEOWILD.SAV, then OPEN READ CLOSE', calls)
        assert g.guards() == guards
        restored = g.state()
        assert not differing(saved, restored, DERIVED_BYTES), ('RESTORE', diff(saved, restored))
        assert g.view() == view, 'the view after RESTORE differs from the view at SAVE'
        assert g.peek(L['stars_stale'], 1) == b'\x00', 'the star list of the restored night was computed'
        print(f'  RESTORE 1: {STATE} state bytes and the DHGR view (rows 0-159, both banks) equal '
              f'to SAVE time, {calls} MLI calls, {seconds:.2f} s: OK')
        for line in later:
            assert g.type(line)[1] == 0
        again = g.state()
        assert again == reference, ('continuation after RESTORE', diff(reference, again))
        print(f'  the same {len(later)} commands after RESTORE: identical journey, byte for byte: OK')

        for line, answer, want in (('RESTORE 3', None, 'GAME 3 IS EMPTY.'),
                                   ('RESTORE 9', None, 'GAMES ARE NUMBERED 1 TO 5.'),
                                   ('SAVE', '\\e', 'ACTION CANCELLED.'),
                                   ('RESTORE', '\\e', 'ACTION CANCELLED.')):
            before_state = g.state()
            g.type(line, answer)
            assert g.result().startswith(want), (line, g.result())
            assert g.state() == before_state, line
            assert g.guards() == guards
        print('  empty game, game 9, ESC at both prompts: message, nothing changed: OK')

        seconds, calls = g.type('SAVE 2')
        timings['SAVE 2 (inline number)'] = seconds
        assert g.result().startswith('GAME 2 SAVED.') and calls == 8
        second = g.state()

        g.menu('3')
        burma = g.state()
        seconds, calls = g.type('RESTORE 1')
        assert g.result().startswith('GAME 1: SIERRA NEVADA ONLY.'), g.result()
        assert g.state() == burma and g.guards() == guards
        print('  Burma: RESTORE 1 answers "GAME 1: SIERRA NEVADA ONLY.", nothing changed: OK')

        g.menu('2')
        seconds, calls = g.type('RESTORE 1')
        assert g.result().startswith('GAME 1 RESTORED.')
        assert not differing(saved, g.state(), DERIVED_BYTES), ('restart', diff(saved, g.state()))
        assert g.view() == view
        print('  QUIT, start menu, the Sierra again: RESTORE 1 = the dump at SAVE, same view: OK')
        s.step('insert:' + str(work / 'other.po'))
        image = find_copy(nonce, t0).read_bytes()
    img = Image(image)
    for game, state in ((1, saved), (2, second)):
        e = entry(img, f'NEOWILD.S{game}')
        data = img.read(e)
        assert e[0] >> 4 == 2 and len(data) == SV_HEAD + STATE, 'a sapling of fixed length'
        assert entry(before, f'NEOWILD.S{game}')[0x11:0x18] == e[0x11:0x18], 'same blocks, same length'
        head = data[:SV_HEAD]
        module = (HERE / 'build/wildsav.bin').read_bytes()
        assert head[:6] == b'NW\x01\x02\x04\x00', head[:6].hex()
        assert head[8:10] == STATE.to_bytes(2, 'little')
        s1, s2 = fletcher16(data[SV_HEAD:])
        assert (head[10], head[11]) == (s1, s2), 'checksum'
        assert head[16:29] == b'SIERRA NEVADA'
        assert data[SV_HEAD:] == state, f'game {game}: the file holds the state at SAVE'
        build_id = Image(DISK.read_bytes())
        sav = build_id.read(entry(build_id, 'NEOWILD.SAV'))
        at = L['sv_build'] - 0x9600
        assert head[6:8] == sav[at:at + 2] != b'\0\0', 'build id of the volume'
    assert img.free_blocks() == before.free_blocks(), 'no block allocated'
    print(f'  NEOWILD.S1/S2 read back with read_volume.py: header, Fletcher-16 and state = the '
          f'dumps at SAVE; sapling, {img.free_blocks()} free blocks unchanged: OK')
    return bytearray(image), saved, timings


def fault(work, image, label, title, line, want):
    disk = work / f'{label}.po'
    disk.write_bytes(image)
    with a2test.Session(disk, timeout=900) as s:
        g = Game(s)
        s.step(L.until('idle', LIMIT))
        g.type('WALK 1 H')
        guards, state = g.guards(), g.state()
        _, calls = g.type(line)
        assert g.result().startswith(want), (title, g.result())
        assert g.state() == state, (title, 'the journey changed')
        assert g.guards() == guards
    print(f'  {title}: "{want}", nothing changed, bitmap restored: OK')


def faults(work, image):
    damaged = bytearray(image)
    patch_file(damaged, 'NEOWILD.S1', SV_HEAD + 100, [Image(bytes(image)).read(
        entry(Image(bytes(image)), 'NEOWILD.S1'))[SV_HEAD + 100] ^ 1])
    fault(work, damaged, 'damaged', 'one state byte changed', 'RESTORE 1', 'GAME 1 IS DAMAGED.')
    other = bytearray(image)
    patch_file(other, 'NEOWILD.S2', 6, b'\x34\x12')
    fault(work, other, 'other', 'another build id', 'RESTORE 2',
          'GAME 2 WAS SAVED BY ANOTHER VERSION.')
    missing = bytearray(image)
    if 'NEOWILD.S4' in present(Image(bytes(image))):
        rename(missing, 'NEOWILD.S4', 'NEOWILD.X4')
    fault(work, missing, 'missing', 'NEOWILD.S4 missing', 'SAVE 4', 'NEOWILD.S4 IS MISSING.')
    nomodule = bytearray(image)
    rename(nomodule, 'NEOWILD.SAV', 'NEOWILD.XAV')
    fault(work, nomodule, 'nomodule', 'NEOWILD.SAV missing', 'SAVE 1', 'NEOWILD.SAV CANNOT BE READ.')
    woz = work / 'protected.woz'
    woz.write_bytes(po_to_woz(DISK.read_bytes(), write_protected=True))
    with a2test.Session(woz, iie=True, timeout=900) as s:
        s.dhgr = True                   # 80-column text and DHGR page peeks
        for step in MENU_SKIP:
            s.step(step)
        g = Game(s)
        s.step(L.until('idle', LIMIT))
        guards, state = g.guards(), g.state()
        g.type('SAVE 3')
        assert g.result().startswith('DISK WRITE-PROTECTED: NOT SAVED.'), g.result()
        assert g.state() == state and g.guards() == guards
        g.type('RESTORE 3')
        assert g.result().startswith('GAME 3 IS EMPTY.'), g.result()
    print('  write-protected WOZ: SAVE 3 "DISK WRITE-PROTECTED: NOT SAVED." (real $2B), '
          'RESTORE 3 still reads: OK')


def day_view(work):
    """By day: the landscape after RESTORE equals the landscape at SAVE."""
    disk = work / 'day.po'
    disk.write_bytes(DISK.read_bytes())
    with a2test.Session(disk, timeout=900) as s:
        g = Game(s)
        s.step(L.until('idle', LIMIT))
        g.type('WALK 1 H')
        assert not g.peek(L['night'], 1)[0]
        g.type('SAVE 1')
        saved, view = g.state(), g.view()
        for line in ('LOOK R', 'WALK 1 H', 'EAT CHEESE 4 OZ'):
            g.type(line)
        g.type('RESTORE 1')
        assert g.result().startswith('GAME 1 RESTORED.'), g.result()
        assert not differing(saved, g.state(), DERIVED_BYTES), diff(saved, g.state())
        assert g.view() == view, 'daytime view after RESTORE'
    print('  by day: SAVE, LOOK R, WALK, EAT, RESTORE: same state, same landscape: OK')


def constants_unchanged(constants):
    with a2test.Session(DISK, timeout=900) as s:
        g = Game(s)
        s.step(L.until('idle', LIMIT))
        for line in ('WALK 1 H', 'EAT CHEESE 4 OZ', 'GET KNIFE', 'DROP KNIFE', 'REST 3 H'):
            g.type(line)
        for name, address, n, data in constants:
            assert g.peek(address, n) == data, f'{name} is written by the game: it must be saved'
    print(f'  {len(constants)} excluded constant tables unchanged by play: OK')


def exit_guards():
    import test_prodos
    menu = L.until('menu_key', 40000)
    steps = ['key:SAVE 1', 'key:\\r', L.until('idle', 20000), 'key:RESTORE 1', 'key:\\r',
             L.until('idle', 20000)]
    quit_steps = steps + ['key:QUIT', 'key:\\r', 'wait:60', 'key:Y', L.until('hof_key_wait', 40000),
                          'key: ']
    test_prodos.exit_state(quit_steps, menu)


def games_on(disk):
    return sum(1 for n in present(Image(disk.read_bytes())) if re.fullmatch(r'NEOWILD\.S\d', n))


def main():
    global DISK
    constants = coverage()
    with tempfile.TemporaryDirectory(prefix='save-') as work:
        work = Path(work)
        shipped = games_on(DISK)
        if shipped < 3:
            # The shipped 140 KB image keeps the saved games that fit after
            # everything else (docs/MEMORY.md 13); this test needs games 1-3:
            # it runs on a copy built without NEOWILD.END (QUIT then goes
            # straight back to the menu, as when the file cannot be read).
            import build_disk
            copy = HERE / 'build/save140.po'     # used after the temporary directory
            build_disk.build_disk(copy, omit=('NEOWILD.END',))
            print(f'  the shipped image holds {shipped} saved games: this test uses a 140 KB copy '
                  f'without NEOWILD.END ({games_on(copy)} games)')
            if games_on(copy) < 3:
                print('SAVE/RESTORE: SKIPPED (fewer than three saved games fit on 140 KB)')
                return
            DISK = copy
        (work / 'other.po').write_bytes(DISK.read_bytes())
        image, saved, timings = main_session(work, constants)
        faults(work, image)
        day_view(work)
    constants_unchanged(constants)
    exit_guards()
    for name, seconds in timings.items():
        print(f'  {name}: {seconds:.2f} s')
    print('SAVE/RESTORE: OK')


if __name__ == '__main__':
    main()
