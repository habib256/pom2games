; ============================================================================
; dos.asm -- run DOS 3.3 commands (BLOAD, BSAVE...) from a BRUN program
; ============================================================================
; A machine-language program talks to DOS the way BASIC does: RETURN, Ctrl-D,
; the command, RETURN, all through COUT. DOS intercepts the line and runs it.
;
;   dos_cmd_new  -- empty the command buffer.
;   dos_cmd_add  -- append the ASCIIZ string at A (lo) / Y (hi).
;   dos_cmd_hex  -- append A as two hex digits (for ",A$6000", ",L$024E").
;   dos_cmd_run  -- have DOS run the command; returns when DOS is done.
;   disk_protected -- C = 1 if the disk in slot 6 is write protected.
;   All clobber A, X, Y.
;
;   JSR dos_cmd_new                     ; "BSAVE SAVE,A$1234,L$0010"
;   LDA #<str_bsave / LDY #>str_bsave   ; .byte "BSAVE SAVE,A$", 0
;   JSR dos_cmd_add
;   LDA #>buf / JSR dos_cmd_hex / LDA #<buf / JSR dos_cmd_hex
;   ...
;   JSR disk_protected                  ; skip the BSAVE on a protected disk:
;   BCS @skip                           ; DOS would stop on WRITE PROTECTED
;   JSR dos_cmd_run
;
; Page zero: DOS and the Monitor need their own. dos_cmd_run sets the
; program's page zero aside (256 bytes of BSS), puts back the snapshot that
; exit.asm's apple2_zp_save took at start, runs the command, makes DOS's page
; zero the new snapshot and restores the program's. So apple2_zp_save must
; have run first, and exit.asm must be included.
;
; Errors: DOS handles them itself (FILE NOT FOUND, I/O ERROR, WRITE
; PROTECTED...) by stopping the program at the BASIC prompt. Put every file
; the program loads on the disk (the Makefile), and test disk_protected
; before writing.
;
; dos_cmd_add reads its string through a self-modified absolute address, so
; the module needs no zero page. The buffer holds DOS_CMD_MAX - 1 characters
; (define DOS_CMD_MAX before the include to change it; default 40).
; disk_protected assumes the boot drive is in slot 6 (the usual Disk II).
;
; BSS: dos_cmd_buf, dos_cmd_ix, dos_zp_prog (256).
; Caller responsibility: .include "apple2.inc" and "exit.asm".
; Mirror for C: a2_dos_cmd(), a2_disk_protected() in ../apple2c/apple2io.h.
; ============================================================================

.ifndef _DOS_ASM_LOADED_
_DOS_ASM_LOADED_ = 1

.ifndef DOS_CMD_MAX
DOS_CMD_MAX = 40
.endif

DOS_HOOKS = $03EA               ; DOS: reconnect its I/O hooks to CSW / KSW

.segment "BSS"
dos_cmd_buf:    .res DOS_CMD_MAX
dos_cmd_ix:     .res 1
dos_zp_prog:    .res 256        ; the program's page zero during a command

.segment "CODE"

dos_cmd_new:
        LDA     #$00
        STA     dos_cmd_ix
        STA     dos_cmd_buf
        RTS

dos_cmd_add:
        STA     @src+1
        STY     @src+2
        LDY     #$00
@lp:    LDX     dos_cmd_ix
@src:   LDA     $FFFF,Y         ; self-modified: the string
        STA     dos_cmd_buf,X
        BEQ     @done           ; (Z from the load: STA keeps it)
        INC     dos_cmd_ix
        INY
        BNE     @lp
@done:  RTS

dos_cmd_hex:
        PHA
        LSR     A
        LSR     A
        LSR     A
        LSR     A
        JSR     @nib
        PLA
        AND     #$0F
@nib:   CMP     #10
        BCC     @dig
        ADC     #6              ; C = 1: + 7, 'A'..'F'
@dig:   ADC     #'0'
        LDX     dos_cmd_ix
        STA     dos_cmd_buf,X
        INX
        LDA     #$00
        STA     dos_cmd_buf,X
        STX     dos_cmd_ix
        RTS

dos_cmd_run:
        LDX     #$00
@in:    LDA     $00,X
        STA     dos_zp_prog,X
        LDA     apple2_zp_buf,X
        STA     $00,X
        INX
        BNE     @in
        JSR     DOS_HOOKS
        LDA     #$8D
        JSR     COUT
        LDA     #$84            ; Ctrl-D
        JSR     COUT
        LDX     #$00
@ch:    LDA     dos_cmd_buf,X
        BEQ     @end
        ORA     #$80
        STX     dos_cmd_ix      ; COUT keeps X, but DOS may not
        JSR     COUT
        LDX     dos_cmd_ix
        INX
        BNE     @ch
@end:   LDA     #$8D            ; DOS runs the command here
        JSR     COUT
        LDX     #$00
@out:   LDA     $00,X
        STA     apple2_zp_buf,X
        LDA     dos_zp_prog,X
        STA     $00,X
        INX
        BNE     @out
        RTS

; Disk II sense, slot 6: motor on, Q6 high, then Q7 low reads the
; write-protect switch in bit 7. The drive keeps spinning ~1 s after.
disk_protected:
        LDA     $C0E9           ; motor on
        LDA     $C0ED           ; Q6H
        LDA     $C0EE           ; Q7L: bit 7 = write protect
        ASL     A               ; -> C
        LDA     $C0E8           ; motor off
        RTS

.endif  ; _DOS_ASM_LOADED_
