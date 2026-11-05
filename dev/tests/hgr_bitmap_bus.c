/* Observe bitmap source reads, including otherwise invisible overreads. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "cpu6502.h"
static unsigned char ram[65536];
static unsigned reads[512];
#ifdef HGRC_BLIT7_BUS
#define WIDTH_LIMIT 40
#define SOURCE_BYTES(w) (w)
#else
#define WIDTH_LIMIT 255
#define SOURCE_BYTES(w) (((w) + 7)/8)
#endif
static unsigned char read_byte(void *ctx, uint16_t addr)
{
    (void)ctx;
    if (addr >= 0x9000 && addr < 0x9200) ++reads[addr - 0x9000];
    return ram[addr];
}
static void write_byte(void *ctx, uint16_t addr, uint8_t v)
{
    (void)ctx;
    ram[addr] = v;
}
int main(int argc, char **argv)
{
    unsigned char code[8192];
    static const unsigned modes[] = {0, 1, 2, 255};
    static const unsigned starts[] = {0, 1, 127, 255};
    unsigned w, h, padding, i, row, bytes, stride, steps, mode, bank;
    size_t size;
    FILE *f;
    (void)argc;
    f = fopen(argv[1], "rb"); assert(f);
    size = fread(code, 1, sizeof(code), f); fclose(f);
    assert(size > 0 && size < sizeof(code));
    for (w = 1; w <= WIDTH_LIMIT; ++w) for (h = 1; h <= 2; ++h)
    for (padding = 0; padding <= 1; ++padding)
    for (mode = 0; mode < 4; ++mode) for (bank = 0; bank < 4; ++bank) {
        Cpu cpu = {0};
        memset(ram, 0, sizeof(ram));
        memset(reads, 0, sizeof(reads));
        memcpy(ram + 0x6000, code, size);
        memset(ram + 0x9000, 0xA5, sizeof(reads)/sizeof(reads[0]));
        bytes = SOURCE_BYTES(w);
        stride = bytes + padding;
        ram[0x1000] = w; ram[0x1001] = h; ram[0x1002] = stride;
        ram[0x1004] = modes[mode]; ram[0x1005] = starts[bank];
        cpu.pc = 0x6000; cpu.s = 0xFF; cpu.p = FU;
        cpu.read = read_byte; cpu.write = write_byte;
        for (steps = 0; !ram[0x1003] && steps < 100000; ++steps) cpu_step(&cpu);
        assert(ram[0x1003]);
        for (i = 0; i < 512; ++i) {
            unsigned expected = 0;
            for (row = 0; row < h; ++row)
                if (i >= starts[bank]+row*stride &&
                    i < starts[bank]+row*stride+bytes) ++expected;
            if (reads[i] != expected) {
                fprintf(stderr,"bitmap %ux%u stride %u: source byte %u read %u times (expected %u)\n",
                        w,h,stride,i,reads[i],expected);
                return 1;
            }
        }
    }
#ifdef HGRC_BLIT7_BUS
    puts("HGR byte-sprite bus: 1..40 bytes, all modes, aligned/crossing sources, tight/padded rows, no overreads.");
#else
    puts("HGR bitmap bus: 1..255 pixels, all modes, aligned/crossing sources, tight/padded rows, no overreads.");
#endif
    return 0;
}
