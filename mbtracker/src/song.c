/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* song.c — the song being edited and its AYS v1 encoding
 * (dev/lib/apple2/AYSONG_FORMAT.md). The encoder lays the bytes out as
 * dev/tools/audio/aysong.py's encode() does, byte for byte (tests/test_mbt.py
 * compares them): header, order list, tracks (identical ones shared, in
 * pattern then voice order), pattern blocks, pattern table, instruments,
 * instrument table, texts.
 *
 * Patterns live unpacked in aux memory from $0800 (3 bytes a cell, a voice
 * = 64 rows = 192 bytes, a pattern = voices x 192: 64 patterns of 3 voices
 * or 32 of 6 up to $97FF); the one being edited is `grid` in main RAM.
 * The decoder is in the overlay OVL2 (src/mbt.cfg). */
#include <string.h>
#include "mbt.h"

unsigned char s_voices, s_rows, s_speed, s_rate, s_nord, s_loop, s_nins, s_npat;
unsigned char s_order[256];
Instrument s_ins[MAXINS];
char s_name[32], s_author[32];
unsigned char cur_pat, grid_dirty;
unsigned song_len;

#pragma bss-name (push, "LOWBSS")
unsigned char grid[2 * MAXVOICES * TRACK];
#pragma bss-name (pop)
#pragma bss-name (push, "SONGBUF")
unsigned char song_buf[SONGBUF_SIZE];
#pragma bss-name (pop)

/* encoder state (its tables below $1000, after crt0's zero-page save) */
static unsigned pos;
static unsigned char *out;
static unsigned char overflow;
#pragma bss-name (push, "LOW8BSS")
static unsigned toff[64 * 3];      /* unique tracks: offset, length */
static unsigned tlen[64 * 3];
static unsigned trk[64 * 3];       /* each pattern's voices: their track */
static unsigned blk[64];
#pragma bss-name (pop)
static unsigned char ntr;

unsigned char max_patterns(void)
{
    return s_voices == 3 ? 64 : 32;
}

static unsigned pat_addr(unsigned char p)
{
    return AUX_PATTERNS + p * (unsigned)(s_voices * TRACK);
}

static void empty(unsigned char *b)
{
    unsigned i;
    for (i = 0; i < MAXVOICES * TRACK; i += CELL) {
        b[i] = NOTE_EMPTY;
        b[i + 1] = 0;
        b[i + 2] = 0;
    }
}

static void aux_xfer(unsigned char *m, unsigned char p, unsigned char put)
{
    ax_main = m;
    ax_aux = pat_addr(p);
    ax_len = s_voices * TRACK;
    if (put)
        aux_put();
    else
        aux_get();
}

void pat_flush(void)
{
    if (grid_dirty) {
        aux_xfer(grid, cur_pat, 1);
        grid_dirty = 0;
    }
}

void pat_select(unsigned char p)
{
    pat_flush();
    cur_pat = p;
    aux_xfer(grid, p, 0);
}

unsigned char pat_new(unsigned char copy)
{
    unsigned char p = s_npat;
    if (p >= max_patterns())
        return 0xFF;
    if (copy) {
        pat_flush();
        aux_xfer(grid, p, 1);
    } else {
        empty(scratch);
        aux_xfer(scratch, p, 1);
    }
    ++s_npat;
    song_len = 0;
    return p;
}

/* Pattern p out of the song: the next ones one down (their aux copies),
 * the order list renumbered by the caller. */
void __fastcall__ pat_delete(unsigned char p)
{
    pat_flush();
    for (--s_npat; p < s_npat; ++p) {
        aux_xfer(scratch, p + 1, 0);
        aux_xfer(scratch, p, 1);
    }
    song_len = 0;
}

void ins_default(unsigned char i)
{
    Instrument *n = &s_ins[i];
    unsigned char k;
    memset(n, 0, sizeof *n);
    n->n = 8;
    n->loop = 7;
    n->shape = 0xFF;
    for (k = 0; k < 8; ++k) {
        n->t[k] = 0x10 | (15 - k);      /* tone, 15 down to 8 */
        n->np[k] = NP_NONE;
    }
}

