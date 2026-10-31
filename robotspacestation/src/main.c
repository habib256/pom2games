/* Robot Space Station — screens and main loop: the chip lab, the test zone
 * and the inside of the drone (docs/SPEC.md). */
#include <string.h>
#include "dhgr.h"
#include "apple2c.h"
#include "apple2io.h"
#include "apple2frame.h"
#include "apple2aux.h"
#include "prodos.h"
#include "mouse.h"
#include "sim.h"
#include "ui.h"
#include "board_ui.h"
#include "zone.h"
#include "title.h"

#define MISSIONS_MAX mission_count()     /* src/room.h, in zone.c */
#define LAB_TICK 8u             /* frames per turn: slow enough to watch */
#define DRONE_TICK 2u            /* loop turns per drone turn: ~16 turns per second */

/* Buttons (ui.c: button 0 reads RUN or PAUSE), and the text each one
 * shows on the message line while the pointer is over it. */
static const char b_run[] = "RUN", b_step[] = "STEP", b_menu[] = "MENU", b_play[] = "PLAY",
    b_lab[] = "LAB", b_goal[] = "GOAL";
static const char *const lab_buttons[] = {b_run, b_step, "BURN", "CLEAR", "TEST"};
static const unsigned char lab_tips[] = {T_B_RUN, T_B_STEP, T_B_BURN, T_B_CLEAR, T_B_TRY};
static const char *const zone_buttons[] = {b_run, b_step, "RESET", b_goal, b_menu};
static const unsigned char zone_tips[] = {T_B_RUN, T_B_STEP, T_B_RESET, T_B_GOAL, T_B_MENU};
static const char *const won_buttons[] = {b_run, b_step, "NEXT", b_goal, b_menu};
static const unsigned char won_tips[] = {T_B_RUN, T_B_STEP, T_B_NEXT, T_B_GOAL, T_B_MENU};
static const char *const drone_buttons[] = {b_run, b_step, "EXIT"};
static const unsigned char drone_tips[] = {T_B_RUN, T_B_STEP, T_B_LEAVE};
/* The title's, help's and briefing's in the FRONT overlay (src/overlay.s):
 * buttons_set() keeps pointers to them, used while that screen is up. */
#pragma rodata-name (push, "FRONTDATA")
static const char *const title_buttons[] = {b_play, b_lab, "HELP", "RECORDS", "PAGE"};
static const unsigned char title_tips[] = {T_B_PLAY, T_B_LAB, T_B_HELP, T_B_RECORDS, T_B_PAGE};
static const char *const help_buttons[] = {"NEXT", "BACK", "DONE"};
static const unsigned char help_tips[] = {T_B_BACK, T_B_PREV, T_B_DONE};
static const char *const brief_buttons[] = {b_play, "HINT", "GATES", b_lab, b_menu};
static const unsigned char brief_tips[] = {T_B_GO, T_B_HINT, T_B_GATES, T_B_LAB, T_B_MENU};
#pragma rodata-name (pop)

unsigned char claimed;
unsigned tick_count;
unsigned char walking, walk_x, walk_y;   /* technician target (screen) */
static unsigned char walk_drone;        /* the drone clicked + 1: he gets in when he touches it */
unsigned char pending_x, pending_y;      /* inside: click done on arrival */
static unsigned char lab_running, drone_running, frames;
static unsigned char board_owner;       /* S_LAB or S_DRONE: whose board is loaded */
unsigned char won, saved_ok;            /* this mission won; last save written */
static unsigned char loaded;            /* a mission is in the zone (mission) */
static unsigned char brief_m, brief_back, hints;   /* the briefing: its mission, */
                                        /* the screen it came from, hints shown */
#pragma bss-name (push, "IOBUF")
unsigned char iobuf[1024];                  /* also zone.c (RSS.ROOMS) */
#pragma bss-name (pop)
static const char save_name[] = "\x08RSS.SAVE";
static const char text_name[] = "\x09RSS.TEXT1";
static const char ovl_name[] = "\x07RSS.OVL";

#define W_NONE 0u
#define W_WALK 1u               /* zone: just walk */
#define W_CLICK 2u              /* inside: then click the board */
#define W_EXIT 3u               /* inside: then leave by the door */

void game_shutdown(void)
{
    mouse_close();
    dhgr_text_restore();
    if (claimed) { prodos_video_release(); claimed = 0u; }
}

