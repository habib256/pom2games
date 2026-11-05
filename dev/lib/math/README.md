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

        JSR mul_init          ; once at startup (~38,000 cycles)
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
| | `MUL_K16 k` | `mul_p = mul_x × k`, k a constant 0..255, inline | general ~60–70 c / 44 B; powers 11–59 c / 8–34 B |
| | `MUL_KS16 k` | same with signed `mul_x` | general ~70–80 c / 55 B; powers 8–45 B |
| `mul.asm` | `mul_init` | builds the square tables (nothing on disk) | ~38,000 c |
| | `mul_u8u8` | `mul_p0..1 = mul_x(low) × mul_y` | ~45 c |
| | `mul_u16u8` | `mul_p = mul_x × mul_y`, unsigned | ~85 c |
| | `mul_s16s8` | same, signed, exact 24 bits (product inline without `mul_u16u8`) | ~115 c |
| | `mul_dir` | `mul_p = A/X × Y` signed; Y = 0, +64, −64 (direction ±1.0 at scale 64) take a shortcut | 15-50 c / ~150 c |
| | `mul_shr6` | `mul_p1..2 = ⌊mul_p / 64⌋` | 30 c |
| | `mul_acc_set` / `_add` / `_shr6` | sum of products over 24 bits, then ⌊/64⌋ | |
| `sqrt.asm` | `sqrt_init`, `isqrt16` | `A = ⌊√mul_x⌋`; start from `sqrt_seed[mul_x+1]`, then steps of 1 with n² = sqr1[2n] | ~40 c + ~25 c/step |
| `div.asm` | `div16by8` | `mul_x = mul_x / A`, `A = remainder`; 8 steps if the quotient fits in one byte | 0/1: 189 c; 65535/255: 349 c, including JSR/RTS |
| `dec.asm` | `byte_to_dec` | `A` (0..255) → `X` hundreds, `Y` tens, `A` units (0..9); no memory | 30-110 c |
| | `byte_div10` | `Y = A / 10` (0..25), `A = A mod 10`, X kept | 18-193 c (excluding JSR and branch page crossings) |
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
  byte. Computing the high-byte product first lets the second high half
  feed the final addition directly: no temporary store/reload and no
  redundant carry setup. This saves 5 bytes and 8 cycles per expansion
  (signed or unsigned). Handy for fixed coefficients (bounce, friction, damping).
* **×64 directions** (`mul_dir`): a flat ground normal is (0, −64);
  ×0 and ×±64 become a clear or two shifts, with exactly the
  same result. In DIRTBIKE, about −16 % on the physics of
  track 1.
* **Square root**: the `sqrt_seed[h] = ⌊√(h·256)⌋` table (256 B, built at
  startup) never overshoots; one or two steps are enough beyond 256.
* **Division**: the PHYSICS demo used a 512 B table of reciprocals
  plus a correction multiply. For a one-byte quotient, eight
  subtraction steps cost as much, with no table.

### Division by bytes

`div16by8` divides the high byte first when the quotient needs more than
one byte, then reuses the low-byte loop. During the high-byte stage the
processed prefix cannot exceed 255, so no ninth-bit remainder test is
needed. The routine occupies **51 bytes instead of 52**, with unchanged
RAM, zero page, stack and Y preservation.

This is a measured tradeoff: **16-bit quotients save 92 cycles**, while
**8-bit quotients cost two more cycles**, excluding branch page crossings.
For example, 65535/255 takes 349 instead of 441 cycles, 256/1 takes 342
instead of 434, and 255/1 takes 245 instead of 243 (JSR/RTS included).
A zero divisor retains the existing sentinel quotient $FFFF and the
original numerator's low byte as remainder.

The normal suite checks all 65,536 numerators for 16 representative
divisors; `make test-math-division-full` checks all **16,777,216 pairs**.
Both paths use Python quotient/remainder as the oracle and check Y
preservation. In the page-contained fixture, the full sweep (including
loop/output overhead) takes 5,789,740,192 instead of 6,547,795,104 cycles.

The subsequent carry-fed high-byte loop keeps the **51-byte** footprint.
Each comparison supplies the quotient bit for the next rotation; one final
rotation appends the last bit. Short quotients stay unchanged, while
65535/1 takes **412 instead of 447 cycles**, 65535/2 takes 410 instead of
440, and 65535/0 takes 380 instead of 415. The full sweep drops another
17,935,360 cycles to **5,771,804,832** on each CPU. All 16,777,216 pairs pass
on NMOS/65C02, as do 16 representative calls at every one of 256 code
alignments, with no measured slowdown. The full Make target includes both
CPUs and alignments; `test_math_division.py --bench --out PATH` records
timings and source/tool/emulator identities, and `--reference PATH` selects
an old source. Y, I/D, RAM and stacks retain their previous contract.

