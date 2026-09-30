/* a2run -- scripted headless Apple II+ runs, portable C (Linux, macOS).
 *
 * The portable sibling of ../a2shot (which needs the arm64 POM2 core): same
 * ROMs, same script syntax, plus a few steps for tests. It boots a DOS 3.3
 * .dsk in slot 6 drive 1 under the Apple ][+ Autostart ROM, then walks the
 * script:
 *
 *   wait:N          run N video frames (17030 cycles each, ~1/60 s)
 *   key:TEXT        type TEXT (\r RETURN, \e ESC, \< \> left/right, \^ \v up/down)
 *   shot:FILE.png   render the screen (HGR in colour, 560x384; TEXT/GR as text)
 *   text            print the 40x24 text page
 *   peek:ADDR[:LEN] hex-dump memory (RAM only, no I/O side effects)
 *   poke:ADDR:VAL   write one RAM byte
 *   joy:X,Y         joystick axes in [-1,1]      btn:N,0|1  game-port button
 *   reset           press RESET
 *   pc              print the program counter
 *   spk             print the speaker toggles since the last spk
 *   dsk:FILE.dsk    write the disk as it is now (DOS order), to check saves
 *
 *   a2run --disk GAME.dsk wait:900 key:" " wait:60 shot:title.png
 *
 * The disk image given with --disk is never modified: writes by the guest
 * stay in memory until a dsk: step. ROMs: ../a2shot/roms next to this binary
 * (apple2p.rom, disk2.rom) or --roms DIR.
 *
 * Emulated: 6502 (NMOS), 48 KB RAM, keyboard latch, speaker, video soft
 * switches, game port (2 paddles by cycle count, 3 buttons), Disk II in slot
 * 6 at nibble level (reads and writes; 6-and-2, DOS 3.3 sector order). Not
 * emulated: language card, cassette, other cards, precise disk timing (a
 * nibble is ready on every read).
 */
#include "cpu6502.h"

#include <zlib.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CYCLES_PER_FRAME 17030
#define TRACKS 35
#define TRACK_LEN 6392          /* nibbles per track: a full 16-sector layout */

static uint8_t ram[0xC000];
static uint8_t rom[0x3000];     /* $D000-$FFFF */
static uint8_t slot6[256];      /* $C600 boot PROM */
static Cpu cpu;

/* --- keyboard ------------------------------------------------------------- */
static uint8_t kbd_latch;
static char kbd_queue[65536];
static int kbd_head, kbd_tail;
static uint64_t kbd_last;

/* --- video / sound / game port -------------------------------------------- */
static int v_text = 1, v_mixed, v_page2, v_hires;
static unsigned long spk_count;
static uint8_t paddle[2] = { 128, 128 };
static uint8_t button[3];
static uint64_t ptrig_at;

/* --- Disk II ---------------------------------------------------------------- */
static uint8_t track_nib[TRACKS][TRACK_LEN];
static int halftrack, head_pos, motor, q6, q7, phases;
static uint64_t motor_off_at;
static int latch_phase;   /* the controller keeps the motor on ~1 s after $C088 */

static int spinning(void) { return motor || cpu.cycles < motor_off_at; }

/* ============================================================================ */
/* 6-and-2 GCR                                                                  */
/* ============================================================================ */
static const uint8_t enc62[64] = {
    0x96, 0x97, 0x9A, 0x9B, 0x9D, 0x9E, 0x9F, 0xA6, 0xA7, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF, 0xB2, 0xB3,
    0xB4, 0xB5, 0xB6, 0xB7, 0xB9, 0xBA, 0xBB, 0xBC, 0xBD, 0xBE, 0xBF, 0xCB, 0xCD, 0xCE, 0xCF, 0xD3,
    0xD6, 0xD7, 0xD9, 0xDA, 0xDB, 0xDC, 0xDD, 0xDE, 0xDF, 0xE5, 0xE6, 0xE7, 0xE9, 0xEA, 0xEB, 0xEC,
    0xED, 0xEE, 0xEF, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF,
};
static int dec62[256];

