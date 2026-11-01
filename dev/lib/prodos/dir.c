/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* dir.c — the directory of the prefix and ProDOS names, for cc65 programs
 * (prodos.h, PRODOS_DIR_SRCS). ProDOS 8, main RAM. Segments: compile it
 * with the program's --code-name / --rodata-name / --data-name /
 * --bss-name to place it (an overlay: the parameter lists are initialised
 * data, they come back with it). BSS: the 512-byte directory block (also
 * the prefix's path until the OPEN) and 12 bytes. */
#include <string.h>
#include "prodos.h"

unsigned char prodos_dir_count;
static unsigned char block[512];

static struct { unsigned char count; void *path; } p_prefix = { 1, block };
static struct { unsigned char count; void *path; void *buf; unsigned char ref; } p_open = { 3, block, 0, 0 };
static struct { unsigned char count, ref; void *buf; unsigned req, got; } p_read = { 4, 0, block, 512, 0 };
static struct { unsigned char count, ref; } p_close = { 1, 0 };

unsigned char __fastcall__ prodos_dir_list(char *names, unsigned char name_len, unsigned char max,
                                           const char *suffix)
{
    static unsigned char err, first, k, per, elen, nl, sl;
    static unsigned char *e;
    sl = strlen(suffix);
    prodos_dir_count = 0;
    first = 1;
    if (!(err = prodos_mli(PD_GET_PREFIX, &p_prefix))) {
        if (block[0] > 1 && block[block[0]] == '/')
            --block[0];
        p_open.buf = prodos_file_iobuf;
        if (err = prodos_mli(PD_OPEN, &p_open))
            return err;
        p_read.ref = p_close.ref = p_open.ref;
        while (!(err = prodos_mli(PD_READ, &p_read)) && p_read.got == 512) {
            e = block + 4;
            if (first) {                     /* the key block: its header */
                elen = block[0x23];
                per = block[0x24];
                e += elen;
            }
            for (k = first; k < per && prodos_dir_count < max && e + elen <= block + 512; ++k) {
                nl = e[0] & 15;
                if (e[0] >= 0x10 && e[0] < 0x40 && nl > sl && !memcmp(e + 1 + nl - sl, suffix, sl)) {
                    memcpy(names, e + 1, nl);
                    names[nl] = 0;
                    names += name_len;
                    ++prodos_dir_count;
                }
                e += elen;
            }
            first = 0;
        }
        prodos_mli(PD_CLOSE, &p_close);
        if (err == 0x4C)
            err = 0;
    }
    return err;
}

unsigned char __fastcall__ prodos_name_valid(const char *s)
{
    static unsigned char n, c;
    if ((unsigned char)(*s - 'A') > 'Z' - 'A')
        return 0;
    for (n = 1; c = *++s; ++n)
        if (n == 15 || ((unsigned char)(c - 'A') > 'Z' - 'A' && (unsigned char)(c - '0') > 9 && c != '.'))
            return 0;
    return 1;
}
