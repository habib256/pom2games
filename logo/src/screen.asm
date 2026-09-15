; ============================================================================
; screen.asm -- Apple II screen for LOGO: TEXT / SPLIT / FULL, 40 / 80 columns
; ============================================================================
; On the Apple-1 + GEN2 machine LOGO had two screens: the Apple-1 terminal for
; the console and the GEN2 card for the turtle. The Apple II has one, so the
; console and the turtle share it the Apple Logo way:
;
;   TEXTSCREEN  / TS  (Ctrl-T)  full text console
;   SPLITSCREEN / SS  (Ctrl-S)  HGR turtle + 4 text lines at the bottom
;   FULLSCREEN  / FS  (Ctrl-L)  HGR turtle only (typing goes on, unseen)
;   COLUMNS 40 / COLUMNS 80     console width
;
; A turtle command issued in TEXTSCREEN switches to SPLITSCREEN by itself
; (scr_gfx); HELP switches to TEXTSCREEN; EDIT uses FULLSCREEN while it runs.
;
; 80 columns: on a //e (or //c) scr_boot starts the 80-column firmware itself
; (JSR $C300, then $03EA hands DOS its I/O hooks back). If the 80-column card
; is there the console comes up in 80 columns, otherwise the firmware stays in
; 40 and COLUMNS 80 answers an error. A ][ / ][+ keeps the Monitor's 40-column
; COUT. The firmware switches width on Ctrl-Q (40) / Ctrl-R (80) output
; characters and reports it in RD80COL ($C01F bit 7).
;
; In SPLITSCREEN / FULLSCREEN the text window starts at row 20 (WNDTOP), so the
; console scrolls inside the 4 visible lines.
; ============================================================================

SCR_TEXT  = 0
SCR_SPLIT = 1
SCR_FULL  = 2

MACHID    = $FBB3       ; $06 on a //e / //c, anything else on a ][ / ][+
RD80COL   = $C01F       ; //e: bit 7 = 80-column display on
SETAN3    = $C05F       ; annunciator 3 on: plain HGR even with 80COL (no DHGR)
WNDTOP    = $22         ; Monitor text window: top row
OURCV     = $05FB       ; //e 80-column firmware: its own cursor row
FW80_INIT = $C300       ; //e 80-column firmware entry (PR#3)
DOS_HOOKS = $03EA       ; DOS 3.3: reconnect DOS to the current CSW / KSW
SPLIT_TOP = 20          ; first text row shown under the HGR in mixed mode

.segment "LINEBUF"
scr_mode:   .res 1      ; SCR_TEXT / SCR_SPLIT / SCR_FULL
scr_iie:    .res 1      ; 1 = //e family (the 80-column firmware exists)
col80_ok:   .res 1      ; 1 = 80 columns available (firmware + card)

.segment "CODE"

; ----------------------------------------------------------------------------
; scr_boot: detect the machine, bring 80 columns up when they exist.
;   Call before any console output. Clobbers A, X, Y.
; ----------------------------------------------------------------------------
scr_boot:
        LDA #0
        STA scr_iie
        STA col80_ok
        STA scr_mode
        LDA MACHID
        CMP #$06
        BNE @done               ; ][ / ][+: 40 columns
        INC scr_iie
        LDA RD80COL
        BMI @on                 ; already on (PR#3 before BRUN)
        JSR FW80_INIT           ; start the firmware (clears the screen)
        JSR DOS_HOOKS
        LDA RD80COL
        BPL @done               ; no 80-column card: the firmware runs 40
@on:    INC col80_ok
@done:  RTS

; ----------------------------------------------------------------------------
; scr_set: A = SCR_TEXT / SCR_SPLIT / SCR_FULL. Preserves X and Y.
; ----------------------------------------------------------------------------
scr_set:
        STA scr_mode
        TXA
        PHA
        LDA HIRES               ; HGR latch, page 1 (never PAGE2: with the
        LDA LOWSCR              ; 80-column firmware on it bank-switches RAM)
        LDA SETAN3
        LDX scr_mode
        BNE @gfx
        LDA TXTSET
        LDA MIXCLR
        LDA #0
        STA WNDTOP
        JMP @out
@gfx:   LDA TXTCLR
        CPX #SCR_FULL
        BEQ @full
        LDA MIXSET
        JMP @win
@full:  LDA MIXCLR
@win:   LDA #SPLIT_TOP
        STA WNDTOP
        LDA CV                  ; cursor above the window: park it on the
        CMP #SPLIT_TOP          ; bottom row so the console stays visible
        BCS @out
        LDA #23
        STA CV
        LDX scr_iie
        BEQ @vtab
        STA OURCV
@vtab:  JSR VTAB
@out:   PLA
        TAX
        RTS

; scr_gfx: a turtle command is about to draw -- leave TEXTSCREEN for
;   SPLITSCREEN. Preserves X and Y.
scr_gfx:
        LDA scr_mode
        BNE @r
        LDA #SCR_SPLIT
        JMP scr_set
@r:     RTS

; ----------------------------------------------------------------------------
; scr_hotkey: A = key (7-bit). Ctrl-T / Ctrl-S / Ctrl-L switch the screen and
;   return C = 1; any other key returns C = 0 with A unchanged. Preserves X, Y.
; ----------------------------------------------------------------------------
scr_hotkey:
        CMP #$14                ; Ctrl-T
        BNE @s
        LDA #SCR_TEXT
        BEQ @set
@s:     CMP #$13                ; Ctrl-S
        BNE @f
        LDA #SCR_SPLIT
        BNE @set
@f:     CMP #$0C                ; Ctrl-L
        BNE @no
        LDA #SCR_FULL
@set:   JSR scr_set
        SEC
        RTS
@no:    CLC
        RTS

; ----------------------------------------------------------------------------
; Line-input cursor: an underscore under the pen, overwritten by the next
; character. Both preserve X and Y (COUT does).
; ----------------------------------------------------------------------------
scr_cursor:
        LDA #'_' | $80
        JSR ECHO
        LDA #$88                ; back over it
        JMP ECHO

; scr_rubout: erase the character before the cursor (pen ends on it).
scr_rubout:
        LDA #$88
        JSR ECHO
        LDA #' ' | $80          ; erase the character
        JSR ECHO
        LDA #' ' | $80          ; erase the cursor
        JSR ECHO
        LDA #$88
        JSR ECHO
        LDA #$88
        JMP ECHO

; ----------------------------------------------------------------------------
; Commands
; ----------------------------------------------------------------------------
cmd_ts: LDA #SCR_TEXT
        JMP scr_set
cmd_ss: LDA #SCR_SPLIT
        JMP scr_set
cmd_fs: LDA #SCR_FULL
        JMP scr_set

; cmd_columns: COLUMNS 40 / COLUMNS 80 (arg_lo:hi parsed by the dispatcher).
cmd_columns:
        LDA arg_hi
        BNE @bad
        LDA arg_lo
        CMP #40
        BEQ @c40
        CMP #80
        BNE @bad
        LDA col80_ok
        BEQ @bad                ; no 80-column card / not a //e
        LDA #$92                ; Ctrl-R: 80-column display
        JMP ECHO
@c40:   LDA col80_ok
        BEQ @r                  ; already 40
        LDA #$91                ; Ctrl-Q: 40-column display
        JMP ECHO
@bad:   LDA #ERR_BAD_ARG
        JMP print_err
@r:     RTS

; logo_exit: BYE -- full text window, then back to DOS with the zero page and
;   the RESET vector restored (dev/lib/apple2/exit.asm). The console width is
;   kept: the DOS prompt stays in 40 or 80 columns.
logo_exit:
        LDA #0
        STA WNDTOP
        JMP apple2_exit
