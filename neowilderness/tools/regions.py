#!/usr/bin/env python3
"""regions.py: extract and decode the six original region headers.

The program side ("Sierra Nevadas") keeps one 256-byte header per region on
SMALLDOS track 0, sector region + 8 (TMAKE0 line 28: POKE 74,0: POKE 75,G+8
into page $60). The header is the template of TOPO $6000-$60FF; TMAKE,
POSTP.OBJ and TMAKE0 then overwrite the map-specific bytes (see FIELDS).

Usage: regions.py [--disk build/SIERRA.dsk] [--out build/regions] [--update]
Writes rN.bin, regions.json and verifies docs/regions.sha256 (--update
rewrites the sums). The decoded data feeds mkmap.py --region and the region
packages; no original byte is copied into the sources.
"""
import argparse, hashlib, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
from smalldos import Disk  # noqa: E402

SUMS = HERE / 'docs/regions.sha256'
NAMES = {1: 'BRITISH COLUMBIA', 2: 'SIERRA NEVADA', 3: 'BURMA',
         4: 'NEW GUINEA', 5: 'BOLIVIA', 6: 'CHILE'}   # MENU line 900
DOS_FILES = {1: 'BRCOLUM', 2: 'SIERRAS', 3: 'BURMA', 4: 'NEWGUIN',
             5: 'BOLIVIA', 6: 'CHILE'}
# Animal sprites of the Journey side in their global order, which is also
# the animal id byte that precedes each record in the MS-DOS .CIM files
# (1 grizzly ... 18 cat); see re_graphics.SPRITES.
SPRITE_ORDER = ('grizzly_bc', 'wolf_bc', 'moose_bc', 'bear', 'cougar',
                'rattlesnake', 'tiger', 'elephant', 'cobra', 'python', 'dani',
                'adder', 'crocodile', 'puma', 'jaguar', 'ferdelance',
                'anaconda', 'cat')
# Our choice, not original data: east longitude of each region for the
# added lunar/star ephemeris (the original has no longitude at all).
LONGITUDE = {1: -124, 2: -120, 3: 97, 4: 143, 5: -66, 6: -70}
JUNGLE = (3, 4, 5)          # POSTP $4211, TMAKE 107, GRND words: JUNGLE
DIMENSIONS = ('season', 'hour', 'terrain', 'altitude', 'slope', 'climate')
# Reaction methods (T0F/S07 $58DE-$5939, T06/S04 $584A-$5864): injury
# threshold = .02 x record[method]; attack success = .005 x record[method+6].
METHODS = {13: 'wait/rest/eat on the ground', 14: 'noise (SCARE) failed',
           15: 'IGNORE / commands >= 22', 16: 'in a tree',
           17: 'club or rock', 18: 'axe or knife', 19: 'spear',
           20: 'bow', 21: 'gun'}

# Byte map of a region sector (= TOPO $6000 + offset). 'map' bytes are
# overwritten for every map; 'region' bytes survive into TOPO unchanged.
FIELDS = (
    (0x00, 0x7F, 'region', 'four animal records of 32 bytes (record k at 32*(k-1))'),
    (0x1F, 0x1F, 'region', 'region number 1-6 (record 1 byte 31, TOPO $601F)'),
    (0x3F, 0x3F, 'map', 'difficulty level (TMAKE0 line 68 POKE 24639)'),
    (0x5F, 0x5F, 'map', 'scenario: 1 plane crash, 2 lost city'),
    (0x7F, 0xA2, 'map', 'text residue on disk; outpost, crash, azimuths, sites, base altitude in TOPO'),
    (0xA3, 0xA3, 'region', 'rocky ground from this altitude /100 ft (POSTP $424C subtracts the base: Sierra 120-24 = 96 levels)'),
    (0xA4, 0xA5, 'region', 'unreferenced by the code (static scan); $60A5 is 0 in the jungle regions'),
    (0xA6, 0xA6, 'region', 'GRND SCRUB above this altitude /100 ft (state.md; Sierra 110)'),
    (0xA7, 0xA7, 'region', 'unreferenced by the code (static scan)'),
    (0xA8, 0xA9, 'map', 'latitude and magnetic declination chosen by TMAKE0 lines 40-44'),
    (0xAA, 0xAA, 'region', 'highest summit /100 ft: POSTP $4221 base = INT(level*(this-top)/10)'),
    (0xAB, 0xAB, 'region', 'unknown; not referenced by the game code'),
    (0xAC, 0xAC, 'region', 'river sources (TMAKE 1000/3100)'),
    (0xAD, 0xAD, 'region', 'TMAKE.OBJ parameter (TMAKE 1200 POKE ST+28)'),
    (0xAE, 0xAF, 'region', 'latitude range (TMAKE0 32-40), signed degrees'),
    (0xB0, 0xB5, 'region', 'precipitation min, max, phase in degrees, LE16 (GO2/T0C S05)'),
    (0xB6, 0xB6, 'region', 'magnetic declination at mid-latitude, signed byte (TMAKE0 32-44)'),
    (0xB7, 0xB7, 'region', 'zero in every region'),
    (0xB8, 0xB8, 'region', 'zero in every region'),
    (0xB9, 0xB9, 'region', 'highest wind in mph (T0A S0C)'),
    (0xBA, 0xBA, 'region', 'climate index of the fauna/resource filters (T09 S0F)'),
    (0xBB, 0xCF, 'map', 'goal, distance, relief, version; disk residue in the sector'),
    (0xD0, 0xFF, 'region', 'four animal names of 12 bytes, high ASCII, NUL padded'),
)