/* physical sector -> DOS 3.3 logical sector (.dsk file order) */
static const int phys2log[16] = { 0, 7, 14, 6, 13, 5, 12, 4, 11, 3, 10, 2, 9, 1, 8, 15 };

static int rev2(int v) { return ((v & 1) << 1) | ((v >> 1) & 1); }

static void nibblize_track(int t, const uint8_t *dsk)
{
    uint8_t *p = track_nib[t];
    int n = 0;
    memset(p, 0xFF, TRACK_LEN);
    n += 48;                                            /* gap 1 */
    for (int ps = 0; ps < 16; ps++) {
        const uint8_t *d = dsk + (t * 16 + phys2log[ps]) * 256;
        int vol = 254;
        p[n++] = 0xD5; p[n++] = 0xAA; p[n++] = 0x96;
        int f[4] = { vol, t, ps, vol ^ t ^ ps };
        for (int i = 0; i < 4; i++) {
            p[n++] = (uint8_t)((f[i] >> 1) | 0xAA);
            p[n++] = (uint8_t)(f[i] | 0xAA);
        }
        p[n++] = 0xDE; p[n++] = 0xAA; p[n++] = 0xEB;
        n += 6;                                         /* gap 2 */
        p[n++] = 0xD5; p[n++] = 0xAA; p[n++] = 0xAD;
        uint8_t v[342];
        for (int k = 0; k < 86; k++) {
            int a = rev2(d[k]) | (rev2(d[k + 86]) << 2);
            if (k + 172 < 256) a |= rev2(d[k + 172]) << 4;
            v[k] = (uint8_t)a;
        }
        for (int i = 0; i < 256; i++) v[86 + i] = d[i] >> 2;
        uint8_t prev = 0;
        for (int k = 0; k < 342; k++) { p[n++] = enc62[v[k] ^ prev]; prev = v[k]; }
        p[n++] = enc62[prev];
        p[n++] = 0xDE; p[n++] = 0xAA; p[n++] = 0xEB;
        n += 27;                                        /* gap 3 */
    }
    if (n > TRACK_LEN) { fprintf(stderr, "a2run: track layout overflow (%d)\n", n); exit(1); }
}

static uint8_t tn(int t, int i) { return track_nib[t][((i % TRACK_LEN) + TRACK_LEN) % TRACK_LEN]; }

/* Decode one track back into DOS order; returns sectors found. */
static int denibblize_track(int t, uint8_t *dsk)
{
    int found = 0;
    for (int i = 0; i < TRACK_LEN; i++) {
        if (tn(t, i) != 0xD5 || tn(t, i + 1) != 0xAA || tn(t, i + 2) != 0x96) continue;
        int f[4];
        for (int k = 0; k < 4; k++) {
            int a = tn(t, i + 3 + 2 * k), b = tn(t, i + 4 + 2 * k);
            f[k] = ((a << 1) | 1) & b;
        }
        if ((f[0] ^ f[1] ^ f[2]) != f[3] || f[1] != t || f[2] > 15) continue;
        int j = i + 11, lim = j + 64;
        while (j < lim && !(tn(t, j) == 0xD5 && tn(t, j + 1) == 0xAA && tn(t, j + 2) == 0xAD)) j++;
        if (j >= lim) continue;
        j += 3;
        uint8_t v[342], acc = 0;
        int bad = 0;
        for (int k = 0; k < 342; k++) {
            int dv = dec62[tn(t, j + k)];
            if (dv < 0) { bad = 1; break; }
            acc ^= (uint8_t)dv;
            v[k] = acc;
        }
        if (bad || dec62[tn(t, j + 342)] != acc) {
            fprintf(stderr, "a2run: bad data field T%d S%d\n", t, f[2]);
            continue;
        }
        uint8_t *d = dsk + (t * 16 + phys2log[f[2]]) * 256;
        for (int y = 0; y < 256; y++) {
            int k = y % 86, sh = (y / 86) * 2;
            d[y] = (uint8_t)((v[86 + y] << 2) | rev2((v[k] >> sh) & 3));
        }
        found++;
    }
    return found;
}

