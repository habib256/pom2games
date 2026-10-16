"""Scenario data, compiled into loader records; no scenario rule in the engine.

The initial manifest reuses a base environment's resource filters and sprite
layout. It replaces its texts, climate, large-animal encounters and scenery.
Animals is an explicit list (currently empty): new animal authoring is separate.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def manifest(path=None):
    data = json.loads(Path(path or HERE / 'scenarios/archipelago.json').read_text())
    if (data['format'], data['version']) != ('neowilderness-scenario', 1):
        raise ValueError('unsupported scenario manifest')
    if data['animals']:
        raise ValueError('new animal records are not supported by manifest v1 yet')
    profiles = data['decor']['profiles']
    if len(profiles) != 2 or any(len(p) != 16 for p in profiles):
        raise ValueError('two 16-column tree profiles required')
    if any(not 0 <= lo <= hi <= 255 for p in profiles for lo, hi in p):
        raise ValueError('invalid tree profile')
    return data


def palette(data):
    import dhgr_palette as p
    from gendhgr import region_tables, resident_moods
    # P.mood_table uses the same generic roles for every environment.
    def tuples(value):
        return tuple(tuples(v) for v in value) if isinstance(value, list) else value
    sentinel = -1
    p.REGIONS[sentinel] = {
        mood: {role: tuples(v) for role, v in roles.items()}
        for mood, roles in data['palette'].items()
    }
    try:
        moods, shades = resident_moods(sentinel)
        base = region_tables(data['base_pack'])
        # Sprite colours follow moods and shades; no new sprite slots in v1.
        return bytes(moods) + bytes(shades) + base[len(moods) + len(shades):]
    finally:
        del p.REGIONS[sentinel]


def header(data):
    h = bytearray(64)
    h[:2] = b'W\x01'
    if data['terrain']['open_sea_horizon']:
        h[1] |= 0x80             # low 7 bits: format; bit 7: sea background
    c = data['climate']
    for offset, name in ((10, 'base'), (11, 'snow'), (12, 'latitude'),
                         (13, 'january'), (14, 'july'), (15, 'wind'),
                         (23, 'climate_index'), (24, 'declination'),
                         (25, 'longitude'), (27, 'timberline')):
        h[offset] = c[name] & 255
    h[22], h[26], h[32] = 4, bool(data['decor']['enabled']), data['base_pack']
    if data['water']['sea_level'] != 0:
        raise ValueError('TMAP v1 requires sea level zero')
    h[50] = 0 if data['water']['sea_is_drinkable'] else 0x80
    shift = data['terrain']['relief_shift']
    if not 0 <= shift <= 2:
        raise ValueError('relief_shift must be 0..2 (terrain height <= 61)')
    h[56] = shift
    return bytes(h)


def scenery_sections(data, sym):
    """Main-RAM data overrides, using addresses of the current engine build."""
    def field(text, n):
        value = text.encode('ascii')
        if len(value) >= n:
            raise ValueError(f'scenario field too long: {text}')
        return value.ljust(n, b'\0')
    texts = (field(data['name'], 16) + field(data['fauna_sentence'], 40)
             + bytes(48) + bytes((data['base_pack'], 0))
             + field(data['name'], 22))
    profiles = bytes(v for p in data['decor']['profiles'] for pair in p for v in pair)
    sections = [(0, sym['dhgr_moods'], palette(data)),
                (0, sym['__REGIONTEXT_RUN__'], texts)]
    if data['decor']['enabled']:
        sections += [(0, sym['forest_profiles'], profiles),
                     (0, sym['forest_crown_floor'], bytes((data['decor']['crown_floor'],)))]
    return sections
