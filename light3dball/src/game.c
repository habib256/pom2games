/* LIGHT3DBALL — original Light Corridor-inspired prototype. GPL-3.0.
 * World: square section 0..127, five courses up to 3072. Ball XY uses Q4.
 * Four swept axial substeps per tick. Rendering never drives collisions.
 */
#include "hgr.h"
#include "hgr_internal.h"
#include "apple2io.h"
#include "apple2frame.h"
#include "mouse.h"
#include "corridor.h"
#pragma rodata-name(push, "ASSETS")
#include "assets.h"
#include "background.h"
#include "levels.h"
#pragma rodata-name(pop)
#include "mousemap.h"

extern unsigned char line_x0, line_y0, line_x1, line_y1;
#pragma zpsym("line_x0")
#pragma zpsym("line_y0")
#pragma zpsym("line_x1")
#pragma zpsym("line_y1")
extern void fast_line(void), frame_mark(void);
extern void erase_scene(void), refresh_rays(void), scene_rectangle(void);
extern unsigned char *rect_cursor;
extern unsigned char scene_line_count, scene_clip_left, scene_clip_right;
extern unsigned char ray_left_top, ray_left_bottom, ray_right_top, ray_right_bottom;
extern unsigned char ray_row0, ray_row1;
#pragma zpsym("rect_cursor")
#pragma zpsym("scene_line_count")
#pragma zpsym("scene_clip_left")
#pragma zpsym("scene_clip_right")
#pragma zpsym("ray_left_top")
#pragma zpsym("ray_left_bottom")
#pragma zpsym("ray_right_top")
#pragma zpsym("ray_right_bottom")
#pragma zpsym("ray_row0")
#pragma zpsym("ray_row1")

/* Exported state also supports deterministic emulator checks. */
int ball_x, ball_y, vel_x, vel_y, ball_z;
int camera_z;
signed char vel_z;
unsigned char paddle_x, paddle_y, lives, launched, advancing, paused, won;
unsigned char door_phase, ticks, hits, wall_hits, blocked;
unsigned frame_count;
unsigned char draw_page, mouse_enabled;
unsigned char level, level_slots, door_visible, aperture_moving;
int level_length, end_contact, camera_limit, plane;
unsigned char aperture_l, aperture_r;
extern void __fastcall__ load_level(unsigned char number);
extern void __fastcall__ opening(unsigned char slot);

static unsigned char quit, mouse_old, page_door[2], page_hud[2];
static unsigned page_camera[2];
static unsigned char keyboard_advance;
static unsigned char dirty_hud;
static unsigned char hud_status;
static unsigned char sound_period, muted;
static char lives_text[2]={'4',0};
static char level_text[2]={'1',0};
static const char level_title[]="LIGHT3D L  LIVES:";
extern void __fastcall__ game_sound(unsigned char period);
extern void step_xy(void);
extern unsigned char paddle_contact(void);
extern int __fastcall__ aim_bias(int offset);
extern void __fastcall__ depth_gauge(unsigned char page);
extern void __fastcall__ reset_gauge(unsigned char page);
static unsigned char scene_lines[2][128], scene_count[2];
static unsigned char old_rays[2][4];
unsigned char sx, sy, left, top, depth;
static unsigned char ball_size, bx, by;
#define project_x a2_corridor_x
#define project_y a2_corridor_y
#define perspective a2_corridor_select
extern void clip_ball(void);
extern void draw_paddle(void);
extern unsigned char ball_clip_left, ball_clip_right;
#pragma zpsym("ball_clip_left")
#pragma zpsym("ball_clip_right")
static unsigned char paddle_screen_x, paddle_screen_y;

/* Geometry and shape used for each page's previous sprites. Restore in reverse
 * order before changing the background, so overlaps and size changes are safe. */