static void __fastcall__ save_layout(unsigned char *buf)
{
    memcpy(buf, parts, sizeof parts);
    memcpy(buf + sizeof parts, wires, sizeof wires);
}

static void __fastcall__ load_layout(const unsigned char *buf)
{
    memcpy(parts, buf, sizeof parts);
    memcpy(wires, buf + sizeof parts, sizeof wires);
    board_compile();
}

/* -- the save file ------------------------------------------------------- */

/* Boot only, in the FRONT overlay (main() loads it first): the defaults
 * and game_load(). */
#pragma code-name (push, "FRONTCODE")
#pragma rodata-name (push, "FRONTDATA")
static void persist_defaults(void)
{
    static unsigned char c;
    memset(&persist, 0, sizeof persist);
    memcpy(persist.magic, "RSS3", 4);
    memset(persist.out, NONE, sizeof persist.out);
    for (c = 0u; c < CHIPS; ++c) memset(persist.layout[c] + PARTS * 3u, NONE, LAYOUT_IDS);
    memset(persist.lab + PARTS * 3u, NONE, LAYOUT_IDS);
    memset(persist.drone + PARTS * 3u, NONE, LAYOUT_IDS);
    memset(persist.drone2 + PARTS * 3u, NONE, LAYOUT_IDS);
}
#pragma rodata-name (pop)
#pragma code-name (pop)

/* The text bank, read at $2000 (DHGR not started yet) into aux $6000 and
 * $8000 (prodos_load_aux); the overlays (RSS.OVL: PLAY padded to 8K, then FRONT)
 * read at $2000-$5FFF, then into aux $4000 and $A000. 1 = done. */
static unsigned char text_load(void)
{
    static char name[10];
    static unsigned char k;
    memcpy(name, text_name, sizeof name);
    prodos_file_name = name;
    prodos_file_iobuf = iobuf;
    prodos_file_buffer = (void *)0x2000;
    prodos_file_length = 0x2000u;
    for (k = 0u; k < 2u; ++k) {
        name[9] = '1' + k;
        if (prodos_load_aux(k ? (void *)0x8000 : (void *)0x6000, 0x2000u)) return 0u;
    }
    memcpy(name, ovl_name, sizeof ovl_name);
    prodos_file_length = 0x4000u;
    if (prodos_load_free()) return 0u;
    aux_store(32u, 0x40u);
    aux_store_src = 0x40u;
    aux_store(32u, 0xA0u);
    return 1u;
}

static void file_setup(void)
{
    prodos_file_name = (void *)save_name;
    prodos_file_iobuf = iobuf;
    prodos_file_buffer = &persist;
    prodos_file_length = sizeof persist;
}

#pragma code-name (push, "FRONTCODE")
#pragma rodata-name (push, "FRONTDATA")
static void game_load(void)
{
    file_setup();
    if (prodos_load() || persist.reached > MISSIONS_MAX) {
        persist_defaults();
    } else if (prodos_file_actual == sizeof persist - BEST_SLOTS - LAYOUT_SIZE
               && !memcmp(persist.magic, "RSS1", 4)) {
        /* A save from before drone B: everything but its board. */
        memcpy(persist.magic, "RSS3", 4);
        memset(persist.drone2, 0, PARTS * 3u);
        memset(persist.drone2 + PARTS * 3u, NONE, LAYOUT_IDS);
        memset(persist.best, 0, BEST_SLOTS);
    } else if (prodos_file_actual == sizeof persist - BEST_SLOTS
               && !memcmp(persist.magic, "RSS2", 4)) {
        /* A save from before the records: no best yet. */
        memcpy(persist.magic, "RSS3", 4);
        memset(persist.best, 0, BEST_SLOTS);
    } else if (prodos_file_actual != sizeof persist || memcmp(persist.magic, "RSS3", 4)) {
        persist_defaults();
    }
}
#pragma rodata-name (pop)
#pragma code-name (pop)

/* Both drones' boards into their records (A or B may be the loaded one). */
static void store_drones(void)
{
    save_layout(cur_drone ? persist.drone2 : persist.drone);
    board_swap();
    save_layout(cur_drone ? persist.drone : persist.drone2);
    board_swap();
}

