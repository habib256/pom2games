/* Complete campaign using the real 48K machine, steering only the paddle.
 * No edits to the ball, grid, lives, score or progression. GPL-3.0.
 * Built on dev/tools/a2run as a library (a2run.h). */
#include <stdio.h>
#include <stdlib.h>
#include "a2run.h"

int main(int argc, char **argv) {
    if (argc != 12) return 2;
    unsigned loop = strtoul(argv[3],0,16);
    unsigned state = strtoul(argv[4],0,16);
    unsigned bx = strtoul(argv[5],0,16), by = strtoul(argv[6],0,16);
    unsigned px = strtoul(argv[7],0,16), width = strtoul(argv[8],0,16);
    unsigned live = strtoul(argv[9],0,16), level = strtoul(argv[10],0,16);
    unsigned dy = strtoul(argv[11],0,16);
    char boundary[64];
    snprintf(boundary,sizeof boundary,"until:%04X:3000",loop);
    char *boot[] = {"a2run","--roms",argv[2],"--disk",argv[1],"wait:1100","key:1","key: ",boundary};
    if (a2run_main(9,boot)) return 3;
    unsigned prev_level = 255;
    uint64_t start = cpu.cycles;
    for (unsigned f=0;f<800000;f++) {
        uint64_t deadline = cpu.cycles+12000000;
        while (cpu.pc != loop && ram[state]==1 && cpu.cycles < deadline) cpu_step(&cpu);
        if (ram[state]!=1) {printf("finish state=%u level=%u updates=%u seconds=%.1f\n",ram[state],ram[level],f,(cpu.cycles-start)/A2RUN_CPU_HZ); return ram[state]==3?0:1;}
        if (cpu.pc!=loop) {printf("stuck at %04X level %u live%u\n",cpu.pc,ram[level],ram[live]);return 4;}
        if (ram[level]!=prev_level) {prev_level=ram[level]; printf("sector %u update %u\n",prev_level+1,f); fflush(stdout);}
        if (ram[live] && (ram[bx]<2 || ram[bx]>248 || ram[by]<18 || ram[by]>179 || ram[dy]>1)) return 6;
        /* Stay inside the edges so <=5 horizontal substeps cannot miss.
         * Vary the impact zone to escape repeating trajectories. */
        static const unsigned zones[4]={1,2,5,6};
        unsigned zone=zones[((f/113)*3+ram[level]*5)%4];
        int target=(int)ram[bx]+1-ram[width]*(zone*2+1)/16;
        if (target<2) target=2;
        if (target>251-ram[width]) target=251-ram[width];
        ram[px]=target;
        if (!ram[live]) kbd_latch=0xA0;
        cpu_step(&cpu);
    }
    printf("timeout: level=%u remaining=%u live=%u ball=%u,%u dy=%u state=%u\n",ram[level]+1,ram[level+1],ram[live],ram[bx],ram[by],ram[dy],ram[state]); return 5;
}
