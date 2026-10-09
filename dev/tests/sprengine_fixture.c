/* VERHILLE Arnaud — GPL-3.0. Independent expected scenes live in Python. */
#include "hgr.h"
#include "gfx.h"
#include <string.h>
#define STAGE (*(volatile unsigned char *)0x1000)
#define RESULT (*(volatile unsigned char *)0x1001)
#define CHECK(x) do { if (!(x)) RESULT |= 1u; } while (0)
#include "masked_test_sprite.inc"
#ifdef SPR_EXTERNAL_POOL
static unsigned char pool[26];
static void init_engine(unsigned char dbuf)
{
    pool[0] = 0xA5u; pool[25] = 0x5Au;
    CHECK(hgr_spr_init_pool(dbuf, pool + 1, 24u, 2u, 6u));
    CHECK(!hgr_spr_init_pool(dbuf, pool + 1, 1u, 2u, 6u));
    CHECK(!hgr_spr_init_pool(dbuf, 0, 24u, 2u, 6u));
    CHECK(!hgr_spr_init_pool(dbuf, pool + 1, 24u, 0u, 6u));
    CHECK(!hgr_spr_init_pool(dbuf, pool + 1, 24u, 2u, 0u));
}
#else
#define init_engine hgr_spr_init
#endif
static void checkpoint(unsigned char stage)
{
#ifdef SPR_EXTERNAL_POOL
    CHECK(pool[0] == 0xA5u && pool[25] == 0x5Au);
#endif
    STAGE = stage;
    apple2_getkey();
}
int main(void)
{
    unsigned i;
    unsigned char phase;
    char number[7];
    hgr_mspr_t invalid;
    RESULT = 0u;
    hgr_init();
    for (i = 0u; i < 8192u; ++i) {
        ((unsigned char *)0x2000)[i] = (unsigned char)(i * 13u + 0x80u);
        ((unsigned char *)0x4000)[i] = (unsigned char)(i * 13u + 0x2Au);
    }
    gfx_utoa(number, 65535u); CHECK(strcmp(number,"65535") == 0);
    gfx_itoa(number, -32767-1); CHECK(strcmp(number,"-32768") == 0);
    init_engine(0u);
    CHECK(hgr_spr_define(0u, &shape0));
    CHECK(hgr_spr_define(1u, &shape1));
    checkpoint(0u);
    for (phase = 0u; phase < 7u; ++phase) {
        hgr_spr_move(0u, 14u + phase, 40u);
        hgr_spr_move(1u, 16u + phase, 41u);
        hgr_spr_update();
        checkpoint(phase + 1u);
    }
    hgr_spr_move(0u, 279u, 191u);
    hgr_spr_move(1u, 280u, 0u);
    hgr_spr_update(); checkpoint(8u);
    CHECK(!hgr_spr_define(0u, &shape1)); /* old definition must survive */
    hgr_spr_hide(0u); hgr_spr_update(); checkpoint(9u);
    init_engine(1u);
    CHECK(hgr_spr_define(0u, &shape0));
    CHECK(hgr_spr_define(1u, &shape1));
    for (phase = 0u; phase < 7u; ++phase) {
        hgr_spr_move(0u, 255u + phase, 187u);
        hgr_spr_move(1u, 257u + phase, 188u);
        hgr_spr_render();
        CHECK(hgr_get_draw_page() == ((phase & 1u) ? 1u : 2u));
        checkpoint(phase + 10u); /* compare before the independent present */
        hgr_spr_present();
        CHECK(hgr_get_draw_page() == ((phase & 1u) ? 2u : 1u));
    }
    hgr_spr_hide(0u); hgr_spr_update(); checkpoint(17u);
    CHECK(!hgr_spr_define(0u, &shape1)); /* other page still needs restore */
    hgr_spr_update(); checkpoint(18u);
    CHECK(hgr_spr_define(0u, 0));
    hgr_spr_hide(1u); hgr_spr_update(); checkpoint(19u);
    hgr_spr_update(); checkpoint(20u);
    init_engine(0u);
    invalid = shape0; invalid.stride = 0u; CHECK(!hgr_spr_define(0u,&invalid));
    invalid = shape0; invalid.h = 0u; CHECK(!hgr_spr_define(0u,&invalid));
    invalid = shape0; invalid.data = 0; CHECK(!hgr_spr_define(0u,&invalid));
    invalid = shape0; invalid.mask = 0; CHECK(!hgr_spr_define(0u,&invalid));
    invalid = shape0; invalid.stride = 41u; CHECK(!hgr_spr_define(0u,&invalid));
    invalid = shape0; invalid.h = 193u; CHECK(!hgr_spr_define(0u,&invalid));
    invalid = shape0; invalid.stride = 4u; invalid.h = 25u;
    CHECK(!hgr_spr_define(0u,&invalid));
    CHECK(!hgr_spr_define(HGR_SPR_MAX,&shape0));
    hgr_spr_move(0u,0u,0u); hgr_spr_update(); checkpoint(21u);
    CHECK(hgr_spr_define(0u,&shape0));
    hgr_spr_move(0u,32u,55u); hgr_spr_update();
    CHECK(!hgr_spr_define(0u,&invalid));
    hgr_spr_move(0u,48u,60u); hgr_spr_update(); checkpoint(22u);
    hgr_spr_hide(0u); hgr_spr_update(); checkpoint(23u);
    CHECK(hgr_spr_define(0u,0));
    for (;;) {}
    return 0;
}
