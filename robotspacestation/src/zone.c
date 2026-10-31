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

#pragma bss-name (push, "LOWBSS")                 /* (MLI READ: only below $2000) */
unsigned char tiles[ROOM_COLS * ROOM_ROWS];   /* this mission's, unpacked (sprites.c: the map) */
#pragma bss-name (pop)
extern const unsigned char dhgr_cellbyte[140];   /* dev/lib/hgrc: x -> (4x)/7 */
#define div7(x) (dhgr_cellbyte[x] >> 2)             /* x / 7 */
static unsigned char bx, by, bw, bh;      /* the box side_blocked() looks at */
static unsigned char di;                  /* the drone moving, NONE: the technician */
static unsigned char bumped[DRONES], sending[DRONES];   /* last turn's (sounds) */

void zone_init(void)
{
}

/* -- RSS.ROOMS (tools/gen_room.py): mission m's record at m * 256 ---------- */

extern unsigned char iobuf[1024];                /* main.c, the ProDOS buffer */
static const char rooms_name[] = "\x09RSS.ROOMS";

/* The record's 199 bytes land at the end of tiles[]: the starts, then the
 * packed tiles, unpacked in place below them. 1 = read. */
static unsigned char __fastcall__ read_room(unsigned char m)
{
    prodos_file_name = (void *)rooms_name;
    prodos_file_iobuf = iobuf;
    prodos_file_buffer = tiles + sizeof tiles - 180u - ROOM_STARTS;
    prodos_file_length = 180u + ROOM_STARTS;
    prodos_file_mark = (unsigned)m << 8;                    /* m * 256 */
    return !prodos_load_at() && prodos_file_actual == 180u + ROOM_STARTS;
}


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
    memset(bumped, 0, sizeof bumped);
    memset(sending, 0, sizeof sending);
    door_open[0] = door_open[1] = 0u;
    return 1u;
}

