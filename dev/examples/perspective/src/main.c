/* GPL-3.0. Fixed camera grid; audio is played only on explicit space press. */
#include "hgr.h"
#include "gfx.h"
#include "audio.h"
#include "perspective.h"
#include "camera.h"
#include "chirp.h"

/* Exported breakpoints are useful for the standalone example test. */
void ready(void) {}
void sound_done(void) {}

int main(void)
{
    static unsigned x;
    static unsigned char y, key;
    static a2_projected_t a, b;
    hgr_init();
    hgr_clear(0);
    for (x=0; x<280; x+=28) {
        a2_perspective_project(&camera,x,0,&a);
        a2_perspective_project(&camera,x,191,&b);
        gfx_line(a.x,a.y,b.x,b.y);
    }
    a2_perspective_project(&camera,279,0,&a);
    a2_perspective_project(&camera,279,191,&b);
    gfx_line(a.x,a.y,b.x,b.y);
    for (y=0; y<192; y+=16) {
        a2_perspective_project(&camera,0,y,&a);
        a2_perspective_project(&camera,279,y,&b);
        gfx_line(a.x,a.y,b.x,b.y);
    }
    a2_perspective_project(&camera,0,191,&a);
    a2_perspective_project(&camera,279,191,&b);
    gfx_line(a.x,a.y,b.x,b.y);
    hgr_puts8(8,168,"PERSPECTIVE 280 PIXELS");
    hgr_puts8(8,184,"SPACE: SAMPLE  ESC: DOS");
    ready();
    for (;;) {
        key=apple2_readkey();
        if (key==KC_ESC) break;
        if (key==' ') {
            a2_sample_play(chirp);
            sound_done();
        }
    }
    return 0;
}
