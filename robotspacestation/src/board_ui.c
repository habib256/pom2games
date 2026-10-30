/* Robot Space Station — the board editor, shared by the chip lab and the
 * inside of the drone (docs/SPEC.md). Lab: sources E1-E4 are test inputs,
 * sinks S1-S4 the chip outputs. Drone: sources are the bumpers N E S O,
 * sinks the thrusters N E S O. Draw with the pointer and technician hidden. */
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

static const char gate_names[] = "ETOUOXNOBA";
static const char in_names[] = "NESOTR";      /* bumpers, HOLDING, RADIO */
static const char out_names[] = "NESOPR";     /* thrusters, CLAW, RADIO */

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
#pragma bss-name (pop)
static char label[3];

/* -- geometry -------------------------------------------------------------- */

static unsigned char __fastcall__ cell_x(unsigned char col) { return GX + col * CW; }
static unsigned char __fastcall__ cell_y(unsigned char row) { return GY + row * CH; }
static unsigned char __fastcall__ term_y(unsigned char k) { return 14u + k * 21u; }
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
        x0 = 11u; y0 = term_y(s) + 5u;
        return 1u;
    }
    i = (unsigned char)(s - TERMINALS) >> 2;
    p = parts + i * 3u;
    if (!p[0] || p[1] >= COLS) return 0u;
    x0 = cell_x(p[1]) + 18u;
    y0 = cell_y(p[2]) + out_dy(p[0], (s - TERMINALS) & 3u);
    return 1u;
}

static unsigned char __fastcall__ sink_point(unsigned char s)
{
    static unsigned char i, *p;
    if (s < TERMINALS) {
        x0 = 128u; y0 = term_y(s) + 5u;
        return 1u;
    }
    i = (unsigned char)(s - TERMINALS) >> 2;
    p = parts + i * 3u;
    if (!p[0] || p[1] >= COLS) return 0u;
    x0 = cell_x(p[1]) + 3u;
    y0 = cell_y(p[2]) + in_dy(p[0], (s - TERMINALS) & 3u);
    return 1u;
}

/* -- drawing --------------------------------------------------------------- */

static void header(void)
{
    dhgr_fill_rect(0, 0, 140, 8, DHGR_BLACK);
    dhgr_puts_small(screen == S_LAB ? "LABO DE PUCES" : cur_drone ? "DANS LE DRONE B" : "DANS LE DRONE A", 0, 1);
    dhgr_puts_small("PORTES", 85, 1);
    label[0] = '0' + fl_count / 10u;
    label[1] = '0' + fl_count % 10u;
    label[2] = 0;
    dhgr_puts_small(label, 120, 1);
}

/* A wire runs horizontally from its source, vertically at the middle, then
 * horizontally into its sink: three rectangles, erased exactly in black. */