/* The board on screen goes into its record first. 1 = written. */
static unsigned char game_save(void)
{
    if (board_owner == S_LAB) save_layout(persist.lab); else store_drones();
    file_setup();
    saved_ok = !prodos_save() && prodos_file_actual == sizeof persist;
    return saved_ok;
}

unsigned char board_saved(void) { return game_save(); }

static void empty_hands(void)
{
    held_kind = 0u; held_part = NONE; held_src = NONE; mode = M_EDIT;
    walking = W_NONE;
}

/* -- screens --------------------------------------------------------------- */

static void enter_lab(void)
{
    screen = S_LAB;
    screen_clear();
    board_draw();
    board_palette();
    buttons_set(lab_buttons, lab_tips, 5);
    hover_force = 1u;
}

/* Load the lab's or the drone's board, keeping the other in its record. */
static void __fastcall__ use_board(unsigned char owner)
{
    empty_hands();
    if (owner == board_owner) return;
    if (board_owner == S_LAB) {
        save_layout(persist.lab);
        lab_running = running;
        board_swap();                       /* drone B's board aside */
        load_layout(persist.drone2);
        board_swap();
        load_layout(persist.drone);
        cur_drone = 0u;
        running = drone_running;
    } else {
        store_drones();
        drone_running = running;
        load_layout(persist.lab);
        running = lab_running;
    }
    board_owner = owner;
}

static void enter_title(void)
{
    screen = S_TITLE;
    running = 0u;
    overlay_use(OV_FRONT);
    screen_clear();
    title_draw();
    buttons_set(title_buttons, title_tips, 5);
    hover_force = 1u;
}

/* The help's pages (title.h), then the records (S_HELP); help_back: the
 * screen to go back to (S_TITLE, S_BRIEF or S_LAB). */
static unsigned char help_page, help_back;
static void __fastcall__ enter_help(unsigned char page)
{
    screen = S_HELP;
    running = 0u;
    help_page = page;
    overlay_use(OV_FRONT);
    screen_clear();
    help_draw(page);
    buttons_set(help_buttons, help_tips, page == RECORDS_PAGE ? 1u : 3u);
    hover_force = 1u;
}
static void enter_brief_again(void);
static void enter_lab(void);
static void help_done(void)
{
    if (help_back == S_BRIEF) enter_brief_again();
    else if (help_back == S_LAB) enter_lab();
    else enter_title();
}
/* A click or a key on a help page: the next one, after the last DONE. */
static void help_next(void)
{
    if (help_page + 1u < HELP_PAGES) enter_help(help_page + 1u); else help_done();
}
static void __fastcall__ open_help(unsigned char page)
{
    help_back = screen;
    enter_help(page);
}

/* The briefing's drawing in the FRONT overlay: enter_brief() loads it. */
#pragma code-name (push, "FRONTCODE")
#pragma rodata-name (push, "FRONTDATA")
/* The hints shown so far, under the briefing. */
static void draw_hints(void)
{
    static unsigned char k;
    if (!hints) return;
    begin_draw();
    text_at(T_H_HINTS, 0, 118);
    dhgr_fill_rect(0, 125, 28, 1, DHGR_ORANGE);
    page_x = 0u; page_y = 129u;
    for (k = 0u; k < hints; ++k) text_page((k ? T_HINT2 : T_HINT1) + brief_m);
}

static void brief_draw(void)
{
    static char num[3];
    static unsigned char m;
    m = brief_m;
    screen_clear();
    num[0] = m < 9u ? '1' + m : '0' + (m + 1u) / 10u;
    num[1] = m < 9u ? 0 : '0' + (m + 1u) % 10u;
    num[2] = 0;
    dhgr_puts_small("MISSION", 0, 1);
    dhgr_puts_small(num, 40, 1);
    text_at(T_NAME + m, 54, 1);
    dhgr_fill_rect(0, 8, 140, 1, DHGR_AQUA);
    page_x = 0u; page_y = 13u;
    text_page(T_BRIEF + m);
    draw_hints();
    buttons_set(brief_buttons, brief_tips, 5);
    hover_force = 1u;
}
#pragma rodata-name (pop)
#pragma code-name (pop)

/* Mission m's briefing: its goal, what is new, then the hints asked for.
 * back: S_ZONE or S_DRONE to go back there (the mission running), or
 * NONE: PLAY starts mission m. */