def signed(b):
    return b - 256 if b > 127 else b


def word(data, offset):
    return data[offset] | data[offset + 1] << 8


def read_headers(disk_path):
    disk = Disk(Path(disk_path).read_bytes())
    if not disk.flip:
        raise ValueError('expected the game side (catalog on physical track $22)')
    return {r: bytes(disk.sector(0, r + 8)) for r in NAMES}


def name_at(data, k):
    raw = data[0xD0 + 12 * k:0xDC + 12 * k]
    return bytes(b & 0x7F for b in raw).split(b'\0')[0].decode('ascii')


def species(data):
    out = []
    for k in range(4):
        rec = data[32 * k:32 * k + 32]
        entry = {
            'slot': k + 1, 'name': name_at(data, k), 'record_offset': 32 * k,
            'filters': [{'dimension': dim, 'centre': rec[2 * i],
                         'width': signed(rec[2 * i + 1])}
                        for i, dim in enumerate(DIMENSIONS)],
            'rate': rec[12],
            'injury': {str(m): rec[m] for m in range(13, 22)},
            'severity_exponent': rec[22],
            'success': {str(m): rec[m + 6] for m in range(17, 22)},
            'theft': rec[28],
            'water_gate': rec[29],
            'byte30': rec[30],
        }
        out.append(entry)
    return out


def tmake0_latitude(lo, hi, u):
    """TMAKE0 line 40: L% = C1 + (C2 - C1) * USR(1), integer truncation."""
    return math.trunc(lo + (hi - lo) * u)


def tmake0_declination(lo, hi, base, latitude):
    """TMAKE0 lines 42-44 and the byte conversion of line 82 (floor)."""
    mid = .5 * (lo + hi)
    return math.floor(base + (latitude - mid) * math.sin(.017453 * mid))


def go2_temperatures(latitude):
    """January and July sea-level means, $4BB0/$4BB1 (GO2 $2876-$2912).

    INT is floor, as the ROM's $E10C. Constants are GO2's floats at
    $29AF (1.7), $29BE (.75), $29B4 (.125), ROM .5, $29C3 (1.25), $29B9 (1.375).
    """
    if latitude >= 19:
        return 105 - math.floor(latitude * 1.7), 105 - math.floor(latitude * .75)
    if latitude >= -20:
        return 78 - math.floor(latitude * .125), 80 + math.floor(latitude * .5)
    return 110 + math.floor(latitude * 1.25), 104 + math.floor(latitude * 1.375)


def season_class(latitude):
    """GO1 $5CF3: resource season widths of types 5,7,8,10,11,12."""
    if latitude >= 23:
        return 'north'
    return 'tropical' if latitude >= -22 else 'south'


def base_altitude(header, region, level, top, low=0):
    """POSTP $4211-$4248: base altitude /100 ft of a map ($60A1).

    Jungle regions put the lowest level ($60BE) at sea level; the others take
    INT(level * max(0, summit - top) / 10), summit = $60AA, top = $6086.
    """
    if region in JUNGLE:
        return -low
    return max(0, math.floor(level * max(0, header[0xAA] - top) / 10))


MAY_6 = 0.344424   # date fraction $4C89 of the scenario start (environment.md)


def snowline(latitude, date=MAY_6):
    """Snow line in hundreds of feet, $4C0A (GO2 $29C8-$2A5F).

    x = |latitude| >> 1; INT(135 - 3x + (15 + x) sin(2 pi (date + k))),
    k = .13 south, -.37 north. The view's snow threshold is this minus the
    base altitude ($E8 = half of it, T17/SC); the introduction prints
    INT(line/10 + .5) thousand feet, or NO SNOW above the highest summit.
    """
    x = abs(latitude) >> 1
    k = .13 if latitude < 0 else -.37
    return math.floor(135 - 3 * x + (15 + x) * math.sin(2 * math.pi * (date + k)))


def climate(data):
    return {
        'rock_altitude': data[0xA3], 'byte_a4': data[0xA4], 'byte_a5': data[0xA5],
        'scrub_altitude': data[0xA6], 'byte_a7': data[0xA7],
        'summit_altitude': data[0xAA], 'byte_ab': data[0xAB],
        'river_sources': data[0xAC], 'tmake_param_ad': data[0xAD],
        'latitude_min': signed(data[0xAE]), 'latitude_max': signed(data[0xAF]),
        'precipitation_min': word(data, 0xB0), 'precipitation_max': word(data, 0xB2),
        'precipitation_phase': word(data, 0xB4),
        'declination': signed(data[0xB6]), 'byte_b7': data[0xB7], 'byte_b8': data[0xB8],
        'wind_max': data[0xB9], 'climate_index': data[0xBA],
    }


