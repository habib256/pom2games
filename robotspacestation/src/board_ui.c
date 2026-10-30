/* Robot Space Station — the board editor, shared by the chip lab and the
 * inside of the drone (docs/SPEC.md). Lab: sources 1-4 are test inputs,
 * sinks 1-4 the chip outputs. Drone: sources are the bumpers N E S W, the
 * claw's hold and the radio heard; the sinks, the thrusters, are shown as
 * motors by where they send the drone (thruster N pushes south: MOTOR S),
 * then the claw and the radio sent. Draw with the pointer and technician
 * hidden. */
#include <string.h>
#include "dhgr.h"
#include "sim.h"
#include "ui.h"
#include "board_ui.h"

/* Layout of the board (color pixels). */
#define GX 14u                  /* grid of COLS x ROWS cells */
#define GY 12u
#define CW 22u
#define CH 26u
#define COLS 5u
#define ROWS 5u
#define BOARD_H 140u
#define PAL_H 10u

#define C_ONE DHGR_ORANGE
#define C_ZERO DHGR_BLUE
#define C_PIN DHGR_GRAY2

static const char gate_names[] = "ANDOR XORNOTMEM";   /* 3 characters each */
static const char in_names[] = "NESWHR";      /* bumpers, HOLDING, RADIO */
static const char out_names[] = "NESWCR";     /* motors (by row), CLAW, RADIO */

unsigned char lab_inputs[4];          /* E1-E4 test values */
unsigned char mode;
unsigned char held_kind;              /* new part in hand (kind), or 0 */
unsigned char held_part = NONE;       /* moved part in hand, or NONE */
unsigned char held_src = NONE;        /* wire start (layout source), or NONE */

/* Screen bookkeeping in low memory (LOWBSS, $1000-$1FFF). */
#pragma bss-name (push, "LOWBSS")
static unsigned char drawn[LAYOUT_IDS];
static unsigned char out_drawn[6], in_drawn[6];
static unsigned char stub_drawn[PARTS * 4u];      /* output pin colors */
static unsigned char x0, y0, x1, y1;  /* points from src_point/sink_point */
static unsigned char gx0[LAYOUT_IDS], gy0[LAYOUT_IDS], gx1[LAYOUT_IDS], gy1[LAYOUT_IDS];
static unsigned char gm[LAYOUT_IDS];   /* the column of each drawn wire's vertical */
#pragma bss-name (pop)
static char label[4];

/* -- geometry -------------------------------------------------------------- */

static unsigned char __fastcall__ cell_x(unsigned char col) { return GX + col * CW; }
static unsigned char __fastcall__ cell_y(unsigned char row) { return GY + row * CH; }
static unsigned char __fastcall__ term_y(unsigned char k) { return 17u + k * 18u; }
/* The power terminal '+' (source POWER, always 1): the left column's last row. */
#define POWER_ROW 6u
static unsigned char __fastcall__ src_row(unsigned char s) { return s == POWER ? POWER_ROW : s; }
/* The row of sink k, and the sink on row k: in a drone, motor N (row 0)
 * is thruster S; in the lab, chip output k is on row k. */
static unsigned char __fastcall__ sink_row(unsigned char k)
{
    return k < 4u && screen != S_LAB ? k ^ 2u : k;
}
/* Terminals per side: the chip's 4 pins in the lab, 6 in the drone. */
#define TERMS (screen == S_LAB ? 4u : 6u)

/* Pin rows inside a cell. */
static unsigned char in_dy(unsigned char kind, unsigned char k)
{
    if (kind >= K_CHIP0) return 5u + k * 5u;
    if (part_inputs(kind) == 1u) return 12u;
    return k ? 16u : 9u;
}

static unsigned char __fastcall__ out_dy(unsigned char kind, unsigned char k)
{
    return kind >= K_CHIP0 ? (unsigned char)(5u + k * 5u) : 12u;
}

/* Point of a layout source; 0 if not on screen (a part in hand). */
static unsigned char __fastcall__ src_point(unsigned char s)
{
    static unsigned char i, *p;
    if (s < TERMINALS) {
        x0 = 11u; y0 = term_y(src_row(s)) + 5u;
        return 1u;
    }
    i = (unsigned char)(s - TERMINALS) >> 2;
    p = parts + i * 3u;
    if (!p[0] || p[1] >= COLS) return 0u;
    x0 = cell_x(p[1]) + 20u;
    y0 = cell_y(p[2]) + out_dy(p[0], (s - TERMINALS) & 3u);
    return 1u;
}