static const hgr_mspr_t *old_shape[2][2];
static unsigned old_x[2][2];
static unsigned char old_y[2][2];
#pragma bss-name(push, "LOWBSS")
/* Save only each sprite's stride * height, including the larger paddle. */
static unsigned char ball_under[2][16];
static unsigned char paddle_under[2][224];
#pragma bss-name(pop)
static unsigned char *const under[2][2] = {
    {ball_under[0], paddle_under[0]}, {ball_under[1], paddle_under[1]}
};

static void position_waiting_ball(void)
{
    ball_x=(int)paddle_x<<4; ball_y=(int)paddle_y<<4;
    ball_z=camera_z+8;
}

/* Only reset or a lost life enters the waiting state. A paddle hit never
 * touches launched, and controls cannot recapture a ball that is in flight. */
static void prepare_ball(void)
{
    launched=0; advancing=0; keyboard_advance=0;
    position_waiting_ball();
    vel_x=0; vel_y=0; vel_z=1;
}

static void serve(void)
{
    if (!launched) { position_waiting_ball(); launched=1; sound_period=64; }
}

static void reset(void)
{
    load_level(level);
    end_contact=level_length-2; camera_limit=level_length-32;
    camera_z=0; paddle_x=64; paddle_y=64; lives=4;
    paused=0; won=0; quit=0; ticks=0; door_phase=0;
    frame_count=0; hits=0; wall_hits=0; blocked=0;
    page_camera[0]=page_camera[1]=0xFFFFu;
    page_door[0]=page_door[1]=255;
    dirty_hud=1; hud_status=255; page_hud[0]=page_hud[1]=0;
    sound_period=0;
    prepare_ball();
}

static void input(void)
{
    unsigned char k=apple2_readkey();
    if (k>='a' && k<='z') k-=32;
    if (k>='1' && k<='5') { level=k-'1'; reset(); }
    if (k==KC_ESC || k=='Q') quit=1;
    if (k=='R') { if (won && level==4) level=0; reset(); }
    if (k=='P') { paused=!paused; ++dirty_hud; }
    if (k=='M') muted=!muted;
    /* Sample the button even while paused: holding it through a pause must
     * not become a fresh serve edge when play resumes. */
    if (mouse_enabled) mouse_poll();
    if (won && level<4 && (k==KC_RET || k==' ' ||
        ((mouse_buttons&128) && !(mouse_old&128)))) { ++level; reset(); }
    if (!paused && !won && lives) {
        if ((k=='J' || k==KC_LEFT) && paddle_x>10) paddle_x-=3;
        if ((k=='L' || k==KC_RIGHT) && paddle_x<117) paddle_x+=3;
        if ((k=='I' || k==KC_UP) && paddle_y>12) paddle_y-=4;
        if ((k=='K' || k==KC_DOWN) && paddle_y<115) paddle_y+=4;
        if (k==' ' && launched) { keyboard_advance=!keyboard_advance; advancing=keyboard_advance; }
        if (mouse_enabled) {
            paddle_x=mouse_map_x[mouse_x];
            paddle_y=mouse_map_y[mouse_y];
            if ((mouse_buttons & 128) && !(mouse_old & 128)) {
                serve();
            }
            if (launched && advancing!=((mouse_buttons & 128)!=0)) {
                advancing=(mouse_buttons & 128)!=0;
            }
        }
        if (paddle_x<8) paddle_x=8;
        if (paddle_x>120) paddle_x=120;
        if (paddle_y<12) paddle_y=12;
        if (paddle_y>116) paddle_y=116;
        if (k==KC_RET || (k==' ' && !launched)) serve();
    }
    if (mouse_enabled) mouse_old=mouse_buttons;
}

