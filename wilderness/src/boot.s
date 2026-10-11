; Transient DOS boot loader. Packed input uses the future HGR page at $2000;
; output goes directly to its linked address. The game replaces this loader
; with its ordinary $5800 overlays after all resident memory is restored.
        .include "apple2.inc"
.segment "ZEROPAGE"
source: .res 2
dest:   .res 2
match:  .res 2
remain: .res 2
flags:  .res 1
bits:   .res 1
offset: .res 1
length: .res 1
.segment "CODE"
start:
        APPLE2_PREAMBLE
        jsr     apple2_zp_save
load:
        jsr     dos_cmd_new
        lda     #<command
        ldy     #>command
        jsr     dos_cmd_add
        jsr     dos_cmd_run
        lda     #0
        sta     source
        lda     #$20
        sta     source+1
block:
        jsr     get
        sta     dest
        jsr     get
        sta     dest+1
        and     dest
        cmp     #$FF
        beq     next_file
        lda     dest
        ora     dest+1
        beq     done
        jsr     get
        sta     remain
        jsr     get
        sta     remain+1
        lda     #0
        sta     bits
token:
        lda     bits
        bne     :+
        jsr     get
        sta     flags
        lda     #8
        sta     bits
:       dec     bits
        lsr     flags
        bcs     copy_match
        jsr     get
        jsr     put
        jmp     check
copy_match:
        jsr     get
        sta     offset
        sec
        lda     dest
        sbc     offset
        sta     match
        php                     ; preserve the low-byte borrow while unpacking
        jsr     get
        sta     length
        lsr
        lsr
        lsr
        lsr
        sta     offset
        plp
        lda     dest+1
        sbc     offset
        sta     match+1
        lda     length
        and     #15
        clc
        adc     #3
        cmp     #18
        bne     :+
        jsr     get
        clc
        adc     #18
:       tax
copy:
        lda     (match),y
        jsr     put
        inc     match
        bne     :+
        inc     match+1
:       dex
        bne     copy
check:
        lda     remain
        ora     remain+1
        bne     token
        jmp     block
next_file:
        inc     number
        jmp     load
done:
        jsr     exit_restore    ; give the game a clean DOS ZP / RESET snapshot
        jmp     $6000

get:
        ldy     #0
        lda     (source),y
        inc     source
        bne     :+
        inc     source+1
:       rts
put:
        sta     (dest),y
        inc     dest
        bne     :+
        inc     dest+1
:       lda     remain
        bne     :+
        dec     remain+1
:       dec     remain
        rts

command: .byte "BLOAD WILDPAK"
number: .byte "1,A$2000", 0

        .include "exit.asm"
        .include "dos.asm"