static unsigned char __fastcall__ sink_point(unsigned char s)
{
    static unsigned char i, *p;
    if (s < TERMINALS) {
        x0 = 128u; y0 = term_y(sink_row(s)) + 5u;
        return 1u;
    }
    i = (unsigned char)(s - TERMINALS) >> 2;
    p = parts + i * 3u;
    if (!p[0] || p[1] >= COLS) return 0u;
    x0 = cell_x(p[1]) + 1u;
    y0 = cell_y(p[2]) + in_dy(p[0], (s - TERMINALS) & 3u);
    return 1u;
}

/* -- drawing --------------------------------------------------------------- */

static void header(void)
{
    dhgr_fill_rect(0, 0, 140, 8, DHGR_BLACK);
    text_at(screen == S_LAB ? T_H_LAB : cur_drone ? T_H_DRONE_B : T_H_DRONE_A, 0, 1);
    dhgr_puts_small("GATES", 95, 1);
    label[0] = '0' + fl_count / 10u;
    label[1] = '0' + fl_count % 10u;
    label[2] = 0;
    dhgr_puts_small(label, 128, 1);
}

/* A wire runs horizontally from its source, vertically at column m, then
 * horizontally into its sink: three rectangles, erased exactly in black. */
static unsigned char m;
static void wire_rects(unsigned char a, unsigned char ay, unsigned char b, unsigned char by,
                       unsigned char color)
{
    static unsigned char lo, hi;
    if (a < m) { lo = a; hi = m; } else { lo = m; hi = a; }
    dhgr_fill_rect(lo, ay, hi - lo + 1u, 1, color);
    if (ay < by) { lo = ay; hi = by; } else { lo = by; hi = ay; }
    dhgr_fill_rect(m, lo, 1, hi - lo + 1u, color);
    if (b < m) { lo = b; hi = m; } else { lo = m; hi = b; }
    dhgr_fill_rect(lo, by, hi - lo + 1u, 1, color);
}

/* Endpoints of a wired sink into x0,y0 (source) and x1,y1; 0 if none. */
static unsigned char __fastcall__ wire_ends(unsigned char sink)
{
    static unsigned char s;
    s = wires[sink];
    if (s == NONE || !sink_point(sink)) return 0u;
    x1 = x0; y1 = y0;
    return src_point(s);
}

/* The vertical's column: the middle, or the nearest one (2 pixels apart,
 * between the ends) that no other drawn wire's vertical uses on these
 * rows: wires from neighbouring pins no longer share their vertical. */
static unsigned char __fastcall__ mid_free(unsigned char sink)
{
    static unsigned char lo, hi, ylo, yhi, j, k, c, ok;
    if (x0 < x1) { lo = x0; hi = x1; } else { lo = x1; hi = x0; }
    if (y0 < y1) { ylo = y0; yhi = y1; } else { ylo = y1; yhi = y0; }
    m = (unsigned char)(((unsigned)lo + hi) >> 1);
    for (k = 0u; k < 24u; ++k) {
        c = k & 1u ? m - (k + 1u) : m + k;      /* m, m+2, m-2, m+4... */
        if (c <= lo || c >= hi) continue;
        ok = 1u;
        for (j = 0u; j < LAYOUT_IDS; ++j)
            if (j != sink && drawn[j] != NONE && gm[j] == c
                && !(gy0[j] > yhi && gy1[j] > yhi) && !(gy0[j] < ylo && gy1[j] < ylo)) {
                ok = 0u;
                break;
            }
        if (ok) return c;
    }
    return m;
}

static void __fastcall__ erase_wire(unsigned char sink)
{
    if (drawn[sink] == NONE) return;
    m = gm[sink];
    wire_rects(gx0[sink], gy0[sink], gx1[sink], gy1[sink], DHGR_BLACK);
    drawn[sink] = NONE;
}

static void __fastcall__ draw_wire(unsigned char sink)
{
    static unsigned char v;
    if (!wire_ends(sink)) { drawn[sink] = NONE; return; }
    /* in place (a color, the same ends): its column; else a free one */
    m = drawn[sink] != NONE ? gm[sink] : mid_free(sink);
    gm[sink] = m;
    v = source_value(wires[sink]);
    drawn[sink] = v;
    gx0[sink] = x0; gy0[sink] = y0; gx1[sink] = x1; gy1[sink] = y1;
    wire_rects(x0, y0, x1, y1, v ? C_ONE : C_ZERO);
}

