; VERHILLE Arnaud — GPL-3.0. Explicit auxiliary-video ownership for ProDOS 8.
; fastcall claim: A=policy (0 preserve, 1 discard); A=status, X=0 on return.
; release: A=1 success/0 failure, X=0. Main RAM/ZP, ROM visible, D=0.
; A/X/Y, flags,tmp1/tmp2 destroyed. No video changes; not reentrant/IRQ-safe.
.export _prodos_video_claim, _prodos_video_release
.import _prodos_format_ram
.importzp tmp1, tmp2
.bss
; 0=unclaimed, 1=claimed without /RAM, otherwise the /RAM unit ($x0).
ram_unit: .res 1
.code
_prodos_video_claim:
        cmp #2
        bcs bad_policy
        sta tmp1
        lda ram_unit
        beq discover
        cmp #1
        beq ok
        lda tmp1
        beq busy
ok:     lda #0
        tax
        rts
bad_policy:
        lda #2
        ldx #0
        rts
busy:   lda #1
        ldx #0
        rts
discover:
        ldy $BF31              ; count minus one, $FF means empty
        cpy #$FF
        beq no_ram
        cpy #14
        bcc scan
        lda #3                 ; malformed list: leave claim untouched
        ldx #0
        rts
scan:   lda $BF32,y
        and #$F0
        sta tmp2
        lsr
        lsr
        lsr
        tax
        lda $BF10,x
        bne next
        lda $BF11,x
        cmp #$FF
        bne next
        lda tmp1
        beq busy
        lda tmp2
        bne claim
        ; A zero unit cannot name /RAM; preserve the no-driver sentinel.
no_ram: lda #1
claim:  sta ram_unit
        jmp ok
next:   dey
        bpl scan
        bmi no_ram

_prodos_video_release:
        lda ram_unit
        beq released
        ldy #0
        sty ram_unit           ; release once, including failed FORMAT
        cmp #1
        beq released
        jmp _prodos_format_ram
released:
        lda #1
        ldx #0
        rts
