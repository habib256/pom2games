"""Physical sectors of a DOS-order .dsk image (35 x 16 x 256).

A DOS-order file stores logical sectors; a boot PROM or a custom loader
reads physical ones. PHYS2LOG[p] = logical sector of physical sector p
(DOS 3.3 interleave).
"""
PHYS2LOG = [0, 7, 14, 6, 13, 5, 12, 4, 11, 3, 10, 2, 9, 1, 8, 15]
IMAGE_SIZE = 35 * 16 * 256


def offset(track, psec):
    return (track * 16 + PHYS2LOG[psec]) * 256


def phys_sector(image, track, psec):
    o = offset(track, psec)
    return image[o:o + 256]
