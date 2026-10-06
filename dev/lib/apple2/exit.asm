; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; exit.asm -- leave a BRUN program cleanly back to DOS 3.3
; ============================================================================
; The Apple II zero page is shared with the Monitor, DOS and Applesoft.
; A program must restore it before returning to BASIC to keep its pointers
; valid. Save a snapshot at startup and restore it on exit:
;
;   main:   APPLE2_PREAMBLE
;           JSR apple2_zp_save      ; FIRST, before touching any ZP byte
;           ...
;   quit:   JMP apple2_exit         ; restore ZP, text screen, DOS prompt
;
;   apple2_zp_save  copy $0000-$00FF into a 256-byte BSS buffer, and point the
;                   Ctrl-RESET vector ($03F2-$03F4) at apple2_exit, so RESET
;                   also leaves cleanly instead of handing DOS/BASIC a zero
;                   page full of game state. Clobbers A, X.
;   apple2_return   the same restore, then RTS to whoever called the program
;                   (a BASIC CALL): the stack pointer saved by the first
;                   apple2_zp_save is put back first. Use it with
;                   APPLE2_PREAMBLE_CALL. Ctrl-RESET still goes to DOS.
;
;   apple2_exit     put the RESET vector and the snapshot back (the live
;                   text window and cursor, $20-$29, are kept: a program
;                   that switched 40/80 columns leaves DOS a consistent
;                   window -- reset WNDTOP yourself if you moved it),
;                   restore a clean text display
;                   (TEXT, full screen, page 1, lores latch), clear the key
;                   strobe, then JMP DOSWARM ($03D0): the ']' prompt, with the
;                   BASIC program still in memory. Never returns.
;
; Calling apple2_zp_save again (a game that restarts through its init code)
; is a no-op: the RESET vector already points at apple2_exit, so the first
; snapshot -- DOS's page zero, DOS's vector -- is kept. apple2_exit without a
; snapshot skips the restore and just goes back to DOS.
; Optional APPLE2_EXIT_HOOK names a routine called after exit_restore, before
; DOSWARM (also on Ctrl-RESET). It may restore BASIC overwritten by the game;
; it runs with DOS's zero page and must return without relying on game ZP.
;
; A program that never exits (it runs until RESET or power-off) can skip both.
; apple2_return is assembled only if referenced before the include (.ifref).
; The snapshot goes to BSS unless the program defined apple2_zp_buf (256 bytes)
; before the include: $0200-$02FF is free while no DOS command is running.
; Caller responsibility: .include "apple2.inc" first.
; ============================================================================

.ifndef _EXIT_ASM_LOADED_
_EXIT_ASM_LOADED_ = 1

.segment "BSS"
.ifndef apple2_zp_buf           ; a program short of BSS may define these 256
apple2_zp_buf:  .res 256        ; bytes itself, before the include (any RAM
.endif                          ; that DOS and the Monitor leave alone)
apple2_entry_sp: .res 1         ; caller's stack pointer (for apple2_return)
apple2_rst_buf: .res 3          ; $03F2-$03F4 as DOS left them

.segment "CODE"

apple2_zp_save:
        JSR     exit_armed      ; already saved? keep that snapshot
        BEQ     @done
        TSX                     ; the caller's stack pointer: ours + our
        INX                     ; own return address
        INX
        STX     apple2_entry_sp
        LDX     #$00
@lp:    LDA     $00,X
        STA     apple2_zp_buf,X
        INX
        BNE     @lp
        LDX     #2
@rsv:   LDA     SOFTEV,X
        STA     apple2_rst_buf,X
        DEX
        BPL     @rsv
        LDA     #<apple2_exit
        STA     SOFTEV
        LDA     #>apple2_exit
        STA     SOFTEV+1
        EOR     #$A5            ; power-up byte: RESET warm-starts through us
        STA     SOFTEV+2
@done:  RTS

; exit_armed: Z = 1 if the RESET vector points at apple2_exit (snapshot taken).
exit_armed:
        LDA     SOFTEV
        CMP     #<apple2_exit
        BNE     @no
        LDA     SOFTEV+1
        CMP     #>apple2_exit
@no:    RTS

apple2_exit:
        JSR     exit_restore
.ifdef APPLE2_EXIT_HOOK
        JSR     APPLE2_EXIT_HOOK
.endif
        JMP     DOSWARM

.ifref apple2_return            ; only for programs started by CALL
apple2_return:
        JSR     exit_restore
        LDX     apple2_entry_sp ; back on the caller's stack, then return to it
        TXS
        RTS
.endif

; exit_restore: RESET vector + zero page (live text window and cursor kept) +
;   a clean text display. Shared by apple2_exit / apple2_return.
exit_restore:
        JSR     exit_armed      ; no snapshot: nothing to put back
        BNE     @text
        LDX     #2
@rrv:   LDA     apple2_rst_buf,X
        STA     SOFTEV,X
        DEX
        BPL     @rrv
        LDX     #9              ; keep the LIVE text window + cursor ($20-$29:
@keep:  LDA     $20,X           ; WNDLFT..WNDBTM, CH, CV, GBASL/H, BASL/H) so
        STA     apple2_zp_buf+$20,X ; the prompt follows the program's output
        DEX
        BPL     @keep
        LDX     #$00
@lp:    LDA     apple2_zp_buf,X
        STA     $00,X
        INX
        BNE     @lp
@text:  BIT     TXTSET
        BIT     MIXCLR
        BIT     LOWSCR
        BIT     LORES
        BIT     KBDSTRB
        RTS

.endif  ; _EXIT_ASM_LOADED_
