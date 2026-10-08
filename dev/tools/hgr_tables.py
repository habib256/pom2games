"""Native Apple II HGR layout and lookup tables, independent of test tools."""


def hgr_offset(y):
    """Byte offset of visible scanline y (0..191) in an 8192-byte page."""
    if not 0 <= y < 192:
        raise ValueError('HGR scanline must be in 0..191')
    return (y % 8) * 1024 + (y // 8 % 8) * 128 + (y // 64) * 40


def scanline_tables(page=0x2000):
    """Low/high address tables (192 bytes each) for HGR page 1 or 2."""
    if page not in (0x2000, 0x4000):
        raise ValueError('HGR page must be $2000 or $4000')
    addresses = [page + hgr_offset(y) for y in range(192)]
    return bytes(a & 255 for a in addresses), bytes(a >> 8 for a in addresses)


def division_tables(width=256):
    """Byte-column and sub-byte phase tables for 1..280 native HGR pixels."""
    if not 1 <= width <= 280:
        raise ValueError('HGR width must be in 1..280')
    return bytes(x // 7 for x in range(width)), bytes(x % 7 for x in range(width))


def shift_tables():
    """Six 256-byte low/carry tables for runtime bitmap shifts 1..6.

    PCS convention: retain the palette bit in both output bytes, but replace
    an isolated $80 with zero to avoid colouring empty output. These are
    runtime lookup tables, not seven pre-shifted copies of each sprite.
    """
    low, high = bytearray(), bytearray()
    for shift in range(1, 7):
        for value in range(256):
            sign = value & 0x80
            bits = (value & 0x7f) << shift
            a, b = (bits & 0x7f) | sign, (bits >> 7) | sign
            low.append(a if a != 0x80 else 0)
            high.append(b if b != 0x80 else 0)
    return bytes(low), bytes(high)
