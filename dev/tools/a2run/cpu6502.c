/* cpu6502.c -- NMOS 6502 core, see cpu6502.h. */
#include "cpu6502.h"

#define RD(a)    c->read(c->ctx, (uint16_t)(a))
#define WR(a, v) c->write(c->ctx, (uint16_t)(a), (uint8_t)(v))

static void push(Cpu *c, uint8_t v) { WR(0x100 | c->s, v); c->s--; }
static uint8_t pull(Cpu *c) { c->s++; return RD(0x100 | c->s); }
static uint16_t rd16(Cpu *c, uint16_t a) { return RD(a) | (RD((uint16_t)(a + 1)) << 8); }
static uint16_t fetch16(Cpu *c) { uint16_t v = rd16(c, c->pc); c->pc += 2; return v; }

static void nz(Cpu *c, uint8_t v)
{
    c->p = (c->p & ~(FN | FZ)) | (v & FN) | (v ? 0 : FZ);
}

void cpu_reset(Cpu *c)
{
    c->s = 0xFD;
    c->p = FU | FI;
    c->pc = rd16(c, 0xFFFC);
    c->cycles += 7;
}

static int extra;   /* page-cross penalty of the current instruction */

static uint16_t a_zp(Cpu *c)  { return RD(c->pc++); }
static uint16_t a_zpx(Cpu *c) { return (uint8_t)(RD(c->pc++) + c->x); }
static uint16_t a_zpy(Cpu *c) { return (uint8_t)(RD(c->pc++) + c->y); }
static uint16_t a_abs(Cpu *c) { return fetch16(c); }
static uint16_t a_abx(Cpu *c, int pen)
{
    uint16_t b = fetch16(c), r = b + c->x;
    if (pen && (b ^ r) & 0xFF00) extra = 1;
    return r;
}
static uint16_t a_aby(Cpu *c, int pen)
{
    uint16_t b = fetch16(c), r = b + c->y;
    if (pen && (b ^ r) & 0xFF00) extra = 1;
    return r;
}
static uint16_t a_izx(Cpu *c)
{
    uint8_t z = RD(c->pc++) + c->x;
    return RD(z) | (RD((uint8_t)(z + 1)) << 8);
}
static uint16_t a_izy(Cpu *c, int pen)
{
    uint8_t z = RD(c->pc++);
    uint16_t b = RD(z) | (RD((uint8_t)(z + 1)) << 8), r = b + c->y;
    if (pen && (b ^ r) & 0xFF00) extra = 1;
    return r;
}

static void adc(Cpu *c, uint8_t m)
{
    unsigned cin = c->p & FC;
    unsigned bin = c->a + m + cin;
    c->p &= ~(FV | FC | FZ | FN);
    if (!(bin & 0xFF)) c->p |= FZ;
    if (c->p & FD) {                /* NMOS: N, V from the half-adjusted sum */
        int lo = (c->a & 0x0F) + (m & 0x0F) + (int)cin;
        if (lo >= 0x0A) lo = ((lo + 0x06) & 0x0F) + 0x10;
        int r = (c->a & 0xF0) + (m & 0xF0) + lo;
        if (r & 0x80) c->p |= FN;
        if (~(c->a ^ m) & (c->a ^ r) & 0x80) c->p |= FV;
        if (r >= 0xA0) r += 0x60;
        if (r >= 0x100) c->p |= FC;
        c->a = (uint8_t)r;
    } else {
        if (bin & 0x80) c->p |= FN;
        if (~(c->a ^ m) & (c->a ^ bin) & 0x80) c->p |= FV;
        if (bin > 0xFF) c->p |= FC;
        c->a = (uint8_t)bin;
    }
}

static void sbc(Cpu *c, uint8_t m)
{
    int cin = c->p & FC;
    unsigned r = c->a - m - (cin ? 0 : 1);
    uint8_t rb = (uint8_t)r;
    c->p &= ~(FV | FC);
    if ((c->a ^ m) & (c->a ^ rb) & 0x80) c->p |= FV;
    if (r < 0x100) c->p |= FC;
    nz(c, rb);                      /* NMOS: flags from the binary result */
    if (c->p & FD) {
        int lo = (c->a & 0x0F) - (m & 0x0F) + cin - 1;
        if (lo < 0) lo = ((lo - 0x06) & 0x0F) - 0x10;
        int d = (c->a & 0xF0) - (m & 0xF0) + lo;
        if (d < 0) d -= 0x60;
        c->a = (uint8_t)d;
    } else {
        c->a = rb;
    }
}

