/* CHROMABREAK — VERHILLE Arnaud, GPL-3.0. Apple //e enhanced 128K, ProDOS. */
#include <string.h>
#include "dhgr.h"
#include "apple2io.h"
#include "apple2frame.h"
#include "mouse.h"
#include "prodos.h"
#include "sound.h"
#include "records.h"
#include "layout.h"
#define COLS 12u
#define ROWS 8u
#define LEFT 4u
#define RIGHT 136u
#define PAD_Y CB_PAD_Y
#define PAD_MIN CB_PAD_MIN
#define PAD_BLOCK CB_PAD_BLOCK

/* Public state also serves the emulator regression tests. */
unsigned char state, level, lives, remaining, paused, mode;
unsigned char pad_x, pad_width;
signed char direction, vdirection;
/* This frame's paddle motion (right, up), which puts spin on rebounds. */
signed char pad_motion, pad_lift;
/* Where the caught ball sits on the paddle. */
unsigned char catch_offset;
unsigned char normal_speed;
#pragma bss-name(push,"ZEROPAGE")
unsigned char ball_x, ball_y, ball_live, pad_y;
signed char dx, dy;
unsigned char vx, vy, fraction_x, fraction_y, speed, effect;
#pragma bss-name(pop)
#pragma zpsym("ball_x")
#pragma zpsym("ball_y")
#pragma zpsym("ball_live")
#pragma zpsym("pad_y")
#pragma zpsym("dx")
#pragma zpsym("dy")
#pragma zpsym("vx")
#pragma zpsym("vy")
#pragma zpsym("fraction_x")
#pragma zpsym("fraction_y")
#pragma zpsym("speed")
#pragma zpsym("effect")

unsigned char capsule, cap_x, cap_y, hits, reward_hits, ramp_hits;
unsigned char difficulty=1, combo, multiplier=1;
unsigned char base_width, speed_limit, ramp_period, reward_period;
unsigned char record_cursor, save_status;
static unsigned char end_result;
static char record_initials[4];
#pragma bss-name(push,"LOWBSS")
unsigned char bricks[96], dirty[2][96], dirty_flags[2][96], brick_color[96];
unsigned char extra_ball[18]; /* x,y,live,dx,dy,vx,vy,fx,fy for two balls */
unsigned char shot_live[2], shot_x[2], shot_y[2];
unsigned char particle_x[4],particle_y[4],particle_life[4],particle_color[4];
signed char particle_dx[4];
unsigned char flash_life[96], flash_slot[4];
unsigned char enemy_live[2], enemy_x[2], enemy_y[2], enemy_color[2];
signed char enemy_dx[2], enemy_dy[2];
#pragma bss-name(pop)
/* enemy_hold stops new enemies (regression fixtures only). */
unsigned char enemy_hold, enemy_timer;
static unsigned char enemy_gate;
unsigned char hud_dirty, round_live, laser_cooldown;
static unsigned char flash_cursor,particle_cursor;
extern const unsigned char tile_x[96],tile_y[96];
void __fastcall__ ball_swap(unsigned char id);
void ball_step(void);
void advance_balls(void);
void lasers_step(void);
/* score, best_score and the records count tens of points (every award is a
 * multiple of ten): 16 bits then reach 650000, shown with a final zero. */
unsigned score, best_score, frames;
unsigned next_life_score;
#define SCORE_CAP 65000u
/* Tens of points between extra lives. next_life_score stops one step past
 * the cap, which must still fit 16 bits. */
#define LIFE_STEP 500u
#if LIFE_STEP>65535u-SCORE_CAP
#error "next_life_score would wrap"
#endif
void timing_init(void);
void timing_close(void);
void timing_present(void);
void timing_scan(void);
/* Level bank: one board and its name copied from AUX (render.s). */
void __fastcall__ level_fetch(unsigned char level);
extern unsigned char level_packed[48];
extern char level_name[11];
unsigned char refresh;
extern unsigned char timing_mode, timing_ticks, video_pal;
void timing_measure(void);
/* Attract mode: after 15 s idle on the title, an autopilot plays a board
 * without sound or records; any key, click, lost life or 60 s ends it. */
unsigned char demo;
/* ESC menu: opened from play (resume) or from the title; level choice. */
unsigned char menu_level;
static unsigned char menu_from, start_level, title_quiet;
extern unsigned char sound_muted;
unsigned demo_idle;
static unsigned demo_time, demo_best;
static unsigned char demo_last, demo_level, demo_hold, demo_mx, demo_my;
static signed char demo_aim, demo_dy;
static unsigned char mouse_old, mouse_last_y, button, held, next_capsule, auto_launch;
static const unsigned char colors[12]={13,9,11,1,3,6,7,14,12,4,8,10};
static const unsigned char highlights[16]={2,11,6,7,12,15,7,15,9,13,15,15,14,15,15,15};
static const unsigned char shadows[16]={0,2,0,2,0,2,2,6,4,8,5,1,4,9,6,10};
static const unsigned char angle_x[8]={120,104,80,32,32,80,104,120};
static const unsigned char angle_y[8]={96,144,200,248,248,200,144,96};
static const unsigned char starting_lives[3]={5,3,2};
static const unsigned char paddle_sizes[3]={26,22,18};
static const unsigned char starting_speeds[3]={2,3,4};
static const unsigned char maximum_speeds[3]={4,6,7};
static const unsigned char ramp_periods[3]={10,8,6};
static const unsigned char reward_periods[3]={4,5,6};
static const char *const mode_names[3]={"RELAX", "ARCADE", "EXPERT"};
static const char *const effect_names[7]={"","   ENLARGE","      SLOW","     CATCH","   DISRUPT","     LASER","    PIERCE"};
/* Game ticks between enemy arrivals (30 per second), and the four gates:
 * two at the top, two in the side walls just below the tile grid. */
static const unsigned char enemy_periods[3]={180,135,90};
static const unsigned char gate_x[4]={34,102,4,132};
static const unsigned char gate_y[4]={CB_FIELD_TOP+1,CB_FIELD_TOP+1,CB_GRID_END+2,CB_GRID_END+2};

/* Specialized assembly renderer: no C division or per-row bank calls. */
extern unsigned char render_x,render_y,render_w,render_h,render_color,render_style;
#pragma zpsym("render_x")
#pragma zpsym("render_y")
#pragma zpsym("render_w")
#pragma zpsym("render_h")
#pragma zpsym("render_color")
#pragma zpsym("render_style")