static void __fastcall__ enter_brief(unsigned char m, unsigned char back)
{
    if (m != brief_m) hints = 0u;
    brief_m = m;
    brief_back = back;
    screen = S_BRIEF;
    running = 0u;
    overlay_use(OV_FRONT);
    brief_draw();
}
static void enter_brief_again(void) { enter_brief(brief_m, brief_back); }

static void enter_zone(void)
{
    screen = S_ZONE;
    overlay_use(OV_PLAY);
    screen_clear();
    zone_draw();
    ui_room();
    if (won) buttons_set(won_buttons, won_tips, 5); else buttons_set(zone_buttons, zone_tips, 5);
    hover_force = 1u;
}

/* Mission m from its start: room (from the disk), objects, drone state
 * reset; 0 if the room could not be read. */
static unsigned char __fastcall__ start_mission(unsigned char m)
{
    overlay_use(OV_PLAY);
    if (!zone_load(m)) return 0u;
    board_compile();
    board_swap();
    board_compile();
    board_swap();
    won = 0u;
    running = 0u;
    loaded = 1u;
    return 1u;
}

static void __fastcall__ enter_drone(unsigned char d)
{
    if (d != cur_drone) {
        board_swap();
        cur_drone = d;
    }
    screen = S_DRONE;
    overlay_use(OV_PLAY);
    empty_hands();
    screen_clear();
    board_draw();
    board_palette();
    buttons_set(drone_buttons, drone_tips, 3);
    hover_force = 1u;
    act_x = DOOR_X + 5u;
    act_y = DOOR_Y - ACT_H - 1u;
    actor_show();
}

/* Mission m in the test zone (the drones' boards already loaded). */
static void __fastcall__ go_mission(unsigned char m)
{
    if (start_mission(m)) {
        enter_zone();
        return;
    }
    enter_title();
    msg(T_NO_ROOM);
}

static void __fastcall__ play(unsigned char m)
{
    use_board(S_DRONE);
    go_mission(m);
}

/* The first mission not won yet (the last one once all are): its briefing. */
static void play_next(void)
{
    enter_brief(persist.reached < MISSIONS_MAX ? persist.reached : MISSIONS_MAX - 1u, NONE);
}

/* PLAY on the briefing: back where it was called from, or the mission. */
static void brief_play(void)
{
    if (brief_back == NONE) { play(brief_m); return; }
    if (brief_back == S_DRONE) { enter_drone(cur_drone); return; }
    enter_zone();
}

/* GOAL (or H) in the room or a drone: the briefing, then back. */
static void show_brief(void)
{
    enter_brief(mission, screen);
}

/* The lab's TEST: back to the mission played, else the next one. */
static void lab_test(void)
{
    if (!loaded) { play_next(); return; }
    use_board(S_DRONE);
    enter_zone();
}

static void go_lab(void)
{
    use_board(S_LAB);
    enter_lab();
}

static void leave_drone(void)
{
    empty_hands();
    tech_beside_drone(cur_drone);
    enter_zone();
}

/* -- actions --------------------------------------------------------------- */

/* After a turn or a step of the technician: the mission's goal reached? */
static void check_won(void)
{
    static const char *text;
    if (won || !zone_won()) return;
    won = 1u;
    running = 0u;
    sfx(SFX_WIN);
    if (persist.reached <= mission) persist.reached = mission + 1u;
    text = zone_won_text();                 /* (the best gates, before the save) */
    begin_draw();
    if (screen == S_ZONE) buttons_set(won_buttons, won_tips, 5); else buttons_draw();
    if (game_save()) message(text); else msg(T_WON_NS);
}

static void step(void)
{
    ++tick_count;
    if (screen == S_LAB) {
        memcpy(values, lab_inputs, 4);
        board_tick();
        board_refresh();
        return;
    }
    zone_tick();
    if (screen == S_ZONE) zone_frame();     /* what changed, each byte once */
    if (screen == S_DRONE) board_refresh();   /* (a drone passes over him) */
    check_won();
}

