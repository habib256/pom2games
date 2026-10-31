# lib/math — exact integer arithmetic for physics (asm)

*[← dev](../../README.md)*

Products, square root, division and a pseudo-random generator for the
6502, designed for fixed-point physics engines. All results
are **exact** and follow Python's "round down" semantics
(`x * y >> 6`): a Python model serves as a bit-exact oracle, as in
DIRTBIKE (`tools/physics.py` ↔ `src/physics.inc`).

Sources of the techniques: DIRTBIKE (products through zero-page pointers) and the
PHYSICS demo rebuilt in [`physics/`](../../../physics/README.md)
(tables read at a fixed offset for constants, shortcuts for ±1.0,
square root from a seed table, LFSR).

## Setup

```asm
.include "zp.inc"            ; if random.asm is used (prng_lo/prng_hi)
MUL_TABLES = $0800           ; 2 KB page-aligned, chosen by the program
MUL_ACC    = 1               ; optional: mul_acc0..2 accumulator (+3 B of ZP)
MUL_INIT_BOOT = 1            ; optional: mul_init in the "INIT" segment (startup
                             ; code that a buffer later overwrites)
.include "math.inc"          ; AT THE TOP: zero page and macros

        JSR mul_init          ; once at startup (~110,000 cycles)
        JSR sqrt_init         ; if isqrt16 is used (after mul_init)
        ...
; at the end of the source, after the callers (.ifref):
.include "sqrt.asm"          ; any order (only reads the tables)
.include "div.asm"
.include "random.asm"
.include "mul.asm"
```

`MUL_TABLES` is mandatory: an `.align 256` in BSS is only reliable if
the ld65 config aligns the segment. Usual choices: `$0800` (HELLO area of a
BRUN program that does not return to BASIC, like DIRTBIKE), 2 KB free in
LOWBSS, or the unused HGR page.

`apple2.mk` adds `-I $(MATH)` to `A2_INCS` and tracks these files in
`A2_ASM_DEPS`.

## Files and routines

| File | Routine | Effect | Cost |
|---|---|---|---|
| `math.inc` | zero page | `mul_x` (16), `mul_y` (8), `mul_p0..p2` (24), `mul_t`, 4 pointers; 13 B (+3 with `MUL_ACC`), each replaceable by an alias | — |
| | `MUL_K16 k` | `mul_p = mul_x × k`, k a constant 0..255, inline | ~60 c |
| | `MUL_KS16 k` | same with signed `mul_x` | ~70 c |
| `mul.asm` | `mul_init` | builds the square tables (nothing on disk) | ~110,000 c |
| | `mul_u8u8` | `mul_p0..1 = mul_x(low) × mul_y` | ~45 c |
| | `mul_u16u8` | `mul_p = mul_x × mul_y`, unsigned | ~85 c |
| | `mul_s16s8` | same, signed, exact 24 bits (product inline without `mul_u16u8`) | ~115 c |
| | `mul_dir` | `mul_p = A/X × Y` signed; Y = 0, +64, −64 (direction ±1.0 at scale 64) take a shortcut | 15-50 c / ~150 c |
| | `mul_shr6` | `mul_p1..2 = ⌊mul_p / 64⌋` | 30 c |
| | `mul_acc_set` / `_add` / `_shr6` | sum of products over 24 bits, then ⌊/64⌋ | |
| `sqrt.asm` | `sqrt_init`, `isqrt16` | `A = ⌊√mul_x⌋`; start from `sqrt_seed[mul_x+1]`, then steps of 1 with n² = sqr1[2n] | ~40 c + ~25 c/step |
| `div.asm` | `div16by8` | `mul_x = mul_x / A`, `A = remainder`; 8 steps if the quotient fits in one byte | ~190 c / ~400 c |
| `dec.asm` | `byte_to_dec` | `A` (0..255) → `X` hundreds, `Y` tens, `A` units (0..9); no memory | 30-110 c |
| | `byte_div10` | `Y = A / 10` (0..25), `A = A mod 10`, X kept | 15-110 c |
| | `u16_to_dec` | `dec_lo/hi` → ASCII at `(dec_ptr)`, no leading zeros, NUL; `Y` = digit count. Zero page `dec_lo`, `dec_hi`, `dec_ptr`, `dec_t`, `dec_d` allocated unless defined beforehand (hgrc: `hgr_utoa`, `gfx_utoa`) | 250-900 c |
| `bcd.asm` | `bcd_add_sat` | `(bcd_ptr) += A/Y`, X bytes of packed BCD (low byte first); overflow → 99..99 and C = 1; D set during the add (IRQ handlers: CLD). 32 B; `bcd_ptr` (2 B ZP) unless defined beforehand | ~15 c/byte |
| | `bcd_put` | the X-byte BCD at A/Y as 2X ASCII digits, top first, each sent to the program's `BCD_PUT_OUT` (keeps X: `hgr_putc8`, `COUT`); `BCD_PUT_LEAD = c`: leading zeros → c, or left out with 0 (units always shown, +27 B). 33 B. From DIRTBIKE (tricks.inc, hof.inc), which is its natural user | |
| `random.asm` | `rand8` | 16-bit Galois LFSR (taps `$B400`) on `prng_lo/hi`; non-zero seed | ~20 c |

### The tricks

* **Quarter squares**: a·b = ⌊(a+b)²/4⌋ − ⌊(a−b)²/4⌋. The low bytes of the
  sqr1 pointers hold `mul_y`, those of sqr2 `mul_y EOR $FF` (a−b+255),
  and the bytes of `mul_x` serve as indices as they are (`(mul_s1l),Y`,
  `(mul_s2l),Y`). No
  self-modifying code (unlike PHYSICS's `mul8x8`, which patches 8
  operands for a 16×8 product).
* **Signed**: product of the unsigned patterns, then two two's-complement
  corrections (y < 0: −x·256; x < 0: −y·65536).
* **Constant** (`MUL_K16`): `sqr1+k,X` and `sqr2+255−k,X` (the second table
  is symmetric around 255), so nothing to prepare, two reads per
  byte. Handy for fixed coefficients (bounce, friction, damping).
* **×64 directions** (`mul_dir`): a flat ground normal is (0, −64);
  ×0 and ×±64 become a clear or two shifts, with exactly the
  same result. In DIRTBIKE, about −16 % on the physics of
  track 1.
* **Square root**: the `sqrt_seed[h] = ⌊√(h·256)⌋` table (256 B, built at
  startup) never overshoots; one or two steps are enough beyond 256.
* **Division**: the PHYSICS demo used a 512 B table of reciprocals
  plus a correction multiply. For a one-byte quotient, eight
  subtraction steps cost as much, with no table.

## Tests

`dev/tests/test_math.py` (in `make test-hgr`) assembles each routine,
runs it in a2run on about 1,900 cases (edges, sign patterns, fixed
random) and compares against the Python computation. It is built twice: tables at
`$0800`, then tables and `sqrt_seed` in HGR page 2.

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../../../LICENSE).
