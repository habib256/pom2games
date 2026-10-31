/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* MB TRACKER — a Mockingboard tracker for the //e / //c 128 KB (ProDOS 8,
 * 80 columns). Edits AYS v1 songs (dev/lib/apple2/AYSONG_FORMAT.md), plays
 * them with dev/lib/apple2/aysong.asm on the mb_irq.asm 50 Hz interrupt.
 * Screens: the pattern grid with the order list and the instruments beside
 * it, the instrument editor, the file list, the help. Only what changes is
 * redrawn (a row, a field, a panel). */
#include <stdlib.h>
#include <string.h>
#include "prodos.h"
#include "mbt.h"

#define K_LEFT 0x08
#define K_RIGHT 0x15
#define K_UP 0x0B
#define K_DOWN 0x0A
#define K_RET 0x0D
#define K_ESC 0x1B
#define K_TAB 0x09
#define K_DEL 0x7F
#define CTRL(c) ((c) & 0x1F)

#define GRID_Y 3
#define GRID_H 19
#define MSG_Y 22
#define KEYS_Y 23

#define RD_HEAD 1
#define RD_GRID 2
#define RD_ORDER 4
#define RD_INS 8
#define RD_MSG 16
#define RD_KEYS 32
#define RD_ALL 63

static unsigned char slot, irq_on, claimed;
static unsigned char rd;
static unsigned char screen;             /* 0 the grid, else another screen */
static unsigned char focus;               /* 0 grid, 1 order list */
static unsigned char cur_row, cur_v, cur_f, vtop, ord_cur, ord_top;
static unsigned char octave = 4, cur_ins = 1, follow = 1, modified;
static unsigned char playing;             /* 0, 1 song, 2 pattern loop */
static unsigned char play_o = 0xFF, play_r = 0xFF;
static char msg[80];
static char line[81];
static char input_buf[33];
#pragma bss-name (push, "LOW8BSS")
static unsigned char aud_buf[200];
#pragma bss-name (pop)

static const char note_names[] = "C-C#D-D#E-F-F#G-G#A-A#B-";
static const char fx_letters[] = "OAUDFSNE";
static const char hexd[] = "0123456789ABCDEF";
static const char piano_lo[] = "ZSXDCVGBHNJM,";
static const char piano_hi[] = "Q2W3ER5T6Y7UI";
static const char mute_keys[] = "!@#$%^";
static const unsigned char fx_x[5] = { 0, 4, 6, 7, 8 };   /* field -> column in a cell */
static const unsigned char fx_w[5] = { 3, 1, 1, 1, 1 };

/* ---------------------------------------------------------------- text helpers */
static void puts_at(unsigned char x, unsigned char y, const char *s)
{
    AT(x, y);
    txt_puts(s);
}

static void clear_line(unsigned char y)
{
    AT(0, y);
    txt_fill(' ', 80);
}

static void hex2(char *d, unsigned char b)
{
    d[0] = hexd[b >> 4];
    d[1] = hexd[b & 15];
}

static void dec2(char *d, unsigned char b)
{
    d[0] = '0' + b / 10;
    d[1] = '0' + b % 10;
}

static void dec3(char *d, unsigned char b)
{
    d[0] = '0' + b / 100;
    dec2(d + 1, b % 100);
}

static void say(const char *s)
{
    strcpy(msg, s);
    rd |= RD_MSG;
}

static void touched(void)
{
    song_len = 0;
    modified = 1;
}

static void blank(unsigned char n)
{
    memset(line, ' ', n);
    line[n] = 0;
}

/* ---------------------------------------------------------------- the grid */
static unsigned char vfirst(void)
{
    return cur_v >= 3 ? 3 : 0;
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
    d[3] = ' ';
    d[4] = (c[1] & 15) ? hexd[c[1] & 15] : '.';
    d[5] = ' ';
    if (fxc) {
        d[6] = fx_letters[fxc - 1];
        hex2(d + 7, c[2]);
    } else
        memcpy(d + 6, "...", 3);
}

