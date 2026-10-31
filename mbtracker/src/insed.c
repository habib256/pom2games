/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* insed.c — MB TRACKER's instrument editor: one row a tick (volume, tone,
 * noise, envelope, noise period), the loop, the envelope shape and period,
 * the name, an audition. Overlay OVL1 (src/mbt.cfg): brought from aux
 * memory by main.c before ins_editor() runs. Keys and mouse: a click on a
 * field moves the cursor there, on the bottom bar presses its key. */
#include <string.h>
#include "mbt.h"
#include "ui.h"

#pragma code-name (push, "OVL1")
#pragma rodata-name (push, "OVL1")

/* ---------------------------------------------------------------- instrument editor */
static signed char e_row;     /* -1: the envelope line */
static unsigned char e_f, e_top;
static const unsigned char e_x[6] = { 7, 12, 18, 23, 27, 28 };
static const unsigned char h_x[3] = { 17, 28, 29 };
static const char e_bar[] = " RETURN LISTEN  ESC BACK  < PREV  > NEXT  ^T NAME  ^O ^Y TICK";
static const unsigned char e_keys[6] = { K_RET, K_ESC, '<', '>', CTRL('T'), CTRL('O') };

/* the field of column x on a row of fields at xs[0..n] */
static unsigned char e_field(const unsigned char *xs, unsigned char n)
{
    while (n && ev_x < xs[n])
        --n;
    return n;
}

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
    clear_line(KEYS_Y);
    puts_at(0, KEYS_Y, e_bar);
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

void ins_editor(void)
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
        old = e_row;
        if (k == K_CLICK) {
            k = 0;
            if (ev_y == KEYS_Y) {
                b = seg_at(e_bar, ev_x);
                if (b < 6)
                    k = e_keys[b];
            } else if (ev_y == 3 && ev_x >= h_x[0]) {
                e_row = -1;
                e_f = e_field(h_x, 2);
            } else if (ev_y >= 6 && ev_y < 22 && ev_x < 33 && e_top + ev_y - 6 < n->n) {
                e_row = e_top + ev_y - 6;
                e_f = e_field(e_x, 5);
            }
        }
        if (k >= 'a' && k <= 'z')
            k -= 32;
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