void __fastcall__ song_new(unsigned char voices)
{
    s_voices = voices;
    s_rows = 64;
    s_speed = 6;
    s_rate = 50;
    s_nord = 1;
    s_order[0] = 0;
    s_loop = 0;
    s_nins = 1;
    ins_default(0);
    s_name[0] = s_author[0] = 0;
    s_npat = 0;
    empty(grid);
    cur_pat = 0;
    grid_dirty = 0;
    pat_new(0);
    song_len = 0;
}

/* ---------------------------------------------------------------- encoder */
static void put(unsigned char b)
{
    if (pos >= SONGBUF_SIZE) {
        overflow = 1;
        return;
    }
    out[pos++] = b;
}

static void putw(unsigned w)
{
    put((unsigned char)w);
    put(w >> 8);
}

static unsigned char run;

static void flush_run(void)
{
    unsigned char k;
    while (run) {
        k = run > 64 ? 64 : run;
        put(0x7F + k);
        run -= k;
    }
}

static void encode_track(const unsigned char *c)
{
    unsigned char r, note, ins, fxc;
    run = 0;
    for (r = 0; r < s_rows; ++r, c += CELL) {
        note = c[0];
        ins = c[1] & 15;
        fxc = c[1] >> 4;
        if (note == NOTE_EMPTY && !ins && !fxc) {
            ++run;
            continue;
        }
        flush_run();
        if (ins)
            put(0x60 + ins);
        if (fxc) {
            put(0x6F + fxc);            /* $70 + effect */
            if (fxc > 1)
                put(c[2]);
        }
        if (note == NOTE_EMPTY)
            run = 1;
        else
            put(note == NOTE_OFF ? 0x60 : note);
    }
    flush_run();
}

static void encode_ins(const Instrument *n)
{
    unsigned at = pos, loopat = 0;
    unsigned char k;
    pos += 4;
    for (k = 0; k < n->n; ++k) {
        if (k == n->loop)
            loopat = pos - at;
        if (n->np[k] != NP_NONE) {
            put(n->t[k] | 0x80);
            put(n->np[k] & 31);
        } else
            put(n->t[k]);
    }
    if (overflow)
        return;
    out[at] = pos - at;
    out[at + 1] = loopat;
    out[at + 2] = n->shape == 0xFF ? 0xFF : n->shape & 15;
    out[at + 3] = n->eper;
}

static void put_str(const char *s)
{
    while (*s)
        put(*s++);
    put(0);
}

/* The song in buf (song_buf, or another buffer for an audition). */
static unsigned encode_to(unsigned char *buf, unsigned char cur_in_grid)
{
    unsigned char p, v, k, nv = s_voices;
    unsigned start, len, i;
    unsigned order_at, pat_at, ins_at, text_at;
    const unsigned char *src;

    out = buf;
    overflow = 0;
    pos = 20;
    order_at = pos;
    for (k = 0; k < s_nord; ++k)
        put(s_order[k]);
    ntr = 0;
    i = 0;
    for (p = 0; p < s_npat; ++p) {
        if (p == cur_pat && cur_in_grid)
            src = grid;
        else {
            aux_xfer(scratch, p, 0);
            src = scratch;
        }
        for (v = 0; v < nv; ++v, ++i) {
            start = pos;
            encode_track(src + v * TRACK);
            if (overflow)
                return 0;
            len = pos - start;
            for (k = 0; k < ntr; ++k)
                if (tlen[k] == len && !memcmp(out + toff[k], out + start, len))
                    break;
            if (k < ntr) {
                pos = start;
                trk[i] = toff[k];
            } else {
                toff[ntr] = start;
                tlen[ntr++] = len;
                trk[i] = start;
            }
        }
    }
    i = 0;
    for (p = 0; p < s_npat; ++p) {
        blk[p] = pos;
        for (v = 0; v < nv; ++v)
            putw(trk[i++]);
    }
    pat_at = pos;
    for (p = 0; p < s_npat; ++p)
        putw(blk[p]);
    for (k = 0; k < s_nins; ++k) {
        trk[k] = pos;                    /* (reused: the instruments' offsets) */
        encode_ins(&s_ins[k]);
    }
    ins_at = pos;
    for (k = 0; k < s_nins; ++k)
        putw(trk[k]);
    text_at = 0;
    v = s_name[0] | s_author[0];
    for (k = 0; k < s_nins; ++k)
        v |= s_ins[k].name[0];
    if (v) {
        text_at = pos;
        put_str(s_name);
        put_str(s_author);
        for (k = 0; k < s_nins; ++k)
            put_str(s_ins[k].name);
    }
    if (overflow)
        return 0;
    len = pos;
    out[0] = 'A';
    out[1] = 'Y';
    out[2] = 'S';
    out[3] = 1;
    out[4] = nv;
    out[5] = s_rows;
    out[6] = s_speed;
    out[7] = s_rate;
    out[8] = s_nord;
    out[9] = s_loop;
    out[10] = s_nins;
    out[11] = s_npat;
    pos = 12;
    putw(order_at);
    putw(pat_at);
    putw(ins_at);
    putw(text_at);
    return len;
}

