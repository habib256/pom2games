; ============================================================================
; hof.inc -- hall of fame: best time and best points per track, on the disk
; ============================================================================
;   hof_load    at start (DOS still in memory): read DIRTHOF; an unreadable
;               or foreign file gives an empty table
;   hof_save    write it back. C = 1: not saved (write protected, error)
;   hof_entry   after a record (hof_new: bit 0 time, bit 1 points): ask for
;               the initials (keyboard or joystick), keep them, save
;   hof_page    A = 0 / 15: 15 tracks from that one (HGR page 1)
;
; DIRTHOF is an ordinary DOS binary file of two sectors, made by
; tools/hof.py; dev/tools/dos33patch.py writes the track / sector of both data
; sectors into hof_t / hof_s. They are read and written whole through RWTS
; in HOFBUF..+511 (track_ids' last page and the T/S list page: free outside
; load_track, which runs again before the next race): bytes 0-3 are DOS's
; header, then hof_img as laid out below.
; ============================================================================

HOFBUF   = TSLBUF - $100
HOF_CHARS_N = 38                ; A-Z, 0-9, space, -
INI_CHARS   = hof_chars         ; initials.asm's ini_key edits last_ini
INI_CHARS_N = HOF_CHARS_N       ; at hpos with this ring of letters
ini_buf     = last_ini
ini_pos     = hpos

.segment "LOWBSS"
hof_img:                        ; = the file after its DOS header
hof_magic: .res 4               ; "DBH", version 1
rec_min:  .res NTRACKS          ; best time per track, rec_min = $FF: none
rec_sec:  .res NTRACKS
rec_hun:  .res NTRACKS
rec_ini:  .res NTRACKS * 3      ; initials of each best time
rec_pts:  .res NTRACKS * 3      ; best points per track, BCD (low byte first)
rec_pini: .res NTRACKS * 3      ; initials of each best points
last_ini: .res 3                ; the last initials typed (the next default)
inp_pref: .res 1                ; the input device chosen (input.inc)
HOF_LEN = * - hof_img
.assert HOF_LEN + 4 <= 512, error, "hof_img: more than DIRTHOF's two sectors"
hof_new:  .res 1                ; the race's records: bit 0 time, bit 1 points
hpos:     .res 1                ; initials: the letter being changed
hrow:     .res 1                ; hof_page: the row of the line
.segment "BSS"

.segment "DATA"
hof_t:    .byte 0, 0            ; DIRTHOF's data sectors (dev/tools/dos33patch.py)
hof_s:    .byte 0, 0

.segment "CODE"

.segment "INIT"                 ; boot only: overwritten by the pool
hof_load:
        JSR     hof_read
        BCS     @empty
        LDX     #3
@m:     LDA     HOFBUF+4,X
        CMP     hof_magic_ok,X
        BNE     @empty
        DEX
        BPL     @m
        LDX     #0
@c:     LDA     HOFBUF+4,X
        STA     hof_img,X
        INX
        BNE     @c
@d:     LDA     HOFBUF+4+256,X          ; exactly HOF_LEN: BSS follows
        STA     hof_img+256,X
        INX
        CPX     #HOF_LEN-256
        BNE     @d
        RTS
@empty: LDX     #3
@em:    LDA     hof_magic_ok,X
        STA     hof_magic,X
        DEX
        BPL     @em
        LDX     #NTRACKS-1
@e1:    LDA     #$FF
        STA     rec_min,X
        DEX
        BPL     @e1
        LDX     #NTRACKS*3-1
@e2:    LDA     #'-'
        STA     rec_ini,X
        STA     rec_pini,X
        LDA     #0
        STA     rec_pts,X
        DEX
        BPL     @e2
        LDA     #'A'
        STA     last_ini
        STA     last_ini+1
        STA     last_ini+2
        LDA     #INP_STICK              ; (the stick if one is found)
        STA     inp_pref
        RTS

.segment "CODE"
hof_save:
        JSR     hof_read                ; keep DOS's header (bytes 0-3)
        BCS     @rts
        LDX     #0
