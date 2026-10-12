"""Shared helpers of the Wilderness tests (disks, labels, floats, views)."""
from pathlib import Path
import subprocess, sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tools'))
import a2test       # noqa: E402
import view_ref     # noqa: E402

L = a2test.labels(HERE / 'build/wild.lbl')
# The numeric reader blocks inside wait_key. Its call-site is a transient
# checkpoint which key:TEXT can pass before the next emulator frame.
L['number_idle'] = L['wait_key']
DISK = HERE.parent / 'dist/WILDERNESS.dsk'


def disk_with(tmp, mapbin):
    """dist/WILDERNESS.dsk with another map."""
    m = Path(tmp) / 'map.bin'
    m.write_bytes(mapbin)
    d = Path(tmp) / 'test.dsk'
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


def view_rows(page):
    """HGR rows 0..159 of an 8 KB page dump."""
    rows = bytearray(b''.join(page[a2test.hgr_offset(y):a2test.hgr_offset(y)+40] for y in range(160)))
    for y in range(view_ref.HUD_ROWS):
        rows[y*40:(y+1)*40] = bytes(40)
    return bytes(rows)


def hgr_rows(page, start=0, stop=176):
    """Displayed graphics and retained terrain, excluding HGR holes.

    Unused rows and screen holes may hold simulation scratch. Terrain-only
    fixtures pass start=16 to omit their disabled HUD panels.
    """
    return b''.join(page[a2test.hgr_offset(y):a2test.hgr_offset(y)+40]
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
