/* Robot Space Station — the message line follows the pointer: what it is
 * over (a terminal, a part, a button, a tile...), or else what to do next.
 * A message the game shows itself (a burn, an error, a win) stays until
 * the pointer moves onto something else. */
#include "sim.h"
#include "ui.h"
#include "board_ui.h"
#include "zone.h"
#include "title.h"

extern unsigned char won;              /* main.c */
unsigned char hover_force, hover_sync;
static unsigned char hover_last = NONE;

/* Some wire reaches a motor, the claw or the radio. */
static unsigned char sinks_wired(void)
{
    static unsigned char k;
    for (k = 0u; k < 6u; ++k)
        if (wires[k] != NONE) return 1u;
    return 0u;
}

static unsigned char hover_text(void)
{
    static unsigned char t;
    if (py >= BTN_Y - 1u && py < BTN_Y + 8u) {
        t = button_at(px);
        if (t != NONE) return btn_tip[t];
    }
    switch (screen) {
    case S_TITLE:
        t = title_row_at(px, py);
        if (t == NONE) return T_G_TITLE;
        return t <= persist.reached ? T_GOAL_DRONE + mission_goal(t) : T_LOCKED;
    case S_HELP:
        return T_G_HELP;
    case S_BRIEF:
        return T_G_BRIEF;
    case S_ZONE:
        t = zone_hover(px, py);
        if (t) return t;
        if (won) return T_G_WON;
        if (running) return T_G_RUN;
        return board_parts() ? T_G_TRY : T_G_ENTER;
    }
    if (mode == M_BURN) return T_BURN_ASK;
    if (mode == M_OPEN) return T_OPEN_ASK;
    if (mode == M_CLEAR) return T_CLEAR_ASK;
    t = board_hover(px, py);
    if (t) return t;
    if (held_src != NONE) return T_G_WIRE;
    if (held_kind || held_part != NONE) return T_G_PLACE;
    if (!board_parts()) return T_G_EMPTY;
    if (screen == S_LAB) return T_G_LAB;
    return sinks_wired() ? T_G_DONE : T_G_WIRING;
}

unsigned char hover_poll(void)
{
    static unsigned char t;
    if (hover_sync) {                   /* a message of the game's: keep it */
        hover_sync = hover_force = 0u;
        hover_last = hover_text();
        return 0u;
    }
    if (!moved && !hover_force) return 0u;
    t = hover_text();
    if (t == hover_last && !hover_force) return 0u;
    hover_last = t;
    return 1u;
}

void hover_draw(void)
{
    hover_force = 0u;
    hover_last = hover_text();          /* (a click may have changed the screen) */
    begin_draw();
    msg(hover_last);
    hover_sync = 0u;                    /* (msg's own) */
}
