/* cpu6502.h -- NMOS 6502 core (documented opcodes, decimal mode).
 *
 * The host supplies the bus through two callbacks. Unknown opcodes execute
 * as NOPs of the usual length so a stray jump into data does not wedge the
 * emulator. Cycle counts are the documented ones, page-cross penalties
 * included; that is what the paddle timers and the delay loops rely on.
 */
#ifndef CPU6502_H
#define CPU6502_H

#include <stdint.h>

typedef struct Cpu {
    uint16_t pc;
    uint8_t a, x, y, s, p;
    uint64_t cycles;
    uint8_t (*read)(void *ctx, uint16_t addr);
    void (*write)(void *ctx, uint16_t addr, uint8_t v);
    void *ctx;
} Cpu;

enum { FC = 0x01, FZ = 0x02, FI = 0x04, FD = 0x08, FB = 0x10, FU = 0x20, FV = 0x40, FN = 0x80 };

void cpu_reset(Cpu *c);
int  cpu_step(Cpu *c);          /* one instruction, returns its cycles */

#endif