void __fastcall__ fast_draw(unsigned char id);
void __fastcall__ fast_restore(unsigned char id);
void fast_reset(void);
void fast_fill(void);
void fast_paddle(void);
void fast_clone_page(void);
unsigned char page_id;
static unsigned char quitting, dirty_any[2], footer_state;
#pragma bss-name(push,"LOWBSS")
/* One desired HUD, with independent drawn-character histories per page. */
unsigned char hud_wanted[CB_HUD_COLS], hud_previous[2][CB_HUD_COLS];
/* Nonzero while a page may differ from hud_wanted (skips idle scans). */
unsigned char hud_stale[2];
#pragma bss-name(pop)
unsigned char __fastcall__ hud_next(unsigned char page);
static unsigned hud_score;
static unsigned char hud_level;
static void rect(unsigned char x,unsigned char y,unsigned char w,unsigned char h,unsigned char c)
{
    render_x=x; render_y=y; render_w=w; render_h=h; render_color=c; render_style=0;
    fast_fill();
}

void __fastcall__ fast_text(const char *s);
void fine_init(void);
extern unsigned char fine_x, fine_y;
void __fastcall__ fine_char(unsigned char c);
void screen_clear(void);
extern unsigned char bg_on;
void bg_fill(void);
void __fastcall__ video_mixed(unsigned char on);
/* Beautiful Boot text: x counts 7-dot units (80 per line), two per glyph. */
static void text(const char *s,unsigned char x,unsigned char y)
{
    render_x=x; render_y=y; render_color=15; fast_text(s);
}
static void centered(const char *s,unsigned char y)
{
    text(s,40u-(unsigned char)strlen(s),y);
}
/* Color-pixel span under 7-dot units u..u+n-1 (a color pixel is four dots). */
static void underline(unsigned char u,unsigned char n,unsigned char y)
{
    unsigned char x=(unsigned char)(((unsigned)u*7u)>>2);
    rect(x,y,(unsigned char)((((unsigned)(u+n)*7u)>>2)-x),1,14);
}
static void hud_changed(void) { hud_dirty=1; }
const char *__fastcall__ fast_number(unsigned value);
static void number(unsigned value, char *s, unsigned char digits)
{
    timing_scan();
    memcpy(s,fast_number(value)+5u-digits,digits);
    s[digits]=0;
    timing_scan();
}
void hud_number(void);
void __fastcall__ score_add_bcd(unsigned bcd);
void __fastcall__ score_set_bcd(unsigned bcd);
void hud_glyph(void);
void hud(unsigned char budget)
{
    /* Statics: cc65 locals live on its slow software stack. */
    static char digits[6];
    static unsigned char tag, changed;
    static unsigned char *line=hud_wanted;
    static const char *message;
    if (hud_dirty) {
        changed=0;
        timing_scan();
        /* Prepare text on this frame; draw it on the following frame.
         * Keep score conversion and a banked glyph out of the same tick.
         * Pages rescan only when a cell really changed (a paddle rebound
         * merely re-asserts combo x1). */
        if (budget==1u) budget=0;
        hud_dirty=0;
        if (hud_score!=score) {
            hud_score=score;
            hud_number(); changed=1;
        }
        tag='0'+lives;
        if (line[CB_HUD_LIVES]!=tag) { line[CB_HUD_LIVES]=tag; changed=1; }
        tag='0'+multiplier;
        if (line[CB_HUD_MULT]!=tag) { line[CB_HUD_MULT]=tag; changed=1; }
        if (hud_level!=level) {
            changed=1;
            hud_level=level;
            number(level+1u,digits,2); memcpy(line+CB_HUD_LEVEL,digits,2);
        }
        tag=demo ? 64u : paused ? 128u : !round_live ? 0u : effect+1u;
        if (footer_state!=tag) {
            footer_state=tag;
            /* Messages come right-aligned to the 10-cell field. */
            if (demo) message="      DEMO";
            else if (paused) message="    PAUSED";
            else if (!round_live) message="SPACE:FIRE";
            else if (effect) message=effect_names[effect];
            else message=level_name;
            memcpy(line+CB_HUD_MESSAGE,message,CB_HUD_COLS-CB_HUD_MESSAGE);
            changed=1;
        }
        if (changed) hud_stale[0]=hud_stale[1]=1;
    }
    while (budget--) hud_glyph();
}
/* Beveled 9x8 tile with rounded corners and a white glint. Resistance shows
 * as black slits splitting the face: one from two hits, two from three.
 * Damage changes only the slits; destruction erases one tile. */
static void grooves(unsigned char x,unsigned char y,unsigned char hp,unsigned char color)
{
    rect(x+3u,y+2u,1,5,hp>2u ? 0u : color);
    rect(x+5u,y+2u,1,5,hp>2u ? 0u : color);
    if (hp==2u) rect(x+4u,y+2u,1,5,0);
    else if (hp<2u) rect(x+4u,y+2u,1,5,color);
}
static void changed_brick(unsigned char i)
{
    unsigned char x=tile_x[i], y=tile_y[i], hp=bricks[i], color;
    if (!hp) {
        /* Back to the level background (style 7), not plain black. */
        render_x=x; render_y=y; render_w=9; render_h=8; render_color=0; render_style=7;
        fast_fill(); return;
    }
    color=brick_color[i];
    rect(x+1u,y,7,1,flash_life[i] ? 15u : highlights[color]);
    grooves(x,y,hp,color);
}
static void tile(unsigned char x,unsigned char y,unsigned char hp,unsigned char color)
{
    rect(x+1u,y+1u,7,6,color);
    rect(x+1u,y,7,1,highlights[color]);
    rect(x,y+1u,1,6,highlights[color]);
    rect(x+8u,y+1u,1,6,shadows[color]);
    rect(x+1u,y+7u,7,1,shadows[color]);
    rect(x+1u,y+1u,3,1,15); rect(x+1u,y+2u,1,1,15);
    if (hp==255u) {
        /* Steel: a diagonal sheen across the plate. */
        rect(x+6u,y+2u,1,1,15); rect(x+5u,y+3u,1,1,15);
        rect(x+4u,y+4u,1,1,15); rect(x+3u,y+5u,1,1,15);
    } else if (hp>1u) grooves(x,y,hp,color);
}
static void brick(unsigned char i)
{
    if (bricks[i]) tile(tile_x[i],tile_y[i],bricks[i],brick_color[i]);
}
static void background(void)
{
    static unsigned char i;
    screen_clear();
    /* A background per decade, above the paddle zone. */
    bg_on=level/10u+1u; bg_fill();
    /* Two-tone frame: dark blue outside, medium blue inside. */
    rect(2,CB_FIELD_TOP-2,136,1,2); rect(3,CB_FIELD_TOP-1,134,1,6);
    rect(1,CB_FIELD_TOP-2,1,194-CB_FIELD_TOP,2); rect(2,CB_FIELD_TOP-1,1,193-CB_FIELD_TOP,6);
    rect(138,CB_FIELD_TOP-2,1,194-CB_FIELD_TOP,2); rect(137,CB_FIELD_TOP-1,1,193-CB_FIELD_TOP,6);
    for (i=0; i<96u; ++i) brick(i);
    /* The HUD band is mono black (bit 7 clear): no mixed-mode colour cell
     * can bleed into its text. */
    for (fine_x=0,fine_y=CB_HUD_Y;fine_x<80u;) fine_char(' ');
    page_id=dhgr_get_draw_page()-1u;
    memset(hud_previous[page_id],0,CB_HUD_COLS);
    memcpy(hud_wanted,"000000 LIVES 3  LV 01  X1            ",CB_HUD_COLS);
    hud_score=65535u; hud_level=255;
    footer_state=255;
    hud_changed(); hud(CB_HUD_COLS);
    fast_reset(); dirty_any[page_id]=0;

}
void draw_actors(void);
void restore_actors(void);
void render(void)
{
    static unsigned char i;
    timing_scan();
    page_id=dhgr_get_draw_page()-1u;
    restore_actors();
    /* Keep score conversion out of the frame that erases a brick. */
    if (!dirty_any[page_id]) {
        if (hud_dirty) hud(1);
        else if (hud_stale[page_id]) hud_glyph();
    }
    if (dirty_any[page_id]) {
        while (dirty_any[page_id]) {
            i=dirty[page_id][--dirty_any[page_id]]; dirty_flags[page_id][i]=0; changed_brick(i);
        }
    }
    draw_actors();
    sound_tick(); timing_present();
}
/* Bottom-row tile met first, scanning toward dir, by a paddle swept over
 * lo..hi-1 with a two-pixel margin; 0 when none (0 is never a bottom tile). */
