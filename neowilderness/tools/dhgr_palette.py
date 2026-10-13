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

# ---------------------------------------------------------------------------
# Region palettes (lot 7, docs/SCENARIOS.md section 5): per region and mood,
# the entries that replace the Sierra Nevada's ground, snow, water and woods
# crowns. Sky zones, sun, ridge (the engine never paints it: render_ridge
# keeps the cleared black, wild.s), outline, trunk, sprite shades and the
# four night moods stay those of MOOD above, as do civil and nautical
# twilight (their ground is already black). Region 2 is MOOD itself.
REGION_NAMES = {1: 'british columbia', 2: 'sierra nevada', 3: 'burma',
                4: 'new guinea', 5: 'bolivia', 6: 'chile'}
_JUNGLE_WATER = dict(day=((BROWN, ORANGE), BROWN, (BROWN, DARK_BLUE)),       # muddy rivers
                     overcast=(BROWN, (BROWN, DARK_BLUE), DARK_BLUE),
                     golden=((ORANGE, BROWN), (BROWN, MAGENTA), PURPLE))
REGIONS = {
    # Boreal forest: dark spruce and fir, grey distance, low blue-white snow.
    1: {'day': dict(ground=((GREEN, DARK_GREEN), DARK_GREEN, (DARK_GREEN, DARK_BLUE)),
                    snow=(WHITE, (WHITE, LIGHT_BLUE), LIGHT_BLUE),
                    crown=(DARK_GREEN, BLACK)),
        'overcast': dict(ground=(DARK_GREEN, (DARK_GREEN, BLACK), GREY1),
                         snow=(GREY2, (GREY2, LIGHT_BLUE), (GREY2, DARK_BLUE)),
                         crown=(BLACK, DARK_GREEN)),
        'golden': dict(ground=((BROWN, DARK_GREEN), (DARK_GREEN, MAGENTA), PURPLE),
                       crown=(DARK_GREEN, BLACK)),
        'overcast dusk': dict(ground=(DARK_GREEN, DARK_BLUE, DARK_BLUE))},
    2: {},
    # Monsoon jungle: bright teak and bamboo canopy, red earth, brown rivers.
    3: {'day': dict(ground=((GREEN, BROWN), (DARK_GREEN, GREEN), DARK_GREEN),
                    water=_JUNGLE_WATER['day'], crown=(GREEN, YELLOW)),
        'overcast': dict(ground=((DARK_GREEN, BROWN), DARK_GREEN, GREY1),
                         water=_JUNGLE_WATER['overcast'], crown=(DARK_GREEN, GREEN)),
        'golden': dict(ground=((ORANGE, GREEN), (BROWN, DARK_GREEN), PURPLE),
                       water=_JUNGLE_WATER['golden'], crown=(GREEN, BROWN))},
    # Rainforest: deep wet greens with a teal sheen, brown rivers.
    4: {'day': dict(ground=((DARK_GREEN, GREEN), DARK_GREEN, (DARK_GREEN, DARK_BLUE)),
                    water=_JUNGLE_WATER['day'], crown=(GREEN, AQUA)),
        'overcast': dict(ground=(DARK_GREEN, (DARK_GREEN, DARK_BLUE), GREY1),
                         water=_JUNGLE_WATER['overcast'], crown=(DARK_GREEN, AQUA)),
        'golden': dict(ground=((BROWN, GREEN), (DARK_GREEN, MAGENTA), PURPLE),
                       water=_JUNGLE_WATER['golden'], crown=(GREEN, DARK_GREEN))},
    # Altiplano: ochre and straw grass, white Andean peaks, yungas below.
    5: {'day': dict(ground=((YELLOW, BROWN), (BROWN, ORANGE), (BROWN, GREY1)),
                    snow=(WHITE, WHITE, WHITE), crown=(DARK_GREEN, GREEN)),
        'overcast': dict(ground=((BROWN, YELLOW), BROWN, GREY1), crown=(DARK_GREEN, BLACK)),
        'golden': dict(ground=((ORANGE, YELLOW), (ORANGE, BROWN), (BROWN, PURPLE)),
                       crown=(BROWN, DARK_GREEN)),
        'sunset': dict(ground=((BROWN, ORANGE), MAGENTA, PURPLE)),
        'overcast dusk': dict(ground=(BROWN, (BROWN, DARK_BLUE), DARK_BLUE))},
    # Atacama to Patagonia: arid sand and grey scree, grey-green cactus.
    6: {'day': dict(ground=((ORANGE, BROWN), (BROWN, GREY1), GREY1),
                    snow=(WHITE, (WHITE, GREY2), GREY2), crown=(GREEN, GREY1)),
        'overcast': dict(ground=((BROWN, GREY1), GREY1, (GREY1, DARK_BLUE)),
                         crown=(DARK_GREEN, GREY1)),
        'golden': dict(ground=((ORANGE, BROWN), (BROWN, PURPLE), PURPLE), crown=(GREEN, BROWN)),
        'overcast dusk': dict(ground=(BROWN, (GREY1, DARK_BLUE), DARK_BLUE))},
}