static void cmp(Cpu *c, uint8_t r, uint8_t m)
{
    uint8_t d = r - m;
    c->p = (c->p & ~FC) | (r >= m ? FC : 0);
    nz(c, d);
}

static uint8_t asl(Cpu *c, uint8_t v) { c->p = (c->p & ~FC) | (v >> 7); v <<= 1; nz(c, v); return v; }
static uint8_t lsr(Cpu *c, uint8_t v) { c->p = (c->p & ~FC) | (v & 1); v >>= 1; nz(c, v); return v; }
static uint8_t rol(Cpu *c, uint8_t v)
{
    uint8_t ci = c->p & FC;
    c->p = (c->p & ~FC) | (v >> 7); v = (uint8_t)(v << 1) | ci; nz(c, v); return v;
}
static uint8_t ror(Cpu *c, uint8_t v)
{
    uint8_t ci = (c->p & FC) << 7;
    c->p = (c->p & ~FC) | (v & 1); v = (v >> 1) | ci; nz(c, v); return v;
}

static int branch(Cpu *c, int cond)
{
    int8_t off = (int8_t)RD(c->pc++);
    if (!cond) return 2;
    uint16_t t = c->pc + off;
    int cyc = ((t ^ c->pc) & 0xFF00) ? 4 : 3;
    c->pc = t;
    return cyc;
}

/* Read-modify-write through a callback on memory. */
#define RMW(addr, fn) do { uint16_t ea = (addr); uint8_t v = RD(ea); WR(ea, v); WR(ea, fn(c, v)); } while (0)
static uint8_t inc_(Cpu *c, uint8_t v) { v++; nz(c, v); return v; }
static uint8_t dec_(Cpu *c, uint8_t v) { v--; nz(c, v); return v; }

