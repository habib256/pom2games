#!/usr/bin/env python3
"""WARGALAGA II game logic, the reference for src/logic.s (logic_step).

Bit-exact oracle, as dirtbike/tools/physics.py: tests/test_game.py pokes the
same inputs into the 6502 at each logic step and compares the whole state.
Constants mirror the top of src/game.s; path bytes come from tools/paths.py.

One step, in this order: ship, shots, new shots (weapon, autofire), bombs,
falling objects, stars, entry waves, formation sway (one row every other
step), dive launcher, aliens (all frozen by the freeze bonus but for
explosions), flying list, shots against aliens (and drops), the ship
against bombs then aliens, pickups, enemy fire, ship and bonus timers,
level (end, teleport, next level).

Sub-games (lot 8), after the level whose icon was caught: Meteor Storm
(storm_step: the ship flies through falling rocks, fire held = faster) and
Memory Station (station: the game waits, the screen is shop.s's overlay;
its rules mem_deal / mem_turn here).

Levels (lot 6): 100, in 25 packs of 4; level 3 of a pack has big aliens
(lot 6, step 3), level 4 is a kamikaze level (even pack: aliens
dive at the ship) or a bonus level (odd pack: aliens fly past and
never fire, all 40 shot = a prize). A complete kamikaze wave pays a prize.
Levels 25/50/75/100 are boss
levels (step 4). Each pack is harder; after level 100 the game loops,
mirrored and harder still. Between two levels: TELEPORT_T steps.
"""
import paths

