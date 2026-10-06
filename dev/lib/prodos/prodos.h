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
/* Claim auxiliary video memory; locate the ProDOS RAM-disk driver.
 * The caller owns aux RAM. No file-preservation check is performed. */
void prodos_video_claim(void);
/* Rebuild the RAM disk emptied by video after video use. 0 = failure. */
unsigned char prodos_video_release(void);
#endif
