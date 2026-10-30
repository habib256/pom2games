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
    elif mission in (9, 11):            # LE GARDIEN: the pillar's latch parks it;
        return solution(2 if mission == 9 else 0)   # LE SAS: east, as in 1
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
            t, z = play(m, solution(m))
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
