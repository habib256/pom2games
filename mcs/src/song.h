/* GPL-3.0; see LICENSE at repository root. Byte-only disk format, no padding. */
#ifndef SONG_H
#define SONG_H
#define STEPS 64
#define SONG_BYTES 200
typedef struct {
    unsigned char magic[4];
    unsigned char version, tempo, length, reserved;
    unsigned char pitch[2][STEPS]; /* MIDI; zero = rest */
    unsigned char duration[STEPS]; /* eighth-note units: 1,2,4,8 */
} Song;
#define SONG ((Song *)0x1000)
#endif
