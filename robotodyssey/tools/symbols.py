"""symbols.py: names of the Robot Odyssey (Apple II) in-memory tables.

World ($6000-$94FF, $3500 bytes, same layout as the PC version's world
file) and other tables established in docs/logic/world.md and
docs/logic/simulation.md.  name_of(addr) -> 'table+off' or ''.
"""

# (start, length, name)
TABLES = [
    (0x6000, 0x100, 'OBJ_NEXT'),      # next object in the same room ($FF end)
    (0x6100, 0x100, 'OBJ_SPRITE'),
    (0x6200, 0x100, 'OBJ_COLOR'),
    (0x6300, 0x100, 'OBJ_ROOM'),      # $3F = nowhere
    (0x6400, 0x100, 'OBJ_X'),
    (0x6500, 0x100, 'OBJ_Y'),
    (0x6600, 0x100, 'OBJ_MOVEDBY'),   # object this one is attached to ($FF none)
    (0x6700, 0x100, 'OBJ_DX'),        # offset from it
    (0x6800, 0x100, 'OBJ_DY'),
    (0x6900, 0x100, 'OBJ_GRAB'),      # 00 can be grabbed, FF cannot
    (0x6A00, 0x400, 'SPRITES'),       # 64 x 16 bytes
    (0x6E00, 0x40, 'ROOM_HEAD'),      # first object of the room
    (0x6E40, 0x40, 'ROOM_BG'),
    (0x6E80, 0x40, 'ROOM_FG'),
    (0x6EC0, 0x40, 'ROOM_UP'),
    (0x6F00, 0x40, 'ROOM_DOWN'),
    (0x6F40, 0x40, 'ROOM_RIGHT'),
    (0x6F80, 0x40, 'ROOM_LEFT'),
    (0x6FC0, 0x40, 'ROOM_RSVD'),
    (0x7000, 0x780, 'ROOM_TILES'),    # 64 x 30 bytes
    (0x7780, 0x100, 'WORLD_UNK'),
    (0x7880, 0x80, 'TXT_ROOM'),
    (0x7900, 0x80, 'TXT_X'),
    (0x7980, 0x80, 'TXT_Y'),
    (0x7A00, 0x80, 'TXT_STYLE'),
    (0x7A80, 0x80, 'TXT_FONT'),
    (0x7B00, 0x80, 'TXT_COLOR'),
    (0x7B80, 0x80, 'TXT_PTRLO'),
    (0x7C00, 0x80, 'TXT_PTRHI'),
    (0x7C80, 0x580, 'TXT_HEAP'),
]


def name_of(a):
    for s, n, name in TABLES:
        if s <= a < s + n:
            return name if a == s else '%s+$%X' % (name, a - s)
    return ''