unsigned song_encode(void)
{
    song_len = encode_to(song_buf, 1);
    return song_len;
}

/* A one-row song: `note` on voice 1 with instrument `ins` (index), for
 * ~1 s, then the end (silence). */
unsigned audition_encode(unsigned char *b, unsigned char ins, unsigned char note)
{
    const Instrument *n = &s_ins[ins];
    unsigned char k;
    out = b;
    overflow = 0;
    memcpy(b, "AYS\1\3\1\62\62\1\377\1\1", 12);
    pos = 12;
    putw(20);           /* order list */
    putw(29);           /* pattern table */
    putw(0);            /* instrument table (below) */
    putw(0);            /* no texts */
    put(0);             /* 20: order: pattern 0 */
    put(note);          /* 21: voice 1's track: the note */
    put(0x60);          /* 22: the other voices': note off */
    putw(21);           /* 23: the pattern's block */
    putw(22);
    putw(22);
    putw(23);           /* 29: the pattern table */
    k = pos;            /* 31: the instrument */
    encode_ins(n);
    b[16] = pos;
    b[17] = 0;
    putw(k);
    return pos;
}

/* ---------------------------------------------------------------- decoder */
/* (in the overlay OVL2 with the file screens: only file_load calls it) */
#pragma code-name (push, "OVL2")
#pragma rodata-name (push, "OVL2")
static const unsigned char *in;
static unsigned in_len;
static unsigned char bad;

static unsigned rw(unsigned at)
{
    if (at + 1 >= in_len) {
        bad = 1;
        return 0;
    }
    return in[at] | in[at + 1] << 8;
}

static unsigned char rb(unsigned at)
{
    if (at >= in_len) {
        bad = 1;
        return 0;
    }
    return in[at];
}

static void decode_track(unsigned at, unsigned char *c, unsigned char rows)
{
    unsigned char r = 0, b, k;
    while (r < rows && !bad) {
        c[0] = NOTE_EMPTY;
        c[1] = c[2] = 0;
        for (;;) {
            b = rb(at++);
            if (bad)
                return;
            if (b < 0x60) {
                c[0] = b;
                break;
            }
            if (b == 0x60) {
                c[0] = NOTE_OFF;
                break;
            }
            if (b < 0x70) {
                c[1] = (c[1] & 0xF0) | (b - 0x60);
                continue;
            }
            if (b < 0x78) {
                k = b - 0x70;
                c[1] = (c[1] & 15) | (k + 1) << 4;
                c[2] = k ? rb(at++) : 0;
                continue;
            }
            if (b >= 0x80 && b < 0xC0) {
                k = b - 0x80;          /* this row then k more empty ones */
                if (r + k >= rows) {
                    bad = 1;
                    return;
                }
                while (k--) {
                    c += CELL;
                    ++r;
                    c[0] = NOTE_EMPTY;
                    c[1] = c[2] = 0;
                }
                break;
            }
            bad = 1;
            return;
        }
        c += CELL;
        ++r;
    }
}

