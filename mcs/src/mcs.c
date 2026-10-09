/* Original Music Construction Set-inspired editor, GPL-3.0. */
#include <string.h>
#include "hgr.h"
#include "song.h"
#include "pitches.h"

extern void audio_block(void);
extern void audio_reset(void);
extern unsigned audio_inc[2];
/* Exported for emulator verification. */
unsigned char cursor, voice, selected[2], dirty, playing, ready;
static unsigned char page;
static const unsigned char scale[14] = {
    0,2,4,5,7,9,11,12,14,16,17,19,21,23
};
static const char *message;

static unsigned char base(unsigned char v) { return v ? 36 : 60; }

static unsigned char valid(const Song *s)
{
    unsigned char i, v, p, d;
    if (memcmp(s->magic, "P2MC", 4) || s->version != 1 || s->reserved ||
        s->tempo < 40 || s->tempo > 240 || !s->length || s->length > STEPS)
        return 0;
    for (i = 0; i < STEPS; ++i) {
        d = s->duration[i];
        if (d != 1 && d != 2 && d != 4 && d != 8) return 0;
        for (v = 0; v < 2; ++v) {
            p = s->pitch[v][i];
            if (p && (p < base(v) || p > base(v)+23)) return 0;
        }
    }
    return 1;
}

static void blank(void)
{
    memset(SONG, 0, SONG_BYTES);
    memcpy(SONG->magic, "P2MC", 4);
    SONG->version = 1;
    SONG->tempo = 120;
    SONG->length = 16;
    memset(SONG->duration, 2, STEPS);
    cursor = voice = 0;
    selected[0] = 60;
    selected[1] = 48;
    dirty = 1;
}

static void disk(unsigned char save)
{
    if (save && a2_disk_protected()) {
        message = "DISQUETTE PROTEGEE";
        return;
    }
    /* The distributed disk always contains SONG, so BLOAD need not create it. */
    if (save) {
        a2_dos_cmd("BSAVE SONG,A$1000,L$00C8");
        dirty = 0;
        message = "SAUVEGARDE OK";
    } else {
        memset((void *)0x1100, 0, SONG_BYTES);
        a2_dos_cmd("BLOAD SONG,A$1100");
        if (!valid((const Song *)0x1100)) {
            message = "FORMAT SONG INVALIDE";
            return;
        }
        memcpy(SONG, (const void *)0x1100, SONG_BYTES);
        dirty = 0;
        cursor = 0;
        message = "PARTITION CHARGEE";
    }
}

static unsigned xslot(unsigned char n) { return 28u + (n & 15u)*15u; }

/* Use the lower natural for accidentals; render a # beside the note. */
static unsigned char degree(unsigned char v, unsigned char p)
{
    unsigned char n = 0;
    p -= base(v);
    while (n < 13 && scale[n+1] <= p) ++n;
    return n;
}

static unsigned char ypitch(unsigned char v, unsigned char p)
{
    return (v ? 140 : 74) - degree(v,p)*3;
}

static void note(unsigned char v, unsigned char slot, unsigned char p)
{
    unsigned x = xslot(slot);
    unsigned char y, ledger, bottom = v ? 128 : 68;
    if (!p) {
        hgr_puts8(x-2, bottom-15, "-");
        return;
    }
    y = ypitch(v,p);
    for (ledger = bottom+6; ledger <= y; ledger += 6)
        hgr_hline(x-4, x+5, ledger);
    if (y < bottom-24) hgr_hline(x-4, x+5, bottom-30);
    if (y < bottom-30) hgr_hline(x-4, x+5, bottom-36);
    hgr_fill_pixrect(x-2, y-1, 5, 3);
    if (SONG->duration[slot] == 8)
        hgr_clear_pixrect(x-1, y, 3, 1);
    else {
        hgr_vline(x+2, y-14, y);
        if (SONG->duration[slot] == 1) hgr_line(x+2, y-14, x+5, y-10);
        if (SONG->duration[slot] == 4) hgr_clear_pixrect(x-1, y, 3, 1);
    }
    if (p != base(v)+scale[degree(v,p)]) hgr_puts8(x-11, y-4, "#");
}

