/* Observe bitmap source reads, including otherwise invisible overreads. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "cpu6502.h"
static unsigned char ram[65536];
static unsigned reads[512];
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
    unsigned w, h, padding, i, row, bytes, stride, steps;
    size_t size;
    FILE *f;
    (void)argc;
    f = fopen(argv[1], "rb"); assert(f);
    size = fread(code, 1, sizeof(code), f); fclose(f);
    assert(size > 0 && size < sizeof(code));
    for (w = 1; w <= 255; ++w) for (h = 1; h <= 2; ++h)
    for (padding = 0; padding <= 1; ++padding) {
        Cpu cpu = {0};
        memset(ram, 0, sizeof(ram));
        memset(reads, 0, sizeof(reads));
        memcpy(ram + 0x6000, code, size);
        memset(ram + 0x9000, 0xA5, sizeof(reads)/sizeof(reads[0]));
        bytes = (w + 7)/8;
        stride = bytes + padding;
        ram[0x1000] = w; ram[0x1001] = h; ram[0x1002] = stride;
        cpu.pc = 0x6000; cpu.s = 0xFF; cpu.p = FU;
        cpu.read = read_byte; cpu.write = write_byte;
        for (steps = 0; !ram[0x1003] && steps < 100000; ++steps) cpu_step(&cpu);
        assert(ram[0x1003]);
        for (i = 0; i < 512; ++i) {
            unsigned expected = 0;
            for (row = 0; row < h; ++row)
                if (i >= row*stride && i < row*stride+bytes) ++expected;
            if (reads[i] != expected) {
                fprintf(stderr,"bitmap %ux%u stride %u: source byte %u read %u times (expected %u)\n",
                        w,h,stride,i,reads[i],expected);
                return 1;
            }
        }
    }
    puts("HGR bitmap bus: 1..255 pixels, tight/padded rows, no source overreads.");
    return 0;
}
