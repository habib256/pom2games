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
#endif