def mood(name, region=2):
    """The colour roles of a mood in a region: MOOD with REGIONS overrides."""
    return dict(MOOD[name], **REGIONS[region].get(name, {}))

# Original sprite codes 0 black, 1 violet, 2 green, 3 white -> DHGR colours
# (day colours; the mood shade is applied on top).
SPRITES = {
    'wreck': (BLACK, MAGENTA, GREEN, WHITE),
    'bear': (BLACK, BROWN, BROWN, GREY2),
    'cougar': (BLACK, BROWN, ORANGE, YELLOW),
    'rattlesnake': (BLACK, BROWN, YELLOW, WHITE),
    'cabin': (BLACK, BROWN, DARK_GREEN, YELLOW),
    # Lot 7: the animals of the five other regions (codes 0..3 of each
    # sprite; build/original_graphics/NAME.png shows the original art).
    'grizzly_bc': (BLACK, ORANGE, BROWN, YELLOW),   # brown fur, golden tips
    'wolf_bc': (BLACK, GREY1, BROWN, WHITE),        # grey timber wolf
    'moose_bc': (BLACK, ORANGE, BROWN, GREY2),      # dark coat, pale antlers
    'tiger': (BLACK, BROWN, ORANGE, WHITE),         # orange, white belly
    'elephant': (BLACK, GREY1, GREY2, WHITE),       # grey hide, white tusks
    'cobra': (BLACK, ORANGE, BROWN, YELLOW),        # brown, pale hood
    'python': (BLACK, DARK_GREEN, BROWN, YELLOW),   # brown and yellow blotches
    'dani': (BLACK, BROWN, ORANGE, WHITE),          # skin, ochre, white ornaments
    'adder': (BLACK, ORANGE, BROWN, GREY2),         # banded death adder
    'crocodile': (BLACK, PINK, BROWN, YELLOW),      # olive brown, pink mouth
    'puma': (BLACK, BROWN, ORANGE, YELLOW),         # as the cougar
    'jaguar': (BLACK, BROWN, YELLOW, ORANGE),       # gold with rosettes
    'ferdelance': (BLACK, GREY1, BROWN, YELLOW),    # brown, pale diamonds
    'anaconda': (BLACK, BROWN, DARK_GREEN, YELLOW), # olive green, dark spots
    'cat': (BLACK, BROWN, GREY2, WHITE),            # grey Andean cat
}
# Sprite of each animal record of a region (species 1-4), from the global
# animal id of the MS-DOS .CIM files (build/regions/fauna.json); Chile
# reuses Bolivia's puma. tools/build_disk.py loads them as modules 6, 7, 8
# and 23; gendhgr.py gives their colours to dhgr_assets.
REGION_ANIMALS = {1: ('grizzly_bc', 'wolf_bc', 'moose_bc'),
                  2: ('bear', 'cougar', 'rattlesnake'),
                  3: ('tiger', 'elephant', 'cobra', 'python'),
                  4: ('dani', 'adder', 'crocodile'),
                  5: ('puma', 'jaguar', 'ferdelance', 'anaconda'),
                  6: ('puma', 'cat')}


def region_assets(region=2):
    """Names of the dhgr_assets slots: overlays 5..9, then module 23."""
    animals = REGION_ANIMALS[region] + (None,) * (4 - len(REGION_ANIMALS[region]))
    return ('wreck',) + animals[:3] + ('cabin', animals[3])


HUD = {'ribbon': DARK_BLUE, 'ink': WHITE, 'paper': BLACK, 'pointer': YELLOW}


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

    def __init__(self, mood, moon8=127, region=2):
        self.mood, self.t = mood, globals()['mood'](mood, region)
        self.moon8, self.region = moon8, region

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


def mood_table(region=2):
    """Resident bytes of the asm tables (see docs/DHGR.md): per mood 19
    entries (sky 3, ground 3, snow 3, water 3, ridge, outline, trunk, crown
    odd/even, sun, shade index), then the distinct shade tables (16 bytes)."""
    shades = []
    out = bytearray()
    for m in MOODS:
        t = mood(m, region)
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
