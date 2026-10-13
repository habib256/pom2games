#!/usr/bin/env python3
"""dhgr_palette.py: the 16 DHGR colours and the Neowilderness colour roles.

Colour numbers are the LORES numbers (Apple IIe Technical Note #3). A DHGR
colour pixel is 4 consecutive bits of the 560-bit scanline. Bit j of pixel k
(bit 4k + j of a 28-bit group: aux even, main even, aux odd, main odd, 7 bits
each, least significant first) is bit j of rot(c) = ((c >> 1) | (c << 3)) & 15,
the same rotation as dev/lib/hgrc/dhgr_pattern.c.

RGB values are those rendered by the POM2 core (a2shot --iie shot of the
sixteen bars written by src/dhgr_test.s), so previews match the emulator.
Roles are decisions of docs/DHGR.md; changing one changes the reference
frames of tools/dhgr_ref.py, never the projection.
"""

BLACK, MAGENTA, DARK_BLUE, PURPLE, DARK_GREEN, GREY1, MEDIUM_BLUE, LIGHT_BLUE = range(8)
BROWN, ORANGE, GREY2, PINK, GREEN, YELLOW, AQUA, WHITE = range(8, 16)
NAMES = ('black', 'magenta', 'dark blue', 'purple', 'dark green', 'grey 1',
         'medium blue', 'light blue', 'brown', 'orange', 'grey 2', 'pink',
         'green', 'yellow', 'aqua', 'white')

# Measured on POM2 (see module docstring); tests/test_dhgr_cols.py re-checks them.
RGB = ((0, 0, 0), (167, 11, 64), (64, 28, 247), (230, 40, 255),
       (0, 116, 64), (128, 128, 128), (25, 144, 255), (191, 156, 255),
       (64, 99, 0), (230, 111, 0), (128, 128, 128), (255, 139, 191),
       (25, 215, 0), (191, 227, 8), (88, 244, 191), (255, 255, 255))


def rot(c):
    """Bit order of colour c inside its 4-bit DHGR cell."""
    c &= 15
    return ((c >> 1) | (c << 3)) & 15


def pattern(c):
    """Four bytes (aux even, main even, aux odd, main odd) of a solid colour c."""
    bits = rot(c) * 0x1111111          # 28 bits: seven cells
    return tuple((bits >> (7 * j)) & 0x7F for j in range(4))


PATTERNS = tuple(pattern(c) for c in range(16))

# ---------------------------------------------------------------------------
# Moods. One mood is chosen per frame (select_mood); it is a small table of
# colour entries indexed by band kind, so the renderer does one lookup per
# span. An entry is either a colour or a pair (a, b) dithered as a
# checkerboard: a where (row + column) is even, b where it is odd. The asm
# stores each entry as one byte a << 4 | b (a == b: solid colour).
#
# Distances are ray steps n (1 step = 1 map cell = 2 world units):
NEAR, MID = 16, 48              # tier 0: n <= 16, tier 1: n <= 48, tier 2 beyond
# Sky template rows (logical): zenith, zenith/mid dither, mid, mid/glow
# dither, horizon glow (also below the horizon when looking down).
SKY_ROWS = (32, 48, 72, 84)

# Altitudes in S8 units: round(128 * sin(altitude)), i.e. sky_up * 128.
SUN_DAY, SUN_GOLDEN, SUN_HORIZON, SUN_CIVIL, SUN_NAUTICAL = 22, 4, -2, -13, -27
#   >= 22  ( >= 10 deg)   day / overcast
#   >= 4   ( >= 2 deg)    golden hour        (overcast: overcast dusk)
#   >= -2  ( >= -1 deg)   sunrise / sunset   (overcast: overcast dusk)
#   >= -13 ( >= -6 deg)   civil twilight     (overcast: nautical)
#   >= -27 ( >= -12 deg)  nautical twilight
#   below                 night, by moonlight
MOON_LOW = 22                   # moon below 10 deg: dimmer light, pale yellow disk
LIGHT_BRIGHT, LIGHT_DIM = 9, 6  # moonlight thresholds, see select_mood

MOODS = ('day', 'overcast', 'golden', 'sunset', 'overcast dusk', 'civil',
         'nautical', 'night bright', 'night dim', 'night dark')


def select_mood(sun8, moon8=-128, phase=0, clouds=False):
    """Mood from the sun altitude, moon altitude/phase (sky_inner sample
    0..11, 11 = full disk) and weather_sky != 0. Integer compares only."""
    if sun8 >= SUN_DAY:
        return 'overcast' if clouds else 'day'
    if sun8 >= SUN_HORIZON:
        if clouds:
            return 'overcast dusk'
        return 'golden' if sun8 >= SUN_GOLDEN else 'sunset'
    if sun8 >= SUN_CIVIL:
        return 'nautical' if clouds else 'civil'
    if sun8 >= SUN_NAUTICAL:
        return 'nautical'
    light = moon_light(moon8, phase, clouds)
    return 'night bright' if light >= LIGHT_BRIGHT else 'night dim' if light >= LIGHT_DIM else 'night dark'


