#!/usr/bin/env python3
"""Robot Space Station — reference model of the logic simulation.

The 6502 code must match this model bit for bit (docs/SPEC.md). A board is
a layout (16 parts on a grid, wires from sources to sinks); compile() turns
it into a flat list of elementary gates, tick() runs one synchronous turn.

Layout ids (what the player wires):
  sources 0-7 board sources, 8 + part*4 + k output k of part `part`
  sinks   0-7 board sinks,   8 + part*4 + k input k of part `part`
Flat ids (what the simulation reads):
  0-7 board sources, 8 + g output of flat gate g, NONE constant 0
"""

NONE = 0xFF
PARTS = 16
BOARD_GATES = 64
CHIP_GATES = 32
CHIPS = 8
TERMINALS = 8
LAYOUT_IDS = TERMINALS + PARTS * 4          # 72 sink (or source) ids

AND, OR, XOR, NOT, FLIP, BUF = 1, 2, 3, 4, 5, 6
CHIP0 = 8                                   # part type 8+n = burned chip n
GATE_INPUTS = {AND: 2, OR: 2, XOR: 2, NOT: 1, FLIP: 2, BUF: 1}


def part_inputs(kind):
    return 4 if kind >= CHIP0 else GATE_INPUTS[kind]


def part_outputs(kind):
    return 4 if kind >= CHIP0 else 1


def gate(kind, a, b, q):
    """New output of one elementary gate from its old inputs and output."""
    if kind == AND:
        return a & b
    if kind == OR:
        return a | b
    if kind == XOR:
        return a ^ b
    if kind == NOT:
        return a ^ 1
    if kind == FLIP:
        return 1 if a else (0 if b else q)
    if kind == BUF:
        return a
    raise ValueError(kind)


class Chip:
    """A burned chip: flat gates over sources 0-3 (inputs), 4+g (gate g),
    NONE; outputs[k] = gate index or NONE. layout = the editable board."""

    def __init__(self, gates=(), outputs=(NONE,) * 4, layout=None):
        self.gates = list(gates)
        self.outputs = list(outputs)
        self.layout = layout


class Board:
    """Editable layout: parts[i] = (kind, x, y) or None, wires[sink] = source."""

    def __init__(self):
        self.parts = [None] * PARTS
        self.wires = [NONE] * LAYOUT_IDS

    def copy(self):
        b = Board()
        b.parts = list(self.parts)
        b.wires = list(self.wires)
        return b

    # -- edits (the same refusals as the 6502 code) --------------------

    def place(self, kind, x, y):
        """Put a part in the first free slot; its index, or None if full."""
        for i, p in enumerate(self.parts):
            if p is None:
                self.parts[i] = (kind, x, y)
                return i
        return None

    def remove(self, i):
        """Take part i away with every wire touching it."""
        self.parts[i] = None
        for k in range(4):
            self.wires[8 + i * 4 + k] = NONE
        for s in range(LAYOUT_IDS):
            if 8 + i * 4 <= self.wires[s] < 12 + i * 4:
                self.wires[s] = NONE

    def connect(self, source, sink):
        self.wires[sink] = source

    def disconnect(self, sink):
        self.wires[sink] = NONE

    def at(self, x, y):
        for i, p in enumerate(self.parts):
            if p is not None and p[1] == x and p[2] == y:
                return i
        return None


class Flat:
    """A compiled board: gates [(kind, a, b)], sinks[8] = flat source ids."""

    def __init__(self, gates, sinks):
        self.gates = gates
        self.sinks = sinks


def compile_board(board, chips):
    """Layout -> Flat, or None when it needs more than BOARD_GATES gates."""
    base = [0] * PARTS
    count = 0
    for i, p in enumerate(board.parts):
        if p is None:
            continue
        base[i] = count
        count += len(chips[p[0] - CHIP0].gates) if p[0] >= CHIP0 else 1
    if count > BOARD_GATES:
        return None

    def resolve(source):
        """Layout source id -> flat source id."""
        if source == NONE or source < TERMINALS:
            return source
        i, k = divmod(source - TERMINALS, 4)
        p = board.parts[i]
        if p is None:
            return NONE
        if p[0] < CHIP0:
            return TERMINALS + base[i] if k == 0 else NONE
        g = chips[p[0] - CHIP0].outputs[k]
        return NONE if g == NONE else TERMINALS + base[i] + g

    gates = []
    for i, p in enumerate(board.parts):
        if p is None:
            continue
        ins = [resolve(board.wires[TERMINALS + i * 4 + k]) for k in range(4)]
        if p[0] < CHIP0:
            gates.append((p[0], ins[0], ins[1] if GATE_INPUTS[p[0]] == 2 else NONE))
            continue
        for kind, a, b in chips[p[0] - CHIP0].gates:
            def inner(s):
                if s == NONE:
                    return NONE
                return ins[s] if s < 4 else TERMINALS + base[i] + s - 4
            gates.append((kind, inner(a), inner(b)))
    sinks = [resolve(board.wires[k]) for k in range(TERMINALS)]
    return Flat(gates, sinks)