void physics(void)
{
    unsigned char step, i, old_wall_hits;
    int dx, dy;
    if (paused || won || !lives) return;
    ++ticks;
    /* Door changes every eight simulation ticks, independent of page parity. */
    door_phase=(ticks>>3)&31;
    if (!launched) { position_waiting_ball(); return; }
    old_wall_hits=wall_hits;
    for (step=0; step<4; ++step) {
        step_xy();
        ball_z+=vel_z;
        /* Axial substeps are exactly +/-1. The packed 128-unit grid locates
         * both faces of any wall in constant time, even in a long course. */
        i=255;
        if (vel_z>0 && (ball_z&127)==126) i=ball_z>>7;
        if (vel_z<0 && (ball_z&127)==2 && ball_z>=128) i=(ball_z>>7)-1;
        if (i<level_slots && i>=(unsigned char)(camera_z>>7)) {
            opening(i);
            if (ball_x<((int)aperture_l+2)*16 || ball_x>((int)aperture_r-2)*16) {
                vel_z=-vel_z; ++wall_hits;
            }
        }
        if (vel_z<0 && ball_z<=camera_z+6) {
            dx=ball_x-((int)paddle_x<<4); dy=ball_y-((int)paddle_y<<4);
            if (paddle_contact()) {
                /* Preserve tangential motion on a central hit. Off-center
                 * impacts add a bounded aiming bias instead of replacing it. */
                vel_x+=aim_bias(dx); vel_y+=aim_bias(dy);
                if (vel_x>8) vel_x=8;
                if (vel_x<-8) vel_x=-8;
                if (vel_y>8) vel_y=8;
                if (vel_y<-8) vel_y=-8;
                vel_z=1; ball_z=camera_z+7; ++hits; sound_period=40;
            } else {
                --lives; ++dirty_hud; prepare_ball(); sound_period=200; return;
            }
        }
        /* The ball wins by hitting the marked cell on the back wall.
         * A miss reflects off the wall, allowing another aimed return. */
        if (vel_z>0 && ball_z>=end_contact) {
            if (camera_z>=level_length-256 && ball_x>=896 && ball_x<=1152 && ball_y>=896 && ball_y<=1152) {
                won=1; advancing=0; keyboard_advance=0; ++dirty_hud;
                ball_z=end_contact; sound_period=24; return;
            }
            ball_z=end_contact+end_contact-ball_z; vel_z=-1; ++wall_hits;
        }
    }
    if (wall_hits!=old_wall_hits && !sound_period) sound_period=112;
    blocked=0;
    if (advancing && ball_z>camera_z+12) {
        if ((camera_z&127)>=118) {
            opening(camera_z>>7);
            /* A side opening reaches the corridor edge: only solid panel
             * edges block the paddle, not the open side of the passage. */
            if (aperture_l && (int)paddle_x<(int)aperture_l+14) blocked=2;
            else if (aperture_r<127 && (int)paddle_x+14>aperture_r) blocked=1;
        }
        if (!blocked && camera_z<camera_limit) camera_z+=2;
    }
}

static void panel(unsigned char x0, unsigned char x1)
{
    if (x1<=x0) return;
    line_x0=x0; line_x1=x1; line_y0=top; line_y1=top+sy;
    scene_rectangle();
}