static void draw_row(unsigned char r)
{
    unsigned char y, j, v, x;
    if (screen || r < vtop || r >= vtop + GRID_H)
        return;
    y = GRID_Y + r - vtop;
    blank(39);
    if (r < s_rows) {
        dec2(line, r);
        if (playing && r == play_r && play_o == ord_cur)
            line[2] = '>';
        for (j = 0; j < 3; ++j) {
            v = vfirst() + j;
            x = 4 + 12 * j;
            if (v < s_voices)
                cell_text(line + x, CELLP(v, r));
            line[x + 10] = '|';
        }
    }
    txt_mode = 0;
    puts_at(0, y, line);
    if (r == cur_row && r < s_rows) {
        txt_mode = 1;
        AT(0, y);
        txt_putc(line[0]);
        txt_putc(line[1]);
        if (focus == 0) {
            x = 4 + 12 * (cur_v - vfirst()) + fx_x[cur_f];
            line[x + fx_w[cur_f]] = 0;
            puts_at(x, y, line + x);
        }
        txt_mode = 0;
    }
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
    unsigned char k;
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
    memcpy(line, "ROW", 3);
    for (k = 0; k < 3; ++k) {
        unsigned char v = vfirst() + k;
        if (v >= s_voices)
            continue;
        memcpy(line + 4 + 12 * k, "VOICE", 5);
        line[10 + 12 * k] = '1' + v;
        if (snd_mute >> v & 1)
            memcpy(line + 12 + 12 * k, "MUTE", 4);
    }
    memcpy(line + 41, focus ? "ORDER*" : "ORDER", focus ? 6 : 5);
    memcpy(line + 55, "INSTRUMENTS", 11);
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
        puts_at(41, GRID_Y + y, line);
    }
    txt_mode = 0;
}

static void draw_ins(void)
{
    unsigned char i;
    for (i = 1; i <= MAXINS; ++i) {
        blank(24);
        line[0] = i == cur_ins ? '>' : ' ';
        line[1] = hexd[i];
        if (i <= s_nins)
            memcpy(line + 3, s_ins[i - 1].name[0] ? s_ins[i - 1].name : "(no name)",
                   strlen(s_ins[i - 1].name[0] ? s_ins[i - 1].name : "(no name)"));
        else
            line[3] = '-';
        puts_at(55, GRID_Y + i - 1, line);
    }
}

static void draw_keys(void)
{
    txt_mode = 1;
    blank(80);
    memcpy(line, " ^P PLAY  ^R LOOP  SPACE STOP  TAB ORDER  ^E INSTRUMENT  ^L LOAD  ^S SAVE  ? HELP", 78);
    puts_at(0, KEYS_Y, line);
    txt_mode = 0;
}

static void redraw(void)
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

static void full(void)
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

static void stop(void)
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

static void audition(unsigned char ins, unsigned char note)
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

/* ---------------------------------------------------------------- prompts */
static unsigned char wait_key(void)
{
    unsigned char k;
    while (!(k = kbd_get()))
        poll_play();
    return k;
}

static unsigned char ask(const char *q)
{
    unsigned char k;
    say(q);
    redraw();
    k = wait_key();
    say("");
    return k == 'Y' || k == 'y';
}

/* Edit input_buf (max chars) on the message line; 0 = cancelled. */
static unsigned char input(const char *prompt, unsigned char max, unsigned char upper)
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

static signed char hexval(unsigned char k)
{
    const char *p = strchr(hexd, k);
    return k && p ? p - hexd : -1;
}

static void edited(void)
{
    grid_dirty = 1;
    touched();
    rd |= RD_HEAD;
    draw_row(cur_row);
    move_row(1);
}

static void ensure_ins(unsigned char i)
{
    while (s_nins < i) {
        ins_default(s_nins);
        ++s_nins;
        rd |= RD_INS;
    }
}

