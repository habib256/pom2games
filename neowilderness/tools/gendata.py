#!/usr/bin/env python3
"""gendata.py: data tables of the game logic (src/game.s), as build/gamedata.inc.

- vocabulary: the 280 command words of the original (word, class 0 verb /
  1 qualifier / 2 noun, number), as lists per word length like the original
  parser (voc_len[n] -> list of n-letter entries: letters, code; $FF ends a
  list). One code byte holds class and number: nouns 1..197 as is, verbs
  200 + number (201..244), qualifiers 245 + number (246..255);
- items 1..75 at the start of the first journey (docs/logic/state.md):
  place, total ounces, volume, ounces on the ground, ounces in the pack (or
  uses), kcal per ounce (food) or body part (clothes), and the INVENTORY
  name;
- floating-point constants in the Applesoft 5-byte format.
"""
import math, sys

VOCAB = [('FILL',0,1),('REFILL',0,1),
    ('N',2,145),('E',2,146),('S',2,147),('W',2,148),('U',2,149),('D',2,150),
    ('R',2,151),('L',2,152),('F',2,156),('B',2,157),('T',2,103),('V',2,104),
    ('H',1,10),('GO',0,22),('UP',2,149),('AZ',2,155),('GET',0,1),('USE',0,2),
    ('FRY',0,11),('EAT',0,12),('DRY',0,13),('RUN',0,23),('ROW',0,28),
    ('CUT',0,31),('WET',0,33),('PAN',0,36),('BAG',2,1),('PAD',2,10),
    ('HAT',2,19),('KIT',2,41),('TAB',2,46),('MAP',2,52),('GUN',2,57),
    ('AXE',2,58),('BOW',2,89),('HUT',2,95),('INV',2,106),('ARM',2,111),
    ('LEG',2,112),('SUN',2,153),('ICE',2,171),('FER',2,194),('CAT',2,197),
    ('FIND',0,1),('MAKE',0,3),('SKIN',0,4),('WEAR',0,5),('PACK',0,6),
    ('TAKE',0,7),('DROP',0,8),('BOIL',0,9),('COOK',0,11),('WARM',0,13),
    ('COOL',0,14),('HEAL',0,15),('CURE',0,15),('LOOK',0,16),('KILL',0,17),
    ('WAIT',0,19),('REST',0,20),('CAMP',0,21),('WALK',0,22),('SWIM',0,24),
    ('STOP',0,26),('MOVE',0,27),('SUCK',0,32),('HANG',0,34),('SCAN',0,36),
    ('SKIP',0,37),('FLAG',0,38),('EXIT',0,39),('WOOL',1,1),('SALT',1,7),
    ('HALF',1,10),('TENT',2,9),('NUTS',2,23),('EGGS',2,24),('BARS',2,25),
    ('RICE',2,27),('PEAS',2,31),('TUNA',2,35),('FUEL',2,40),('SOAP',2,51),
    ('ROPE',2,60),('GEAR',2,67),('RAFT',2,70),('BOAT',2,70),('TRAP',2,72),
    ('GAME',2,80),('FISH',2,81),('FIRE',2,88),('CLUB',2,91),('ROCK',2,92),
    ('HIDE',2,94),('CITY',2,100),('TOPO',2,103),('VIEW',2,104),('HELP',2,107),
    ('CLUE',2,108),('CUTS',2,110),('BITE',2,117),('FOOD',2,135),('LAKE',2,144),
    ('EAST',2,146),('WEST',2,148),('DOWN',2,150),('LEFT',2,152),('BACK',2,157),
    ('BODY',2,158),('EYES',2,160),('HEAD',2,163),('COLD',2,166),('HEAT',2,167),
    ('WIND',2,168),('RAIN',2,169),('SNOW',2,170),('TREE',2,173),('BAIT',2,175),
    ('STAT',2,105),('BEAR',2,76),('WOLF',2,77),('PUMA',2,192),('CROC',2,190),
    ('DANI',2,188),('GOLD',2,75),('SAVE',0,41),('ENTER',0,40),('CATCH',0,1),
    ('BUILD',0,3),('STORE',0,6),('CARRY',0,7),('DRINK',0,10),('TREAT',0,15),
    ('SCARE',0,18),('PAUSE',0,19),('SLEEP',0,20),('CLIMB',0,25),('DOUSE',0,26),
    ('LOWER',0,29),('TASTE',0,35),('LEAVE',0,39),('CRAWL',0,43),('COTTN',1,2),
    ('IODIN',1,6),('PARKA',2,2),('PANTS',2,4),('BOOTS',2,5),('SOCKS',2,6),
    ('COVER',2,11),('JEANS',2,15),('SHOES',2,17),('WATER',2,22),('BACON',2,26),
    ('BREAD',2,34),('BEANS',2,36),('GLASS',2,39),('WATCH',2,54),('CHART',2,56),
    ('KNIFE',2,59),('STOVE',2,71),('FRUIT',2,83),('CACTI',2,84),('SPEAR',2,90),
    ('IGLOO',2,96),('SHOCK',2,113),('RIVER',2,144),('NORTH',2,145),
    ('SOUTH',2,147),('RIGHT',2,151),('STARS',2,154),('AHEAD',2,156),
    ('VENOM',2,161),('COBRA',2,186),('ADDER',2,189),('TIGER',2,184),
    ('MOOSE',2,78),('SCRUB',2,176),('SHIELD',0,30),('REMOVE',0,8),
    ('ATTACK',0,17),('PADDLE',0,28),('SAMPLE',0,35),('IGNORE',0,37),
    ('COTTON',1,2),('SEWING',1,5),('IODINE',1,6),('JERSEY',2,14),
    ('SHORTS',2,16),('GLOVES',2,20),('CHEESE',2,28),('APPLES',2,37),
    ('FLAGYL',2,47),('OXYGEN',2,49),('PITONS',2,61),('STATUE',2,75),
    ('PLANTS',2,86),('STICKS',2,87),('SPLINT',2,93),('TRENCH',2,97),
    ('STATUS',2,105),('THREAT',2,129),('HAZARD',2,130),('DANGER',2,131),
    ('INJURY',2,138),('RESCUE',2,142),('SHADOW',2,174),('NATURE',2,177),
    ('COUGAR',2,181),('PYTHON',2,187),('JAGUAR',2,193),('FRSTAID',1,3),
    ('SNAKEBT',1,4),('MITTENS',2,7),('SWEATER',2,8),('GAITERS',2,13),
    ('CARROTS',2,29),('RAISINS',2,32),('BOLOGNA',2,33),('MATCHES',2,38),
    ('TABLETS',2,46),('QUININE',2,50),('COMPASS',2,53),('CANTEEN',2,64),
    ('INSECTS',2,82),('OUTPOST',2,99),('SUNBURN',2,114),('GIARDIA',2,121),
    ('MALARIA',2,122),('CLOTHES',2,136),('SHELTER',2,137),('ILLNESS',2,139),
    ('WEATHER',2,143),('AZIMUTH',2,155),('FORWARD',2,156),('RATTLER',2,182),
    ('RESTORE',0,42),('EXERCISE',0,44),('FIRSTAID',1,3),('RAINCOAT',2,12),
    ('BACKPACK',2,21),('POTATOES',2,30),('CRAMPONS',2,62),('UTENSILS',2,73),
    ('TRINKETS',2,74),('AIRPLANE',2,98),('SICKNESS',2,126),('BACKWARD',2,157),
    ('BLEEDING',2,159),('PRESSURE',2,162),('CANNIBAL',2,188),('ELEPHANT',2,185),
    ('ANACONDA',2,195),('SNAKEBITE',1,4),('BALACLAVA',2,3),('CANDYBARS',2,25),
    ('SUNSCREEN',2,44),('REPELLENT',2,45),('ALTIMETER',2,55),('SNOWSHOES',2,63),
    ('MUSHROOMS',2,85),('INVENTORY',2,106),('BLINDNESS',2,115),
    ('FROSTBITE',2,116),('INFECTION',2,118),('POISONING',2,120),
    ('DIRECTION',2,140),('CROCODILE',2,190),('SUNGLASSES',2,43),
    ('FLASHLIGHT',2,66),('BINOCULARS',2,68),('DEFICIENCY',2,119),
    ('STARVATION',2,124),('EXHAUSTION',2,125),('PROTECTION',2,141),
    ('FERDELANCE',2,194),('THERMOMETER',2,69),('DEHYDRATION',2,123),
    ('HYPOTHERMIA',2,127),('RATTLESNAKE',2,182),('HYPERTHERMIA',2,128),
]

