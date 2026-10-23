#!/usr/bin/env python3
"""WARGALAGA II game logic, the reference for src/logic.s (logic_step).

Bit-exact oracle, as dirtbike/tools/physics.py: tests/test_game.py pokes the
same inputs into the 6502 at each logic step and compares the whole state.
Constants mirror the top of src/game.s; path bytes come from tools/paths.py.

One step, in this order: ship, shots, new shot, stars, entry waves,
formation sway (one row every other step), dive launcher, aliens.
"""
import paths

FIELD_TOP = 8
SHIP_Y = 180
SHIP_MAX = 140 - 7
SHIP_SPEED = 2
MAX_SHOTS = 10                  # slots; shot_limit (jauge B) uses 5 at start
SHOT_LIMIT = 5
SHOT_DY = 8
SHOT_Y0 = SHIP_Y - 6
NSTARS = 24

ROWS, COLS = 5, 8
NALIENS = ROWS * COLS
ALIEN_MAX = 140 - 7
FORM_X0, FORM_DX = 11, 14       # cells
FORM_Y0, FORM_DY = 20, 14       # rows
SWAY_MAX = 12
DEAD, ENTER, DIVE, HOME, FORM = range(5)
HOME_DX, HOME_DY = 2, 4
ENTRY_FIRST, WAVE_GAP, LAUNCH_GAP = 20, 60, 6
DIVE_GAP, MAX_DIVERS = 20, 6
OFF_TOP = 240                   # row 240 = -16: above the screen
SEED = 0xAD3C

_, ENTRY, DIVES = paths.data()
ENTRY_X0, ENTRY_Y0 = paths.data()[0]


def star_speed(i):
    return 1 + i % 3


def signed(b):
    return b - 256 if b > 127 else b


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Game:
    def __init__(self):
        self.ship_c = SHIP_MAX // 2
        self.shot_limit = SHOT_LIMIT
        self.shot_y = [0] * MAX_SHOTS
        self.shot_c = [0] * MAX_SHOTS
        self.star_y = [FIELD_TOP + (i * 97 + 13) % (192 - FIELD_TOP) for i in range(NSTARS)]
        self.star_col = [(i * 23 + 5) % 40 for i in range(NSTARS)]
        self.prng = SEED
        self.entry_w, self.entry_k, self.entry_t = 0, 0, ENTRY_FIRST
        self.form_off, self.form_dir, self.sway_row, self.sway_t = 0, 1, 0, 0
        self.row_off = [0] * ROWS
        self.row_anim = [0] * ROWS
        self.dive_t = DIVE_GAP
        self.a_state = [DEAD] * NALIENS
        self.a_x = [0] * NALIENS
        self.a_y = [0] * NALIENS
        self.a_path = [0] * NALIENS       # index into a_route
        self.a_route = [ENTRY] * NALIENS
        self.a_mirror = [0] * NALIENS

    def rand8(self):
        """dev/lib/math/random.asm: LSR hi, ROR lo, EOR #$B4 into hi on carry."""
        lo, hi = self.prng & 0xFF, self.prng >> 8
        lo, carry = (lo >> 1) | (hi & 1) << 7, lo & 1
        hi >>= 1
        if carry:
            hi ^= 0xB4
        self.prng = hi << 8 | lo
        return lo

    def slot_x(self, i):
        return FORM_X0 + self.row_off[i // COLS] + FORM_DX * (i % COLS)

    @staticmethod
    def slot_y(i):
        return FORM_Y0 + FORM_DY * (i // COLS)

    def step(self, move_dir=0, fire=False):
        """move_dir: -1 left, 0, 1 right."""
        if move_dir > 0:
            self.ship_c = min(self.ship_c + SHIP_SPEED, SHIP_MAX)
        elif move_dir < 0:
            self.ship_c = max(self.ship_c - SHIP_SPEED, 0)
        for x in range(MAX_SHOTS):
            y = self.shot_y[x]
            if y:
                y -= SHOT_DY
                self.shot_y[x] = y if y >= FIELD_TOP else 0
        if fire:
            for x in reversed(range(self.shot_limit)):
                if not self.shot_y[x]:
                    self.shot_y[x] = SHOT_Y0
                    self.shot_c[x] = self.ship_c + 3
                    break
        for i in range(NSTARS):
            y = self.star_y[i] + star_speed(i)
            if y >= 192:
                y -= 192 - FIELD_TOP
                self.star_col[i] = (self.star_col[i] + 17) % 40
            self.star_y[i] = y
        self.launch()
        self.sway()
        self.dive()
        for i in range(NALIENS):
            self.alien(i)

    def launch(self):
        if self.entry_w == ROWS:
            return
        self.entry_t -= 1
        if self.entry_t:
            return
        w, k = self.entry_w, self.entry_k
        for i, x, mirror in ((w * COLS + 3 - k, ENTRY_X0, 0), (w * COLS + 4 + k, ALIEN_MAX - ENTRY_X0, 1)):
            self.a_state[i] = ENTER
            self.a_x[i], self.a_y[i] = x, ENTRY_Y0
            self.a_route[i], self.a_path[i], self.a_mirror[i] = ENTRY, 0, mirror
        self.entry_k += 1
        if self.entry_k == 4:
            self.entry_k = 0
            self.entry_w += 1
            self.entry_t = WAVE_GAP
        else:
            self.entry_t = LAUNCH_GAP

    def sway(self):
        self.sway_t ^= 1
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
        if self.entry_w != ROWS:
            return
        self.dive_t -= 1
        if self.dive_t:
            return
        self.dive_t = DIVE_GAP
        if sum(ENTER <= s <= HOME for s in self.a_state) >= MAX_DIVERS:
            return
        i = self.rand8() & 63
        if i >= NALIENS:
            i -= NALIENS
        for _ in range(NALIENS):
            if self.a_state[i] == FORM:
                break
            i = i + 1 if i < NALIENS - 1 else 0
        else:
            return
        route = DIVES[self.rand8() & 3]
        self.a_state[i] = DIVE
        self.a_route[i], self.a_path[i] = route, 0
        self.a_mirror[i] = int(i % COLS >= COLS // 2)

    def alien(self, i):
        s = self.a_state[i]
        if s in (ENTER, DIVE):
            b = self.a_route[i][self.a_path[i]]
            if b == paths.END:
                self.a_state[i] = HOME
                return
            self.a_path[i] += 1
            dx, dy = paths.decode(b)
            if self.a_mirror[i]:
                dx = -dx
            self.a_x[i] = clamp(self.a_x[i] + dx, 0, ALIEN_MAX)
            y = (self.a_y[i] + dy) & 0xFF
            self.a_y[i] = y
            if s == DIVE and 192 <= y < OFF_TOP:
                self.a_state[i] = HOME
                self.a_y[i] = OFF_TOP
                self.a_x[i] = self.slot_x(i)
        elif s == HOME:
            tx, ty = self.slot_x(i), self.slot_y(i)
            self.a_x[i] += clamp(tx - self.a_x[i], -HOME_DX, HOME_DX)
            self.a_y[i] = (self.a_y[i] + clamp(signed((ty - self.a_y[i]) & 0xFF), -HOME_DY, HOME_DY)) & 0xFF
            if self.a_x[i] == tx and self.a_y[i] == ty:
                self.a_state[i] = FORM

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
                'row_off': bytes(self.row_off),
                'row_anim': bytes(self.row_anim),
                'prng': bytes([self.prng & 0xFF, self.prng >> 8])}
