/* Robot Space Station — the test zone and its missions (docs/SPEC.md).
 * zone_tick(), zone_doors() and zone_won() transcribe Zone in
 * tools/model.py. Drone B's board lives aside (board_swap) except while
 * the technician is inside it (cur_drone). */
#include <string.h>
#include "dhgr.h"
#include "sim.h"
#include "ui.h"
#include "zone.h"
#include "room.h"
#include "prodos.h"

#define ROOM_COLS 20u
#define ROOM_ROWS 18u
#define ROOM_W 140u
#define N 0u
#define E 1u
#define S 2u
#define W 3u
#define CLAW 4u
#define RADIO 5u
#define T_FLOOR 0u
#define T_WALL 1u
#define T_GRATE 2u
#define T_CHARGER 3u
#define T_DOOR 4u
#define T_PLATE 5u
#define T_DOOR2 6u
#define T_PLATE2 7u
#define T_TUNNEL 8u
#define O_CELL 1u
#define GOAL_CELL 1u
#define GOAL_TECH 2u
#define TECH_W 5u
#define TECH_H 9u

unsigned char mission, drone_n;
unsigned char drone_x[DRONES], drone_y[DRONES];
unsigned char holding[DRONES] = {NONE, NONE};
unsigned char thrust[DRONES][6];
unsigned char obj_n, obj_kind[OBJECTS], obj_x[OBJECTS], obj_y[OBJECTS];
unsigned char door_open[2];

#pragma bss-name (push, "LOWBSS")
static unsigned char tiles[ROOM_COLS * ROOM_ROWS];   /* this mission's, unpacked */
#pragma bss-name (pop)
static unsigned char div7[ROOM_W];
static unsigned char drawn_x[DRONES] = {NONE, NONE}, drawn_y[DRONES], drawn_thrust[DRONES][6];
static unsigned char drawn_obj[DRONES] = {NONE, NONE}, drawn_ox[DRONES], drawn_oy[DRONES];
static unsigned char bx, by, bw, bh;      /* the box side_blocked() looks at */
static unsigned char di;                  /* the drone moving, NONE: the technician */

void zone_init(void)
{
    static unsigned char x, q, r;
    for (x = 0u, q = 0u, r = 0u; x < ROOM_W; ++x) {
        div7[x] = q;
        if (++r == 7u) { r = 0u; ++q; }
    }
}

/* -- RSS.ROOMS (tools/gen_room.py): mission m's record at m * 256 ---------- */

extern unsigned char iobuf[1024];                /* main.c, the ProDOS buffer */
static const char rooms_name[] = "\x09RSS.ROOMS";
static unsigned char p_open[6] = {3};            /* path, buffer, ref */
static unsigned char p_mark[5] = {2};            /* ref, mark (3 bytes) */
static unsigned char p_read[8] = {4};            /* ref, buffer, request, done */
static unsigned char p_close[2] = {1};           /* ref */

static unsigned char __fastcall__ mli(unsigned char command, void *params)
{
    prodos_command = command;
    prodos_params = params;
    return prodos_call();
}

/* The record's 199 bytes land at the end of tiles[]: the starts, then the
 * packed tiles, unpacked in place below them. 1 = read. */
static unsigned char __fastcall__ read_room(unsigned char m)
{
    static unsigned char error;
    *(const char **)(p_open + 1) = rooms_name;
    *(unsigned char **)(p_open + 3) = iobuf;
    if (mli(PD_OPEN, p_open)) return 0u;
    p_mark[1] = p_read[1] = p_close[1] = p_open[5];
    p_mark[2] = 0u; p_mark[3] = m; p_mark[4] = 0u;          /* m * 256 */
    *(unsigned char **)(p_read + 2) = tiles + sizeof tiles - 180u - ROOM_STARTS;
    *(unsigned *)(p_read + 4) = 180u + ROOM_STARTS;
    error = mli(0xCEu, p_mark);                             /* SET_MARK */
    if (!error) error = mli(PD_READ, p_read);
    if (!error && *(unsigned *)(p_read + 6) != 180u + ROOM_STARTS) error = 1u;
    mli(PD_CLOSE, p_close);
    return !error;
}

