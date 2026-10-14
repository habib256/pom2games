"""Shared helpers of the Neowilderness tests (disks, labels, floats, views).

The game is a ProDOS volume for the enhanced //e: every run of a .po image
goes to a2shot --iie (a2run emulates only the II+ and DOS 3.3 images).
The frozen HGR/DOS reference stays bootable for state comparisons.
"""
from pathlib import Path
import re
import subprocess, sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tools'))
import a2test       # noqa: E402
import view_ref     # noqa: E402

L = a2test.labels(HERE / 'build/wild.lbl')
# Completed text pages now reach the keyboard loop in less than one video
# frame. Stop in that loop rather than at a one-shot JSR before preparation;
# otherwise a fast page change can pass the checkpoint during key:/wait:1.
for name in ('wait_key', 'status_key', 'inventory_key', 'help_key',
             'topo_key', 'graphical_topo_key', 'ending_key'):
    L[name] = L['keyboard_wait']
L['number_idle'] = L['keyboard_wait']
DISK = HERE.parent / 'dist/NEOWILDERNESS.po'
# HGR / DOS 3.3 / II+ build frozen before the 128 KB migration (lot 0):
# ../wilderness at the synchronised HEAD, with its own symbol file.
REFERENCE = HERE / 'build/reference-hgr'
REFERENCE_DISK = REFERENCE / 'WILDERNESS.dsk'
SCREEN_KEYS = ('wait_key', 'status_key', 'inventory_key', 'help_key',
               'topo_key', 'graphical_topo_key', 'ending_key')


def reference_labels():
    labels = a2test.labels(REFERENCE / 'wild.lbl')
    for name in SCREEN_KEYS:
        labels[name] = labels['keyboard_wait']
    labels['number_idle'] = labels['keyboard_wait']
    return labels


def _prodos(disk):
    return str(disk).lower().endswith('.po')


_run = a2test.run

# The game draws a DHGR page: a `peek:2000:8192` step of a test on a ProDOS
# volume reads both banks (main, then aux through PAGE2) and yields ONE dump of
# 16 KB: main bytes 0..8191, aux bytes 8192..16383. Scripts that switch PAGE2
# themselves (tests/test_dhgr_cols.py) are left alone.
PAGE_PEEK = 'peek:2000:8192'
DHGR_BANKS = [PAGE_PEEK, 'poke:C055:00', PAGE_PEEK, 'poke:C054:00']
# Lot 4: the view, the curtain and MAP are 80-column text (even columns in the
# aux page). A `peek:0400:1024` step yields ONE 2049-byte dump: main page,
# aux page (through PAGE2 under 80STORE), then the RD80VID byte ($C01F) that
# tells text_screen() which layout the screen shows.
TEXT_PEEK = 'peek:0400:1024'
TEXT_BANKS = [TEXT_PEEK, 'poke:C055:00', TEXT_PEEK, 'poke:C054:00', 'peek:C01F:1']
_EXPANSIONS = {PAGE_PEEK: DHGR_BANKS, TEXT_PEEK: TEXT_BANKS}


def _expand(steps):
    """Expand the page peeks, except in scripts that bank $2000 themselves
    (tests/test_dhgr_cols.py); explicit DHGR_BANKS sequences are kept."""
    steps = list(steps)
    if any('C055' in str(s) and (i == 0 or steps[i - 1] not in _EXPANSIONS)
           for i, s in enumerate(steps)):
        return steps
    out = []
    for i, s in enumerate(steps):
        explicit = ((i + 1 < len(steps) and steps[i + 1] == 'poke:C055:00')
                    or (i > 0 and steps[i - 1] == 'poke:C055:00'))
        out += [s] if explicit else _EXPANSIONS.get(s, [s])
    return out


def _merge_pages(result, pages=True):
    """Join each (main, aux) pair of $2000 8 KB dumps into one 16 KB dump
    (not when the script reads the banks itself), and each text triple."""
    dumps = []
    for addr, data in result.rows:
        if dumps and dumps[-1][0] + len(dumps[-1][1]) == addr:
            dumps[-1][1] += data
        else:
            dumps.append([addr, bytearray(data)])
    merged, texts, i = [], [], 0
    while i < len(dumps):
        addr, data = dumps[i]
        if (pages and addr == 0x2000 and len(data) == 8192 and i + 1 < len(dumps)
                and dumps[i + 1][0] == 0x2000 and len(dumps[i + 1][1]) == 8192):
            merged.append(bytes(data) + bytes(dumps[i + 1][1]))
            i += 2
        elif (addr == 0x400 and len(data) == 1024 and i + 2 < len(dumps)
                and dumps[i + 1][0] == 0x400 and len(dumps[i + 1][1]) == 1024
                and dumps[i + 2][0] == 0xC01F and len(dumps[i + 2][1]) == 1):
            merged.append(bytes(data) + bytes(dumps[i + 1][1]) + bytes(dumps[i + 2][1]))
            texts.append(merged[-1])
            i += 3
        else:
            merged.append(bytes(data))
            i += 1
    result.dumps = merged
    if texts:
        result.texts = texts
    return result