static unsigned char decode_ins(unsigned at, Instrument *n, unsigned char commit)
{
    unsigned char end = rb(at), lp = rb(at + 1), k = 0, o = 4, b, li = 0xFF;
    Instrument t;
    if (end < 5 || lp < 4 || lp >= end)
        return 1;
    t.shape = rb(at + 2);
    if (t.shape != 0xFF)
        t.shape &= 15;
    t.eper = rb(at + 3);
    while (o < end) {
        if (k == MAXTICKS)
            return 1;
        if (o == lp)
            li = k;
        b = rb(at + o++);
        t.t[k] = b & 0x7F;
        t.np[k] = NP_NONE;
        if (b & 0x80)
            t.np[k] = rb(at + o++) & 31;
        ++k;
    }
    if (li == 0xFF || bad)
        return 1;
    t.n = k;
    t.loop = li;
    if (commit) {
        memcpy(n, &t, sizeof t - sizeof t.name);
        n->name[0] = 0;
    }
    return 0;
}

static unsigned text_at;

static void read_str(char *d, unsigned char max)
{
    unsigned char k = 0, c;
    if (!text_at) {
        *d = 0;
        return;
    }
    while (text_at < in_len && (c = in[text_at++]) != 0)
        if (k < max - 1)
            d[k++] = c;
    d[k] = 0;
    if (text_at >= in_len)
        text_at = 0;
}

/* Two passes: check, then commit (the song is kept on a bad file). */
unsigned char song_decode(unsigned len)
{
    unsigned char pass, p, v, nv, rows, npat, nins, nord;
    unsigned order_at, pat_at, ins_at, b;
    in = song_buf;
    in_len = len;
    if (len < 20 || memcmp(in, "AYS\1", 4))
        return 1;
    nv = in[4];
    rows = in[5];
    nord = in[8];
    nins = in[10];
    npat = in[11];
    if ((nv != 3 && nv != 6) || !rows || rows > 64 || !in[6] || !nord || !nins || nins > 15 || !npat
        || npat > (nv == 3 ? 64 : 32) || (in[9] != 0xFF && in[9] >= nord))
        return 1;
    order_at = in[12] | in[13] << 8;
    pat_at = in[14] | in[15] << 8;
    ins_at = in[16] | in[17] << 8;
    if (order_at + nord > len)
        return 1;
    for (p = 0; p < nord; ++p)
        if (in[order_at + p] >= npat)
            return 1;
    for (pass = 0; pass < 2; ++pass) {
        bad = 0;
        if (pass) {
            s_voices = nv;
            s_rows = rows;
            s_speed = in[6];
            s_rate = in[7];
            s_nord = nord;
            s_loop = in[9];
            s_nins = nins;
            s_npat = npat;
            memcpy(s_order, in + order_at, nord);
        }
        for (p = 0; p < npat; ++p) {
            b = rw(pat_at + 2 * p);
            empty(scratch);
            for (v = 0; v < nv; ++v)
                decode_track(rw(b + 2 * v), scratch + v * TRACK, rows);
            if (bad)
                return 1;
            if (pass)
                aux_xfer(scratch, p, 1);
        }
        for (p = 0; p < nins; ++p)
            if (decode_ins(rw(ins_at + 2 * p), &s_ins[p], pass) || bad)
                return 1;
    }
    text_at = in[18] | in[19] << 8;
    if (text_at >= len)
        text_at = 0;
    read_str(s_name, sizeof s_name);
    read_str(s_author, sizeof s_author);
    for (p = 0; p < nins; ++p)
        read_str(s_ins[p].name, sizeof s_ins[p].name);
    grid_dirty = 0;
    cur_pat = s_order[0];
    aux_xfer(grid, cur_pat, 0);
    return 0;
}
#pragma rodata-name (pop)
#pragma code-name (pop)