unsigned char mission_count(void) { return MISSIONS; }
const char *__fastcall__ mission_name_of(unsigned char m) { return mission_names[m]; }

unsigned char __fastcall__ zone_load(unsigned char m)
{
    static unsigned char starts[ROOM_STARTS];
    static const unsigned char *s;
    static unsigned char i, *t, b;
    if (!read_room(m)) return 0u;
    mission = m;
    memcpy(starts, tiles + sizeof tiles - 180u - ROOM_STARTS, ROOM_STARTS);
    /* Byte i of the packed tiles (at 180 + i) gives tiles 2i and 2i + 1:
     * always written below what is still to be read. */
    for (i = 0u, s = tiles + 180u, t = tiles; i < 180u; ++i, ++s) {
        b = *s;
        *t++ = b & 15u;
        *t++ = b >> 4;
    }
    s = starts;
    drone_x[0] = s[0]; drone_y[0] = s[1];
    drone_x[1] = s[2]; drone_y[1] = s[3];
    drone_n = s[2] == NONE ? 1u : 2u;
    act_x = s[4]; act_y = s[5] + ROOM_Y;
    obj_n = s[6];
    for (i = 0u, s += 7; i < obj_n; ++i, s += 3) {
        obj_kind[i] = s[0]; obj_x[i] = s[1]; obj_y[i] = s[2];
    }
    holding[0] = holding[1] = NONE;
    memset(thrust, 0, sizeof thrust);
    door_open[0] = door_open[1] = 0u;
    return 1u;
}

/* Outside the room counts as wall (x-1 and y-1 wrap to 255). */
static unsigned char __fastcall__ tile_raw(unsigned char x, unsigned char y)
{
    if (x >= ROOM_W || y >= ROOM_H) return T_WALL;
    return tiles[(unsigned)(y >> 3) * ROOM_COLS + div7[x]];
}

/* What blocks the mover di: a closed door is a wall, an open one floor;
 * a tunnel is a wall for the drones only. */
static unsigned char __fastcall__ tile_at(unsigned char x, unsigned char y)
{
    static unsigned char t;
    t = tile_raw(x, y);
    if (t == T_DOOR) return door_open[0] ? T_FLOOR : T_WALL;
    if (t == T_DOOR2) return door_open[1] ? T_FLOOR : T_WALL;
    if (t == T_TUNNEL) return di == NONE ? T_FLOOR : T_WALL;
    return t;
}

/* -- doors (tools/model.py Zone.update_doors) ------------------------------- */

static unsigned char opens[2];

/* The box bx, by, bw, bh: which groups it opens (plate under its centre,
 * or a door of the group under it). */
static void box_opens(void)
{
    static unsigned char tx, ty, tx1, ty1, t;
    t = tile_raw(bx + (bw >> 1), by + (bh >> 1));
    if (t == T_PLATE) opens[0] = 1u;
    if (t == T_PLATE2) opens[1] = 1u;
    tx1 = div7[bx + bw - 1u]; ty1 = (by + bh - 1u) >> 3;
    for (ty = by >> 3; ty <= ty1; ++ty)
        for (tx = div7[bx]; tx <= tx1; ++tx) {
            t = tiles[(unsigned)ty * ROOM_COLS + tx];
            if (t == T_DOOR) opens[0] = 1u;
            if (t == T_DOOR2) opens[1] = 1u;
        }
}

/* Recompute door_open; 1 if it changed. The technician counts while he
 * is in the room (the zone screen), not inside a drone. */
unsigned char zone_doors(void)
{
    static unsigned char i, changed;
    opens[0] = opens[1] = 0u;
    bw = DRONE_W; bh = DRONE_H;
    for (i = 0u; i < drone_n; ++i) {
        bx = drone_x[i]; by = drone_y[i];
        box_opens();
    }
    bw = OBJ_W; bh = OBJ_H;
    for (i = 0u; i < obj_n; ++i) {
        bx = obj_x[i]; by = obj_y[i];
        box_opens();
    }
    if (screen == S_ZONE) {
        bx = act_x; by = act_y - ROOM_Y; bw = TECH_W; bh = TECH_H;
        box_opens();
    }
    changed = opens[0] != door_open[0] || opens[1] != door_open[1];
    door_open[0] = opens[0];
    door_open[1] = opens[1];
    return changed;
}