@c:     LDA     hof_img,X
        STA     HOFBUF+4,X
        LDA     hof_img+256,X           ; (past HOF_LEN: BSS that follows,
        STA     HOFBUF+4+256,X          ;  harmless in the file's slack)
        INX
        BNE     @c
        LDX     #0
        JSR     hof_sector
        JSR     rwts_write
        BCS     @rts
        LDX     #1
        JSR     hof_sector
        JMP     rwts_write
@rts:   RTS

; hof_read -- both sectors into HOFBUF. C = 1: error
hof_read:
        LDX     #0
        JSR     hof_sector
        JSR     rwts_read
        BCS     @rts
        LDX     #1
        JSR     hof_sector
        JMP     rwts_read
@rts:   RTS

; hof_sector -- point RWTS at data sector X (0 / 1) and its page
hof_sector:
        LDA     hof_t,X
        STA     rwts_track
        LDA     hof_s,X
        STA     rwts_sector
        TXA
        CLC
        ADC     #>HOFBUF
        STA     rwts_page
        RTS

; ---------------------------------------------------------------------------
; hof_entry -- the record of track sel: initials, then save
; ---------------------------------------------------------------------------
hof_entry:
        JSR     page1_text
        JSR     hgr_puts8_at
        .byte   14, 32
        .addr   msg_newrec
        LDA     #8                      ; "NN NAME"
        STA     ht_col
        LDA     #48
        STA     ht_sl
        LDA     sel
        JSR     put_track_label
        LDA     hof_new                 ; "TEMPS  M:SS.T" / "POINTS NNNNNN"
        LSR     A
        BCC     @nt
        JSR     hgr_puts8_at
        .byte   12, 62
        .addr   msg_rtime
        LDA     #20
        STA     ht_col
        LDX     sel
        LDA     rec_min,X
        LDY     rec_sec,X
        PHA
        LDA     rec_hun,X
        TAX
        PLA
        JSR     put_time
@nt:    LDA     hof_new
        AND     #2
        BEQ     @np
        JSR     hgr_puts8_at
        .byte   12, 72
        .addr   msg_rpts
        LDA     #20
        STA     ht_col
        LDA     sel
        JSR     put_points
@np:    JSR     hgr_puts8_at
        .byte   8, 88
        .addr   msg_ini
        JSR     hgr_puts8_at
        .byte   1, 144
        .addr   msg_inihelp
        JSR     hgr_puts8_at
        .byte   1, 156
        .addr   msg_inihelp2
        LDA     #0
        STA     hpos
        STA     hrow
@show:  JSR     ini_draw
@wait:  LDA     #79                     ; ~1/60 s a turn
        JSR     WAIT
        LDA     KBD
        BMI     @key
        LDY     #REPEAT * 2
        JSR     stick_menu
        BEQ     @wait
        CMP     #KC_RET
        BNE     @ini
        LDA     hpos                    ; button: next letter, then done
        CMP     #2
        BCS     @done
        INC     hpos
        BCC     @show                   ; (always)
@key:   BIT     KBDSTRB
        AND     #$7F
@ini:   JSR     ini_key                 ; initials.asm: a letter of hof_chars
        BCC     @show                   ; (lowercase too), arrows, DELETE
        CMP     #KC_RET                 ; ESC: ignored
        BNE     @wait
@done:  LDA     sel                     ; the records' initials
        STA     msel
        ASL     A
        ADC     msel
        TAY
        LDX     #0
@cp:    LDA     last_ini,X
        LSR     hof_new                 ; (bit 0 to C, back with ROL)
        BCC     @c1
        STA     rec_ini,Y
@c1:    ROL     hof_new
        PHA
        LDA     hof_new
        AND     #2
        BEQ     @c2
        PLA
        STA     rec_pini,Y
        PHA
@c2:    PLA
        INY
        INX
        CPX     #3
        BNE     @cp
        JSR     hgr_puts8_at
        .byte   8, 120
        .addr   msg_saving
        JSR     hof_save
        BCC     @ok
        JSR     hgr_puts8_at            ; write protected: say so, go on
        .byte   4, 120
        .addr   msg_nosave
        LDX     #120                    ; ~2 s
@pause: LDA     #79
        JSR     WAIT
        DEX
        BNE     @pause
@ok:    BIT     KBDSTRB
        RTS

; ini_draw -- the three letters (cols 24-26) and the marker under hpos
ini_draw:
        LDA     #24
        STA     ht_col
        LDA     #88
        STA     ht_sl
        LDA     #<last_ini
        STA     ht_src_lo
        LDA     #>last_ini
        STA     ht_src_hi
        LDX     #0
@c:     LDA     last_ini,X
        JSR     hgr_putc8
        INX
        CPX     #3
        BNE     @c
        LDA     #24
        STA     ht_col
        LDA     #98
        STA     ht_sl
        LDX     #0
@m:     LDA     #' '
        CPX     hpos
        BNE     @sp
        LDA     #'^'
@sp:    JSR     hgr_putc8
        INX
        CPX     #3
        BNE     @m
        RTS

; ---------------------------------------------------------------------------
; hof_page -- A = first track (0 / 15): 15 lines of
; "NN NAME           M:SS.T ABC 012345 ABC" (best time, best points)
; ---------------------------------------------------------------------------
hof_page:
        STA     msel
        JSR     page1_text
        JSR     hgr_puts8_at
        .byte   14, 6
        .addr   msg_hof
        JSR     hgr_puts8_at
        .byte   18, 20
        .addr   msg_hofcols
        LDA     #34
        STA     hrow
@line:  LDA     #0
        STA     ht_col
        LDA     hrow
        STA     ht_sl
        LDA     msel
        JSR     put_track_label
        LDA     #18
        STA     ht_col
        LDX     msel
        LDA     rec_min,X
        CMP     #$FF
        BNE     @time
        LDA     #<msg_notime
        LDY     #>msg_notime
        LDX     hrow
        JSR     puts_at
        JMP     @ini
@time:  LDY     rec_sec,X
        PHA
        LDA     rec_hun,X
        TAX
        PLA
        JSR     put_time
@ini:   LDA     #25
        STA     ht_col
        LDA     #<rec_ini
        LDX     #>rec_ini
        JSR     put_ini
        LDA     #29
        STA     ht_col
        LDA     msel
        JSR     put_points
        LDA     #36
        STA     ht_col
        LDA     #<rec_pini
        LDX     #>rec_pini
        JSR     put_ini
        CLC
        LDA     hrow
        ADC     #9
        STA     hrow
        INC     msel
        LDA     msel
        CMP     #15
        BEQ     @end
        CMP     #30
        BNE     @line
@end:   RTS

; put_ini -- the 3 initials of track msel from the table at A/X (lo/hi)
put_ini:
        STA     ht_src_lo
        STX     ht_src_hi
        LDA     msel
        ASL     A
        ADC     msel
        TAY
        LDX     #3
@c:     LDA     (ht_src_lo),Y
        JSR     hgr_putc8
        INY
        DEX
        BNE     @c
        RTS

; put_points -- the 6 BCD digits of rec_pts of track A
put_points:
        STA     ht_src_lo               ; (scratch)
        ASL     A
        ADC     ht_src_lo
        TAX
        LDA     rec_pts+2,X
        JSR     put_bcd
        LDA     rec_pts+1,X
        JSR     put_bcd
        LDA     rec_pts,X
put_bcd:
        PHA
        LSR     A
        LSR     A
        LSR     A
        LSR     A
        ORA     #'0'
        JSR     hgr_putc8
        PLA
        AND     #$0F
        ORA     #'0'
        JMP     hgr_putc8

.segment "RODATA"
hof_magic_ok: .byte "DBH", 1
hof_chars:    .byte "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -"
msg_newrec:   .byte "NEW RECORD !", 0
msg_ini:      .byte "YOUR INITIALS :", 0
msg_inihelp:  .byte "LETTERS OR UP/DOWN, LEFT/RIGHT", 0
msg_inihelp2: .byte "RETURN OR BUTTON: DONE", 0
msg_saving:   .byte "SAVING...    ", 0
msg_nosave:   .byte "WRITE PROTECTED: NOT SAVED", 0
msg_hof:      .byte "HALL OF FAME", 0
msg_hofcols:  .byte "TIME        POINTS", 0
msg_rtime:    .byte "TIME", 0
msg_rpts:     .byte "POINTS", 0
msg_notime:   .byte "-:--.-", 0
.segment "CODE"
