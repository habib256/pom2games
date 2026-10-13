#!/usr/bin/env python3
"""Draw the complete journey terrain as a native Apple II HGR topo sheet.

Contours interpolate the resident grid (400 ft intervals), north is up.
The image belongs to each disk's map, including alternate-map test disks.
No original copyrighted TOPO image is used.
"""

WIDTH, HEIGHT = 112, 84
GLYPHS = {'C': ('111', '100', '100', '100', '111'),
          'H': ('101', '101', '111', '101', '101'),
          'R': ('110', '101', '110', '101', '101'),
          'N': ('101', '111', '111', '111', '101')}


def render(data):
    if len(data) < 64 + WIDTH * HEIGHT:
        raise ValueError('incomplete journey map')
    page = bytearray(8192)
    grid = data[64:64 + WIDTH * HEIGHT]

    def pixel(x, y, color):
        # HGR artifact colors: green on odd pixels, magenta on even pixels.
        # White uses adjacent bits. Keep phase zero throughout the sheet.
        x, y = round(x), round(y)
        if not (0 <= x < 280 and 0 <= y < 160):
            return
        offset = (y % 8) * 1024 + (y // 8 % 8) * 128 + y // 64 * 40
        if color == 'white':
            for px in (x, min(x + 1, 279)):
                page[offset + px // 7] |= 1 << (px % 7)
        else:
            x = (x & ~1) + (color == 'green')
            page[offset + x // 7] |= 1 << (x % 7)

    def line(a, b, color):
        steps = max(1, round(max(abs(a[0]-b[0]), abs(a[1]-b[1])) * 2))
        for i in range(steps + 1):
            t = i / steps
            pixel(a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t, color)

    def point(x, y):
        return 28 + 2*x, 155 - y*150/(HEIGHT-1)

    # Piecewise linear contour crossings. Splitting each quad into triangles
    # resolves saddle cells consistently instead of joining ambiguous edges.
    for y in range(HEIGHT-1):
        for x in range(WIDTH-1):
            corners = [(point(xx, yy), grid[yy*WIDTH+xx] & 127)
                       for xx, yy in ((x,y), (x+1,y), (x+1,y+1), (x,y+1))]
            for tri in ((corners[0],corners[1],corners[2]),
                        (corners[0],corners[2],corners[3])):
                low, high = min(v for _,v in tri), max(v for _,v in tri)
                for level in range((low//4+1)*4, high+1, 4):
                    crossings = []
                    for (a,va),(b,vb) in zip(tri, tri[1:]+tri[:1]):
                        if min(va,vb) < level <= max(va,vb):
                            t = (level-va)/(vb-va)
                            crossings.append((a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t))
                    if len(crossings) == 2:
                        line(*crossings, 'green')

    # Sparse woodland hatching beneath water and site symbols.
    forest = data[64 + WIDTH*HEIGHT:64 + WIDTH*HEIGHT + 294] if data[26] else b''
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if forest:
                bit = (y//2)*56 + x//2
                if len(forest) > bit//8 and forest[bit//8] & (1 << (bit%8)) and (x+y)%4 == 0:
                    pixel(*point(x,y), 'green')
            if grid[y*WIDTH+x] & 128:
                a = point(x,y)
                line(a, (a[0]+1, a[1]+1), 'magenta')

    # Frame, true-north indicator and the original sheet's fixed sites.
    for a,b in (((26,3),(252,3)), ((252,3),(252,157)),
                ((252,157),(26,157)), ((26,157),(26,3))):
        line(a,b,'white')
    marks = [('C', data[3] + data[2]/256, data[5] + data[4]/256),
             ('R', data[8], data[9])]
    if data[16]:
        marks.append(('H', data[17], data[18]))
    for symbol, x, y in marks:
        sx, sy = point(x,y)
        pixel(sx,sy,'white')
        # Clamp labels inside the sheet, including sites near its borders.
        sx, sy = min(246, round(sx)+3), max(6, min(149, round(sy)-2))
        for row, bits in enumerate(GLYPHS[symbol]):
            for col, bit in enumerate(bits):
                if bit == '1':
                    pixel(sx+col*2, sy+row, 'white')
    for row,bits in enumerate(GLYPHS['N']):
        for col,bit in enumerate(bits):
            if bit == '1':
                pixel(12+col*2,6+row,'white')
    line((15,15),(15,32),'white')
    line((15,15),(11,21),'white')
    line((15,15),(19,21),'white')
    return bytes(page)
