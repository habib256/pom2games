/* Robot Space Station — screens and main loop: the chip lab, the test zone
 * and the inside of the drone (docs/SPEC.md). */
#include <string.h>
#include "dhgr.h"
#include "apple2c.h"
#include "apple2io.h"
#include "apple2frame.h"
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

static const char *const lab_buttons[] = {"MARCHE", "PAS", "GRAVE", "EFFACE", "ESSAI"};
static const char *const zone_buttons[] = {"MARCHE", "PAS", "REPLACER", "LABO", "MENU"};
static const char *const won_buttons[] = {"MARCHE", "PAS", "SUITE", "LABO", "MENU"};
static const char *const title_buttons[] = {"JOUER", "LABO"};
static const char *const drone_buttons[] = {"MARCHE", "PAS", "SORTIR"};

unsigned char claimed;
unsigned tick_count;
unsigned char walking, walk_x, walk_y;   /* technician target (screen) */
unsigned char pending_x, pending_y;      /* inside: click done on arrival */
static unsigned char lab_running, drone_running, frames;
static unsigned char board_owner;       /* S_LAB or S_DRONE: whose board is loaded */
unsigned char won, saved_ok;            /* this mission won; last save written */
#pragma bss-name (push, "IOBUF")
unsigned char iobuf[1024];                  /* also zone.c (RSS.ROOMS) */
#pragma bss-name (pop)
static const char save_name[] = "\x08RSS.SAVE";

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

static void persist_defaults(void)
{
    static unsigned char c;
    memset(&persist, 0, sizeof persist);
    memcpy(persist.magic, "RSS2", 4);
    memset(persist.out, NONE, sizeof persist.out);
    for (c = 0u; c < CHIPS; ++c) memset(persist.layout[c] + PARTS * 3u, NONE, LAYOUT_IDS);
    memset(persist.lab + PARTS * 3u, NONE, LAYOUT_IDS);
    memset(persist.drone + PARTS * 3u, NONE, LAYOUT_IDS);
    memset(persist.drone2 + PARTS * 3u, NONE, LAYOUT_IDS);
}

static void file_setup(void)
{
    prodos_file_name = (void *)save_name;
    prodos_file_iobuf = iobuf;
    prodos_file_buffer = &persist;
    prodos_file_length = sizeof persist;
}

static void game_load(void)
{
    file_setup();
    if (prodos_load() || persist.reached > MISSIONS_MAX) {
        persist_defaults();
    } else if (prodos_file_actual == sizeof persist - LAYOUT_SIZE
               && !memcmp(persist.magic, "RSS1", 4)) {
        /* A save from before drone B: everything but its board. */
        memcpy(persist.magic, "RSS2", 4);
        memset(persist.drone2, 0, PARTS * 3u);
        memset(persist.drone2 + PARTS * 3u, NONE, LAYOUT_IDS);
    } else if (prodos_file_actual != sizeof persist || memcmp(persist.magic, "RSS2", 4)) {
        persist_defaults();
    }
}

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
    buttons_set(lab_buttons, 5);
    message(mouse_slot ? "SOURIS ACTIVE" : "FLECHES + ESPACE");
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
    screen_clear();
    title_draw();
    buttons_set(title_buttons, 2);
    message("CLIQUER UNE MISSION OU JOUER");
}

static void enter_zone(void)
{
    screen = S_ZONE;
    screen_clear();
    zone_draw();
    buttons_set(won ? won_buttons : zone_buttons, 5);
    message(won ? "MISSION REUSSIE !" : "TOUCHER LE DRONE POUR ENTRER");
    actor_show();
}

/* Mission m from its start: room (from the disk), objects, drone state
 * reset; 0 if the room could not be read. */
static unsigned char __fastcall__ start_mission(unsigned char m)
{
    if (!zone_load(m)) return 0u;
    board_compile();
    board_swap();
    board_compile();
    board_swap();
    won = 0u;
    running = 0u;
    return 1u;
}

static void __fastcall__ enter_drone(unsigned char d)
{
    if (d != cur_drone) {
        board_swap();
        cur_drone = d;
    }
    screen = S_DRONE;
    empty_hands();
    screen_clear();
    board_draw();
    board_palette();
    buttons_set(drone_buttons, 3);
    message("DANS LE DRONE");
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
    message("DISQUE : SALLE ILLISIBLE");
}

static void __fastcall__ play(unsigned char m)
{
    use_board(S_DRONE);
    go_mission(m);
}

/* The first mission not won yet (the last one once all are). */
static void play_next(void)
{
    play(persist.reached < MISSIONS_MAX ? persist.reached : MISSIONS_MAX - 1u);
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
    if (won || !zone_won()) return;
    won = 1u;
    running = 0u;
    sfx(SFX_WIN);
    if (persist.reached <= mission) persist.reached = mission + 1u;
    begin_draw();
    if (screen == S_ZONE) buttons_set(won_buttons, 4); else buttons_draw();
    message(game_save() ? "MISSION REUSSIE !" : "REUSSIE (PAS SAUVEE)");
}

static void step(void)
{
    static unsigned char d;
    ++tick_count;
    if (screen == S_LAB) {
        memcpy(values, lab_inputs, 4);
        board_tick();
        board_refresh();
        return;
    }
    d = zone_tick();
    if (d && screen == S_ZONE) drone_draw(d);
    if (screen == S_DRONE) {
        board_refresh();
    } else {
        d = tech_touches_drone();
        if (d) enter_drone(d - 1u);                 /* a drone took him in */
    }
    check_won();
}