static int load_disk(const char *path)
{
    static uint8_t dsk[TRACKS * 16 * 256];
    FILE *f = fopen(path, "rb");
    if (!f || fread(dsk, 1, sizeof dsk, f) != sizeof dsk) {
        fprintf(stderr, "a2run: cannot read 140 KB image %s\n", path);
        return 0;
    }
    fclose(f);
    for (int t = 0; t < TRACKS; t++) nibblize_track(t, dsk);
    return 1;
}

static int save_disk(const char *path)
{
    static uint8_t dsk[TRACKS * 16 * 256];
    memset(dsk, 0, sizeof dsk);
    for (int t = 0; t < TRACKS; t++) {
        int n = denibblize_track(t, dsk);
        if (n != 16) fprintf(stderr, "a2run: track %d: %d sectors decoded\n", t, n);
    }
    FILE *f = fopen(path, "wb");
    if (!f || fwrite(dsk, 1, sizeof dsk, f) != sizeof dsk) return 0;
    return fclose(f) == 0;
}

static uint8_t disk_io(int reg, int write, uint8_t val)
{
    if (reg < 8) {
        int ph = reg >> 1;
        if (reg & 1) {
            phases |= 1 << ph;
            int delta = (ph - (halftrack & 3)) & 3;
            if (delta == 1) halftrack++;
            else if (delta == 3) halftrack--;
            if (halftrack < 0) halftrack = 0;
            if (halftrack > (TRACKS - 1) * 2) halftrack = (TRACKS - 1) * 2;
        } else {
            phases &= ~(1 << ph);
        }
        return 0;
    }
    switch (reg) {
    case 0x8: if (motor) motor_off_at = cpu.cycles + 1020000; motor = 0; break;
    case 0x9: motor = 1; break;
    case 0xA: case 0xB: break;                    /* drive select: drive 1 only */
    case 0xC: q6 = 0; break;
    case 0xD: q6 = 1; break;
    case 0xE: q7 = 0; break;
    case 0xF: q7 = 1; break;
    }
    int t = halftrack >> 1;
    if (write && q7 && (reg == 0xD || reg == 0xF)) {
        if (spinning()) {                          /* RWTS: STA Q6H / Q7H = one nibble */
            track_nib[t][head_pos] = val;
            head_pos = (head_pos + 1) % TRACK_LEN;
        }
        return 0;
    }
    if (reg == 0xC && !q7) {
        if (!spinning()) return 0;
        /* Every other read finds the latch still shifting (bit 7 clear), as
         * the hardware does between nibbles: RWTS's "is the disk spinning"
         * test compares two reads and must see them differ even in a run of
         * $FF sync bytes. Read loops (LDA Q6L / BPL) just poll once more. */
        if ((latch_phase ^= 1)) return 0x00;
        uint8_t v = track_nib[t][head_pos];
        head_pos = (head_pos + 1) % TRACK_LEN;
        return v;
    }
    if (reg == 0xD && !q7) return 0x00;            /* write-protect sense: not protected */
    return 0;
}

/* ============================================================================ */
/* bus                                                                          */
/* ============================================================================ */
static uint8_t io(uint16_t a, int write, uint8_t val)
{
    int lo = a & 0xFF;
    if (lo < 0x10) return kbd_latch;
    if (lo < 0x20) { kbd_latch &= 0x7F; return kbd_latch; }
    if (lo >= 0x30 && lo < 0x40) { spk_count++; return 0; }
    switch (lo) {
    case 0x50: v_text = 0; return 0;
    case 0x51: v_text = 1; return 0;
    case 0x52: v_mixed = 0; return 0;
    case 0x53: v_mixed = 1; return 0;
    case 0x54: v_page2 = 0; return 0;
    case 0x55: v_page2 = 1; return 0;
    case 0x56: v_hires = 0; return 0;
    case 0x57: v_hires = 1; return 0;
    case 0x61: case 0x62: case 0x63: return button[lo - 0x61] ? 0x80 : 0x00;
    case 0x64: case 0x65:
        return (cpu.cycles - ptrig_at) < (uint64_t)paddle[lo - 0x64] * 11 ? 0x80 : 0x00;
    case 0x66: case 0x67: return 0;
    }
    if (lo >= 0x70 && lo < 0x80) { ptrig_at = cpu.cycles; return 0; }
    if (lo >= 0xE0 && lo < 0xF0) return disk_io(lo & 0x0F, write, val);
    return 0;
}

