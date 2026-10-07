/* a2run.h -- a2run as a library: boot a disk with a2run_main(), then step the
 * machine yourself. Build with -DA2RUN_LIB so a2run.c keeps no main(). */
#ifndef A2RUN_H
#define A2RUN_H
#include <stdint.h>
#include "cpu6502.h"

#define A2RUN_CPU_HZ 1020484.0      /* average Apple II clock */
#define A2RUN_CYCLES_PER_FRAME 17030

extern uint8_t ram[0xC000];         /* main RAM, $0000-$BFFF */
extern Cpu cpu;                     /* cpu_step(&cpu) runs one instruction */
extern uint8_t kbd_latch;           /* $C000: bit 7 = key ready */

/* Parse [--roms DIR] [--wp] --disk X.dsk step..., boot and play the steps.
 * 0 on success; the machine state stays live for the caller. */
int a2run_main(int argc, char **argv);

#endif
