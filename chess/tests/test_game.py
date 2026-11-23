#!/usr/bin/env python3
"""Play the rules the front end handles itself, in a2run: castling by the
player, the promotion prompt, the 50-move rule and dead material."""
from pathlib import Path
import argparse
import re
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

    # Black clears the queen side, then castles long.
    c = Cursor()
    steps = []
    for frm, to in (('e2', 'e4'), ('d7', 'd5'), ('e4', 'd5'), ('d8', 'd6'),
                    ('a2', 'a3'), ('b8', 'c6'), ('a3', 'a4'), ('c8', 'f5'),
                    ('b2', 'b3'), ('e8', 'c8')):
        steps += c.move(frm, to)
    b, s, result = run(steps + state)
    assert (b[sq('c8')], b[sq('d8')], b[sq('e8')], b[sq('a8')]) == (BK, 0x84, 0, 0), 'Black O-O-O'
    assert s == 0 and result == 0, 'White to move after Black castles'
    print('Black castles queen side: king c8, rook d8, White to move: ok')

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

    def endgame(pieces, white_material, black_material):
        steps = L.poke('board', bytes(128))
        for square, piece in [('e1', WK), ('e8', BK), *pieces]:
            steps.append(L.poke('board', piece, sq(square)))
        return steps + [L.poke('castling_rights', 0), *L.poke('mat_tot', [white_material, black_material])]

    # A promotion is a pawn move even when the destination is empty.
    position = endgame([('b7', WP), ('a8', 0x84)], 1, 5)
    steps = position + [L.poke('halfmove_clock', 99)] + Cursor().move('b7', 'b8', 'Q')
    r = a2test.run(args.disk, BOOT + steps + state + [L.peek('halfmove_clock')], emulator=args.a2run)
    assert r.mem(board, 128)[sq('b8')] == WQ and r.mem(side, 1)[0] == 0x80
    assert r.mem(half, 1)[0] == 0 and r.mem(L['game_result'], 1)[0] == 0
    print('Quiet promotion resets the fifty-move clock: ok')

    # Five king moves plus four promotions each for b8 and bxa8.
    steps = position + [f'call:{L["perft1"]:04X}:30', L.peek('perft_count_lo', 2)]
    r = a2test.run(args.disk, BOOT + steps, emulator=args.a2run)
    assert int.from_bytes(r.mem(L['perft_count_lo'], 2), 'little') == 13
    print('Perft counts quiet and capturing underpromotions: ok')

    # c1 and f8 are the same colour. Moving the black bishop to c8
    # instead, or replacing it with a knight, makes mate possible.
    for black_square, black_piece, expected in [('f8', 0x83, 4), ('c8', 0x83, 0), ('f8', 0x82, 0)]:
        steps = endgame([('c1', 3), (black_square, black_piece)], 3, 3)
        _, _, result = run(steps + ['key:J', 'wait:20'] + state)
        assert result == expected, (black_square, black_piece, result)
    print('Dead material distinguishes bishop square colours and mixed minors: ok')


