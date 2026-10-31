/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* fileui.c — MB TRACKER's file screens: the list of the .AYS files to load
 * (arrows or a click; a click on the chosen one loads it), a typed name,
 * the save prompt. Overlay OVL2 (src/mbt.cfg), with files.c. */
#include <string.h>
#include "mbt.h"
#include "ui.h"

#pragma code-name (push, "OVL2")
#pragma rodata-name (push, "OVL2")

static const char l_bar[] = " ARROWS CHOOSE  RETURN LOAD  / TYPE A NAME  ESC CANCEL";
static const unsigned char l_keys[4] = { 0, K_RET, '/', K_ESC };

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

void load(void)
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
    txt_mode = 1;
    puts_at(0, KEYS_Y, l_bar);
    txt_mode = 0;
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
        if (k == K_CLICK) {
            i = ev_y - 2 + (ev_x - 2) / 20 * 20;
            k = 0;
            if (ev_y == KEYS_Y) {
                i = seg_at(l_bar, ev_x);
                if (i < 4)
                    k = l_keys[i];
            } else if (ev_x >= 2 && ev_y >= 2 && ev_y < 22 && (ev_x - 2) % 20 < 15 && i < file_count) {
                if (i == sel)
                    k = K_RET;
                sel = i;
            }
        }
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
            strcpy(input_buf, file_names[sel]);   /* (the decoder's scratch) */
            load_name(input_buf);
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

void save(void)
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