static unsigned char pad_tile(unsigned char lo,unsigned char hi,signed char dir)
{
    static unsigned char i, n, t;
    i=dir<0 ? 95u : 84u;
    for (n=12;n;--n) {
        if (bricks[i]) { t=tile_x[i]; if (t<hi+2u && t+11u>lo) return i; }
        if (dir<0) --i; else ++i;
    }
    return 0;
}
/* The paddle cannot pass through tiles: across the bottom tile row it stops
 * at the first tile on its way, and it rises past PAD_BLOCK only where no
 * tile is above it. */
/* Statics, not locals: input() runs every frame and cc65 locals are slow. */
static unsigned char old_x, old_y;
static void pad_walls(void)
{
    if (pad_x<LEFT || pad_x>200u) pad_x=LEFT;
    if (pad_x>RIGHT-pad_width) pad_x=RIGHT-pad_width;
}
static void clamp_pad(void)
{
    static unsigned char i;
    pad_walls();
    if (pad_y>PAD_Y) pad_y=PAD_Y;
    if (pad_y<PAD_MIN) pad_y=PAD_MIN;
    if (pad_y>=PAD_BLOCK) return;
    /* Tiles stop only a paddle that was already at their height: one that
     * rises from below may be under a tile, and then stays below it. */
    if (old_y<PAD_BLOCK) {
        if (pad_x>old_x && (i=pad_tile(old_x,pad_x+pad_width,1))) pad_x=tile_x[i]-2u-pad_width;
        else if (pad_x<old_x && (i=pad_tile(pad_x,old_x+pad_width,-1))) pad_x=tile_x[i]+11u;
    }
    /* No room at this height, under a tile or between a tile and a wall (a
     * paddle that just grew): back below the tiles. */
    i=pad_x; pad_walls();
    if (pad_x!=i || pad_tile(pad_x,pad_x+pad_width,1)) pad_y=PAD_BLOCK;
}
static void attach(void)
{
    if (catch_offset>pad_width-3u) catch_offset=pad_width-3u;
    ball_x=pad_x+catch_offset; ball_y=pad_y-6u;
}
void __fastcall__ mark_dirty(unsigned char i);
static void reset_ball(void)
{
    static unsigned char i;
    for(i=0;i<4u;++i) if(flash_slot[i]!=255u && flash_life[flash_slot[i]]) mark_dirty(flash_slot[i]);
    ball_live=0; capsule=0; effect=0; pad_width=base_width; speed=normal_speed;
    pad_y=PAD_Y; vdirection=0; pad_motion=pad_lift=0; catch_offset=(pad_width>>1)-1u;
    enemy_live[0]=enemy_live[1]=0; enemy_timer=enemy_periods[difficulty];
    combo=0; multiplier=1; round_live=0;
    memset(extra_ball,0,sizeof(extra_ball)); memset(shot_live,0,2);
    memset(particle_life,0,4); memset(flash_life,0,96); memset(flash_slot,255,4);
    laser_cooldown=flash_cursor=particle_cursor=0;
    old_x=pad_x; clamp_pad(); dx=1; dy=-1; vx=64; vy=224; fraction_x=fraction_y=0;
    attach(); hud_changed();
}
static void redraw(void);
static void load_level(void)
{
    static unsigned char i;
    remaining=0;
    level_fetch(level);
    for (i=0;i<96u;++i) {
        bricks[i]=level_packed[i>>1];
        bricks[i]=i&1u ? bricks[i]>>4 : bricks[i]&15u;
        if (bricks[i]==15u) bricks[i]=255u;
        if (bricks[i] && bricks[i]!=255u) ++remaining;
        brick_color[i]=bricks[i]==255u ? 10u : colors[(i+i/COLS*3u+level*2u)%12u];
    }
    memset(dirty_flags,0,sizeof(dirty_flags)); dirty_any[0]=dirty_any[1]=0;
    ramp_hits=reward_hits=hits=0; normal_speed=starting_speeds[difficulty];
    reset_ball();
    if (auto_launch) { ball_live=round_live=1; auto_launch=0; }
    redraw();
}
/* Prepare the hidden page completely from the current state, present it
 * once, then clone it to the other page including sprite save-under. */