def go3_texts(go3):
    """Region name and fauna sentence of the introduction (GO3 at $3000)."""
    def text(addr):
        o = addr - 0x3000
        end = o
        while go3[end] & 0x80:
            end += 1
        return bytes(b & 0x7F for b in go3[o:end]).decode('ascii')
    return {r: (text(0x3668 + go3[0x6AA + r - 1]), text(0x3832 + go3[0x90B + r - 1]))
            for r in NAMES}


def decode(region, data, go3=None):
    c = climate(data)
    lat = tmake0_latitude(c['latitude_min'], c['latitude_max'], .5)
    winter, summer = go2_temperatures(lat)
    entry = {
        'region': region, 'name': NAMES[region], 'sector': f'T00/S{region + 8:X}',
        'sha256': hashlib.sha256(data).hexdigest(),
        'region_byte': data[0x1F], 'jungle': region in JUNGLE,
        'species': [s for s in species(data) if s['rate']],
        'empty_slots': [s['slot'] for s in species(data) if not s['rate']],
        'climate': c,
        'defaults': {
            'latitude_mid': lat,
            'declination_mid': tmake0_declination(c['latitude_min'], c['latitude_max'],
                                                  c['declination'], lat),
            'january_temperature': winter, 'july_temperature': summer,
            'season_class': season_class(lat),
            'snowline_may6': snowline(lat),
            'longitude_port': LONGITUDE[region],
        },
    }
    if go3 is not None:
        entry['intro_name'], entry['fauna_sentence'] = go3_texts(go3)[region]
    return entry


def dos_check(headers, zip_path):
    """Compare with the MS-DOS .CIM files (cross-check only).

    .CIM: 384 bytes of star data, then $60AA-$60BA (17 bytes), $60A3-$60A7,
    then four records of an animal id byte + 31 bytes (record bytes 0-30).
    Returns {region: {field: bool}} and the list of differing record bytes.
    """
    import zipfile
    out = {}
    with zipfile.ZipFile(zip_path) as z:
        for r, name in DOS_FILES.items():
            cim = z.read(f'WILD/{name}.CIM')
            h = headers[r]
            recs = [cim[406 + 32 * k:438 + 32 * k] for k in range(4)]
            out[r] = {
                'climate_block': cim[384:401] == h[0xAA:0xBB],
                'a4_a7': cim[402:406] == h[0xA4:0xA8],
                'filters': all(rec[1:13] == h[32 * k:32 * k + 12] for k, rec in enumerate(recs)),
                'record_differences': [(k + 1, i, h[32 * k + i], rec[1 + i])
                                       for k, rec in enumerate(recs) for i in range(31)
                                       if rec[1 + i] != h[32 * k + i]],
                'animal_ids': [rec[0] for rec in recs],
                'rock_altitude_dos': cim[401],
            }
    return out


def dos_zip():
    found = sorted((HERE / 'original/extras').glob('*MS-DOS*.zip'))
    return found[0] if found else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--disk', type=Path, default=HERE / 'build/SIERRA.dsk')
    ap.add_argument('--out', type=Path, default=HERE / 'build/regions')
    ap.add_argument('--update', action='store_true', help='rewrite docs/regions.sha256')
    a = ap.parse_args()
    headers = read_headers(a.disk)
    go3_path = HERE / 'build/files/GO3.B'
    go3 = go3_path.read_bytes() if go3_path.exists() else None
    a.out.mkdir(parents=True, exist_ok=True)
    sums = []
    regions = []
    for r, data in headers.items():
        (a.out / f'r{r}.bin').write_bytes(data)
        sums.append(f'{hashlib.sha256(data).hexdigest()}  r{r}.bin')
        regions.append(decode(r, data, go3))
    doc = {'source': str(a.disk), 'fields': [
        {'from': f'${0x6000 + lo:04X}', 'to': f'${0x6000 + hi:04X}', 'kind': kind, 'meaning': text}
        for lo, hi, kind, text in FIELDS], 'regions': regions}
    z = dos_zip()
    if z:
        doc['dos_check'] = {str(r): v for r, v in dos_check(headers, z).items()}
    (a.out / 'regions.json').write_text(json.dumps(doc, indent=1) + '\n')
    text = '\n'.join(sums) + '\n'
    if a.update or not SUMS.exists():
        SUMS.write_text(text)
        print(f'wrote {SUMS}')
    elif SUMS.read_text() != text:
        sys.exit(f'region headers differ from {SUMS}')
    for e in regions:
        names = ', '.join(f"{s['name']} {s['rate']}" for s in e['species'])
        print(f"r{e['region']} {e['name']}: lat {e['climate']['latitude_min']}..{e['climate']['latitude_max']}"
              f", climate {e['climate']['climate_index']}, fauna {names}")
    print(f'6 region headers OK ({SUMS.name})')


if __name__ == '__main__':
    main()
