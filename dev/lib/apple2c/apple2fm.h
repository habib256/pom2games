/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* apple2fm.h — DOS 3.3 files by name from Apple II C programs (cc65),
 * through the file manager, with error codes (../apple2/fm.asm).
 *
 * Link apple2fm.s (APPLE2C_FM_SRCS, assembled with $(APPLE2C_AFLAGS)).
 * Unlike a2_dos_cmd() (apple2dos.h), a failure never stops the program
 * at the BASIC prompt: every call returns a code.
 *
 *     static const unsigned char hdr[4] = {0x00, 0x10, 16, 0};
 *     if (a2_fm_open("HISCORE", A2_FM_BINARY) <= A2_FM_CREATED) {
 *         a2_fm_write(hdr, 4);                // BLOAD header: A$1000, L16
 *         rc = a2_fm_write(scores, 16);       // A2_FM_ERR_FULL...
 *         a2_fm_close();
 *     }
 *
 *     if (a2_fm_open("HISCORE", A2_FM_MUST_EXIST) == A2_FM_OK) {
 *         a2_fm_seek(4);                      // skip the header
 *         a2_fm_read(scores, 16);
 *         a2_fm_close();
 *     }
 *
 * Return codes: A2_FM_OK (0); a2_fm_open: A2_FM_CREATED (1) when it made
 * the file (empty); else an error, always greater than A2_FM_CREATED.
 * The file manager writes zero page $26-$49 only (Monitor scratch: the
 * text window and cursor stay), none of the cc65 runtime's ($50-$FF).
 *
 * One DOS buffer (of MAXFILES, 3 by default) per open file; a2_fm_file is
 * the open file's handle: save it after a2_fm_open and put it back before
 * the read / write / seek / close of that file to keep several open.
 * Close every file before the program goes back to DOS. A DOS binary
 * file starts with a 4-byte header (load address, length) that BLOAD
 * reads: write it, or seek past it. The file manager keeps no length (a
 * file is whole sectors; the last one's tail reads as zeros).
 *
 * Drive: a2_fm_slot / a2_fm_drive, 0 = DOS's last access (the program's
 * disk); set both to name another (slot 1-7, drive 1-2). Interrupts: a
 * program that enables them assembles apple2fm.s with -D FM_SEI=1.
 * 560 bytes of code, 27 of variables (dev/tests/test_fm_c.py). */
#ifndef APPLE2FM_H
#define APPLE2FM_H

#define A2_FM_TEXT          0x00   /* file types (catalog letters T I A B) */
#define A2_FM_INTEGER       0x01
#define A2_FM_APPLESOFT     0x02
#define A2_FM_BINARY        0x04
#define A2_FM_MUST_EXIST    0x80   /* a2_fm_open: never create */
#define A2_FM_LOCKED        0x80   /* in a2_fm_type after a2_fm_open */

#define A2_FM_OK            0
#define A2_FM_CREATED       1      /* a2_fm_open made a new, empty file */
#define A2_FM_ERR_PROTECTED 4
#define A2_FM_ERR_END       5      /* read past the file's last sector */
#define A2_FM_ERR_NOT_FOUND 6
#define A2_FM_ERR_VOLUME    7
#define A2_FM_ERR_IO        8
#define A2_FM_ERR_FULL      9      /* the file keeps what fitted */
#define A2_FM_ERR_LOCKED    10     /* delete or write of a locked file */
#define A2_FM_ERR_NO_BUFFER 12     /* all MAXFILES DOS buffers in use */

/* name: ASCII, ends with 0 or ',' (30 characters at most).
 * type: the type to create a missing file with, or A2_FM_MUST_EXIST. */
unsigned char __fastcall__ a2_fm_open(const char *name, unsigned char type);
unsigned char __fastcall__ a2_fm_read(void *buf, unsigned len);
unsigned char __fastcall__ a2_fm_write(const void *buf, unsigned len);
unsigned char __fastcall__ a2_fm_seek(unsigned pos);  /* byte position */
unsigned char a2_fm_close(void);          /* frees the buffer, even on error */
unsigned char __fastcall__ a2_fm_delete(const char *name);
unsigned char __fastcall__ a2_fm_lock(const char *name);
unsigned char __fastcall__ a2_fm_unlock(const char *name);
unsigned char __fastcall__ a2_fm_verify(const char *name);

/* apple2fmfile.s (APPLE2C_FM_FILE_SRCS, on its own: no need for apple2fm.s):
 * whole binary files, the error-returning BLOAD / BSAVE. 0 or an error code.
 * a2_fm_save writes the 4-byte header (buf, len) then len bytes, creating
 * the file if missing; a2_fm_load reads the first len data bytes into buf
 * (the header is skipped); the file must exist (A2_FM_ERR_NOT_FOUND). */
unsigned char __fastcall__ a2_fm_load(const char *name, void *buf, unsigned len);
unsigned char __fastcall__ a2_fm_save(const char *name, const void *buf, unsigned len);

extern unsigned a2_fm_file;               /* handle of the open file */
extern unsigned char a2_fm_type;          /* its type, A2_FM_LOCKED bit too */
extern unsigned char a2_fm_slot, a2_fm_drive;

#endif /* APPLE2FM_H */