def burn(board, chips):
    """Lab board -> Chip, or None when over CHIP_GATES (or BOARD_GATES)."""
    flat = compile_board(board, chips)
    if flat is None:
        return None

    def local(s):
        if s == NONE or 4 <= s < TERMINALS:
            return NONE                     # lab sources 4-7 are always 0
        return s if s < 4 else 4 + s - TERMINALS

    gates = [(k, local(a), local(b)) for k, a, b in flat.gates]
    outputs = []
    for k in range(4):
        s = flat.sinks[k]
        if s == NONE or 4 <= s < TERMINALS:
            outputs.append(NONE)
        elif s < 4:                         # E -> S directly: one BUF delay
            gates.append((BUF, s, NONE))
            outputs.append(len(gates) - 1)
        else:
            outputs.append(s - TERMINALS)
    if len(gates) > CHIP_GATES:
        return None
    return Chip(gates, outputs, board.copy())


class Sim:
    """Values of the 72 flat sources; tick() = one synchronous turn."""

    def __init__(self, flat):
        self.flat = flat
        self.values = [0] * (TERMINALS + BOARD_GATES)

    def value(self, s):
        return 0 if s == NONE else self.values[s]

    def tick(self, sources):
        v = self.values
        v[:TERMINALS] = [x & 1 for x in sources]
        new = [gate(k, self.value(a), self.value(b), v[TERMINALS + g])
               for g, (k, a, b) in enumerate(self.flat.gates)]
        v[TERMINALS:TERMINALS + len(new)] = new

    def sinks(self):
        return [self.value(s) for s in self.flat.sinks]


# -- byte images shared with the 6502 code (src/board.h) -----------------

def layout_bytes(board):
    """16 x (kind, x, y) then the 72 wire bytes: 120 bytes."""
    out = bytearray()
    for p in board.parts:
        out += bytes(p) if p else bytes(3)
    return bytes(out + bytes(board.wires))


def _planar(gates, size):
    pad = [(0, 0, 0)] * (size - len(gates))
    rows = list(gates) + pad
    return bytes(k for k, _, _ in rows) + bytes(a for _, a, _ in rows) \
        + bytes(b for _, _, b in rows)


def flat_bytes(flat):
    """count, kinds[64], a[64], b[64], sinks[8]: 201 bytes."""
    return bytes([len(flat.gates)]) + _planar(flat.gates, BOARD_GATES) + bytes(flat.sinks)


def chip_bytes(chip):
    """count, kinds[32], a[32], b[32], outputs[4]: 101 bytes."""
    return bytes([len(chip.gates)]) + _planar(chip.gates, CHIP_GATES) + bytes(chip.outputs)


# -- the test zone and the missions (docs/SPEC.md, "La zone d'essai") ---

TILE_W, TILE_H = 7, 8                       # color pixels
ROOM_COLS, ROOM_ROWS = 20, 18               # 140 x 144 pixels
DRONE_W, DRONE_H = 10, 12
OBJ_W, OBJ_H = 7, 8
OBJECTS = 4
N, E, S, W = 0, 1, 2, 3
SRC_HOLD, SINK_GRAB = 4, 4                  # board terminal 4: TIENT / PINCE
SRC_RADIO, SINK_RADIO = 5, 5                # board terminal 5: RECOIT / EMET

FLOOR, WALL, GRATE, CHARGER, DOOR, PLATE, DOOR2, PLATE2, TUNNEL = range(9)
TILES = {'#': WALL, '=': GRATE, 'X': CHARGER, '|': DOOR, '_': PLATE,
         '!': DOOR2, ',': PLATE2, '+': TUNNEL}