static void redraw(void)
{
    static unsigned char i;
    dhgr_draw_page(dhgr_get_display_page()==1u ? 2u : 1u);
    background(); refresh=0; render(); fast_clone_page();
    i=page_id^1u;
    memcpy(hud_previous[i],hud_previous[page_id],CB_HUD_COLS);
    hud_stale[i]=hud_stale[page_id];
    dirty_any[i]=0;
    memset(dirty_flags,0,sizeof(dirty_flags));
}
static void start(void)
{
    state=1; score=0; score_set_bcd(0); next_life_score=LIFE_STEP; lives=starting_lives[difficulty]; paused=0;
    level=demo ? demo_level : start_level;
    base_width=paddle_sizes[difficulty]; speed_limit=maximum_speeds[difficulty];
    ramp_period=ramp_periods[difficulty]; reward_period=reward_periods[difficulty];
    direction=0; pad_x=60; next_capsule=1; frames=0; auto_launch=1; mouse_last_y=mouse_y;
    sound_event(SND_START); load_level();
}
/* Logo from Beautiful Boot glyphs, three lines per glyph row. Dot d starts
 * at color pixel 3d/2, so every double-dot stroke is three pixels wide and a
 * glyph nine; letters advance by eleven. A dark blue shadow, one pixel right
 * and two lines lower, goes first; the top glyph row is lit, the bottom one
 * shaded. */
void __fastcall__ glyph_fetch(unsigned char c);
extern unsigned char glyph[7];
static void logo(const char *s,unsigned char x,unsigned char y)
{
    static unsigned char i, row, bits, d, first, color, shade, pass;
    for (pass=0;pass<2u;++pass)
        for (i=0;s[i];++i) {
            color=colors[i]; glyph_fetch(s[i]);
            for (row=0;row<7u;++row) {
                bits=glyph[row];
                shade=pass==0u ? 2u : row==0u ? highlights[color] :
                      row==6u && shadows[color] ? shadows[color] : color;
                for (d=0;d<7u;) {
                    if (!(bits>>d&1u)) { ++d; continue; }
                    first=d;
                    while (d<7u && bits>>d&1u) ++d;
                    rect(x+i*11u+first*3u/2u+(pass ? 0u : 1u),y+row*3u+(pass ? 0u : 2u),
                         d*3u/2u-first*3u/2u,3,shade);
                }
            }
        }
}
static void difficulty_mark(void)
{
    underline(difficulty==0u ? 17u : difficulty==1u ? 35u : 55u,difficulty ? 12u : 10u,136);
}
static const char credit[]="V1.1  BY ARNAUD VERHILLE";
static void title(void)
{
    static unsigned char i;
    dhgr_draw_page(1); screen_clear();
    logo("CHROMABREAK",10,8);
    centered("APPLE //C AND //E 128K 65C02",37);
    for (i=0;i<12u;++i) tile(5u+i*11u,50,i==11u ? 255u : i==10u ? 3u : i==9u ? 2u : 1u,colors[i]);
    rect(14,66,112,1,14); rect(14,100,112,1,14);
    rect(14,67,1,33,14); rect(125,67,1,33,14);
    centered("PLAY",74);
    centered("CLICK / SPACE / ENTER",87);
    centered(mouse_slot ? "MOUSE ACTIVE" : "KEYBOARD ACTIVE",111);
    centered("1 RELAX  2 ARCADE  3 EXPERT",127);
    difficulty_mark();
    centered("K:KEYS J:JOYSTICK H:SCORES ?:HELP",145);
    centered("ARROWS OR A/D W/X:MOVE  P:PAUSE",157);
    centered("ESC:MENU",169);
    centered(credit,183);
    dhgr_show_page(1); dhgr_draw_page(2);
    /* The theme plays on arrival, not after a demo; a key cuts it short. */
    if (!title_quiet && !sound_muted) play_title();
    title_quiet=0;
    demo_idle=0; demo_last=timing_ticks;
}
/* A score as text: its tens on five digits, then the final zero. */
static char points_text[7];
static void points(unsigned value)
{
    number(value,points_text,5); points_text[5]='0';
}
static void end_screen(void)
{
    dhgr_draw_page(dhgr_get_display_page()==1u ? 2u : 1u); screen_clear();
    centered(state==3 ? "SECTORS CLEARED" : "GAME OVER",48);
    centered("SCORE",76);
    points(score); centered(points_text,90);
    centered("CLICK/SPACE/ENTER:PLAY",130);
    centered("ESC:MENU",152);
    timing_present();
}
static void record_letters(void)
{
    text(record_initials,37,102);
    rect(63,110,14,1,0);
    underline(37u+(record_cursor<3u ? record_cursor : 2u)*2u,2,110);
}
static void record_entry(void)
{
    state=4; record_cursor=0; memcpy(record_initials,"AAA",4);
    dhgr_draw_page(dhgr_get_display_page()==1u ? 2u : 1u); screen_clear();
    centered("NEW HIGH SCORE",36);
    points(score); centered(points_text,60);
    centered("YOUR INITIALS",84); record_letters();
    centered("A-Z:INITIALS  LEFT:DELETE",144);
    centered("ENTER:SAVE  ESC:SKIP",166);
    timing_present(); fast_clone_page();
}
static void record_table(void)
{
    static unsigned char i;
    static char row[15];
    state=5;
    dhgr_draw_page(dhgr_get_display_page()==1u ? 2u : 1u); screen_clear();
    centered("HIGH SCORES",24);
    text("#  ID   SCORE  MODE",19,44);
    underline(19,42,54);
    for(i=0;i<5u;++i) {
        memcpy(row,"1  AAA  000000",15); row[0]='1'+i;
        memcpy(row+3,records[i].initials,3);
        points(records[i].score); memcpy(row+8,points_text,5);
        text(row,19,64u+i*14u);
        text(records[i].score ? mode_names[records[i].mode] : (const char *)"-",49,64u+i*14u);
    }
    if(save_status) centered(save_status==1u ? "SCORE SAVED" : "SAVE FAILED",140);
    centered("ENTER:PLAY   ESC:MENU",170);
    timing_present();
}
static void demo_stop(void);
/* The cleared sector (level is already the next one): a banner drawn on the
 * hidden page and presented, one of ten endings (the sector's place in its
 * decade), then the next board is built on the other page. Nothing is ever
 * drawn on the shown page. */
static void sector_clear(void)
{
    static char line[16];
    sound_stop();
    memcpy(line,"SECTOR 00 CLEAR",16); number(level,line+7,2); line[9]=' ';
    centered(line,140);
    timing_present();
    /* A new sector reached is saved at once (the banner covers the write). */
    if (level>records_progress) {
        records_progress=level; timing_close(); records_save(); timing_init();
    }
    play_jingle((level-1u)%10u);
}
void finale(void);
/* The ENDING overlay goes to page 2 memory while page 1 shows what it draws:
 * the finale once all sectors are cleared (then the records take over), or
 * the help page from the title. */
