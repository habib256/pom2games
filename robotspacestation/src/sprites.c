/* Robot Space Station — what the room shows, as shapes of rectangles for
 * the flicker-free DHGR compositor (dev/lib/hgrc dhgr_spr_*): the tiles,
 * the objects, the drones and the technician in profile, facing the way
 * they last went (drawn facing east, mirrored to face west). Each update
 * writes every changed screen byte once with its final value: nothing is
 * erased first. Collisions keep their boxes (zone.h, ui.h). */
#include "dhgr.h"
#include "ui.h"
#include "zone.h"

#define C_BODY 16u              /* the slot's palette (dhgr_spr_palette) */
#define C_TIP 17u
#define C_CLAW 18u
#define C_JET 19u

/* x, y, width, height, colour; facing east. The exhaust last: drone_jet_s
 * (pushed sideways, the jet behind it). */
static const unsigned char drone_r[] = {
    3, 0, 1, 2, C_TIP,                  /* antenna */
    2, 2, 6, 4, C_BODY,                 /* the dome */
    5, 3, 3, 2, DHGR_DARKBLUE,          /* the visor, in front */
    6, 3, 2, 1, DHGR_WHITE,             /* its eye */
    1, 6, 8, 4, DHGR_GRAY2,             /* the body */
    2, 7, 5, 1, C_BODY,                 /* a stripe */
    7, 8, 3, 1, C_CLAW,                 /* the arm and its claw */
    2, 10, 2, 2, C_JET,                 /* hover jets */
    6, 10, 2, 2, C_JET,
    0, 7, 1, 2, DHGR_ORANGE,            /* the exhaust */
};
const dhgr_shape_t drone_s = {DHGR_SHAPE_RECTS, DRONE_W, DRONE_H, 9, drone_r};
const dhgr_shape_t drone_jet_s = {DHGR_SHAPE_RECTS, DRONE_W, DRONE_H, 10, drone_r};

/* Legs apart (standing, or a step), the body, legs together (the other
 * step): standing = the first 7, stepping = the last 6. */
static const unsigned char tech_r[] = {
    1, 7, 1, 2, DHGR_GRAY2,             /* legs apart */
    3, 7, 1, 2, DHGR_GRAY2,
    1, 0, 3, 3, DHGR_WHITE,             /* helmet */
    3, 1, 2, 1, DHGR_AQUA,              /* visor, in front */
    0, 3, 1, 3, DHGR_GRAY2,             /* backpack */
    1, 3, 3, 4, DHGR_ORANGE,            /* suit */
    4, 4, 1, 1, DHGR_WHITE,             /* glove */
    2, 7, 1, 2, DHGR_GRAY2,             /* legs together */
};
const dhgr_shape_t tech_s = {DHGR_SHAPE_RECTS, ACT_W, ACT_H, 7, tech_r};
const dhgr_shape_t tech_step_s = {DHGR_SHAPE_RECTS, ACT_W, ACT_H, 6, tech_r + 10};

static const unsigned char cell_r[] = {
    0, 0, OBJ_W, OBJ_H, DHGR_YELLOW,    /* a power cell */
    1, 3, 5, 2, DHGR_ORANGE,
};
static const unsigned char crate_r[] = {0, 0, OBJ_W, OBJ_H, DHGR_BROWN};
const dhgr_shape_t cell_s = {DHGR_SHAPE_RECTS, OBJ_W, OBJ_H, 2, cell_r};
const dhgr_shape_t crate_s = {DHGR_SHAPE_RECTS, OBJ_W, OBJ_H, 1, crate_r};

/* The tiles, 7 x 8 (zone.c T_*). Floor = the grate's first rectangle,
 * wall = the tunnel's first two. */
static const unsigned char grate_r[] = {
    0, 0, 7, 8, DHGR_BLACK, 0, 1, 7, 1, DHGR_DARKBLUE, 0, 5, 7, 1, DHGR_DARKBLUE,
};
static const unsigned char tunnel_r[] = {
    0, 0, 7, 8, DHGR_GRAY1, 0, 7, 7, 1, DHGR_DARKBLUE,
    2, 0, 3, 8, DHGR_BLACK,             /* a crawlway */
};
static const unsigned char charger_r[] = {0, 0, 7, 8, DHGR_DARKGREEN, 3, 2, 1, 4, DHGR_GREEN};
/* Doors: a shutter (orange, or violet for the second group) or open
 * (black) between brown jambs; three rectangles each, overlapping here. */
static const unsigned char door_r[] = {
    1, 0, 5, 8, DHGR_ORANGE, 0, 0, 1, 8, DHGR_BROWN, 6, 0, 1, 8, DHGR_BROWN,
    1, 0, 5, 8, DHGR_BLACK, 0, 0, 1, 8, DHGR_BROWN, 6, 0, 1, 8, DHGR_BROWN,
    1, 0, 5, 8, DHGR_VIOLET,
};
/* Plates: brown (or magenta) while nothing presses them, yellow if so. */
static const unsigned char plate_r[] = {
    0, 0, 7, 8, DHGR_BLACK, 1, 2, 5, 4, DHGR_BROWN,
    0, 0, 7, 8, DHGR_BLACK, 1, 2, 5, 4, DHGR_YELLOW,
    0, 0, 7, 8, DHGR_BLACK, 1, 2, 5, 4, DHGR_MAGENTA,
};
const dhgr_shape_t tile_s[] = {
    {DHGR_SHAPE_RECTS, 7, 8, 1, grate_r},               /* 0 floor */
    {DHGR_SHAPE_RECTS, 7, 8, 2, tunnel_r},              /* 1 wall */
    {DHGR_SHAPE_RECTS, 7, 8, 3, grate_r},               /* 2 grate */
    {DHGR_SHAPE_RECTS, 7, 8, 2, charger_r},             /* 3 charger */
    {DHGR_SHAPE_RECTS, 7, 8, 3, door_r},                /* 4 door, closed */
    {DHGR_SHAPE_RECTS, 7, 8, 2, plate_r},               /* 5 plate */
    {DHGR_SHAPE_RECTS, 7, 8, 3, door_r + 20},           /* 6 second door */
    {DHGR_SHAPE_RECTS, 7, 8, 2, plate_r + 20},          /* 7 second plate */
    {DHGR_SHAPE_RECTS, 7, 8, 3, tunnel_r},              /* 8 tunnel */
    {DHGR_SHAPE_RECTS, 7, 8, 3, door_r + 5},            /* 9 a door open */
    {DHGR_SHAPE_RECTS, 7, 8, 2, plate_r + 10},          /* 10 a plate pressed */
};
const dhgr_shape_t *tile_set[9];

/* src/sprites_asm.s: his shape and facing for act_x, act_y. */
extern const dhgr_shape_t *pose_s;
extern unsigned char pose_f;
void tech_pose(void);

/* The technician on the board screen (ui.c actor_show: background saved). */
void __fastcall__ tech_paint(unsigned char x, unsigned char y)
{
    static const unsigned char *r;
    static unsigned char n, rx;
    tech_pose();
    r = pose_s->data;
    for (n = pose_s->n; n; --n, r += 5) {
        rx = r[0];
        if (pose_f) rx = ACT_W - rx - r[2];
        dhgr_fill_rect(x + rx, y + r[1], r[2], r[3], r[4]);
    }
}
