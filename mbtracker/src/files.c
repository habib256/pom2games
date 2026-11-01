/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* files.c — the .AYS files of the boot volume (the prefix sysboot set):
 * the catalog (dev/lib/prodos dir.c, mbt.h's dir_list), whole-file load /
 * save (dev/lib/prodos file.s). MLI buffers in $1000-$1FFF (pages crt0
 * leaves free in the system bitmap); the song is read into song_buf with
 * prodos_load_free (its pages are marked used). The caller stops the
 * music first (the Disk II driver masks interrupts ~1 s). Overlay OVL2 with
 * fileui.c and dir.c (the Makefile: its initialised parameter blocks come
 * back with it). */
#include <string.h>
#include "prodos.h"
#include "mbt.h"

#pragma code-name (push, "OVL2")
#pragma rodata-name (push, "OVL2")
#pragma data-name (push, "OVL2")

char cur_file[16];

#pragma bss-name (push, "IOBUF")
unsigned char file_iobuf[1024];
#pragma bss-name (pop)
#pragma bss-name (push, "LOWBSS")
static unsigned char path[66];
#pragma bss-name (pop)

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