/* -- drones ----------------------------------------------------------------- */

/* For drone di: walls, the objects it does not hold, the other drone. */
static unsigned char obstacle(unsigned char x, unsigned char y)
{
    static unsigned char i;
    if (tile_at(x, y) == T_WALL) return 1u;
    for (i = 0u; i < obj_n; ++i)
        if (i != holding[di] && (unsigned char)(x - obj_x[i]) < OBJ_W
            && (unsigned char)(y - obj_y[i]) < OBJ_H) return 1u;
    if (drone_n == 2u) {
        i = di ^ 1u;
        if ((unsigned char)(x - drone_x[i]) < DRONE_W && (unsigned char)(y - drone_y[i]) < DRONE_H)
            return 1u;
    }
    return 0u;
}

/* Something right next to that side of the box bx, by, bw, bh? */
static unsigned char __fastcall__ side_blocked(unsigned char side)
{
    static unsigned char c;
    if (side == N || side == S) {
        c = side == N ? by - 1u : by + bh;
        return obstacle(bx, c) | obstacle(bx + (bw >> 1), c) | obstacle(bx + bw - 1u, c);
    }
    c = side == W ? bx - 1u : bx + bw;
    return obstacle(c, by) | obstacle(c, by + (bh >> 1)) | obstacle(c, by + bh - 1u);
}

static void drone_box(void) { bx = drone_x[di]; by = drone_y[di]; bw = DRONE_W; bh = DRONE_H; }

/* Drone di, and the object it holds, can move one pixel that way. */
static unsigned char __fastcall__ free_side(unsigned char side)
{
    static unsigned char h;
    drone_box();
    if (side_blocked(side)) return 0u;
    h = holding[di];
    if (h != NONE) {
        bx = obj_x[h]; by = obj_y[h]; bw = OBJ_W; bh = OBJ_H;
        if (side_blocked(side)) return 0u;
    }
    return 1u;
}

static void move(signed char dx, signed char dy)
{
    static unsigned char h;
    drone_x[di] += dx; drone_y[di] += dy;
    h = holding[di];
    if (h != NONE) { obj_x[h] += dx; obj_y[h] += dy; }
}

unsigned char zone_tick(void)
{
    static unsigned char d, k, i, ox, oy, oh, redraw, heard[DRONES], *t, bumps;
    static unsigned char bumped[DRONES], sending[DRONES];
    if (zone_doors() && screen == S_ZONE) zone_draw_doors();
    heard[0] = drone_n == 2u ? thrust[1][RADIO] : 0u;
    heard[1] = thrust[0][RADIO];
    /* Every board turns on the positions before any drone moves. */
    for (d = 0u; d < drone_n; ++d) {
        if (d != cur_drone) board_swap_run();
        di = d;
        drone_box();
        bumps = 0u;
        for (k = 0u; k < 4u; ++k) bumps |= (values[k] = side_blocked(k)) << k;
        if (bumps & ~bumped[d]) sfx(SFX_CONTACT);   /* a new contact */
        bumped[d] = bumps;
        values[4] = holding[d] != NONE;
        values[RADIO] = heard[d];
        board_tick();
        for (k = 0u; k < 6u; ++k) thrust[d][k] = sink_value(k);
        if (thrust[d][RADIO] && !sending[d]) sfx(SFX_RADIO);
        sending[d] = thrust[d][RADIO];
        if (d != cur_drone) board_swap_run();
    }
    redraw = 0u;
    for (d = 0u; d < drone_n; ++d) {
        di = d;
        t = thrust[d];
        ox = drone_x[d]; oy = drone_y[d]; oh = holding[d];
        if (!t[CLAW]) {
            holding[d] = NONE;
        } else if (holding[d] == NONE) {
            for (i = 0u; i < obj_n; ++i)
                if (i != holding[d ^ 1u] && obj_x[i] <= drone_x[d] + DRONE_W
                    && drone_x[d] <= obj_x[i] + OBJ_W && obj_y[i] <= drone_y[d] + DRONE_H
                    && drone_y[d] <= obj_y[i] + OBJ_H) {
                    holding[d] = i;
                    break;
                }
        }
        if (holding[d] != oh) sfx(holding[d] == NONE ? SFX_DROP : SFX_GRAB);
        if (t[W] > t[E] && free_side(E)) move(1, 0);
        else if (t[W] < t[E] && free_side(W)) move(-1, 0);
        if (t[N] > t[S] && free_side(S)) move(0, 1);
        else if (t[N] < t[S] && free_side(N)) move(0, -1);
        if (ox != drone_x[d] || oy != drone_y[d] || oh != holding[d]
            || memcmp(t, drawn_thrust[d], 6)) redraw |= 1u << d;
    }
    di = NONE;
    return redraw;
}