static uint8_t bus_read(void *ctx, uint16_t a)
{
    (void)ctx;
    if (a < 0xC000) return ram[a];
    if (a >= 0xD000) return rom[a - 0xD000];
    if (a < 0xC100) return io(a, 0, 0);
    if (a >= 0xC600 && a < 0xC700) return slot6[a & 0xFF];
    return 0;
}

static void bus_write(void *ctx, uint16_t a, uint8_t v)
{
    (void)ctx;
    if (a < 0xC000) ram[a] = v;
    else if (a < 0xC100) io(a, 1, v);
}

/* ============================================================================ */
/* running                                                                      */
/* ============================================================================ */
static void feed_keyboard(void)
{
    if (kbd_head == kbd_tail || (kbd_latch & 0x80)) return;
    if (cpu.cycles - kbd_last < CYCLES_PER_FRAME) return;
    kbd_latch = (uint8_t)kbd_queue[kbd_tail++] | 0x80;
    kbd_last = cpu.cycles;
}

static void run_cycles(uint64_t n)
{
    uint64_t end = cpu.cycles + n;
    while (cpu.cycles < end) {
        feed_keyboard();
        cpu_step(&cpu);
    }
}

/* ============================================================================ */
/* screen                                                                       */
/* ============================================================================ */
static void put32(uint8_t *p, uint32_t v) { p[0] = v >> 24; p[1] = v >> 16; p[2] = v >> 8; p[3] = v; }

static void png_chunk(FILE *f, const char *type, const uint8_t *data, uint32_t len)
{
    uint8_t hdr[8];
    put32(hdr, len);
    memcpy(hdr + 4, type, 4);
    fwrite(hdr, 1, 8, f);
    if (len) fwrite(data, 1, len, f);
    uint32_t crc = crc32(0, hdr + 4, 4);
    if (len) crc = crc32(crc, data, len);
    uint8_t c[4];
    put32(c, crc);
    fwrite(c, 1, 4, f);
}

static int write_png(const char *path, const uint32_t *px, int w, int h)
{
    size_t rawlen = (size_t)h * (w * 3 + 1);
    uint8_t *raw = malloc(rawlen), *q = raw;
    for (int y = 0; y < h; y++) {
        *q++ = 0;
        for (int x = 0; x < w; x++) {
            uint32_t c = px[y * w + x];
            *q++ = c >> 16; *q++ = c >> 8; *q++ = c;
        }
    }
    uLongf zlen = compressBound(rawlen);
    uint8_t *z = malloc(zlen);
    compress2(z, &zlen, raw, rawlen, 9);
    FILE *f = fopen(path, "wb");
    if (!f) return 0;
    static const uint8_t sig[8] = { 0x89, 'P', 'N', 'G', '\r', '\n', 0x1A, '\n' };
    fwrite(sig, 1, 8, f);
    uint8_t ihdr[13];
    put32(ihdr, w); put32(ihdr + 4, h);
    ihdr[8] = 8; ihdr[9] = 2; ihdr[10] = ihdr[11] = ihdr[12] = 0;
    png_chunk(f, "IHDR", ihdr, 13);
    png_chunk(f, "IDAT", z, (uint32_t)zlen);
    png_chunk(f, "IEND", NULL, 0);
    free(raw); free(z);
    return fclose(f) == 0;
}

static int hgr_row_addr(int y, int page2)
{
    return (page2 ? 0x4000 : 0x2000) + (y & 7) * 0x400 + ((y >> 3) & 7) * 0x80 + (y >> 6) * 0x28;
}

static int text_row_addr(int r, int page2)
{
    return (page2 ? 0x800 : 0x400) + (r & 7) * 0x80 + (r >> 3) * 0x28;
}

