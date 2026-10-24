"""Shared start of the //e tests: boot past the title (lot 9).

front_skip (poked at _main) sends the boot straight into a game with SEED,
as before the title existed; the title has its own tests (test_front.py)."""


def boot(L):
    return [L.until('main', 3000), L.poke('front_skip', 1), L.until('game_tick', 3000)]