unsigned char zone_won(void)
{
    static unsigned char i, goal;
    goal = mission_goals[mission];
    if (goal == GOAL_CELL) {
        for (i = 0u; i < obj_n; ++i)
            if (obj_kind[i] == O_CELL && i != holding[0] && i != holding[1]
                && tile_raw(obj_x[i] + (OBJ_W >> 1), obj_y[i] + (OBJ_H >> 1)) == T_CHARGER)
                return 1u;
        return 0u;
    }
    if (goal == GOAL_TECH)
        return screen == S_ZONE
            && tile_raw(act_x + (TECH_W >> 1), act_y - ROOM_Y + (TECH_H >> 1)) == T_CHARGER;
    return tile_raw(drone_x[0] + (DRONE_W >> 1), drone_y[0] + (DRONE_H >> 1)) == T_CHARGER;
}

/* -- drawing --------------------------------------------------------------- */

static void __fastcall__ draw_tile(unsigned char tx, unsigned char ty)
{
    static unsigned char x, y, t, open;
    x = tx * 7u; y = ROOM_Y + (ty << 3);
    t = tiles[(unsigned)ty * ROOM_COLS + tx];
    if (t == T_WALL || t == T_TUNNEL) {
        dhgr_fill_rect(x, y, 7, 8, DHGR_GRAY1);
        dhgr_fill_rect(x, y + 7u, 7, 1, DHGR_DARKBLUE);
        if (t == T_TUNNEL) dhgr_fill_rect(x + 2u, y, 3, 8, DHGR_BLACK);   /* a crawlway */
    } else if (t == T_DOOR || t == T_DOOR2) {
        /* Closed: shutters (orange, or violet for the second group). */
        open = door_open[t == T_DOOR2];
        dhgr_fill_rect(x, y, 7, 8, open ? DHGR_BLACK : t == T_DOOR ? DHGR_ORANGE : DHGR_VIOLET);
        dhgr_fill_rect(x, y, 1, 8, DHGR_BROWN);
        dhgr_fill_rect(x + 6u, y, 1, 8, DHGR_BROWN);
    } else {
        dhgr_fill_rect(x, y, 7, 8, t == T_CHARGER ? DHGR_DARKGREEN : DHGR_BLACK);
        if (t == T_PLATE || t == T_PLATE2) {
            open = door_open[t == T_PLATE2];
            dhgr_fill_rect(x + 1u, y + 2u, 5, 4, open ? DHGR_YELLOW
                           : t == T_PLATE ? DHGR_BROWN : DHGR_MAGENTA);
        } else if (t == T_GRATE) {
            dhgr_fill_rect(x, y + 1u, 7, 1, DHGR_DARKBLUE);
            dhgr_fill_rect(x, y + 5u, 7, 1, DHGR_DARKBLUE);
        } else if (t == T_CHARGER) {
            dhgr_fill_rect(x + 3u, y + 2u, 1, 4, DHGR_GREEN);
        }
    }
}

