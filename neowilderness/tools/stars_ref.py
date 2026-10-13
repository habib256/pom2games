#!/usr/bin/env python3
"""stars_ref.py: bit-exact reference of the night-sky stars (lot 7, step 5).

The integer algorithm below is the specification of src/stars.s (hourly
module wildsky.bin) and src/stars_draw.s (per-column drawing); the bench
tests/test_stars.py compares both banks of the DHGR page and the resident
list with this file, byte for byte. Everything is integer arithmetic on the
tables built here (genstars.py assembles the same tables for the 6502).

Angles. The view unit: 560 per turn (src/wild.s UNITS), 140 per quadrant,
0 = geographic north, 140 = east. Sines come from the view engine's own
quarter-wave table sin_lo (tools/gentables.py: round(256 sin(i * 90/140)),
i = 0..140), the only integer trigonometric table of the engine
(sky_position itself works with the ROM floating point), clamped to 255 so
that every product is 8 x 8 bits. Right ascensions and sidereal time are
16-bit binary angles (65536 per turn).

Time. The game clock is apparent local solar time (solar noon = 12 h, see
src/sky.s). The local sidereal time is then the true Sun's right ascension
plus the Sun's hour angle:
    LST16 = C(day) + Tsid(minute) - (lon >> 1)
  C(day)        alpha_sun(day, 0 h UT) - 32768, the Sun from
                tools/sky_ephemeris.orbit (1985, equinox of date): table of
                47 words (every 8 days), linear interpolation in day & 7;
  Tsid(minute)  minute * 45 + (minute * 163 >> 8): 65536 * (1 + 1/365.25)
                / 1440 = 45.6357 per minute (sidereal rate);
  lon >> 1      the Sun's motion between local and Universal time, 179.4 /
                360 = 0.498 binary units per degree of east longitude (an
                arithmetic shift of the signed header byte +25).
day = INT(s_date * 365) (0 = 1 January, as sky_lunar), minute = INT(s_hour
* 60) mod 1440.

Position of a catalogue star (tools/stars_catalog.py, 3-byte records):
    LSTq = ((LST16 * 35 + 512) >> 10) mod 2240     (quarter view units, once)
    HAq  = (LSTq - RAq) mod 2240;  H = ((HAq + 2) >> 2) mod 560
    S(i) = min(sin_lo[i], 255);  sin/cos of H by quadrant; dec_u, lat_u in
    view units: lat_u = (|lat| * 199 + 66) >> 7 = round(|lat| * 14 / 9)
    sf, cf = +-S(lat_u), S(140 - lat_u);  sd, cd = +-S(dec_u), S(140 - dec_u)
    cdcH = sign(cosH) * (cd * |cosH| >> 8)
    up  = sf * sd + cf * cdcH                    (sin altitude, 1.0 = 65536)
    N   = cf * sd - sf * cdcH                    (north component)
    E   = -sinH * cd                             (east component)
  up <= 0: below the horizon; up >= 65536: above the view. A star whose
  declination lies across the equator from the latitude with dec_u + lat_u
  > 140 never rises: the module skips it before H (up <= 0 at every H,
  S being monotonic and cdcH <= cd), which changes no result. h = number of
  T[k] <= up >> 7, k = 1..80: T[k] = ceil(512 k / sqrt(k^2 + 48^2)) for
  k <= 48, the Moon's perspective (sky_y = 95 - INT(48 tan alt)) at 1/512
  resolution in sin(alt), up to 45 degrees (row 47); above, T[k] = round(363
  + (k - 48) * 148 / 32): the rows 46..16 share the remaining sin(alt)
  evenly, so that the zenith stays in the view (the Moon alone keeps its
  perspective and hides above 59 degrees). h = 80 (up >> 7 = 511, alt >=
  86.4 degrees) is above the view. row = 95 - h. The table holds T[k] &
  255; T[k] >= 256 from k = T_HIGH + 1 on (the sin_lo trick).
  Azimuth: |E|, |N| halved when either reaches 65536; q = (small << 8) //
  large (small < large), r = (q + 1) >> 1 (128 when equal), a = AT[r] =
  round(atan(r / 128) * 560 / 2 pi); a' = a if |E| <= |N| else 140 - AT[r of
  N / E]; az = a' (E >= 0, N >= 0), 280 - a' (E >= 0, N < 0), 280 + a'
  (E < 0, N < 0), (560 - a') mod 560 (E < 0, N >= 0).
  Moon: hidden if 16 <= sky_y <= 95 (a drawn Moon), d = (az - sky_bearing
  + 5) mod 560 < 11 and |row - sky_y| <= sky_outer[d] (the full outer disc
  of src/sky.s).
Visible list: the first LIST_MAX (160) entries of the catalogue (selection
order: Polaris and the four stars of the Cross, then class 0, 1, 2, each by
magnitude) that pass, grouped by azimuth bucket b = az >> 4 (16 units,
0..34) in catalogue order within a bucket (a stable counting sort), with
bucket starts B[b] = first index of bucket >= b, b = 0..35 (B[35] = count).
A first-magnitude star (record bit 6) gives two consecutive entries, the
second one row below (the list may end between them). Entry, 2 bytes:
attr = class << 6 | look << 4 | (az & 15), row. The class (from the index,
tools/stars_catalog.class_layout) compares below any threshold of the same
class; the low azimuth bits identify the star's column inside its bucket.

Drawing (stars_frame / stars_column, per column after the sky zones and
before the Moon): threshold = $40 (night bright: class 0, the figures and
the stars brighter than 2.0), $80 (night dim: classes 0-1), $C0 (night
dark: every star), 0 otherwise or whenever weather_sky != 0; the entries of
the column's bucket are scanned from the last to the first (the brightest
is painted last, on top of a fainter star of the same pixel); an entry of
the column's azimuth with attr < threshold and row < top (the ridge) is a
span of ROWS[look] rows from its row (2 in the tint, 1 grey for the faint
look; the second row may be the black ridge row), colour COLOURS[look];
opaque sprite rows are kept (scene_span), trees are painted afterwards. A
first-magnitude star, two entries one row apart, is 3 rows high.

Usage: stars_ref.py [--out build/stars]   (PNG previews, almanac summary)
"""
import argparse, bisect, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
import stars_catalog as K  # noqa: E402
import sky_ephemeris  # noqa: E402
import dhgr_palette as P  # noqa: E402