FIELD_TOP = 8
# Lot 10: walls of FIELD_COL bytes on each side (Warblade's frame); the
# field is the FIELD_CELLS cells between them, cell 0 at byte FIELD_COL.
# 4 bytes = 14 cells: the shifts and colours of a cell stay the same.
FIELD_COL = 4
FIELD_CELLS = 140 - 2 * (7 * FIELD_COL // 2)
SHIP_Y = 180
SHIP_MAX = FIELD_CELLS - 8      # 3 bytes from cell 104 end on byte 35 (105: the wall)
SHIP_SPEED = 2
MAX_SHOTS = 10                  # slots; shot_limit (jauge B) uses 5 at start
SHOT_LIMIT = 5
SHOT_DY = 8
SHOT_H = 6
SHOT_Y0 = SHIP_Y - SHOT_H
STAR_COLS = 2 * FIELD_CELLS // 7  # byte columns of the field
NSTARS = 16                     # (24 until lot 6: ~1 100 cycles a frame back)

ROWS, COLS = 5, 8
NALIENS = ROWS * COLS
ALIEN_MAX = FIELD_CELLS - 8
ALIEN_CELLS, ALIEN_H = 7, 8
FORM_X0, FORM_DX = 5, 12        # cells (11, 14 before the walls)
FORM_Y0, FORM_DY = 20, 14       # rows
SWAY_MAX = 12
SWAY_EVERY = 3                  # steps per row move (2 until lot 6: frame budget)
DEAD, ENTER, DIVE, HOME, FORM, BOOM = range(6)
HOME_DX, HOME_DY = 2, 4
ENTRY_FIRST, WAVE_GAP, LAUNCH_GAP = 20, 60, 6
DIVE_GAP, MAX_DIVERS = 20, 6
OFF_TOP = 240                   # row 240 = -16: above the screen
ESCAPE_Y = 224                  # rows 192..223: gone out through the bottom (an
                                # alien starting above, 236.., never is there)
SEED = 0xAD3C
BOOM_T = 8                      # steps an alien explosion lasts

E_SHOTS = 6                     # enemy bombs
BOMB_DY, BOMB_H = 4, 4
FIRE_GAP = 12                   # steps between two bomb attempts
FIRE_MAX_Y = 150                # an alien lower than this does not fire

LIVES = 3
DEATH_T = 45                    # steps from a hit to the respawn
RESPAWN_INVUL = 60
SHIELD_T = 60                   # after armour took a bomb
SHIP_HIT_X0, SHIP_HIT_X1 = 1, 5     # cells of the ship that can be hit
SHIP_HIT_Y0, SHIP_HIT_Y1 = SHIP_Y + 2, SHIP_Y + 9
POINTS_SEATED, POINTS_FLYING = 50, 100

# Lot 6: levels.
PASS, KAMI = 6, 7               # alien states: flies past (bonus), dives at the ship
NORMAL, BIG, BONUS, KAMIKAZE, BOSS = range(5)   # level kinds
LEVELS = 100
TELEPORT_T = 60                 # steps between two levels
BONUS_PRIZE = 10000             # all 40 shot on a bonus level
KAMI_PRIZE = 2000               # a kamikaze wave shot down: 2000, 4000, 8000...
BOSS_LEVELS = (24, 49, 74, 99)  # level indexes (levels 25, 50, 75, 100)
DEMO_NEXT = {1: 2, 4: 7, 8: 24}  # attract mode: ordinary, big, kami, bonus, boss
# Big aliens (level 3 of a pack): the even slots of formation row 0, two
# hits, 200 points, a rank mark of the pack's colour. Anchored on the slot
# like a small one: their box is cells x-2..x+7, rows y-8..y+7 (drawn only
# from row 16 down, not over the HUD).
BIG_HP, POINTS_BIG = 2, 200
# The boss (levels 25, 50, 75, 100; lot 10c: bigger, smooth): 24 cells x
# 28 rows at BOSS_Y, a cell every BOSS_STEP steps, bouncing between the
# walls; only its core (cells 9..14) takes hits, its claws swallow shots; a
# rosette of 5 bombs every boss_gap steps, an aimed bomb half-way; shot
# down: 5000 points, its escorts explode, a life and a 200 coin drop.
BOSS_CELLS, BOSS_H, BOSS_Y = 24, 28, 24
BOSS_CORE0, BOSS_CORE1 = 9, 14
BOSS_MIN_X = 1                  # (its STA margin, a cell each side, and
BOSS_MAX_X = 80                 # its 9 bytes: never on a wall)
BOSS_STEP = 8
BOSS_X0 = BOSS_MAX_X // 2
BOSS_BOOM_T = 40
POINTS_BOSS, POINTS_BOSS_HIT = 5000, 10
ROSETTE = (-2, -1, 0, 1, 2)
# Lot 7: the shop, after the 4th level of each pack (levels 4, 8 ... 100)
# when the player has SHOP_MIN credits: (name, price) from the Warblade
# 1.2c list, the items this game has. The game's logic is frozen while it is
# open; leaving it applies the ranks: the 6 marks -> rank + 1 (marks
# cleared), the dark mark -> rank - 1.
SHOP_MIN = 50
ITEMS = [('EXTRA SPEED', 50), ('EXTRA BULLET', 75), ('DOUBLE SHOT', 100), ('LESS SPEED', 150),
         ('TRIPLE SHOT', 200), ('AUTO FIRE', 400), ('SHIP ARMOUR', 600), ('EXTRA LIFE', 800),
         ('RANK MARKER', 1250), ('EXTRA TIME', 1500)]
RANK_MAX = 99
# Hurry-up: a normal or big level still on after HURRY_T steps (60 s) gets
# a saucer at HURRY_Y crossing the top, 2 cells a step, bouncing, out of
# reach, dropping a bomb that drifts towards the ship every HURRY_FIRE steps.
HURRY_T, HURRY_Y, HURRY_FIRE = 1800, 10, 12
BIG_X0, BIG_CELLS, BIG_Y0, BIG_H = -2, 10, -8, 16
# Lot 8, Meteor Storm: rocks are aliens (slots 0..M_ROCKS-1) in state ROCK,
# drawn with the rock table in cur_alien. Fire held: m_speed + M_ACC, else
# - M_DEC (slowing is faster), 0..M_SPEED_MAX; the field falls dy = M_DY0 +
# m_speed // 8 rows a step (rocks, coins, and the stars on top of their own
# speed, dy // 2). A rock or a coin every M_SPACING rows of field; the
# distance M_DIST in rows. A rock hits: the ship explodes, no life lost, the
# storm ends when the explosion does. Through: a prize by the time taken
# (steps // 128, ~4 s: the average speed). First M_WAIT steps: METEOR STORM.
ROCK = 8
M_ROCKS = 12
M_SPEED_MAX, M_ACC, M_DEC = 63, 1, 2
M_DY0 = 2
M_SPACING = 28
M_DIST = 4096
M_WAIT = 60
M_TOP = 248                     # a rock starts at row -8
M_COIN = 48                     # rand8 below: a coin instead of a rock
M_COINS = ['c10', 'c10', 'c10', 'c50', 'c50', 'c100', 'c100', 'c200']
M_TIME_MAX = 2047
M_PRIZE = [max(1, 32 - 2 * b) for b in range(16)]  # thousands, by steps // 128
# Memory Station: grids of cols x rows cards, row-major; every pair of a
# kind drawn from MEM_KINDS, one pirate flag (the skull icon) that ends it.
# A pair turned: its bonus (take); the grid cleared: MEM_PRIZE points and
# the next grid. T gauge: seconds a grid (the screen's clock, not the logic).
MEM_GRIDS = [(3, 3), (5, 3), (5, 5), (7, 5)]
MEM_KINDS = ['c50', 'c100', 'c200', 's', 'b', 't', 'life', 'armour', 'w2', 'w3',
             'e', 'x', 'lt', 'r', 'a', 'x2']
MEM_CELLS = 35
MEM_PRIZE = 25000
MEM_NONE = 0xFF


def level_kind(level):
    if level in BOSS_LEVELS:
        return BOSS
    sub = level % 4
    if sub < 2:
        return NORMAL
    if sub == 2:
        return BIG
    return KAMIKAZE if level // 4 % 2 == 0 else BONUS


def alien_combo(level):
    """Small alien design x tint of the level's pack: WG2.AUX table index
    design * 4 + tint (design pack mod 6, tint (pack div 6) mod 4)."""
    pack = level // 4
    return pack % 6 * 4 + pack // 6 % 4


def big_combo(level):
    """Big alien design x tint of the level's pack (WG2.AUX big table)."""
    pack = level // 4
    return pack % 2 * 4 + pack // 6 % 4


# Lot 10: Warblade's formations are shapes, not a full grid, and mix two
# species. A shape: ROWS rows of (columns, staggered); a staggered row sits
# half a pitch (ROW_SHIFT cells) to the right (no alien in its column 7:
# the sway would take it past ALIEN_MAX). Original shapes, after the
# blocks, bricks, arrows and gaps of Warblade's squadrons.
ROW_SHIFT = FORM_DX // 2
SHAPES = {
    'block':   [('XXXXXXXX', 0)] * 5,
    'brick':   [('XXXXXXXX', 0), ('XXXXXXX.', 1), ('XXXXXXXX', 0), ('XXXXXXX.', 1), ('XXXXXXXX', 0)],
    'pyramid': [('..XXX...', 1), ('..XXXX..', 0), ('.XXXXX..', 1), ('.XXXXXX.', 0), ('XXXXXXX.', 1)],
    'gap':     [('XXX..XXX', 0), ('XXXXXXXX', 0), ('XXX..XXX', 0), ('XXXXXXXX', 0), ('XXX..XXX', 0)],
    'diamond': [('..XXX...', 1), ('.XXXXXX.', 0), ('XXXXXXX.', 1), ('.XXXXXX.', 0), ('..XXX...', 1)],
    'columns': [('XX.XX.XX', 0)] * 5,
    'vee':     [('XXXXXXX.', 1), ('.XXXXXX.', 0), ('.XXXXX..', 1), ('..XXXX..', 0), ('..XXX...', 1)],
    'wings':   [('XXX..XXX', 0), ('XX....XX', 0), ('XXX..XXX', 0), ('XX....XX', 0), ('XXX..XXX', 0)],
    'checker': [('X.X.X.X.', 0), ('X.X.X.X.', 1), ('.X.X.X.X', 0), ('X.X.X.X.', 1), ('X.X.X.X.', 0)],
}
SHAPE_ORDER = ['block', 'brick', 'pyramid', 'gap', 'diamond', 'columns', 'vee', 'wings', 'checker']
# Rows drawn as the second species (bit r = row r), by formation level.
DESIGN_ROWS = [0b00001, 0b11000, 0b00110, 0b10101]
FULL = 0xFF


def mask(cells):
    return sum(1 << c for c, ch in enumerate(cells) if ch == 'X')


def entry_params(level):
    """Rows, pair gap, wave gap. WGII tuning, not Warblade's original data.

    Special stages keep all their waves (and perfect/wave prizes). Bosses
    still start at row 3. Normal stages grow into the 40-slot formation.
    """
    if level_kind(level) in (BONUS, KAMIKAZE, BOSS):
        return ROWS, LAUNCH_GAP, WAVE_GAP
    return level_form(level)[0], 10 if level < 12 else LAUNCH_GAP, 90 if level < 12 else WAVE_GAP


def level_form(level):
    """(rows, masks, staggered rows, second-species rows): the waves fill
    rows 0..rows-1, a wave launching only its row's columns. A normal or big
    level takes the next shape (a big level's row 0: big aliens on the even
    columns) and the rows that bring it near the opening's count (8 a row);
    the special levels keep the full grid, the boss its two rows of escorts."""
    kind = level_kind(level)
    if kind == BOSS:
        return ROWS, [FULL] * ROWS, 0, 0       # (one species: cur_big, iobuf hold the boss)
    if kind in (BONUS, KAMIKAZE):
        return ROWS, [FULL] * ROWS, 0, 0b01010
    k = 3 * (level // 4) + level % 4         # the normal and big levels, in turn
    shape = SHAPES[SHAPE_ORDER[k % len(SHAPE_ORDER)]]
    masks = [mask(cells) for cells, _ in shape]
    stagger = sum(st << r for r, (_, st) in enumerate(shape))
    design = DESIGN_ROWS[k % len(DESIGN_ROWS)]
    if kind == BIG:
        masks[0], stagger, design = 0x55, stagger & ~1, design & ~1
    want = 8 * min(ROWS, 2 + level % 4 + level // 4) - (4 if kind == BIG else 0)
    rows = min(ROWS, 2 + level % 4 + level // 4)
    while rows < ROWS and sum(bin(m).count('1') for m in masks[:rows]) < want - 4:
        rows += 1
    return rows, masks, stagger, design


def alien_combo2(level):
    """The pack's second species: design + 2, the other palette (tint + 2)."""
    c = alien_combo(level)
    return (c // 4 + 2) % 6 * 4 + (c % 4 + 2) % 4


def level_params(level, loop):
    """(dive gap, max divers, fire gap, bomb dy, kamikaze dy): each pack is
    harder, each loop more so."""
    pack = level // 4
    # Teach aiming, then dodging, then crowd control. Beyond the opening,
    # retain the original late-game pressure and the seven-diver budget.
    opening_dive = (60, 52, 44, 44, 40, 36, 32, 32, 30, 28, 26, 26, 24, 22, 20, 20)
    opening_fire = (60, 52, 44, 44, 40, 36, 32, 32, 28, 26, 24, 24, 22, 20, 18, 18)
    dive = opening_dive[level] if level < 16 else DIVE_GAP - pack // 2
    fire = opening_fire[level] if level < 16 else max(FIRE_GAP - pack // 3, 18 - (level - 16) // 2)
    loop = min(loop, 20)         # every parameter has reached its bound
    return (max(8, dive - 4 * loop),
            min(7, min(MAX_DIVERS + pack // 6, 1 + (level + 1) // 3) + 2 * loop),
            max(5, fire - 3 * loop),
            min(7, (2 if level < 2 else 3 if level < 8 else BOMB_DY + pack // 12) + loop),
            min(7, 3 + pack // 8 + loop))

# Lot 5: falling objects, gauges, timed bonuses.
N_OBJ, OBJ_DY, OBJ_H = 6, 2, 13          # (icons 8 rows high until 2026-10-23)
DROP_RATE = 40                  # rand8 < 40: a kill drops something (~16 %)
S_MAX, B_MIN, B_MAX, T_MIN, T_MAX = 5, 5, 10, 3, 9
GAUGE_POINTS = 500              # a gauge icon at its maximum
AUTO_GAP = 4                    # autofire: a volley every 4 steps, fire held
KINDS = ['c10', 'c50', 'c100', 'c200', 's', 'b', 't', 'w1', 'w2', 'w3', 'auto', 'armour',
         'life', 'skull', 'e', 'x', 'lt', 'r', 'a', 'x2', 'x5', 'shield', 'freeze',
         'mark0', 'mark1', 'mark2', 'mark3', 'mark4', 'mark5', 'markdark', 'meteor', 'memory']
K = {name: i for i, name in enumerate(KINDS)}
COINS = {'c10': 10, 'c50': 50, 'c100': 100, 'c200': 200}
WEIGHTS = {'c10': 10, 'c50': 5, 'c100': 2, 'c200': 1, 's': 3, 'b': 3, 't': 3, 'w1': 2, 'w2': 3,
           'w3': 2, 'auto': 2, 'armour': 2, 'life': 1, 'skull': 3, 'e': 1, 'x': 1, 'lt': 1,
           'r': 1, 'a': 1, 'x2': 2, 'x5': 1, 'shield': 2, 'freeze': 3, 'mark0': 1, 'mark1': 1,
           'mark2': 1, 'mark3': 1, 'mark4': 1, 'mark5': 1, 'markdark': 1, 'meteor': 1, 'memory': 1}
DROP_TABLE = [K[n] for n in KINDS for _ in range(WEIGHTS[n])]
assert len(DROP_TABLE) == 64
WEAPONS = [[(3, 0)], [(1, 0), (5, 0)], [(3, 0), (1, -1), (5, 1)]]   # (cell, dx) per shot
EXTRA = ['e', 'x', 'lt', 'r', 'a']
# What a pickup did, named mid-field for PICK_T steps (and a sound): one
# text per kind (pick_msg = the kind), then what replaces it: a gauge, the
# armour or the lives already full (points instead), the skull's malus.
PICK_T = 45                     # 1.5 s
PICK_TEXT = ['+10 CREDITS', '+50 CREDITS', '+100 CREDITS', '+200 CREDITS', 'EXTRA SPEED',
             'EXTRA BULLET', 'EXTRA TIME', 'SINGLE SHOT', 'DOUBLE SHOT', 'TRIPLE SHOT', 'AUTO FIRE',
             'SHIP ARMOUR', 'EXTRA LIFE', 'SKULL', 'LETTER E', 'LETTER X', 'LETTER T', 'LETTER R',
             'LETTER A', 'SCORE X2', 'SCORE X5', 'SHIELD', 'FREEZE', 'RANK MARK 1', 'RANK MARK 2',
             'RANK MARK 3', 'RANK MARK 4', 'RANK MARK 5', 'RANK MARK 6', 'DARK MARK',
             'METEOR STORM', 'MEMORY GAME',
             'BONUS POINTS', 'LESS SPEED', 'LESS BULLET', 'BONUS LOST']
PM_POINTS, PM_LESS_SPEED, PM_LESS_BULLET, PM_LOST = range(32, 36)
assert len(PICK_TEXT) == PM_LOST + 1 and max(map(len, PICK_TEXT)) <= 12


def pick_bad(msg):
    """A malus: its own sound."""
    return msg >= PM_LESS_SPEED or msg in (K['w1'], K['markdark'])


def duration(t_level):
    """Steps a timed bonus lasts: T seconds at 30 steps a second."""
    return 300 * t_level

_, ENTRY, DIVES = paths.data()
ENTRIES = paths.entries()
FLYPAST = paths.flypast()
ENTRY_X0, ENTRY_Y0 = paths.data()[0]


def star_speed(i):
    return 1 + i % 3


def signed(b):
    return b - 256 if b > 127 else b


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def bcd(value, nbytes):
    """value -> little-endian packed BCD."""
    out = []
    for _ in range(nbytes):
        out.append(value % 10 | value // 10 % 10 << 4)
        value //= 100
    return bytes(out)


def visible(y):
    return FIELD_TOP <= y < 192


def flying(state):
    """An alien that moves on its own (shot and collided as such)."""
    return ENTER <= state <= HOME or state in (PASS, KAMI, ROCK)


class Game:
    def __init__(self, start_level=0):
        self.ship_c = SHIP_MAX // 2
        self.demo = False
        self.shot_limit = SHOT_LIMIT
        self.shot_y = [0] * MAX_SHOTS
        self.shot_c = [0] * MAX_SHOTS
        self.star_y = [FIELD_TOP + (i * 97 + 13) % (192 - FIELD_TOP) for i in range(NSTARS)]
        self.star_col = [(i * 23 + 5) % STAR_COLS for i in range(NSTARS)]
        self.prng = SEED
        self.entry_w, self.entry_k, self.entry_t = 0, 0, ENTRY_FIRST
        self.form_off, self.form_dir, self.sway_row, self.sway_t = 0, 1, 0, 0
        self.row_off = [0] * ROWS
        self.row_anim = [0] * ROWS
        self.dive_t = DIVE_GAP
        self.a_state = [DEAD] * NALIENS
        self.a_x = [0] * NALIENS
        self.a_y = [0] * NALIENS
        self.a_timer = [0] * NALIENS
        self.a_path = [0] * NALIENS       # index into a_route
        self.a_route = [ENTRY] * NALIENS
        self.a_mirror = [0] * NALIENS
        self.a_big = [0] * NALIENS
        self.a_hp = [0] * NALIENS
        self.flying = []                  # visible flying aliens, descending
        self.e_y = [0] * E_SHOTS
        self.e_c = [0] * E_SHOTS
        self.fire_t = FIRE_GAP
        self.lives = LIVES
        self.armour = 0
        self.ship_state = 0               # >0: exploding, steps to respawn
        self.invul_t = 0
        self.game_over = 0
        self.score = 0
        self.credits = 0
        self.shot_dx = [0] * MAX_SHOTS
        self.obj_y = [0] * N_OBJ
        self.obj_k = [0] * N_OBJ          # column: cells 7k..7k+6
        self.obj_kind = [0] * N_OBJ
        self.s_level, self.t_level, self.weapon = 1, T_MIN, 0
        self.autofire_t = self.mult_t = self.shield_t = self.freeze_t = 0
        self.mult, self.auto_cnt, self.extra_bits = 1, 0, 0
        self.marks, self.mark_dark, self.subgame = 0, 0, 0
        self.pick_msg = self.pick_t = 0
        self.shop, self.rank = 0, 0
        self.perfects = 0                 # bonus levels all shot (front.s pays them)
        self.level, self.loop, self.phase, self.clear_t, self.level_t = start_level, 0, 0, 0, 0
        self.bonus_kills, self.w_kills = 0, [0] * ROWS
        self.e_dx = [0] * E_SHOTS
        self.boss_hp = self.boss_x = self.boss_dir = self.boss_boom = self.boss_gap = self.boss_t = 0
        self.boss_mv = 0
        self.hurry = self.h_x = self.h_dir = self.h_t = 0
        self.storm = self.station = 0
        self.m_speed = self.m_dist = self.m_acc = self.m_time = self.m_wait = self.m_crash = 0
        self.m_round = self.m_pairs = 0
        self.m_first = MEM_NONE
        self.m_card = [0] * MEM_CELLS
        self.m_up = [0] * MEM_CELLS
        self.setup_level()

    def boss_setup(self):
        n = self.level // 25 + 4 * self.loop
        self.boss_hp = min(250, 60 + 20 * n)   # (lot 10c: x2, it moves a cell at a time)
        self.boss_x, self.boss_dir, self.boss_boom, self.boss_mv = BOSS_X0, 1, 0, BOSS_STEP
        self.boss_gap = max(16, 40 - 5 * n)
        self.boss_t = self.boss_gap

    def setup_level(self):
        self.lkind = level_kind(self.level)
        (self.dive_gap, self.max_divers, self.fire_gap, self.bomb_dy,
         self.kami_dy) = level_params(self.level, self.loop)
        _, self.f_mask, stagger, self.f_design = level_form(self.level)
        self.row_sh = [ROW_SHIFT * (stagger >> r & 1) for r in range(ROWS)]
        self.entry_w = 3 if self.lkind == BOSS else 0
        self.entry_k, self.entry_t = 0, ENTRY_FIRST
        self.dive_t, self.fire_t, self.level_t = self.dive_gap, self.fire_gap, 0
        self.bonus_kills, self.w_kills = 0, [0] * ROWS
        if self.lkind == BOSS:
            self.boss_setup()
        self.hurry = 0

    def rand8(self):
        """dev/lib/math/random.asm: LSR hi, ROR lo, EOR #$B4 into hi on carry."""
        lo, hi = self.prng & 0xFF, self.prng >> 8
        lo, carry = (lo >> 1) | (hi & 1) << 7, lo & 1
        hi >>= 1
        if carry:
            hi ^= 0xB4
        self.prng = hi << 8 | lo
        return lo

    def rand_alien(self):
        i = self.rand8() & 63
        return i - NALIENS if i >= NALIENS else i

    def slot_x(self, i):
        return FORM_X0 + self.row_off[i // COLS] + self.row_sh[i // COLS] + FORM_DX * (i % COLS)

    @staticmethod
    def slot_y(i):
        return FORM_Y0 + FORM_DY * (i // COLS)

    def box(self, i):
        """(first cell, last cell, top row, bottom row) of alien i."""
        x, y = self.a_x[i], self.a_y[i]
        if self.a_big[i]:
            return x + BIG_X0, x + BIG_X0 + BIG_CELLS - 1, y + BIG_Y0, y + BIG_Y0 + BIG_H - 1
        return x, x + ALIEN_CELLS - 1, y, y + ALIEN_H - 1

    def shown(self, i):
        """On screen (big: its top row not in the HUD)."""
        y = self.a_y[i]
        return (16 if self.a_big[i] else FIELD_TOP) <= y < 192

    def target(self, i):
        """Shot and collided with through the list: flying, or a seated big
        one (the grid only knows small seats)."""
        s = self.a_state[i]
        return flying(s) or (s == FORM and self.a_big[i])

    def alive(self):
        return not self.ship_state and not self.game_over

    def step(self, move_dir=0, fire=False, held=False):
        """move_dir: -1 left, 0, 1 right; fire: a new press; held: fire is
        held down (autofire)."""
        if self.shop or self.station:   # (the game waits for the screen)
            return
        if self.storm:
            self.storm_step(move_dir, held)
            return
        speed = self.s_level + 1
        if self.alive():
            if move_dir > 0:
                self.ship_c = min(self.ship_c + speed, SHIP_MAX)
            elif move_dir < 0:
                self.ship_c = max(self.ship_c - speed, 0)
        for x in range(MAX_SHOTS):
            y = self.shot_y[x]
            if y:
                y -= SHOT_DY
                c = (self.shot_c[x] + self.shot_dx[x]) & 0xFF
                self.shot_c[x] = c
                self.shot_y[x] = y if y >= FIELD_TOP and c < FIELD_CELLS else 0
        volley = self.autofire_t and held and not self.auto_cnt
        self.auto_cnt = (self.auto_cnt + 1) % AUTO_GAP
        if (fire or volley) and self.alive() and not self.phase:
            for cell, dx in WEAPONS[self.weapon]:
                for x in reversed(range(self.shot_limit)):
                    if not self.shot_y[x]:
                        self.shot_y[x] = SHOT_Y0
                        self.shot_c[x] = self.ship_c + cell
                        self.shot_dx[x] = dx & 0xFF
                        break
                else:
                    break
        for k in range(E_SHOTS):
            y = self.e_y[k]
            if y:
                y += self.bomb_dy
                c = (self.e_c[k] + self.e_dx[k]) & 0xFF
                self.e_c[k] = c
                self.e_y[k] = y if y <= 192 - BOMB_H and c < FIELD_CELLS else 0
        for k in range(N_OBJ):
            y = self.obj_y[k]
            if y:
                y += OBJ_DY
                self.obj_y[k] = y if y <= 192 - OBJ_H else 0
        for i in range(NSTARS):
            y = self.star_y[i] + star_speed(i)
            if y >= 192:
                y -= 192 - FIELD_TOP
                self.star_col[i] = (self.star_col[i] + 17) % STAR_COLS
            self.star_y[i] = y
        if self.freeze_t:               # frozen: only explosions go on
            for i in range(NALIENS):
                if self.a_state[i] == BOOM:
                    self.alien(i)
        else:
            self.launch()
            self.sway()
            self.dive()
            for i in range(NALIENS):
                self.alien(i)
            self.boss_move()
            self.hurry_move()
        if self.boss_boom:
            self.boss_boom -= 1
        self.flying = [i for i in reversed(range(NALIENS)) if self.target(i) and self.shown(i)]
        for x in reversed(range(MAX_SHOTS)):
            if self.shot_y[x]:
                self.shoot(x)
        if self.alive() and not self.phase:
            if not self.invul_t and not self.shield_t:
                self.ship_hits()
            if self.alive():
                self.pickups()
        if not self.freeze_t and self.lkind != BONUS:
            self.enemy_fire()
        self.ship_timers()
        self.level_step()

    def ship_timers(self):
        if self.ship_state:
            self.ship_state -= 1
            if not self.ship_state:
                if self.lives:
                    self.ship_c = SHIP_MAX // 2
                    self.invul_t = RESPAWN_INVUL
                else:
                    self.game_over = 1
        elif self.invul_t:
            self.invul_t -= 1
        if self.autofire_t:
            self.autofire_t -= 1
        if self.mult_t:
            self.mult_t -= 1
            if not self.mult_t:
                self.mult = 1
        if self.shield_t:
            self.shield_t -= 1
        if self.freeze_t:
            self.freeze_t -= 1
        if self.pick_t:
            self.pick_t -= 1

    # --- levels -------------------------------------------------------------
    def level_step(self):
        if self.game_over:              # (levels went on behind GAME OVER)
            return
        if self.phase:                  # teleporting
            self.clear_t -= 1
            if not self.clear_t:
                self.phase = 0
                self.teleported()
            return
        self.level_t = min(0xFFFF, self.level_t + 1)
        if not self.hurry and self.level_t >= HURRY_T and self.lkind in (NORMAL, BIG):
            self.hurry, self.h_x, self.h_dir, self.h_t = 1, 0, 1, HURRY_FIRE
        # (objects still falling hold the end: the boss's life and coin were
        # wiped 40 steps after it fell, half-way down; bug hunt 6)
        if self.entry_w != ROWS or any(self.a_state) or self.boss_hp or self.boss_boom or any(self.obj_y):
            return
        if self.lkind == BONUS and self.bonus_kills == NALIENS:
            self.add_score(BONUS_PRIZE)
            self.perfects = min(255, self.perfects + 1)   # (lot 10: GAME BONUSES)
        self.phase, self.clear_t = 1, TELEPORT_T
        self.hurry = 0
        self.shot_y = [0] * MAX_SHOTS
        self.e_y = [0] * E_SHOTS
        self.obj_y = [0] * N_OBJ

    def teleported(self):
        """The teleport is over: a sub-game whose icon was caught, then the
        shop after a pack's 4th level (credits enough), then the next level
        (each one comes back here when it ends)."""
        if self.subgame == 1:
            self.storm_start()
        elif self.subgame == 2:
            self.subgame = 0
            self.station = 1            # the screen deals (mem_deal)
        elif self.level % 4 == 3 and self.credits >= SHOP_MIN:
            self.shop = 1               # the next level once it closes
        else:
            self.next_level()

    def next_level(self):
        self.level += 1
        if self.demo:
            self.level = DEMO_NEXT.get(self.level, self.level)
        if self.level == LEVELS:
            self.level = 0
            self.loop = min(255, self.loop + 1)   # (wrapped to 0: easy again)
        self.setup_level()

    # --- shop (lot 7) -------------------------------------------------------
    def can_buy(self, item):
        name, price = ITEMS[item]
        if self.credits < price:
            return False
        return {'EXTRA SPEED': self.s_level < S_MAX, 'EXTRA BULLET': self.shot_limit < B_MAX,
                'DOUBLE SHOT': self.weapon < 1, 'LESS SPEED': self.s_level > 1,
                'TRIPLE SHOT': self.weapon < 2, 'AUTO FIRE': self.autofire_t < duration(T_MAX),
                'SHIP ARMOUR': self.armour < 2, 'EXTRA LIFE': self.lives < 4,
                'RANK MARKER': self.marks != 63, 'EXTRA TIME': self.t_level < T_MAX}[name]

    def buy(self, item):
        """-> bought (enough credits, not at the item's limit)."""
        if not self.can_buy(item):
            return False
        name, price = ITEMS[item]
        self.credits -= price
        if name == 'EXTRA SPEED':
            self.s_level += 1
        elif name == 'EXTRA BULLET':
            self.shot_limit += 1
        elif name == 'DOUBLE SHOT':
            self.weapon = 1
        elif name == 'LESS SPEED':
            self.s_level -= 1
        elif name == 'TRIPLE SHOT':
            self.weapon = 2
        elif name == 'AUTO FIRE':
            self.autofire_t = duration(T_MAX)
        elif name == 'SHIP ARMOUR':
            self.armour += 1
        elif name == 'EXTRA LIFE':
            self.lives += 1
        elif name == 'RANK MARKER':                  # the first one missing
            self.marks |= (self.marks + 1) & ~self.marks
        else:
            self.t_level += 1
        return True

    def shop_exit(self):
        if self.marks == 63:
            self.marks = 0
            self.rank = min(RANK_MAX, self.rank + 1)
        if self.mark_dark:
            self.mark_dark = 0
            self.rank = max(0, self.rank - 1)
        self.shop = 0
        self.next_level()

    # --- Meteor Storm (lot 8) ----------------------------------------------
    def storm_start(self):
        self.subgame = 0
        self.storm = 1
        self.m_speed = self.m_acc = self.m_time = self.m_crash = 0
        self.m_dist, self.m_wait = M_DIST, M_WAIT
        for i in range(M_ROCKS):
            self.a_big[i], self.a_hp[i] = 0, 1

    def storm_end(self):
        """Back to a teleport, then the shop or the next level."""
        self.storm = 0
        self.a_state = [DEAD] * NALIENS
        self.obj_y = [0] * N_OBJ
        self.phase, self.clear_t = 1, TELEPORT_T

    def storm_step(self, move_dir, held):
        alive = not self.ship_state
        if alive:
            speed = self.s_level + 1
            if move_dir > 0:
                self.ship_c = min(self.ship_c + speed, SHIP_MAX)
            elif move_dir < 0:
                self.ship_c = max(self.ship_c - speed, 0)
        if alive and held:
            self.m_speed = min(M_SPEED_MAX, self.m_speed + M_ACC)
        else:
            self.m_speed = max(0, self.m_speed - M_DEC)
        dy = M_DY0 + self.m_speed // 8
        for k in range(N_OBJ):
            y = self.obj_y[k]
            if y:
                y += dy
                self.obj_y[k] = y if y <= 192 - OBJ_H else 0
        for i in range(NSTARS):
            y = self.star_y[i] + star_speed(i) + dy // 2
            if y >= 192:
                y -= 192 - FIELD_TOP
                self.star_col[i] = (self.star_col[i] + 17) % STAR_COLS
            self.star_y[i] = y
        for i in reversed(range(NALIENS)):
            s = self.a_state[i]
            if s == ROCK:
                y = (self.a_y[i] + dy) & 0xFF
                self.a_y[i] = y
                if 192 <= y < M_TOP:
                    self.a_state[i] = DEAD
            elif s == BOOM:
                self.alien(i)
        self.flying = [i for i in reversed(range(NALIENS)) if self.target(i) and self.shown(i)]
        if self.m_wait:
            self.m_wait -= 1
        else:
            self.m_acc += dy
            if self.m_acc >= M_SPACING:
                self.m_acc -= M_SPACING
                self.storm_spawn()
            self.m_time = min(M_TIME_MAX, self.m_time + 1)
        if alive:
            if not self.invul_t and not self.shield_t:
                for i in self.flying:
                    x0, x1, y0, y1 = self.box(i)
                    if x1 >= self.ship_c + SHIP_HIT_X0 and x0 <= self.ship_c + SHIP_HIT_X1 \
                            and y1 >= SHIP_HIT_Y0 and y0 <= SHIP_HIT_Y1:
                        self.explode(i)
                        self.ship_state, self.m_crash = DEATH_T, 1     # no life lost
                        break
            if not self.ship_state:
                self.pickups()
                if not self.m_wait:
                    if self.m_dist <= dy:
                        self.m_dist = 0
                        self.add_score(1000 * M_PRIZE[self.m_time >> 7])
                        self.storm_end()
                        return
                    self.m_dist -= dy
        self.ship_timers()
        if self.m_crash and not self.ship_state:
            self.storm_end()

    def storm_spawn(self):
        if self.rand8() < M_COIN:
            kind = K[M_COINS[self.rand8() & 7]]
            for k in reversed(range(N_OBJ)):
                if not self.obj_y[k]:
                    self.obj_y[k], self.obj_kind[k] = FIELD_TOP, kind
                    self.obj_k[k] = self.rand8() & 15
                    return
            return
        x = self.rand8() & 127
        if x > ALIEN_MAX:
            x -= 64
        for i in reversed(range(M_ROCKS)):
            if not self.a_state[i]:
                self.a_state[i], self.a_x[i], self.a_y[i] = ROCK, x, M_TOP
                return

    # --- Memory Station (lot 8) ---------------------------------------------
    def mem_grid(self):
        return MEM_GRIDS[min(self.m_round, len(MEM_GRIDS) - 1)]

    def mem_deal(self):
        """The grid of this round: a kind drawn for each pair, the flag,
        shuffled (Fisher-Yates, j = rand8 mod (i + 1))."""
        cols, rows = self.mem_grid()
        n = cols * rows
        cards = []
        for _ in range(n // 2):
            cards += [K[MEM_KINDS[self.rand8() & 15]]] * 2
        cards.append(K['skull'])
        for i in reversed(range(1, n)):
            j = self.rand8() % (i + 1)
            cards[i], cards[j] = cards[j], cards[i]
        self.m_card = cards + [0] * (MEM_CELLS - n)
        self.m_up = [0] * MEM_CELLS
        self.m_pairs, self.m_first = n // 2, MEM_NONE

    def mem_turn(self, cell):
        """-> 'no' (face up already), 'flag' (the end), 'first', 'pair',
        'cleared' (the next grid dealt) or 'miss' (both face down again)."""
        if self.m_up[cell]:
            return 'no'
        self.m_up[cell] = 1
        kind = self.m_card[cell]
        if kind == K['skull']:
            return 'flag'
        first = self.m_first
        if first == MEM_NONE:
            self.m_first = cell
            return 'first'
        self.m_first = MEM_NONE
        if self.m_card[first] != kind:
            self.m_up[first] = self.m_up[cell] = 0
            return 'miss'
        self.take(KINDS[kind])
        self.m_pairs -= 1
        if self.m_pairs:
            return 'pair'
        self.add_score(MEM_PRIZE)
        self.m_round = min(255, self.m_round + 1)
        self.mem_deal()
        return 'cleared'

    def station_exit(self):
        self.station = 0
        self.m_round = 0
        self.teleported()

    # --- bonuses ------------------------------------------------------------
    def add_score(self, points):
        self.score = min(999999, self.score + points * self.mult)   # (wrapped to 0)

    def drop(self, i):
        if self.level < 4 and i % COLS == 3:
            kind = K['c50']            # first pack's predictable carriers
        else:
            if self.rand8() >= DROP_RATE:
                return
            self.rand8()                # kind: high byte (low = first draw >> 1)
            kind = DROP_TABLE[self.prng >> 8 & 63]
        if self.a_y[i] > 192 - OBJ_H:   # rows past 191: no (a guard: shots hit
            # nothing below row 179 today; the renderer has no rows past 191)
            return
        for k in reversed(range(N_OBJ)):
            if not self.obj_y[k]:
                self.obj_y[k] = self.a_y[i]
                self.obj_k[k] = (self.a_x[i] + 3) // 7
                self.obj_kind[k] = kind
                return

    def drop_mark(self, i):
        """A big alien leaves the pack's rank mark (no draw: always)."""
        if self.a_y[i] > 192 - OBJ_H:
            return
        for k in reversed(range(N_OBJ)):
            if not self.obj_y[k]:
                self.obj_y[k] = self.a_y[i]
                self.obj_k[k] = (self.a_x[i] + 3) // 7
                self.obj_kind[k] = K['mark0'] + self.level // 4 % 6
                return

    def pickups(self):
        for k in reversed(range(N_OBJ)):
            y = self.obj_y[k]
            c = 7 * self.obj_k[k]
            if y and c + 6 >= self.ship_c + SHIP_HIT_X0 and c <= self.ship_c + SHIP_HIT_X1 \
                    and y + OBJ_H - 1 >= SHIP_HIT_Y0 and y <= SHIP_HIT_Y1:
                self.obj_y[k] = 0
                self.take(KINDS[self.obj_kind[k]])
                self.pick_t = PICK_T

    def gauge_full(self):
        self.add_score(GAUGE_POINTS)
        self.pick_msg = PM_POINTS

    def take(self, kind):
        self.pick_msg = K[kind]
        if kind in COINS:
            self.credits = min(9999, self.credits + COINS[kind])
        elif kind == 's':
            if self.s_level < S_MAX:
                self.s_level += 1
            else:
                self.gauge_full()
        elif kind == 'b':
            if self.shot_limit < B_MAX:
                self.shot_limit += 1
            else:
                self.gauge_full()
        elif kind == 't':
            if self.t_level < T_MAX:
                self.t_level += 1
            else:
                self.gauge_full()
        elif kind in ('w1', 'w2', 'w3'):
            self.weapon = int(kind[1]) - 1
        elif kind == 'auto':
            self.autofire_t = duration(self.t_level)
        elif kind == 'armour':
            if self.armour < 2:
                self.armour += 1
            else:
                self.gauge_full()
        elif kind == 'life':
            if self.lives < 4:
                self.lives += 1
            else:
                self.gauge_full()
        elif kind == 'skull':
            r = self.rand8() & 3
            self.pick_msg = (K['w1'], PM_LESS_SPEED, PM_LESS_BULLET, PM_LOST)[r]
            if r == 0:
                self.weapon = 0
            elif r == 1:
                self.s_level = max(1, self.s_level - 1)
            elif r == 2:
                self.shot_limit = max(B_MIN, self.shot_limit - 1)
            else:                       # every timed bonus ends
                self.autofire_t = self.mult_t = self.shield_t = self.freeze_t = 0
                self.mult = 1
        elif kind in EXTRA:
            self.extra_bits |= 1 << EXTRA.index(kind)
            if self.extra_bits == 31:
                self.extra_bits = 0
                self.pick_msg = K['life']
                if self.lives < 4:
                    self.lives += 1
                else:
                    self.gauge_full()
        elif kind in ('x2', 'x5'):          # the larger multiplier, time anew
            self.mult = max(self.mult, int(kind[1]))
            self.mult_t = duration(self.t_level)
        elif kind == 'shield':
            self.shield_t = duration(self.t_level)
        elif kind == 'freeze':
            self.freeze_t = duration(self.t_level)
        elif kind.startswith('mark') and kind != 'markdark':
            self.marks |= 1 << int(kind[4])          # ranks: lot 7
        elif kind == 'markdark':
            self.mark_dark = 1
        else:                                        # sub-games: lot 8
            self.subgame = 1 if kind == 'meteor' else 2

    # --- collisions ---------------------------------------------------------
    def explode(self, i):
        self.a_state[i] = BOOM
        self.a_timer[i] = BOOM_T

    def shoot(self, x):
        c, y = self.shot_c[x], self.shot_y[x]
        if self.boss_hp and self.boss_x <= c <= self.boss_x + BOSS_CELLS - 1 \
                and y <= BOSS_Y + BOSS_H - 1 and y + SHOT_H - 1 >= BOSS_Y:
            self.shot_y[x] = 0          # the wings swallow it, the core bleeds
            if self.boss_x + BOSS_CORE0 <= c <= self.boss_x + BOSS_CORE1:
                self.boss_hp -= 1
                self.add_score(POINTS_BOSS_HIT)
                if not self.boss_hp:
                    self.boss_down()
            return
        # seated: the one band a shot can touch, then the column
        r = shot_row(y)
        if r is not None:
            dx = c - (FORM_X0 + self.row_off[r] + self.row_sh[r])
            if 0 <= dx < COLS * FORM_DX and dx % FORM_DX < ALIEN_CELLS:
                i = r * COLS + dx // FORM_DX
                if self.a_state[i] == FORM and not self.a_big[i]:
                    self.shot_y[x] = 0
                    self.explode(i)
                    self.add_score(POINTS_SEATED)
                    self.drop(i)
                    return
        for i in self.flying:
            x0, x1, y0, y1 = self.box(i)
            if self.target(i) and x0 <= c <= x1 and y <= y1 and y + SHOT_H - 1 >= y0:
                self.shot_y[x] = 0
                if self.a_big[i]:
                    self.a_hp[i] -= 1
                    if self.a_hp[i]:            # dented
                        return
                    self.explode(i)
                    self.add_score(POINTS_BIG)
                    self.drop_mark(i)
                    return
                self.explode(i)
                self.add_score(POINTS_FLYING)
                if self.lkind == BONUS:
                    self.bonus_kills += 1
                elif self.lkind == KAMIKAZE:
                    w = i // COLS
                    self.w_kills[w] += 1
                    if self.w_kills[w] == COLS:
                        self.add_score(KAMI_PRIZE << w)
                self.drop(i)
                return

    def ship_hits(self):
        for k in reversed(range(E_SHOTS)):
            y = self.e_y[k]
            if y and self.ship_c + SHIP_HIT_X0 <= self.e_c[k] <= self.ship_c + SHIP_HIT_X1 \
                    and y <= SHIP_HIT_Y1 and y + BOMB_H - 1 >= SHIP_HIT_Y0:
                self.e_y[k] = 0
                if self.armour:
                    self.armour -= 1
                    self.invul_t = SHIELD_T
                else:
                    self.kill()
                return
        for i in self.flying:
            x0, x1, y0, y1 = self.box(i)
            if self.target(i) and x1 >= self.ship_c + SHIP_HIT_X0 and x0 <= self.ship_c + SHIP_HIT_X1 \
                    and y1 >= SHIP_HIT_Y0 and y0 <= SHIP_HIT_Y1:
                self.explode(i)
                self.kill()
                return

    # --- the boss -----------------------------------------------------------
    def boss_move(self):
        if not self.boss_hp:
            return
        self.boss_mv -= 1
        if not self.boss_mv:
            self.boss_mv = BOSS_STEP
            x = self.boss_x + self.boss_dir
            if x < BOSS_MIN_X or x > BOSS_MAX_X:
                self.boss_dir = -self.boss_dir
                x = self.boss_x + self.boss_dir
            self.boss_x = x
        self.boss_t -= 1
        mid = self.boss_x + BOSS_CELLS // 2
        if not self.boss_t:
            self.boss_t = self.boss_gap
            for dx in ROSETTE:
                self.bomb(BOSS_Y + BOSS_H, mid, dx)
        elif self.boss_t == self.boss_gap // 2:
            self.bomb(BOSS_Y + BOSS_H, mid, (mid < self.ship_c + 3) - (mid > self.ship_c + 3))

    def hurry_move(self):
        if not self.hurry:
            return
        x = self.h_x + 2 * self.h_dir
        if x < 0 or x > ALIEN_MAX:
            self.h_dir = -self.h_dir
            x = self.h_x + 2 * self.h_dir
        self.h_x = x
        self.h_t -= 1
        if not self.h_t:
            self.h_t = HURRY_FIRE
            mid = self.h_x + 3
            self.bomb(HURRY_Y + ALIEN_H, mid, (mid < self.ship_c + 3) - (mid > self.ship_c + 3))

    def bomb(self, y, c, dx):
        for k in reversed(range(E_SHOTS)):
            if not self.e_y[k]:
                self.e_y[k], self.e_c[k], self.e_dx[k] = y, c, dx & 0xFF
                return

    def boss_down(self):
        self.add_score(POINTS_BOSS)
        self.boss_boom = BOSS_BOOM_T
        for i in range(NALIENS):
            if self.a_state[i] not in (DEAD, BOOM):
                self.explode(i)
        for kind, k in (('life', 0), ('c200', 1)):
            self.obj_y[k] = BOSS_Y + 8
            self.obj_k[k] = (self.boss_x + BOSS_CELLS // 2) // 7 - k
            self.obj_kind[k] = K[kind]

    def kill(self):
        self.ship_state = DEATH_T
        self.lives -= 1

    def enemy_fire(self):
        self.fire_t -= 1
        if self.fire_t:
            return
        self.fire_t = self.fire_gap
        i = self.rand_alien()
        for _ in range(NALIENS):
            if self.a_state[i] in (FORM, DIVE) and self.shown(i) and self.a_y[i] < FIRE_MAX_Y:
                break
            i = i + 1 if i < NALIENS - 1 else 0
        else:
            return
        self.bomb(self.a_y[i] + ALIEN_H, self.a_x[i] + 3, 0)

    # --- formation ----------------------------------------------------------
    def launch(self):
        if self.entry_w == ROWS:
            return
        self.entry_t -= 1
        if self.entry_t:
            return
        w, k = self.entry_w, self.entry_k
        flip = self.loop & 1            # after level 100: mirrored
        state = {BONUS: PASS, KAMIKAZE: KAMI}.get(self.lkind, ENTER)
        route = FLYPAST if state == PASS else ENTRIES[paths.entry_index(self.level, w)]
        for i, mirror in ((w * COLS + 3 - k, 0), (w * COLS + 4 + k, 1)):
            if not self.f_mask[w] >> (i % COLS) & 1:     # (lot 10) not in the shape
                continue
            big = self.lkind == BIG and w == 0
            if big and i % 2:           # a big level's row 0: even slots only
                continue
            self.a_big[i], self.a_hp[i] = int(big), BIG_HP if big else 1
            mirror ^= flip
            self.a_state[i] = state
            self.a_x[i] = ALIEN_MAX - ENTRY_X0 if mirror else ENTRY_X0
            self.a_y[i] = ENTRY_Y0
            self.a_route[i], self.a_path[i], self.a_mirror[i] = route, 0, mirror
        self.entry_k += 1
        if self.entry_k == 4:
            self.entry_k = 0
            self.entry_w += 1
            if self.entry_w == entry_params(self.level)[0]:
                self.entry_w = ROWS   # shared "all waves in" sentinel
            self.entry_t = entry_params(self.level)[2]
        else:
            self.entry_t = entry_params(self.level)[1]

    def sway(self):
        self.sway_t = (self.sway_t + 1) % SWAY_EVERY     # one row every 3 steps
        if self.sway_t:
            return
        r = self.sway_row
        self.row_off[r] = self.form_off
        self.row_anim[r] ^= 1
        for i in range(r * COLS, r * COLS + COLS):
            if self.a_state[i] == FORM:
                self.a_x[i] = self.slot_x(i)
        self.sway_row += 1
        if self.sway_row == ROWS:
            self.sway_row = 0
            self.form_off += self.form_dir
            if self.form_off in (0, SWAY_MAX):
                self.form_dir = -self.form_dir

    def dive(self):
        if self.entry_w != ROWS or self.lkind in (BONUS, KAMIKAZE):
            return
        self.dive_t -= 1
        if self.dive_t:
            return
        self.dive_t = self.dive_gap
        if sum(ENTER <= s <= HOME for s in self.a_state) >= self.max_divers:
            return
        i = self.rand_alien()
        for _ in range(NALIENS):
            if self.a_state[i] == FORM:
                break
            i = i + 1 if i < NALIENS - 1 else 0
        else:
            return
        route = DIVES[self.rand8() & 3]
        self.a_state[i] = DIVE
        self.a_route[i], self.a_path[i] = route, 0
        self.a_mirror[i] = int(i % COLS >= COLS // 2) ^ (self.loop & 1)

    def alien(self, i):
        s = self.a_state[i]
        if s == KAMI:                   # straight down at its speed, sideways
            x = self.a_x[i]             # one cell a step towards the ship
            x += (x < self.ship_c) - (x > self.ship_c)
            self.a_x[i] = x
            y = (self.a_y[i] + self.kami_dy) & 0xFF
            self.a_y[i] = y
            if 192 <= y < ESCAPE_Y:     # escaped
                self.a_state[i] = DEAD
            return
        if s in (ENTER, DIVE, PASS):
            b = self.a_route[i][self.a_path[i]]
            if b == paths.END:
                self.a_state[i] = DEAD if s == PASS else HOME
                return
            self.a_path[i] += 1
            dx, dy = paths.decode(b)
            if self.a_mirror[i]:
                dx = -dx
            lo, hi = (-BIG_X0, FIELD_CELLS - 9) if self.a_big[i] else (0, ALIEN_MAX)   # (4 bytes from x-2)
            self.a_x[i] = clamp(self.a_x[i] + dx, lo, hi)
            y = (self.a_y[i] + dy) & 0xFF
            self.a_y[i] = y
            if s == DIVE and 192 <= y < OFF_TOP:
                self.a_state[i] = HOME
                self.a_y[i] = OFF_TOP
                self.a_x[i] = self.slot_x(i)
            elif s == PASS and 192 <= y < ESCAPE_Y:
                self.a_state[i] = DEAD     # flew past: escaped
        elif s == HOME:
            tx, ty = self.slot_x(i), self.slot_y(i)
            self.a_x[i] += clamp(tx - self.a_x[i], -HOME_DX, HOME_DX)
            self.a_y[i] = (self.a_y[i] + clamp(signed((ty - self.a_y[i]) & 0xFF), -HOME_DY, HOME_DY)) & 0xFF
            if self.a_x[i] == tx and self.a_y[i] == ty:
                self.a_state[i] = FORM
        elif s == BOOM:
            self.a_timer[i] -= 1
            if not self.a_timer[i]:
                self.a_state[i] = DEAD

    def state(self):
        """The bytes test_game.py peeks, by label."""
        return {'ship_c': bytes([self.ship_c]),
                'shot_y': bytes(self.shot_y),
                'shot_c': bytes(self.shot_c),
                'star_y': bytes(self.star_y),
                'star_col': bytes(self.star_col),
                'a_state': bytes(self.a_state),
                'a_x': bytes(self.a_x),
                'a_y': bytes(self.a_y),
                'a_timer': bytes(self.a_timer),
                'a_big': bytes(self.a_big),
                'a_hp': bytes(self.a_hp),
                'row_off': bytes(self.row_off),
                'row_sh': bytes(self.row_sh),
                'perfects': bytes([self.perfects]),
                'row_anim': bytes(self.row_anim),
                'e_y': bytes(self.e_y),
                'e_c': bytes(self.e_c),
                'lives': bytes([self.lives]),
                'armour': bytes([self.armour]),
                'ship_state': bytes([self.ship_state]),
                'invul_t': bytes([self.invul_t]),
                'game_over': bytes([self.game_over]),
                'score': bcd(self.score % 1000000, 3),
                'credits': bcd(self.credits, 2),
                'shot_limit': bytes([self.shot_limit]),
                'shot_dx': bytes(self.shot_dx),
                'obj_y': bytes(self.obj_y),
                'obj_k': bytes(self.obj_k),
                'obj_kind': bytes(self.obj_kind),
                's_level': bytes([self.s_level]),
                't_level': bytes([self.t_level]),
                'weapon': bytes([self.weapon]),
                'autofire_t': self.autofire_t.to_bytes(2, 'little'),
                'mult_t': self.mult_t.to_bytes(2, 'little'),
                'shield_t': self.shield_t.to_bytes(2, 'little'),
                'freeze_t': self.freeze_t.to_bytes(2, 'little'),
                'mult': bytes([self.mult]),
                'auto_cnt': bytes([self.auto_cnt]),
                'extra_bits': bytes([self.extra_bits]),
                'marks': bytes([self.marks]),
                'mark_dark': bytes([self.mark_dark]),
                'pick_msg': bytes([self.pick_msg]),
                'pick_t': bytes([self.pick_t]),
                'shop': bytes([self.shop]),
                'rank': bytes([self.rank]),
                'subgame': bytes([self.subgame]),
                'storm': bytes([self.storm]),
                'station': bytes([self.station]),
                'm_speed': bytes([self.m_speed]),
                'm_dist': self.m_dist.to_bytes(2, 'little'),
                'm_acc': bytes([self.m_acc]),
                'm_time': self.m_time.to_bytes(2, 'little'),
                'm_wait': bytes([self.m_wait]),
                'm_crash': bytes([self.m_crash]),
                'level': bytes([self.level]),
                'loop': bytes([self.loop]),
                'phase': bytes([self.phase]),
                'clear_t': bytes([self.clear_t]),
                'level_t': self.level_t.to_bytes(2, 'little'),
                'lkind': bytes([self.lkind]),
                'bonus_kills': bytes([self.bonus_kills]),
                'w_kills': bytes(self.w_kills),
                'dive_gap': bytes([self.dive_gap]),
                'max_divers': bytes([self.max_divers]),
                'fire_gap': bytes([self.fire_gap]),
                'bomb_dy': bytes([self.bomb_dy]),
                'kami_dy': bytes([self.kami_dy]),
                'e_dx': bytes(self.e_dx),
                'boss_hp': bytes([self.boss_hp]),
                'boss_x': bytes([self.boss_x]),
                'boss_dir': bytes([self.boss_dir & 0xFF]),
                'boss_boom': bytes([self.boss_boom]),
                'boss_gap': bytes([self.boss_gap]),
                'boss_t': bytes([self.boss_t]),
                'boss_mv': bytes([self.boss_mv]),
                'hurry': bytes([self.hurry]),
                'h_x': bytes([self.h_x]),
                'h_dir': bytes([self.h_dir & 0xFF]),
                'h_t': bytes([self.h_t]),
                'prng': bytes([self.prng & 0xFF, self.prng >> 8])}


def shot_row(y):
    """The formation row a shot whose top is y can touch: its rows y..y+5
    meet the alien rows top..top+7 (one band at most: 6 + 8 - 1 < 14)."""
    for r in range(ROWS):
        top = FORM_Y0 + FORM_DY * r
        if y <= top + ALIEN_H - 1 and y + SHOT_H - 1 >= top:
            return r
    return None


if __name__ == '__main__':
    g = Game()
    deaths = []
    for k in range(6000):
        lives = g.lives
        g.step()
        if g.lives != lives:
            deaths.append(k + 1)
        if g.game_over:
            break
    print('deaths at steps', deaths, 'game over at', k + 1, 'score', g.score)