static void print_text(void)
{
    for (int r = 0; r < 24; r++) {
        char line[41];
        int a = text_row_addr(r, v_page2);
        for (int c = 0; c < 40; c++) {
            int ch = ram[a + c] & 0x7F;
            if (ch < 0x20) ch += 0x40;              /* inverse / flash upper case */
            line[c] = (char)ch;
        }
        line[40] = 0;
        printf("|%s|\n", line);
    }
}

/* HGR in colour: an isolated dot takes its column colour (even: violet/blue,
 * odd: green/orange, by the byte's bit 7) and spans two pixels, one colour
 * period, so 1010 patterns show as solid colour; two adjacent dots are
 * white -- roughly what an NTSC monitor shows. */
static int shot(const char *path)
{
    enum { W = 280, H = 192 };
    static uint32_t img[W * 2 * H * 2];
    static const uint32_t pal[2][2] = { { 0xD043E5, 0x2FB81F }, { 0x1A8FFF, 0xF06A1C } };
    if (v_text) {
        print_text();
        memset(img, 0, sizeof img);
    } else {
        for (int y = 0; y < H; y++) {
            int on[W + 2] = { 0 }, hi[W];
            uint32_t col[W];
            int a = hgr_row_addr(y, v_page2);
            for (int b = 0; b < 40; b++) {
                uint8_t v = ram[a + b];
                for (int i = 0; i < 7; i++) {
                    on[1 + b * 7 + i] = (v >> i) & 1;
                    hi[b * 7 + i] = v >> 7;
                }
            }
            for (int x = 0; x < W; x++) {
                if (on[x + 1]) col[x] = (on[x] || on[x + 2]) ? 0xFFFFFF : pal[hi[x]][x & 1];
                else col[x] = 0;
            }
            /* a colour dot is two pixels wide on screen (one colour period) */
            for (int x = W - 1; x > 0; x--) {
                if (!on[x + 1] && on[x] && col[x - 1] != 0xFFFFFF)
                    col[x] = col[x - 1];
            }
            for (int x = 0; x < W; x++) {
                uint32_t c = col[x];
                img[(2 * y) * (2 * W) + 2 * x] = c;
                img[(2 * y) * (2 * W) + 2 * x + 1] = c;
                img[(2 * y + 1) * (2 * W) + 2 * x] = c;
                img[(2 * y + 1) * (2 * W) + 2 * x + 1] = c;
            }
        }
        if (!v_hires) fprintf(stderr, "a2run: lores not rendered (shot shows HGR memory)\n");
    }
    return write_png(path, img, 2 * W, 2 * H);
}

/* ============================================================================ */
/* script                                                                       */
/* ============================================================================ */
static void queue_keys(const char *s)
{
    for (; *s; s++) {
        char ch = *s;
        if (*s == '\\' && s[1]) {
            s++;
            switch (*s) {
            case 'r': ch = '\r'; break;
            case 'e': ch = 0x1B; break;
            case '<': ch = 0x08; break;
            case '>': ch = 0x15; break;
            case '^': ch = 0x0B; break;
            case 'v': ch = 0x0A; break;
            default: ch = *s; break;
            }
        }
        if (ch >= 'a' && ch <= 'z') ch -= 0x20;     /* a ][+ keyboard */
        if (kbd_head < (int)sizeof kbd_queue) kbd_queue[kbd_head++] = ch;
    }
}

static int load_file(const char *path, uint8_t *dst, long len, long skip)
{
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    if (skip < 0) skip = sz - len;
    fseek(f, skip, SEEK_SET);
    int ok = fread(dst, 1, len, f) == (size_t)len;
    fclose(f);
    return ok;
}

