; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; txtpage.inc -- whole pages of text on the Apple screen, no COUT
; ============================================================================
; Shared by the launcher (ROGUE) and ROGUE.TMS (boot.inc). Needs ez_slot
; (ezcolor.inc) and EZ_DETECT_BOOT_SLOT for the '#' / '%' digits.
; ============================================================================

.segment "ZEROPAGE"
txt_ptr:        .res 2          ; record cursor (and vdp_patch's table cursor)
txt_dst:        .res 2          ; screen address (and a patched operand)

.segment "BSS"
txt_mode:       .res 1

.segment "CODE"

INV = $80                       ; row flag: inverse video

; ----------------------------------------------------------------------------
; txt_page -- A/Y = records `row, col, "TEXT", 0`, ended by $FF, written
; straight into text page 1 (no COUT: works with the game's zero page).
; Row bit 7 = inverse video. In the text, '#' prints the card's slot and
; '%' the boot drive's slot. Upper case, 40 columns.
; ----------------------------------------------------------------------------
txt_page:
        STA     txt_ptr
        STY     txt_ptr+1
@rec:   LDY     #0
        LDA     (txt_ptr),Y     ; row (+$80 = inverse)
        CMP     #$FF
        BEQ     @end
        PHA
        AND     #$7F
        JSR     txt_row         ; txt_dst = row base
        PLA
        AND     #$80
        EOR     #$80
        STA     txt_mode        ; $80 normal, $00 inverse
        INY
        LDA     (txt_ptr),Y     ; column
        CLC
        ADC     txt_dst
        STA     txt_dst
        ; skip the two header bytes
        CLC
        LDA     txt_ptr
        ADC     #2
        STA     txt_ptr
        BCC     @c
        INC     txt_ptr+1
@c:     LDY     #0
@ch:    LDA     (txt_ptr),Y
        BEQ     @eos
        CMP     #'#'
        BNE     @np
        LDA     ez_slot
        ORA     #'0'
@np:    CMP     #'%'
        BNE     @put
        LDA     EZ_DETECT_BOOT_SLOT
        LSR
        LSR
        LSR
        LSR
        ORA     #'0'
@put:   BIT     txt_mode
        BMI     @norm
        AND     #$3F            ; inverse: $00-$3F
        .byte   $2C             ; BIT abs: skips the ORA
@norm:  ORA     #$80
        STA     (txt_dst),Y
        INY
        BNE     @ch
@eos:   INY                     ; past the 0
        TYA
        CLC
        ADC     txt_ptr
        STA     txt_ptr
        BCC     @rec
        INC     txt_ptr+1
        BNE     @rec
@end:   RTS

; txt_row -- A = row 0..23 -> txt_dst = $0400 + 128 (row & 7) + 40 (row >> 3)
txt_row:
        PHA
        LSR
        AND     #$03
        ORA     #$04
        STA     txt_dst+1
        PLA
        PHA
        LSR
        LSR
        LSR                     ; row >> 3: 0, 1, 2
        TAX
        PLA
        LSR                     ; bit 0 -> carry
        LDA     #0
        ROR                     ; $80 for odd rows
        CLC
        ADC     txt_row40,X
        STA     txt_dst
        RTS
txt_row40:
        .byte   0, 40, 80

