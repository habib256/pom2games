#ifndef BREAKOUT_SOUND_H
#define BREAKOUT_SOUND_H
/* Higher priorities interrupt quieter impacts; tones are spread across frames. */
#define SND_WALL 1
#define SND_PAD 2
#define SND_STEEL 3
#define SND_HIT 4
#define SND_BREAK 5
#define SND_LAUNCH 6
#define SND_START 7
#define SND_BONUS 8
#define SND_LEVEL 9
#define SND_LOST 10
#define SND_WIN 11
void __fastcall__ sound_event(unsigned char event);
void sound_tick(void);
void sound_stop(void);
#endif