/* Put the room's background back under a box (room pixels). */
static void erase_box(unsigned char x, unsigned char y, unsigned char w, unsigned char h)
{
    static unsigned char tx, ty, tx1, ty1;
    tx1 = div7[x + w - 1u]; ty1 = (y + h - 1u) >> 3;
    for (ty = y >> 3; ty <= ty1; ++ty)
        for (tx = div7[x]; tx <= tx1; ++tx) draw_tile(tx, ty);
}

static void __fastcall__ draw_object(unsigned char i)
{
    static unsigned char x, y;
    x = obj_x[i]; y = obj_y[i] + ROOM_Y;
    if (obj_kind[i] == O_CELL) {
        dhgr_fill_rect(x, y, OBJ_W, OBJ_H, DHGR_YELLOW);
        dhgr_fill_rect(x + 1u, y + 3u, 5, 2, DHGR_ORANGE);
    } else {
        dhgr_fill_rect(x, y, OBJ_W, OBJ_H, DHGR_BROWN);
    }
}

static void __fastcall__ draw_hull(unsigned char d)
{
    static unsigned char x, y, *t;
    x = drone_x[d]; y = drone_y[d] + ROOM_Y; t = thrust[d];
    dhgr_fill_rect(x, y, DRONE_W, DRONE_H, d ? DHGR_AQUA : DHGR_LIGHTBLUE);
    dhgr_fill_rect(x + 1u, y + 1u, DRONE_W - 2u, DRONE_H - 2u, DHGR_BLACK);
    dhgr_fill_rect(x + 3u, y + 4u, 4, 4, t[CLAW] ? DHGR_WHITE : d ? DHGR_GREEN : DHGR_VIOLET);
    if (t[RADIO]) dhgr_fill_rect(x + 4u, y + 2u, 2, 1, DHGR_YELLOW);   /* transmitting */
    /* A lit thruster: an orange bar on its side, inside the hull. */
    if (t[N]) dhgr_fill_rect(x + 2u, y + 1u, 6, 1, DHGR_ORANGE);
    if (t[S]) dhgr_fill_rect(x + 2u, y + DRONE_H - 2u, 6, 1, DHGR_ORANGE);
    if (t[W]) dhgr_fill_rect(x + 1u, y + 2u, 1, 8, DHGR_ORANGE);
    if (t[E]) dhgr_fill_rect(x + DRONE_W - 2u, y + 2u, 1, 8, DHGR_ORANGE);
    drawn_x[d] = drone_x[d]; drawn_y[d] = drone_y[d];
    memcpy(drawn_thrust[d], t, 6);
    drawn_obj[d] = holding[d];
    if (holding[d] != NONE) {
        drawn_ox[d] = obj_x[holding[d]]; drawn_oy[d] = obj_y[holding[d]];
    }
}

/* Drones in mask moved: erase their old boxes (and held objects), then
 * draw the objects and every drone again (an erased tile may cut a
 * neighbour). */
void __fastcall__ drone_draw(unsigned char mask)
{
    static unsigned char d, i, x, y;
    if (drone_n == 1u && !obj_n && drawn_x[0] != NONE) {
        /* Old and new boxes, with a tile of margin for erase_box(). */
        x = drawn_x[0] < drone_x[0] ? drawn_x[0] : drone_x[0];
        y = drawn_y[0] < drone_y[0] ? drawn_y[0] : drone_y[0];
        begin_draw_box(x > 7u ? x - 7u : 0u, y + ROOM_Y > 8u ? y + ROOM_Y - 8u : 0u,
                       x + DRONE_W + 8u, y + ROOM_Y + DRONE_H + 9u);
    } else {
        begin_draw();
    }
    for (d = 0u; d < drone_n; ++d) {
        if (!(mask & (1u << d))) continue;
        if (drawn_x[d] != NONE) erase_box(drawn_x[d], drawn_y[d], DRONE_W, DRONE_H);
        if (drawn_obj[d] != NONE) erase_box(drawn_ox[d], drawn_oy[d], OBJ_W, OBJ_H);
    }
    for (i = 0u; i < obj_n; ++i) draw_object(i);
    for (d = 0u; d < drone_n; ++d) draw_hull(d);
}