PLACE = {None: 0xFF, 'GND': 0, 'WEAR': 1, 'PACK': 2, 'CARRY': 3, 'BOTH': 4}
ITEMS = [  # id, name, place, oz, volume in3, oz on ground, oz in pack / uses, kcal/oz or body part
    (1, 'SLPNG BAG', None, 64, 518, 0, 9, 1),
    (2, 'DOWN PARKA', 'PACK', 24, 180, 0, 3, 2),
    (3, 'BALACLAVA', 'WEAR', 5, 52, 0, 1, 3),
    (4, 'WOOL PANTS', 'WEAR', 32, 173, 0, 3, 4),
    (5, 'BOOTS', 'WEAR', 80, 104, 0, 3, 5),
    (6, 'WOOL SOCKS', 'WEAR', 8, 86, 0, 1, 5),
    (7, 'MITTENS', 'WEAR', 10, 35, 0, 1, 6),
    (8, 'SWEATER', 'WEAR', 16, 121, 0, 3, 2),
    (9, 'TENT', 'PACK', 64, 518, 30, 18, 1),
    (10, 'ENSOL PAD', 'GND', 24, 432, 0, 3, 2),
    (11, 'GND COVER', 'GND', 45, 200, 0, 15, 2),
    (12, 'RAINCOAT', 'PACK', 16, 60, 0, 6, 2),
    (13, 'GAITERS', None, 5, 52, 0, 2, 5),
    (14, 'JERSEY', 'WEAR', 5, 52, 0, 3, 2),
    (15, 'JEANS', 'GND', 24, 121, 0, 3, 4),
    (16, 'SHORTS', 'GND', 4, 40, 0, 2, 4),
    (17, 'SHOES', None, 26, 40, 0, 2, 5),
    (18, 'COTTN SOCKS', 'GND', 5, 52, 0, 1, 5),
    (19, 'HAT', 'GND', 2, 35, 0, 1, 3),
    (20, 'GLOVES', 'GND', 10, 40, 0, 1, 6),
    (21, 'BACKPACK', 'CARRY', 64, 60, 0, 3, 2),
    (22, 'WATER', 'BOTH', 128, 2, 64, 64, 0),
    (23, 'NUTS', None, 48, 1, 48, 0, 160),
    (24, 'EGGS', 'PACK', 16, 1, 0, 16, 168),
    (25, 'CANDYBARS', 'GND', 16, 1, 16, 0, 141),
    (26, 'BACON', 'GND', 16, 1, 16, 0, 125),
    (27, 'RICE', None, 48, 2, 48, 0, 110),
    (28, 'CHEESE', 'BOTH', 48, 2, 16, 32, 110),
    (29, 'CARROTS', 'GND', 16, 1, 16, 0, 100),
    (30, 'POTATOES', 'BOTH', 80, 2, 48, 32, 100),
    (31, 'PEAS', None, 32, 1, 32, 0, 93),
    (32, 'RAISINS', 'BOTH', 24, 1, 8, 16, 81),
    (33, 'BOLOGNA', 'BOTH', 48, 1, 32, 16, 80),
    (34, 'BREAD', None, 32, 3, 32, 0, 70),
    (35, 'TUNA', 'PACK', 16, 2, 0, 16, 47),
    (36, 'BEANS', 'BOTH', 80, 2, 48, 32, 35),
    (37, 'APPLES', 'BOTH', 80, 2, 48, 32, 13),
    (38, 'MATCHES', 'PACK', 1, 2, 0, 24, 0),
    (39, 'MAGNF GLASS', 'GND', 1, 2, 0, 0, 0),
    (40, 'FUEL', 'PACK', 8, 69, 0, 8, 0),
    (41, 'FRSTAID KIT', None, 4, 35, 30, 0, 1),
    (42, 'SNAKEBT KIT', 'PACK', 1, 5, 30, 0, 8),
    (43, 'SUNGLASSES', 'PACK', 2, 3, 0, 0, 6),
    (44, 'SUNSCREEN', 'GND', 4, 12, 0, 7, 5),
    (45, 'REPELLENT', 'PACK', 3, 7, 0, 10, 0),
    (46, 'IODIN TAB', None, 1, 2, 30, 12, 0),
    (47, 'FLAGYL', 'PACK', 1, 2, 0, 12, 0),
    (48, 'SALT TAB', 'GND', 1, 2, 0, 12, 0),
    (49, 'OXYGEN', 'GND', 320, 900, 15, 17, 0),
    (50, 'QUININE', 'GND', 2, 3, 0, 14, 0),
    (51, 'SOAP', None, 4, 8, 0, 31, 1),
    (52, 'TOPO MAP', 'CARRY', 0, 0, 0, 0, 0),
    (53, 'COMPASS', 'PACK', 1, 1, 0, 0, 4),
    (54, 'WATCH', 'WEAR', 2, 1, 0, 0, 6),
    (55, 'ALTIMETER', 'PACK', 2, 7, 0, 0, 0),
    (56, 'STAR CHART', None, 0, 0, 0, 0, 6),
    (57, 'GUN', None, 50, 100, 0, 18, 10),
    (58, 'AXE', 'PACK', 32, 52, 0, 0, 5),
    (59, 'KNIFE', 'PACK', 8, 10, 0, 0, 3),
    (60, 'ROPE', 'PACK', 32, 340, 30, 0, 10),
    (61, 'PITONS/CARB', 'GND', 48, 103, 30, 0, 7),
    (62, 'CRAMPONS', None, 21, 52, 0, 0, 2),
    (63, 'SNOWSHOES', 'GND', 64, 600, 0, 0, 0),
    (64, '2QT CANTEEN', 'CARRY', 80, 144, 0, 0, 0),
    (65, 'SEWING KIT', None, 2, 5, 0, 0, 0),
    (66, 'FLASHLGHT', 'PACK', 11, 43, 0, 6, 0),
    (67, 'FISHNG GEAR', 'PACK', 55, 110, 0, 0, 0),
    (68, 'BINOCULARS', None, 20, 70, 0, 0, 0),
    (69, 'THERMOMETER', 'PACK', 1, 1, 0, 0, 0),
    (70, 'RAFT', 'GND', 96, 400, 30, 0, 0),
    (71, 'STOVE', None, 32, 120, 30, 0, 0),
    (72, 'TRAP', 'GND', 48, 100, 0, 0, 0),
    (73, 'UTENSILS', 'PACK', 16, 120, 15, 0, 0),
    (74, 'TRINKETS', 'GND', 12, 12, 0, 6, 0),
    (75, 'GOLD', None, 370, 82, 0, 0, 0),
]

