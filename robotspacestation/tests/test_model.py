#!/usr/bin/env python3
"""The reference model's rules (docs/SPEC.md), host only."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from model import (AND, OR, XOR, NOT, FLIP, BUF, CHIP0, NONE, Board, Chip,
                   Sim, burn, compile_board, chip_bytes, flat_bytes,
                   layout_bytes, Zone, MISSIONS, SINK_GRAB, GOAL_TECH,
                   SRC_RADIO, SINK_RADIO, OR, DRONE_W)

EMPTY = [Chip() for _ in range(8)]


def out(i, k=0):
    return 8 + i * 4 + k


def inp(i, k):
    return 8 + i * 4 + k


def run(board, inputs, ticks, chips=EMPTY):
    sim = Sim(compile_board(board, chips))
    for _ in range(ticks):
        sim.tick(inputs)
    return sim.sinks()


class Gates(unittest.TestCase):
    def test_truth_tables_after_one_tick(self):
        for kind, table in ((AND, (0, 0, 0, 1)), (OR, (0, 1, 1, 1)),
                            (XOR, (0, 1, 1, 0))):
            b = Board()
            i = b.place(kind, 0, 0)
            b.connect(0, inp(i, 0))
            b.connect(1, inp(i, 1))
            b.connect(out(i), 0)
            for n, want in enumerate(table):
                ab = [n >> 1, n & 1, 0, 0, 0, 0, 0, 0]
                self.assertEqual(run(b, ab, 0)[0], 0)
                self.assertEqual(run(b, ab, 1)[0], want, (kind, n))

    def test_not_starts_at_zero(self):
        b = Board()
        i = b.place(NOT, 0, 0)
        b.connect(out(i), 0)
        self.assertEqual(run(b, [0] * 8, 0)[0], 0)
        self.assertEqual(run(b, [0] * 8, 1)[0], 1)

    def test_not_loop_oscillates(self):
        b = Board()
        i = b.place(NOT, 0, 0)
        b.connect(out(i), inp(i, 0))
        b.connect(out(i), 0)
        sim = Sim(compile_board(b, EMPTY))
        seen = []
        for _ in range(6):
            sim.tick([0] * 8)
            seen.append(sim.sinks()[0])
        self.assertEqual(seen, [1, 0, 1, 0, 1, 0])

    def test_flip_set_wins(self):
        b = Board()
        i = b.place(FLIP, 0, 0)
        b.connect(0, inp(i, 0))
        b.connect(1, inp(i, 1))
        b.connect(out(i), 0)
        sim = Sim(compile_board(b, EMPTY))
        for s, r, want in ((1, 0, 1), (0, 0, 1), (0, 1, 0), (0, 0, 0), (1, 1, 1)):
            sim.tick([s, r] + [0] * 6)
            self.assertEqual(sim.sinks()[0], want, (s, r))

    def test_direct_wire_has_no_delay(self):
        b = Board()
        b.connect(2, 3)
        self.assertEqual(run(b, [0, 0, 1, 0, 0, 0, 0, 0], 1)[3], 1)

    def test_remove_drops_wires(self):
        b = Board()
        i = b.place(AND, 0, 0)
        j = b.place(NOT, 1, 0)
        b.connect(0, inp(i, 0))
        b.connect(out(i), inp(j, 0))
        b.connect(out(i), 1)
        b.remove(i)
        self.assertEqual(b.wires[inp(j, 0)], NONE)
        self.assertEqual(b.wires[1], NONE)
        self.assertEqual(b.wires[inp(i, 0)], NONE)


class Chips(unittest.TestCase):
    def half_adder(self):
        b = Board()
        x = b.place(XOR, 0, 0)
        a = b.place(AND, 0, 1)
        for g in (x, a):
            b.connect(0, inp(g, 0))
            b.connect(1, inp(g, 1))
        b.connect(out(x), 0)
        b.connect(out(a), 1)
        return b

    def test_burn_and_use(self):
        chips = list(EMPTY)
        chips[2] = burn(self.half_adder(), chips)
        self.assertEqual(len(chips[2].gates), 2)
        self.assertEqual(chips[2].outputs[:2], [0, 1])
        b = Board()
        c = b.place(CHIP0 + 2, 0, 0)
        b.connect(0, inp(c, 0))
        b.connect(1, inp(c, 1))
        b.connect(out(c, 0), 0)
        b.connect(out(c, 1), 1)
        self.assertEqual(run(b, [1, 1, 0, 0, 0, 0, 0, 0], 1, chips)[:2], [0, 1])
        self.assertEqual(run(b, [1, 0, 0, 0, 0, 0, 0, 0], 1, chips)[:2], [1, 0])

    def test_pass_through_gets_a_buffer(self):
        b = Board()
        b.connect(3, 2)
        chip = burn(b, EMPTY)
        self.assertEqual(chip.gates, [(BUF, 3, NONE)])
        self.assertEqual(chip.outputs, [NONE, NONE, 0, NONE])

    def test_nested_chip_flattens(self):
        chips = list(EMPTY)
        chips[0] = burn(self.half_adder(), chips)
        b = Board()
        c = b.place(CHIP0, 0, 0)
        n = b.place(NOT, 1, 0)
        b.connect(0, inp(c, 0))
        b.connect(1, inp(c, 1))
        b.connect(out(c, 1), inp(n, 0))
        b.connect(out(n), 0)
        chips[1] = burn(b, chips)
        self.assertEqual(len(chips[1].gates), 3)
        # NAND after two ticks: carry, then its inverse.
        b2 = Board()
        c2 = b2.place(CHIP0 + 1, 0, 0)
        b2.connect(0, inp(c2, 0))
        b2.connect(1, inp(c2, 1))
        b2.connect(out(c2, 0), 0)
        self.assertEqual(run(b2, [1, 1] + [0] * 6, 2, chips)[0], 0)
        self.assertEqual(run(b2, [1, 0] + [0] * 6, 2, chips)[0], 1)

    def test_gate_limits(self):
        chips = list(EMPTY)
        b = Board()
        for k in range(16):
            b.place(NOT, k % 5, k // 5)
        chips[0] = burn(b, chips)
        self.assertEqual(len(chips[0].gates), 16)
        big = Board()
        big.place(CHIP0, 0, 0)
        big.place(CHIP0, 1, 0)
        self.assertEqual(len(burn(big, chips).gates), 32)
        big.place(NOT, 2, 0)
        self.assertIsNone(burn(big, chips))
        self.assertIsNotNone(compile_board(big, chips))
        chips[1] = burn(self._two(chips), chips)
        many = Board()
        for k in range(3):
            many.place(CHIP0 + 1, k, 0)
        self.assertIsNone(compile_board(many, chips))

    def _two(self, chips):
        b = Board()
        b.place(CHIP0, 0, 0)
        b.place(CHIP0, 1, 0)
        return b


class Images(unittest.TestCase):
    def test_sizes(self):
        b = Board()
        b.place(AND, 1, 2)
        self.assertEqual(len(layout_bytes(b)), 120)
        self.assertEqual(layout_bytes(b)[:3], bytes((AND, 1, 2)))
        self.assertEqual(len(flat_bytes(compile_board(b, EMPTY))), 201)
        self.assertEqual(len(chip_bytes(burn(b, EMPTY))), 101)




def wire(b, src, sink):
    b.connect(src, sink)


def solution(mission):
    """A board that wins each mission (layout ids: 8 + part*4 + k)."""
    b = Board()
    if mission in (0, 4, 5):            # always push east
        n = b.place(NOT, 0, 0)
        wire(b, out(n), 3)
    elif mission == 1:                  # east, and south once against a wall
        n = b.place(NOT, 0, 0)
        wire(b, out(n), 3)
        wire(b, 1, 0)
    elif mission == 2:                  # latch the bump: then only south
        f = b.place(FLIP, 1, 0)
        k = b.place(NOT, 2, 0)
        wire(b, 1, inp(f, 0))
        wire(b, out(f), inp(k, 0))
        wire(b, out(k), 3)
        wire(b, out(f), 0)
    elif mission == 6:
        return relay()
    elif mission == 13:
        return tandem()
    elif mission == 14:
        return counter()
    elif mission == 15:
        return spiral()
    elif mission == 16:                 # LE DEMENAGEMENT: north to the cell, take it,
        l1 = b.place(FLIP, 0, 0)        # east, south, let it go at the bottom
        l2 = b.place(FLIP, 1, 0)
        a = b.place(AND, 2, 0)
        n1 = b.place(NOT, 3, 0)
        n2 = b.place(NOT, 0, 1)
        g = b.place(AND, 1, 1)
        ns = b.place(NOT, 2, 1)
        h = b.place(AND, 3, 1)
        wire(b, 0, inp(l1, 0))          # the cell above: L1
        wire(b, 1, inp(a, 0))           # the east wall once L1: L2
        wire(b, out(l1), inp(a, 1))
        wire(b, out(a), inp(l2, 0))
        wire(b, out(l1), inp(n1, 0))
        wire(b, out(n1), 2)             # not L1: north
        wire(b, out(l2), inp(n2, 0))
        wire(b, out(n2), inp(g, 0))
        wire(b, out(l1), inp(g, 1))
        wire(b, out(g), 3)              # L1, not L2: east
        wire(b, out(l2), 0)             # L2: south
        wire(b, 2, inp(ns, 0))
        wire(b, out(ns), inp(h, 0))
        wire(b, out(l1), inp(h, 1))
        wire(b, out(h), SINK_GRAB)      # held from L1 to the bottom
    elif mission == 7:                  # south always, east / west by turns
        n = b.place(NOT, 0, 0)
        f = b.place(FLIP, 1, 0)
        k = b.place(NOT, 2, 0)
        wire(b, out(n), 0)
        wire(b, 1, inp(f, 0))           # east bump: go west
        wire(b, 3, inp(f, 1))           # west bump: go east
        wire(b, out(f), 1)
        wire(b, out(f), inp(k, 0))
        wire(b, out(k), 3)
    elif mission in (9, 11, 17):        # LE GARDIEN: the pillar's latch parks it;
        return solution({9: 2, 11: 0, 17: 12}[mission])   # LE SAS: east, as in 1;
                                        # LES DEUX CLES: LA CAISSE's board
    elif mission == 12:                 # LA CAISSE: north to the crate, take it east,
        l1 = b.place(FLIP, 0, 0)        # let it go on the plate, south through the door
        l2 = b.place(FLIP, 1, 0)
        a = b.place(AND, 2, 0)
        n1 = b.place(NOT, 3, 0)
        n2 = b.place(NOT, 0, 1)
        g = b.place(AND, 1, 1)
        wire(b, 0, inp(l1, 0))          # the north bump: L1
        wire(b, 1, inp(a, 0))           # the east bump once L1: L2
        wire(b, out(l1), inp(a, 1))
        wire(b, out(a), inp(l2, 0))
        wire(b, out(l1), inp(n1, 0))
        wire(b, out(n1), 2)             # not L1: north
        wire(b, out(l2), inp(n2, 0))
        wire(b, out(n2), inp(g, 0))
        wire(b, out(l1), inp(g, 1))
        wire(b, out(g), SINK_GRAB)      # L1, not L2: hold it, east
        wire(b, out(g), 3)
        wire(b, out(l2), 0)             # L2: south
    elif mission == 10:                 # LA RONDE: east, then south, then west
        l1 = b.place(FLIP, 0, 0)
        l2 = b.place(FLIP, 1, 0)
        n1 = b.place(NOT, 2, 0)
        a = b.place(AND, 3, 0)
        n2 = b.place(NOT, 0, 1)
        a2 = b.place(AND, 1, 1)
        wire(b, 1, inp(l1, 0))          # the east bump: L1
        wire(b, 2, inp(a, 0))           # the south bump once L1: L2
        wire(b, out(l1), inp(a, 1))
        wire(b, out(a), inp(l2, 0))
        wire(b, out(l1), inp(n1, 0))
        wire(b, out(n1), 3)             # not L1: east
        wire(b, out(l2), inp(n2, 0))
        wire(b, out(n2), inp(a2, 0))
        wire(b, out(l1), inp(a2, 1))
        wire(b, out(a2), 0)             # L1, not L2: south
        wire(b, out(l2), 1)             # L2: west
    else:                               # fetch the cell, bring it back (3, 8)
        f = b.place(FLIP, 1, 0)
        k = b.place(NOT, 2, 0)
        j = b.place(NOT, 2, 1)
        a = b.place(AND, 3, 1)
        wire(b, 1, inp(f, 0))
        wire(b, out(f), inp(k, 0))
        wire(b, out(k), 3)              # not latched: push east
        wire(b, out(f), 1)              # latched: push west
        wire(b, 3, inp(j, 0))
        wire(b, out(f), inp(a, 0))
        wire(b, out(j), inp(a, 1))
        wire(b, out(a), SINK_GRAB)      # hold until the west wall
    return b


# Where the technician stands in each mission's solution (None: inside).
TECH = {4: (8 * 7 + 1, 7 * 8 + 2),      # on LA PORTE's plate (columns 8-9)
        8: (6 * 7 + 4, 10 * 8 + 4)}     # on LE COLIS's plate (columns 6-7)


def relay():
    """LE RELAIS: A holds the plate until B, parked on its own plate, calls
    by radio; then A goes south and, at the bottom, east. B: always north,
    calling once against the top wall."""
    a = Board()
    f = a.place(FLIP, 0, 0)
    n = a.place(NOT, 1, 0)
    o = a.place(OR, 2, 0)
    wire(a, SRC_RADIO, inp(f, 0))
    wire(a, out(f), inp(n, 0))
    wire(a, out(f), 0)                  # called: push south
    wire(a, out(n), inp(o, 0))
    wire(a, 2, inp(o, 1))
    wire(a, out(o), 3)                  # not called, or at the bottom: east
    b = Board()
    k = b.place(NOT, 0, 0)
    wire(b, out(k), 2)                  # push north
    wire(b, 0, SINK_RADIO)              # against the top wall: call
    return a, b


def tandem(radio=True):
    """LE TANDEM: A goes east onto the plate beyond the grate and calls
    there; B waits for the call (a latch), then fetches the cell through the
    door A holds open (LA CELLULE's board, its east thrust gated)."""
    a = Board()
    n = a.place(NOT, 0, 0)
    wire(a, out(n), 3)                  # east
    wire(a, 1, SINK_RADIO)              # against the east wall, on the plate: call
    b = solution(3)
    r = b.place(FLIP, 0, 1)
    g = b.place(AND, 0, 2)
    k = [i for i, p in enumerate(b.parts) if p and p[0] == NOT][0]
    b.disconnect(3)
    wire(b, SRC_RADIO, inp(r, 0))       # the call, latched
    wire(b, out(k), inp(g, 0))
    wire(b, out(r), inp(g, 1))
    wire(b, out(g), 3)                  # east only once called
    if not radio:
        b.disconnect(inp(g, 1))
        wire(b, out(k), inp(g, 1))      # (AND with itself: no wait)
    return a, b


def counter(first=False):
    """LE COMPTEUR: south down the shaft along its west wall; W two turns
    late and NOT W a turn late make a falling edge (an opening); the
    second one turns the drone west (first: the first one, the trap)."""
    b = Board()
    d1 = b.place(AND, 0, 0)
    d2 = b.place(AND, 1, 0)
    nw = b.place(NOT, 2, 0)
    f = b.place(AND, 3, 0)
    l1 = b.place(FLIP, 0, 1)
    g = b.place(AND, 1, 1)
    l2 = b.place(FLIP, 2, 1)
    n0 = b.place(NOT, 3, 1)
    wire(b, 3, inp(d1, 0))              # W, a turn late
    wire(b, 3, inp(d1, 1))
    wire(b, out(d1), inp(d2, 0))        # two turns late
    wire(b, out(d1), inp(d2, 1))
    wire(b, 3, inp(nw, 0))              # not W, a turn late
    wire(b, out(d2), inp(f, 0))         # an opening begins
    wire(b, out(nw), inp(f, 1))
    wire(b, out(f), inp(l1, 0))         # the first
    wire(b, out(f), inp(g, 0))
    wire(b, out(l1), inp(g, 1))
    wire(b, out(f) if first else out(g), inp(l2, 0))   # the second
    wire(b, out(l2), 1)                 # then west
    wire(b, out(l2), inp(n0, 0))
    wire(b, out(n0), 0)                 # until then south
    return b


def spiral():
    """LA SPIRALE: heading east (no latch), south (A), west (B), north (C);
    a bump ahead turns right (the next latch set, the last one reset)."""
    b = Board()
    A = b.place(FLIP, 0, 0)
    B = b.place(FLIP, 1, 0)
    C = b.place(FLIP, 2, 0)
    o1 = b.place(OR, 3, 0)
    o2 = b.place(OR, 4, 0)
    e = b.place(NOT, 0, 1)
    turns = [b.place(AND, k, 1) for k in range(1, 5)]
    wire(b, out(A), inp(o1, 0))
    wire(b, out(B), inp(o1, 1))
    wire(b, out(o1), inp(o2, 0))
    wire(b, out(C), inp(o2, 1))
    wire(b, out(o2), inp(e, 0))         # east: none of them
    for t, bump, state, sets, resets in ((turns[0], 1, e, A, None), (turns[1], 2, A, B, A),
                                         (turns[2], 3, B, C, B), (turns[3], 0, C, None, C)):
        wire(b, bump, inp(t, 0))        # a bump ahead, in that heading
        wire(b, out(state), inp(t, 1))
        if sets is not None:
            wire(b, out(t), inp(sets, 0))
    wire(b, out(B), inp(A, 1))          # each heading resets the previous one
    wire(b, out(C), inp(B, 1))
    wire(b, out(turns[3]), inp(C, 1))   # north's bump: east again
    for state, sink in ((e, 3), (A, 0), (B, 1), (C, 2)):
        wire(b, out(state), sink)       # the thruster opposite the heading
    return b


def play(mission, board, ticks=600, tech=None, board2=None):
    if isinstance(board, tuple):
        board, board2 = board
    z = Zone(mission, compile_board(board, EMPTY),
             compile_board(board2, EMPTY) if board2 else None)
    z.tech = TECH.get(mission) if tech is None else tech
    for t in range(ticks):
        z.tick()
        if z.won():
            return t + 1, z
    return None, z


class Missions(unittest.TestCase):
    def test_each_mission_has_a_solution(self):
        for m in range(len(MISSIONS)):
            if MISSIONS[m][1] == GOAL_TECH:
                continue
            t, z = play(m, solution(m), 1500)
            self.assertIsNotNone(t, (MISSIONS[m][0], z.x, z.y, z.objects))

    def test_the_door_waits_for_the_technician(self):
        t, z = play(4, solution(4), 300, tech=(3 * 7, 9 * 8))   # not on the plate
        self.assertIsNone(t)
        self.assertEqual(z.x, 60)               # against the closed door
        self.assertEqual(z.door_open[0], 0)

    def test_the_doorway_jams_the_door(self):
        z = Zone(4, compile_board(solution(4), EMPTY))
        z.tech = TECH[4]
        for _ in range(4):                      # into the doorway
            z.tick()
        for _ in range(200):
            if z.x >= 66:
                break
            z.tick()
        self.assertGreaterEqual(z.x, 66)
        z.tech = (3 * 7, 9 * 8)                 # he steps off the plate
        for _ in range(100):
            z.tick()
        self.assertTrue(z.won())

    def test_relay_needs_the_radio(self):
        a, b = relay()
        # A leaves its plate as soon as it is there (a bump latch, no radio):
        # B is still far from the door, which shuts on it.
        a.disconnect(inp(0, 0))
        a.connect(1, inp(0, 0))
        t, z = play(6, (a, b), 800)
        self.assertIsNone(t)
        self.assertEqual(z.drones[1].y, 72)     # B stuck under the door
        # The radio heard a turn late: B calls at turn t, A hears at t + 1.
        t, z = play(6, relay(), 800)
        self.assertEqual((z.drones[1].x, z.drones[1].y), (77, 8))

    def test_drones_block_each_other(self):
        z = Zone(6, compile_board(Board(), EMPTY), compile_board(Board(), EMPTY))
        z.drones[1].x, z.drones[1].y = z.x + DRONE_W, z.y
        self.assertEqual(z.bumpers()[1], 1)

    def test_parking_opens_the_door_for_the_technician(self):
        z = Zone(5, compile_board(solution(5), EMPTY))
        z.tech = (3 * 7, 9 * 8)
        for _ in range(100):
            z.tick()
        self.assertEqual((z.x, z.door_open[0]), (60, 1))
        self.assertFalse(z.won())
        z.tech = (16 * 7 + 4, 6 * 8 + 4)        # walked through, on the charger
        self.assertTrue(z.won())
        self.assertFalse(play(5, Board(), 100, tech=(3 * 7, 9 * 8))[1].door_open[0])

    def test_zigzag_needs_the_turns(self):
        b = Board()                     # south and east only: stuck on the left
        n = b.place(NOT, 0, 0)
        wire(b, out(n), 0)
        wire(b, out(n), 3)
        self.assertIsNone(play(7, b, 1500)[0])

    def test_the_delivery_waits_for_the_technician(self):
        t, z = play(8, solution(8), 1500, tech=(3 * 7, 12 * 8))
        self.assertIsNone(t)
        self.assertEqual(z.door_open[0], 0)

    def test_the_guard_parks_on_the_plate(self):
        z = Zone(9, compile_board(solution(9), EMPTY))
        z.tech = (3 * 7, 11 * 8)
        for _ in range(400):
            z.tick()
        self.assertEqual((z.x, z.y, z.door_open[0]), (53, 124, 1))
        self.assertFalse(z.won())
        z.tech = (16 * 7 + 2, 2 * 8 + 4)        # through the door, on the charger
        self.assertTrue(z.won())
        z = Zone(9, compile_board(solution(1), EMPTY))   # no latch: never parked
        z.tech = (3 * 7, 11 * 8)
        for _ in range(400):
            z.tick()
        self.assertEqual(z.door_open[0], 0)

    def test_the_round_needs_two_latches(self):
        b = Board()                     # after the east bump, south and west at once
        f = b.place(FLIP, 0, 0)
        n = b.place(NOT, 1, 0)
        wire(b, 1, inp(f, 0))
        wire(b, out(f), inp(n, 0))
        wire(b, out(n), 3)
        wire(b, out(f), 0)
        wire(b, out(f), 1)
        t, z = play(10, b, 1500)
        self.assertIsNone(t)            # into the trap's opening
        self.assertIsNone(play(10, solution(1), 1500)[0])

    def test_the_airlock(self):
        z = Zone(11, compile_board(solution(11), EMPTY))
        z.tech = (2 * 7 + 4, 8 * 8 + 4)         # he holds the upper door
        for _ in range(300):
            z.tick()
        self.assertEqual((z.x, z.y, z.door_open), (123, 16, [1, 1]))
        z.tech = (15 * 7 + 4, 14 * 8 + 4)       # through the lower door
        self.assertTrue(z.won())
        z = Zone(11, compile_board(solution(11), EMPTY))
        z.tech = (3 * 7, 13 * 8)                # nobody on the plate
        for _ in range(300):
            z.tick()
        self.assertEqual((z.x, z.door_open), (46, [0, 0]))

    def test_the_crate_holds_the_door(self):
        t, z = play(12, solution(12), 2000)
        self.assertIsNotNone(t)
        self.assertEqual(z.objects[0][1:], [123, 34])  # on the plate
        b = solution(12)
        b.disconnect(SINK_GRAB)                         # without the claw
        t, z = play(12, b, 2000)
        self.assertIsNone(t)
        self.assertEqual(z.objects[0][1:], [56, 32])

    def test_the_tandem_waits_for_the_call(self):
        t, z = play(13, tandem(), 3000)
        self.assertIsNotNone(t)
        t, z = play(13, tandem(radio=False), 3000)
        self.assertIsNone(t)
        self.assertEqual(z.objects[0][1:], [105, 64])  # B came back empty

    def test_the_counter_skips_the_first_opening(self):
        t, z = play(14, counter(first=True), 1500)
        self.assertIsNone(t)
        self.assertEqual((z.x, z.y), (63, 59))   # in the trap
        b = Board()                             # south and west at once
        n = b.place(NOT, 0, 0)
        wire(b, out(n), 0)
        wire(b, out(n), 1)
        self.assertIsNone(play(14, b, 1500)[0])

    def test_the_spiral_needs_four_headings(self):
        t, z = play(15, spiral(), 1500)
        self.assertIsNotNone(t)
        self.assertIsNone(play(15, solution(10), 1500)[0])     # LA RONDE's three legs

    def test_the_move_holds_through_the_turns(self):
        b = solution(16)
        b.disconnect(SINK_GRAB)
        t, z = play(16, b, 1500)
        self.assertIsNone(t)
        self.assertEqual(z.objects[0][1:], [21, 16])   # left where it was
        self.assertIsNone(play(16, solution(3), 1500)[0])

    def test_two_keys(self):
        z = Zone(17, compile_board(solution(17), EMPTY))
        z.tech = (3 * 7, 11 * 8)
        for _ in range(500):
            z.tick()
        self.assertEqual((z.x, z.y, z.objects[0][1:], z.door_open), (123, 124, [123, 34], [1, 1]))
        z.tech = (13 * 7 + 2, 15 * 8 + 3)       # through both doors, on the charger
        self.assertTrue(z.won())
        b = solution(17)
        b.disconnect(SINK_GRAB)                 # no crate on the first plate
        z = Zone(17, compile_board(b, EMPTY))
        z.tech = (3 * 7, 11 * 8)
        for _ in range(500):
            z.tick()
        self.assertEqual(z.door_open, [0, 1])

    def test_an_empty_board_wins_nothing(self):
        for m in range(len(MISSIONS)):
            self.assertIsNone(play(m, Board(), 300)[0])

    def test_the_pillar_needs_a_latch(self):
        self.assertIsNone(play(2, solution(1))[0])

    def test_the_cell_must_be_let_go(self):
        b = solution(3)
        b.disconnect(SINK_GRAB)
        f = [i for i, p in enumerate(b.parts) if p and p[0] == FLIP][0]
        b.connect(out(f), SINK_GRAB)    # grab, never release
        t, z = play(3, b)
        self.assertIsNone(t)
        self.assertEqual(z.holding, 0)

    def test_corner_bumpers(self):
        z = Zone(0, compile_board(Board(), EMPTY))
        z.drones[0].x, z.drones[0].y = 7, 8
        self.assertEqual(z.bumpers(), [1, 0, 0, 1])


if __name__ == '__main__':
    unittest.main()
