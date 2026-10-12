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
        bne     :+
        jmp     next_file
:      lda     dest
        ora     dest+1
        bne     :+
        jmp     done
:      jsr     get
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
        sta     (dest),y
        inc     dest
        bne     :+
        inc     dest+1
:       lda     remain
        bne     :+
        dec     remain+1
:       dec     remain
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
        sta     (dest),y
        iny
        dex
        bne     copy
        ; Indexed reads preserve overlapping LZ matches, including page
        ; crossings. Advance output and remaining length once per token.
        tya
        clc
        adc     dest
        sta     dest
        bcc     :+
        inc     dest+1
:       sty     length
        sec
        lda     remain
        sbc     length
        sta     remain
        bcs     :+
        dec     remain+1
:       ldy     #0
check:
        lda     remain
        ora     remain+1
        beq     :+
        jmp     token
:      jmp     block
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
command: .byte "BLOAD WILDPAK"
number: .byte "1,A$2000", 0

        .include "exit.asm"
        .include "dos.asm"