static void click_button(unsigned char b)
{
    if (b == 0xFFu) return;
    if (mode == M_CLEAR && !(screen == S_LAB && b == 3u)) mode = M_EDIT;
    if (screen != S_TITLE) {
        if (b == 0u) { running ^= 1u; buttons_draw(); return; }
        if (b == 1u) { running = 0u; buttons_draw(); step(); return; }
    }
    if (screen == S_TITLE) {
        if (b == 0u) play_next(); else go_lab();
        return;
    }
    if (screen == S_LAB) {
        if (b == 2u) {
            mode = M_BURN;
            message("GRAVER DANS : CLIQUER P1-P8");
        } else if (b == 3u) {
            if (mode != M_CLEAR) {
                mode = M_CLEAR;
                message("EFFACER TOUT ? RECLIQUER");
            } else {
                mode = M_EDIT;
                board_clear_all();
                message("PLANCHE EFFACEE");
            }
        } else {
            play_next();
        }
    } else if (screen == S_ZONE) {
        if (b == 2u && won && mission + 1u >= MISSIONS_MAX) {
            message("LA STATION EST REPAREE !");
        } else if (b == 2u) {
            go_mission(won ? mission + 1u : mission);
        } else if (b == 3u) {
            go_lab();
        } else {
            enter_title();
        }
    } else {
        walking = W_EXIT;
        walk_x = DOOR_X + 5u;
        walk_y = DOOR_Y - ACT_H - 1u;
        message("VERS LA PORTE");
    }
}

static void click(unsigned char x, unsigned char y)
{
    if (y >= BTN_Y - 1u && y < BTN_Y + 8u) { click_button(button_at(x)); return; }
    if (screen == S_TITLE) {
        x = title_mission_at(x, y);
        if (x != NONE) play(x);
        return;
    }
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
        walk_x = x > 2u ? x - 2u : 0u;
        walk_y = y > 4u ? y - 4u : 0u;
    }
}

/* Inside the drone nothing blocks him: straight to the target, 3 pixels
 * per frame on each axis. */
static unsigned char __fastcall__ toward(unsigned char a, unsigned char b)
{
    if (a + 3u < b) return a + 3u;
    if (a > b + 3u) return a - 3u;
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
        again = tech_touches_drone();
        if (again) { actor_hide(); enter_drone(again - 1u); return; }
        if (zone_doors()) zone_draw_doors();     /* he may stand on a plate */
        check_won();
        return;
    }
    if (inside_step()) return;
    actor_hide();
    if (walking == W_EXIT) { leave_drone(); return; }
    walking = W_NONE;
    board_click(pending_x, pending_y);
}

int main(void)
{
    static unsigned char busy, cursor_kept, m;
    if (prodos_video_claim(PD_VIDEO_DISCARD_RAM) != PD_VIDEO_OK) {
        a2_puts("PAS DE MEMOIRE AUXILIAIRE.\r");
        apple2_getkey();
        return 1;
    }
    claimed = 1u;
    mouse_init();
    if (!dhgr_init()) {
        a2_puts("IIE ENHANCED 128K OU IIC REQUIS.\r");
        apple2_getkey();
        return 1;
    }
    a2_frame_init();
    a2_frame_set_delay(40u);
    dhgr_draw_page(1);
    dhgr_show_page(1);
    zone_init();
    game_load();
    load_layout(persist.lab);
    board_owner = S_LAB;
    enter_title();
    show();
    for (;;) {
        ui_poll();
        if (key == 0x11u) return 0;            /* Ctrl-Q: back to ProDOS */
        if (running && ++frames >= (screen == S_LAB ? LAB_TICK : DRONE_TICK)) frames = 0u;
        if (running && !frames) step();         /* draws only what changed */
        busy = pressed || walking || key == KC_ESC
            || key == 'M' || key == 'S' || key == 'P' || key == 'G' || key == 'O' || (key >= '0' && key <= '9');
        if (!busy) {
            if (screen == S_ZONE || screen == S_DRONE) actor_show();
            show();
            a2_frame_wait();
            continue;
        }
        /* A walk alone moves only the technician: keep the pointer unless
         * it is near him (its pixels are inverted, his are saved). */
        cursor_kept = walking && !pressed && !key
            && ((unsigned char)(px - act_x + 8u) > 20u || (unsigned char)(py - act_y + 10u) > 30u);
        if (!cursor_kept) hide();
        actor_hide();
        if (key == KC_ESC) { if (screen == S_ZONE) walking = W_NONE; else board_drop(); }
        else if (key == 'S') {
            sound_on ^= 1u;
            message(sound_on ? "SON ACTIF" : "SON COUPE");
        }
        else if (key == 'M') click_button(0);
        else if (key == 'P') click_button(1);
        else if (key == 'G' && screen == S_LAB) click_button(2);
        else if (key == 'O' && screen == S_LAB) { mode = M_OPEN; message("OUVRIR : CLIQUER P1-P8"); }
        else if (screen == S_ZONE && key >= '0' && key <= '9') {
            /* Replay a mission, or play the next one not yet won (0: the 10th). */
            m = key == '0' ? 9u : key - '1';
            if (m < MISSIONS_MAX && m <= persist.reached) go_mission(m);
        }
        if (pressed) click(px, py);
        if (walking) walk();
        if (screen == S_ZONE || screen == S_DRONE) actor_show();
        show();
        a2_frame_wait();
    }
}