static void click_button(unsigned char b)
{
    if (screen == S_HELP) {
        if (b == 1u) { if (help_page) enter_help(help_page - 1u); }
        else if (b == 2u || help_page == RECORDS_PAGE) help_done();
        else help_next();
        return;
    }
    if (b == 0xFFu) return;
    if (mode == M_CLEAR && !(screen == S_LAB && b == 3u)) mode = M_EDIT;
    switch (screen) {
    case S_TITLE:
        if (b == 0u) play_next();
        else if (b == 1u) go_lab();
        else if (b == 4u) { title_page ^= 1u; enter_title(); }
        else open_help(b == 2u ? 0u : RECORDS_PAGE);
        return;
    case S_BRIEF:
        if (b == 0u) brief_play();
        else if (b == 1u) {
            if (hints < 2u) ++hints;
            draw_hints();
        }
        else if (b == 2u) open_help(GATES_PAGE);
        else if (b == 3u) go_lab();
        else enter_title();
        return;
    }
    if (b == 0u) { running ^= 1u; buttons_draw(); return; }
    if (b == 1u) { running = 0u; buttons_draw(); step(); return; }
    if (screen == S_LAB) {
        if (b == 2u) {
            mode = M_BURN;
            msg(T_BURN_ASK);
        } else if (b == 3u) {
            if (mode != M_CLEAR) {
                mode = M_CLEAR;
                msg(T_CLEAR_ASK);
            } else {
                mode = M_EDIT;
                board_clear_all();
                msg(T_CLEARED);
            }
        } else {
            lab_test();
        }
    } else if (screen == S_ZONE) {
        if (b == 2u && won && mission + 1u >= MISSIONS_MAX) {
            msg(T_ALL_DONE);
        } else if (b == 2u && won) {
            enter_brief(mission + 1u, NONE);
        } else if (b == 2u) {
            go_mission(mission);
        } else if (b == 3u) {
            show_brief();
        } else {
            enter_title();
        }
    } else {
        walking = W_EXIT;
        walk_x = DOOR_X + 5u;
        walk_y = DOOR_Y - ACT_H - 1u;
        msg(T_TO_DOOR);
    }
}

static void click(unsigned char x, unsigned char y)
{
    if (screen == S_HELP && (y < BTN_Y - 1u || y >= BTN_Y + 8u)) { help_next(); return; }
    if (y >= BTN_Y - 1u && y < BTN_Y + 8u) { click_button(button_at(x)); return; }
    if (screen == S_TITLE) {
        x = title_mission_at(x, y);
        if (x != NONE) enter_brief(x, NONE);
        return;
    }
    if (screen == S_BRIEF) return;
    if (screen == S_LAB) { board_click(x, y); return; }
    if (screen == S_DRONE) {
        if (y >= PAL_Y) { board_click(x, y); return; }
        /* The technician walks there first; his hand is at his right. */
        walking = W_CLICK;
        pending_x = x; pending_y = y;
        walk_x = x > ACT_W + 1u ? x - ACT_W - 1u : 0u;
        walk_y = y > BOARD_TOP + 4u ? y - 4u : BOARD_TOP;
        if (walk_y > DOOR_Y - ACT_H) walk_y = DOOR_Y - ACT_H;
        return;
    }
    if (y >= ROOM_Y && y < ROOM_Y + ROOM_H) {
        walking = W_WALK;
        walk_drone = zone_hover(x, y) - (T_R_DRONE_A - 1u);   /* 1 A, 2 B, else not a drone */
        walk_x = x > 2u ? x - 2u : 0u;
        walk_y = y > 4u ? y - 4u : 0u;
    }
}

/* Inside the drone nothing blocks him: straight to the target, 6 pixels
 * per frame on each axis. */
static unsigned char __fastcall__ toward(unsigned char a, unsigned char b)
{
    if (a + 6u < b) return a + 6u;
    if (a > b + 6u) return a - 6u;
    return b;
}

static unsigned char inside_step(void)
{
    act_x = toward(act_x, walk_x);
    act_y = toward(act_y, walk_y);
    return act_x != walk_x || act_y != walk_y;
}

static void walk(void)
{
    static unsigned char again;
    if (screen == S_ZONE) {
        again = tech_step(walk_x, walk_y) && tech_step(walk_x, walk_y)
            && tech_step(walk_x, walk_y);
        if (!again) walking = W_NONE;
        again = tech_touches_drone();       /* in only by a click on it */
        if (again && again == walk_drone) { enter_drone(again - 1u); return; }
        if (zone_doors()) zone_draw_doors();     /* he may stand on a plate */
        zone_frame();
        check_won();
        return;
    }
    if (inside_step()) return;
    begin_draw();                       /* (the pointer was kept while he walked) */
    if (walking == W_EXIT) { leave_drone(); return; }
    walking = W_NONE;
    board_click(pending_x, pending_y);
}