static void scene(unsigned char pg)
{
    unsigned char i, a, b, first=(unsigned char)(camera_z>>7), last=first+4;
    if (last>level_slots) last=level_slots;
    door_visible=0;
    perspective(level_length-camera_z);
    ray_left_top=ray_right_top=top;
    ray_left_bottom=ray_right_bottom=top+sy;
    for (i=first; i<last; ++i) {
        opening(i);
        door_visible|=aperture_moving;
        perspective(plane-camera_z);
        if (aperture_l && top<ray_left_top) {
            ray_left_top=top; ray_left_bottom=top+sy;
        }
        if (aperture_r<127 && top<ray_right_top) {
            ray_right_top=top; ray_right_bottom=top+sy;
        }
        /* A broad panel can also cover the opposite corridor diagonal.
         * Clip at its actual raster intersection, not just its own side. */
        if (aperture_l) {
            a=project_x(aperture_l);
            if (a>140) {
                b=ray_upper_y[254-a];
                if (b<ray_right_top) {
                    ray_right_top=b; ray_right_bottom=160-b;
                }
            }
        }
        if (aperture_r<127) {
            a=project_x(aperture_r);
            if (a<116) {
                b=ray_upper_y[a-2];
                if (b<ray_left_top) {
                    ray_left_top=b; ray_left_bottom=160-b;
                }
            }
        }
    }
    rect_cursor=scene_lines[pg];
    scene_line_count=scene_count[pg];
    erase_scene();
    if (page_camera[pg]==0xFFFFu) {
        ray_row0=0; ray_row1=159; refresh_rays();
    } else {
        /* Only rows whose visibility changed need their old rays removed. */
        if (ray_left_top!=old_rays[pg][0]) {
            ray_row0=ray_left_top<old_rays[pg][0] ? ray_left_top : old_rays[pg][0];
            ray_row1=(ray_left_top>old_rays[pg][0] ? ray_left_top : old_rays[pg][0])-1;
            refresh_rays();
        }
        if (ray_left_bottom!=old_rays[pg][1]) {
            ray_row0=(ray_left_bottom<old_rays[pg][1] ? ray_left_bottom : old_rays[pg][1])+1;
            ray_row1=ray_left_bottom>old_rays[pg][1] ? ray_left_bottom : old_rays[pg][1];
            refresh_rays();
        }
        if (ray_right_top!=old_rays[pg][2]) {
            ray_row0=ray_right_top<old_rays[pg][2] ? ray_right_top : old_rays[pg][2];
            ray_row1=(ray_right_top>old_rays[pg][2] ? ray_right_top : old_rays[pg][2])-1;
            refresh_rays();
        }
        if (ray_right_bottom!=old_rays[pg][3]) {
            ray_row0=(ray_right_bottom<old_rays[pg][3] ? ray_right_bottom : old_rays[pg][3])+1;
            ray_row1=ray_right_bottom>old_rays[pg][3] ? ray_right_bottom : old_rays[pg][3];
            refresh_rays();
        }
    }
    old_rays[pg][0]=ray_left_top; old_rays[pg][1]=ray_left_bottom;
    old_rays[pg][2]=ray_right_top; old_rays[pg][3]=ray_right_bottom;
    rect_cursor=scene_lines[pg];
    scene_clip_left=0; scene_clip_right=255;
    /* Near-to-far visibility windows: hidden strokes are never drawn. */
    for (i=first; i<last; ++i) {
        opening(i); perspective(plane-camera_z);
        a=project_x(aperture_l); b=project_x(aperture_r);
        if (aperture_l) {
            panel(left,a);
            if (a>=scene_clip_left) scene_clip_left=a+1;
        }
        if (aperture_r<127) {
            panel(b,left+sx);
            if (b<=scene_clip_right) scene_clip_right=b-1;
        }
    }
    perspective(level_length-camera_z);
    line_x0=left; line_x1=left+sx; line_y0=top; line_y1=top+sy;
    scene_rectangle();
    if (level_length-camera_z<=256) {
        line_x0=project_x(54); line_x1=project_x(74);
        line_y0=project_y(54); line_y1=project_y(74);
        scene_rectangle();
    }
    scene_count[pg]=(rect_cursor-scene_lines[pg])>>2;
}

static void restore(unsigned char pg)
{
    signed char id;
    for (id=1; id>=0; --id) {
        if (!old_shape[pg][id]) continue;
        hgr_ms_x=old_x[pg][id]; hgr_ms_y=old_y[pg][id];
        hgr_ms_spr=old_shape[pg][id]; hgr_ms_under=under[pg][id];
        hgr_ms_restore_run(); old_shape[pg][id]=0;
    }
}

static void sprite(unsigned char pg, unsigned char id, unsigned char x,
                   unsigned char y, const hgr_mspr_t *shape)
{
    hgr_ms_x=x; hgr_ms_y=y; hgr_ms_spr=shape; hgr_ms_under=under[pg][id];
    if (id) draw_paddle(); else hgr_msu_run();
    old_shape[pg][id]=shape; old_x[pg][id]=x; old_y[pg][id]=y;
}