static void finale_run(void)
{
    sound_stop();
    dhgr_draw_page(1); screen_clear(); dhgr_show_page(1);
    if (records_load_overlay((void *)0x4000,0x2000u)) finale();
    /* Help without its file on the disk: the title comes back. */
    else if (state==0u) { title_quiet=1; title(); }
}
static void ending(void)
{
    if (demo) { demo_stop(); return; }
    end_result=state;
    if (state==3u) finale_run();
    if(records_rank(score)!=255u) record_entry();
    else end_screen();
}
static void update_best(void) { if (score>best_score) best_score=score; }
/* Add tens of points (at most ten), up to the cap; 1 = an extra life. */
static unsigned char award(unsigned char tens)
{
    score+=tens; score_add_bcd(tens>9u ? 0x10u : tens);
    if (score>SCORE_CAP) { score=SCORE_CAP; score_set_bcd(0x5000); }
    if (score>=next_life_score) {
        next_life_score+=LIFE_STEP;
        if (lives<5u) { ++lives; return 1; }
    }
    return 0;
}
void __fastcall__ mark_dirty(unsigned char i)
{
    if(!dirty_flags[0][i]) { dirty_flags[0][i]=1; dirty[0][dirty_any[0]++]=i; }
    if(!dirty_flags[1][i]) { dirty_flags[1][i]=1; dirty[1][dirty_any[1]++]=i; }
}
static void flash(unsigned char i)
{
    static unsigned char old;
    if(!flash_life[i]) {
        old=flash_slot[flash_cursor];
        if(old!=255u && flash_life[old]) { flash_life[old]=0; mark_dirty(old); }
        flash_slot[flash_cursor]=i; flash_cursor=(flash_cursor+1u)&3u;
    }
    flash_life[i]=4;
}
static void burst(unsigned char x,unsigned char y,unsigned char color)
{
    static unsigned char j;
    for(j=0;j<2u;++j) {
        particle_x[particle_cursor]=x; particle_y[particle_cursor]=y;
        particle_life[particle_cursor]=6; particle_color[particle_cursor]=color;
        particle_dx[particle_cursor]=j ? 1 : -1; particle_cursor=(particle_cursor+1u)&3u;
    }
}
static void shards(unsigned char i) { burst(tile_x[i]+4u,tile_y[i]+3u,brick_color[i]); }
void effects_tick(void);
void __fastcall__ damage(unsigned char i)
{
    unsigned char life_bonus;
    timing_scan();
    if (bricks[i]==255u) { sound_event(SND_STEEL); return; }
    --bricks[i];
    mark_dirty(i);
    if(bricks[i]) flash(i); else { flash_life[i]=0; shards(i); }
    if (!bricks[i]) {
        if (combo<21u) {
            ++combo;
            if (combo==3u || combo==6u || combo==9u || combo==12u ||
                combo==15u || combo==18u || combo==21u) ++multiplier;
        }
        life_bonus=award(multiplier);
    } else life_bonus=award(1);
    timing_scan();
    update_best(); hud_changed(); sound_event(bricks[i] ? SND_HIT : SND_BREAK);
    if (life_bonus) sound_event(SND_BONUS);
    timing_scan();
    if (!bricks[i]) {
        --remaining; ++hits;
        if (++ramp_hits>=ramp_period) {
            ramp_hits=0; if (normal_speed<speed_limit) ++normal_speed;
            speed=effect==2u ? 2u : normal_speed;
        }
        if (++reward_hits>=reward_period) {
            reward_hits=0;
            if (!capsule) {
                capsule=next_capsule;
                if (++next_capsule>6u) next_capsule=1;
                cap_x=tile_x[i]+2u; cap_y=tile_y[i];
            }
        }
        if (!remaining) {
            if (++level>=CB_LEVELS) { state=3; sound_event(SND_WIN); ending(); }
            else { refresh=1; sound_event(SND_LEVEL); }
        }
    }
}
/* Enemies: motion and hits in enemies.s; arrivals, scoring and shards here. */
void enemies_tick(void);
unsigned char enemy_blocked(void);
extern unsigned char enemy_hit, enemy_probe_x, enemy_probe_y;
#pragma zpsym("enemy_probe_x")
#pragma zpsym("enemy_probe_y")
static void enemy_down(unsigned char i)
{
    enemy_live[i]=0;
    burst(enemy_x[i]+1u,enemy_y[i]+2u,enemy_color[i]);
    if (award(10)) sound_event(SND_BONUS);
    update_best(); hud_changed(); sound_event(SND_BREAK);
}
/* The multiball budget leaves no frame time for enemies: none arrive while
 * extra balls fly, and the multiball capsule blows up those present. */
