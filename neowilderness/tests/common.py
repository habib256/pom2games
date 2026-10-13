"""Shared helpers of the Neowilderness tests (disks, labels, floats, views).

The game is a ProDOS volume for the enhanced //e: every run of a .po image
goes to a2shot --iie (a2run emulates only the II+ and DOS 3.3 images).
The frozen HGR/DOS reference stays bootable for state comparisons.
"""
from pathlib import Path
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


def _expand(steps):
    if any('C055' in str(s) for s in steps):
        return list(steps)
    return [x for s in steps for x in (DHGR_BANKS if s == PAGE_PEEK else [s])]


def _merge_pages(result):
    """Join each (main, aux) pair of $2000 8 KB dumps into one 16 KB dump."""
    dumps = []
    for addr, data in result.rows:
        if dumps and dumps[-1][0] + len(dumps[-1][1]) == addr:
            dumps[-1][1] += data
        else:
            dumps.append([addr, bytearray(data)])
    merged, i = [], 0
    while i < len(dumps):
        addr, data = dumps[i]
        if (addr == 0x2000 and len(data) == 8192 and i + 1 < len(dumps)
                and dumps[i + 1][0] == 0x2000 and len(dumps[i + 1][1]) == 8192):
            merged.append(bytes(data) + bytes(dumps[i + 1][1]))
            i += 2
        else:
            merged.append(bytes(data))
            i += 1
    result.dumps = merged
    return result


def _run_iie(disk, steps, emulator=None, iie=False, **kw):
    """ProDOS volumes need the enhanced //e: a2shot --iie, whatever the caller
    asked for (the legacy tests chose a2run or the II+ a2shot)."""
    if _prodos(disk):
        expanded = _expand(steps)
        result = _run(disk, expanded, emulator=a2test.A2SHOT, iie=True, **kw)
        return _merge_pages(result) if expanded != list(steps) else result
    return _run(disk, steps, emulator=emulator, iie=iie, **kw)


class _Session(a2test.Session):
    def __init__(self, disk, cwd=None, timeout=120, iie=None):
        self.dhgr = _prodos(disk)
        super().__init__(disk, cwd=cwd, timeout=timeout,
                         iie=_prodos(disk) if iie is None else iie)

    def step(self, step):
        if self.dhgr and step == PAGE_PEEK:
            out = ''.join(super(_Session, self).step(s).out for s in DHGR_BANKS)
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


def text_screen(mem40x24):
    """24 lines of the text page from a $0400-$07FF dump."""
    lines = []
    for r in range(24):
        o = (r % 8) * 128 + (r // 8) * 40
        # Inverse uppercase letters occupy $00..$1F on the Apple II.
        chars=[c & 0x7F for c in mem40x24[o:o + 40]]
        lines.append(bytes(c+0x40 if c<0x20 else c for c in chars).decode('latin1'))
    return lines


def state(mem6):
    """px, py, heading from a 6-byte dump at px."""
    return tuple(int.from_bytes(mem6[o:o + 2], 'little') for o in (0, 2, 4))


def terrain_boot(timeout=20000):
    """Isolate terrain/sprite differential tests from celestial artwork."""
    return [L.until('game_start', timeout), L.poke('forest_enabled', 0), L.poke('sky_enabled', 0), L.poke('ui_enabled', 0),
            L.until('idle', timeout)]
