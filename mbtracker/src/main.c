/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* MB TRACKER — a Mockingboard tracker for the //e / //c 128 KB (ProDOS 8,
 * 80 columns). Edits AYS v1 songs (dev/lib/apple2/AYSONG_FORMAT.md) of 3 or
 * 6 voices, plays them with dev/lib/apple2/aysong.asm on the mb_irq.asm
 * 50 Hz interrupt. Keyboard and mouse (dev/lib/mouse: an AppleMouse card
 * on the //e, the //c's own; the Mockingboard is detected first, the 4c's
 * wake-up at $C403 can hide the //c's slot 4 mouse ROM).
 * Resident here: the pattern grid with the order list and the instruments
 * beside it, the blocks (copy, cut, paste, transpose, undo), the help.
 * The instrument editor (insed.c) and the file screens (fileui.c, files.c)
 * are overlays fetched from aux memory (MBT.OVL). Only what changes is
 * redrawn (a row, a field, a panel). */
#include <stdlib.h>
#include <string.h>
#include "prodos.h"
#include "mouse.h"
#include "mbt.h"
#include "ui.h"

unsigned char slot, rd, screen, cur_ins = 1, octave = 4, modified, ev_x, ev_y;
char msg[80], line[81], input_buf[33];
const char hexd[] = "0123456789ABCDEF";

static unsigned char irq_on, claimed;
/* (not static: tests/test_mbt.py reads them) */
unsigned char focus;                      /* 0 grid, 1 order list */
unsigned char cur_row, cur_v, cur_f, vtop, ord_cur, ord_top;
static unsigned char follow = 1;
unsigned char playing;                    /* 0, 1 song, 2 pattern loop */
static unsigned char play_o = 0xFF, play_r = 0xFF;
#pragma bss-name (push, "LOW8BSS")
static unsigned char aud_buf[200];
#pragma bss-name (pop)

static const char note_names[] = "C-C#D-D#E-F-F#G-G#A-A#B-";
static const char fx_letters[] = "OAUDFSNE";
static const char piano_lo[] = "ZSXDCVGBHNJM,";
static const char piano_hi[] = "Q2W3ER5T6Y7UI";
static const char mute_keys[] = "!@#$%^";
static const char main_bar[] = " ^P PLAY  ^R LOOP  SPC STOP  PAT  TAB ORD  ^E INS  ^L LOAD  ^S SAVE  ? HELP";
static const unsigned char main_keys[9] = { CTRL('P'), CTRL('R'), ' ', K_PAT, K_ORD, CTRL('E'), CTRL('L'), CTRL('S'), '?' };

/* the layout: 3 voices of 12 columns, or 6 of 8 (note, instrument, effect
 * and parameter without spaces) */
static unsigned char gx, cw, cs, gw, ord_x, ins_x, ins_w;
static const unsigned char *fx_x;
static const unsigned char fx_x3[5] = { 0, 4, 6, 7, 8 };   /* field -> column in a cell */
static const unsigned char fx_x6[5] = { 0, 3, 4, 5, 6 };
static const unsigned char fx_w[5] = { 3, 1, 1, 1, 1 };

/* the block: anchor (sel_v, sel_r) to the cursor; its rectangle, the clipboard */
unsigned char sel_on, sel_v, sel_r, sv0, sv1, sr0, sr1, clip_v, clip_r, drag;
/* undo: 1 a cell (u_cell), 2 the pattern (aux AUX_UNDO); again = redo */
unsigned char u_kind, u_pat, u_v, u_r, u_cell[3];

/* ---------------------------------------------------------------- text helpers */
void puts_at(unsigned char x, unsigned char y, const char *s)
{
    AT(x, y);
    txt_puts(s);
}

void __fastcall__ clear_line(unsigned char y)
{
    AT(0, y);
    txt_fill(' ', 80);
}

void hex2(char *d, unsigned char b)
{
    d[0] = hexd[b >> 4];
    d[1] = hexd[b & 15];
}

void dec2(char *d, unsigned char b)
{
    d[0] = '0' + b / 10;
    d[1] = '0' + b % 10;
}

static void dec3(char *d, unsigned char b)
{
    d[0] = '0' + b / 100;
    dec2(d + 1, b % 100);
}

void __fastcall__ say(const char *s)
{
    strcpy(msg, s);
    rd |= RD_MSG;
}

void touched(void)
{
    song_len = 0;
    modified = 1;
}

void __fastcall__ blank(unsigned char n)
{
    memset(line, ' ', n);
    line[n] = 0;
}

/* line[x .. x + n - 1] at (x, y) */
static void seg(unsigned char x, unsigned char y, unsigned char n)
{
    char c = line[x + n];
    line[x + n] = 0;
    puts_at(x, y, line + x);
    line[x + n] = c;
}

unsigned char __fastcall__ seg_at(const char *bar, unsigned char x)
{
    unsigned char i, n = 0;
    if (x >= strlen(bar) || (bar[x] == ' ' && (bar[x + 1] == ' ' || bar[x - 1] == ' ')))
        return 0xFF;
    for (i = 1; i <= x; ++i)
        if (bar[i] == ' ' && bar[i - 1] == ' ')
            ++n;
    return n;
}

/* main <-> aux: n bytes, op 0 aux to main, 1 main to aux, 2 / 3 the
 * same with the aux language card */
static void ax(unsigned char *m, unsigned a, unsigned n, unsigned char op)
{
    ax_main = m;
    ax_aux = a;
    ax_len = n;
    if (op == 3)
        lc_put();
    else if (op == 2)
        lc_get();
    else if (op)
        aux_put();
    else
        aux_get();
}

/* ---------------------------------------------------------------- overlays */
static unsigned char ovl_cur;
static void ovl_use(unsigned char n)
{
    if (ovl_cur != n) {
        ax((unsigned char *)OVL_RUN, LC_OVL + (n - 1) * OVL_SIZE, OVL_SIZE, 2);
        ovl_cur = n;
    }
}

/* ---------------------------------------------------------------- the grid */
void layout(void)
{
    if (s_voices == 6) {
        gx = 3;
        cw = 8;
        cs = 7;
        gw = 51;
        ord_x = 52;
        ins_x = 65;
        ins_w = 15;
        fx_x = fx_x6;
        txt_sw = 25;
    } else {
        gx = 4;
        cw = 12;
        cs = 10;
        gw = 39;
        ord_x = 41;
        ins_x = 55;
        ins_w = 24;
        fx_x = fx_x3;
        txt_sw = 19;
    }
}

static void note_text(char *d, unsigned char n)
{
    if (n == NOTE_EMPTY)
        memcpy(d, "---", 3);
    else if (n == NOTE_OFF)
        memcpy(d, "===", 3);
    else {
        memcpy(d, note_names + (n % 12) * 2, 2);
        d[2] = '0' + n / 12;
    }
}

static void cell_text(char *d, const unsigned char *c)
{
    unsigned char fxc = c[1] >> 4;
    note_text(d, c[0]);
    d[fx_x[1]] = (c[1] & 15) ? hexd[c[1] & 15] : '.';
    d += fx_x[2];
    if (fxc) {
        d[0] = fx_letters[fxc - 1];
        hex2(d + 1, c[2]);
    } else
        memcpy(d, "...", 3);
}

static void m_sample(void);

/* the block's rectangle (the cursor's cell without a block) */
static void sel_calc(void)
{
    sv0 = sv1 = cur_v;
    sr0 = sr1 = cur_row;
    if (!sel_on)
        return;
    if (sel_v < sv0)
        sv0 = sel_v;
    else
        sv1 = sel_v;
    if (sel_r < sr0)
        sr0 = sel_r;
    else
        sr1 = sel_r;
    if (sv1 >= s_voices)
        sv1 = s_voices - 1;
    if (sr1 >= s_rows)
        sr1 = s_rows - 1;
}

static void draw_row(unsigned char r)
{
    unsigned char y, v, x;
    if (screen || r < vtop || r >= vtop + GRID_H)
        return;
    m_sample();
    y = GRID_Y + r - vtop;
    blank(gw);
    if (r < s_rows) {
        dec2(line, r);
        if (playing && r == play_r && play_o == ord_cur)
            line[2] = '>';
        for (v = 0; v < s_voices; ++v) {
            x = gx + cw * v;
            cell_text(line + x, CELLP(v, r));
            line[x + cs] = '|';
        }
    }
    txt_mode = 0;
    puts_at(0, y, line);
    if (r >= s_rows)
        return;
    txt_mode = 1;
    sel_calc();
    if (sel_on && r >= sr0 && r <= sr1)
        for (v = sv0; v <= sv1; ++v)
            seg(gx + cw * v, y, cs);
    if (r == cur_row) {
        seg(0, y, 2);
        if (focus == 0) {
            txt_mode = !sel_on;
            seg(gx + cw * cur_v + fx_x[cur_f], y, fx_w[cur_f]);
        }
    }
    txt_mode = 0;
}

static void draw_grid(void)
{
    unsigned char r;
    for (r = vtop; r < vtop + GRID_H; ++r)
        draw_row(r);
}

/* the cursor row in view; a scroll redraws the grid */
static void view(void)
{
    unsigned char t = vtop;
    if (cur_row >= s_rows)
        cur_row = s_rows - 1;
    if (cur_row < vtop)
        vtop = cur_row;
    else if (cur_row >= vtop + GRID_H)
        vtop = cur_row - GRID_H + 1;
    if (t == vtop || (rd & RD_GRID) || screen)
        return;
    if (vtop == t + 1 || vtop + 1 == t) {      /* one row: the screen scrolls */
        AT(GRID_H, GRID_Y);
        txt_scroll(vtop < t);
        draw_row(vtop < t ? vtop : vtop + GRID_H - 1);
    } else
        rd |= RD_GRID;
}

static void goto_row(unsigned char r)
{
    unsigned char old = cur_row;
    cur_row = r;
    if (sel_on)
        rd |= RD_GRID;
    view();
    if (!(rd & RD_GRID)) {
        draw_row(old);
        draw_row(cur_row);
    }
}

static void move_row(signed char d)
{
    int r = cur_row + d;
    if (r < 0)
        r = 0;
    if (r >= s_rows)
        r = s_rows - 1;
    goto_row(r);
}

/* ---------------------------------------------------------------- panels */
static void draw_head(void)
{
    unsigned char k, x;
    blank(80);
    memcpy(line, " MB TRACKER ", 12);
    memcpy(line + 14, s_name[0] ? s_name : "(untitled)", strlen(s_name[0] ? s_name : "(untitled)"));
    if (slot) {
        memcpy(line + 63, "MOCKINGBOARD S", 14);
        line[77] = '0' + slot;
    } else
        memcpy(line + 64, "NO MOCKINGBOARD", 15);
    txt_mode = 1;
    puts_at(0, 0, line);
    txt_mode = 0;
    blank(80);
    memcpy(line, "FILE", 4);
    memcpy(line + 5, cur_file[0] ? cur_file : "-", strlen(cur_file[0] ? cur_file : "-"));
    memcpy(line + 21, "PAT", 3);
    dec2(line + 25, cur_pat);
    line[27] = '/';
    dec2(line + 28, s_npat);
    memcpy(line + 32, "ROWS", 4);
    dec2(line + 37, s_rows);
    memcpy(line + 41, "SPD", 3);
    dec3(line + 45, s_speed);
    memcpy(line + 50, "OCT", 3);
    line[54] = '0' + octave;
    memcpy(line + 57, "INS", 3);
    line[61] = hexd[cur_ins];
    memcpy(line + 64, playing == 1 ? "PLAY" : playing == 2 ? "LOOP" : "STOP", 4);
    if (follow)
        memcpy(line + 69, "FOLLOW", 6);
    if (modified)
        line[77] = '*';
    puts_at(0, 1, line);
    blank(80);
    memcpy(line, gx == 3 ? "RW" : "ROW", gx - 1);
    for (k = 0; k < s_voices; ++k) {
        x = gx + cw * k;
        if (s_voices == 6) {
            line[x] = 'V';
            line[x + 1] = '1' + k;
            x -= 3;
        } else {
            memcpy(line + x, "VOICE", 5);
            line[x + 6] = '1' + k;
        }
        if (snd_mute >> k & 1)
            memcpy(line + x + 6, "MUTE", 4);
    }
    memcpy(line + ord_x, focus ? "ORDER*" : "ORDER", focus ? 6 : 5);
    memcpy(line + ins_x, "INSTRUMENTS", 11);
    puts_at(0, 2, line);
}

static void draw_order(void)
{
    unsigned char y, i;
    if (ord_cur < ord_top)
        ord_top = ord_cur;
    if (ord_cur >= ord_top + GRID_H)
        ord_top = ord_cur - GRID_H + 1;
    for (y = 0; y < GRID_H; ++y) {
        i = ord_top + y;
        blank(12);
        if (i < s_nord) {
            line[0] = i == ord_cur ? '>' : ' ';
            dec3(line + 1, i);
            line[4] = ':';
            dec2(line + 5, s_order[i]);
            if (i == s_loop)
                line[8] = 'L';
            if (playing && i == play_o)
                line[9] = '*';
        } else if (i == s_nord)
            memcpy(line + 1, s_loop == 0xFF ? "END" : "LOOP", s_loop == 0xFF ? 3 : 4);
        txt_mode = (focus == 1 && i == ord_cur) ? 1 : 0;
        puts_at(ord_x, GRID_Y + y, line);
    }
    txt_mode = 0;
}

static void draw_ins(void)
{
    unsigned char i;
    const char *s;
    for (i = 1; i <= MAXINS; ++i) {
        blank(ins_w);
        line[0] = i == cur_ins ? '>' : ' ';
        line[1] = hexd[i];
        if (i <= s_nins) {
            s = s_ins[i - 1].name[0] ? s_ins[i - 1].name : "(no name)";
            memcpy(line + 3, s, strlen(s));
            line[ins_w] = 0;
        } else
            line[3] = '-';
        puts_at(ins_x, GRID_Y + i - 1, line);
    }
}

static void draw_keys(void)
{
    txt_mode = 1;
    clear_line(KEYS_Y);
    puts_at(0, KEYS_Y, main_bar);
    txt_mode = 0;
}

void redraw(void)
{
    if (screen) {
        if (rd & RD_MSG) {
            clear_line(MSG_Y);
            puts_at(1, MSG_Y, msg);
        }
        rd &= ~RD_MSG;
        return;
    }
    if (rd & RD_HEAD)
        draw_head();
    if (rd & RD_GRID)
        draw_grid();
    if (rd & RD_ORDER)
        draw_order();
    if (rd & RD_INS)
        draw_ins();
    if (rd & RD_MSG) {
        clear_line(MSG_Y);
        puts_at(1, MSG_Y, msg);
    }
    if (rd & RD_KEYS)
        draw_keys();
    rd = 0;
}

void full(void)
{
    screen = 0;
    txt_init();
    rd = RD_ALL;
}

/* ---------------------------------------------------------------- sound */
static unsigned char encoded(void)
{
    if (!song_len && !song_encode()) {
        say("SONG TOO BIG FOR THE 12 KB BUFFER");
        return 0;
    }
    return 1;
}

void stop(void)
{
    if (slot)
        snd_stop();
    snd_loop = 0xFF;
    if (playing) {
        playing = 0;
        rd |= RD_HEAD | RD_ORDER;
        if (play_o == ord_cur)
            draw_row(play_r);
    }
    play_o = play_r = 0xFF;
}

static void play(unsigned char mode)
{
    if (!slot) {
        say("NO MOCKINGBOARD: PLAYBACK IS OFF (EDITING AND FILES WORK)");
        return;
    }
    stop();
    if (!encoded())
        return;
    snd_song = song_buf;
    snd_order0 = ord_cur;
    snd_row0 = 0;
    snd_loop = mode == 2 ? ord_cur : 0xFF;
    snd_play();
    playing = mode;
    rd |= RD_HEAD | RD_ORDER;
}

void audition(unsigned char ins, unsigned char note)
{
    if (!slot || playing || ins > s_nins || !ins)
        return;
    audition_encode(aud_buf, ins - 1, note);
    snd_song = aud_buf;
    snd_order0 = snd_row0 = 0;
    snd_loop = 0xFF;
    snd_play();
}

/* An edit while playing: the song encoded again, the play resumes at the
 * row it was about to read (voices silent until their next note). */
static void resync(void)
{
    unsigned char o = ays_order, r = ays_row;
    snd_stop();
    if (!encoded()) {
        stop();
        return;
    }
    if (o >= s_nord)
        o = 0;
    if (snd_loop != 0xFF && snd_loop >= s_nord)
        snd_loop = s_nord - 1;
    if (r >= s_rows) {
        r = 0;
        if (snd_loop != 0xFF)
            o = snd_loop;
        else if (++o >= s_nord) {
            if (s_loop == 0xFF) {
                stop();
                return;
            }
            o = s_loop;
        }
    }
    snd_song = song_buf;
    snd_order0 = o;
    snd_row0 = r;
    snd_play();
}

static void poll_play(void)
{
    unsigned char o, r, oldo, oldr;
    if (!playing)
        return;
    if (!song_len) {
        resync();
        if (!playing)
            return;
    }
    if (!ays_play) {
        stop();
        say("END OF THE SONG");
        return;
    }
    do {
        o = ays_order;
        r = ays_row;
    } while (o != ays_order);
    r = r ? r - 1 : 0;
    if (screen || (o == play_o && r == play_r))
        return;
    oldo = play_o;
    oldr = play_r;
    play_o = o;
    play_r = r;
    if (oldo != o)
        rd |= RD_ORDER;
    if (follow) {
        if (o != ord_cur && o < s_nord) {
            ord_cur = o;
            if (s_order[o] != cur_pat) {
                pat_select(s_order[o]);
                rd |= RD_GRID | RD_HEAD;
            }
            rd |= RD_ORDER;
        }
        if (oldo == ord_cur)
            draw_row(oldr);
        goto_row(r);
    } else {
        if (oldo == ord_cur)
            draw_row(oldr);
        if (o == ord_cur)
            draw_row(r);
    }
}

/* ---------------------------------------------------------------- events */
/* The mouse is read once a refresh on the //e (two READMOUSE calls in a
 * row lose part of the motion: robotspacestation/src/ui.c), on every call
 * on the //c (its firmware counts the motion under interrupt). m_sample
 * also runs between the rows of a long redraw: no refresh goes unread
 * (a2shot's closed loop and a real hand alike) and a press made meanwhile
 * is latched where it happened. */
static unsigned char m_old, m_latch, m_lx, m_ly, m_drag, m_dx, m_dy, vbl_gate, vbl_armed;
static void m_sample(void)
{
    unsigned char b;
    if (!mouse_slot)
        return;
    if (vbl_gate) {
        if (*(volatile unsigned char *)0xC019 & 0x80) {
            vbl_armed = 1;              /* the picture: armed */
            return;
        }
        if (!vbl_armed)                 /* the blank, already read */
            return;
        vbl_armed = 0;
    }
    mouse_read();
    b = mouse_buttons & 0x80;
    if (b && !m_old && !m_latch) {
        m_latch = 1;
        m_lx = mouse_x >> 1;
        m_ly = mouse_y >> 3;
    } else if (b && m_old && ((mouse_x >> 1) != m_dx || (mouse_y >> 3) != m_dy)) {
        m_drag = 1;                     /* held on another cell */
        m_dx = mouse_x >> 1;
        m_dy = mouse_y >> 3;
    }
    m_old = b;
}

/* A key, or a mouse event (K_CLICK, K_DRAG: the cell in ev_x, ev_y), 0 =
 * none; the pointer follows the mouse. */
static unsigned char event(void)
{
    unsigned char k = kbd_get(), x, y;
    if (k || !mouse_slot)
        return k;
    m_sample();
    x = mouse_x >> 1;
    y = mouse_y >> 3;
    if (x != ptr_x || y != ptr_y) {
        ptr_hide();
        ptr_x = x;
        ptr_y = y;
    }
    ptr_show();
    if (m_latch) {
        m_latch = 0;
        ev_x = m_dx = m_lx;
        ev_y = m_dy = m_ly;
        m_drag = 0;
        return K_CLICK;
    }
    if (m_drag) {
        m_drag = 0;
        ev_x = m_dx;
        ev_y = m_dy;
        return K_DRAG;
    }
    return 0;
}

/* ---------------------------------------------------------------- prompts */
unsigned char wait_key(void)
{
    unsigned char k;
    while (!(k = event()))
        poll_play();
    return k;
}

unsigned char __fastcall__ ask(const char *q)
{
    unsigned char k;
    say(q);
    redraw();
    k = wait_key();
    say("");
    return k == 'Y' || k == 'y';
}

/* Edit input_buf (max chars) on the message line; 0 = cancelled. */
unsigned char input(const char *prompt, unsigned char max, unsigned char upper)
{
    unsigned char n = strlen(input_buf), k, x = strlen(prompt) + 2;
    for (;;) {
        clear_line(MSG_Y);
        puts_at(1, MSG_Y, prompt);
        puts_at(x, MSG_Y, input_buf);
        txt_mode = 1;
        txt_putc(' ');
        txt_mode = 0;
        k = wait_key();
        if (k == K_RET)
            break;
        if (k == K_ESC) {
            say("");
            return 0;
        }
        if ((k == K_DEL || k == K_LEFT) && n)
            input_buf[--n] = 0;
        else if (k >= ' ' && k < 0x7F && n < max) {
            if (upper && k >= 'a' && k <= 'z')
                k -= 32;
            input_buf[n++] = k;
            input_buf[n] = 0;
        }
    }
    say("");
    return 1;
}

/* ---------------------------------------------------------------- grid editing */
static int piano(unsigned char k)
{
    const char *p = strchr(piano_lo, k);
    if (k && p)
        return p - piano_lo;
    p = strchr(piano_hi, k);
    if (k && p)
        return 12 + (p - piano_hi);
    return -1;
}

signed char __fastcall__ hexval(unsigned char k)
{
    const char *p = strchr(hexd, k);
    return k && p ? p - hexd : -1;
}

static void changed(void)
{
    grid_dirty = 1;
    touched();
    rd |= RD_HEAD;
}

static void edited(void)
{
    changed();
    draw_row(cur_row);
    move_row(1);
}

void __fastcall__ ensure_ins(unsigned char i)
{
    while (s_nins < i) {
        ins_default(s_nins);
        ++s_nins;
        rd |= RD_INS;
    }
}

/* the cell's bytes kept for ^Z */
static void undo_cell(unsigned char *c)
{
    u_kind = 1;
    u_pat = cur_pat;
    u_v = cur_v;
    u_r = cur_row;
    memcpy(u_cell, c, CELL);
}

/* the whole pattern kept for ^Z (aux AUX_UNDO) */
static void undo_pat(void)
{
    u_kind = 2;
    u_pat = cur_pat;
    ax(grid, AUX_UNDO, s_voices * TRACK, 1);
}

static unsigned char grid_key(unsigned char k)
{
    unsigned char *c = CELLP(cur_v, cur_row);
    unsigned char t[CELL];
    int n;
    signed char h;
    unsigned char fx = (c[1] >> 4);
    memcpy(t, c, CELL);
    switch (cur_f) {
    case 0:
        if (k == '1') {
            c[0] = NOTE_OFF;
            c[1] &= 0xF0;
            break;
        }
        n = piano(k);
        if (n < 0)
            return 0;
        n += octave * 12;
        if (n > 95)
            return 1;
        ensure_ins(cur_ins);
        c[0] = n;
        c[1] = (c[1] & 0xF0) | cur_ins;
        audition(cur_ins, n);
        break;
    case 1:
        h = hexval(k);
        if (h < 0)
            return 0;
        if (h)
            ensure_ins(h);
        c[1] = (c[1] & 0xF0) | h;
        break;
    case 2: {
        const char *p = strchr(fx_letters, k);
        if (!k || !p)
            return 0;
        fx = p - fx_letters;
        c[1] = (c[1] & 15) | (fx + 1) << 4;
        if (!fx)
            c[2] = 0;
        else if ((fx == 4 || fx == 5) && !c[2])
            c[2] = 1;
        break;
    }
    default:
        h = hexval(k);
        if (h < 0)
            return 0;
        if (fx <= 1) {
            say(fx ? "EFFECT O TAKES NO PARAMETER" : "TYPE AN EFFECT LETTER FIRST: O A U D F S N E");
            return 1;
        }
        if (cur_f == 3)
            c[2] = (c[2] & 15) | h << 4;
        else
            c[2] = (c[2] & 0xF0) | h;
        if ((fx == 5 || fx == 6) && !c[2])
            c[2] = 1;
    }
    undo_cell(t);
    edited();
    return 1;
}

static void clear_field(void)
{
    unsigned char *c = CELLP(cur_v, cur_row);
    undo_cell(c);
    if (cur_f == 0) {
        c[0] = NOTE_EMPTY;
        c[1] &= 0xF0;
    } else if (cur_f == 1)
        c[1] &= 0xF0;
    else {
        c[1] &= 15;
        c[2] = 0;
    }
    edited();
}

static void shift_rows(unsigned char ins)
{
    unsigned char v;
    unsigned char *t;
    undo_pat();
    for (v = 0; v < s_voices; ++v) {
        if (ins) {
            memmove(CELLP(v, cur_row + 1), CELLP(v, cur_row), (MAXROWS - 1 - cur_row) * CELL);
            t = CELLP(v, cur_row);
        } else {
            memmove(CELLP(v, cur_row), CELLP(v, cur_row + 1), (MAXROWS - 1 - cur_row) * CELL);
            t = CELLP(v, MAXROWS - 1);
        }
        t[0] = NOTE_EMPTY;
        t[1] = t[2] = 0;
    }
    changed();
    rd |= RD_GRID;
}

static void field(signed char d)
{
    if (d > 0) {
        if (++cur_f == 5) {
            cur_f = 0;
            if (++cur_v == s_voices)
                cur_v = 0;
        }
    } else if (cur_f-- == 0) {
        cur_f = 4;
        cur_v = cur_v ? cur_v - 1 : s_voices - 1;
    }
    if (sel_on)
        rd |= RD_GRID;
    else
        draw_row(cur_row);
}

/* ---------------------------------------------------------------- blocks */
static void sel_off(void)
{
    if (sel_on) {
        sel_on = 0;
        rd |= RD_GRID;
    }
}

static void block_copy(void)
{
    unsigned char v;
    sel_calc();
    clip_v = sv1 - sv0 + 1;
    clip_r = sr1 - sr0 + 1;
    for (v = 0; v < clip_v; ++v)
        ax(CELLP(sv0 + v, sr0), AUX_CLIP + v * TRACK, clip_r * CELL, 1);
}

/* op: 0 cut, 1 paste, else a transposition (semitones + 100) */
static void block_op(unsigned char op)
{
    unsigned char v, r, n, *c;
    if (op == 1 && !clip_v) {
        say("NOTHING TO PASTE: ^C OR ^X A BLOCK FIRST");
        return;
    }
    undo_pat();
    sel_calc();
    if (op == 1) {
        n = s_rows - sr0;
        if (n > clip_r)
            n = clip_r;
        for (v = 0; v < clip_v && sv0 + v < s_voices; ++v)
            ax(CELLP(sv0 + v, sr0), AUX_CLIP + v * TRACK, n * CELL, 0);
    } else
        for (v = sv0; v <= sv1; ++v)
            for (r = sr0; r <= sr1; ++r) {
                c = CELLP(v, r);
                if (!op) {
                    c[0] = NOTE_EMPTY;
                    c[1] = c[2] = 0;
                } else if (c[0] < NOTE_OFF) {
                    n = c[0] + op - 100;
                    if (n < NOTE_OFF)
                        c[0] = n;
                }
            }
    changed();
    rd |= RD_GRID;
}

static void ord_go(unsigned char i);

static void undo(void)
{
    unsigned char t[CELL], *c, i;
    if (!u_kind) {
        say("NOTHING TO UNDO");
        return;
    }
    if (u_pat != cur_pat) {
        for (i = 0; i < s_nord && s_order[i] != u_pat; ++i)
            ;
        if (i < s_nord)
            ord_go(i);
        else
            pat_select(u_pat);
        rd |= RD_ALL;
    }
    if (u_kind == 1) {
        c = CELLP(u_v, u_r);
        memcpy(t, c, CELL);
        memcpy(c, u_cell, CELL);
        memcpy(u_cell, t, CELL);
        cur_v = u_v;
        cur_row = u_r;
        view();
    } else {
        ax(scratch, AUX_UNDO, s_voices * TRACK, 0);
        ax(grid, AUX_UNDO, s_voices * TRACK, 1);
        memcpy(grid, scratch, s_voices * TRACK);
    }
    changed();
    rd |= RD_GRID;
    say("UNDONE (^Z AGAIN: REDO)");
}

/* ---------------------------------------------------------------- order list */
static void order_changed(void)
{
    touched();
    if (s_order[ord_cur] != cur_pat) {
        pat_select(s_order[ord_cur]);
        rd |= RD_GRID;
        view();
    }
    rd |= RD_ORDER | RD_HEAD;
}

static void ord_go(unsigned char i)
{
    ord_cur = i;
    if (s_order[ord_cur] != cur_pat) {
        pat_select(s_order[ord_cur]);
        rd |= RD_GRID | RD_HEAD;
        view();
    }
    rd |= RD_ORDER;
}

static void set_entry(unsigned char p)
{
    s_order[ord_cur] = p;
    order_changed();
}

static void ord_insert(unsigned char p)
{
    memmove(s_order + ord_cur + 1, s_order + ord_cur, s_nord - ord_cur);
    ++s_nord;
    if (s_loop != 0xFF && s_loop > ord_cur)
        ++s_loop;
    s_order[++ord_cur] = p;
    order_changed();
}

/* The entry's pattern out of the song: its entries go, the patterns after
 * it one number down. */
static void ord_kill(void)
{
    unsigned char p = s_order[ord_cur], i, j = 0, q, nl = 0xFF;
    if (s_npat == 1 || !ask("DELETE THIS PATTERN AND ITS ENTRIES? (Y/N)"))
        return;
    stop();
    pat_delete(p);
    for (i = 0; i < s_nord; ++i) {
        if (i == s_loop)
            nl = j;
        q = s_order[i];
        if (q != p)
            s_order[j++] = q > p ? q - 1 : q;
    }
    if (!j)
        s_order[j++] = 0;
    if (nl != 0xFF && nl >= j)
        nl = j - 1;
    s_nord = j;
    s_loop = nl;
    if (ord_cur >= j)
        ord_cur = j - 1;
    u_kind = 0;
    cur_pat = 0xFF;
    order_changed();
    rd |= RD_ALL;
}

static unsigned char order_key(unsigned char k)
{
    unsigned char p = s_order[ord_cur];
    switch (k) {
    case K_UP:
        if (ord_cur)
            ord_go(ord_cur - 1);
        return 1;
    case K_DOWN:
        if (ord_cur + 1 < s_nord)
            ord_go(ord_cur + 1);
        return 1;
    case K_LEFT:
    case '-':
        if (p)
            set_entry(p - 1);
        return 1;
    case K_RIGHT:
    case '=':
    case '+':
        if (p + 1 < s_npat)
            set_entry(p + 1);
        else if (pat_new(0) != 0xFF)
            set_entry(p + 1);
        else
            say("NO ROOM FOR ANOTHER PATTERN");
        return 1;
    case 'N':
    case 'C':
    case 'I':
        p = pat_new(k == 'C');
        if (p == 0xFF)
            say("NO ROOM FOR ANOTHER PATTERN");
        else if (k == 'I' && s_nord < 255)
            ord_insert(p);
        else
            set_entry(p);
        return 1;
    case 'D':
        ord_kill();
        return 1;
    case CTRL('O'):
        if (s_nord < 255)
            ord_insert(p);
        return 1;
    case CTRL('Y'):
    case K_DEL:
        if (s_nord == 1)
            return 1;
        memmove(s_order + ord_cur, s_order + ord_cur + 1, s_nord - ord_cur - 1);
        --s_nord;
        if (s_loop != 0xFF && s_loop > ord_cur)
            --s_loop;
        if (s_loop != 0xFF && s_loop >= s_nord)
            s_loop = s_nord - 1;
        if (ord_cur >= s_nord)
            ord_cur = s_nord - 1;
        order_changed();
        return 1;
    case 'L':
        s_loop = s_loop == ord_cur ? 0xFF : ord_cur;
        touched();
        rd |= RD_ORDER | RD_HEAD;
        return 1;
    case K_TAB:
    case K_RET:
    case K_PAT:
        focus = 0;
        rd |= RD_ORDER | RD_HEAD;
        draw_row(cur_row);
        return 1;
    }
    return 0;
}

/* ---------------------------------------------------------------- help */
/* The help pages (tools/help.py: MBT.HELP, 4 words: where the 3 pages
 * start and end), read into the song buffer at boot, kept in aux memory,
 * a page shown through the grid buffer (its pattern is fetched again). */
static unsigned help_off[4];

static void help_load(void)
{
    static const char name[] = "\010MBT.HELP";
    prodos_file_name = (void *)name;
    prodos_file_iobuf = file_iobuf;
    prodos_file_buffer = song_buf;
    prodos_file_length = HELP_MAX;
    if (!prodos_load_free() && prodos_file_actual < HELP_MAX) {
        memcpy(help_off, song_buf, 8);
        ax(song_buf, AUX_HELP, prodos_file_actual, 1);
    }
}

/* The overlays (MBT.OVL: OVL1 then OVL2, OVL_SIZE each), read into the
 * song buffer at boot, kept in the aux language card. */
static unsigned char ovl_load(void)
{
    static const char name[] = "\007MBT.OVL";
    prodos_file_name = (void *)name;
    prodos_file_iobuf = file_iobuf;
    prodos_file_buffer = song_buf;
    prodos_file_length = 2 * OVL_SIZE;
    if (prodos_load_free() || prodos_file_actual != 2 * OVL_SIZE)
        return 0;
    ax(song_buf, LC_OVL, 2 * OVL_SIZE, 3);
    return 1;
}

void help_page(unsigned char page, unsigned char x, unsigned char y)
{
    const char *p = (const char *)grid, *end;
    unsigned n = help_off[page + 1] - help_off[page];
    if (!help_off[0]) {
        puts_at(x, y, "(MBT.HELP IS NOT ON THE DISK)");
        return;
    }
    pat_flush();
    ax(grid, AUX_HELP + help_off[page], n, 0);
    for (end = p + n; p < end; p += strlen(p) + 1)
        puts_at(x, y++, p);
    pat_select(cur_pat);
}

/* page 0, then page 2 (page 1: the instrument editor's keys) */
static void help(void)
{
    unsigned char k;
    screen = 2;
    for (k = 0; k < 3; k += 2) {
        txt_init();
        txt_mode = 1;
        blank(80);
        memcpy(line, k ? " MB TRACKER  HELP 2/2   (ANY KEY: BACK)" : " MB TRACKER  HELP 1/2   (ANY KEY: MORE)", 39);
        puts_at(0, 0, line);
        txt_mode = 0;
        help_page(k, 0, 2);
        wait_key();
    }
    full();
}

void after_load(void)
{
    ord_cur = ord_top = 0;
    cur_row = vtop = 0;
    cur_v = cur_f = 0;
    focus = 0;
    modified = 0;
    sel_on = u_kind = 0;
    if (cur_ins > s_nins)
        cur_ins = 1;
    layout();
    full();
}

/* ---------------------------------------------------------------- the mouse */
/* A press: on the bar its key, in the grid the cursor there (and the
 * anchor of a drag: a block), on a row number that row (the first and
 * last ones visible: 16 rows up / down), in the order list its entry, on
 * an instrument the one for new notes (on it again: its editor), on a
 * voice's name its mute. */
static void key(unsigned char k);

static void click(void)
{
    unsigned char x = ev_x, y = ev_y, k, v, f, r;
    drag = 0;
    if (y == KEYS_Y) {
        k = seg_at(main_bar, x);
        if (k < 9)
            key(main_keys[k]);
        return;
    }
    if (y == 2) {
        if (x >= gx && (x - gx) / cw < s_voices)
            key(mute_keys[(x - gx) / cw]);
        return;
    }
    if (y < GRID_Y || y >= GRID_Y + GRID_H)
        return;
    r = y - GRID_Y;
    if (x >= ins_x) {
        if (r < MAXINS) {
            if (r + 1 == cur_ins && cur_ins <= s_nins)
                key(CTRL('E'));
            else {
                cur_ins = r + 1;
                rd |= RD_HEAD | RD_INS;
            }
        }
        return;
    }
    if (x >= ord_x) {
        r += ord_top;
        if (r < s_nord) {
            focus = 1;
            ord_go(r);
            rd |= RD_HEAD;
            draw_row(cur_row);
        }
        return;
    }
    r += vtop;
    if (r >= s_rows || x >= gw)
        return;
    if (focus)
        key(K_PAT);
    sel_off();
    if (x < gx) {
        if (y == GRID_Y)
            key('[');
        else if (y == GRID_Y + GRID_H - 1)
            key(']');
        else
            goto_row(r);
        return;
    }
    x -= gx;
    v = x / cw;
    if (v >= s_voices)
        return;
    x -= v * cw;
    for (f = 4; f && x < fx_x[f]; --f)
        ;
    cur_v = sel_v = v;
    cur_f = f;
    sel_r = r;
    draw_row(cur_row);
    goto_row(r);
    drag = 1;
}

/* held from a grid cell to another: the block from the anchor to it */
static void dragged(void)
{
    unsigned char x = ev_x, r = ev_y - GRID_Y + vtop, v;
    if (!drag || x < gx || x >= gw || ev_y < GRID_Y || ev_y >= GRID_Y + GRID_H || r >= s_rows)
        return;
    v = (x - gx) / cw;
    if (v >= s_voices)
        return;
    sel_on = 1;
    cur_v = v;
    goto_row(r);
    rd |= RD_GRID;
}

/* ---------------------------------------------------------------- keys */
static void key(unsigned char k)
{
    signed char d;
    const char *p;
    if (k >= 'a' && k <= 'z')
        k -= 32;
    if (k == K_CLICK) {
        click();
        return;
    }
    if (k == K_DRAG) {
        dragged();
        return;
    }
    if (focus == 1 && order_key(k))
        return;
    switch (k) {
    case K_UP:
        move_row(-1);
        return;
    case K_DOWN:
        move_row(1);
        return;
    case '[':
        move_row(-16);
        return;
    case ']':
        move_row(16);
        return;
    case K_LEFT:
        field(-1);
        return;
    case K_RIGHT:
        field(1);
        return;
    case K_PAT:
        return;
    case K_TAB:
    case K_ORD:
        focus = 1;
        rd |= RD_ORDER | RD_HEAD;
        draw_row(cur_row);
        return;
    case '-':
        if (octave)
            --octave;
        rd |= RD_HEAD;
        return;
    case '=':
        if (octave < 7)
            ++octave;
        rd |= RD_HEAD;
        return;
    case '<':
    case '>':
        if (k == '<' && cur_ins > 1)
            --cur_ins;
        if (k == '>' && cur_ins < MAXINS)
            ++cur_ins;
        rd |= RD_HEAD | RD_INS;
        return;
    case '_':
    case '+':
        if (k == '_' && s_speed > 1)
            --s_speed;
        if (k == '+' && s_speed < 255)
            ++s_speed;
        touched();
        rd |= RD_HEAD;
        return;
    case '{':
    case '}':
        if (k == '{' && s_rows > 1)
            --s_rows;
        if (k == '}' && s_rows < MAXROWS)
            ++s_rows;
        touched();
        view();
        rd |= RD_HEAD | RD_GRID;
        return;
    case K_ESC:
        sel_off();
    case ' ':
        stop();
        return;
    case '?':
        help();
        return;
    case CTRL('P'):
        play(1);
        return;
    case CTRL('R'):
        play(2);
        return;
    case CTRL('F'):
        follow ^= 1;
        rd |= RD_HEAD;
        return;
    case CTRL('E'):
        ovl_use(1);
        ins_editor();
        full();
        return;
    case CTRL('L'):
        ovl_use(2);
        load();
        return;
    case CTRL('S'):
        ovl_use(2);
        save();
        return;
    case CTRL('N'):
        if (ask("NEW SONG: FORGET THIS ONE? (Y/N)")) {
            k = ask("6 VOICES (BOTH CHIPS)? (Y: 6, N: 3)");
            stop();
            song_new(k ? 6 : 3);
            cur_file[0] = 0;
            after_load();
        }
        return;
    case CTRL('W'):
        ovl_use(1);
        voices();
        return;
    case CTRL('Q'):
        if (ask("QUIT TO PRODOS? (Y/N)"))
            exit(0);
        return;
    case CTRL('O'):
        shift_rows(1);
        return;
    case CTRL('Y'):
        shift_rows(0);
        return;
    case CTRL('T'):
    case CTRL('A'): {
        char *s = k == CTRL('T') ? s_name : s_author;
        strcpy(input_buf, s);
        if (input(k == CTRL('T') ? "SONG NAME:" : "AUTHOR:", 31, 0)) {
            strcpy(s, input_buf);
            touched();
            rd |= RD_HEAD;
        }
        return;
    }
    case K_DEL:
    case '.':
        clear_field();
        return;
    case CTRL('B'):
        if (sel_on)
            sel_off();
        else {
            sel_on = 1;
            sel_v = cur_v;
            sel_r = cur_row;
            rd |= RD_GRID;
        }
        return;
    case CTRL('C'):
        block_copy();
        say("BLOCK COPIED");
        return;
    case CTRL('X'):
        block_copy();
        block_op(0);
        return;
    case CTRL('V'):
        block_op(1);
        return;
    case ';':
    case '\'':
    case ':':
    case '"':
        block_op(k == ';' ? 99 : k == '\'' ? 101 : k == ':' ? 88 : 112);
        return;
    case CTRL('Z'):
        undo();
        return;
    }
    p = strchr(mute_keys, k);
    if (k && p) {
        d = p - mute_keys;
        if (d < s_voices) {
            snd_mute ^= 1 << d;
            if (slot)
                snd_mute_set(snd_mute);
            rd |= RD_HEAD;
        }
        return;
    }
    grid_key(k);
}

void game_shutdown(void)
{
    mouse_close();
    if (irq_on)
        snd_shutdown();
    if (claimed)
        prodos_video_release();
}

void main(void)
{
    unsigned char k;
    txt_init();
    claimed = prodos_video_claim(PD_VIDEO_DISCARD_RAM) == PD_VIDEO_OK;
    help_load();
    if (!ovl_load()) {
        puts_at(0, 0, "MBT.OVL IS MISSING");
        for (;;)
            ;
    }
    slot = snd_detect();            /* before the mouse (the //c's 4c) */
    if (slot) {
        irq_on = snd_start();
        if (!irq_on)
            slot = 0;
    }
    if (mouse_init()) {
        mouse_wide();
        vbl_gate = *(unsigned char *)0xFBC0 == 0xE0;   /* enhanced //e */
    }
    song_new(3);
    after_load();
    say(slot ? "CTRL-L: LOAD DEMO.AYS    ?: ALL THE KEYS" : "NO MOCKINGBOARD FOUND: EDITING AND FILES ONLY    ?: ALL THE KEYS");
    for (;;) {
        if (rd)
            redraw();
        k = event();            /* (kbd_idle: every key handled, drawn) */
        if (k)
            key(k);
        else
            poll_play();
    }
}