int main(int argc, char **argv)
{
    const char *disk = NULL;
    char roms[1024];
    const char *slash = strrchr(argv[0], '/');
    snprintf(roms, sizeof roms, "%.*s../a2shot/roms", slash ? (int)(slash - argv[0] + 1) : 0, argv[0]);
    int i = 1;
    for (; i < argc; i++) {
        if (!strcmp(argv[i], "--disk") && i + 1 < argc) disk = argv[++i];
        else if (!strcmp(argv[i], "--roms") && i + 1 < argc) snprintf(roms, sizeof roms, "%s", argv[++i]);
        else break;
    }
    if (!disk) {
        fprintf(stderr, "usage: a2run [--roms DIR] --disk X.dsk step...\n");
        return 2;
    }
    char path[1200];
    snprintf(path, sizeof path, "%s/apple2p.rom", roms);
    if (!load_file(path, rom, sizeof rom, -1)) { fprintf(stderr, "a2run: %s\n", path); return 1; }
    snprintf(path, sizeof path, "%s/disk2.rom", roms);
    if (!load_file(path, slot6, 256, 0)) { fprintf(stderr, "a2run: %s\n", path); return 1; }
    for (int k = 0; k < 256; k++) dec62[k] = -1;
    for (int k = 0; k < 64; k++) dec62[enc62[k]] = k;
    if (!load_disk(disk)) return 1;

    for (int k = 0; k < 0xC000; k++) ram[k] = (k & 2) ? 0xFF : 0x00;   /* power-on pattern */
    cpu.read = bus_read;
    cpu.write = bus_write;
    cpu_reset(&cpu);

    for (; i < argc; i++) {
        const char *s = argv[i];
        if (!strncmp(s, "wait:", 5)) {
            run_cycles((uint64_t)atol(s + 5) * CYCLES_PER_FRAME);
        } else if (!strncmp(s, "key:", 4)) {
            queue_keys(s + 4);
            while (kbd_head != kbd_tail || (kbd_latch & 0x80)) run_cycles(1000);
        } else if (!strncmp(s, "shot:", 5)) {
            if (!shot(s + 5)) { fprintf(stderr, "a2run: cannot write %s\n", s + 5); return 1; }
        } else if (!strcmp(s, "text")) {
            print_text();
        } else if (!strncmp(s, "peek:", 5)) {
            unsigned a = (unsigned)strtoul(s + 5, NULL, 16), n = 1;
            const char *c = strchr(s + 5, ':');
            if (c) n = (unsigned)strtoul(c + 1, NULL, 0);
            for (unsigned k = 0; k < n; k++) {
                if (k % 16 == 0) printf("%s%04X:", k ? "\n" : "", a + k);
                printf(" %02X", (a + k) < 0xC000 ? ram[a + k] : bus_read(NULL, (uint16_t)(a + k)));
            }
            printf("\n");
        } else if (!strncmp(s, "poke:", 5)) {
            char *e;
            unsigned a = (unsigned)strtoul(s + 5, &e, 16);
            unsigned v = (unsigned)strtoul(e + 1, NULL, 16);
            if (a < 0xC000) ram[a] = (uint8_t)v;
        } else if (!strncmp(s, "joy:", 4)) {
            double x = 0, y = 0;
            sscanf(s + 4, "%lf,%lf", &x, &y);
            paddle[0] = (uint8_t)((x + 1) * 127.5 + 0.5);
            paddle[1] = (uint8_t)((y + 1) * 127.5 + 0.5);
        } else if (!strncmp(s, "btn:", 4)) {
            int n = 0, v = 0;
            sscanf(s + 4, "%d,%d", &n, &v);
            if (n >= 0 && n < 3) button[n] = (uint8_t)v;
        } else if (!strcmp(s, "reset")) {
            cpu_reset(&cpu);
        } else if (!strcmp(s, "pc")) {
            printf("PC=%04X A=%02X X=%02X Y=%02X S=%02X P=%02X\n", cpu.pc, cpu.a, cpu.x, cpu.y, cpu.s, cpu.p);
        } else if (!strcmp(s, "spk")) {
            printf("spk %lu\n", spk_count);
            spk_count = 0;
        } else if (!strncmp(s, "dsk:", 4)) {
            if (!save_disk(s + 4)) { fprintf(stderr, "a2run: cannot write %s\n", s + 4); return 1; }
        } else {
            fprintf(stderr, "a2run: unknown step '%s'\n", s);
            return 2;
        }
        fflush(stdout);
    }
    return 0;
}