static void enemies(void)
{
    static unsigned char i, n;
    if (enemy_live[0] | enemy_live[1]) {
        enemies_tick();
        if (enemy_hit&1u) enemy_down(0);
        if (enemy_hit&2u) enemy_down(1);
    }
    if (enemy_hold || !round_live || extra_ball[2] || extra_ball[11] || --enemy_timer) return;
    enemy_timer=enemy_periods[difficulty];
    i=enemy_live[0] ? 1u : 0u;
    if (enemy_live[i]) return;
    for (n=4;n;--n) {
        enemy_gate=(enemy_gate+1u)&3u;
        enemy_probe_x=gate_x[enemy_gate]; enemy_probe_y=gate_y[enemy_gate];
        if (!enemy_blocked()) {
            enemy_x[i]=enemy_probe_x; enemy_y[i]=enemy_probe_y;
            enemy_dx[i]=enemy_gate&1u ? -1 : 1; enemy_dy[i]=1;
            enemy_color[i]=9; enemy_live[i]=1;
            return;
        }
    }
}
/* Sample the round silhouette: center tips and both sides. */
#include "collision_tables.h"
void rebound(void)
{
    static signed char zone;
    combo=0; multiplier=1; hud_changed();
    zone=ball_x+1u<pad_x ? 0 : (signed char)(((unsigned)(ball_x+1u-pad_x)*8u)/pad_width);
    if (zone>7) zone=7;
    /* Spin: a sliding paddle drags the angle its way (two zones when fast);
     * a rising paddle steepens the bounce, a sinking one flattens it. */
    if (pad_motion>=8) zone+=2; else if (pad_motion>0) ++zone;
    else if (pad_motion<=-8) zone-=2; else if (pad_motion<0) --zone;
    if (zone<0) zone=0; else if (zone>7) zone=7;
    if (pad_lift>0) { if (zone<3) ++zone; else if (zone>4) --zone; }
    else if (pad_lift<0) { if (zone && zone<4) --zone; else if (zone>3 && zone<7) ++zone; }
    dx=zone<4 ? -1 : 1; dy=-1; vx=angle_x[zone]; vy=angle_y[zone];
    fraction_x=fraction_y=0; ball_y=pad_y-6u; sound_event(SND_PAD);
    if (effect==3u) {
        /* Catch: the ball stays where it met the paddle. */
        catch_offset=ball_x>pad_x ? ball_x-pad_x : 0;
        ball_live=round_live=0; attach(); hud_changed();
    }
}
static void drop(void)
{
    static unsigned char center;
    if (!capsule) return;
    ++cap_y;
    /* The 5x6 capsule meets the paddle top. */
    if (cap_y>=pad_y-5u && cap_y<=pad_y && cap_x+4u>=pad_x && cap_x<pad_x+pad_width) {
        effect=capsule; capsule=0;
        center=pad_x+(pad_width>>1);
        pad_width=base_width+(effect==1u ? 8u : 0u);
        pad_x=center>pad_width/2u ? center-pad_width/2u : LEFT;
        old_x=pad_x; clamp_pad(); speed=effect==2u ? 2u : normal_speed;
        memset(shot_live,0,2); laser_cooldown=0;
        if(effect==4u) {
            if (enemy_live[0]) enemy_down(0);
            if (enemy_live[1]) enemy_down(1);
            ball_live=round_live=1; dy=-1; dx=1; vx=32; vy=224;
            memset(extra_ball,0,sizeof(extra_ball));
            extra_ball[0]=extra_ball[9]=ball_x; extra_ball[1]=extra_ball[10]=ball_y;
            extra_ball[2]=extra_ball[11]=1; extra_ball[3]=255; extra_ball[12]=1;
            extra_ball[4]=extra_ball[13]=255; extra_ball[5]=extra_ball[14]=104;
            extra_ball[6]=extra_ball[15]=144;
        }
        if(effect==3u) { memset(extra_ball,0,sizeof(extra_ball)); if(!ball_live) round_live=0; }
        hud_changed(); sound_event(SND_BONUS);
    } else if (cap_y>=PAD_Y) capsule=0;
}
static void fire(void)
{
    if(effect==5u && !laser_cooldown && !shot_live[0] && !shot_live[1]) {
        shot_live[0]=shot_live[1]=1; shot_x[0]=pad_x+2u; shot_x[1]=pad_x+pad_width-3u;
        shot_y[0]=shot_y[1]=pad_y-4u; laser_cooldown=8; sound_event(SND_LAUNCH);
    }
}
/* Joystick or paddles (mode 2), read by timing.s while waiting for VBL. */
extern unsigned char joy_x, joy_y;
void input(unsigned char key)
{
    static int height;
    old_x=pad_x; old_y=pad_y;
    if (key=='M' && mouse_slot) { mode=1; direction=vdirection=0; mouse_poll(); mouse_last_y=mouse_y; }
    if (key=='K') { mode=0; direction=vdirection=0; }
    if (key=='J') { mode=2; direction=vdirection=0; }
    if (key=='P') { paused^=1u; direction=vdirection=0; hud_changed(); sound_stop(); }
    if (key=='A' || key==KC_LEFT) { mode=0; direction=-1; }
    if (key=='D' || key==KC_RIGHT) { mode=0; direction=1; }
    if (key=='W' || key==KC_UP) { mode=0; vdirection=-1; }
    if (key=='X' || key==KC_DOWN) { mode=0; vdirection=1; }
    if (key=='S') direction=vdirection=0;
    if (paused) { mouse_last_y=mouse_y; pad_motion=pad_lift=0; return; }
    if (mode==2u) {
        /* Paddle 0 / stick X sets the centre, paddle 1 / stick Y the height
         * (scaled by timing.s; an underflow wraps and clamps to LEFT). */
        pad_x=joy_x-(pad_width>>1); pad_y=joy_y;
    } else if (mode && mouse_slot) {
        /* Horizontal position is absolute; height follows relative motion. */
        pad_x=mouse_x>pad_width/2u ? mouse_x-pad_width/2u : LEFT;
        height=(int)pad_y+mouse_y-mouse_last_y;
        pad_y=height<PAD_MIN ? PAD_MIN : height>PAD_Y ? PAD_Y : (unsigned char)height;
    } else {
        if (direction<0) pad_x=pad_x>=LEFT+4u ? pad_x-4u : LEFT;
        else if (direction>0) pad_x+=4u;
        if (vdirection) pad_y+=vdirection<0 ? 253u : 3u;
    }
    mouse_last_y=mouse_y;
    clamp_pad();
    pad_motion=(signed char)(pad_x-old_x); pad_lift=(signed char)(old_y-pad_y);
    if (!round_live) attach();
    if (!round_live && (key==' ' || key==KC_RET || (mode && button))) {
        ball_live=round_live=1; hud_changed(); sound_event(SND_LAUNCH);
    }
    if(laser_cooldown) --laser_cooldown;
    if(key==' ' || key==KC_RET || (mode && mouse_old)) fire();
}
/* Autopilot: follow the primary ball a little off-center, varying the aim
 * at each rebound; relaunch after a short hold and fire any laser. */
