#!/usr/bin/env python3
"""tms9918.py — render a TMS9918A picture from its 16 KB VRAM and registers.

The E-Z Color card (dev/lib/apple2/ezcolor.asm) has its own monitor, so a2run
dumps the VRAM (vpeek:0:16384) and the registers (vregs) and this module
draws what that monitor shows:

    import tms9918
    rows = tms9918.render(vram, regs)            # 192 rows of 256 (r, g, b)
    tms9918.png(path, vram, regs, scale=2)       # through apple2img.png_write

Modes: Graphics I, Graphics II, Multicolour, Text (40 columns of 6 px, 8 px
side borders); blanked display (R1 bit 6 = 0) shows the backdrop. Sprites
(not in Text mode): 8x8 / 16x16, magnified, early clock, the Y = $D0
terminator, colour 0 transparent, lower number in front, at most four a line
(the fifth and later are not drawn, as on the chip). Colour 0 shows the
backdrop (R7 low nibble). border=True adds the 16/12 px border all round
(288 x 216, the size POM2's card monitor paints)."""
from pathlib import Path

# The usual TMS9918A palette (as in MAME / openMSX approximations).
PALETTE = [
    (0, 0, 0), (0, 0, 0), (33, 200, 66), (94, 220, 120),
    (84, 85, 237), (125, 118, 252), (212, 82, 77), (66, 235, 245),
    (252, 85, 84), (255, 121, 120), (212, 193, 84), (230, 206, 128),
    (33, 176, 59), (201, 91, 186), (204, 204, 204), (255, 255, 255),
]

W, H = 256, 192


def mode(regs):
    """'text', 'multicolor', 'graphics2' or 'graphics1' from R0/R1."""
    if regs[1] & 0x10:
        return 'text'
    if regs[1] & 0x08:
        return 'multicolor'
    if regs[0] & 0x02:
        return 'graphics2'
    return 'graphics1'


def tables(regs):
    """VRAM bases of the name, colour, pattern, sprite attribute and sprite
    pattern tables (Graphics II colour/pattern: the high bit only)."""
    m = mode(regs)
    name = (regs[2] & 0x0F) * 0x400
    if m == 'graphics2':
        colour = (regs[3] & 0x80) << 6
        pattern = (regs[4] & 0x04) << 11
    else:
        colour = regs[3] * 0x40
        pattern = (regs[4] & 0x07) * 0x800
    return dict(name=name, colour=colour, pattern=pattern,
                sat=(regs[5] & 0x7F) * 0x80, spt=(regs[6] & 0x07) * 0x800)


def render(vram, regs, border=False):
    """Rows of (r, g, b): 192 x 256 (216 x 288 with border)."""
    vram = bytes(vram)
    assert len(vram) >= 0x4000, 'need the whole 16 KB VRAM'
    back = regs[7] & 0x0F
    idx = [[back] * W for _ in range(H)]
    m = mode(regs)
    t = tables(regs)
    if regs[1] & 0x40:
        if m == 'text':
            fg, bg = regs[7] >> 4, regs[7] & 0x0F
            for y in range(H):
                row = idx[y]
                for col in range(40):
                    ch = vram[t['name'] + (y // 8) * 40 + col]
                    bits = vram[t['pattern'] + ch * 8 + (y & 7)]
                    for b in range(6):
                        c = fg if bits & (0x80 >> b) else bg
                        row[8 + col * 6 + b] = c or back
        else:
            for y in range(H):
                row = idx[y]
                for col in range(32):
                    ch = vram[t['name'] + (y // 8) * 32 + col]
                    if m == 'multicolor':
                        byte = vram[t['pattern'] + ch * 8 + ((y // 8) & 3) * 2 + ((y & 7) >> 2)]
                        for b in range(8):
                            c = byte >> 4 if b < 4 else byte & 0x0F
                            row[col * 8 + b] = c or back
                        continue
                    if m == 'graphics2':
                        index = (((y // 64) << 8) | ch) * 8 + (y & 7)
                        bits = vram[t['pattern'] | (index & (((regs[4] & 3) << 11) | 0x7FF))]
                        cbyte = vram[t['colour'] | (index & (((regs[3] & 0x7F) << 6) | 0x3F))]
                    else:
                        bits = vram[t['pattern'] + ch * 8 + (y & 7)]
                        cbyte = vram[t['colour'] + (ch >> 3)]
                    fg, bg = cbyte >> 4, cbyte & 0x0F
                    for b in range(8):
                        c = fg if bits & (0x80 >> b) else bg
                        row[col * 8 + b] = c or back
            _sprites(vram, regs, t, idx)
    rows = [[PALETTE[c] for c in row] for row in idx]
    if border:
        edge = PALETTE[back]
        side = [edge] * 16
        rows = [[edge] * 288 for _ in range(12)] + [side + r + side for r in rows] + \
            [[edge] * 288 for _ in range(12)]
    return rows


def _sprites(vram, regs, t, idx):
    size = 16 if regs[1] & 0x02 else 8
    mag = 2 if regs[1] & 0x01 else 1
    span = size * mag
    drawn = [[False] * W for _ in range(H)]
    per_line = [0] * H
    for n in range(32):
        a = t['sat'] + n * 4
        y0 = vram[a]
        if y0 == 0xD0:
            break
        y = y0 + 1 if y0 < 0xE0 else y0 - 255          # $E0..$FF: partly above
        x = vram[a + 1]
        pat = vram[a + 2] & (0xFC if size == 16 else 0xFF)
        colour = vram[a + 3]
        if colour & 0x80:
            x -= 32                                     # early clock
        c = colour & 0x0F
        for dy in range(span):
            sy = y + dy
            if not 0 <= sy < H:
                continue
            per_line[sy] += 1
            if per_line[sy] > 4 or not c:
                continue
            py = dy // mag
            base = t['spt'] + pat * 8
            for dx in range(span):
                sx = x + dx
                if not 0 <= sx < W or drawn[sy][sx]:
                    continue
                px = dx // mag
                byte = vram[base + (16 if px >= 8 else 0) + py] if size == 16 else vram[base + py]
                if byte & (0x80 >> (px & 7)):
                    idx[sy][sx] = c
                    drawn[sy][sx] = True


def png(path, vram, regs, scale=2, border=False):
    """Write the picture as a PNG (apple2img.png_write)."""
    import apple2img
    apple2img.png_write(Path(path), render(vram, regs, border), scale=scale)


if __name__ == '__main__':
    import sys
    sys.exit('import tms9918: render(vram, regs) / png(path, vram, regs)')