static unsigned char grid_key(unsigned char k)
{
    unsigned char *c = CELLP(cur_v, cur_row);
    int n;
    signed char h;
    unsigned char fx = (c[1] >> 4);
    switch (cur_f) {
    case 0:
        if (k == '1') {
            c[0] = NOTE_OFF;
            c[1] &= 0xF0;
            edited();
            return 1;
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
        edited();
        return 1;
    case 1:
        h = hexval(k);
        if (h < 0)
            return 0;
        if (h)
            ensure_ins(h);
        c[1] = (c[1] & 0xF0) | h;
        edited();
        return 1;
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
        edited();
        return 1;
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
        edited();
        return 1;
    }
}

static void clear_field(void)
{
    unsigned char *c = CELLP(cur_v, cur_row);
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
    for (v = 0; v < s_voices; ++v) {
        t = CELLP(v, 0);
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
    grid_dirty = 1;
    touched();
    rd |= RD_GRID | RD_HEAD;
}

static void field(signed char d)
{
    unsigned char ov = vfirst();
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
    if (vfirst() != ov)
        rd |= RD_GRID | RD_HEAD;
    else
        draw_row(cur_row);
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

static void set_entry(unsigned char p)
{
    s_order[ord_cur] = p;
    order_changed();
}

static unsigned char order_key(unsigned char k)
{
    unsigned char p = s_order[ord_cur];
    switch (k) {
    case K_UP:
    case K_DOWN:
        if (k == K_UP && ord_cur)
            --ord_cur;
        else if (k == K_DOWN && ord_cur + 1 < s_nord)
            ++ord_cur;
        if (s_order[ord_cur] != cur_pat) {
            pat_select(s_order[ord_cur]);
            rd |= RD_GRID | RD_HEAD;
            view();
        }
        rd |= RD_ORDER;
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
        p = pat_new(k == 'C');
        if (p == 0xFF)
            say("NO ROOM FOR ANOTHER PATTERN");
        else
            set_entry(p);
        return 1;
    case CTRL('O'):
        if (s_nord == 255)
            return 1;
        memmove(s_order + ord_cur + 1, s_order + ord_cur, s_nord - ord_cur);
        ++s_nord;
        if (s_loop != 0xFF && s_loop > ord_cur)
            ++s_loop;
        ++ord_cur;
        order_changed();
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
        focus = 0;
        rd |= RD_ORDER | RD_HEAD;
        draw_row(cur_row);
        return 1;
    }
    return 0;
}

/* ---------------------------------------------------------------- instrument editor */
static signed char e_row;     /* -1: the envelope line */
static unsigned char e_f, e_top;
static const unsigned char e_x[6] = { 7, 12, 18, 23, 27, 28 };
static const unsigned char h_x[3] = { 17, 28, 29 };

static void e_draw_head(void)
{
    Instrument *n = &s_ins[cur_ins - 1];
    blank(79);
    memcpy(line, "INSTRUMENT", 10);
    line[11] = hexd[cur_ins];
    memcpy(line + 13, "OF", 2);
    line[16] = hexd[s_nins];
    memcpy(line + 20, "NAME:", 5);
    memcpy(line + 26, n->name, strlen(n->name));
    puts_at(0, 2, line);
    blank(40);
    memcpy(line, "ENVELOPE SHAPE:", 15);
    line[17] = n->shape == 0xFF ? '-' : hexd[n->shape];
    memcpy(line + 20, "PERIOD:", 7);
    hex2(line + 28, n->eper);
    puts_at(0, 3, line);
    blank(40);
    memcpy(line, "TICKS", 5);
    dec2(line + 6, n->n);
    memcpy(line + 10, "LOOP AT", 7);
    dec2(line + 18, n->loop);
    puts_at(0, 4, line);
}

static void e_cursor_head(void)
{
    Instrument *n = &s_ins[cur_ins - 1];
    char t[3];
    if (e_row >= 0)
        return;
    t[0] = n->shape == 0xFF ? '-' : hexd[n->shape];
    hex2(t + 1, n->eper);
    txt_mode = 1;
    AT(h_x[e_f], 3);
    txt_putc(t[e_f]);
    txt_mode = 0;
}

static void e_draw_tick(unsigned char k)
{
    Instrument *n = &s_ins[cur_ins - 1];
    unsigned char y, b;
    if (k < e_top || k >= e_top + 16)
        return;
    y = 6 + k - e_top;
    blank(40);
    if (k < n->n) {
        b = n->t[k];
        dec2(line + 1, k);
        line[7] = hexd[b & 15];
        line[12] = b & 0x10 ? '*' : '.';
        line[18] = b & 0x20 ? '*' : '.';
        line[23] = b & 0x40 ? '*' : '.';
        if (n->np[k] == NP_NONE)
            memcpy(line + 27, "--", 2);
        else
            hex2(line + 27, n->np[k]);
        if (k == n->loop)
            memcpy(line + 31, n->loop == n->n - 1 ? "<HOLD" : "<LOOP", 5);
    }
    puts_at(0, y, line);
    if (k == e_row) {
        txt_mode = 1;
        AT(1, y);
        txt_putc(line[1]);
        txt_putc(line[2]);
        AT(e_x[e_f], y);
        txt_putc(line[e_x[e_f]]);
        txt_mode = 0;
    }
}

static void e_draw_ticks(void)
{
    unsigned char k;
    for (k = e_top; k < e_top + 16; ++k)
        e_draw_tick(k);
}

/* The help pages (tools/help.py: MBT.HELP), kept in aux memory from boot
 * and shown through the grid buffer (its pattern is fetched again). */
#define AUX_HELP 0x9800u
static unsigned help_len;

static void help_load(void)
{
    static const char name[] = "\010MBT.HELP";
    prodos_file_name = (void *)name;
    prodos_file_iobuf = file_iobuf;
    prodos_file_buffer = grid;
    prodos_file_length = 2 * MAXVOICES * TRACK;
    if (!prodos_load() && prodos_file_actual < 2 * MAXVOICES * TRACK) {
        help_len = prodos_file_actual;
        ax_main = grid;
        ax_aux = AUX_HELP;
        ax_len = help_len;
        aux_put();
    }
}

static void help_page(unsigned char page, unsigned char x, unsigned char y)
{
    const char *p = (const char *)grid, *end = (const char *)grid + help_len;
    if (!help_len) {
        puts_at(x, y, "(MBT.HELP IS NOT ON THE DISK)");
        return;
    }
    pat_flush();
    ax_main = grid;
    ax_aux = AUX_HELP;
    ax_len = help_len;
    aux_get();
    for (; page && p < end; p += strlen(p) + 1)
        if (*p == 12)
            --page;
    for (; p < end && *p != 12; p += strlen(p) + 1)
        puts_at(x, y++, p);
    pat_select(cur_pat);
}

static void e_full(void)
{
    screen = 1;
    txt_init();
    txt_mode = 1;
    blank(80);
    memcpy(line, " MB TRACKER  INSTRUMENT EDITOR", 30);
    puts_at(0, 0, line);
    txt_mode = 0;
    puts_at(0, 5, "TICK  VOL  TONE  NOISE  ENV  NP");
    help_page(1, 42, 6);
    e_draw_head();
    e_cursor_head();
    e_draw_ticks();
    txt_mode = 1;
    blank(80);
    memcpy(line, " RETURN LISTEN  ESC BACK  < > INSTRUMENT  ^T NAME", 50);
    puts_at(0, KEYS_Y, line);
    txt_mode = 0;
    rd = RD_MSG;
}

static void e_view(void)
{
    unsigned char t = e_top;
    if (e_row < 0)
        return;
    if (e_row < e_top)
        e_top = e_row;
    else if (e_row >= e_top + 16)
        e_top = e_row - 15;
    if (t != e_top)
        e_draw_ticks();
}

static void ins_editor(void)
{
    Instrument *n;
    unsigned char k, old, b;
    signed char h;
    e_row = 0;
    e_f = 0;
    e_top = 0;
    ensure_ins(cur_ins);
    say("");
    e_full();
    for (;;) {
        n = &s_ins[cur_ins - 1];
        if (e_row >= (signed char)n->n)
            e_row = n->n - 1;
        redraw();
        k = wait_key();
        if (k >= 'a' && k <= 'z')
            k -= 32;
        old = e_row;
        h = hexval(k);
        switch (k) {
        case K_ESC:
            return;
        case K_UP:
            if (e_row >= 0) {
                if (--e_row < 0)
                    e_f = 0;
            }
            break;
        case K_DOWN:
            if (e_row + 1 < n->n) {
                if (e_row++ < 0)
                    e_f = 0;
            }
            break;
        case K_LEFT:
            if (e_f)
                --e_f;
            break;
        case K_RIGHT:
            if (e_f < (e_row < 0 ? 2 : 5))
                ++e_f;
            break;
        case '<':
        case '>':
            if (k == '<' && cur_ins > 1)
                --cur_ins;
            else if (k == '>' && cur_ins < MAXINS)
                ensure_ins(++cur_ins);
            e_row = 0;
            e_f = 0;
            e_top = 0;
            e_full();
            continue;
        case '-':
            if (octave)
                --octave;
            break;
        case '=':
        case '+':
            if (octave < 7)
                ++octave;
            break;
        case K_RET:
            audition(cur_ins, octave * 12);
            break;
        case CTRL('T'):
            strcpy(input_buf, n->name);
            if (input("NAME:", 15, 0)) {
                strcpy(n->name, input_buf);
                touched();
            }
            break;
        case 'L':
            if (e_row >= 0) {
                b = n->loop;
                n->loop = e_row;
                touched();
                e_draw_tick(b);
            }
            break;
        case CTRL('O'):
            if (e_row >= 0 && n->n < MAXTICKS) {
                memmove(n->t + e_row + 1, n->t + e_row, n->n - e_row);
                memmove(n->np + e_row + 1, n->np + e_row, n->n - e_row);
                ++n->n;
                if (n->loop > e_row)
                    ++n->loop;
                ++e_row;
                touched();
                e_draw_ticks();
            }
            break;
        case CTRL('Y'):
            if (e_row >= 0 && n->n > 1) {
                memmove(n->t + e_row, n->t + e_row + 1, n->n - e_row - 1);
                memmove(n->np + e_row, n->np + e_row + 1, n->n - e_row - 1);
                --n->n;
                if (n->loop > e_row || n->loop == n->n)
                    --n->loop;
                touched();
                e_draw_ticks();
            }
            break;
        case ' ':
            if (e_row >= 0 && e_f >= 1 && e_f <= 3) {
                n->t[e_row] ^= 0x08 << e_f;
                touched();
            }
            break;
        case K_DEL:
            if (e_row < 0 && e_f == 0)
                n->shape = 0xFF;
            else if (e_row >= 0 && e_f >= 4)
                n->np[e_row] = NP_NONE;
            touched();
            break;
        default:
            if (h < 0)
                break;
            if (e_row < 0) {
                if (e_f == 0)
                    n->shape = h;
                else if (e_f == 1)
                    n->eper = (n->eper & 15) | h << 4;
                else
                    n->eper = (n->eper & 0xF0) | h;
            } else if (e_f == 0)
                n->t[e_row] = (n->t[e_row] & 0xF0) | h;
            else if (e_f >= 4) {
                b = n->np[e_row] == NP_NONE ? 0 : n->np[e_row];
                b = e_f == 4 ? (b & 15) | h << 4 : (b & 0xF0) | h;
                n->np[e_row] = b & 31;
            } else
                break;
            touched();
        }
        e_view();
        e_draw_head();
        e_cursor_head();
        if (old != (unsigned char)e_row)
            e_draw_tick(old);
        if (e_row >= 0)
            e_draw_tick(e_row);
    }
}

/* ---------------------------------------------------------------- help */
static void help(void)
{
    screen = 2;
    txt_init();
    txt_mode = 1;
    blank(80);
    memcpy(line, " MB TRACKER  HELP   (ANY KEY: BACK)", 35);
    puts_at(0, 0, line);
    txt_mode = 0;
    help_page(0, 0, 2);
    wait_key();
    full();
}

/* ---------------------------------------------------------------- files */
static void file_error(unsigned char e)
{
    strcpy(msg, e == 0xFD ? "TOO BIG FOR THE 12 KB BUFFER" : e == 0xFE ? "NOT AN AYS V1 SONG (OR TOO BIG FOR THE EDITOR)"
                                                                       : "PRODOS ERROR $");
    if (e < 0xFD) {
        hex2(msg + 14, e);
        msg[16] = 0;
    }
    rd |= RD_MSG;
}

static void after_load(void)
{
    ord_cur = ord_top = 0;
    cur_row = vtop = 0;
    cur_v = cur_f = 0;
    focus = 0;
    modified = 0;
    if (cur_ins > s_nins)
        cur_ins = 1;
    full();
}

static void load_name(const char *name)
{
    unsigned char e = file_load(name);
    after_load();
    if (e)
        file_error(e);
    else {
        strcpy(msg, "LOADED ");
        strcat(msg, name);
    }
}

static void load(void)
{
    unsigned char e, sel = 0, i, k;
    if (modified && !ask("THE SONG CHANGED. LOAD ANOTHER ONE? (Y/N)"))
        return;
    stop();
    e = dir_list();
    screen = 3;
    txt_init();
    txt_mode = 1;
    blank(80);
    memcpy(line, " MB TRACKER  LOAD A SONG", 24);
    puts_at(0, 0, line);
    txt_mode = 0;
    puts_at(0, 22, "ARROWS: CHOOSE  RETURN: LOAD  /: TYPE A NAME  ESC: CANCEL");
    if (e || !file_count)
        puts_at(2, 2, e ? "CANNOT READ THE CATALOG" : "NO .AYS FILE ON THIS DISK");
    for (;;) {
        for (i = 0; i < file_count; ++i) {
            txt_mode = i == sel;
            AT(2 + (i / 20) * 20, 2 + i % 20);
            txt_puts(file_names[i]);
            txt_mode = 0;
        }
        k = wait_key();
        if (k == K_ESC) {
            full();
            return;
        }
        if (k == K_UP && sel)
            --sel;
        else if (k == K_DOWN && sel + 1 < file_count)
            ++sel;
        else if (k == K_LEFT && sel >= 20)
            sel -= 20;
        else if (k == K_RIGHT && sel + 20 < file_count)
            sel += 20;
        else if (k == K_RET && file_count) {
            load_name(file_names[sel]);
            return;
        } else if (k == '/') {
            input_buf[0] = 0;
            if (input("NAME:", 15, 1))
                load_name(input_buf);
            else
                full();
            return;
        }
    }
}

static unsigned char valid_name(char *s)
{
    unsigned char i, n = strlen(s);
    if (!strchr(s, '.') && n <= 11) {
        strcat(s, ".AYS");
        n += 4;
    }
    if (!n || n > 15 || s[0] < 'A' || s[0] > 'Z')
        return 0;
    for (i = 1; i < n; ++i)
        if (!((s[i] >= 'A' && s[i] <= 'Z') || (s[i] >= '0' && s[i] <= '9') || s[i] == '.'))
            return 0;
    return 1;
}

static void save(void)
{
    unsigned char e;
    strcpy(input_buf, cur_file[0] ? cur_file : "SONG.AYS");
    if (!input("SAVE AS:", 15, 1))
        return;
    if (!valid_name(input_buf)) {
        say("A PRODOS NAME: A LETTER, THEN LETTERS, DIGITS, DOTS (15 AT MOST)");
        return;
    }
    stop();
    pat_flush();
    say("SAVING...");
    redraw();
    e = file_save(input_buf);
    if (e)
        file_error(e);
    else {
        modified = 0;
        strcpy(msg, "SAVED ");
        strcat(msg, input_buf);
        rd |= RD_MSG | RD_HEAD;
    }
}

/* ---------------------------------------------------------------- keys */
static void key(unsigned char k)
{
    signed char d;
    const char *p;
    if (k >= 'a' && k <= 'z')
        k -= 32;
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
    case K_TAB:
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
    case ' ':
    case K_ESC:
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
        ins_editor();
        full();
        return;
    case CTRL('L'):
        load();
        return;
    case CTRL('S'):
        save();
        return;
    case CTRL('N'):
        if (ask("NEW SONG: FORGET THIS ONE? (Y/N)")) {
            stop();
            song_new();
            cur_file[0] = 0;
            after_load();
        }
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
    slot = snd_detect();
    if (slot) {
        irq_on = snd_start();
        if (!irq_on)
            slot = 0;
    }
    song_new();
    rd = RD_ALL;
    say(slot ? "CTRL-L: LOAD DEMO.AYS    ?: ALL THE KEYS" : "NO MOCKINGBOARD FOUND: EDITING AND FILES ONLY    ?: ALL THE KEYS");
    for (;;) {
        if (rd)
            redraw();
        k = kbd_get();          /* (kbd_idle: every key handled, drawn) */
        if (k)
            key(k);
        else
            poll_play();
    }
}