static void hud(unsigned char pg)
{
    unsigned char status=won ? 5 : !lives ? 4 : paused ? 3 : !launched ? 0 :
        blocked ? blocked+8 : 1;
    if (hud_status!=status) { hud_status=status; ++dirty_hud; }
    if (page_hud[pg]==dirty_hud) return;
    hgr_fill_rect(160,32,0,40,0);
    hgr_puts8(7,160,level_title);
    level_text[0]='1'+level;
    hgr_puts8(77,160,level_text);
    lives_text[0]='0'+lives;
    hgr_puts8(135,160,lives_text);
    hgr_puts8(7,170,status==5 ? (level<4 ? "TARGET HIT! CLICK/RETURN" : "FINAL CLEAR! R:NEW GAME") : status==4 ? "GAME OVER  R:RESTART" :
        status==3 ? "PAUSED  P:RESUME" : status==0 ?
        (mouse_enabled ? "CLICK:SERVE  MOVE MOUSE" : "RETURN:SERVE  IJKL:MOVE") :
        status==9 ? "BLOCKED:MOVE LEFT" : status==10 ? "BLOCKED:MOVE RIGHT" : "");
    hgr_puts8(7,182,"1-5:LEVEL P:PAUSE M:SOUND Q:QUIT");
    page_hud[pg]=dirty_hud;
    reset_gauge(pg);
}

void render(void)
{
    unsigned char pg=draw_page-1, i, edge, first=(unsigned char)(camera_z>>7), last=first+4;
    int dist;
    hgr_set_draw_page(draw_page);
    restore(pg);
    /* Cache the exact pose used to draw each page. A four-unit cache key
     * retained different two-unit projections on alternating pages at rest. */
    if (page_camera[pg]!=(unsigned)camera_z ||
        (door_visible && page_door[pg]!=door_phase)) {
        scene(pg); page_camera[pg]=(unsigned)camera_z; page_door[pg]=door_phase;
    }
    dist=ball_z-camera_z;
    if (dist<0) dist=0;
    perspective(dist);
    ball_size=depth<32 ? 2 : depth<64 ? 1 : 0;
    bx=project_x(ball_x>>4); by=project_y(ball_y>>4);
    /* Intersect the nearer openings. Clip the sprite's actual pixels instead
     * of making the whole sphere vanish when its centre crosses an edge. */
    ball_clip_left=0; ball_clip_right=255;
    if (last>level_slots) last=level_slots;
    for (i=first; i<last; ++i) {
        opening(i);
        if (plane>=ball_z) continue;
        perspective(plane-camera_z);
        if (aperture_l) {
            edge=project_x(aperture_l)+1;
            if (edge>ball_clip_left) ball_clip_left=edge;
        }
        if (aperture_r<127) {
            edge=project_x(aperture_r)-1;
            if (edge<ball_clip_right) ball_clip_right=edge;
        }
    }
    if (ball_clip_left<=ball_clip_right && lives) {
        i=balls[ball_size]->h>>1;
        sprite(pg,0,bx-i,by-i,balls[ball_size]);
        clip_ball();
    }
    perspective(4);
    paddle_screen_x=project_x(paddle_x)-24;
    paddle_screen_y=project_y(paddle_y)-14;
    sprite(pg,1,paddle_screen_x,paddle_screen_y,&paddle);
    hud(pg);
    depth_gauge(pg);
    if (sound_period) {
        if (!muted) game_sound(sound_period);
        sound_period=0;
    }
    a2_frame_wait();
    hgr_show_page(); draw_page=3-draw_page;
    ++frame_count; frame_mark();
}

void main(void)
{
    unsigned char i;
    hgr_init();
    hgr_build_tables(); /* Native wireframe renderer reads the shared X tables. */
    for (i=1; i<=2; ++i) { hgr_set_draw_page(i); hgr_clear(0); }
    a2_frame_init(); a2_frame_set_delay(1);
    mouse_enabled=mouse_init();
    old_shape[0][0]=old_shape[0][1]=old_shape[1][0]=old_shape[1][1]=0;
    draw_page=2; reset();
    while (!quit) { input(); physics(); render(); }
    mouse_close(); hgr_text_restore();
}
