/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Double hi-res drawing; banked memory access lives in dhgr_asm.s.
 * Layout and color phase: Apple IIe Technical Note #3, November 1988.
 */
#include "dhgr.h"
#include "hgr_layout.h"

unsigned char *dhgr_addr;
unsigned char dhgr_aux, dhgr_mask, dhgr_bits;
unsigned char dhgr_base;
unsigned char dhgr_display;
unsigned char dhgr_pattern[4]; /* aux even, main even, aux odd, main odd */
void dhgr_write_asm(void);
unsigned char dhgr_read_asm(void);
void dhgr_clear_asm(void);
void dhgr_span_asm(void);
unsigned char dhgr_first, dhgr_last, dhgr_first_mask, dhgr_last_mask;

static void address(unsigned x, unsigned char y)
{
    unsigned char byte = (unsigned char)(x / 7u);
    dhgr_addr = (unsigned char *)(HGR_ROW_ADDR(dhgr_base, y) + (byte >> 1));
    dhgr_aux = (unsigned char)((byte & 1u) ^ 1u);
    dhgr_mask = (unsigned char)(1u << (x % 7u));
}

void dhgr_plot(unsigned x, unsigned char y, unsigned char set)
{
    if (x >= DHGR_WIDTH || y >= DHGR_HEIGHT) return;
    address(x, y);
    dhgr_bits = set ? dhgr_mask : 0u;
    dhgr_write_asm();
}

unsigned char dhgr_getpixel(unsigned x, unsigned char y)
{
    if (x >= DHGR_WIDTH || y >= DHGR_HEIGHT) return 0u;
    address(x, y);
    return (unsigned char)((dhgr_read_asm() & dhgr_mask) != 0u);
}

static unsigned char color_bits(unsigned char color)
{
    color &= 15u;
    return (unsigned char)(((color >> 1) | (color << 3)) & 15u);
}

static void prepare_pattern(unsigned char color)
{
    unsigned pattern;
    unsigned char i;
    pattern = (unsigned)color_bits(color) * 0x1111u;
    for (i = 0; i < 4u; ++i)
        dhgr_pattern[i] = (unsigned char)((pattern >> ((i * 7u) & 3u)) & 0x7Fu);
}

void dhgr_clear(unsigned char color)
{
    prepare_pattern(color);
    dhgr_clear_asm();
}

void dhgr_plot_color(unsigned char x, unsigned char y, unsigned char color)
{
    dhgr_fill_rect(x, y, 1u, 1u, color);
}

static void bit_rect(unsigned x, unsigned char y, unsigned width,
                     unsigned char height)
{
    unsigned end_bit, bottom, row;
    unsigned char first, last, first_mask, last_mask, cy, tail;
    if (x >= DHGR_WIDTH || y >= DHGR_HEIGHT || !width || !height) return;
    /* Subtract first to avoid 16-bit wrap for an arbitrary width. */
    if (width > DHGR_WIDTH - x) width = DHGR_WIDTH - x;
    end_bit = x + width;
    bottom = (unsigned)y + height;
    if (bottom > DHGR_HEIGHT) bottom = DHGR_HEIGHT;
    first = (unsigned char)(x / 7u);
    last = (unsigned char)((end_bit - 1u) / 7u);
    first_mask = (unsigned char)((0x7Fu << (x % 7u)) & 0x7Fu);
    tail = (unsigned char)(end_bit % 7u);
    last_mask = tail ? (unsigned char)((1u << tail) - 1u) : 0x7Fu;
    for (cy = y; cy < bottom; ++cy) {
        row = HGR_ROW_ADDR(dhgr_base, cy);
        dhgr_addr = (unsigned char *)row;
        dhgr_first = first;
        dhgr_last = last;
        dhgr_first_mask = first_mask;
        dhgr_last_mask = last_mask;
        dhgr_span_asm();
    }
}

void dhgr_fill_rect(unsigned char x, unsigned char y,
                    unsigned char width, unsigned char height,
                    unsigned char color)
{
    unsigned right;
    if (x >= DHGR_COLOR_WIDTH) return;
    right = (unsigned)x + width;
    if (right > DHGR_COLOR_WIDTH) right = DHGR_COLOR_WIDTH;
    prepare_pattern(color);
    bit_rect((unsigned)x * 4u, y, (right - x) * 4u, height);
}

void dhgr_fill_bits(unsigned x, unsigned char y, unsigned width,
                    unsigned char height, unsigned char set)
{
    unsigned char i;
    for (i = 0; i < 4; ++i) dhgr_pattern[i] = set ? 0x7F : 0;
    bit_rect(x, y, width, height);
}

void __fastcall__ dhgr_draw_page(unsigned char page)
{
    if (page == 1 || page == 2) dhgr_base = page == 1 ? 0x20 : 0x40;
}

unsigned char dhgr_get_draw_page(void) { return dhgr_base == 0x20 ? 1 : 2; }
unsigned char dhgr_get_display_page(void) { return dhgr_display; }

void dhgr_flip(void)
{
    unsigned char previous = dhgr_display;
    dhgr_show_page(dhgr_get_draw_page());
    dhgr_draw_page(previous);
}