def extras(args, L, board, side):
    """Board orientation, joystick input and the speaker."""
    page = 'peek:2000:8192'

    def block(data, top, col):
        # the 22 scanlines x 3 bytes of the square drawn at (top, col)
        return b''.join(data[a2test.hgr_offset(y) + col:a2test.hgr_offset(y) + col + 3]
                        for y in range(top, top + 22))

    # 1. Mode 3 (you play Black): the board is drawn the other way round.
    #    a1 (white rook, dark square) moves from the bottom-left corner to the
    #    top-right one, and the cursor starts on e7.
    normal = a2test.run(args.disk, BOOT + [page], emulator=args.a2run, timeout=120)
    flipped = a2test.run(args.disk, ['wait:1500', 'key:3', 'wait:900', page, L.peek('flipped'), L.peek('cur_sq')],
                         emulator=args.a2run, timeout=120)
    n, f = normal.dumps[0], flipped.dumps[0]
    assert flipped.mem(L['flipped'], 1)[0] == 1 and flipped.mem(L['cur_sq'], 1)[0] == 0x64
    assert block(f, 14, 23) == block(n, 168, 2), 'a1 drawn top-right when flipped'
    assert block(f, 14, 23) != block(n, 14, 23), 'and the corner differs from h8'
    print('You play Black: board turned round, a1 top right, cursor on e7: ok')

    # The e2 corner alternates while waiting for input. Sample two seconds
    # so the assertion is independent of the cursor phase at boot.
    corner = f'peek:{0x2000 + a2test.hgr_offset(146) + 14:04X}:1'
    samples = [step for _ in range(13) for step in (corner, 'wait:10')]
    r = a2test.run(args.disk, BOOT + samples, emulator=args.a2run)
    assert len(set(r.dumps)) == 2, 'idle cursor shows both phases'

    # Fool's mate leaves White to move. Compare the panel glyph at game
    # over with its boot appearance, when White also had the move.
    header = [f'peek:{0x2000 + a2test.hgr_offset(y) + 31:04X}:1' for y in range(8)]
    c = Cursor()
    moves = c.move('f2', 'f3') + c.move('e7', 'e5') + c.move('g2', 'g4') + c.move('d8', 'h4')
    r = a2test.run(args.disk, BOOT + header + moves + header + [L.peek('game_result')], emulator=args.a2run)
    assert r.dumps[-1] == bytes([1]) and r.dumps[:8] == r.dumps[8:16], 'white to move after mate'
    print('Idle cursor blinks and the final header shows the mated side: ok')

    # 2. Joystick: deflections move the cursor once each, button 0 selects
    #    and confirms, button 1 cancels a selection.
    steps = ['btn:0,1', 'wait:12', 'btn:0,0', 'wait:12',            # select e2
             'joy:0,-1', 'wait:12', 'joy:0,0', 'wait:12',           # e3
             'joy:0,-1', 'wait:12', 'joy:0,0', 'wait:12',           # e4
             'btn:0,1', 'wait:12', 'btn:0,0', 'wait:30',            # confirm e2-e4
             L.peek('board', 128), L.peek('side_to_move'), L.peek('cur_sq'),
             'btn:0,1', 'wait:12', 'btn:0,0', 'wait:12',            # Black: select e4? no, cursor on e4 (white pawn)
             'btn:1,1', 'wait:12', 'btn:1,0', 'wait:12',            # cancel
             L.peek('sel_active')]
    r = a2test.run(args.disk, BOOT + steps, emulator=args.a2run, timeout=120)
    b = r.mem(board, 128)
    assert b[sq('e4')] == WP and b[sq('e2')] == 0 and r.mem(side, 1)[0] == 0x80, 'e2-e4 by joystick'
    assert r.mem(L['cur_sq'], 1)[0] == sq('e4') and r.mem(L['sel_active'], 1)[0] == 0
    print('Joystick: stick moves the cursor, button 0 selects/confirms, button 1 cancels: ok')

    # 3. Speaker: a move clicks, S silences it.
    c = Cursor()
    steps = ['spk'] + c.move('e2', 'e4') + ['spk', 'key:S', 'wait:5'] + c.move('e7', 'e5') + ['spk']
    r = a2test.run(args.disk, BOOT + steps, emulator=args.a2run, timeout=120)
    assert r.spk[1] > 0 and r.spk[2] == 0, r.spk
    print('Speaker: move click, S toggles silence: ok')


    def play(steps):
        return a2test.run(args.disk, BOOT + steps, emulator=args.a2run, timeout=120)

    # U before the first move of a new game must leave the starting position intact.
    r = play([L.peek('board', 128)] + Cursor().move('e2', 'e4')
             + ['key:N', 'wait:120', 'key:1', 'wait:120', L.peek('undo_avail'),
                'key:U', 'wait:30', L.peek('board', 128), L.peek('hist_n')])
    assert r.mem(L['undo_avail'], 1)[0] == 0
    assert r.mem(board, 128, 1) == r.mem(board, 128) and r.mem(L['hist_n'], 1)[0] == 0
    print('New game discards the previous move before undo: ok')

    # M while a piece is selected, then enter BAI and move up on screen.
    r = play(['key: MM', 'wait:900', 'key:I', 'wait:30', L.peek('flipped'),
              L.peek('sel_active'), L.peek('cur_sq')])
    assert r.mem(L['flipped'], 1)[0] == 1 and r.mem(L['sel_active'], 1)[0] == 0
    assert r.mem(L['cur_sq'], 1)[0] == sq('e6'), 'M enters the same Black view as menu choice 3'

    # Undo after selecting the black pawn. The move-list row must be empty.
    c = Cursor()
    r = play(c.move('e2', 'e4') + ['key:III U', 'wait:60', page, L.peek('move_row'),
                                   L.peek('hist_n'), L.peek('sel_active')])
    assert r.mem(L['move_row'], 1)[0] == 2 and r.mem(L['hist_n'], 1)[0] == 0
    assert r.mem(L['sel_active'], 1)[0] == 0
    for y in range(16, 24):
        start = a2test.hgr_offset(y) + 31
        assert r.dumps[0][start:start+9] == n[start:start+9], 'undo clears the move from HGR'

    c = Cursor()
    r = play(c.move('e2', 'e4') + c.move('f7', 'f6') + ['spk']
             + c.move('d1', 'h5') + ['wait:120', 'spk'])
    assert r.spk[-1] == 8 + 2 * 24, 'Qh5+ sounds a move click and two check blips'

    r = play(Cursor().move('e2', 'e8') + [L.peek('sel_active')])
    assert r.mem(L['sel_active'], 1)[0] == 0, 'illegal last-rank move must not prompt'
    r = play([L.poke('board', WP, sq('b7')), L.poke('board', 0, sq('b8'))]
             + Cursor().move('b7', 'b8') + [L.peek('tx_col'), 'btn:1,1', 'wait:30',
                                            L.peek('sel_active'), L.peek('board', 128)])
    assert r.mem(L['tx_col'], 1)[0] == 40, 'promotion prompt stays inside its row'
    assert r.mem(L['sel_active'], 1)[0] == 0 and r.mem(board, 128)[sq('b7')] == WP

    # Compare stack depth at the same menu instruction after an ordinary N
    # and after a draw. An abandoned JSR used to cost two bytes per game.
    menu = ['press:N', L.until('a1_choose_mode'), 'pc', 'wait:60', 'key:1', 'wait:100']
    r = play(menu + [L.poke('halfmove_clock', 100), 'key:I', 'wait:100']
             + menu + [L.peek('game_result')])
    depths = re.findall(r'^PC=.* S=([0-9A-F]{2}) ', r.out, re.M)
    assert len(depths) == 2 and depths[0] == depths[1], depths
    assert r.mem(L['game_result'], 1)[0] == 0, 'new game clears the previous draw'

    r = a2test.run(args.disk, [L.poke('stick_key_btn', 255), 'btn:0,1'] + BOOT
                   + [L.peek('sel_active')], emulator=args.a2run, timeout=120)
    assert r.mem(L['sel_active'], 1)[0] == 1, 'first button press is independent of initial RAM'
    print('Mode changes, undo, check sound, promotion, restart and joystick startup: ok')


if __name__ == '__main__':
    main()
    _ap = argparse.ArgumentParser()
    _ap.add_argument('--a2run', type=Path, default=a2test.A2RUN)
    _ap.add_argument('--disk', type=Path, default=ROOT / 'dist/CHESS.dsk')
    _ap.add_argument('--labels', type=Path, default=ROOT / 'chess/build/chess.lbl')
    _a = _ap.parse_args()
    _L = a2test.labels(_a.labels)
    extras(_a, _L, _L['board'], _L['side_to_move'])
