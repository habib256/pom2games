#!/usr/bin/env python3
"""MBT.HELP: the help pages of MB TRACKER (loaded at boot into aux $9800,
shown by src/main.c): page 0 the help screen (rows 2..), page 1 the
instrument editor's key list (column 42, rows 6..). Lines NUL-terminated,
a page ends with an empty line made of a single $0C byte."""
import sys
from pathlib import Path

PAGES = [[
    "PATTERN                                    SONG",
    "ARROWS      MOVE (NOTE INS FX PARAM)       ^P      PLAY THE SONG FROM THIS ORDER",
    "[ ]         16 ROWS UP / DOWN              ^R      LOOP THIS PATTERN",
    "Z S X D C V G B H N J M ,  PIANO, OCTAVE   SPACE   STOP (ALSO ESC)",
    "Q 2 W 3 E R 5 T 6 Y 7 U I  PIANO, OCT+1    ^F      FOLLOW THE PLAY ON/OFF",
    "1           NOTE OFF                       ! @ #   MUTE VOICE 1 2 3 ($ % ^: 4-6)",
    "DELETE .    CLEAR THE FIELD                _ +     SPEED (TICKS A ROW)",
    "- =         OCTAVE DOWN / UP               { }     ROWS OF THE PATTERNS",
    "< >         INSTRUMENT FOR NEW NOTES       ^T ^A   SONG NAME / AUTHOR",
    "0-F         INSTRUMENT, PARAMETER          ^E      INSTRUMENT EDITOR",
    "O A U D F S N E  EFFECT: OFF ARPEGGIO      ^N      NEW SONG",
    "  SLIDE UP/DOWN FADE SWELL NOISE ENVELOPE  ^L ^S   LOAD / SAVE AN .AYS FILE",
    "^O ^Y       INSERT / DELETE A ROW          ^Q      QUIT TO PRODOS",
    "TAB         ORDER LIST",
    "",
    "ORDER LIST (TAB)",
    "UP DOWN     ENTRY (THE GRID SHOWS ITS PATTERN)",
    "- = LEFT RIGHT  PATTERN NUMBER (PAST THE LAST ONE: A NEW PATTERN)",
    "N C         NEW EMPTY PATTERN / COPY OF THIS ONE",
    "^O ^Y       INSERT (SAME PATTERN) / DELETE THE ENTRY",
    "L           LOOP TO THIS ENTRY AFTER THE END (AGAIN: STOP AT THE END)",
], [
    "KEYS",
    "ARROWS     MOVE",
    "0-F        VOLUME / NOISE PERIOD /",
    "           SHAPE / ENV PERIOD",
    "SPACE      TONE, NOISE, ENV ON/OFF",
    "DELETE     NO NOISE PERIOD / SHAPE",
    "L          LOOP FROM THIS TICK",
    "^O / ^Y    DUPLICATE / DELETE TICK",
    "< >        PREVIOUS / NEXT INSTRUMENT",
    "RETURN     LISTEN (C OF THE OCTAVE)",
    "- =        OCTAVE DOWN / UP",
    "^T         NAME",
    "ESC        BACK TO THE PATTERN",
]]
LIMIT = 2304            # src/song.c: the grid and the scratch pattern


def build():
    out = bytearray()
    for page in PAGES:
        for line in page:
            assert len(line) <= 80 and line.isascii()
            out += line.encode() + b'\0'
        out += b'\x0c\0'
    assert len(out) <= LIMIT, len(out)
    return bytes(out)


if __name__ == '__main__':
    Path(sys.argv[1]).write_bytes(build())