TECH_W, TECH_H = 5, 9
CELL, CRATE = 1, 2
OBJECT_KINDS = {'C': CELL, 'B': CRATE}

# A mission is won when its goal sits on a charger tile 'X' (tested by
# centre): the drone, a released cell 'C', or the technician. The
# technician cannot cross grates '=', the drones cannot cross tunnels '+'.
# Doors '|' are walls unless a plate '_' is pressed (the centre of a drone,
# an object or the technician on it) or something stands in one of them;
# doors '!' and plates ',' are a second, independent group.
GOAL_DRONE, GOAL_CELL, GOAL_TECH = 0, 1, 2
MISSIONS = (
    ('TOUT DROIT', GOAL_DRONE, (
        '####################',
        '#..................#',
        '#..................#',
        '#..................#',
        '#..................#',
        '#..................#',
        '#..............XXX.#',
        '#.D............XXX.#',
        '#..............XXX.#',
        '#..............XXX.#',
        '#..................#',
        '#..................#',
        '#..T...............#',
        '#..................#',
        '#..................#',
        '#..................#',
        '#..................#',
        '####################')),
    ('LE VIRAGE', GOAL_DRONE, (
        '####################',
        '#..................#',
        '#.D................#',
        '#..................#',
        '#..................#',
        '#......######......#',
        '#..................#',
        '#..................#',
        '#..T...............#',
        '#..................#',
        '#..................#',
        '#.....######.......#',
        '#..................#',
        '#..................#',
        '#...............XXX#',
        '#...............XXX#',
        '#...............XXX#',
        '####################')),
    ('LE PILIER', GOAL_DRONE, (
        '####################',
        '#.........#........#',
        '#.D.......#........#',
        '#.........#........#',
        '#.........#........#',
        '#.........#........#',
        '#.........#........#',
        '#.........#........#',
        '#.........#........#',
        '#..................#',
        '#..................#',
        '#..T...............#',
        '#..................#',
        '#..................#',
        '#......XXX.........#',
        '#......XXX.........#',
        '#......XXX.........#',
        '####################')),
    ('LA CELLULE', GOAL_CELL, (
        '####################',
        '#.........=........#',
        '#.........=........#',
        '#.........=........#',
        '#.........=........#',
        '#.........=........#',
        '#.XXX.....=........#',
        '#DXXX.....=....C...#',
        '#.XXX.....=........#',
        '#.........=........#',
        '#.........=........#',
        '#.........=........#',
        '#..T......=........#',
        '#.........=........#',
        '#.........=........#',
        '#.........=........#',
        '#.........=........#',
        '####################')),
    ('LA PORTE', GOAL_DRONE, (
        '####################',
        '#.........#........#',
        '#.........#........#',
        '#.D.......|......XX#',
        '#.........|......XX#',
        '#.........#........#',
        '#.........#........#',
        '#.......__#........#',
        '#.......__#........#',
        '#..T......#........#',
        '#.........#........#',
        '#.........#........#',
        '#.........#........#',
        '#.........#........#',
        '#.........#........#',
        '#.........#........#',
        '#.........#........#',
        '####################')),
    ('LE PARKING', GOAL_TECH, (
        '####################',
        '#.........#........#',
        '#.D.....__#........#',
        '#.......__#........#',
        '#.........#........#',
        '#.........#........#',
        '#.........|.....XX.#',
        '#.........|.....XX.#',
        '#.........#........#',
        '#..T......#........#',
        '#.........#........#',
        '#.........#........#',
        '#.........#........#',
        '#.........#........#',
        '#.........#........#',
        '#.........#........#',
        '#.........#........#',
        '####################')),
    ('LE RELAIS', GOAL_DRONE, (
        '####################',
        '#........#.,,......#',
        '#....D.__#.,,......#',
        '#......__#.........#',
        '#........#.........#',
        '#........#.........#',
        '#........#.........#',
        '#........#.........#',
        '#........#|||||||||#',
        '#........#.........#',
        '#........+.........#',
        '#........+.........#',
        '#..T.....#.........#',
        '#........#.........#',
        '#........#.........#',
        '#........!.E.....XX#',
        '#........!.......XX#',
        '####################')),
)


def room_tiles(room):
    """One byte per tile, row by row: FLOOR, WALL, GRATE or CHARGER."""
    return bytes(TILES.get(ch, FLOOR) for row in room for ch in row)


