; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; sysreloc.inc — ca65 macros for a ProDOS SYS relocator at $2000 (65C02).
;
; A game's src/startup.s is linked with PRODOS_SYS_CFG at $2000, carries its
; images (.incbin) after the code and moves them into place before jmp $6000:
;
;     .setcpu "65C02"
;     .include "sysreloc.inc"
;     .segment "CODE"
;             sysreloc_prologue
;             sysreloc_copy_pages boot, $1700, >bsize + 1
;             sysreloc_copy_down payload, $6000, size
;             jmp $6000
;     payload: .incbin "game.bin"
;     size = *-payload
;
; Zero page: $06/$07 source, $08/$09 destination, $0A/$0B length (free
; under ProDOS at that point). Every macro clobbers A/X/Y and flags.
;
; sysreloc_prologue          cld, main RAM read/write, 80STORE off, S = $FF
; sysreloc_copy_bytes s,d,n  1..255 bytes (n constant), X-indexed, from the end
; sysreloc_copy_pages s,d,p  p whole pages forwards (p = 1..255; 0 = 256);
;                            `stz $08` when d's low byte is a constant 0
; sysreloc_copy_pages_aux    the same into AUX: sei, RAMWRT aux .. RAMWRT
;                            main; I stays SET (the caller re-enables it, or
;                            not: the game starts with I set). The destination
;                            low byte is always loaded (lda/sta).
; sysreloc_copy_down s,d,n   n bytes (1..$FFFF) downwards from the last byte:
;                            safe when d > s overlap (all bytes move in
;                            descending address order); inline
; sysreloc_down_args s,d,n   + jsr to sysreloc_down_sub: the same as a
; sysreloc_down_sub name     subroutine `name` (default sysreloc_down), for
;                            several downward copies in one startup
;
; Option (ABI.md, "Speed/RAM options"):
;
; SYSRELOC_DOWN_FAST = 1  Downward copy as the len&$FF tail then whole pages,
;   dey/lda (),y/sta (),y/cpy #0/bne: ~18 cycles per byte instead of ~53
;   (a 24 KB game: ~0.85 s less at 1 MHz), 40 bytes inline instead of 60;
;   the order stays strictly descending, so overlap stays safe. The length
;   must stay below $8000 (assembly-time assert when it is constant at the
;   end of the source). $0A/$0B are not used; down_args leaves the page
;   count in X and the tail length in Y for the subroutine.
;   Undefined: the byte-at-a-time 16-bit counter loop (34 bytes) of the
;   historic startups.

.ifndef SYSRELOC_DOWN_FAST
SYSRELOC_DOWN_FAST = 0
.endif

.macro sysreloc_prologue
        cld
        sta $C002               ; RAMRD main
        sta $C004               ; RAMWRT main
        sta $C000               ; 80STORE off
        ldx #$FF
        txs
.endmacro

; Up to 255 bytes, highest first (X = n .. 1).
.macro sysreloc_copy_bytes src, dst, n
.local loop
        ldx #(n)
loop:   lda src-1,x
        sta dst-1,x
        dex
        bne loop
.endmacro

; Pointers of the forward page copy; `stz $08` for a page-aligned constant.
.macro sysreloc__page_ptrs src, dst, keep_lo
        lda #<(src)
        sta $06
        lda #>(src)
        sta $07
.if (keep_lo = 0) .and .const(dst)
.if <(dst) = 0
        stz $08
.else
        lda #<(dst)
        sta $08
.endif
.else
        lda #<(dst)
        sta $08
.endif
        lda #>(dst)
        sta $09
.endmacro

.macro sysreloc__page_loop
.local loop
loop:   lda ($06),y
        sta ($08),y
        iny
        bne loop
        inc $07
        inc $09
        dex
        bne loop
.endmacro

.macro sysreloc_copy_pages src, dst, pages
        sysreloc__page_ptrs src, dst, 0
        ldx #(pages)
        ldy #0
        sysreloc__page_loop
.endmacro

.macro sysreloc_copy_pages_aux src, dst, pages
        sysreloc__page_ptrs src, dst, 1
        ldx #(pages)
        ldy #0
        sei
        sta $C005               ; RAMWRT aux
        sysreloc__page_loop
        sta $C004               ; RAMWRT main (I stays set)
.endmacro

; Arguments of the downward copy.
.macro sysreloc_down_args src, dst, len
.if SYSRELOC_DOWN_FAST
        ; bases of the last (partial) page: offsets 0..len&$FF-1 above them
        lda #<(src)
        sta $06
        lda #>((src)+((len)&$FF00))
        sta $07
        lda #<(dst)
        sta $08
        lda #>((dst)+((len)&$FF00))
        sta $09
        ldx #>(len)             ; whole pages under the tail
        ldy #<(len)             ; tail bytes (Z set when none)
        .assert (len) < $8000, error, "sysreloc: SYSRELOC_DOWN_FAST copies less than $8000 bytes"
.else
        lda #<((src)+(len)-1)
        sta $06
        lda #>((src)+(len)-1)
        sta $07
        lda #<((dst)+(len)-1)
        sta $08
        lda #>((dst)+(len)-1)
        sta $09
        lda #<(len)
        sta $0A
        lda #>(len)
        sta $0B
.endif
.endmacro

; The loop proper, after sysreloc_down_args (Y = 0 for the default form).
.macro sysreloc__down_loop
.local byte, next, done, loop, s1, s2, s3
.if SYSRELOC_DOWN_FAST
        beq next                ; no tail: whole pages only
byte:   dey
        lda ($06),y
        sta ($08),y
        cpy #0
        bne byte
next:   dex
        bmi done                ; X was 0: every page moved
        dec $07
        dec $09
        bra byte                ; Y = 0: 256 bytes, $FF first
done:
.else
loop:   lda ($06),y
        sta ($08),y
        lda $06
        bne s1
        dec $07
s1:     dec $06
        lda $08
        bne s2
        dec $09
s2:     dec $08
        lda $0A
        bne s3
        dec $0B
s3:     dec $0A
        lda $0A
        ora $0B
        bne loop
.endif
.endmacro

.macro sysreloc_copy_down src, dst, len
        sysreloc_down_args src, dst, len
.if .not SYSRELOC_DOWN_FAST
        ldy #0
.endif
        sysreloc__down_loop
.endmacro

; The subroutine form: sysreloc_down_args ..., then jsr name.
.macro sysreloc_down_sub name
.ifblank name
sysreloc_down:
.else
name:
.endif
.if SYSRELOC_DOWN_FAST
        cpy #0                  ; Z from Y, whatever ran after down_args
.else
        ldy #0
.endif
        sysreloc__down_loop
        rts
.endmacro