/* Outside the room counts as wall (x-1 and y-1 wrap to 255). */
static unsigned char __fastcall__ tile_raw(unsigned char x, unsigned char y)
{
    if (x >= ROOM_W || y >= ROOM_H) return T_WALL;
    return tiles[(unsigned)(y >> 3) * ROOM_COLS + div7(x)];
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
    tx1 = div7(bx + bw - 1u); ty1 = (by + bh - 1u) >> 3;
    for (ty = by >> 3; ty <= ty1; ++ty)
        for (tx = div7(bx); tx <= tx1; ++tx) {
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

void zone_tick(void)
{
    static unsigned char d, k, i, oh, heard[DRONES], *t, bumps;
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
    for (d = 0u; d < drone_n; ++d) {
        di = d;
        t = thrust[d];
        oh = holding[d];
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
    }
    di = NONE;
}

unsigned char zone_won(void)
{
    static unsigned char i, goal;
    goal = mission_goal(mission);
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

/* -- drawing: src/sprites.c's shapes through the compositor --------------- */

/* Doors and plates after door_open changed: their tiles swapped, their
 * cells redrawn (with whatever stands on them), an update every 16 cells
 * so that the damage list never fills up. */
void zone_draw_doors(void)
{
    static unsigned char tx, ty, t, n;
    sprites_doors();
    for (ty = 0u, n = 0u; ty < ROOM_ROWS; ++ty)
        for (tx = 0u; tx < ROOM_COLS; ++tx) {
            t = tiles[(unsigned)ty * ROOM_COLS + tx];
            if (t >= T_DOOR && t <= T_PLATE2) {
                dhgr_spr_invalidate(tx * 7u, ROOM_Y + (ty << 3), 7u, 8u);
                if (++n == 16u) { dhgr_spr_update(); n = 0u; }
            }
        }
}

/* The title, then the room one row of tiles at a time (a click is
 * latched between them) with everything on it. The caller cleared the
 * screen. */
void zone_draw(void)
{
    static unsigned char ty;
    static char title[3];
    zone_doors();
    title[0] = mission < 9u ? '1' + mission : '0' + (mission + 1u) / 10u;   /* 1..9, 10.. */
    title[1] = mission < 9u ? 0 : '0' + (mission + 1u) % 10u;
    title[2] = 0;
    dhgr_puts_small("MISSION", 0, 1);
    dhgr_puts_small(title, 40, 1);
    text_at(T_NAME + mission, 54, 1);
    sprites_room();
    zone_sprites();
    for (ty = 0u; ty < ROOM_ROWS; ++ty) {
        ui_latch();
        dhgr_spr_invalidate(0u, ROOM_Y + (ty << 3), ROOM_W, 8u);
        dhgr_spr_update();
    }
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

/* Where drone d's board (the loaded one) is about to send it: four turns
 * ahead (its sensors as they are), then put back. The technician steps
 * out behind it first, then to a side, in its way last. */
#pragma bss-name (push, "LOW8BSS")
static unsigned char kept_values[TERMINALS + BOARD_GATES];
#pragma bss-name (pop)
static unsigned char exit_order[4], order_n;
static void __fastcall__ add_side(unsigned char side)
{
    static unsigned char k;
    for (k = 0u; k < order_n; ++k)
        if (exit_order[k] == side) return;
    exit_order[order_n++] = side;
}

static void plan_exit(void)
{
    static const unsigned char sides[4] = {E, W, S, N};
    static unsigned char k, ahead, way_x, way_y;
    memcpy(kept_values, values, sizeof values);
    for (k = 0u; k < 4u; ++k) board_tick();
    /* thruster W (3) pushes east, N (0) south */
    way_x = sink_value(W) > sink_value(E) ? E : sink_value(W) < sink_value(E) ? W : NONE;
    way_y = sink_value(N) > sink_value(S) ? S : sink_value(N) < sink_value(S) ? N : NONE;
    memcpy(values, kept_values, sizeof values);
    order_n = 0u;
    if (way_x != NONE) add_side(way_x ^ 2u);                 /* behind it */
    if (way_y != NONE) add_side(way_y ^ 2u);
    for (ahead = 0u; ahead < 2u; ++ahead)
        for (k = 0u; k < 4u; ++k)
            if (ahead || (sides[k] != way_x && sides[k] != way_y)) add_side(sides[k]);
}

/* Out of drone d: the first free spot beside it, its sides tried in
 * plan_exit()'s order, centred on it. */
void __fastcall__ tech_beside_drone(unsigned char d)
{
    static unsigned char dx, dy, k, side;
    plan_exit();
    dx = drone_x[d]; dy = drone_y[d] + ROOM_Y;
    for (k = 0u; k < 4u; ++k) {
        side = exit_order[k];
        act_x = side == E ? dx + DRONE_W + 1u : side == W ? dx - ACT_W - 1u : dx + 2u;
        act_y = side == S ? dy + DRONE_H + 1u : side == N ? dy - ACT_H - 1u : dy + 1u;
        if (side == W && dx <= ACT_W) continue;
        if (side == N && dy <= ROOM_Y + ACT_H) continue;
        if (tech_free(act_x, act_y) && !tech_touches_drone()) return;
    }
}

/* -- what the pointer is on ----------------------------------------------- */

/* The text for screen point x, y in the room (0: nothing to say). */
unsigned char zone_hover(unsigned char x, unsigned char y)
{
    static unsigned char d, i, t;
    static const unsigned char tile_text[] = {
        0u, 0u, T_R_GRATE, T_R_CHARGER, T_R_DOOR, T_R_PLATE, T_R_DOOR2, T_R_PLATE2, T_R_TUNNEL
    };
    if ((unsigned char)(y - ROOM_Y) >= ROOM_H || x >= ROOM_W) return 0u;
    if ((unsigned char)(x - act_x) < ACT_W && (unsigned char)(y - act_y) < ACT_H) return T_R_TECH;
    y -= ROOM_Y;
    for (d = 0u; d < drone_n; ++d)
        if ((unsigned char)(x - drone_x[d]) < DRONE_W && (unsigned char)(y - drone_y[d]) < DRONE_H)
            return T_R_DRONE_A + d;
    for (i = 0u; i < obj_n; ++i)
        if ((unsigned char)(x - obj_x[i]) < OBJ_W && (unsigned char)(y - obj_y[i]) < OBJ_H)
            return obj_kind[i] == O_CELL ? T_R_CELL : T_R_CRATE;
    t = tile_raw(x, y);
    return t < sizeof tile_text ? tile_text[t] : 0u;
}

/* -- records (RSS3: persist.best) ------------------------------------------ */

static char gate_text[29];

static void __fastcall__ put_gates(unsigned char at, unsigned char n)
{
    if (n > 99u) n = 99u;                   /* (two drones: up to 128) */
    gate_text[at] = n >= 10u ? '0' + n / 10u : ' ';
    gate_text[at + 1u] = '0' + n % 10u;
}

const char *zone_won_text(void)
{
    static unsigned char gates, *best;
    gates = fl_count;                       /* both drones' boards */
    if (drone_n == 2u) { board_swap(); gates += fl_count; board_swap(); }
    best = &persist.best[mission];
    strcpy(gate_text, "DONE WITH    GATES");
    put_gates(10u, gates);
    if (gates == 1u) gate_text[17] = ' ';   /* GATE */
    if (!*best || gates + 1u < *best) {     /* best = gates + 1 (0: never won) */
        *best = gates + 1u;
        strcpy(gate_text + 18, " - RECORD!");
    }
    return gate_text;
}