def room_start(ch, room):
    for ty, row in enumerate(room):
        if ch in row:
            return row.index(ch) * TILE_W, ty * TILE_H
    raise ValueError(ch)


def room_objects(room):
    """[[kind, x, y]] in reading order, at most OBJECTS."""
    out = [[OBJECT_KINDS[ch], tx * TILE_W, ty * TILE_H]
           for ty, row in enumerate(room) for tx, ch in enumerate(row) if ch in OBJECT_KINDS]
    assert len(out) <= OBJECTS
    return out


def tile(tiles, x, y):
    """Outside the room counts as wall."""
    if not (0 <= x < ROOM_COLS * TILE_W and 0 <= y < ROOM_ROWS * TILE_H):
        return WALL
    return tiles[(y // TILE_H) * ROOM_COLS + x // TILE_W]


def inside(px, py, x, y, w, h):
    return x <= px < x + w and y <= py < y + h


class Drone:
    """One drone: its box, the object it holds, its board, its radio."""

    def __init__(self, x, y, flat):
        self.x, self.y = x, y
        self.holding = None                 # index of the held object
        self.sim = Sim(flat)
        self.emit = 0                       # sink 5 after its last turn


class Zone:
    """The room of one mission: one or two drones ('D', then 'E' in the
    room), the objects, the doors, the technician, the goal."""

    def __init__(self, mission, flat, flat2=None):
        _, self.goal, room = MISSIONS[mission]
        self.tiles = room_tiles(room)
        self.tech = None                    # technician in the room: x, y
        self.door_open = [0, 0]             # groups '_'/'|' and ','/'!'
        self.objects = room_objects(room)
        self.drones = [Drone(*room_start('D', room), flat)]
        if any('E' in row for row in room):
            self.drones.append(Drone(*room_start('E', room), flat2 or Flat([], [NONE] * 8)))

    # The first drone, as the one-drone missions knew it.
    x = property(lambda self: self.drones[0].x)
    y = property(lambda self: self.drones[0].y)
    holding = property(lambda self: self.drones[0].holding)

    def tile(self, x, y, d=None):
        """What blocks drone d (None: the technician): a closed door is a
        wall, an open one floor; tunnels are walls for drones only."""
        t = tile(self.tiles, x, y)
        if t in (DOOR, DOOR2):
            return FLOOR if self.door_open[t == DOOR2] else WALL
        if t == TUNNEL:
            return FLOOR if d is None else WALL
        return t

    def boxes(self):
        """Drones, objects, technician: x, y, w, h."""
        out = [(d.x, d.y, DRONE_W, DRONE_H) for d in self.drones]
        out += [(ox, oy, OBJ_W, OBJ_H) for _, ox, oy in self.objects]
        if self.tech is not None:
            out.append((self.tech[0], self.tech[1], TECH_W, TECH_H))
        return out

    def update_doors(self):
        """A group is open while one of its plates is pressed (a box's
        centre on it) or one of its doorways is not empty."""
        for g, (door, plate) in enumerate(((DOOR, PLATE), (DOOR2, PLATE2))):
            def on_door(x, y, w, h):
                return any(tile(self.tiles, px, py) == door
                           for px in range(x, x + w) for py in range(y, y + h))
            self.door_open[g] = int(any(tile(self.tiles, x + w // 2, y + h // 2) == plate
                                        or on_door(x, y, w, h) for x, y, w, h in self.boxes()))

    def obstacle(self, x, y, d):
        """For drone d: walls, the objects it does not hold, the other drone."""
        if self.tile(x, y, d) == WALL:
            return 1
        if any(inside(x, y, ox, oy, OBJ_W, OBJ_H)
               for i, (_, ox, oy) in enumerate(self.objects) if i != d.holding):
            return 1
        return int(any(inside(x, y, o.x, o.y, DRONE_W, DRONE_H) for o in self.drones if o is not d))

    def side_blocked(self, x, y, w, h, side, d):
        """Something right next to that side of the box x, y, w, h?
        Samples every 5 pixels at most, so nothing slips between them."""
        if side in (N, S):
            yy = y - 1 if side == N else y + h
            return int(any(self.obstacle(sx, yy, d) for sx in (x, x + w // 2, x + w - 1)))
        xx = x - 1 if side == W else x + w
        return int(any(self.obstacle(xx, sy, d) for sy in (y, y + h // 2, y + h - 1)))

    def bumpers(self, d=None):
        d = d or self.drones[0]
        return [self.side_blocked(d.x, d.y, DRONE_W, DRONE_H, k, d) for k in (N, E, S, W)]

    def free(self, d, side):
        """Drone d, and the object it holds, can move one pixel that way."""
        if self.side_blocked(d.x, d.y, DRONE_W, DRONE_H, side, d):
            return False
        if d.holding is not None:
            _, ox, oy = self.objects[d.holding]
            if self.side_blocked(ox, oy, OBJ_W, OBJ_H, side, d):
                return False
        return True

    def move(self, d, dx, dy):
        d.x += dx
        d.y += dy
        if d.holding is not None:
            self.objects[d.holding][1] += dx
            self.objects[d.holding][2] += dy

    def tick(self):
        """0. doors; 1. each drone's sources: 0-3 bumpers N, E, S, W,
        4 holding, 5 radio = what the other drone emitted last turn; 2. one
        turn of each board; then drone by drone, in order: 3. sinks 0-3 =
        thrusters (a thruster pushes away from its side), 4 = grabber,
        5 = radio; 4. grabber off: let go; on: take the first object
        touching the drone (not held by the other); 5. one pixel along x if
        free, then along y (the held object comes along)."""
        self.update_doors()
        heard = [self.drones[1 - i].emit if len(self.drones) == 2 else 0
                 for i in range(len(self.drones))]
        for i, d in enumerate(self.drones):
            d.sim.tick(self.bumpers(d) + [int(d.holding is not None), heard[i], 0, 0])
        for d in self.drones:
            t = d.sim.sinks()
            d.emit = t[SINK_RADIO]
            if not t[SINK_GRAB]:
                d.holding = None
            elif d.holding is None:
                taken = [o.holding for o in self.drones if o is not d]
                for i, (_, ox, oy) in enumerate(self.objects):
                    if (i not in taken and ox <= d.x + DRONE_W and d.x <= ox + OBJ_W
                            and oy <= d.y + DRONE_H and d.y <= oy + OBJ_H):
                        d.holding = i
                        break
            vx, vy = t[W] - t[E], t[N] - t[S]
            if vx and self.free(d, E if vx > 0 else W):
                self.move(d, vx, 0)
            if vy and self.free(d, S if vy > 0 else N):
                self.move(d, 0, vy)

    def won(self):
        if self.goal == GOAL_CELL:
            held = [d.holding for d in self.drones]
            return any(o[0] == CELL and i not in held
                       and tile(self.tiles, o[1] + OBJ_W // 2, o[2] + OBJ_H // 2) == CHARGER
                       for i, o in enumerate(self.objects))
        if self.goal == GOAL_TECH:
            return self.tech is not None and tile(
                self.tiles, self.tech[0] + TECH_W // 2, self.tech[1] + TECH_H // 2) == CHARGER
        d = self.drones[0]                  # the first drone ('D') must get there
        return tile(self.tiles, d.x + DRONE_W // 2, d.y + DRONE_H // 2) == CHARGER


# -- the save file RSS.SAVE (src/sim.h Persist) ----------------------------

SAVE_SIZE = 4 + 1 + CHIPS * (1 + 3 * CHIP_GATES + 4 + LAYOUT_IDS + 3 * PARTS) + 3 * (LAYOUT_IDS + 3 * PARTS)


def save_bytes(chips, reached=0, lab=None, drone=None, drone2=None):
    """The image of Persist: chips[] as burned (empty Chip() = free slot)."""
    def planar(field):
        out = bytearray()
        for c in chips:
            rows = [g[field] for g in c.gates] + [0] * (CHIP_GATES - len(c.gates))
            out += bytes(rows)
        return bytes(out)
    out = bytearray(b'RSS2') + bytes([reached])
    out += bytes(len(c.gates) for c in chips)
    out += planar(0) + planar(1) + planar(2)
    out += b''.join(bytes(c.outputs) for c in chips)
    out += b''.join(layout_bytes(c.layout) if c.layout else bytes(48) + bytes([NONE] * 72)
                    for c in chips)
    for b in (lab, drone, drone2):
        out += layout_bytes(b) if b else bytes(48) + bytes([NONE] * 72)
    assert len(out) == SAVE_SIZE
    return bytes(out)