static void wire_rects(unsigned char a, unsigned char ay, unsigned char b, unsigned char by,
                       unsigned char color)
{
    static unsigned char m, lo, hi;
    m = (unsigned char)(((unsigned)a + b) >> 1);
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

static void __fastcall__ erase_wire(unsigned char sink)
{
    if (drawn[sink] == NONE) return;
    wire_rects(gx0[sink], gy0[sink], gx1[sink], gy1[sink], DHGR_BLACK);
    drawn[sink] = NONE;
}

static void __fastcall__ draw_wire(unsigned char sink)
{
    static unsigned char v;
    if (!wire_ends(sink)) { drawn[sink] = NONE; return; }
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
    dhgr_fill_rect(cell_x(p[1]) + 17u, cell_y(p[2]) + out_dy(p[0], k), 2, 1, v ? C_ONE : C_ZERO);
}

static void __fastcall__ draw_part(unsigned char i)
{
    static unsigned char *p, kind, cx, cy, top, h, k, n;
    p = parts + i * 3u;
    kind = p[0];
    if (!kind || p[1] >= COLS) return;
    cx = cell_x(p[1]);
    cy = cell_y(p[2]);
    if (kind >= K_CHIP0) {
        top = cy + 3u; h = 20u;
        label[0] = 'P'; label[1] = '1' + kind - K_CHIP0;
    } else {
        top = cy + 6u; h = 13u;
        label[0] = gate_names[(kind - 1u) << 1];
        label[1] = gate_names[((kind - 1u) << 1) + 1u];
    }
    label[2] = 0;
    dhgr_fill_rect(cx + 5u, top, 12, h, kind >= K_CHIP0 ? DHGR_VIOLET : DHGR_GREEN);
    dhgr_fill_rect(cx + 6u, top + 1u, 10, h - 2u, DHGR_BLACK);
    dhgr_puts_small(label, cx + 6u, cy + 10u);
    n = part_inputs(kind);
    for (k = 0u; k < n; ++k)
        dhgr_fill_rect(cx + 3u, cy + in_dy(kind, k), 2, 1, C_PIN);
    n = part_outputs(kind);
    for (k = 0u; k < n; ++k) draw_stub(i, k);
}

static unsigned char __fastcall__ in_value(unsigned char k)
{
    return screen == S_LAB ? lab_inputs[k] : values[k];
}

static void draw_terminal(unsigned char k, unsigned char out, unsigned char v)
{
    static unsigned char x;
    x = out ? 130u : 1u;
    label[0] = screen == S_LAB ? '1' + k : out ? out_names[k] : in_names[k];
    label[1] = 0;
    dhgr_fill_rect(x, term_y(k), 9, 11, v ? C_ONE : C_ZERO);
    dhgr_puts_small(label, x + 2u, term_y(k) + 3u);
    dhgr_fill_rect(out ? 128u : 10u, term_y(k) + 5u, 2, 1, C_PIN);
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
    dhgr_fill_rect(cell_x(p[1]) + 3u, cell_y(p[2]) + 2u, 17, 22, DHGR_BLACK);
}

void board_draw(void)
{
    static unsigned char y;
    for (y = BOARD_TOP; y < BOARD_TOP + BOARD_H; y += 20u) {
        ui_latch();
        dhgr_clear_rows(y, 20, DHGR_BLACK);
    }
    memset(drawn, NONE, sizeof drawn);
    if (screen == S_LAB) {
        dhgr_puts_small("E", 3, 11);
        dhgr_puts_small("S", 132, 11);
    } else {
        dhgr_puts_small("CAPT", 0, 11);
        dhgr_puts_small("PROP", 120, 11);
        dhgr_fill_rect(DOOR_X, DOOR_Y, DOOR_W, 3, DHGR_YELLOW);
    }
    board_update();
}

void board_palette(void)
{
    static unsigned char i, x;
    label[2] = 0;
    dhgr_fill_rect(0, PAL_Y, 140, PAL_H, DHGR_BLACK);
    for (i = 0u; i < 5u; ++i) {
        x = i * 12u;
        dhgr_fill_rect(x, PAL_Y, 11, PAL_H, DHGR_GREEN);
        label[0] = gate_names[i << 1]; label[1] = gate_names[(i << 1) + 1u];
        dhgr_puts_small(label, x + 1u, PAL_Y + 2u);
    }
    for (i = 0u; i < CHIPS; ++i) {
        x = 60u + i * 10u;
        dhgr_fill_rect(x, PAL_Y, 9, PAL_H, chip_count[i] ? DHGR_VIOLET : DHGR_GRAY1);
        label[0] = 'P'; label[1] = '1' + i;
        dhgr_puts_small(label, x, PAL_Y + 2u);
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

/* -- clicks ---------------------------------------------------------------- */

static void click_source(unsigned char s)
{
    held_kind = 0u;
    held_src = s;
    message("FIL : CLIQUER UNE ENTREE");
}

static void click_sink(unsigned char s)
{
    if (held_src != NONE) {
        wires[s] = held_src;
        held_src = NONE;
        message("FIL POSE");
    } else if (wires[s] != NONE) {
        wires[s] = NONE;
        message("FIL RETIRE");
    } else {
        return;
    }
    board_recompile();
}

static void click_cell(unsigned char col, unsigned char row, unsigned char lx, unsigned char ly)
{
    static unsigned char i, kind, k, n;
    i = part_at(col, row);
    if (i == NONE) {
        if (held_part != NONE) {
            parts[held_part * 3u + 1u] = col;
            parts[held_part * 3u + 2u] = row;
            held_part = NONE;
            message("PIECE DEPLACEE");
            board_update();
        } else if (held_kind) {
            i = part_place(held_kind, col, row);
            if (i == NONE) {
                message("16 PIECES AU PLUS");
            } else if (!board_compile()) {
                part_remove(i);
                board_compile();
                message("TROP DE PORTES (64 AU PLUS)");
            } else {
                message("PIECE POSEE");
                board_update();
            }
        }
        return;
    }
    kind = parts[i * 3u];
    if (lx <= 5u) {
        n = part_inputs(kind);
        for (k = 0u; k < n; ++k)
            if ((unsigned char)(ly - in_dy(kind, k) + 2u) <= 4u) {
                click_sink(TERMINALS + (i << 2) + k);
                return;
            }
    } else if (lx >= 16u) {
        n = part_outputs(kind);
        for (k = 0u; k < n; ++k)
            if ((unsigned char)(ly - out_dy(kind, k) + 2u) <= 4u) {
                click_source(TERMINALS + (i << 2) + k);
                return;
            }
    } else if (!held_kind && held_part == NONE) {
        held_part = i;
        held_src = NONE;
        erase_part(i);
        parts[i * 3u + 1u] = NONE;  /* off the grid while in hand */
        message("EN MAIN : CASE VIDE/PALETTE");
        board_update();
    } else {
        message("CASE OCCUPEE");
    }
}

static void click_palette(unsigned char x)
{
    static unsigned char c;
    if (held_part != NONE) {
        part_remove(held_part);
        held_part = NONE;
        message("PIECE JETEE");
        board_recompile();
        return;
    }
    held_src = NONE;
    if (x < 60u) {
        held_kind = 1u + x / 12u;
        message("CLIQUER UNE CASE VIDE");
        return;
    }
    c = (x - 60u) / 10u;
    if (mode == M_BURN) {
        mode = M_EDIT;
        if (!board_burn(c)) {
            message("TROP DE PORTES (32 AU PLUS)");
            return;
        }
        board_compile();
        board_palette();
        board_update();
        message(board_saved() ? "PUCE GRAVEE" : "GRAVEE (PAS SAUVEE)");
        return;
    }
    if (!chip_count[c]) {
        message("PUCE VIDE : GRAVER D'ABORD");
        return;
    }
    if (mode == M_OPEN) {
        mode = M_EDIT;
        memcpy(parts, chip_layout[c], sizeof parts);
        memcpy(wires, chip_layout[c] + sizeof parts, sizeof wires);
        held_kind = 0u;
        message("PUCE OUVERTE");
        board_compile();
        board_draw();
        return;
    }
    held_kind = K_CHIP0 + c;
    message("CLIQUER UNE CASE VIDE");
}

void board_click(unsigned char x, unsigned char y)
{
    static unsigned char k;
    if (y >= PAL_Y && y < PAL_Y + PAL_H) { click_palette(x); return; }
    if (y < GY || y >= GY + ROWS * CH) return;
    if (x < GX) {
        for (k = 0u; k < TERMS; ++k) {
            if ((unsigned char)(y - term_y(k)) >= 11u) continue;
            if (x >= 10u) {
                click_source(k);
            } else if (screen == S_LAB) {
                lab_inputs[k] ^= 1u;
                in_drawn[k] = lab_inputs[k];
                draw_terminal(k, 0u, lab_inputs[k]);
            }
        }
        return;
    }
    if (x >= GX + COLS * CW) {
        for (k = 0u; k < TERMS; ++k)
            if ((unsigned char)(y - term_y(k)) < 11u) click_sink(k);
        return;
    }
    x -= GX; y -= GY;
    click_cell(x / CW, y / CH, x % CW, y % CH);
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
    message("MAINS VIDES");
}

void board_clear_all(void)
{
    board_clear();
    held_kind = 0u; held_part = NONE; held_src = NONE;
    board_compile();
    board_draw();
}