UNITS = 560
HORIZON, HUD_ROWS, VIEW_ROWS = 95, 16, 160
H_MAX = HORIZON - HUD_ROWS + 1          # 80: rows 16..95
LIST_MAX = 160
BUCKET_SHIFT = 4                        # 16 azimuth units per bucket
BUCKETS = 36                            # az >> 4 = 0..34, then the count
RA_UNITS = K.RA_UNITS                   # 2240: quarter view units
SKY_OUTER = (3, 5, 6, 7, 7, 8, 7, 7, 6, 5, 3)   # src/sky.s sky_outer
COLOURS = (P.WHITE, P.YELLOW, P.LIGHT_BLUE, P.GREY2)   # look 0, 1, 2, 3 (faint)
ROWS = (2, 2, 2, 1)                             # rows of a span per look
THRESHOLD = {'night bright': 0x40, 'night dim': 0x80, 'night dark': 0xC0}
MOOD_IDS = {m: i for i, m in enumerate(P.MOODS)}
DAY0 = -5477                            # Schlyter day number of 1985 Jan 1 0 h UT (sky_ephemeris.entry)

# Test positions of the six regions (geographic, signed degrees east): the
# engine reads the map header (+12 latitude, +25 longitude), filled from the
# region headers by tools/mkmap.py --region. Longitude is a signed byte:
# beyond +-127 it must be clamped, which moves the stars by 0.5/65536 turn
# per degree (nothing) and the Moon by its motion in 4 min per degree.
REGIONS = {
    1: ('BRITISH COLUMBIA', 52, -122),
    2: ('SIERRA NEVADA', 38, -120),     # tools/mkmap.py header: 38, -120
    3: ('BURMA', 22, 96),
    4: ('NEW GUINEA', -5, 127),         # 142 E does not fit the S8 header byte: clamped
    5: ('BOLIVIA', -16, -68),
    6: ('CHILE', -24, -69),
}


# ---------------------------------------------------------------------------
# Tables (assembled by tools/genstars.py)
SINQ = tuple(round(256 * math.sin(i * math.pi / 2 / 140)) for i in range(141))   # gentables


