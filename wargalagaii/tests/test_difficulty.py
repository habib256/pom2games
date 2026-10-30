#!/usr/bin/env python3
"""Opening composition, completion and pressure across all 100 stages."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import model as M


def main():
    assert [M.level_kind(i) for i in range(8)] == [
        M.NORMAL, M.NORMAL, M.BIG, M.KAMIKAZE,
        M.NORMAL, M.NORMAL, M.BIG, M.BONUS]
    expected = [16, 23, 26, 40, 20, 25, 28, 40]     # (lot 10: shaped formations)
    for level in range(100):
        g = M.Game(level)
        for _ in range(1000):
            g.launch()           # isolate spawning: no kills, no movement
        count = sum(s != M.DEAD for s in g.a_state)
        rows, masks = M.level_form(level)[:2]
        want = 16 if g.lkind == M.BOSS else sum(bin(m).count('1') for m in masks[:rows])
        assert count == want, (level + 1, count, want)
        if level < 8:
            assert count == expected[level], (level + 1, count)
        for i, state in enumerate(g.a_state):
            if state:
                route = M.FLYPAST if g.lkind == M.BONUS else M.ENTRIES[M.paths.entry_index(level, i // M.COLS)]
                assert g.a_route[i] == route, (level + 1, i, 'wrong wave script')
        assert g.entry_w == M.ROWS and g.entry_k == 0
        # Sparse formations must be able to dive and finish normally.
        if g.lkind in (M.NORMAL, M.BIG):
            g.a_state = [M.FORM if s else M.DEAD for s in g.a_state]
            g.dive_t = 1
            g.dive()
            assert M.DIVE in g.a_state, level + 1
        g.a_state = [M.DEAD] * M.NALIENS
        g.boss_hp = g.boss_boom = 0
        g.level_step()
        assert g.phase, (level + 1, 'cannot finish')
        previous = M.level_params(level, 0)
        for loop in (1, 5, 20, 255):
            current = M.level_params(level, loop)
            assert 8 <= current[0] <= previous[0]
            assert previous[1] <= current[1] <= 7
            assert 5 <= current[2] <= previous[2]
            assert previous[3] <= current[3] <= 7
            assert previous[4] <= current[4] <= 7
            previous = current
        assert previous == (8, 7, 5, 7, 7), (level, previous)
    assert M.level_params(0, 0) == (60, 1, 60, 2, 3)
    assert M.level_params(1, 0) == (52, 1, 52, 2, 3)
    # The first squadron is mirrored on each new loop, without changing
    # its route or inventing a different PRNG draw.
    g = M.Game()
    h = M.Game()
    h.loop = 1
    for _ in range(M.ENTRY_FIRST):
        g.launch()
        h.launch()
    for i in (3, 4):
        assert g.a_mirror[i] != h.a_mirror[i]
        assert g.a_x[i] + h.a_x[i] == M.ALIEN_MAX
        assert g.a_route[i] == h.a_route[i]
    for level in range(4):
        g = M.Game(level)
        g.a_y[3], g.a_x[3] = 100, 60
        before = g.prng
        g.drop(3)
        assert g.prng == before and g.obj_kind[-1] == M.K['c50'] and g.obj_y[-1] == 100
        # A full pool must not erase another pickup to force the coin in.
        g.obj_y = [100] * M.N_OBJ
        g.obj_kind = [M.K['shield']] * M.N_OBJ
        g.drop(3)
        assert g.obj_kind == [M.K['shield']] * M.N_OBJ
    g = M.Game(4)
    g.prng = 0xFFFF
    g.a_y[3] = 100
    g.drop(3)
    assert not any(g.obj_y), 'guaranteed carriers only belong to the first pack'
    # Catch one gold coin, rather than granting cash automatically: this
    # is enough to enter the first shop and buy Extra Speed.
    g = M.Game(3)
    g.obj_kind[-1], g.obj_k[-1], g.obj_y[-1] = M.K['c50'], 9, M.SHIP_Y
    g.ship_c = 63
    g.pickups()
    assert g.credits == M.SHOP_MIN
    g.teleported()
    assert g.shop and g.can_buy(0)
    print('PASS difficulty: all 100 spawns/clears, scripted routes, mirrored loops, gold carriers and first purchase')


if __name__ == '__main__':
    main()