static void pitchlabel(unsigned x, unsigned char y, unsigned char p)
{
    static const char *names[12] = {
        "C ","C#","D ","D#","E ","F ","F#","G ","G#","A ","A#","B "
    };
    hgr_puts8(x,y,names[p%12]);
    hgr_putu8(x+16,y,p/12-1);
}

static void draw(void)
{
    unsigned char v, i, n, bottom, y;
    unsigned x;
    page = cursor & 0xf0;
    hgr_clear(0);
    hgr_puts8(4,0,"MUSIC CONSTRUCTION / POM2");
    hgr_puts8(4,12,"PAS"); hgr_putu8(36,12,cursor+1);
    hgr_puts8(64,12,"FIN"); hgr_putu8(96,12,SONG->length);
    hgr_puts8(128,12,"BPM"); hgr_putu8(160,12,SONG->tempo);
    pitchlabel(208,12,selected[voice]);
    if (dirty) hgr_puts8(248,12,"*");
    for (v = 0; v < 2; ++v) {
        bottom = v ? 128 : 68;
        for (i = 0; i < 5; ++i) hgr_hline(16,270,bottom-i*6);
        hgr_puts8(0,bottom-18,v ? "B" : "T");
        for (i = 0; i < 16; ++i) {
            n = page+i;
            if (n < SONG->length) note(v,n,SONG->pitch[v][n]);
            x = xslot(n);
            if (!(i&3)) hgr_vline(x-8,bottom-24,bottom);
        }
    }
    for (i = 0; i < 16; ++i) {
        n = page+i;
        if (n < SONG->length) hgr_putu8(xslot(n)-3,144,SONG->duration[n]);
    }
    x = xslot(cursor);
    y = ypitch(voice,selected[voice]);
    /* Box marks the insertion pitch, underlining the selected time slot. */
    hgr_hline(x-4,x+5,y-3); hgr_hline(x-4,x+5,y+3);
    hgr_vline(x-4,y-3,y+3); hgr_vline(x+5,y-3,y+3);
    hgr_hline(x-4,x+5,155);
    hgr_puts8(0,162,message);
    hgr_puts8(0,174,"IJKM:BOUGE TAB:VOIX ENTREE:NOTE");
    hgr_puts8(0,184,"?:AIDE ESP:JOUE S:SAUVE L:CHARGE");
}

static void help(void)
{
    hgr_clear(0);
    hgr_puts8(8,8,"MCS / COMMANDES");
    hgr_puts8(8,28,"J/K : PAS PRECEDENT/SUIVANT");
    hgr_puts8(8,40,"I/M : MONTER/DESCENDRE LA NOTE");
    hgr_puts8(8,52,"FLECHES : MEMES COMMANDES");
    hgr_puts8(8,64,"TAB/V : PORTEE AIGUE OU BASSE");
    hgr_puts8(8,76,"ENTREE : POSER/REMPLACER NOTE");
    hgr_puts8(8,88,"R/X : SILENCE SUR CETTE VOIX");
    hgr_puts8(8,100,"D : DUREE 1/2/4/8 CROCHES");
    hgr_puts8(8,112,"+/- : NOTE PAR DEMI-TON");
    hgr_puts8(8,124,"[/] : TEMPO -/+ 5 BPM");
    hgr_puts8(8,136,"F : FIN AU PAS COURANT");
    hgr_puts8(8,148,"N : NOUVEAU  A : ECOUTER NOTE");
    hgr_puts8(8,160,"S/L : SAUVER/CHARGER SONG");
    hgr_puts8(8,172,"ESPACE : JOUER  ESC : QUITTER");
    apple2_getkey();
}

static unsigned char confirm(const char *text)
{
    unsigned char k;
    hgr_clear_pixrect(0,160,140,12);
    hgr_clear_pixrect(140,160,140,12);
    hgr_puts8(0,162,text);
    k = apple2_getkey();
    return k == 'O' || k == 'Y';
}

