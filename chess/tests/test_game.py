#!/usr/bin/env python3
"""Play the rules the front end handles itself, in a2run: castling by the
player, the promotion prompt, the 50-move rule and dead material."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test

BOOT = ['wait:1500', 'key:1', 'wait:120']          # mode 1 = human vs human
WK, WR, WN, WQ, WP, BK = 6, 4, 2, 5, 1, 0x86


def sq(name):
    return (ord(name[1]) - ord('1')) * 16 + ord(name[0]) - ord('a')


class Cursor:
    """Key presses that walk the on-screen cursor (I/K/J/L) and confirm."""
    def __init__(self):
        self.at = sq('e2')

    def goto(self, target):
        keys = ''
        dr = (target >> 4) - (self.at >> 4)
        df = (target & 7) - (self.at & 7)
        keys += ('I' * dr) if dr > 0 else ('K' * -dr)
        keys += ('L' * df) if df > 0 else ('J' * -df)
        self.at = target
        return keys

    def move(self, frm, to, extra=''):
        return ['key:' + self.goto(sq(frm)) + ' ' + self.goto(sq(to)) + ' ' + extra, 'wait:30']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--a2run', type=Path, default=a2test.A2RUN)
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/CHESS.dsk')
    ap.add_argument('--labels', type=Path, default=ROOT / 'chess/build/chess.lbl')
    args = ap.parse_args()
    L = a2test.labels(args.labels)
    board, side, half = L['board'], L['side_to_move'], L['halfmove_clock']
    state = [L.peek('board', 128), L.peek('side_to_move'), L.peek('game_result'), L.peek('cur_sq')]

    def run(steps):
        r = a2test.run(args.disk, BOOT + steps, emulator=args.a2run, timeout=120)
        return r.mem(board, 128), r.mem(side, 1)[0], r.mem(L['game_result'], 1)[0]

    # 1. Italian opening, then the player castles king side.
    c = Cursor()
    steps = []
    for frm, to in (('e2', 'e4'), ('e7', 'e5'), ('g1', 'f3'), ('b8', 'c6'),
                    ('f1', 'c4'), ('g8', 'f6')):
        steps += c.move(frm, to)
    steps += c.move('e1', 'g1')
    b, s, result = run(steps + state)
    assert (b[sq('g1')], b[sq('f1')], b[sq('e1')], b[sq('h1')]) == (WK, WR, 0, 0), 'king and rook after O-O'
    assert s == 0x80 and result == 0, 'Black to move, game on'
    print('Player castles king side: king g1, rook f1, Black to move: ok')

    # 1b. A castle that is not available (rook moved away) is refused.
    c = Cursor()
    steps = []
    for frm, to in (('e2', 'e4'), ('e7', 'e5'), ('g1', 'f3'), ('b8', 'c6'),
                    ('f1', 'c4'), ('g8', 'f6'), ('h1', 'g1'), ('d7', 'd6'), ('g1', 'h1'), ('d6', 'd5')):
        steps += c.move(frm, to)
    steps += c.move('e1', 'g1')
    b, s, _ = run(steps + state)
    assert (b[sq('e1')], b[sq('h1')], b[sq('g1')]) == (WK, WR, 0) and s == 0, 'lost right: move refused'
    print('Castling refused once the rook has moved: ok')

    # 2. Promotion prompt: a white pawn poked onto b7, promoted to a rook,
    #    then to a knight; ESC cancels without moving.
    for key, piece in (('R', WR), ('N', WN), ('Q', WQ)):
        c = Cursor()
        steps = [f'poke:{board + sq("b7"):04X}:01', f'poke:{board + sq("b8"):04X}:00']
        steps += c.move('b7', 'b8', key)
        b, s, _ = run(steps + state)
        assert b[sq('b8')] == piece and b[sq('b7')] == 0 and s == 0x80, (key, b[sq('b8')])
    c = Cursor()
    steps = [f'poke:{board + sq("b7"):04X}:01', f'poke:{board + sq("b8"):04X}:00']
    steps += c.move('b7', 'b8', '\x1b')
    b, s, _ = run(steps + state)
    assert b[sq('b7')] == WP and b[sq('b8')] == 0 and s == 0, 'ESC keeps the pawn'
    print('Promotion prompt: queen, rook, knight chosen; ESC cancels: ok')

    # 3. Fifty-move rule: 99 quiet half-moves already counted, one more draws.
    c = Cursor()
    steps = [f'poke:{half:04X}:63'] + c.move('g1', 'f3')
    b, s, result = run(steps + state)
    assert result == 4, ('expected DRAW', result)
    print('Fifty-move rule: DRAW after the 100th quiet half-move: ok')

    # 4. Dead material: kings only. The draw is declared as soon as the turn
    #    starts, so the king move that follows is never played.
    c = Cursor()
    steps = [f'poke:{board + i:04X}:00' for i in range(0x78) if i & 0x88 == 0]
    steps += [f'poke:{board + sq("e1"):04X}:{WK:02X}', f'poke:{board + sq("e8"):04X}:{BK:02X}',
              f'poke:{L["castling_rights"]:04X}:00',
              f'poke:{L["mat_tot"]:04X}:00', f'poke:{L["mat_tot"] + 1:04X}:00']
    steps += c.move('e1', 'd1')
    b, s, result = run(steps + state)
    assert b[sq('e1')] == WK and b[sq('d1')] == 0 and result == 4, ('kings only', result)
    print('Dead material (K vs K): DRAW declared at once: ok')


if __name__ == '__main__':
    main()