static void demo_input(void)
{
    static int want;
    old_x=pad_x; old_y=pad_y;
    if (ball_live) {
        if (dy<0 && demo_dy>0) demo_aim=(signed char)((frames*5u)&7u)-4;
        demo_dy=dy;
        want=(int)ball_x+1-(int)(pad_width>>1)+demo_aim;
        if (want>(int)pad_x+6) pad_x+=6u;
        else if (want<(int)pad_x-6) pad_x-=6u;
        else pad_x=want<LEFT ? LEFT : (unsigned char)want;
    }
    clamp_pad();
    pad_motion=(signed char)(pad_x-old_x); pad_lift=0;
    if (!round_live) {
        attach();
        if (++demo_hold>=20u) { demo_hold=0; ball_live=round_live=1; hud_changed(); }
    }
    if (laser_cooldown) --laser_cooldown;
    fire();
}
static void demo_start(void)
{
    demo=1; demo_time=0; demo_hold=0; demo_best=best_score; mode=0;
    start();
    demo_level=demo_level<CB_LEVELS-1u ? demo_level+1u : 0;
}
static void demo_stop(void)
{
    demo=0; best_score=demo_best; sound_stop(); state=0; title_quiet=1; title();
}
/* Title idle time in video refreshes: VBL waits on IIe, VBL IRQs on IIc. */
static unsigned char demo_due(void)
{
    if (timing_mode==2u) { demo_idle+=(unsigned char)(timing_ticks-demo_last); demo_last=timing_ticks; }
    else ++demo_idle;
    return demo_idle>=(video_pal ? 750u : 900u);
}
static void menu(void)
{
    static char line[20];
    state=7;
    dhgr_draw_page(dhgr_get_display_page()==1u ? 2u : 1u); screen_clear();
    centered("MENU",24); underline(36,8,33);
    centered(menu_from ? "ESC:RESUME" : "ESC:TITLE",50);
    centered("ARROWS:CHOOSE LEVEL",76);
    memcpy(line,"LEVEL ",6); number(menu_level+1u,line+6,2);
    level_fetch(menu_level); memcpy(line+8,level_name,11);
    centered(line,92);
    centered("ENTER:PLAY THIS LEVEL",108);
    centered(sound_muted ? "S:SOUND OFF" : "S:SOUND ON ",132);
    centered("T:TITLE",150);
    centered("Q:QUIT TO PRODOS",168);
    timing_present();
}
void game_shutdown(void)
{
    sound_stop(); timing_close(); mouse_close(); video_mixed(0); dhgr_text_restore();
    if (!prodos_video_release()) {
        a2_home(); puts_apple2("/RAM RESTORE FAILED\r");
    }
}
/* Frame boundary exported for tests without changing production gameplay. */
void game_tick(void)
{
    static unsigned char key;
    key=apple2_readkey();
    if(state==4u) {
        if(key==KC_ESC) { state=end_result; end_screen(); return; }
        if(key==KC_RET) {
            sound_stop(); timing_close();
            save_status=records_submit(score,record_initials,difficulty) ? 1u : 2u;
            timing_init(); record_table(); return;
        }
        if(key>='A' && key<='Z' && record_cursor<3u) record_initials[record_cursor++]=key;
        else if(key==KC_LEFT || key==127u) {
            if(record_cursor) --record_cursor;
            record_initials[record_cursor]='A';
        } else { sound_tick(); a2_frame_wait(); return; }
        record_letters(); sound_tick(); timing_present(); return;
    }
    if(state==5u && key==KC_ESC) { state=0; save_status=0; title(); return; }
    if(state==7u) {
        if(key==KC_ESC || key=='R') {
            if(menu_from) { state=1; paused=0; level_fetch(level); hud_changed(); redraw(); } else { state=0; title(); }
        /* Only the sectors reached so far (saved on disk) can be chosen. */
        } else if(key==KC_LEFT || key=='A') { menu_level=menu_level ? menu_level-1u : records_progress; menu(); }
        else if(key==KC_RIGHT || key=='D') { menu_level=menu_level<records_progress ? menu_level+1u : 0; menu(); }
        else if(key==KC_RET || key==' ') { start_level=menu_level; if (mode!=2u) mode=mouse_slot!=0; start(); start_level=0; }
        else if(key=='S') { sound_muted^=1u; sound_stop(); menu(); }
        else if(key=='T') { state=0; title(); }
        else if(key=='Q') quitting=1;
        else { sound_tick(); a2_frame_wait(); }
        return;
    }
    if (demo && key) { demo_stop(); return; }
    if (key==KC_ESC) {
        menu_from=state==1u; menu_level=menu_from ? level : records_progress;
        sound_stop(); menu(); return;
    }
    /* Keyboard play ignores the mouse: skip the firmware call (1300 cycles). */
    if (mode==1u || state!=1u || demo) mouse_poll();
    /* Joystick mode: buttons 0/1 (or the Apple keys) act as the click. */
    held=mode==2u ? (*(volatile unsigned char *)0xC061|*(volatile unsigned char *)0xC062)&0x80u : mouse_buttons&0x80u;
    button=held && !mouse_old;
    mouse_old=held;
    /* 60 s of game ticks, 30 or 25 per second. */
    if (demo && (button || ++demo_time>=(video_pal ? 1500u : 1800u))) { demo_stop(); return; }
    if (state==0u && (key || button || mouse_x!=demo_mx || mouse_y!=demo_my)) {
        demo_mx=mouse_x; demo_my=mouse_y; demo_idle=0; demo_last=timing_ticks;
    }
    if (state!=1u) {
        if(key=='H') { save_status=0; record_table(); return; }
        if (state==0u) {
            /* Help draws the title again itself when it is left. */
            if (key=='?') { finale_run(); return; }
            if (key>='1' && key<='3') {
                /* Only the selection mark moves, on the shown title page. */
                difficulty=key-'1'; dhgr_draw_page(1);
                rect(5,136,130,1,0); difficulty_mark(); dhgr_draw_page(2); return;
            }
        }
        if (key==' ' || key==KC_RET || key=='M' || key=='K' || key=='J' || button) {
            mode=key=='J' ? 2u : (key!='K') && mouse_slot;
            start();
        } else if (state==0u && demo_due()) demo_start();
        else { sound_tick(); a2_frame_wait(); }
        return;
    }
    if (demo) demo_input(); else input(key);
    if (!paused) {
        advance_balls();
        if(state==1u && !refresh) {
            if(!ball_live && round_live) {
                if(extra_ball[2]) ball_swap(0);
                else if(extra_ball[11]) ball_swap(1);
                else if (demo) { demo_stop(); return; }
                else {
                    sound_event(SND_LOST);
                    if(--lives) reset_ball();
                    else { state=2; update_best(); ending(); }
                }
            }
            if(state==1u) { lasers_step(); if(!refresh && state==1u) { drop(); effects_tick(); enemies(); } }
        }
    }
    if (state==1u) {
        if (demo) sound_stop();
        if (refresh) { if (!demo) sector_clear(); load_level(); }
        else render();
        ++frames;
    }
}
int main(void)
{
    a2_text(); a2_home(); fine_init();
    memset(flash_slot,255,4);
    records_load();
    if (!dhgr_init()) {
        puts_apple2("REQUIRES IIE ENHANCED / IIC 128K.\rPRESS A KEY TO RETURN TO PRODOS.\r");
        apple2_getkey(); return 0;
    }
    prodos_video_claim(); video_mixed(1);
    dhgr_draw_page(1); fast_reset(); dhgr_draw_page(2); fast_reset();
    mouse_init(); timing_init(); timing_measure(); a2_frame_set_delay(40);
    mode=mouse_slot!=0; title();
    while (!quitting) game_tick();
    return 0;
}

