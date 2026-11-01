#!/usr/bin/env python3
"""applesoft.py: list a tokenized Applesoft program (loaded at $0801)."""
import sys

TOKENS = ('END FOR NEXT DATA INPUT DEL DIM READ GR TEXT PR# IN# CALL PLOT HLIN VLIN '
          'HGR2 HGR HCOLOR= HPLOT DRAW XDRAW HTAB HOME ROT= SCALE= SHLOAD TRACE NOTRACE '
          'NORMAL INVERSE FLASH COLOR= POP VTAB HIMEM: LOMEM: ONERR RESUME RECALL STORE '
          'SPEED= LET GOTO RUN IF RESTORE & GOSUB RETURN REM STOP ON WAIT LOAD SAVE DEF '
          'POKE PRINT CONT LIST CLEAR GET NEW TAB( TO FN SPC( THEN AT NOT STEP + - * / ^ '
          'AND OR > = < SGN INT ABS USR FRE SCRN( PDL POS SQR RND LOG EXP COS SIN TAN ATN '
          'PEEK LEN STR$ VAL ASC CHR$ LEFT$ RIGHT$ MID$').split()


def line_text(body):
    """Detokenize one line: keywords get a space on each side; text inside
    quotes, after REM and in DATA (up to a ':' outside quotes) stays as is."""
    out, quote, literal = '', False, None
    for c in body:
        if quote or literal == 'REM' or (literal == 'DATA' and c != ord(':')):
            ch = chr(c & 0x7F)
            out += ch
            if ch == '"' and literal != 'REM':
                quote = not quote
            continue
        literal = None if literal == 'DATA' else literal
        if 0x80 <= c < 0x80 + len(TOKENS):
            word = TOKENS[c - 0x80]
            out = out.rstrip(' ') + (' ' if out else '') + word + ' '
            if word in ('REM', 'DATA'):
                literal = word
            continue
        ch = chr(c & 0x7F)
        if ch == '"':
            quote = True
        out += ch
    return out.rstrip(' ') if not quote else out


def listing(b, base=0x801):
    """Lines of the program in b (a $0800 image starting with its 0 byte, or
    the program itself)."""
    skip = base - 0x800 if b[:1] == b'\0' else 0
    p = skip
    while p + 4 <= len(b):
        nxt = b[p] | b[p + 1] << 8
        if nxt == 0:
            break
        ln = b[p + 2] | b[p + 3] << 8
        end = b.index(0, p + 4)
        yield f'{ln} ' + line_text(b[p + 4:end])
        p = nxt - base + skip


if __name__ == '__main__':
    for line in listing(open(sys.argv[1], 'rb').read()):
        print(line)
