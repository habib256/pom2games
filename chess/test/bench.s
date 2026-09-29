; bench.s -- 6502 side of the engine bench (see bench.cpp).
; Linked first so bench_entry sits at $6000: the host patches the JSR operand,
; points the soft-reset vector here, presses RESET, and runs until bench_done.
.exportzp tmp, tmp2
.export bench_entry, bench_done, bench_a, bench_p

.segment "ZEROPAGE"
tmp:        .res 1
tmp2:       .res 1

.segment "BSS"
bench_a:    .res 1          ; A returned by the routine
bench_p:    .res 1          ; flags returned by the routine (bit 0 = carry)

.segment "CODE"
bench_entry:
        JSR $FFFF           ; operand patched by the host
        STA bench_a
        PHP
        PLA
        STA bench_p
bench_done:
        JMP bench_done