/* Doors and plates after door_open changed. */
void zone_draw_doors(void)
{
    static unsigned char tx, ty, t;
    begin_draw();
    for (ty = 0u; ty < ROOM_ROWS; ++ty)
        for (tx = 0u; tx < ROOM_COLS; ++tx) {
            t = tiles[(unsigned)ty * ROOM_COLS + tx];
            if (t >= T_DOOR && t <= T_PLATE2) draw_tile(tx, ty);
        }
}

void zone_draw(void)
{
    static unsigned char tx, ty;
    static char title[2];
    zone_doors();                   /* the caller cleared the screen */
    title[0] = '1' + mission; title[1] = 0;
    dhgr_puts_small("MISSION", 0, 1);
    dhgr_puts_small(title, 40, 1);
    dhgr_puts_small(mission_names[mission], 50, 1);
    ui_latch();
    for (ty = 0u; ty < ROOM_ROWS; ++ty) {
        ui_latch();
        for (tx = 0u; tx < ROOM_COLS; ++tx)
            if (tiles[(unsigned)ty * ROOM_COLS + tx]) draw_tile(tx, ty);
    }
    drawn_x[0] = drawn_x[1] = NONE;
    drawn_obj[0] = drawn_obj[1] = NONE;
    drone_draw(3u);
}

/* -- the technician in the room -------------------------------------------- */

/* Room point x, y: wall, grate, closed door or object (he cannot pass)? */
static unsigned char __fastcall__ tech_blocked(unsigned char x, unsigned char y)
{
    static unsigned char i, t;
    t = tile_at(x, y);
    if (t == T_WALL || t == T_GRATE) return 1u;
    for (i = 0u; i < obj_n; ++i)
        if ((unsigned char)(x - obj_x[i]) < OBJ_W && (unsigned char)(y - obj_y[i]) < OBJ_H)
            return 1u;
    return 0u;
}

/* The 5 x 9 technician at screen x, y. */
static unsigned char __fastcall__ tech_free(unsigned char x, unsigned char y)
{
    di = NONE;
    y -= ROOM_Y;
    return !(tech_blocked(x, y) | tech_blocked(x + 4u, y) | tech_blocked(x, y + 4u)
             | tech_blocked(x + 4u, y + 4u) | tech_blocked(x, y + 8u) | tech_blocked(x + 4u, y + 8u));
}

unsigned char tech_step(unsigned char x, unsigned char y)
{
    static unsigned char moved;
    moved = 0u;
    if (act_x < x && tech_free(act_x + 1u, act_y)) { ++act_x; moved = 1u; }
    else if (act_x > x && tech_free(act_x - 1u, act_y)) { --act_x; moved = 1u; }
    if (act_y < y && tech_free(act_x, act_y + 1u)) { ++act_y; moved = 1u; }
    else if (act_y > y && tech_free(act_x, act_y - 1u)) { --act_y; moved = 1u; }
    return moved;
}

unsigned char tech_touches_drone(void)
{
    static unsigned char d, dy;
    for (d = 0u; d < drone_n; ++d) {
        dy = drone_y[d] + ROOM_Y;
        if (act_x + ACT_W > drone_x[d] && act_x < drone_x[d] + DRONE_W
            && act_y + ACT_H > dy && act_y < dy + DRONE_H) return d + 1u;
    }
    return 0u;
}

/* Out of drone d: the first free spot east, west, south or north of it. */
void __fastcall__ tech_beside_drone(unsigned char d)
{
    static unsigned char dx, dy;
    dx = drone_x[d]; dy = drone_y[d] + ROOM_Y;
    act_x = dx + DRONE_W + 1u; act_y = dy;
    if (tech_free(act_x, act_y) && !tech_touches_drone()) return;
    act_x = dx - ACT_W - 1u;
    if (dx > ACT_W && tech_free(act_x, act_y) && !tech_touches_drone()) return;
    act_x = dx; act_y = dy + DRONE_H + 1u;
    if (tech_free(act_x, act_y) && !tech_touches_drone()) return;
    act_y = dy - ACT_H - 1u;
}