_mem = a2test.Result.mem


def _text_mem(self, address, length, occurrence=0):
    """r.mem(0x400, 1024, k): the k-th merged text dump (2049 bytes)."""
    texts = getattr(self, 'texts', None)
    if texts and address == 0x400 and length == 1024:
        return texts[occurrence]
    return _mem(self, address, length, occurrence)


a2test.Result.mem = _text_mem


# Lot 7: NEOWILD.SYSTEM stops at the start menu. Every test of the game
# volume plays the default scenario unless it drives the menu itself: the
# Sierra Nevada (2) at level 4 (RETURN), typed once the menu waits for a key.
# A script that stops in the loader before the menu (one of LOADER_PHASE)
# or passes menu=False types its own choice (tests/test_menu.py menu_keys).
LOADER_PHASE = ('loader_main', 'loader_claimed', 'loader_ram_files', 'ld_wait',
                'loader_menu', 'menu_key')


# Region number -> its key at the start menu (tools/genmenu.py MENU_ORDER:
# the Sierra Nevada first, chosen by RETURN alone).
MENU_KEY = {'2': '1', '1': '2', '3': '3', '4': '4', '5': '5', '6': '6'}


def menu_keys(choice='2', level=''):
    """Steps that answer the start menu: choice (a region '1'..'6', or '7'
    then the region digit, translated to the menu keys) and level digits
    ('' = RETURN = 4)."""
    keys = ''.join(MENU_KEY.get(c, c) for c in choice)
    return [L.until('menu_key', 40000), f'key:{keys}{level}\r']


MENU_SKIP = menu_keys()


def _game_volume(disk):
    """A Neowilderness volume with its start menu (not the DHGR/stars benches)."""
    try:
        with open(disk, 'rb') as f:
            return b'NEOWILD.SYSTEM' in f.read(0x1000)
    except OSError:
        return False


def _loader_phase(step):
    op, _, rest = str(step).partition(':')
    if op not in ('until', 'pcprof', 'tracepc', 'watch'):
        return False
    return any(f'{L[name]:04X}' in rest.upper() for name in LOADER_PHASE)


def _with_menu(disk, steps, menu):
    if menu is False or not _game_volume(disk) or any(_loader_phase(s) for s in steps):
        return list(steps)
    return MENU_SKIP + list(steps)


def _run_iie(disk, steps, emulator=None, iie=False, menu=None, **kw):
    """ProDOS volumes need the enhanced //e: a2shot --iie, whatever the caller
    asked for (the legacy tests chose a2run or the II+ a2shot). The game
    volume first answers the start menu (MENU_SKIP)."""
    if _prodos(disk):
        steps = _with_menu(disk, steps, menu)
        expanded = _expand(steps)
        result = _run(disk, expanded, emulator=a2test.A2SHOT, iie=True, **kw)
        explicit = any(s == 'poke:C055:00' for s in steps)
        return _merge_pages(result, not explicit) if expanded != list(steps) else result
    return _run(disk, steps, emulator=emulator, iie=iie, **kw)


class _Session(a2test.Session):
    def __init__(self, disk, cwd=None, timeout=120, iie=None, menu=None):
        self.dhgr = _prodos(disk)
        # The menu is answered before the first step, unless that step stops
        # in the loader (the test then types its own choice).
        self.menu_pending = self.dhgr and menu is not False and _game_volume(disk)
        super().__init__(disk, cwd=cwd, timeout=timeout,
                         iie=_prodos(disk) if iie is None else iie)

    def step(self, step):
        if self.menu_pending:
            self.menu_pending = False
            if not _loader_phase(step):
                for s in MENU_SKIP:
                    super().step(s)
        if self.dhgr and step in _EXPANSIONS:
            out = ''.join(super(_Session, self).step(s).out for s in _EXPANSIONS[step])
            return _merge_pages(a2test.Result(out))
        return super().step(step)