## Tests

`dev/tests/test_math.py` (in `make test-hgr`) assembles each routine,
runs it in a2run on about 2,100 cases (edges, sign patterns, fixed
random) and compares against the Python computation. It is built twice: tables at
`$0800`, then tables and `sqrt_seed` in HGR page 2.
It also checks all 2,048 generated quarter-square bytes, all 256 seed bytes,
and all 65,536 square roots at both table placements in a separate fixture,
on both 6502 and 65C02.

`mul_init` advances the quarter-square difference every other entry and uses
a descending half counter in X and a low index in Y. A single pass copies both
halves of the mirrored table. In the exhaustive fixture this takes **37,687
cycles and 109 bytes**, down from 37,691/110 before the counter pass
(originally 48,707/128). The square-root kernel
uses the candidate's wrap to detect the maximum root: 42 bytes instead of 44.
Seed construction reuses the root already returned in Y: **23,519 cycles
and 20 bytes**, down from 24,031/21 (originally 25,049 cycles). The complete root
sweep, including the fixture's stores and loop, takes 5,529,438 instead of
5,727,330 cycles. Returning the maximal root 255 costs two extra cycles;
other candidate steps save two. Table storage and zero page are unchanged.

`test_math_products.py` checks every 16-bit input, signed and unsigned, for
constants 0, 1, 2, 4, 8, 16, 32, 64, 73, 128, 183 and 255:
**1,572,864 products**, plus Y preservation and the caller's cheap-label
scope. The general macros occupy 44/55 bytes instead of the original
49/60; they save eight cycles per expansion.

Zero, one and powers of two use smaller table-free paths. Low factors
shift left; ×16 joins nibbles; ×32/64/128 shift a value initially placed
one byte higher. Signed large factors repeat the sign bit directly, so
there is no later correction. These paths work before `mul_init`; the
test deliberately poisons all square-table bytes for those constants.
Allocated zero page stays unchanged, and `MUL_TABLES` must still be defined
when including `math.inc`.

| Factor | Unsigned / signed code bytes | Unsigned cycles, including JSR/RTS |
|---|---:|---:|
| 0 | 8 / 8 | 23 |
| 1 | 12 / 23 | 29 |
| 2 | 15 / 26 | 35 |
| 4 | 21 / 32 | 50 |
| 8 | 27 / 38 | 65 |
| 16 | 34 / 45 | 71 |
| 32 | 27 / 33 | 65 |
| 64 | 22 / 26 | 53 |
| 128 | 17 / 19 | 41 |

The general path previously used 44/55 bytes for all these factors and,
at input $FFFF, took 76 cycles for ×0 and 80 for the others. Branches in
the measurement fixture remain within one page. Each specialized unsigned
path is also faster than the general path's 72-cycle minimum including
JSR/RTS. General factors (73, 183, 255 in the exhaustive test) are unchanged.

`mul_acc_shr6` falls through to `mul_shr6`, saving 3 bytes and 3 cycles:
60 cycles including JSR/RTS instead of 63. The accumulator remains intact.
The test exercises accumulator-only, shift-only, combined and unused
includes; the shared tail is emitted when either entry is requested.
No table, allocated zero page or stack requirements change.

Author: VERHILLE Arnaud. Licence: [GPL-3.0](../../../LICENSE).

`dec.asm` emits only the requested byte conversion entry: `byte_div10`
alone occupies 11 bytes instead of 21. When both entries are referenced
before inclusion, they still share the same 21-byte implementation, with
identical instructions. If `byte_to_dec` is first referenced after an
earlier division-only include, its 10-byte prefix uses a 3-byte jump back
to the existing division tail. `test_math.py` checks all 256 inputs in
these configurations, X preservation and repeated includes.

The 16-bit decimal converter counts down through the four powers of ten.
Testing the index's sign removes two code bytes and four explicit comparisons
(eight instruction cycles per call, before placement effects). Digits, leading
zero suppression and NUL termination stay unchanged. The GFX signed wrapper
also propagates the sign-test carry through the complement, saving two more
bytes. `test_gfx_decimal.py` checks every signed and unsigned word, lengths and
buffer guards on both 6502 and 65C02 (`--iie`).