/* The output pin k of part i, colored by its value. */
static void draw_stub(unsigned char i, unsigned char k)
{
    static unsigned char *p, v;
    p = parts + i * 3u;
    v = source_value(TERMINALS + (i << 2) + k);
    stub_drawn[(i << 2) + k] = v;
    dhgr_fill_rect(cell_x(p[1]) + 19u, cell_y(p[2]) + out_dy(p[0], k), 2, 1, v ? C_ONE : C_ZERO);
}

/* Gate g's (kind - 1) three letters into label. */
static void __fastcall__ gate_label(unsigned char g)
{
    g *= 3u;
    label[0] = gate_names[g];
    label[1] = gate_names[g + 1u];
    label[2] = gate_names[g + 2u];
    label[3] = 0;
}

/* src/symbol.s: the gates' schematic symbols (AND OR XOR NOT, kind - 1). */
extern unsigned char sym_x, sym_y;
void __fastcall__ draw_symbol(unsigned char g);

static void __fastcall__ draw_part(unsigned char i)
{
    static unsigned char *p, kind, cx, cy, top, h, k, n;
    p = parts + i * 3u;
    kind = p[0];
    if (!kind || p[1] >= COLS) return;
    cx = cell_x(p[1]);
    cy = cell_y(p[2]);
    if (kind < K_FLIP) {
        dhgr_fill_rect(cx + 3u, cy + 6u, 16, 13, DHGR_BLACK);
        sym_x = cx + 3u; sym_y = cy + 6u;
        draw_symbol(kind - 1u);
    } else {
        if (kind >= K_CHIP0) {
            top = cy + 3u; h = 20u;
            label[0] = ' '; label[1] = 'C'; label[2] = '1' + kind - K_CHIP0;
        } else {
            top = cy + 6u; h = 13u;
            gate_label(kind - 1u);
        }
        dhgr_fill_rect(cx + 3u, top, 16, h, kind >= K_CHIP0 ? DHGR_VIOLET : DHGR_GREEN);
        dhgr_fill_rect(cx + 4u, top + 1u, 14, h - 2u, DHGR_BLACK);
        dhgr_puts_small(label, cx + 4u, cy + 10u);
    }
    n = part_inputs(kind);
    for (k = 0u; k < n; ++k)
        dhgr_fill_rect(cx + 1u, cy + in_dy(kind, k), 2, 1, C_PIN);
    n = part_outputs(kind);
    for (k = 0u; k < n; ++k) draw_stub(i, k);
}

static unsigned char __fastcall__ in_value(unsigned char k)
{
    return screen == S_LAB ? lab_inputs[k] : values[k];
}

/* Source k, or sink k (out) on its row. */
static void draw_terminal(unsigned char k, unsigned char out, unsigned char v)
{
    static unsigned char x, y;
    x = out ? 130u : 1u;
    if (out) k = sink_row(k);
    y = term_y(src_row(k));
    label[0] = k == POWER && !out ? '+' : screen == S_LAB ? '1' + k : out ? out_names[k] : in_names[k];
    label[1] = 0;
    dhgr_fill_rect(x, y, 9, 11, v ? C_ONE : C_ZERO);
    dhgr_puts_small(label, x + 2u, y + 3u);
    dhgr_fill_rect(out ? 128u : 10u, y + 5u, 2, 1, C_PIN);
}

static void draw_parts_and_terminals(void)
{
    static unsigned char i;
    for (i = 0u; i < PARTS; ++i) {
        if (!(i & 3u)) ui_latch();
        draw_part(i);
    }
    for (i = 0u; i < TERMS; ++i) {
        out_drawn[i] = sink_value(i);
        draw_terminal(i, 1u, out_drawn[i]);
        in_drawn[i] = in_value(i);
        draw_terminal(i, 0u, in_drawn[i]);
    }
    draw_terminal(POWER, 0u, 1u);
}

