/* Each checkpoint is compared with an independent framebuffer model. */
#include "hgr.h"
#include "gfx.h"
#define STAGE (*(volatile unsigned char *)0x1000)
static const unsigned char sprite[] = {0xA5, 0xC0, 0x5A, 0x80, 0xFF, 0x00};
static const unsigned char packed[] = {0x12, 0x35, 0x7F, 0x61, 0x24, 0x08};
#include "hgr_test_sprite.inc"
static void checkpoint(unsigned char n)
{
    STAGE = n;
    apple2_getkey();
}
int main(void)
{
    unsigned x;
    unsigned char phase;
    hgr_init();
    hgr_set_draw_page(2u); hgr_clear(0x2Au);
    hgr_set_draw_page(1u); hgr_clear(0x80u);
    checkpoint(0u);
    gfx_filled_rect(0u, 0u, 255u, 3u);
    checkpoint(1u);
    gfx_filled_rect(0u, 5u, 279u, 8u);
    checkpoint(2u);
    gfx_filled_rect(65535u, 255u, 100u, 180u);
    checkpoint(3u);
    gfx_filled_rect(280u, 0u, 65535u, 255u);
    gfx_filled_rect(0u, 192u, 279u, 255u);
    hgr_fill_pixrect(0u, 0u, 0u, 10u);
    hgr_fill_pixrect(65535u, 0u, 10u, 10u);
    checkpoint(4u);
    hgr_fill_pixrect(3u, 15u, 10u, 2u);
    hgr_fill_pixrect(275u, 189u, 255u, 255u);
    checkpoint(5u);
    hgr_clear_pixrect(6u, 15u, 4u, 1u);
    checkpoint(6u);
    for (x = 0; x < 280u; ++x) hgr_plot(x, (unsigned char)(x % 192u));
    for (x = 0; x < 280u; x += 3u) hgr_unplot(x, (unsigned char)(x % 192u));
    hgr_plot(280u, 0u); hgr_plot(65535u, 255u);
    checkpoint(7u);
    hgr_blit7(273u, 190u, 3u, 2u, packed, HGR_SET);
    hgr_blit7(1792u, 0u, 3u, 2u, packed, HGR_SET);
    hgr_blit7(65535u, 0u, 3u, 2u, packed, HGR_SET);
    checkpoint(8u);
    for (phase = 0; phase < 7u; ++phase)
        hgr_blit((unsigned)phase * 22u, 50u, 10u, 3u, sprite, HGR_SET);
    hgr_blit(276u, 191u, 10u, 3u, sprite, HGR_SET);
    checkpoint(9u);
    hgr_blit(22u, 50u, 10u, 3u, sprite, HGR_XOR);
    hgr_blit(22u, 50u, 10u, 3u, sprite, HGR_XOR);
    hgr_blit7(14u, 40u, 3u, 2u, packed, HGR_XOR);
    hgr_blit7(14u, 40u, 3u, 2u, packed, HGR_XOR);
    checkpoint(10u);
    for (phase = 0; phase < 7u; ++phase)
        hgr_sprite_xor((unsigned)phase * 22u, 80u, &test_sprite);
    hgr_sprite_xor(276u, 191u, &test_sprite);
    checkpoint(11u);
    for (phase = 0; phase < 7u; ++phase)
        hgr_sprite_xor((unsigned)phase * 22u, 80u, &test_sprite);
    hgr_sprite_xor(276u, 191u, &test_sprite);
    hgr_sprite(200u, 80u, &test_sprite, HGR_SET);
    hgr_sprite(200u, 80u, &test_sprite, HGR_CLEAR);
    checkpoint(12u);
    hgr_puts8(13u, 120u, "Hi!");
    hgr_puts(150u, 120u, "AB");
    hgr_puts8(273u, 184u, "AB");
    checkpoint(13u);
    hgr_fill_rect(100u, 4u, 0u, 6u, 0x7Fu);
    hgr_colorize(0u, 100u, 42u, 4u, HGR_ORANGE);
    hgr_colorize(280u, 0u, 7u, 1u, HGR_BLUE);
    hgr_colorize(65535u, 0u, 7u, 1u, HGR_BLUE);
    checkpoint(14u);
    hgr_puts_color(6u, 136u, "C", HGR_ORANGE);
    hgr_puts_color(15u, 154u, "D", HGR_GREEN);
    checkpoint(15u);
    hgr_putu_field(50u, 20u, 65535u, 5u);
    hgr_putu_field(50u, 20u, 9u, 5u);
    hgr_putu(0u, 20u, 0u);
    hgr_puti(150u, 20u, -32768);
    hgr_putx(0u, 40u, 0xABCDu);
    hgr_putu8(220u, 60u, 65535u);
    checkpoint(16u);
    hgr_cell(34u, 23u, 1u);
    checkpoint(17u);
    hgr_cell(34u, 23u, 0u);
    checkpoint(18u);
    hgr_set_draw_page(2u);
    gfx_filled_rect(279u, 191u, 0u, 0u);
    hgr_show_page();
    checkpoint(19u);
    hgr_set_draw_page(1u); hgr_show_page();
    hgr_text_restore();
    checkpoint(20u);
    return 0;
}