int cpu_step(Cpu *c)
{
    uint8_t op = RD(c->pc++);
    int cyc;
    extra = 0;

    switch (op) {
    /* --- loads / stores --- */
    case 0xA9: c->a = RD(c->pc++); nz(c, c->a); cyc = 2; break;
    case 0xA5: c->a = RD(a_zp(c)); nz(c, c->a); cyc = 3; break;
    case 0xB5: c->a = RD(a_zpx(c)); nz(c, c->a); cyc = 4; break;
    case 0xAD: c->a = RD(a_abs(c)); nz(c, c->a); cyc = 4; break;
    case 0xBD: c->a = RD(a_abx(c, 1)); nz(c, c->a); cyc = 4; break;
    case 0xB9: c->a = RD(a_aby(c, 1)); nz(c, c->a); cyc = 4; break;
    case 0xA1: c->a = RD(a_izx(c)); nz(c, c->a); cyc = 6; break;
    case 0xB1: c->a = RD(a_izy(c, 1)); nz(c, c->a); cyc = 5; break;
    case 0xA2: c->x = RD(c->pc++); nz(c, c->x); cyc = 2; break;
    case 0xA6: c->x = RD(a_zp(c)); nz(c, c->x); cyc = 3; break;
    case 0xB6: c->x = RD(a_zpy(c)); nz(c, c->x); cyc = 4; break;
    case 0xAE: c->x = RD(a_abs(c)); nz(c, c->x); cyc = 4; break;
    case 0xBE: c->x = RD(a_aby(c, 1)); nz(c, c->x); cyc = 4; break;
    case 0xA0: c->y = RD(c->pc++); nz(c, c->y); cyc = 2; break;
    case 0xA4: c->y = RD(a_zp(c)); nz(c, c->y); cyc = 3; break;
    case 0xB4: c->y = RD(a_zpx(c)); nz(c, c->y); cyc = 4; break;
    case 0xAC: c->y = RD(a_abs(c)); nz(c, c->y); cyc = 4; break;
    case 0xBC: c->y = RD(a_abx(c, 1)); nz(c, c->y); cyc = 4; break;
    case 0x85: WR(a_zp(c), c->a); cyc = 3; break;
    case 0x95: WR(a_zpx(c), c->a); cyc = 4; break;
    case 0x8D: WR(a_abs(c), c->a); cyc = 4; break;
    case 0x9D: WR(a_abx(c, 0), c->a); cyc = 5; break;
    case 0x99: WR(a_aby(c, 0), c->a); cyc = 5; break;
    case 0x81: WR(a_izx(c), c->a); cyc = 6; break;
    case 0x91: WR(a_izy(c, 0), c->a); cyc = 6; break;
    case 0x86: WR(a_zp(c), c->x); cyc = 3; break;
    case 0x96: WR(a_zpy(c), c->x); cyc = 4; break;
    case 0x8E: WR(a_abs(c), c->x); cyc = 4; break;
    case 0x84: WR(a_zp(c), c->y); cyc = 3; break;
    case 0x94: WR(a_zpx(c), c->y); cyc = 4; break;
    case 0x8C: WR(a_abs(c), c->y); cyc = 4; break;

    /* --- transfers / stack --- */
    case 0xAA: c->x = c->a; nz(c, c->x); cyc = 2; break;
    case 0xA8: c->y = c->a; nz(c, c->y); cyc = 2; break;
    case 0x8A: c->a = c->x; nz(c, c->a); cyc = 2; break;
    case 0x98: c->a = c->y; nz(c, c->a); cyc = 2; break;
    case 0xBA: c->x = c->s; nz(c, c->x); cyc = 2; break;
    case 0x9A: c->s = c->x; cyc = 2; break;
    case 0x48: push(c, c->a); cyc = 3; break;
    case 0x08: push(c, c->p | FB | FU); cyc = 3; break;
    case 0x68: c->a = pull(c); nz(c, c->a); cyc = 4; break;
    case 0x28: c->p = (pull(c) & ~FB) | FU; cyc = 4; break;

    /* --- logic / arithmetic --- */
#define ALU(base, fn)                                                        \
    case base + 0x09: fn(RD(c->pc++)); cyc = 2; break;                       \
    case base + 0x05: fn(RD(a_zp(c))); cyc = 3; break;                       \
    case base + 0x15: fn(RD(a_zpx(c))); cyc = 4; break;                      \
    case base + 0x0D: fn(RD(a_abs(c))); cyc = 4; break;                      \
    case base + 0x1D: fn(RD(a_abx(c, 1))); cyc = 4; break;                   \
    case base + 0x19: fn(RD(a_aby(c, 1))); cyc = 4; break;                   \
    case base + 0x01: fn(RD(a_izx(c))); cyc = 6; break;                      \
    case base + 0x11: fn(RD(a_izy(c, 1))); cyc = 5; break;
#define F_ORA(v) (c->a |= (v), nz(c, c->a))
#define F_AND(v) (c->a &= (v), nz(c, c->a))
#define F_EOR(v) (c->a ^= (v), nz(c, c->a))
#define F_ADC(v) adc(c, (v))
#define F_SBC(v) sbc(c, (v))
#define F_CMP(v) cmp(c, c->a, (v))
    ALU(0x00, F_ORA)
    ALU(0x20, F_AND)
    ALU(0x40, F_EOR)
    ALU(0x60, F_ADC)
    ALU(0xC0, F_CMP)
    ALU(0xE0, F_SBC)

    case 0xE0: cmp(c, c->x, RD(c->pc++)); cyc = 2; break;
    case 0xE4: cmp(c, c->x, RD(a_zp(c))); cyc = 3; break;
    case 0xEC: cmp(c, c->x, RD(a_abs(c))); cyc = 4; break;
    case 0xC0: cmp(c, c->y, RD(c->pc++)); cyc = 2; break;
    case 0xC4: cmp(c, c->y, RD(a_zp(c))); cyc = 3; break;
    case 0xCC: cmp(c, c->y, RD(a_abs(c))); cyc = 4; break;

    case 0x24: case 0x2C: {
        uint8_t m = RD(op == 0x24 ? a_zp(c) : a_abs(c));
        c->p = (c->p & ~(FN | FV | FZ)) | (m & (FN | FV)) | ((m & c->a) ? 0 : FZ);
        cyc = op == 0x24 ? 3 : 4;
        break;
    }

    /* --- shifts, inc/dec --- */
#define SHIFT(base, fn)                                                      \
    case base + 0x0A: c->a = fn(c, c->a); cyc = 2; break;                    \
    case base + 0x06: RMW(a_zp(c), fn); cyc = 5; break;                      \
    case base + 0x16: RMW(a_zpx(c), fn); cyc = 6; break;                     \
    case base + 0x0E: RMW(a_abs(c), fn); cyc = 6; break;                     \
    case base + 0x1E: RMW(a_abx(c, 0), fn); cyc = 7; break;
    SHIFT(0x00, asl)
    SHIFT(0x20, rol)
    SHIFT(0x40, lsr)
    SHIFT(0x60, ror)

    case 0xE6: RMW(a_zp(c), inc_); cyc = 5; break;
    case 0xF6: RMW(a_zpx(c), inc_); cyc = 6; break;
    case 0xEE: RMW(a_abs(c), inc_); cyc = 6; break;
    case 0xFE: RMW(a_abx(c, 0), inc_); cyc = 7; break;
    case 0xC6: RMW(a_zp(c), dec_); cyc = 5; break;
    case 0xD6: RMW(a_zpx(c), dec_); cyc = 6; break;
    case 0xCE: RMW(a_abs(c), dec_); cyc = 6; break;
    case 0xDE: RMW(a_abx(c, 0), dec_); cyc = 7; break;
    case 0xE8: c->x++; nz(c, c->x); cyc = 2; break;
    case 0xC8: c->y++; nz(c, c->y); cyc = 2; break;
    case 0xCA: c->x--; nz(c, c->x); cyc = 2; break;
    case 0x88: c->y--; nz(c, c->y); cyc = 2; break;

    /* --- flags --- */
    case 0x18: c->p &= ~FC; cyc = 2; break;
    case 0x38: c->p |= FC; cyc = 2; break;
    case 0x58: c->p &= ~FI; cyc = 2; break;
    case 0x78: c->p |= FI; cyc = 2; break;
    case 0xB8: c->p &= ~FV; cyc = 2; break;
    case 0xD8: c->p &= ~FD; cyc = 2; break;
    case 0xF8: c->p |= FD; cyc = 2; break;

    /* --- control flow --- */
    case 0x10: cyc = branch(c, !(c->p & FN)); break;
    case 0x30: cyc = branch(c, c->p & FN); break;
    case 0x50: cyc = branch(c, !(c->p & FV)); break;
    case 0x70: cyc = branch(c, c->p & FV); break;
    case 0x90: cyc = branch(c, !(c->p & FC)); break;
    case 0xB0: cyc = branch(c, c->p & FC); break;
    case 0xD0: cyc = branch(c, !(c->p & FZ)); break;
    case 0xF0: cyc = branch(c, c->p & FZ); break;
    case 0x4C: c->pc = fetch16(c); cyc = 3; break;
    case 0x6C: {                                   /* NMOS page-wrap bug */
        uint16_t p = fetch16(c);
        c->pc = RD(p) | (RD((p & 0xFF00) | ((p + 1) & 0xFF)) << 8);
        cyc = 5;
        break;
    }
    case 0x20: {
        uint16_t t = fetch16(c);
        uint16_t r = c->pc - 1;
        push(c, r >> 8); push(c, r & 0xFF);
        c->pc = t; cyc = 6;
        break;
    }
    case 0x60: { uint16_t lo = pull(c); uint16_t hi = pull(c); c->pc = ((hi << 8) | lo) + 1; cyc = 6; break; }
    case 0x40: {
        c->p = (pull(c) & ~FB) | FU;
        uint16_t lo = pull(c); uint16_t hi = pull(c);
        c->pc = (hi << 8) | lo; cyc = 6;
        break;
    }
    case 0x00: {
        uint16_t r = c->pc + 1;
        push(c, r >> 8); push(c, r & 0xFF);
        push(c, c->p | FB | FU);
        c->p |= FI;
        c->pc = rd16(c, 0xFFFE); cyc = 7;
        break;
    }
    case 0xEA: cyc = 2; break;

    default: {
        /* undocumented: NOP of the standard length for its column */
        int col = op & 0x1F;
        int n = (col == 0x0C || col == 0x0E || col == 0x0F || col == 0x19 ||
                 col == 0x1B || col == 0x1C || col == 0x1D || col == 0x1E ||
                 col == 0x1F) ? 3 : (col == 0x1A || col == 0x0A || col == 0x12 ||
                 col == 0x02) ? 1 : 2;
        c->pc += n - 1;
        cyc = 2;
        break;
    }
    }
    cyc += extra;
    c->cycles += cyc;
    return cyc;
}
