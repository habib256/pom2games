"""Fixed-point helpers shared by the verlet model and lib/physics.

Every operation is the 6502 one: two's complement words, arithmetic shifts
that round down (Python >>), except asr0 (toward zero, lib/physics vl_heavy).

Units used by the library:
  8.8   one byte of pixel, one of fraction (y, velocities, deltas);
  16.8  24-bit x (world pixels on a long track);
  q     quarter pixels: q = delta >> 6, what the constraints square;
  l2q   a rest length squared in q units (l2q(24 px) = 96^2 = 9216).
"""


def s8(v):
    """Low byte as a signed value."""
    v &= 0xFF
    return v - 0x100 if v & 0x80 else v


def s16(v):
    """Low 16 bits as a signed value (the 6502 keeps 16 bits of a delta)."""
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def asr(v, n):
    """Arithmetic shift right, rounded down (LDA hi / CMP #$80 / ROR ROR)."""
    return v >> n


def asr0(v, n):
    """Arithmetic shift right rounded toward zero (add 2^n - 1 first if < 0)."""
    return (v + ((1 << n) - 1 if v < 0 else 0)) >> n


def damp(v, n):
    """v - (v >> n): the friction of vl_damp."""
    return v - (v >> n)


def fx88(px):
    """Pixels (float) -> 8.8."""
    return int(round(px * 256))


def fx168(px):
    """Pixels (float) -> 16.8 (the same scale, 24 bits)."""
    return int(round(px * 256))


def px(v):
    """8.8 or 16.8 -> pixels (float)."""
    return v / 256


def l2q(length):
    """Rest length (px) squared, in quarter pixels squared (q = delta >> 6)."""
    return int(round((length * 4) ** 2))


def k8(length, stiff):
    """The constraint gain: f = ((diff >> 3) * k8) >> 8 ~ diff * 256 / (2 l2q),
    half for each point, times the stiffness (1.0 = rigid in one pass)."""
    return int(round(2048 / (2 * l2q(length)) * 256 * stiff / 2))


def lo(v):
    return v & 0xFF


def hi(v):
    return (v >> 8) & 0xFF


def le(v, n):
    """Little-endian bytes of v (two's complement)."""
    return [(v >> (8 * i)) & 0xFF for i in range(n)]
