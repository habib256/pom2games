/* Robot Space Station — boards, chips and the logic simulation.
 * A transcription of tools/model.py: keep both in step. */
#include <string.h>
#include "sim.h"

unsigned char parts[PARTS * 3u];
unsigned char wires[LAYOUT_IDS];
unsigned char fl_count;
unsigned char fl_kind[BOARD_GATES], fl_a[BOARD_GATES], fl_b[BOARD_GATES];
unsigned char fl_sinks[TERMINALS];
unsigned char values[TERMINALS + BOARD_GATES];
#pragma bss-name (push, "LOWBSS")
Persist persist;
#pragma bss-name (pop)

static unsigned char base[PARTS];
static unsigned char ins[4];
static unsigned char fresh[BOARD_GATES];

unsigned char __fastcall__ part_inputs(unsigned char kind)
{
    if (kind >= K_CHIP0) return 4u;
    return (kind == K_NOT || kind == K_BUF) ? 1u : 2u;
}

unsigned char __fastcall__ part_outputs(unsigned char kind)
{
    return kind >= K_CHIP0 ? 4u : 1u;
}

unsigned char part_place(unsigned char kind, unsigned char x, unsigned char y)
{
    static unsigned char i, *p;
    for (i = 0u, p = parts; i < PARTS; ++i, p += 3) {
        if (!p[0]) {
            p[0] = kind; p[1] = x; p[2] = y;
            return i;
        }
    }
    return NONE;
}

void __fastcall__ part_remove(unsigned char i)
{
    static unsigned char s, lo;
    lo = TERMINALS + (i << 2);
    parts[i * 3u] = 0u;
    for (s = 0u; s < LAYOUT_IDS; ++s) {
        if ((unsigned char)(wires[s] - lo) < 4u) wires[s] = NONE;
    }
    memset(wires + lo, NONE, 4);
}

unsigned char part_at(unsigned char x, unsigned char y)
{
    static unsigned char i, *p;
    for (i = 0u, p = parts; i < PARTS; ++i, p += 3) {
        if (p[0] && p[1] == x && p[2] == y) return i;
    }
    return NONE;
}

void board_clear(void)
{
    memset(parts, 0, sizeof parts);
    memset(wires, NONE, sizeof wires);
}

/* Layout source id -> flat source id (bases already assigned). */
static unsigned char __fastcall__ resolve(unsigned char s)
{
    static unsigned char i, k, kind, g;
    if (s == NONE || s < TERMINALS) return s;
    i = (unsigned char)(s - TERMINALS) >> 2;
    k = (s - TERMINALS) & 3u;
    kind = parts[i * 3u];
    if (!kind) return NONE;
    if (kind < K_CHIP0) return k ? NONE : (unsigned char)(TERMINALS + base[i]);
    g = chip_out[kind - K_CHIP0][k];
    return g == NONE ? NONE : (unsigned char)(TERMINALS + base[i] + g);
}

/* A chip's local source s placed at flat base cur_base: its inputs come
 * from ins[], CHIP_POWER is the board's POWER. */
static unsigned char cur_base;
static unsigned char __fastcall__ inner(unsigned char s)
{
    if (s == NONE) return NONE;
    if (s == CHIP_POWER) return POWER;
    return s < 4u ? ins[s] : (unsigned char)(TERMINALS + cur_base + s - 4u);
}

