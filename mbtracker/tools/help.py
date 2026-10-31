#!/usr/bin/env python3
"""MBT.HELP: the help pages of MB TRACKER (loaded at boot into aux $9800,
shown by src/main.c): pages 0 and 2 the help screens (rows 2..), page 1
the instrument editor's key list (column 42, rows 6..). A header of 4
words: the offset of each page, then the end; lines NUL-terminated. A page
is fetched alone into the grid buffer (2304 bytes)."""
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
    "O A U D F S N E  EFFECT: OFF ARPEGGIO      ^W      SONG TO 3 <-> 6 VOICES",
    "  SLIDE UP/DOWN FADE SWELL NOISE ENVELOPE  ^L ^S   LOAD / SAVE AN .AYS FILE",
    "^O ^Y       INSERT / DELETE A ROW          ^Q      QUIT TO PRODOS",
    "TAB         ORDER LIST                     ^N      NEW SONG: 3 OR 6 VOICES",
    "",
    "ORDER LIST (TAB)",
    "UP DOWN     ENTRY (THE GRID SHOWS ITS PATTERN)",
    "- = LEFT RIGHT  PATTERN NUMBER (PAST THE LAST ONE: A NEW PATTERN)",
    "N C         THIS ENTRY: NEW EMPTY PATTERN / COPY OF ITS PATTERN (CLONE)",
    "I           INSERT A NEW EMPTY PATTERN AFTER THIS ENTRY",
    "D           DELETE THIS PATTERN (ITS ENTRIES GO, THE NEXT ONES RENUMBERED)",
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
    "MOUSE      CLICK A FIELD, THE BAR",
], [
    "BLOCKS (PATTERN)",
    "^B          MARK: THE BLOCK GOES FROM HERE TO THE CURSOR (AGAIN, ESC: OFF)",
    "^C ^X       COPY / CUT THE BLOCK (NO BLOCK: THE CURSOR'S CELL)",
    "^V          PASTE AT THE BLOCK'S CORNER / THE CURSOR (ANY PATTERN)",
    "; '         TRANSPOSE THE BLOCK A SEMITONE DOWN / UP",
    ": \"         TRANSPOSE THE BLOCK AN OCTAVE DOWN / UP",
    "^Z          UNDO THE LAST CELL EDIT OR BLOCK CHANGE (AGAIN: REDO)",
    "",
    "MOUSE (APPLEMOUSE CARD ON THE //E, THE //C'S OWN)",
    "CLICK A CELL       THE CURSOR THERE (NOTE, INSTRUMENT, EFFECT, PARAMETER)",
    "DRAG               A BLOCK FROM THE CELL PRESSED",
    "ROW NUMBERS        THAT ROW; THE FIRST / LAST ONE SHOWN: 16 ROWS UP / DOWN",
    "ORDER LIST         THAT ENTRY (THE LIST GETS THE KEYS)",
    "INSTRUMENT         THE ONE FOR NEW NOTES; CLICKED AGAIN: ITS EDITOR",
    "VOICE N            MUTE / UNMUTE",
    "BOTTOM BAR         PLAY LOOP STOP, PAT / ORD (KEYS TO THE GRID / THE LIST),",
    "                   INS (EDITOR), LOAD, SAVE, HELP",
    "",
    "6 VOICES: BOTH CHIPS OF THE MOCKINGBOARD (VOICES 4-6 ON THE SECOND ONE)",
    "A CELL THEN READS C-41A47: NOTE, INSTRUMENT, EFFECT, PARAMETER",
]]
LIMIT = 0x0C00          # src/mbt.h HELP_MAX: aux $9800-$A3FF
PAGE = 2304             # the grid and the scratch pattern


def build():
    body = bytearray()
    offs = []
    for page in PAGES:
        offs.append(8 + len(body))
        for line in page:
            assert len(line) <= 80 and line.isascii()
            body += line.encode() + b'\0'
        assert 8 + len(body) - offs[-1] <= PAGE
    offs.append(8 + len(body))
    out = b''.join(o.to_bytes(2, 'little') for o in offs) + body
    assert len(out) <= LIMIT, len(out)
    return out


if __name__ == '__main__':
    Path(sys.argv[1]).write_bytes(build())