FLOATS = {     # name: value
    'f_zero': 0.0, 'f_one': 1.0, 'f_half': 0.5, 'f_60': 60.0, 'f_24': 24.0, 'f_100': 100.0,
    'f_hmax': 7.866609670221806, 'f_dead': 0.3, 'f_body': 98.6,
    'f_tol_water': 190.5, 'f_tol_food': 480.0, 'f_tol_rest': 68.0,
    'f_deg_heading': 560 / 360,
    # Original T08/S07 $5CF6 stores .06 as 7C 75 C2 8F 5D (one bit
    # above the nearest Python encoding); preserve its ROM arithmetic.
    'f_shiver_k':.04, 'f_swim_k':.06000000001222361,
    'f_rest_rate': 1.65,
    # T0F/S00: .73 - .6 * saved $4C7A (.5833333). The evolving
    # perspiration factor still needs porting; this is the initial credit.
    'f_oz_hour': 0.38, 'f_eat_rate': 2.31,
    'f_goal_k': -2.5, 'f_goal_v': 0.6, 'f_2pi': 2 * math.pi, 'f_quarter': 0.25,
    'f_0_398': 0.398, 'f_1_378': 1.378, 'f_12_pi': 3.82, 'f_rad': math.pi / 180,
    'f_twilight': 0.75, 'f_6': 6.0, 'f_18': 18.0, 'f_12': 12.0, 'f_15': 15.0,
    'f_inv60': 1 / 60, 'f_inv_year': 1 / 525600, 'f_third': 1 / 3,
    'f_half_pi': math.pi / 2, 'f_0_2': 0.2, 'f_0_15': 0.15, 'f_4': 4.0, 'f_365': 365.0,
    'f_5': 5.0, 'f_16': 16.0, 'f_7': 7.0, 'f_0_2236': 0.2236, 'f_2': 2.0,
}


