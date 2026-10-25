/* VERHILLE Arnaud — GPL-3.0. ProDOS 8, main RAM/ZP, cc65. */
#ifndef PRODOS_H
#define PRODOS_H
#define PD_READ_BLOCK 0x80u
#define PD_WRITE_BLOCK 0x81u
#define PD_GET_TIME 0x82u
#define PD_CREATE 0xC0u
#define PD_DESTROY 0xC1u
#define PD_RENAME 0xC2u
#define PD_SET_FILE_INFO 0xC3u
#define PD_GET_FILE_INFO 0xC4u
#define PD_ONLINE 0xC5u
#define PD_SET_PREFIX 0xC6u
#define PD_GET_PREFIX 0xC7u
#define PD_OPEN 0xC8u
#define PD_READ 0xCAu
#define PD_WRITE 0xCBu
#define PD_CLOSE 0xCCu
#define PD_FLUSH 0xCDu
#define PD_SET_EOF 0xD0u
#define PD_QUIT 0x65u
/* Parameter lists start with a count byte; pointers/words are little endian.
 * Non-reentrant. Returns zero on success, otherwise the MLI error code. */
extern unsigned char prodos_command;
extern void *prodos_params;
unsigned char prodos_call(void);
#define PD_VIDEO_PRESERVE_RAM 0u
#define PD_VIDEO_DISCARD_RAM  1u
#define PD_VIDEO_OK          0u
#define PD_VIDEO_RAM_BUSY    1u
#define PD_VIDEO_BAD_POLICY  2u
#define PD_VIDEO_BAD_DEVLIST 3u
/* Claim auxiliary video memory BEFORE drawing. Returns PD_VIDEO_*.
 * PRESERVE refuses any installed /RAM (even empty); DISCARD explicitly
 * permits destroying its files and rebuilding an empty disk at release.
 * Failure leaves the current claim intact. Repeated claims are idempotent.
 * Main RAM/ZP and ROM visible; not reentrant or callable from IRQ. */
unsigned char __fastcall__ prodos_video_claim(unsigned char policy);
/* Rebuild the RAM disk emptied by video after video use. 0 = failure. */
unsigned char prodos_video_release(void);

/* Whole files (file.s, PRODOS_FILE_SRCS; file.asm in assembly). Set the
 * fields, then call; the result is zero or the MLI error code.
 * name: Pascal string (relative to the prefix, or a full path); iobuf: 1 KB
 * OPEN buffer, page aligned, free in the system bitmap; actual: bytes moved,
 * reset before OPEN and each transfer (zero if OPEN or range validation fails).
 * load: OPEN, READ length bytes at buffer, CLOSE (READ error, else CLOSE).
 * load_free: the same, the destination pages freed in the system bitmap
 * during the READ (pages a crt0 claimed, video pages). A nonempty range must
 * fit below $C000 without 16-bit wrap, else $56 with no READ or bitmap change.
 * Zero length uses ordinary READ without changing the bitmap.
 * save: OPEN, or CREATE a BIN file (access $C3) then OPEN; WRITE; SET_EOF to
 * bytes written; CLOSE. Replaces the whole file, even with length zero.
 * First error wins; CLOSE is always attempted after successful OPEN.
 * Saves are not atomic: failure can leave partial data. */
extern void *prodos_file_name, *prodos_file_iobuf, *prodos_file_buffer;
extern unsigned prodos_file_length, prodos_file_actual;
unsigned char prodos_load(void);
unsigned char prodos_load_free(void);
unsigned char prodos_save(void);
#endif