def S(i):
    return min(SINQ[i], 255)


def sun_ra16(day):
    ra = sky_ephemeris.orbit(DAY0 + day)[0]
    return round(ra / (2 * math.pi) * 65536) & 0xFFFF


C_TABLE = tuple((sun_ra16(8 * i) - 32768) & 0xFFFF for i in range(47))
KNEE = 48                               # row 47: 45 degrees; above, even in sin(alt)
T_TABLE = tuple(math.ceil(512 * k / math.sqrt(k * k + 48 * 48)) if k <= KNEE
                else round(363 + (k - KNEE) * 148 / (H_MAX - KNEE)) for k in range(1, H_MAX + 1))
T_HIGH = next(j for j, t in enumerate(T_TABLE) if t >= 256)     # first entry >= 256
AT_TABLE = tuple(round(math.atan(r / 128) * UNITS / (2 * math.pi)) for r in range(129))
CATALOGUE = K.stars()
LAYOUT = K.class_layout(CATALOGUE)      # priority classes, first index of classes 1 and 2
assert all(K.star_class(k, LAYOUT) == s['cls'] for k, s in enumerate(CATALOGUE))
assert all(0 < (C_TABLE[i + 1] - C_TABLE[i]) & 0xFFFF < 4096 for i in range(46))
assert T_TABLE[KNEE - 1] == 363 and T_TABLE[-1] == 511 and AT_TABLE[-1] == 70
assert all(a < b for a, b in zip(T_TABLE, T_TABLE[1:]))


# ---------------------------------------------------------------------------
def lst16(day, minute, lon):
    """Local sidereal time, 16-bit binary angle."""
    i, f = day >> 3, day & 7
    diff = (C_TABLE[i + 1] - C_TABLE[i]) & 0xFFFF
    c = (C_TABLE[i] + (diff * f >> 3)) & 0xFFFF
    tsid = minute * 45 + (minute * 163 >> 8)
    return (c + tsid - (lon >> 1)) & 0xFFFF


def lst_quarter(lst):
    """LST16 in quarter view units (0..2239), rounded."""
    return ((lst * 35 + 512) >> 10) % RA_UNITS


def never_rises(lat, star):
    """The module's early skip: up <= 0 at every hour angle."""
    return lat != 0 and star['dec_u'] and (star['south'] != (lat < 0)) \
        and star['dec_u'] + lat_units(lat) > 140


def lat_units(lat):
    return (abs(lat) * 199 + 66) >> 7


def sincos(h):
    """(sin, cos) of view angle h = 0..559, signed, magnitudes from S."""
    q, i = divmod(h, 140)
    s, c = S(i), S(140 - i)
    return ((s, c), (c, -s), (-s, -c), (-c, s))[q]