/* Blocks are ~17ms. The keyboard is checked between blocks, even in rests. */
static unsigned char sound(unsigned char p0, unsigned char p1, unsigned blocks)
{
    audio_inc[0] = p0 ? increments[p0-36] : 0;
    /* Avoid cancellation of two phase-identical unison square waves. */
    audio_inc[1] = p1 && p1 != p0 ? increments[p1-36] : 0;
    while (blocks--) {
        if (apple2_iskeypressed()) { apple2_getkey(); return 0; }
        audio_block();
    }
    return 1;
}

static void play(void)
{
    unsigned char n, old = cursor;
    unsigned blocks;
    playing = 1;
    message = "LECTURE / TOUCHE POUR ARRETER";
    cursor = 0;
    draw();
    audio_reset();
    for (n = 0; n < SONG->length; ++n) {
        if ((n & 0xf0) != page) { cursor = n; draw(); }
        hgr_hline(xslot(n)-4,xslot(n)+5,155);
        blocks = (1759u*SONG->duration[n]+SONG->tempo/2)/SONG->tempo;
        if (!sound(SONG->pitch[0][n],SONG->pitch[1][n],blocks)) break;
        hgr_clear_pixrect(xslot(n)-4,155,10,1);
    }
    cursor = old;
    playing = 0;
    message = "LECTURE TERMINEE";
}

static void move_pitch(unsigned char up)
{
    unsigned char d = degree(voice,selected[voice]);
    if (up) {
        if (d < 13) selected[voice] = base(voice)+scale[d+1];
    } else if (selected[voice] != base(voice)+scale[d])
        selected[voice] = base(voice)+scale[d];
    else if (d) selected[voice] = base(voice)+scale[d-1];
}

int main(void)
{
    unsigned char k;
    blank();
    disk(0);
    hgr_init();
    audio_reset();
    for (;;) {
        draw();
        ready = 1;
        k = apple2_getkey();
        ready = 0;
        message = "PRET";
        switch (k) {
        case 'J': case KC_LEFT: if (cursor) --cursor; break;
        case 'K': case KC_RIGHT: if (cursor < STEPS-1) ++cursor; break;
        case 'I': case KC_UP: move_pitch(1); break;
        case 'M': case KC_DOWN: move_pitch(0); break;
        case 9: case 'V': voice ^= 1; break;
        case '+': if (selected[voice] < base(voice)+23) ++selected[voice]; break;
        case '-': if (selected[voice] > base(voice)) --selected[voice]; break;
        case KC_RET:
            SONG->pitch[voice][cursor] = selected[voice]; dirty = 1;
            if (SONG->length <= cursor) SONG->length = cursor+1;
            break;
        case 'R': case 'X': SONG->pitch[voice][cursor] = 0; dirty = 1; break;
        case 'D':
            SONG->duration[cursor] <<= 1;
            if (SONG->duration[cursor] > 8) SONG->duration[cursor] = 1;
            dirty = 1; break;
        case '[':
            if (SONG->tempo > 40) {
                SONG->tempo = SONG->tempo < 45 ? 40 : SONG->tempo-5; dirty = 1;
            } break;
        case ']':
            if (SONG->tempo < 240) {
                SONG->tempo = SONG->tempo > 235 ? 240 : SONG->tempo+5; dirty = 1;
            } break;
        case 'F': SONG->length = cursor+1; dirty = 1; break;
        case 'N': if (!dirty || confirm("EFFACER ? O/N")) blank(); break;
        case 'L': if (!dirty || confirm("RECHARGER ? O/N")) disk(0); break;
        case 'S': disk(1); break;
        case ' ': play(); break;
        case 'A':
            audio_reset();
            sound(selected[voice],0,12);
            break;
        case '?': help(); break;
        case KC_ESC:
            if (!dirty || confirm("QUITTER SANS SAUVER ? O/N")) return 0;
            break;
        }
    }
}