a2test.run = _run_iie
a2test.Session = _Session


def disk_with(tmp, mapbin):
    """dist/NEOWILDERNESS.po with another map."""
    m = Path(tmp) / 'map.bin'
    m.write_bytes(mapbin)
    d = Path(tmp) / 'test.po'
    subprocess.run(['python3', str(HERE / 'tools/build_disk.py'),
                    '--out', str(d), '--map', str(m)], check=True, capture_output=True)
    return d


def fp(b):
    """Applesoft 5-byte float -> Python float."""
    if b[0] == 0:
        return 0.0
    mant = int.from_bytes(b[1:5], 'big')
    sign = -1 if mant & 0x80000000 else 1
    mant |= 0x80000000
    return sign * mant / 2 ** 32 * 2.0 ** (b[0] - 0x80)


def dhgr():
    """tools/dhgr_ref (imported lazily: it imports the oracles that import us)."""
    import dhgr_ref
    return dhgr_ref


def banks(page):
    """(main, aux) of a 16 KB page dump, or of (main, aux) given separately."""
    return (page[:8192], page[8192:]) if len(page) == 16384 else page


def dhgr_page(page, aux=None):
    """192 rows x 140 colour indices of a DHGR page dump (16 KB, or main, aux)."""
    main, aux = banks(page) if aux is None else (page, aux)
    return dhgr().decode(main, aux)


def dhgr_view(page, aux=None):
    """Logical view rows 0..159 (rows 0..15 are the cache rows 160..175)."""
    R = dhgr()
    full = dhgr_page(page, aux)
    return [full[R.physical(r)] for r in range(R.VIEW_ROWS)]


def undouble(aux, main):
    """The HGR byte whose pixels were doubled into this aux/main byte pair
    (src/dhgr.s dbl_put: HGR pixel k = dots 2k and 2k+1)."""
    wide = aux & 0x7F | (main & 0x7F) << 7
    return sum(1 << k for k in range(7) if wide >> (2 * k) & 1)


def hgr_equivalent(page):
    """8 KB page of the HGR bytes drawn doubled (HUD, survival panels): the
    old HGR layout for tests that read glyphs. Meaningless for the view."""
    main, aux = banks(page)
    return bytes(undouble(a, m) for a, m in zip(aux, main))


def mood_name(index):
    import dhgr_palette
    return dhgr_palette.MOODS[index[0] if isinstance(index, (bytes, bytearray)) else index]


def dhgr_scene(m, px, py, heading, mood, animal=None, forest=False, sprites=True, sky=None):
    """tools/dhgr_ref.view in a mood (name or the sky_mood byte): terrain of
    view_ref.columns, the nearest billboard of tests/scene_ref, canopies of
    tools/forest_ref; no sun or Moon unless `sky` is given."""
    R = dhgr()
    if sky is None:
        sky = R.Sky(mood_name=mood if isinstance(mood, str) else mood_name(mood))
    return R.view(m, px, py, heading, sky, animal, forest=forest, sprites=sprites)


def view_diff(got, want, rows=range(160)):
    """(count, first (row, col, got, want)) of differing colour pixels."""
    bad = [(r, c, got[r][c], want[r][c]) for r in rows for c in range(140)
           if got[r][c] != want[r][c]]
    return len(bad), (bad[0] if bad else None)


def view_rows(page):
    """HGR rows 0..159 of an 8 KB page dump."""
    rows = bytearray(b''.join(page[a2test.hgr_offset(y):a2test.hgr_offset(y)+40] for y in range(160)))
    for y in range(view_ref.HUD_ROWS):
        rows[y*40:(y+1)*40] = bytes(40)
    return bytes(rows)


def hgr_rows(page, start=0, stop=176):
    """Displayed graphics and retained terrain, excluding HGR holes.

    Unused rows and screen holes may hold simulation scratch. Terrain-only
    fixtures pass start=16 to omit their disabled HUD panels. A 16 KB DHGR
    dump gives the rows of the main bank, then those of the aux bank.
    """
    return b''.join(bank[a2test.hgr_offset(y):a2test.hgr_offset(y)+40]
                    for bank in ((page[:8192], page[8192:]) if len(page) == 16384 else (page,))
                    for y in range(start, stop))


def text80(mem):
    """True when a merged text dump (main, aux, RD80VID) shows 80 columns."""
    return len(mem) == 2049 and mem[2048] >= 0x80


