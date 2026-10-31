/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* files.c — the .AYS files of the boot volume (the prefix sysboot set):
 * the catalog read through OPEN/READ of the directory, whole-file load /
 * save (dev/lib/prodos file.s). MLI buffers in $1000-$1FFF (pages crt0
 * leaves free in the system bitmap); the song is read into song_buf with
 * prodos_load_free (its pages are marked used). The caller stops the
 * music first (the Disk II driver masks interrupts ~1 s). Overlay OVL2 with
 * fileui.c (its initialised parameter blocks come back with it). */
#include <string.h>
#include "prodos.h"
#include "mbt.h"

#pragma code-name (push, "OVL2")
#pragma rodata-name (push, "OVL2")
#pragma data-name (push, "OVL2")

unsigned char file_count;
char cur_file[16];

#pragma bss-name (push, "IOBUF")
unsigned char file_iobuf[1024];
#pragma bss-name (pop)
#pragma bss-name (push, "LOWBSS")
static unsigned char dirbuf[512];
static unsigned char path[66];
#pragma bss-name (pop)

static struct { unsigned char count; void *path; } p_prefix = { 1, path };
static struct { unsigned char count; void *path; void *buf; unsigned char ref; } p_open = { 3, path, file_iobuf, 0 };
static struct { unsigned char count, ref; void *buf; unsigned req, got; } p_read = { 4, 0, dirbuf, 512, 0 };
static struct { unsigned char count, ref; } p_close = { 1, 0 };

static unsigned char is_ays(const unsigned char *n, unsigned char len)
{
    return len > 4 && !memcmp(n + len - 4, ".AYS", 4);
}

unsigned char dir_list(void)
{
    unsigned char err, first = 1, k, per, elen, st, nl;
    unsigned char *e;
    file_count = 0;
    err = prodos_mli(PD_GET_PREFIX, &p_prefix);
    if (err)
        return err;
    if (path[0] > 1 && path[path[0]] == '/')
        --path[0];
    err = prodos_mli(PD_OPEN, &p_open);
    if (err)
        return err;
    p_read.ref = p_close.ref = p_open.ref;
    elen = 0x27;
    per = 13;
    while (!(err = prodos_mli(PD_READ, &p_read)) && p_read.got == 512) {
        if (first) {
            elen = dirbuf[0x23];
            per = dirbuf[0x24];
        }
        e = dirbuf + 4;
        for (k = first; k < per && file_count < MAXFILES; ++k) {
            e = dirbuf + 4 + k * elen;
            if (e + elen > dirbuf + 512)
                break;
            st = e[0] >> 4;
            nl = e[0] & 15;
            if (st >= 1 && st <= 3 && is_ays(e + 1, nl)) {
                memcpy(file_names[file_count], e + 1, nl);
                file_names[file_count++][nl] = 0;
            }
        }
        first = 0;
    }
    prodos_mli(PD_CLOSE, &p_close);
    return err == 0x4C ? 0 : err;
}

static void pname(const char *name)
{
    unsigned char n = strlen(name);
    path[0] = n;
    memcpy(path + 1, name, n);
    prodos_file_name = path;
    prodos_file_iobuf = file_iobuf;
    prodos_file_buffer = song_buf;
}

unsigned char file_load(const char *name)
{
    unsigned char err;
    pname(name);
    prodos_file_length = SONGBUF_SIZE;
    err = prodos_load_free();
    song_len = 0;
    if (err)
        return err;

    if (prodos_file_actual >= SONGBUF_SIZE)
        return 0xFD;
    if (song_decode(prodos_file_actual))
        return 0xFE;
    song_len = prodos_file_actual;
    strcpy(cur_file, name);
    return 0;
}

unsigned char file_save(const char *name)
{
    unsigned char err;
    if (!song_len && !song_encode())
        return 0xFD;
    pname(name);
    prodos_file_length = song_len;
    err = prodos_save();
    if (!err)
        strcpy(cur_file, name);
    return err;
}