unsigned char board_compile(void)
{
    static unsigned char i, k, n, count, kind, c, g, *p;
    count = 0u;
    for (i = 0u, p = parts; i < PARTS; ++i, p += 3) {
        kind = p[0];
        if (!kind) continue;
        base[i] = count;
        count += kind >= K_CHIP0 ? chip_count[kind - K_CHIP0] : 1u;
        if (count > BOARD_GATES) return 0u;
    }
    n = 0u;
    for (i = 0u, p = parts; i < PARTS; ++i, p += 3) {
        kind = p[0];
        if (!kind) continue;
        for (k = 0u; k < 4u; ++k) ins[k] = resolve(wires[TERMINALS + (i << 2) + k]);
        if (kind < K_CHIP0) {
            fl_kind[n] = kind;
            fl_a[n] = ins[0];
            fl_b[n] = part_inputs(kind) == 2u ? ins[1] : NONE;
            ++n;
            continue;
        }
        c = kind - K_CHIP0;
        cur_base = base[i];
        for (g = 0u; g < chip_count[c]; ++g, ++n) {
            fl_kind[n] = chip_kind[c][g];
            fl_a[n] = inner(chip_a[c][g]);
            fl_b[n] = inner(chip_b[c][g]);
        }
    }
    for (k = 0u; k < TERMINALS; ++k) fl_sinks[k] = resolve(wires[k]);
    fl_count = n;
    memset(values, 0, sizeof values);
    values[POWER] = 1u;
    return 1u;
}

/* Flat id -> chip-local id: 0-3 inputs, 4+g gate g, CHIP_POWER the
 * board's POWER; lab sources 4-6 = 0. */
static unsigned char __fastcall__ local(unsigned char s)
{
    if (s == POWER) return CHIP_POWER;
    if (s == NONE || (s >= 4u && s < TERMINALS)) return NONE;
    return s < 4u ? s : (unsigned char)(s - TERMINALS + 4u);
}

unsigned char __fastcall__ board_burn(unsigned char c)
{
    static unsigned char g, k, n, s, cc;
    cc = c;
    if (!board_compile()) return 0u;
    n = fl_count;
    for (k = 0u; k < 4u; ++k) {
        s = fl_sinks[k];
        if (s < 4u || s == POWER) ++n;      /* E (or +) -> S directly: one BUF */
    }
    if (n > CHIP_GATES) return 0u;
    for (g = 0u; g < fl_count; ++g) {
        chip_kind[cc][g] = fl_kind[g];
        chip_a[cc][g] = local(fl_a[g]);
        chip_b[cc][g] = local(fl_b[g]);
    }
    for (k = 0u; k < 4u; ++k) {
        s = fl_sinks[k];
        if (s == NONE || (s >= 4u && s < POWER)) {
            chip_out[cc][k] = NONE;
        } else if (s <= POWER) {
            chip_kind[cc][g] = K_BUF;
            chip_a[cc][g] = local(s);
            chip_b[cc][g] = NONE;
            chip_out[cc][k] = g++;
        } else {
            chip_out[cc][k] = s - TERMINALS;
        }
    }
    for (; g < CHIP_GATES; ++g) {
        chip_kind[cc][g] = 0u; chip_a[cc][g] = 0u; chip_b[cc][g] = 0u;
    }
    chip_count[cc] = n;
    memcpy(chip_layout[cc], parts, sizeof parts);
    memcpy(chip_layout[cc] + sizeof parts, wires, sizeof wires);
    return 1u;
}

void board_tick(void)
{
    static unsigned char g, a, b, q, kind;
    for (g = 0u; g < fl_count; ++g) {
        a = fl_a[g]; a = a == NONE ? 0u : values[a];
        b = fl_b[g]; b = b == NONE ? 0u : values[b];
        kind = fl_kind[g];
        if (kind == K_AND) q = a & b;
        else if (kind == K_OR) q = a | b;
        else if (kind == K_XOR) q = a ^ b;
        else if (kind == K_NOT) q = a ^ 1u;
        else if (kind == K_FLIP) q = a ? 1u : b ? 0u : values[TERMINALS + g];
        else q = a;
        fresh[g] = q;
    }
    memcpy(values + TERMINALS, fresh, fl_count);
}

unsigned char __fastcall__ sink_value(unsigned char k)
{
    k = fl_sinks[k];
    return k == NONE ? 0u : values[k];
}

unsigned char __fastcall__ source_value(unsigned char s)
{
    s = resolve(s);
    return s == NONE ? 0u : values[s];
}
