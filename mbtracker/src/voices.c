/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* voices.c — MB TRACKER's ^W: the song from 3 to 6 voices or back
 * (song.c's song_voices repacks the aux pattern store). Patterns, order,
 * instruments and texts kept; 3 -> 6 refused past 32 patterns; 6 -> 3
 * asks before voices 4-6 are dropped if they hold anything; the undo is
 * forgotten. Overlay OVL1 (src/mbt.cfg), with the instrument editor. */
#include <string.h>
#include "mbt.h"
#include "ui.h"

#pragma code-name (push, "OVL1")
#pragma rodata-name (push, "OVL1")

extern unsigned char u_kind, sel_on, cur_v;

void voices(void)
{
    unsigned char n;
    stop();
    pat_flush();
    if (s_voices == 3 && s_npat > 32) {
        strcpy(msg, "6 VOICES: 32 PATTERNS AT MOST, THIS SONG HAS ");
        n = strlen(msg);
        dec2(msg + n, s_npat);
        msg[n + 2] = 0;
        rd |= RD_MSG;
        return;
    }
    if (s_voices == 6 && song_hi_used() && !ask("VOICES 4-6 ARE NOT EMPTY: DROP THEM? (Y/N)"))
        return;
    song_voices();
    snd_mute &= 7;
    if (slot)
        snd_mute_set(snd_mute);
    u_kind = sel_on = 0;
    if (cur_v >= s_voices)
        cur_v = s_voices - 1;
    touched();
    layout();
    full();
    say(s_voices == 6 ? "NOW 6 VOICES (4-6 EMPTY: THE SECOND CHIP); UNDO CLEARED"
                      : "NOW 3 VOICES (4-6 DROPPED); UNDO CLEARED");
}