static void grid_dots(void)
{
    static unsigned char occupied[COLS * ROWS], i, c, r, *p;
    memset(occupied, 0, sizeof occupied);
    for (i = 0u, p = parts; i < PARTS; ++i, p += 3)
        if (p[0] && p[1] < COLS) occupied[p[2] * COLS + p[1]] = 1u;
    for (r = 0u, i = 0u; r < ROWS; ++r)
        for (c = 0u; c < COLS; ++c, ++i)
            if (!occupied[i])
                dhgr_plot_color(cell_x(c) + 10u, cell_y(r) + 12u, DHGR_GRAY1);
}

void board_update(void)
{
    static unsigned char i;
    for (i = 0u; i < LAYOUT_IDS; ++i) {
        if (drawn[i] == NONE) continue;
        if (!wire_ends(i) || x0 != gx0[i] || y0 != gy0[i] || x1 != gx1[i] || y1 != gy1[i])
            erase_wire(i);
    }
    grid_dots();
    for (i = 0u; i < LAYOUT_IDS; ++i) {
        if (!(i & 15u)) ui_latch();
        draw_wire(i);
    }
    draw_parts_and_terminals();
    header();
}

/* Before a part leaves its cell: blank the cell (wires are redrawn after). */
static void __fastcall__ erase_part(unsigned char i)
{
    static unsigned char *p;
    p = parts + i * 3u;
    if (p[1] >= COLS) return;
    dhgr_fill_rect(cell_x(p[1]) + 1u, cell_y(p[2]) + 2u, 20, 22, DHGR_BLACK);
}

void board_draw(void)
{
    static unsigned char y;
    for (y = BOARD_TOP; y < BOARD_TOP + BOARD_H; y += 20u) {
        ui_latch();
        dhgr_clear_rows(y, 20, DHGR_BLACK);
    }
    memset(drawn, NONE, sizeof drawn);
    text_at(T_H_TOOLBOX, 0, 145);
    if (screen == S_LAB) {
        text_at(T_H_INPUTS, 0, 10);
        text_at(T_H_OUTPUTS, 105, 10);
    } else {
        text_at(T_H_SENSORS, 0, 10);
        text_at(T_H_MOTORS, 110, 10);
        dhgr_fill_rect(DOOR_X, DOOR_Y, DOOR_W, 3, DHGR_YELLOW);
    }
    board_update();
}

void board_palette(void)
{
    static unsigned char i, x;
    dhgr_fill_rect(0, PAL_Y, 140, PAL_H, DHGR_BLACK);
    for (i = 0u; i < 5u; ++i) {
        x = i * PAL_GATE_W;
        dhgr_fill_rect(x, PAL_Y, PAL_GATE_W - 1u, PAL_H, DHGR_GREEN);
        gate_label(i);
        dhgr_puts_small(label, x + 1u, PAL_Y + 2u);
    }
    label[1] = 0;
    for (i = 0u; i < CHIPS; ++i) {
        x = PAL_CHIP_X + i * PAL_CHIP_W;
        dhgr_fill_rect(x, PAL_Y, PAL_CHIP_W - 1u, PAL_H, chip_count[i] ? DHGR_VIOLET : DHGR_GRAY1);
        label[0] = '1' + i;
        dhgr_puts_small(label, x + 1u, PAL_Y + 2u);
    }
}

/* After a turn only colors change: wires, output pins and terminals whose
 * value moved (a wire redrawn in place covers the same pixels as before). */
void board_refresh(void)
{
    static unsigned char i, k, n, v, *p;
    for (i = 0u; i < LAYOUT_IDS; ++i) {
        if (wires[i] != NONE && drawn[i] != NONE && drawn[i] != source_value(wires[i])) {
            begin_draw();
            draw_wire(i);
        }
    }
    for (i = 0u, p = parts; i < PARTS; ++i, p += 3) {
        if (!p[0] || p[1] >= COLS) continue;
        n = part_outputs(p[0]);
        for (k = 0u; k < n; ++k)
            if (stub_drawn[(i << 2) + k] != source_value(TERMINALS + (i << 2) + k)) {
                begin_draw();
                draw_stub(i, k);
            }
    }
    for (i = 0u; i < TERMS; ++i) {
        v = sink_value(i);
        if (out_drawn[i] != v) {
            begin_draw();
            out_drawn[i] = v;
            draw_terminal(i, 1u, v);
        }
        v = in_value(i);
        if (in_drawn[i] != v) {
            begin_draw();
            in_drawn[i] = v;
            draw_terminal(i, 0u, v);
        }
    }
}

void board_recompile(void)
{
    board_compile();
    board_update();
}