/* ---- ENDING overlay ($4000, loaded from disk after sector 60) ---------- */
#pragma code-name(push,"FINALE")
#pragma rodata-name(push,"FINALE")
#pragma bss-name(push,"FINALEBSS")
/* Four fireworks at a time, two in the band above the title and two in the
 * band under the score: rings of eight sparks that grow from a random point,
 * fade to grey and start again, until a key or about 20 s. */
/* Spark offsets for ring radius 0..8 (x: dx*r/2, y: dy*r/3), precomputed:
 * cc65 signed multiply/divide would make each frame far too slow. */
static const signed char spark_ox[9][8]={
    {0,0,0,0,0,0,0,0},
    {0,1,1,1,0,-1,-1,-1},
    {0,2,3,2,0,-2,-3,-2},
    {0,3,4,3,0,-3,-4,-3},
    {0,4,6,4,0,-4,-6,-4},
    {0,5,7,5,0,-5,-7,-5},
    {0,6,9,6,0,-6,-9,-6},
    {0,7,10,7,0,-7,-10,-7},
    {0,8,12,8,0,-8,-12,-8}};
static const signed char spark_oy[9][8]={
    {0,0,0,0,0,0,0,0},
    {-2,-1,0,1,2,1,0,-1},
    {-4,-2,0,2,4,2,0,-2},
    {-6,-4,0,4,6,4,0,-4},
    {-8,-5,0,5,8,5,0,-5},
    {-10,-6,0,6,10,6,0,-6},
    {-12,-8,0,8,12,8,0,-8},
    {-14,-9,0,9,14,9,0,-9},
    {-16,-10,0,10,16,10,0,-10}};
static const unsigned char spark_colours[6]={15,13,9,11,14,12};
static unsigned char fw_x[4], fw_y[4], fw_c[4], fw_r[4], fw_seed;
static void sparks(unsigned char b,unsigned char colour)
{
    static unsigned char k, x, y;
    static const signed char *ox, *oy;
    ox=spark_ox[fw_r[b]]; oy=spark_oy[fw_r[b]];
    for (k=0;k<8u;++k) {
        x=fw_x[b]+ox[k]; y=fw_y[b]+oy[k];
        if (x>3u && x<136u && y>1u && y<190u) rect(x,y,1,2,colour);
    }
}
static void launch(unsigned char b)
{
    fw_seed=fw_seed*5u+17u;
    fw_x[b]=14u+fw_seed%112u;
    fw_y[b]=b<2u ? 18u+(fw_seed>>4)%14u : 146u+(fw_seed>>4)%10u;
    fw_c[b]=spark_colours[fw_seed%6u]; fw_r[b]=0;
    sound_event(SND_BREAK);
}
/* Every string of the overlay is a named array: cc65 pools string literals
 * in RODATA, in main memory, whatever the rodata-name in force. */
static const char s_victory[]="VICTORY";
static const char s_cleared[]="ALL 60 SECTORS CLEARED";
static const char s_final[]="FINAL SCORE";
static const char s_thanks[]="THANK YOU FOR PLAYING";
static const char s_capsules[]="BONUS CAPSULES";
static const char help_names[6][8]={"ENLARGE","SLOW","CATCH","DISRUPT","LASER","PIERCE"};
static const char help_effects[6][26]={
    "WIDER PADDLE","SLOWER BALL","BALL STICKS TO THE PADDLE",
    "THREE BALLS","CLICK OR SPACE: FIRE","BREAKS TILES IN ONE HIT"};
static const char s_tiles[]="TILES";
static const char help_hits[3][7]={"1 HIT","2 HITS","3 HITS"};
static const unsigned char help_colors[3]={13,3,12};
static const char s_steel[]="STEEL: NEVER BREAKS";
static const char s_points[]="POINTS";
static const char s_enemy[]="ENEMY: 100 POINTS";
static const char s_combo[]="COMBO: X2 TO X8 EVERY 3 TILES";
static const char s_life[]="5000 POINTS: EXTRA LIFE";
static const char s_key[]="PRESS A KEY";
/* Help, from the title: what each capsule and each tile does, and what
 * scores. Capsules and enemies are the game's own sprites, drawn once on the
 * page shown; fast_reset then forgets their save-under. */
static void sprite(unsigned char x,unsigned char y,unsigned char w,unsigned char color,unsigned char style)
{
    render_x=x; render_y=y; render_w=w; render_h=6; render_color=color; render_style=style;
    fast_draw(4);
}
void help(void)
{
    static unsigned char i, y;
    centered(s_capsules,3); underline(26,28,12);
    for (i=0;i<6u;++i) {
        y=18u+i*11u;
        sprite(10,y+1u,5,i+1u,5);
        text(help_names[i],10,y); text(help_effects[i],26,y);
    }
    centered(s_tiles,90); underline(35,10,99);
    for (i=0;i<3u;++i) {
        tile(8u+i*42u,105,i+1u,help_colors[i]);
        text(help_hits[i],12u+i*24u,105);
    }
    tile(8,117,255,10);
    text(s_steel,12,117);
    centered(s_points,131); underline(34,12,140);
    sprite(8,147,4,9,6); sprite(14,147,4,13,14);
    text(s_enemy,12,146);
    text(s_combo,12,157);
    text(s_life,12,168);
    centered(s_key,182);
    fast_reset();
    while (apple2_readkey()) ;
    /* A key or a click goes back; the click must not start a game. */
    for (;;) {
        if (apple2_readkey()) break;
        mouse_poll();
        if (mouse_buttons&0x80u) { mouse_old=0x80u; break; }
        a2_frame_wait();
    }
    /* Page 1 is drawn again from main memory: this code is still intact. */
    title_quiet=1; title();
}
void finale(void)
{
    static unsigned t;
    static unsigned char b;
    if (state!=3u) { help(); return; }
    logo(s_victory,32,52);
    centered(s_cleared,84);
    points(score);
    centered(s_final,100); centered(points_text,112);
    centered(mode_names[difficulty],124);
    centered(s_thanks,176);
    play_tune(tune_fanfare);
    while (apple2_readkey()) ;
    for (b=0;b<4u;++b) { launch(b); fw_r[b]=b*2u; }
    for (t=0;t<600u && !apple2_readkey();++t) {
        /* One firework per frame keeps the rects within a frame. */
        b=(unsigned char)t&3u;
        if (fw_r[b]) sparks(b,0);
        if (++fw_r[b]>8u) launch(b);
        else sparks(b,fw_r[b]>5u ? 5u : fw_c[b]);
        sound_tick(); a2_frame_wait();
    }
    sound_stop();
}
#pragma bss-name(pop)
#pragma rodata-name(pop)
#pragma code-name(pop)