def atan_units(e, n):
    """Angle from north toward east of the vector (|e|, |n|), 0..140."""
    if max(e, n) >= 65536:
        e, n = e >> 1, n >> 1
    if e <= n:
        small, large, flip = e, n, False
    else:
        small, large, flip = n, e, True
    if large == 0:
        return 0
    r = 128 if small == large else ((small << 8) // large + 1) >> 1
    a = AT_TABLE[r]
    return 140 - a if flip else a


def position(lst, lat, star):
    """(up, az, row) of a catalogue star at LST16 `lst`; row None when not
    in the view."""
    ha = (lst_quarter(lst) - star['ra_q']) % RA_UNITS
    h = ((ha + 2) >> 2) % UNITS
    sin_h, cos_h = sincos(h)
    lu = lat_units(lat)
    sf, cf = (S(lu) if lat >= 0 else -S(lu)), S(140 - lu)
    du = star['dec_u']
    sd, cd = (-S(du) if star['south'] else S(du)), S(140 - du)
    cdch = ((cd * abs(cos_h) + 128) >> 8) * (1 if cos_h >= 0 else -1)
    up = sf * sd + cf * cdch
    n = cf * sd - sf * cdch
    e = -sin_h * cd
    a = atan_units(abs(e), abs(n))
    if e >= 0:
        az = a if n >= 0 else 280 - a
    else:
        az = 280 + a if n < 0 else (UNITS - a) % UNITS
    row = None
    if 0 < up < 65536:
        k = bisect.bisect_right(T_TABLE, up >> 7)
        if k < H_MAX:
            row = HORIZON - k
    return up, az, row


def behind_moon(az, row, moon):
    """moon = (sky_bearing, sky_y): the outer disc of sky_column, when the
    Moon is drawn (rows 16..95)."""
    if moon is None or moon[1] > HORIZON or moon[1] < HUD_ROWS:
        return False
    d = (az - moon[0] + 5) % UNITS
    return d < 11 and abs(row - moon[1]) <= SKY_OUTER[d]


def list_attr(k, star, az):
    """Byte `attr` of a list entry: class (from the index) << 6 | look << 4
    | azimuth & 15."""
    return K.star_class(k, LAYOUT) << 6 | star['look'] << 4 | az & 15


def entry(attr, row, az):
    """A list entry as the drawing sees it (also decoded from memory):
    colour and span rows of its look."""
    look = attr >> 4 & 3
    return dict(az=az, row=row, attr=attr, colour=COLOURS[look], rows=ROWS[look])


def visible(day, minute, lat, lon, moon=None, limit=LIST_MAX):
    """The selected entries in catalogue (selection) order, at most
    LIST_MAX: [dict(index, star, az, row, attr, colour, rows, up)]; a
    first-magnitude star twice, one row apart."""
    lst = lst16(day, minute, lon)
    out = []
    for k, star in enumerate(CATALOGUE):
        if never_rises(lat, star):
            continue
        up, az, row = position(lst, lat, star)
        if row is None or behind_moon(az, row, moon):
            continue
        for r in range(row, row + 1 + star['big']):
            out.append(dict(entry(list_attr(k, star, az), r, az), index=k, star=star, up=up))
            if len(out) == limit:
                return out
    return out


def resident(vis):
    """The resident arrays: (attr, row) LIST_MAX bytes each, grouped by
    bucket az >> 4 (stable: catalogue order inside a bucket), unused
    entries 0; bucket starts (36 bytes). Returns (attr, row, buckets, srt)."""
    srt = sorted(vis, key=lambda v: v['az'] >> BUCKET_SHIFT)
    attr = bytearray(LIST_MAX)
    row = bytearray(LIST_MAX)
    for i, v in enumerate(srt):
        attr[i], row[i] = v['attr'], v['row']
    buckets = bytearray(BUCKETS)
    for b in range(BUCKETS):
        buckets[b] = next((i for i, v in enumerate(srt) if v['az'] >> BUCKET_SHIFT >= b), len(srt))
    return bytes(attr), bytes(row), bytes(buckets), srt


def decode_resident(attr, row, buckets):
    """Entries of a resident list read from memory (az from the bucket)."""
    out = []
    for b in range(BUCKETS - 1):
        for i in range(buckets[b], buckets[b + 1]):
            out.append(entry(attr[i], row[i], b << BUCKET_SHIFT | attr[i] & 15))
    return out


def paint_order(entries):
    """The order in which stars_column paints the entries of a column: its
    bucket from the last entry to the first, so the brightest wins a shared
    pixel. Any list in catalogue order inside a bucket works."""
    return list(reversed(entries))


# ---------------------------------------------------------------------------
# Mood (src/dhgr.s select_mood, integer compares) and visibility
def engine_mood(night, view_dark=False, clouds=False, sun8=-128, moon8=-128, phase=0):
    if view_dark:
        return 'night dark'
    if not night:
        for limit, clear, cloudy in ((P.SUN_DAY, 'day', 'overcast'),
                                     (P.SUN_GOLDEN, 'golden', 'overcast dusk'),
                                     (P.SUN_HORIZON, 'sunset', 'overcast dusk'),
                                     (P.SUN_CIVIL, 'civil', 'nautical')):
            if sun8 >= limit:
                return cloudy if clouds else clear
        return 'nautical'
    light = P.moon_light(moon8, phase, clouds)
    if moon8 <= 0:
        return 'night dark'
    return 'night bright' if light >= P.LIGHT_BRIGHT else 'night dim' if light >= P.LIGHT_DIM \
        else 'night dark'


def threshold(mood, clouds):
    """stars_frame: attr limit of the frame (0: no star)."""
    return 0 if clouds else THRESHOLD.get(mood, 0)


# ---------------------------------------------------------------------------
# DHGR frame of the bench: black page, sky zones above a ridge profile,
# stars; logical rows 0..15 go to the cache rows 160..175 (dhgr_ref).
def physical(row):
    return row if row >= HUD_ROWS else 160 + row


def column_az(heading, col):
    return (heading - 70 + col) % UNITS


def draw_columns(page, heading, cols, tops, mood, entries, thr):
    """Paint columns `cols` (any order): sky zones of the mood on rows
    0..top-1, then the stars of the column (resident entries)."""
    for col in cols:
        az = column_az(heading, col)
        top = tops[col]
        for r in range(top):
            page[physical(r)][col] = P.sky_colour(mood, r, az)
        if not thr:
            continue
        for v in paint_order(entries):
            if v['az'] == az and v['attr'] < thr and v['row'] < top:
                for r in range(v['row'], v['row'] + v['rows']):
                    page[physical(r)][col] = v['colour']


def frame(heading, tops, mood, entries, thr, cols=range(140)):
    page = [[P.BLACK] * 140 for _ in range(192)]
    draw_columns(page, heading, cols, tops, mood, entries, thr)
    return page


def star_pixels(heading, tops, entries, thr):
    """{(col, row): colour} of the stars drawn in a full view."""
    out = {}
    for col in range(140):
        az = column_az(heading, col)
        for v in paint_order(entries):
            if thr and v['az'] == az and v['attr'] < thr and v['row'] < tops[col]:
                for r in range(v['row'], v['row'] + v['rows']):
                    out[(col, r)] = v['colour']
    return out


# ---------------------------------------------------------------------------
# Independent floating-point almanac (validation only): Meeus, Astronomical
# Algorithms, GMST eq. 12.4, low-precision Sun ch. 25, equation of time 28.3.
def julian_day(day, ut_hours):
    return 2446066.5 + day + ut_hours / 24        # 1985 Jan 1 0 h UT = JD 2446066.5


def sun_meeus(jd):
    t = (jd - 2451545.0) / 36525
    l0 = (280.46646 + 36000.76983 * t + 0.0003032 * t * t) % 360
    m = math.radians(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    c = ((1.914602 - 0.004817 * t) * math.sin(m) + (0.019993 - 0.000101 * t) * math.sin(2 * m)
         + 0.000289 * math.sin(3 * m))
    lon = math.radians(l0 + c)
    eps = math.radians(23.439291 - 0.0130042 * t)
    ra = math.degrees(math.atan2(math.cos(eps) * math.sin(lon), math.cos(lon))) % 360
    eot = (l0 - 0.0057183 - ra + 180) % 360 - 180    # degrees (nutation ignored)
    return ra, eot


def gmst(jd):
    t = (jd - 2451545.0) / 36525
    return (280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t * t
            - t ** 3 / 38710000) % 360


def lst_float(day, minute, lon):
    """Degrees, from local apparent solar time (minutes) and east longitude."""
    t = minute / 60
    ut = t - lon / 15
    for _ in range(3):                                # UT = T - lon - EoT
        _, eot = sun_meeus(julian_day(day, ut))
        ut = t - lon / 15 - eot / 15
    return (gmst(julian_day(day, ut)) + lon) % 360


def altaz_float(day, minute, lat, lon, ra, dec):
    """(altitude, azimuth) in degrees, azimuth clockwise from north."""
    h = math.radians(lst_float(day, minute, lon) - ra)
    f, d = math.radians(lat), math.radians(dec)
    alt = math.asin(math.sin(f) * math.sin(d) + math.cos(f) * math.cos(d) * math.cos(h))
    e = -math.cos(d) * math.sin(h)
    n = math.cos(f) * math.sin(d) - math.sin(f) * math.cos(d) * math.cos(h)
    return math.degrees(alt), math.degrees(math.atan2(e, n)) % 360


def row_float(alt):
    """The row of T_TABLE's two projections, as a float (no INT)."""
    if alt <= 45:
        return HORIZON - 48 * math.tan(math.radians(alt))
    return HORIZON - KNEE - (512 * math.sin(math.radians(alt)) - 363) * (H_MAX - KNEE) / 148


# ---------------------------------------------------------------------------
# LOOK STARS (optional command): landmarks with bearing and height.
def alt_degrees(up):
    """Integer height in degrees: count of S(i) << 8 <= up, i = 1..140."""
    u = sum(1 for i in range(1, 141) if S(i) << 8 <= up)
    return (u * 9 + 7) // 14


def az_degrees(az):
    return (az * 9 + 7) // 14 % 360


def look_stars(day, minute, lat, lon, mood, clouds):
    """Message lines of LOOK STARS (docs/STARS.md, spec of the command)."""
    if not mood.startswith('night'):
        return ['IT IS NOT DARK ENOUGH TO SEE THE STARS.']
    if clouds:
        return ['CLOUDS HIDE THE STARS.']
    lst = lst16(day, minute, lon)
    thr = THRESHOLD[mood]
    lines, named = [], set()
    for mark in (1, 2):
        star = next(s for s in CATALOGUE if s['landmark'] == mark)
        up, az, _ = position(lst, lat, star)
        if up > 0:
            lines.append(f'{K.LANDMARK_NAMES[mark]}: BEARING {az_degrees(az)}, HEIGHT {alt_degrees(up)}.')
            named.add(star['name'])
    up_stars = [(s['v'], s, position(lst, lat, s)) for s in CATALOGUE if (s['cls'] << 6) < thr]
    up_stars = [(v, s, p) for v, s, p in up_stars if p[0] > 0]
    if up_stars:                                 # brightest star above the horizon
        _, star, (up, az, _) = min(up_stars, key=lambda t: t[0])
        if star['name'] not in named:
            lines.append(f"{star['name']}: BEARING {az_degrees(az)}, HEIGHT {alt_degrees(up)}.")
    return lines or ['NO BRIGHT STAR IS ABOVE THE HORIZON.']


# ---------------------------------------------------------------------------
def panorama(day, minute, lat, lon, moon=None, thr=0xC0):
    """560 x 96 page of the whole horizon (rows 0..95, column = azimuth)."""
    page = [[P.BLACK] * UNITS for _ in range(96)]
    for r in range(96):
        for c in range(0, UNITS, 140):
            page[r][c] = P.DARK_BLUE                # N, E, S, W marks
    for v in paint_order(visible(day, minute, lat, lon, moon)):
        if v['attr'] < thr:
            for r in range(v['row'], min(v['row'] + v['rows'], 96)):
                page[r][v['az']] = v['colour']
    return page


def png(path, page, scale=2):
    import topo
    rgb = bytearray()
    for row in page:
        line = b''.join(bytes(P.RGB[c]) * scale for c in row)
        rgb += line * scale
    topo.png(str(path), len(page[0]) * scale, len(page) * scale, rgb)


def ridge(heading, base=110, amp=18):
    """A synthetic ridge profile (tops of 140 columns), deterministic."""
    return [max(0, min(VIEW_ROWS, base + round(amp * math.sin((heading + c) / 23.0)
                                                  + amp / 2 * math.sin((heading + 3 * c) / 9.0))))
            for c in range(140)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', type=Path, default=HERE / 'build/stars')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    day, minute = 125, 23 * 60                  # 6 May, 23 h
    for r, (name, lat, lon) in REGIONS.items():
        vis = visible(day, minute, lat, lon)
        png(a.out / f'panorama_r{r}.png', panorama(day, minute, lat, lon))
        print(f'{name:17} lat {lat:+3} lon {lon:+4}: {len(vis)} stars; '
              + ' / '.join(look_stars(day, minute, lat, lon, 'night dark', False)))
    for name, (lat, lon), heading in (('sierra_south', REGIONS[2][1:], 280),
                                       ('sierra_north', REGIONS[2][1:], 0),
                                       ('bolivia_south', REGIONS[5][1:], 280)):
        tops = ridge(heading)
        _, _, _, srt = resident(visible(day, minute, lat, lon))
        page = frame(heading, tops, 'night dark', srt, 0xC0)
        for col in range(140):                  # preview only: the ground in grey
            for r in range(max(HUD_ROWS, tops[col]), VIEW_ROWS):
                page[r][col] = P.GREY1
        png(a.out / f'view_{name}.png', page[16:160], scale=4)
    print(f'previews in {a.out}')


if __name__ == '__main__':
    main()