/* -- what the pointer is on ----------------------------------------------- */

/* board_hit(): what is at x, y; hit_n its number (terminal, layout pin,
 * part, palette slot), hit_c, hit_r the cell. */
#define H_NONE 0u
#define H_SOURCE 1u             /* a source terminal (hit_n: its number) */
#define H_TOGGLE 2u             /* lab: the box of input hit_n (0 / 1) */
#define H_SINK 3u               /* a sink terminal (hit_n: the sink) */
#define H_PIN_IN 4u             /* hit_n: the layout sink id */
#define H_PIN_OUT 5u            /* hit_n: the layout source id */
#define H_PART 6u               /* hit_n: the part */
#define H_CELL 7u               /* a free cell hit_c, hit_r */
#define H_GATE 8u               /* palette: gate kind hit_n */
#define H_CHIP 9u               /* palette: chip hit_n */
static unsigned char hit_n, hit_c, hit_r;

static unsigned char __fastcall__ terminal_row(unsigned char y)
{
    static unsigned char k;
    for (k = 0u; k <= POWER_ROW; ++k)
        if ((unsigned char)(y - term_y(k)) < 11u) return k;
    return NONE;
}

static unsigned char board_hit(unsigned char x, unsigned char y)
{
    static unsigned char k, kind, n, lx, ly;
    if (y >= PAL_Y && y < PAL_Y + PAL_H) {
        if (x < PAL_CHIP_X) { hit_n = 1u + x / PAL_GATE_W; return H_GATE; }
        hit_n = (x - PAL_CHIP_X) / PAL_CHIP_W;
        return hit_n < CHIPS ? H_CHIP : H_NONE;
    }
    if (y < GY || y >= GY + ROWS * CH) return H_NONE;
    if (x < GX || x >= GX + COLS * CW) {
        k = terminal_row(y);
        if (k == POWER_ROW && x < GX) { hit_n = POWER; return H_SOURCE; }
        if (k >= TERMS) return H_NONE;
        if (x >= GX) { hit_n = sink_row(k); return H_SINK; }
        hit_n = k;
        return screen == S_LAB && x < 10u ? H_TOGGLE : H_SOURCE;
    }
    x -= GX; y -= GY;
    hit_c = x / CW; hit_r = y / CH;
    lx = x % CW; ly = y % CH;
    hit_n = part_at(hit_c, hit_r);
    if (hit_n == NONE) return H_CELL;
    kind = parts[hit_n * 3u];
    if (lx <= 3u) {
        n = part_inputs(kind);
        for (k = 0u; k < n; ++k)
            if ((unsigned char)(ly - in_dy(kind, k) + 2u) <= 4u) {
                hit_n = TERMINALS + (hit_n << 2) + k;
                return H_PIN_IN;
            }
    } else if (lx >= 18u) {
        n = part_outputs(kind);
        for (k = 0u; k < n; ++k)
            if ((unsigned char)(ly - out_dy(kind, k) + 2u) <= 4u) {
                hit_n = TERMINALS + (hit_n << 2) + k;
                return H_PIN_OUT;
            }
    }
    return H_PART;
}

/* The text for what is under x, y; 0: nothing to say. */
unsigned char board_hover(unsigned char x, unsigned char y)
{
    static unsigned char h, kind;
    h = board_hit(x, y);
    switch (h) {
    case H_SOURCE:
        if (hit_n == POWER) return T_POWER;
        return screen == S_LAB ? T_LAB_PIN : T_SENS_N + hit_n;
    case H_TOGGLE: return T_LAB_IN;
    case H_SINK: return screen == S_LAB ? T_LAB_OUT : T_MOT_N + sink_row(hit_n);
    case H_PIN_OUT: return T_PIN_OUT;
    case H_PIN_IN:
        kind = parts[((hit_n - TERMINALS) >> 2) * 3u];
        if (kind == K_FLIP) return (hit_n & 3u) ? T_PIN_RESET : T_PIN_SET;
        return T_PIN_IN;
    case H_PART:
        kind = parts[hit_n * 3u];
        return kind >= K_CHIP0 ? T_PART_CHIP : T_PART_AND - 1u + kind;
    case H_GATE: return T_PART_AND - 1u + hit_n;
    case H_CHIP: return chip_count[hit_n] ? T_PART_CHIP : T_CHIP_EMPTY;
    }
    return 0u;
}