THERMAL_FLOATS = {
    'th_500':500., 'th_200':200., 'th_surface':6058., 'th_10':10.,
    'th_20':20., 'th_inv6':1/6, 'th_9':9., 'th_55':55., 'th_80':80.,
    'th_a':0.0006058, 'th_inv12':1/12, 'th_0_1':.1, 'th_0_017':.017,
    'th_0_012':.012, 'th_0_027':.027,
    'th_water_k':.3, 'th_2000':2000.,
}


def fp(v):
    """Applesoft 5-byte float: exponent (bias $80, 0 = zero), 4 mantissa
    bytes, the sign in bit 7 of the first (where the implicit 1 sits)."""
    if v == 0:
        return bytes(5)
    m, e = math.frexp(abs(v))            # v = m * 2^e, 0.5 <= m < 1
    mant = int(round(m * 2 ** 32))
    if mant >= 2 ** 32:
        mant >>= 1
        e += 1
    mant &= 0x7FFFFFFF
    if v < 0:
        mant |= 0x80000000
    return bytes([e + 0x80]) + mant.to_bytes(4, 'big')


def byte_rows(name, values):
    out = [f'{name}:']
    for k in range(0, len(values), 16):
        out.append('        .byte   ' + ', '.join(f'${v & 255:02X}' for v in values[k:k + 16]))
    return out