int main(void)
{
    static unsigned char busy, cursor_kept, m, fast, line;
    if (prodos_video_claim(PD_VIDEO_DISCARD_RAM) != PD_VIDEO_OK) {
        a2_puts("NO AUXILIARY MEMORY.\r");
        apple2_getkey();
        return 1;
    }
    claimed = 1u;
    if (!text_load()) {
        a2_puts("CANNOT READ RSS.TEXT1/2 OR RSS.OVL.\r");
        apple2_getkey();
        return 1;
    }
    mouse_init();
    if (!dhgr_init()) {
        a2_puts("NEEDS A IIE ENHANCED 128K OR A IIC.\r");
        apple2_getkey();
        return 1;
    }
    a2_frame_init();
    a2_frame_set_delay(40u);
    dhgr_draw_page(1);
    dhgr_show_page(1);
    overlay_use(OV_PLAY);
    zone_init();
    overlay_use(OV_FRONT);
    game_load();
    title_page = persist.reached >= 14u;   /* the next mission's page */
    load_layout(persist.lab);
    board_owner = S_LAB;
    enter_title();
    show();
    for (;;) {
        ui_poll();
        if (key == 0x11u) return 0;            /* Ctrl-Q: back to ProDOS */
        if (running && ++frames >= (screen == S_LAB ? LAB_TICK : fast ? 1u : DRONE_TICK)) frames = 0u;
        if (running && !frames) step();         /* draws only what changed */
        line = hover_poll();
        busy = line || pressed || walking || key == KC_ESC
            || key == 'M' || key == 'S' || key == 'V' || key == 'H' || key == 'P' || key == 'G' || key == 'O' || (key >= '0' && key <= '9');
        if (!busy) {
            actor_show();
            show();
            a2_frame_wait();
            continue;
        }
        /* A walk alone moves only the technician: keep the pointer unless
         * it is near him, even after this frame's step of up to 6 pixels
         * (the pointer and he both save what they cover: neither may be
         * drawn over the other). In the room the compositor draws both.
         * He is hidden after his step, just before he is drawn again. */
        cursor_kept = walking && !pressed && !key;
        if (cursor_kept && screen == S_DRONE)
            cursor_kept = (unsigned char)(px - act_x + 14u) > 32u || (unsigned char)(py - act_y + 16u) > 42u;
        if (!cursor_kept) hide();
        if (!walking || pressed || key) actor_hide();
        if (screen == S_HELP && key) {      /* a key: on (ESC: done) */
            if (key == KC_ESC) help_done(); else help_next();
            pressed = 0u;                   /* (SPACE: once) */
        }
        else if (key == KC_ESC) { if (screen == S_ZONE) walking = W_NONE; else board_drop(); }
        else if (key == 'V' && screen != S_LAB) {     /* the drones twice as often */
            fast ^= 1u;
            msg(fast ? T_SPEED_F : T_SPEED_N);
        }
        else if (key == 'S') {
            sound_on ^= 1u;
            msg(sound_on ? T_SOUND_ON : T_SOUND_OFF);
        }
        else if (key == 'H' && screen == S_TITLE) open_help(0);
        else if (key == 'H' && screen == S_LAB) open_help(LAB_PAGE);
        else if (key == 'H' && (screen == S_ZONE || screen == S_DRONE)) show_brief();
        else if (key == 'H' && screen == S_BRIEF) click_button(1);
        else if (key == 'M' && screen != S_TITLE && screen != S_BRIEF) click_button(0);
        else if (key == 'P' && screen != S_TITLE && screen != S_BRIEF) click_button(1);
        else if (key == 'G' && screen == S_LAB) click_button(2);
        else if (key == 'O' && screen == S_LAB) { mode = M_OPEN; msg(T_OPEN_ASK); }
        else if (screen == S_ZONE && key >= '0' && key <= '9') {
            /* Replay a mission, or play the next one not yet won (0: the 10th). */
            m = key == '0' ? 9u : key - '1';
            if (m < MISSIONS_MAX && m <= persist.reached) go_mission(m);
        }
        if (pressed) click(px, py);
        if (walking) walk();
        actor_hide();
        if (line && !hover_sync) hover_draw();
        actor_show();
        show();
        a2_frame_wait();
    }
}
