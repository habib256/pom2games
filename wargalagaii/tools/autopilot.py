#!/usr/bin/env python3
"""WARGALAGA II autopilot on tools/model.py: proves a level can be finished.

At every step it tries a few plans on copies of the model (deterministic,
random numbers included): hold left / nothing / right for PLAN steps, or
move for a few steps then stop. A plan that loses the ship within LOOK steps
is out; among the others, the one that ends nearest under its target wins
(the boss's core if there is a boss, else the nearest alien, lowest first).
It always fires (pressed and held: autofire when it has it). No cheat: it
starts the level as a new game does (3 lives, no armour).

    tools/autopilot.py LEVEL...      levels 1..100: steps to finish, lives left
"""
import copy
import sys

import model as M

LOOK = 10
PLANS = [(m, n) for m in (-1, 1) for n in (2, 5, LOOK)] + [(0, LOOK)]


def lost(game):
    return game.ship_state or game.game_over


def target_cell(game):
    """The cell the ship's middle (ship_c + 3) should be under."""
    if game.boss_hp:
        return game.boss_x + (M.BOSS_CORE0 + M.BOSS_CORE1) // 2
    best = None
    for i in range(M.NALIENS):
        s = game.a_state[i]
        if s in (M.DEAD, M.BOOM) or not game.shown(i):
            continue
        key = (-game.a_y[i], abs(game.a_x[i] + 3 - game.ship_c - 3))
        if best is None or key < best[0]:
            best = (key, game.a_x[i] + 3)
    return best[1] if best else game.ship_c + 3


def choose(game):
    """-> move for this step."""
    goal = target_cell(game)
    best = None
    for m, n in PLANS:
        sim = copy.deepcopy(game)
        safe = True
        for t in range(LOOK):
            sim.step(m if t < n else 0, True, True)
            if lost(sim):
                safe = False
                break
        score = (not safe, abs(sim.ship_c + 3 - goal), abs(m))
        if best is None or score < best[0]:
            best = (score, m)
    return best[1]


def play(level, limit=12000, log=None):
    """Play level (0..99) from a new game. -> (finished, steps, lives)."""
    game = M.Game(level)
    for k in range(limit):
        if game.game_over:
            return False, k, 0
        move = choose(game) if game.alive() and not game.phase else 0
        game.step(move, True, True)
        if game.station:                # (nothing turned)
            game.station_exit()
        if game.shop:                   # (nothing bought)
            game.shop_exit()
        if log is not None:
            log.append(move)
        if game.level != level:
            return True, k + 1, game.lives
    return False, limit, game.lives


def main():
    levels = [int(a) for a in sys.argv[1:]] or [1, 25, 100]
    for lv in levels:
        ok, steps, lives = play(lv - 1)
        print(f'level {lv}: {"finished" if ok else "FAILED"} in {steps} steps, {lives} lives left')


if __name__ == '__main__':
    main()
