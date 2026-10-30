/* Robot Space Station — the drones and the technician seen in profile,
 * facing the way they last went: tables of rectangles drawn facing east,
 * mirrored to face west. Collisions keep their boxes (zone.h, ui.h). */
#include "dhgr.h"
#include "ui.h"
#include "zone.h"

/* Colours above 15: the drone's own (A light blue, B aqua), the antenna's
 * tip (yellow while the radio sends), the claw (white while it grabs), the
 * jets (orange while a motor runs). */
#define C_BODY 16u
#define C_TIP 17u
#define C_CLAW 18u
#define C_JET 19u
static unsigned char special[4];

/* x, y, width, height, colour; facing east. */
static const unsigned char drone_rects[][5] = {
    {3, 0, 1, 2, C_TIP},                /* antenna */
    {2, 2, 6, 4, C_BODY},               /* the dome */
    {5, 3, 3, 2, DHGR_DARKBLUE},        /* the visor, in front */
    {6, 3, 2, 1, DHGR_WHITE},           /* its eye */
    {1, 6, 8, 4, DHGR_GRAY2},           /* the body */
    {2, 7, 5, 1, C_BODY},               /* a stripe */
    {7, 8, 3, 1, C_CLAW},               /* the arm and its claw */
    {2, 10, 2, 2, C_JET},               /* hover jets */
    {6, 10, 2, 2, C_JET},
};
#define DRONE_RECTS (sizeof drone_rects / sizeof drone_rects[0])

static const unsigned char tech_rects[][5] = {
    {1, 0, 3, 3, DHGR_WHITE},           /* helmet */
    {3, 1, 2, 1, DHGR_AQUA},            /* visor, in front */
    {0, 3, 1, 3, DHGR_GRAY2},           /* backpack */
    {1, 3, 3, 4, DHGR_ORANGE},          /* suit */
    {4, 4, 1, 1, DHGR_WHITE},           /* glove */
    {1, 7, 1, 2, DHGR_GRAY2},           /* legs apart (standing, or a step) */
    {3, 7, 1, 2, DHGR_GRAY2},
    {2, 7, 1, 2, DHGR_GRAY2},           /* legs together (the other step) */
};

/* n rectangles from r at x0, y0 in a box w wide; west: mirrored. */
static const unsigned char *r;
static unsigned char n, x0, y0, w, west;
static void paint(void)
{
    static unsigned char c, x;
    for (; n; --n, r += 5) {
        c = r[4];
        if (c >= C_BODY) c = special[c - C_BODY];
        x = r[0];
        if (west) x = w - x - r[2];
        dhgr_fill_rect(x0 + x, y0 + r[1], r[2], r[3], c);
    }
}

static unsigned char drone_west[DRONES];

void __fastcall__ drone_paint(unsigned char d)
{
    static unsigned char *t;
    x0 = drone_x[d]; y0 = drone_y[d] + ROOM_Y; t = thrust[d];
    /* thruster W pushes east: it faces east; E, west; else as it was */
    if (t[3] != t[1]) drone_west[d] = t[1];
    west = drone_west[d];
    special[0] = d ? DHGR_AQUA : DHGR_LIGHTBLUE;
    special[1] = t[5] ? DHGR_YELLOW : DHGR_GRAY2;
    special[2] = t[4] ? DHGR_WHITE : DHGR_GRAY1;
    special[3] = t[0] | t[1] | t[2] | t[3] ? DHGR_ORANGE : DHGR_GRAY1;
    dhgr_fill_rect(x0, y0, DRONE_W, DRONE_H, DHGR_BLACK);
    r = drone_rects[0]; n = DRONE_RECTS; w = DRONE_W;
    paint();
    /* pushed sideways: the exhaust behind it */
    if (t[3] != t[1]) dhgr_fill_rect(west ? x0 + DRONE_W - 1u : x0, y0 + 7u, 1, 2, DHGR_ORANGE);
}

/* The technician faces the way he last walked; walking, his legs swap
 * every two pixels (tech_rects: the body, legs apart, legs together). */
void __fastcall__ tech_paint(unsigned char x, unsigned char y)
{
    static unsigned char last_x, last_y, face, step;
    if (x != last_x) face = x < last_x;
    step = (x != last_x || y != last_y) && ((x + y) & 2u);
    last_x = x0 = x; last_y = y0 = y;
    west = face; w = ACT_W;
    r = tech_rects[0]; n = step ? 5u : 7u;
    paint();
    if (step) { r = tech_rects[7]; n = 1u; paint(); }
}