/* -- clicks ---------------------------------------------------------------- */

static void click_source(unsigned char s)
{
    held_kind = 0u;
    held_src = s;
    msg(T_G_WIRE);
}

static void click_sink(unsigned char s)
{
    if (held_src != NONE) {
        wires[s] = held_src;
        held_src = NONE;
    } else if (wires[s] != NONE) {
        wires[s] = NONE;
        msg(T_WIRE_OFF);
    } else {
        return;
    }
    board_recompile();
}

static void click_cell(void)
{
    static unsigned char i;
    if (held_part != NONE) {
        parts[held_part * 3u + 1u] = hit_c;
        parts[held_part * 3u + 2u] = hit_r;
        held_part = NONE;
        board_update();
    } else if (held_kind) {
        i = part_place(held_kind, hit_c, hit_r);
        if (i == NONE) {
            msg(T_FULL);
        } else if (!board_compile()) {
            part_remove(i);
            board_compile();
            msg(T_TOO_MANY);
        } else {
            board_update();
        }
    }
}

static void click_part(unsigned char i)
{
    if (!held_kind && held_part == NONE) {
        held_part = i;
        held_src = NONE;
        erase_part(i);
        parts[i * 3u + 1u] = NONE;  /* off the grid while in hand */
        msg(T_IN_HAND);
        board_update();
    } else {
        msg(T_OCCUPIED);
    }
}

static void click_palette(unsigned char h)
{
    static unsigned char c;
    if (held_part != NONE) {
        part_remove(held_part);
        held_part = NONE;
        msg(T_THROWN);
        board_recompile();
        return;
    }
    held_src = NONE;
    if (h == H_GATE) {
        held_kind = hit_n;
        msg(T_G_PLACE);
        return;
    }
    c = hit_n;
    if (mode == M_BURN) {
        mode = M_EDIT;
        if (!board_burn(c)) {
            msg(T_CHIP_MAX);
            return;
        }
        board_compile();
        board_palette();
        board_update();
        sfx(SFX_BURN);
        msg(board_saved() ? T_BURNED : T_BURNED_NS);
        return;
    }
    if (!chip_count[c]) {
        msg(T_CHIP_EMPTY);
        return;
    }
    if (mode == M_OPEN) {
        mode = M_EDIT;
        memcpy(parts, chip_layout[c], sizeof parts);
        memcpy(wires, chip_layout[c] + sizeof parts, sizeof wires);
        held_kind = 0u;
        msg(T_OPENED);
        board_compile();
        board_draw();
        return;
    }
    held_kind = K_CHIP0 + c;
    msg(T_G_PLACE);
}

void board_click(unsigned char x, unsigned char y)
{
    static unsigned char h;
    h = board_hit(x, y);
    switch (h) {
    case H_GATE: case H_CHIP: click_palette(h); break;
    case H_SOURCE: case H_PIN_OUT: click_source(hit_n); break;
    case H_SINK: case H_PIN_IN: click_sink(hit_n); break;
    case H_TOGGLE:
        lab_inputs[hit_n] ^= 1u;
        in_drawn[hit_n] = lab_inputs[hit_n];
        draw_terminal(hit_n, 0u, lab_inputs[hit_n]);
        break;
    case H_CELL: click_cell(); break;
    case H_PART: click_part(hit_n); break;
    }
}

void board_drop(void)
{
    static unsigned char c, r;
    if (held_part != NONE) {
        /* Back where nothing else stands: the first free cell. */
        for (r = 0u; r < ROWS; ++r)
            for (c = 0u; c < COLS; ++c)
                if (part_at(c, r) == NONE) {
                    parts[held_part * 3u + 1u] = c;
                    parts[held_part * 3u + 2u] = r;
                    r = ROWS; c = COLS;
                }
        held_part = NONE;
        board_update();
    }
    held_kind = 0u;
    held_src = NONE;
    mode = M_EDIT;
    msg(T_EMPTY_HANDS);
}

void board_clear_all(void)
{
    board_clear();
    held_kind = 0u; held_part = NONE; held_src = NONE;
    board_compile();
    board_draw();
}

/* Parts on the board (for the guidance line). */
unsigned char board_parts(void)
{
    static unsigned char i, n;
    for (i = 0u, n = 0u; i < PARTS; ++i) n += parts[i * 3u] != 0u;
    return n;
}