def text_screen(mem):
    """24 lines of the displayed text page: 40 characters from a $0400-$07FF
    dump, or 80 (aux even, main odd columns) from a merged dump taken while
    80COL is on (the view's mixed rows, the curtain, MAP)."""
    lines = []
    wide = text80(mem)
    for r in range(24):
        o = (r % 8) * 128 + (r // 8) * 40
        cells = mem[o:o + 40]
        if wide:
            cells = bytes(b for pair in zip(mem[1024 + o:1024 + o + 40], cells) for b in pair)
        # Inverse uppercase letters occupy $00..$1F on the Apple II.
        chars = [c & 0x7F for c in cells]
        lines.append(bytes(c+0x40 if c<0x20 else c for c in chars).decode('latin1'))
    return lines


RESULT_COL = 40            # src/menu.s: the result column of the four mixed rows
MENU_BASE = 0xBA00         # src/wild.cfg MENU: build/wildmenu.bin, where idle lives


def idle_bytes(n=9):
    """The first n bytes of the idle loop (src/menu.s), from its image: tests
    that patch the loop with calls restore them afterwards."""
    return (HERE / 'build/wildmenu.bin').read_bytes()[L['idle'] - MENU_BASE:L['idle'] - MENU_BASE + n]


def result_rows(screen):
    """The result column (rows 20..23, columns 40..78) of a text_screen(),
    or of its last four rows; the last row holds the stock row, or "> " and
    the command being typed or composed."""
    rows = screen[20:24] if len(screen) > 4 else screen[:4]
    return [row[RESULT_COL:79] for row in rows]


def result_text(screen):
    """The result column as one string, its rows separated by newlines."""
    return '\n'.join(result_rows(screen))


# Every differential text store (STA (BASL),Y): src/dhgr.s t_update, the
# 40-column menus (transitions.s) and the MAP cells (sites.s).
TEXT_STORES = ('t_store_main', 't_store_aux', 't_store_menu', 't_store_pad', 't_store_odd',
               't_store_even', 'topo_store_main', 'topo_store_aux')


# The MAP stores live in the shared $5800 module window: while another module
# runs there (INVENTORY, HELP...), their addresses hold its code. Profiles
# taken outside MAP count only the resident stores.
MENU_STORES = tuple(label for label in TEXT_STORES if not label.startswith('topo_'))


def text_writes(pcs, stores=TEXT_STORES):
    """Text cells stored, from a pcprof {pc: cycles} (STA (BASL),Y: 6 cycles)."""
    return sum(pcs.get(L[label], 0) // 6 for label in stores)


def text_changes(before, after, rows=range(24)):
    """Changed text cells between two text dumps (both pages when merged)."""
    pages = (0, 1024) if len(before) == len(after) == 2049 else (0,)
    return sum(before[p + o + c] != after[p + o + c] for p in pages for row in rows
               for o in [(row % 8) * 128 + (row // 8) * 40] for c in range(40))


MAP_CUE = re.compile(r' (\d+ MIN )?\d+,\d+ HEAD \d+ (N |NE|E |SE|S |SW|W |NW)( P\+[CHR])? ')


def map_cue(screen):
    """The inverse cue at the start of MAP's row 0 (src/sites.s topo_draw):
    " [N MIN ]X,Y HEAD H CARD[ P+S] ", padded to whole cells; None if absent."""
    m = MAP_CUE.match(screen[0])
    if not m:
        return None
    return screen[0][:m.end() + m.end() % 2]


def map_rows(screen):
    """The 24 grid rows of the full-screen MAP (text rows 0..23), 40 cells,
    one character per cell: MAP draws each cell as two 80-column characters
    (src/sites.s). The cells under the cue of row 0 read as spaces."""
    rows = [row[0:80:2] for row in screen[0:24]]
    cue = map_cue(screen)
    if cue:
        rows[0] = ' ' * (len(cue) // 2) + rows[0][len(cue) // 2:]
    return rows


def state(mem6):
    """px, py, heading from a 6-byte dump at px."""
    return tuple(int.from_bytes(mem6[o:o + 2], 'little') for o in (0, 2, 4))


def terrain_boot(timeout=20000):
    """Isolate terrain/sprite differential tests from celestial artwork."""
    return [L.until('game_start', timeout), L.poke('forest_enabled', 0), L.poke('sky_enabled', 0), L.poke('ui_enabled', 0),
            L.until('idle', timeout)]
