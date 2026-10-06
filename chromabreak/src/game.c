/* CHROMABREAK — VERHILLE Arnaud, GPL-3.0. Apple //e enhanced 128K, ProDOS. */
#include <string.h>
#include "dhgr.h"
#include "apple2io.h"
#include "apple2frame.h"
#include "mouse.h"
#include "prodos.h"
#include "levels.h"
#include "sound.h"
#include "records.h"
#include "layout.h"
#define COLS 12u
#define ROWS 8u
#define LEFT 4u
#define RIGHT 136u
#define PAD_Y CB_PAD_Y

/* Public state also serves the emulator regression tests. */
unsigned char state, level, lives, remaining, paused, mode;
unsigned char pad_x, pad_width;
signed char direction;
unsigned char normal_speed;
#pragma bss-name(push,"ZEROPAGE")
unsigned char ball_x, ball_y, ball_live;
signed char dx, dy;
unsigned char vx, vy, fraction_x, fraction_y, speed, effect;
#pragma bss-name(pop)
#pragma zpsym("ball_x")
#pragma zpsym("ball_y")
#pragma zpsym("ball_live")
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
#pragma bss-name(pop)
unsigned char hud_dirty, round_live, laser_cooldown;
static unsigned char flash_cursor,particle_cursor;
extern const unsigned char tile_x[96],tile_y[96];
void __fastcall__ ball_swap(unsigned char id);
void ball_step(void);
void advance_balls(void);
void lasers_step(void);
unsigned score, best_score, frames;
unsigned next_life_score;
void timing_init(void);
void timing_close(void);
void timing_present(void);
void timing_scan(void);
unsigned char refresh;
static unsigned char mouse_old, button, next_capsule, auto_launch;
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
static void text(const char *s,unsigned char x,unsigned char y)
{
    render_x=x; render_y=y; render_color=15; fast_text(s);
}
/* Compact font: a five-column advance, independent of DHGR byte phase. */
static void centered(const char *s,unsigned char y)
{
    text(s,(140u-(unsigned char)strlen(s)*DHGR_SMALL_ADVANCE)/2u,y);
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
void __fastcall__ hud_number(unsigned value);
void hud_glyph(void);
void hud(unsigned char budget)
{
    static char digits[6];
    unsigned char tag;
    unsigned char *line=hud_wanted;
    const char *message;
    if (hud_dirty) {
        timing_scan();
        /* Prepare text on this frame; draw it on the following frame.
         * Keep score conversion and a banked glyph out of the same tick. */
        if (budget==1u) budget=0;
        hud_dirty=0;
        if (hud_score!=score) {
            hud_score=score;
            hud_number(score);
        }
        line[7]='0'+lives;
        line[14]='X'; line[15]='0'+multiplier;
        if (hud_level!=level) {
            hud_level=level;
            number(level+1u,digits,2); memcpy(line+11,digits,2);
        }
        tag=paused ? 128u : !round_live ? 0u : effect+1u;
        if (footer_state!=tag) {
            footer_state=tag;
            message=paused ? "PAUSED" : !round_live ? "SPACE:FIRE" :
                      effect==1 ? "WIDE" : effect==2 ? "SLOW" :
                      effect==3 ? "CATCH" : effect==4 ? "MULTIBALL" :
                      effect==5 ? "LASER" : effect==6 ? "PIERCE" : "PLAY";
            if (!paused && round_live && !effect) message=level_names[level];
            memset(line+16,' ',CB_HUD_COLS-16); memcpy(line+16,message,strlen(message));
        }
    }
    while (budget--) hud_glyph();
}
/* Damage changes only the resistance notches; destruction erases one tile. */
static void changed_brick(unsigned char i)
{
    unsigned char x=tile_x[i], y=tile_y[i], hp=bricks[i], color;
    if (!hp) { rect(x,y,9,8,0); return; }
    color=brick_color[i];
    rect(x,y,9,1,flash_life[i] ? 15u : highlights[color]);
    rect(x+2u,y+3u,1,2,hp>1u ? 0u : color);
    rect(x+6u,y+3u,1,2,hp>2u ? 0u : color);
}
static void brick(unsigned char i)
{
    unsigned char x=tile_x[i], y=tile_y[i], hp=bricks[i], color;
    if (!hp) return;
    color=brick_color[i];
    rect(x,y,9,8,color);
    rect(x,y,9,1,highlights[color]);
    rect(x,y+1u,1,6,highlights[color]);
    rect(x+8u,y+1u,1,7,shadows[color]);
    rect(x,y+7u,9,1,shadows[color]);
    rect(x+1u,y+1u,2,1,15);
    if (hp==255u) {
        rect(x+2u,y+2u,1,4,15); rect(x+6u,y+2u,1,4,5);
    } else if (hp>1u) {
        rect(x+2u,y+3u,1,2,0);
        if (hp>2u) rect(x+6u,y+3u,1,2,0);
    }
}
static void background(void)
{
    unsigned char i;
    dhgr_clear(0);
    rect(4,CB_FIELD_TOP-1,132,1,2); rect(4,191,132,1,2);
    rect(2,CB_FIELD_TOP,1,191-CB_FIELD_TOP,2); rect(137,CB_FIELD_TOP,1,191-CB_FIELD_TOP,2);
    for (i=0; i<96u; ++i) brick(i);
    page_id=dhgr_get_draw_page()-1u;
    memset(hud_previous[page_id],0,CB_HUD_COLS);
    memcpy(hud_wanted,"00000 L3 LV01   ",16);
    hud_score=65535u; hud_level=255;
    footer_state=255;
    hud_changed(); hud(CB_HUD_COLS);
    fast_reset(); dirty_any[page_id]=0;

}
void draw_actors(void);
void render(void)
{
    unsigned char i;
    timing_scan();
    page_id=dhgr_get_draw_page()-1u;
    for(i=10;i;--i) fast_restore(i);
    /* Keep score conversion out of the frame that erases a brick. */
    if (!dirty_any[page_id]) hud(1);
    if (dirty_any[page_id]) {
        while (dirty_any[page_id]) {
            i=dirty[page_id][--dirty_any[page_id]]; dirty_flags[page_id][i]=0; changed_brick(i);
        }
    }
    draw_actors();
    sound_tick(); timing_present();
}
static void clamp_pad(void)
{
    if (pad_x<LEFT) pad_x=LEFT;
    if (pad_x>RIGHT-pad_width) pad_x=RIGHT-pad_width;
}
static void attach(void) { ball_x=pad_x+(pad_width>>1)-1u; ball_y=PAD_Y-6u; }
void __fastcall__ mark_dirty(unsigned char i);
static void reset_ball(void)
{
    unsigned char i;
    for(i=0;i<4u;++i) if(flash_slot[i]!=255u && flash_life[flash_slot[i]]) mark_dirty(flash_slot[i]);
    ball_live=0; capsule=0; effect=0; pad_width=base_width; speed=normal_speed;
    combo=0; multiplier=1; round_live=0;
    memset(extra_ball,0,sizeof(extra_ball)); memset(shot_live,0,2);
    memset(particle_life,0,4); memset(flash_life,0,96); memset(flash_slot,255,4);
    laser_cooldown=flash_cursor=particle_cursor=0;
    clamp_pad(); dx=1; dy=-1; vx=64; vy=224; fraction_x=fraction_y=0;
    attach(); hud_changed();
}
static void load_level(void)
{
    unsigned char i;
    memcpy(bricks,boards[level],96);
    remaining=0;
    for (i=0;i<96u;++i) {
        if (bricks[i] && bricks[i]!=255u) ++remaining;
        brick_color[i]=bricks[i]==255u ? 10u : colors[(i+i/COLS*3u+level*2u)%12u];
    }
    memset(dirty_flags,0,sizeof(dirty_flags)); dirty_any[0]=dirty_any[1]=0;
    ramp_hits=reward_hits=hits=0; normal_speed=starting_speeds[difficulty];
    reset_ball();
    if (auto_launch) { ball_live=round_live=1; auto_launch=0; }
    /* Prepare the currently hidden page completely, present it once, then
     * clone it to the other (now hidden) page including sprite save-under. */
    dhgr_draw_page(dhgr_get_display_page()==1u ? 2u : 1u);
    background(); refresh=0; render(); fast_clone_page();
    i=page_id^1u;
    memcpy(hud_previous[i],hud_previous[page_id],CB_HUD_COLS);
    dirty_any[i]=0;
    memset(dirty_flags,0,sizeof(dirty_flags));
}
static void start(void)
{
    state=1; score=0; next_life_score=1000; lives=starting_lives[difficulty]; level=0; paused=0;
    base_width=paddle_sizes[difficulty]; speed_limit=maximum_speeds[difficulty];
    ramp_period=ramp_periods[difficulty]; reward_period=reward_periods[difficulty];
    direction=0; pad_x=60; next_capsule=1; frames=0; auto_launch=1;
    sound_event(SND_START); load_level();
}
static void title(void)
{
    unsigned char i, x, color;
    unsigned char row, col, bits;
    const unsigned char *glyph;
    static const char name[]="CHROMABREAK";
    dhgr_draw_page(1); dhgr_clear(0);
    /* The compact library font also supplies the enlarged colored logo. */
    for (i=0;i<11u;++i) {
        glyph=dhgr_small_font+(unsigned)(name[i]-32u)*DHGR_SMALL_FONT_STRIDE;
        for(row=0;row<5u;++row) {
            bits=glyph[row];
            for(col=0;col<4u;++col) {
                if(bits&1u) rect(15u+i*10u+col*2u,18u+row*2u,2,2,colors[i]);
                bits>>=1;
            }
        }
    }
    centered("APPLE //E / //C",36);
    for (i=0;i<12u;++i) {
        x=5u+i*11u; color=colors[i];
        rect(x,50,9,8,color); rect(x,50,9,1,highlights[color]);
        rect(x,57,9,1,shadows[color]); rect(x+1u,51,2,1,15);
    }
    rect(14,72,112,1,14); rect(14,104,112,1,14);
    rect(14,73,1,31,14); rect(125,73,1,31,14);
    centered("PLAY",80);
    centered("CLICK / SPACE / ENTER",92);
    centered(mouse_slot ? "MOUSE ACTIVE" : "KEYBOARD ACTIVE",114);
    centered("1 RELAX  2 ARCADE  3 EXPERT",133);
    x=difficulty==0u ? 12u : difficulty==1u ? 57u : 107u;
    rect(x,141,difficulty ? 30u : 25u,1,14);
    centered("K:KEYBOARD  H:HIGH SCORES",158);
    centered("A/D OR ARROWS:MOVE  P:PAUSE",171);
    centered("ESC:QUIT TO PRODOS",184);
    dhgr_show_page(1); dhgr_draw_page(2);
}
static void end_screen(void)
{
    static char value[6];
    dhgr_draw_page(dhgr_get_display_page()==1u ? 2u : 1u); dhgr_clear(0);
    centered(state==3 ? "SECTORS CLEARED" : "GAME OVER",48);
    centered("SCORE",76);
    number(score,value,5); centered(value,90);
    centered("CLICK/SPACE/ENTER:PLAY",130);
    centered("ESC:QUIT TO PRODOS",152);
    timing_present();
}
static void record_letters(void)
{
    text(record_initials,63,102);
    rect(63,110,15,1,0);
    rect(63u+(record_cursor<3u ? record_cursor : 2u)*5u,110,3,1,14);
}
static void record_entry(void)
{
    static char value[6];
    state=4; record_cursor=0; memcpy(record_initials,"AAA",4);
    dhgr_draw_page(dhgr_get_display_page()==1u ? 2u : 1u); dhgr_clear(0);
    centered("NEW HIGH SCORE",36);
    number(score,value,5); centered(value,60);
    centered("YOUR INITIALS",84); record_letters();
    centered("A-Z:INITIALS  LEFT:DELETE",144);
    centered("ENTER:SAVE  ESC:SKIP",166);
    timing_present(); fast_clone_page();
}
static void record_table(void)
{
    unsigned char i;
    static char row[12], value[6];
    state=5;
    dhgr_draw_page(dhgr_get_display_page()==1u ? 2u : 1u); dhgr_clear(0);
    centered("HIGH SCORES",24);
    text("  ID  SCORE MODE",24,44);
    rect(20,54,100,1,14);
    for(i=0;i<5u;++i) {
        memcpy(row,"1 AAA 00000",12); row[0]='1'+i;
        memcpy(row+2,records[i].initials,3);
        number(records[i].score,value,5); memcpy(row+6,value,5);
        text(row,24,64u+i*14u);
        text(records[i].score ? mode_names[records[i].mode] : (const char *)"-",84,64u+i*14u);
    }
    if(save_status) centered(save_status==1u ? "SCORE SAVED" : "SAVE FAILED",140);
    centered("ENTER:PLAY   ESC:MENU",170);
    timing_present();
}
static void ending(void)
{
    end_result=state;
    if(records_rank(score)!=255u) record_entry();
    else end_screen();
}
static void update_best(void) { if (score>best_score) best_score=score; }
void __fastcall__ mark_dirty(unsigned char i)
{
    if(!dirty_flags[0][i]) { dirty_flags[0][i]=1; dirty[0][dirty_any[0]++]=i; }
    if(!dirty_flags[1][i]) { dirty_flags[1][i]=1; dirty[1][dirty_any[1]++]=i; }
}
static void flash(unsigned char i)
{
    unsigned char old;
    if(!flash_life[i]) {
        old=flash_slot[flash_cursor];
        if(old!=255u && flash_life[old]) { flash_life[old]=0; mark_dirty(old); }
        flash_slot[flash_cursor]=i; flash_cursor=(flash_cursor+1u)&3u;
    }
    flash_life[i]=4;
}
static void shards(unsigned char i)
{
    unsigned char j;
    for(j=0;j<2u;++j) {
        particle_x[particle_cursor]=tile_x[i]+4u; particle_y[particle_cursor]=tile_y[i]+3u;
        particle_life[particle_cursor]=6; particle_color[particle_cursor]=brick_color[i];
        particle_dx[particle_cursor]=j ? 1 : -1; particle_cursor=(particle_cursor+1u)&3u;
    }
}
void effects_tick(void);
void __fastcall__ damage(unsigned char i)
{
    unsigned char life_bonus=0;
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
        score+=(unsigned)multiplier*10u;
    } else score+=10u;
    if (score>59990u) score=59990u;
    if (score>=next_life_score) {
        next_life_score+=1000u;
        if (lives<5u) { ++lives; life_bonus=1; }
    }
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
            if (++level>=12u) { state=3; sound_event(SND_WIN); ending(); }
            else { refresh=1; sound_event(SND_LEVEL); }
        }
    }
}
/* Sample the round silhouette: center tips and both sides. */
#include "collision_tables.h"
void rebound(void)
{
    unsigned char zone;
    combo=0; multiplier=1; hud_changed();
    zone=ball_x+1u<pad_x ? 0u : ((unsigned)(ball_x+1u-pad_x)*8u)/pad_width;
    if (zone>7u) zone=7;
    dx=zone<4u ? -1 : 1; dy=-1; vx=angle_x[zone]; vy=angle_y[zone];
    fraction_x=fraction_y=0; ball_y=PAD_Y-6u; sound_event(SND_PAD);
    if (effect==3u) { ball_live=round_live=0; attach(); hud_changed(); }
}
static void drop(void)
{
    unsigned char center;
    if (!capsule) return;
    ++cap_y;
    if (cap_y>=PAD_Y-5u && cap_y<=PAD_Y && cap_x+3u>=pad_x && cap_x<pad_x+pad_width) {
        effect=capsule; capsule=0;
        center=pad_x+(pad_width>>1);
        pad_width=base_width+(effect==1u ? 8u : 0u);
        pad_x=center>pad_width/2u ? center-pad_width/2u : LEFT;
        clamp_pad(); speed=effect==2u ? 2u : normal_speed;
        memset(shot_live,0,2); laser_cooldown=0;
        if(effect==4u) {
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
void input(unsigned char key)
{
    if (key=='M' && mouse_slot) { mode=1; direction=0; }
    if (key=='K') { mode=0; direction=0; }
    if (key=='P') { paused^=1u; direction=0; hud_changed(); sound_stop(); }
    if (key=='A' || key==KC_LEFT) { mode=0; direction=-1; }
    if (key=='D' || key==KC_RIGHT) { mode=0; direction=1; }
    if (key=='S') direction=0;
    if (paused) return;
    if (mode && mouse_slot) {
        pad_x=mouse_x>pad_width/2u ? mouse_x-pad_width/2u : LEFT;
    } else if (direction<0) pad_x=pad_x>=LEFT+4u ? pad_x-4u : LEFT;
    else if (direction>0) pad_x+=4u;
    clamp_pad();
    if (!round_live) attach();
    if (!round_live && (key==' ' || key==KC_RET || (mode && button))) {
        ball_live=round_live=1; hud_changed(); sound_event(SND_LAUNCH);
    }
    if(laser_cooldown) --laser_cooldown;
    if(effect==5u && !laser_cooldown && !shot_live[0] && !shot_live[1] &&
       (key==' ' || key==KC_RET || (mode && mouse_buttons&0x80u))) {
        shot_live[0]=shot_live[1]=1; shot_x[0]=pad_x+2u; shot_x[1]=pad_x+pad_width-3u;
        shot_y[0]=shot_y[1]=PAD_Y-4u; laser_cooldown=8; sound_event(SND_LAUNCH);
    }
}
void game_shutdown(void)
{
    sound_stop(); timing_close(); mouse_close(); dhgr_text_restore();
    if (!prodos_video_release()) {
        a2_home(); puts_apple2("/RAM RESTORE FAILED\r");
    }
}
/* Frame boundary exported for tests without changing production gameplay. */
void game_tick(void)
{
    unsigned char key;
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
    if (key==KC_ESC) { quitting=1; return; }
    mouse_poll(); button=(mouse_buttons&0x80u) && !mouse_old;
    mouse_old=mouse_buttons&0x80u;
    if (state!=1u) {
        if(key=='H') { save_status=0; record_table(); return; }
        if (state==0u && key>='1' && key<='3') {
            difficulty=key-'1'; title(); return;
        }
        if (key==' ' || key==KC_RET || key=='M' || key=='K' || button) {
            mode=(key!='K') && mouse_slot;
            start();
        } else { sound_tick(); a2_frame_wait(); }
        return;
    }
    input(key);
    if (!paused) {
        advance_balls();
        if(state==1u && !refresh) {
            if(!ball_live && round_live) {
                if(extra_ball[2]) ball_swap(0);
                else if(extra_ball[11]) ball_swap(1);
                else {
                    sound_event(SND_LOST);
                    if(--lives) reset_ball();
                    else { state=2; update_best(); ending(); }
                }
            }
            if(state==1u) { lasers_step(); if(!refresh && state==1u) { drop(); effects_tick(); } }
        }
    }
    if (state==1u) {
        if (refresh) load_level();
        else render();
        ++frames;
    }
}
int main(void)
{
    a2_text(); a2_home();
    memset(flash_slot,255,4);
    records_load();
    if (!dhgr_init()) {
        puts_apple2("REQUIRES IIE ENHANCED / IIC 128K.\rPRESS A KEY TO RETURN TO PRODOS.\r");
        apple2_getkey(); return 0;
    }
    prodos_video_claim();
    dhgr_draw_page(1); fast_reset(); dhgr_draw_page(2); fast_reset();
    mouse_init(); timing_init(); a2_frame_set_delay(40);
    mode=mouse_slot!=0; title();
    while (!quitting) game_tick();
    return 0;
}