def moon_light(moon8, phase, clouds=False):
    """Moonlight 0..11: the phase sample, -2 when the Moon is low, -3 under clouds."""
    if moon8 <= 0:
        return 0
    light = phase - (2 if moon8 < MOON_LOW else 0) - (3 if clouds else 0)
    return max(light, 0)


# Sprite shades: original-colour -> lit colour, per mood (None: hidden).
SHADE_DAY = tuple(range(16))
SHADE_WARM = (0, 1, 3, 3, 8, 8, 3, 11, 8, 9, 11, 11, 8, 9, 11, 9)
SHADE_SILHOUETTE = (0,) * 16
SHADE_MOON = (0, 2, 2, 2, 4, 5, 2, 10, 8, 8, 10, 10, 4, 10, 2, 10)
SHADE_DIM = (0, 0, 2, 2, 0, 2, 2, 2, 0, 2, 2, 2, 2, 2, 2, 2)

_ = None
MOOD = {
    # sky (zenith, mid, glow); ground/snow/water (near, mid, far tier)
    'day': dict(sky=(MEDIUM_BLUE, MEDIUM_BLUE, LIGHT_BLUE),
                ground=(GREEN, DARK_GREEN, DARK_BLUE), snow=(WHITE, WHITE, GREY2),
                water=(AQUA, MEDIUM_BLUE, DARK_BLUE), ridge=BLACK,
                outline=BLACK, trunk=BROWN, crown=(GREEN, DARK_GREEN),
                sun=YELLOW, shade=SHADE_DAY),
    'overcast': dict(sky=(GREY1, GREY1, (GREY1, LIGHT_BLUE)),
                     ground=(DARK_GREEN, DARK_GREEN, GREY1), snow=(GREY2, GREY2, (GREY2, DARK_BLUE)),
                     water=(GREY1, DARK_BLUE, DARK_BLUE), ridge=BLACK,
                     outline=BLACK, trunk=BROWN, crown=(DARK_GREEN, BLACK),
                     sun=_, shade=SHADE_DAY),
    'golden': dict(sky=(MEDIUM_BLUE, LIGHT_BLUE, (PINK, YELLOW)),
                   ground=((ORANGE, BROWN), (BROWN, MAGENTA), PURPLE), snow=(PINK, PINK, PURPLE),
                   water=((ORANGE, PINK), (PINK, LIGHT_BLUE), PURPLE), ridge=BLACK,
                   outline=BLACK, trunk=BLACK, crown=(BROWN, DARK_GREEN),
                   sun=ORANGE, shade=SHADE_WARM),
    'sunset': dict(sky=(PURPLE, PINK, ORANGE),
                   ground=(BROWN, MAGENTA, PURPLE), snow=(PINK, PINK, PURPLE),
                   water=(ORANGE, (PINK, ORANGE), PURPLE), ridge=BLACK,
                   outline=BLACK, trunk=BLACK, crown=(BLACK, BLACK),
                   sun=MAGENTA, shade=SHADE_SILHOUETTE),
    'overcast dusk': dict(sky=(DARK_BLUE, GREY1, (GREY1, PINK)),
                          ground=(BROWN, DARK_BLUE, DARK_BLUE), snow=(GREY2, PURPLE, DARK_BLUE),
                          water=(GREY1, DARK_BLUE, DARK_BLUE), ridge=BLACK,
                          outline=BLACK, trunk=BLACK, crown=(BLACK, BLACK),
                          sun=_, shade=SHADE_WARM),
    'civil': dict(sky=(DARK_BLUE, PURPLE, PINK),
                  ground=((DARK_BLUE, BLACK), BLACK, BLACK), snow=(LIGHT_BLUE, PURPLE, DARK_BLUE),
                  water=(PINK, PURPLE, DARK_BLUE), ridge=BLACK,
                  outline=BLACK, trunk=BLACK, crown=(BLACK, BLACK),
                  sun=MAGENTA, shade=SHADE_SILHOUETTE),
    'nautical': dict(sky=(BLACK, (BLACK, DARK_BLUE), DARK_BLUE),
                     ground=(BLACK, BLACK, BLACK), snow=(DARK_BLUE, (DARK_BLUE, BLACK), BLACK),
                     water=((DARK_BLUE, BLACK), BLACK, BLACK), ridge=BLACK,
                     outline=BLACK, trunk=BLACK, crown=(BLACK, BLACK),
                     sun=_, shade=SHADE_DIM),
    'night bright': dict(sky=(BLACK, BLACK, (BLACK, DARK_BLUE)),
                         ground=(DARK_GREEN, (DARK_GREEN, DARK_BLUE), DARK_BLUE),
                         snow=(GREY2, LIGHT_BLUE, DARK_BLUE),
                         water=((DARK_BLUE, WHITE), DARK_BLUE, DARK_BLUE), ridge=BLACK,
                         outline=BLACK, trunk=BLACK, crown=(DARK_GREEN, BLACK),
                         sun=_, shade=SHADE_MOON),
    'night dim': dict(sky=(BLACK, BLACK, BLACK),
                      ground=((DARK_BLUE, BLACK), BLACK, BLACK), snow=((GREY1, BLACK), DARK_BLUE, BLACK),
                      water=((BLACK, DARK_BLUE), BLACK, BLACK), ridge=BLACK,
                      outline=BLACK, trunk=BLACK, crown=(BLACK, BLACK),
                      sun=_, shade=SHADE_DIM),
    'night dark': dict(sky=(BLACK, BLACK, BLACK),
                       ground=(BLACK, BLACK, BLACK), snow=(BLACK, BLACK, BLACK),
                       water=(BLACK, BLACK, BLACK), ridge=BLACK,
                       outline=BLACK, trunk=BLACK, crown=(BLACK, BLACK),
                       sun=_, shade=None),
}
MOON_HIGH, MOON_LOW_COLOUR = WHITE, YELLOW