def main():
    out = ['; generated by tools/gendata.py', '.segment "VOCAB"']
    # vocabulary by length
    out.append('voc_len_lo:')
    out.append('        .byte   ' + ', '.join(f'<voc_{n}' for n in range(1, 13)))
    out.append('voc_len_hi:')
    out.append('        .byte   ' + ', '.join(f'>voc_{n}' for n in range(1, 13)))
    for n in range(1, 13):
        out.append(f'voc_{n}:')
        for w, c, k in VOCAB:
            if len(w) == n:
                code = (k, 200 + k, 245 + k)[(2, 0, 1).index(c)]
                out.append(f'        .byte   "{w}", {code}')
        out.append('        .byte   $FF')
    out.append('.segment "GDATA"')
    # The 6502 load calculator multiplies food volume by 1..3.
    assert all(1 <= it[4] <= 3 for it in ITEMS if 22 <= it[0] < 38)
    # items 0..75 (0 unused)
    rows = {it[0]: it for it in ITEMS}
    get = lambda i, k, d=0: rows[i][k] if i in rows else d
    out += byte_rows('it_place', [PLACE[get(i, 2, None)] for i in range(76)])
    for k, name in ((3, 'it_oz'), (4, 'it_vol'), (5, 'it_gnd'), (6, 'it_pack')):
        vals = [get(i, k) for i in range(76)]
        out += byte_rows(name + '_lo', [v & 255 for v in vals])
        out += byte_rows(name + '_hi', [(v >> 8) & 255 for v in vals])
    out += byte_rows('it_kcal', [get(i, 7) for i in range(76)])
    out.append('.segment "LOWTEXT"   ; names: $1000-$1FFF, room is short in $4000')
    out += byte_rows('it_x', [0] * 76)
    out += byte_rows('it_y', [0] * 76)
    out.append('it_name_lo:')
    out.append('        .byte   ' + ', '.join(f'<it_n{i}' for i in range(76)))
    out.append('it_name_hi:')
    out.append('        .byte   ' + ', '.join(f'>it_n{i}' for i in range(76)))
    for i in range(76):
        out.append(f'it_n{i}:  .byte   "{get(i, 1, "")}", 0')
    out.append('.segment "RODATA"    ; constants: $6000-$6FFF')
    for name, v in FLOATS.items():
        out.append(f'{name}: .byte   ' + ', '.join(f'${b:02X}' for b in fp(v)) + f'   ; {v}')
    out.append('.segment "THERMAL"')
    for name, v in THERMAL_FLOATS.items():
        if name in ('th_surface', 'th_a'):
            out += ['.pushseg', '.segment "GDATA"']
        out.append(f'{name}: .byte ' + ', '.join(f'${b:02X}' for b in fp(v)))
        if name in ('th_surface', 'th_a'):
            out.append('.popseg')
    open(sys.argv[1], 'w').write('\n'.join(out) + '\n')


if __name__ == '__main__':
    main()
