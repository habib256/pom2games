/* Real 48K campaign, using simulated AppleMouse polling results only.
 * Never changes ball state, lives, collision data or level progression.
 * GPL-3.0. The test supplies a labels header for the linked game binary. */
#include <stdio.h>
#include <stdlib.h>
#include "a2run.h"
#include "game_labels.h"

static int word(unsigned address) { return (int16_t)(ram[address] | ram[address+1]<<8); }
static int clamp(int v,int lo,int hi) { return v<lo?lo:v>hi?hi:v; }
static int reflect(int p) {
    p=(p-32)%3936; if(p<0)p+=3936;
    return 32+(p>1968?3936-p:p);
}
static int opening_center(unsigned level,int slot) {
    if(slot<0 || slot>=24)return 64;
    unsigned code=ram[LEVEL_MAPS+level*24+slot];
    static const int widths[4]={48,40,44,36};
    int width=widths[(code>>4)&3];
    if(!code)return 64;
    if(code&128) {
        int phase=(ram[DOOR_PHASE]+(code&15)*2)&31;
        return 8+4*(phase<16?phase:31-phase)+width/2;
    }
    return code&64?127-width/2:width/2;
}
static int next_slot(unsigned level,int camera) {
    int i=camera>>7;
    while(i<ram[LEVEL_SLOTS] && !ram[LEVEL_MAPS+level*24+i])i++;
    return i;
}
static void mouse_at(int x,int y) {
    /* Each world position has at least one entry in the firmware maps. */
    for(int i=0;i<140;i++)if(8+i*112/139>=x){ram[MOUSE_X]=i;break;}
    for(int i=0;i<192;i++)if(12+i*104/191>=y){ram[MOUSE_Y]=i;break;}
}
int main(int argc,char **argv) {
    if(argc!=3)return 2;
    char *boot[]={"a2run","--roms",argv[2],"--disk",argv[1],"wait:1100"};
    if(a2run_main(6,boot))return 3;
    uint64_t stop=cpu.cycles+1000000;
    while(cpu.pc!=FRAME_MARK && cpu.cycles<stop)cpu_step(&cpu);
    if(cpu.pc!=FRAME_MARK)return 4;
    ram[MOUSE_ENABLED]=1;
    ram[MOUSE_POLL]=0x60; /* Substitute firmware only; all game code runs. */
    int previous=-1,previous_progress=-1;
    uint64_t started=cpu.cycles;
    for(unsigned tick=0;tick<150000;tick++) {
        unsigned level=ram[LEVEL]; int camera=word(CAMERA_Z);
        if((int)level!=previous) {
            printf("level %u length %d tick %u lives %u\n",level+1,word(LEVEL_LENGTH),tick,ram[LIVES]);
            fflush(stdout);previous=level;previous_progress=-1;
        }
        if(ram[LIVES]!=4) {printf("lost life: level%u cam%d bx%d vx%d ticks%u\n",level+1,camera,word(BALL_X),word(VEL_X),tick);return 5;}
        if(ram[WON] && level==4) {
            printf("five levels cleared, lives %u, %u ticks, %.1f simulated seconds\n",ram[LIVES],tick,(cpu.cycles-started)/A2RUN_CPU_HZ);
            return 0;
        }
        if(camera/512!=previous_progress) {previous_progress=camera/512;printf("  camera %d ball %d\n",camera,word(BALL_Z));fflush(stdout);}
        int slot=next_slot(level,camera), plane=(slot+1)*128;
        int gap=slot<ram[LEVEL_SLOTS]?opening_center(level,slot):64;
        int px=gap,py=64;
        unsigned button=0;
        if(ram[WON] || !ram[LAUNCHED]) {
            if(ram[WON])px=opening_center(level+1,0);
            button=ram[MOUSE_BUTTONS]&128?0:128;
        } else if((int8_t)ram[VEL_Z]<0) {
            int distance=word(BALL_Z)-camera-6;
            int vx=word(VEL_X),vy=word(VEL_Y);
            int x=reflect(word(BALL_X)+vx*distance);
            int y=reflect(word(BALL_Y)+vy*distance);
            int travel=plane-camera-6;
            if(slot>=ram[LEVEL_SLOTS])travel=word(LEVEL_LENGTH)-camera-8;
            if(travel<8)travel=8;
            int wantx=clamp((gap*16-x)/travel,-8,8);
            int wanty=clamp((64*16-y)/travel,-8,8);
            px=clamp((x-32*clamp(wantx-vx,-4,4))/16,8,120);
            py=clamp((y-32*clamp(wanty-vy,-4,4))/16,12,116);
        } else {
            /* Advance behind the ball after it has cleared the next wall. */
            button=slot>=ram[LEVEL_SLOTS] || word(BALL_Z)>plane+8?128:0;
        }
        mouse_at(clamp(px,8,120),clamp(py,12,116));
        ram[MOUSE_BUTTONS]=button;
        cpu_step(&cpu);
        stop=cpu.cycles+500000;
        while(cpu.pc!=FRAME_MARK && cpu.cycles<stop)cpu_step(&cpu);
        if(cpu.pc!=FRAME_MARK){printf("stuck PC %04x\n",cpu.pc);return 6;}
    }
    printf("timeout level%u cam%d ball%d vx%d\n",ram[LEVEL]+1,word(CAMERA_Z),word(BALL_Z),word(VEL_X));return 7;
}