# Original sprite codes 0 black, 1 violet, 2 green, 3 white -> DHGR colours
# (day colours; the mood shade is applied on top).
SPRITES = {
    'wreck': (BLACK, MAGENTA, GREEN, WHITE),
    'bear': (BLACK, BROWN, BROWN, GREY2),
    'cougar': (BLACK, BROWN, ORANGE, YELLOW),
    'rattlesnake': (BLACK, BROWN, YELLOW, WHITE),
    'cabin': (BLACK, BROWN, DARK_GREEN, YELLOW),
}
# Colour HUD (lot 4, tools/genhud.py): ribbon frame, letters (north apart),
# ticks and pointer; survival panels: plain ink, gauge inks OKAY / SO-SO /
# VERY (also poor health), alarm strip behind black letters (warnings).
HUD = {'border': WHITE, 'ink': WHITE, 'paper': BLACK, 'pointer': YELLOW,
       'north': PINK, 'tick': GREY1, 'okay': AQUA, 'soso': YELLOW, 'very': PINK,
       'alarm': ORANGE}


def tier(n):
    return 0 if n <= NEAR else 1 if n <= MID else 2


def pick(entry, row, col):
    """Colour of a mood entry at a pixel (checkerboard for pairs)."""
    if isinstance(entry, tuple):
        return entry[(row + col) & 1]
    return entry


def sky_colour(mood, row, col):
    zen, mid, glow = MOOD[mood]['sky']
    a, b, c, d = SKY_ROWS
    if row < a:
        e = zen
    elif row < b:
        e = (pick(zen, row, col), pick(mid, row, col))
    elif row < c:
        e = mid
    elif row < d:
        e = (pick(mid, row, col), pick(glow, row, col))
    else:
        e = glow
    return pick(e, row, col)


class Lighting:
    """Palette object used by dhgr_ref: colour of each band kind for one mood."""
    BLACK = BLACK

    def __init__(self, mood, moon8=127):
        self.mood, self.t = mood, MOOD[mood]
        self.moon8 = moon8

    def sky(self, row, col):
        return sky_colour(self.mood, row, col)

    def band(self, kind, n, row, col):
        return pick(self.t[kind][tier(n)], row, col)

    def ridge(self, row, col):
        return pick(self.t['ridge'], row, col)

    def tree(self, part, row, col, odd=False):
        if part == 'crown':
            return self.t['crown'][0 if odd else 1]
        return self.t[part]

    def sun(self):
        return self.t['sun']

    def moon(self):
        return MOON_LOW_COLOUR if self.moon8 < MOON_LOW else MOON_HIGH

    def sprite(self, c):
        shade = self.t['shade']
        return None if shade is None else shade[c]

    def sprite_colours(self, name):
        return None                     # converted sprites carry day colours


def entry_byte(e):
    return (e[0] << 4 | e[1]) if isinstance(e, tuple) else (e << 4 | e)


def mood_table():
    """Resident bytes of the asm tables (see docs/DHGR.md): per mood 19
    entries (sky 3, ground 3, snow 3, water 3, ridge, outline, trunk, crown
    odd/even, sun, shade index), then the distinct shade tables (16 bytes)."""
    shades = []
    out = bytearray()
    for m in MOODS:
        t = MOOD[m]
        for key in ('sky', 'ground', 'snow', 'water'):
            out += bytes(entry_byte(e) for e in t[key])
        out += bytes(entry_byte(t[k]) for k in ('ridge', 'outline', 'trunk'))
        out += bytes(entry_byte(c) for c in t['crown'])
        out.append(0xFF if t['sun'] is None else entry_byte(t['sun']))
        if t['shade'] is None:
            out.append(0xFF)
        else:
            if t['shade'] not in shades:
                shades.append(t['shade'])
            out.append(shades.index(t['shade']))
    for sh in shades:
        out += bytes(sh)
    return bytes(out)


def swatch_rgb(width=16):
    """A 16-bar swatch (width pixels per colour) as RGB rows, for docs."""
    row = b''.join(bytes(RGB[c]) * width for c in range(16))
    return row


if __name__ == '__main__':
    print(f'mood tables: {len(mood_table())} bytes')
    for c in range(16):
        p = PATTERNS[c]
        print(f'{c:2} {NAMES[c]:12} rot={rot(c):04b} bytes={" ".join(f"{b:02X}" for b in p)}'
              f'  rgb=#{"".join(f"{v:02X}" for v in RGB[c])}')
