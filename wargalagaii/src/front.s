; WARGALAGA II -- the title screen (lot 9): its menu, the high scores, the
; help, a new record's initials, the HIGHSCORES file. Included by shop.s:
; in the overlay with the shop and Memory Station (memory SHOPM, run at
; $4000), copied there by front_run while page 1 shows. The fixed screens'
; routines are the shop's (sh_texts, sh_putc, sh_tick...).
;
; Page 1: the title picture (tools/title.py, LZ4FH-packed) on rows
; 0..PANEL_TOP-1, a panel below: menu, high scores or help, in turn while
; nobody plays (menu, scores, then the demo). Keys: RETURN, SPACE or button
; 0 plays; J (or TAB) keyboard / joystick; S sound; H help; ESC quits to
; ProDOS (elsewhere than the menu: back to the menu).
;
; HIGHSCORES: tools/records.py has the layout and the rules (8 entries,
; initials, BCD score, level reached; the controls). Read once, written
; after a new record or when the controls changed; a missing file is
; created, a write-protected disk only gets a message.

PANEL_LINE = 11
PANEL_TOP  = PANEL_LINE * 8      ; (tools/title.py: PANEL_TOP)
FR_MENU    = 0                   ; panels
FR_SCORES  = 1
FR_HELP    = 2
FR_ENTRY   = 3
FR_BONUS   = 4                   ; lot 10: GAME BONUSES (after a game)
REC_N      = 8                   ; tools/records.py
REC_ENTRY  = 7
REC_SIZE   = 64
REC_VERSION = 1
FR_TABLE_LINE = 13
FR_NAME_COL = 26                 ; initials on the entry panel
KEY_RETURN = $0D
KEY_DELETE = $7F

lz4fh_src = src                  ; (the decoder's scratch: the game's ZP)
lz4fh_dst = dst
lz4fh_read = ptr
lz4fh_write = r_row
lz4fh_match = r_w
lz4fh_token = tmp
lz4fh_length = tmp2
.assert r_col = r_row + 1 && r_h = r_w + 1, error, "lz4fh pointer pairs"

.segment "FRONT"
; A = 0 (boot, after the demo) or 1 (a game ended: a record?).
; -> A = 0 play, 1 the demo, $FF quit.
front_main:
        sta fr_why
        lda #0                   ; drawing on page 1, shown
        jsr select_page
        lda #<title_lz4
        sta lz4fh_src
        lda #>title_lz4
        sta lz4fh_src+1
        stz lz4fh_dst
        lda #$20
        sta lz4fh_dst+1
        jsr lz4fh_unpack
        stz sh_ev                ; the speaker's tune (sh_tick)
        lda #DUET_EVENT_SLICES
        sta sh_sl
        lda #$80
        sta DUET_KEYS
        lda $C010                ; a key still held from the game: locked
        and #$80                 ; until every key is up (fr_input)
        sta fr_lock
        jsr rec_load
        lda #FR_MENU
        ldx fr_why
        beq :+
        jsr fr_bonuses           ; (the score is final after it)
        jsr rec_new
        lda #FR_MENU
        bcc :+
        lda #FR_SCORES           ; a record: the table first
:       pha
        lda $C061                ; fire still held (from the game, the last
        and #$80                 ; initial): no press
        sta fr_btn
        pla
fr_go:  jsr fr_show
fr_loop:
        jsr sh_tick              ; ~1/30 s
        jsr sound_frame
        jsr fr_input
        bne fr_key
        lda fr_t
        bne :+
        dec fr_t+1
:       dec fr_t
        lda fr_t
        ora fr_t+1
        bne fr_loop
        lda fr_panel             ; idle: menu -> scores -> demo, help -> menu
        cmp #FR_SCORES
        beq fr_demo
        cmp #FR_MENU
        bne fr_menu
        lda #FR_SCORES
        bra fr_go
fr_demo:
        jsr rec_sync
        lda #1
        rts
fr_key: ldx fr_panel
        cpx #FR_MENU
        bne fr_other
        cmp #KEY_ESC
        beq fr_quit
        cmp #KEY_RETURN
        beq fr_play
        cmp #' '
        beq fr_play
        cmp #'J'
        beq fr_joy
        cmp #KEY_TAB
        beq fr_joy
        cmp #'S'
        beq fr_sound
        cmp #'H'
        beq fr_help
        cmp #'?'
        bne fr_menu              ; (another key: the idle time again)
fr_help:
        lda #FR_HELP
        bra fr_go
fr_other:                        ; scores, help: play, or back to the menu
        cmp #KEY_RETURN
        beq fr_play
        cmp #' '
        beq fr_play
fr_menu:
        lda #FR_MENU
        bra fr_go
fr_joy: lda joy_mode
        eor #1
        sta joy_mode
        bra fr_menu
fr_sound:
        jsr sound_toggle
        bra fr_menu
fr_play:
        jsr rec_sync
        lda #0
        rts
fr_quit:
        jsr rec_sync
        lda #$FF
        rts

; -> A: a key (upper case), KEY_RETURN for a press of button 0, else 0 (Z).
fr_input:
        lda $C000
        bpl fi_btn
        bit $C010
        bit fr_lock              ; a key held since the game: its repeats
        bmi fi_none              ; don't count (SPACE held for autofire)
        and #$7F
        ; fall through
; A -> upper case (a..z only: DELETE stays $7F).
fr_upper:
        cmp #'a'
        bcc :+
        cmp #'z'+1
        bcs :+
        and #$DF
:       rts
fi_none:
        lda #0
        rts
fi_btn: bit $C010                ; every key up: no more lock
        bmi :+
        stz fr_lock
:       lda $C061                ; button 0 / open apple: a new press
        and #$80
        tay
        eor fr_btn
        sty fr_btn
        and fr_btn
        beq :+
        lda #KEY_RETURN
:       rts

; GAME BONUSES (lot 10, as Warblade's end of game): the credits left x 100,
; the rank x 10 000, the perfect bonus levels x 5 000, their sum added to
; the score (999 999 at most); until a key or FR_BONUS's time.
FB_AMOUNT = 30                   ; column of the amounts
fr_bonuses:
        lda #FR_BONUS
        jsr fr_show
        stz fb_sum
        stz fb_sum+1
        stz fb_sum+2
        lda #13*8                ; cash: credits (BCD) x 100
        sta sh_row
        stz sh_lead
        ldy #17
        lda credits+1
        jsr sh_bcd
        lda credits
        jsr sh_bcd_last
        stz fb_val
        lda credits
        sta fb_val+1
        lda credits+1
        sta fb_val+2
        jsr fb_line
        lda #14*8                ; rank x 10 000
        sta sh_row
        lda rank
        ldy #19
        jsr sh_dec2
        lda rank
        jsr fb_bcd
        stz fb_val
        stz fb_val+1
        sta fb_val+2
        jsr fb_line
        lda #15*8                ; perfects x 5 000 (99 at most)
        sta sh_row
        lda perfects
        cmp #100
        bcc :+
        lda #99
:       sta fr_k
        ldy #19
        jsr sh_dec2
        stz fb_val
        stz fb_val+1
        stz fb_val+2
        ldx fr_k
        sed
:       dex
        bmi :+
        clc
        lda fb_val+1
        adc #$50
        sta fb_val+1
        lda fb_val+2
        adc #0
        sta fb_val+2
        bra :-
:       cld
        jsr fb_line
        lda #17*8                ; their sum
        sta sh_row
        ldx #2
:       lda fb_sum,x
        sta fb_val,x
        dex
        bpl :-
        jsr fb_show
        ldx #2                   ; score += sum
:       lda score,x
        sta fb_sum,x
        dex
        bpl :-
        jsr fb_add
        ldx #2
:       lda fb_sum,x
        sta score,x
        sta fb_val,x
        dex
        bpl :-
        lda #19*8
        sta sh_row
        jsr fb_show
fb_wait:
        jsr sh_tick              ; ~1/30 s
        jsr sound_frame
        jsr fr_input
        bne :++
        lda fr_t
        bne :+
        dec fr_t+1
:       dec fr_t
        lda fr_t
        ora fr_t+1
        bne fb_wait
:       rts
; fb_val at column FB_AMOUNT (six digits), then fb_sum += fb_val.
fb_line:
        jsr fb_show
        ; fall through
; fb_sum += fb_val (BCD), 999 999 at most.
fb_add: sed
        clc
        ldx #0
:       lda fb_sum,x
        adc fb_val,x
        sta fb_sum,x
        inx
        txa                      ; (keeps the carry)
        eor #3
        bne :-
        cld
        bcc :+
        lda #$99
        sta fb_sum
        sta fb_sum+1
        sta fb_sum+2
:       rts
fb_show:
        stz sh_lead
        ldy #FB_AMOUNT
        lda fb_val+2
        jsr sh_bcd
        lda fb_val+1
        jsr sh_bcd
        lda fb_val
        jmp sh_bcd_last
; A = 0..99 -> BCD.
fb_bcd: tax
        lda #0
        sed
:       dex
        bmi :+
        clc
        adc #1
        bra :-
:       cld
        rts

; Panel A: cleared, its texts, its idle time.
fr_show:
        sta fr_panel
        jsr fr_clear
        ldx fr_panel
        lda fr_txt_lo,x
        sta ptr
        lda fr_txt_hi,x
        sta ptr+1
        jsr sh_texts
        ldx fr_panel
        lda fr_time_lo,x
        sta fr_t
        lda fr_time_hi,x
        sta fr_t+1
        lda fr_panel
        beq fr_menu_vars
        cmp #FR_SCORES
        beq fr_table
        rts

; The menu's settings and the best score.
fr_menu_vars:
        lda #14*8
        sta sh_row
        lda #<fr_kbd_txt
        ldy #>fr_kbd_txt
        ldx joy_mode
        beq :+
        lda #<fr_joy_txt
        ldy #>fr_joy_txt
:       sta ptr
        sty ptr+1
        ldx #8
        ldy #22
        jsr sh_chars
        lda #15*8
        sta sh_row
        lda #<fr_on_txt
        ldy #>fr_on_txt
        ldx sound_on
        bne :+
        lda #<fr_off_txt
        ldy #>fr_off_txt
:       sta ptr
        sty ptr+1
        ldx #3
        ldy #22
        jsr sh_chars
        lda #20*8
        sta sh_row
        ldx #0
        jmp fr_entry

; The table: rank, initials, score, level.
fr_table:
        ldx #0
:       phx
        txa
        clc
        adc #FR_TABLE_LINE
        asl
        asl
        asl
        sta sh_row
        txa
        clc
        adc #'1'
        ldy #6
        jsr sh_putc
        lda #'.'
        ldy #7
        jsr sh_putc
        plx
        phx
        jsr fr_entry
        plx
        inx
        cpx #REC_N
        bne :-
        rts

; Entry X at line sh_row: initials (column 9), score (14), L level (22).
fr_entry:
        lda fr_off,x
        sta fr_e
        ldy #9
:       ldx fr_e
        lda rec_buf,x
        jsr sh_putc
        inc fr_e
        iny
        cpy #12
        bne :-
        ldy #14                  ; (fr_e: the score)
        ; fall through
; Score at rec_buf + fr_e (3 BCD bytes, low first) at column Y, 6 digits
; with no leading zeros; then L and the level (rec_buf + fr_e + 3).
fr_score:
        stz sh_lead
        ldx fr_e
        lda rec_buf+2,x
        jsr sh_bcd
        ldx fr_e
        lda rec_buf+1,x
        jsr sh_bcd
        ldx fr_e
        lda rec_buf,x
        jsr sh_bcd_last
        iny
        iny
        lda #'L'
        jsr sh_putc
        iny
        ldx fr_e
        lda rec_buf+3,x
        ; fall through
; A = 0..255 at column Y: three characters, leading zeros as spaces.
fr_dec3:
        stz sh_lead
        ldx #0
:       cmp #100
        bcc :+
        sbc #100
        inx
        bra :-
:       pha
        txa
        jsr sh_digit
        pla
        ldx #0
:       cmp #10
        bcc :+
        sbc #10
        inx
        bra :-
:       pha
        txa
        jsr sh_digit
        sec
        ror sh_lead
        pla
        jmp sh_digit

; Rows PANEL_TOP..191 of page 1: black.
fr_clear:
        ldx #PANEL_TOP
fc_row: lda hgr_lo,x
        sta dst
        lda hgr_hi,x
        sta dst+1
        lda #0
        ldy #39
:       sta (dst),y
        dey
        bpl :-
        inx
        cpx #192
        bne fc_row
        rts

; ---------------------------------------------------------------------------
; The game that ended: a record? Its place in the table, initials typed (or
; picked with the stick), the file written. C = 1: a record.
rec_new:
        lda loop                 ; the level reached: 100 loop + level + 1
        cmp #3                   ; (at most 255)
        bcs rn_255
        tax
        lda level
        sec
        adc fr_hund,x
        bcc :+
rn_255: lda #255
:       sta fr_lv
        ldx #0
rn_find:
        ldy fr_off,x             ; score > entry X? (equal: below it)
        lda score+2
        cmp rec_buf+5,y
        bne :+
        lda score+1
        cmp rec_buf+4,y
        bne :+
        lda score
        cmp rec_buf+3,y
        beq rn_next
:       bcs rn_found
rn_next:
        inx
        cpx #REC_N
        bne rn_find
        clc
        rts
rn_found:
        stx fr_k
        lda fr_off,x             ; the entries below move down one
        clc
        adc #REC_ENTRY
        sta fr_e
        ldy #3+REC_N*REC_ENTRY-1
:       cpy fr_e
        bcc :+
        lda rec_buf-REC_ENTRY,y
        sta rec_buf,y
        dey
        bra :-
:       ldy fr_off,x             ; the new entry: score and level
        lda score
        sta rec_buf+3,y
        lda score+1
        sta rec_buf+4,y
        lda score+2
        sta rec_buf+5,y
        lda fr_lv
        sta rec_buf+6,y
        lda #FR_ENTRY
        jsr fr_show
        lda #14*8                ; the score and the level
        sta sh_row
        ldx fr_k
        lda fr_off,x
        clc
        adc #3
        sta fr_e
        ldy #14
        jsr fr_score
        stz fr_pos               ; initials: _ _ _ (stick: A to pick)
        lda #'_'
        sta fr_name
        sta fr_name+1
        sta fr_name+2
        jsr rn_first
        lda $C061                ; (the stick's button: as fr_btn)
        and #$80
        sta sh_held
        stz sh_rep
rn_draw:
        lda #<FR_ENTRY_T         ; (nobody there: counted from the last change)
        sta fr_t
        lda #>FR_ENTRY_T
        sta fr_t+1
        lda #17*8
        sta sh_row
        ldx #0
:       phx
        txa
        asl
        adc #FR_NAME_COL
        tay
        lda fr_name,x
        jsr sh_putc
        plx
        inx
        cpx #3
        bne :-
rn_loop:
        jsr sh_tick
        jsr sound_frame
        lda fr_t                 ; nobody there: what was typed
        bne :+
        dec fr_t+1
:       dec fr_t
        lda fr_t
        ora fr_t+1
        jeq rn_done
        lda $C000
        bmi rn_key
        jsr sh_stick             ; joystick mode: 1 up, 2 down, 3 button
        beq rn_loop
        ldx fr_pos
        cmp #3
        beq rn_next_letter
        ldy fr_name,x            ; up: A -> Z -> Y ..., down: A -> B ...
        cmp #1
        bne :+
        dey
        cpy #'A'
        bcs rn_set
        ldy #'Z'
        bra rn_set
:       iny
        cpy #'Z'+1
        bcc rn_set
        ldy #'A'
rn_set: tya
        sta fr_name,x
        bra rn_draw
rn_next_letter:
        inx                      ; (the letter shown is kept)
        stx fr_pos
        cpx #3
        beq rn_done
        jsr rn_first
        bra rn_draw
rn_key: bit $C010
        and #$7F
        jsr fr_upper
        cmp #KEY_RETURN
        beq rn_done
        ldx fr_pos
        cmp #KEY_LEFT
        beq rn_erase
        cmp #KEY_DELETE
        beq rn_erase
        cmp #'.'                 ; letters, digits and . are initials
        beq :+
        cmp #'0'
        bcc rn_loop
        cmp #'9'+1
        bcc :+
        cmp #'A'
        jcc rn_loop
        cmp #'Z'+1
        jcs rn_loop
:       sta fr_name,x
        bra rn_next_letter
rn_erase:
        cpx #0
        jeq rn_loop
        lda #'_'
        cpx #3
        beq :+
        sta fr_name,x
:       dex
        stx fr_pos
        sta fr_name,x
        jsr rn_first
        jmp rn_draw
rn_done:
        ldy fr_k                 ; the initials in, blanks for the rest
        ldx fr_off,y
        ldy #0
:       lda fr_name,y
        cmp #'_'
        bne :+
        lda #' '
:       sta rec_buf,x
        inx
        iny
        cpy #3
        bne :--
        inc rec_dirty
        jsr rec_sync
        sec
        rts
; The letter at fr_pos: A to start from with the stick, else _.
rn_first:
        lda joy_mode
        beq :+
        ldx fr_pos
        lda #'A'
        sta fr_name,x
:       rts

; ---------------------------------------------------------------------------
; HIGHSCORES -> rec_buf, once (the defaults if it can't be read).
rec_load:
        lda rec_state
        bne rl_done
        inc rec_state
        jsr rec_file
        jsr prodos_load
        bcs rl_default
        lda pf_got               ; all of it (a short file: the defaults)
        cmp #<REC_SIZE
        bne rl_default
        lda pf_got+1
        bne rl_default
        lda rec_buf
        cmp #'W'
        bne rl_default
        lda rec_buf+1
        cmp #REC_VERSION
        bne rl_default
        lda rec_buf+2
        and #1
        sta joy_mode
rl_done:
        rts
rl_default:
        ldx #REC_SIZE-1
:       lda rec_defaults,x
        sta rec_buf,x
        dex
        bpl :-
        rts

; Written if it changed (a record, the controls). A failure: a message on
; the panel's last line for ~2 s.
rec_sync:
        lda joy_mode
        cmp rec_buf+2
        beq :+
        sta rec_buf+2
        inc rec_dirty
:       lda rec_dirty
        beq rs_done
        stz rec_dirty
        jsr rec_save
        bcc rs_done
        lda #<fr_err_txt
        sta ptr
        lda #>fr_err_txt
        sta ptr+1
        jsr sh_texts
        stz DUET_KEYS            ; (a key would cut the speaker's ticks)
        lda #60
        sta fr_k
:       jsr sh_tick
        dec fr_k
        bne :-
        lda #$80
        sta DUET_KEYS
rs_done:
        rts

; rec_buf -> HIGHSCORES (created if missing). C = 1: an error, its code in
; rec_err (0: none).
rec_save:
        jsr rec_file
        jsr prodos_save
        sta rec_err
        rts

; The parameters of dev/lib/prodos/file.asm (here, in the overlay; the end
; of this file): HIGHSCORES <-> rec_buf.
rec_file:
        lda #<rec_name
        sta pf_name
        lda #>rec_name
        sta pf_name+1
        lda #<iobuf
        sta pf_iobuf
        lda #>iobuf
        sta pf_iobuf+1
        lda #<rec_buf
        sta pf_buf
        lda #>rec_buf
        sta pf_buf+1
        lda #<REC_SIZE
        sta pf_len
        lda #>REC_SIZE
        sta pf_len+1
        rts

rec_name:   .byte 10, "HIGHSCORES"
rec_defaults:
        .incbin "HIGHSCORES"     ; tools/records.py: the new disk's file
.assert * - rec_defaults = REC_SIZE, error, "HIGHSCORES: REC_SIZE bytes"
fr_off:
.repeat REC_N, K
        .byte 3 + REC_ENTRY * K
.endrepeat
fr_hund:  .byte 0, 100, 200
fr_txt_lo: .lobytes fr_menu_txt, fr_scores_txt, fr_help_txt, fr_entry_txt, fr_bonus_txt
fr_txt_hi: .hibytes fr_menu_txt, fr_scores_txt, fr_help_txt, fr_entry_txt, fr_bonus_txt
FR_ENTRY_T = 900
fr_time_lo: .lobytes 300, 240, 900, FR_ENTRY_T, 240    ; idle ticks (~1/30 s)
fr_time_hi: .hibytes 300, 240, 900, FR_ENTRY_T, 240
fr_kbd_txt: .byte "KEYBOARD"
fr_joy_txt: .byte "JOYSTICK"
fr_on_txt:  .byte "ON "
fr_off_txt: .byte "OFF"
fr_menu_txt:
        .byte 12, 6, "RETURN OR FIRE TO PLAY", 0
        .byte 14, 9, "J  CONTROLS", 0
        .byte 15, 9, "S  SOUND", 0
        .byte 16, 9, "H  HELP", 0
        .byte 17, 9, "ESC  QUIT", 0
        .byte 20, 4, "TOP", 0
        .byte 23, 6, "VERHILLE ARNAUD 2026  GPL-3", 0
        .byte $FF
fr_scores_txt:
        .byte 11, 14, "HIGH SCORES", 0
        .byte $FF
fr_help_txt:
        .byte 11, 2, "<- -> OR J L, STICK      MOVE", 0
        .byte 12, 2, "SPACE, APPLE, BUTTON     FIRE", 0
        .byte 13, 2, "HOLD FIRE: AUTOFIRE ONCE BOUGHT", 0
        .byte 14, 2, "CATCH $ COINS AND BONUSES:", 0
        .byte 15, 2, " S SPEED, B BULLETS, T TIME", 0
        .byte 16, 2, " E X T R A: AN EXTRA LIFE", 0
        .byte 17, 2, " ROCK, ? CARD: A SUB-GAME NEXT", 0
        .byte 18, 2, "A SHOP EVERY 4 LEVELS, A BOSS", 0
        .byte 19, 2, "EVERY 25. 100 LEVELS, THEN AGAIN.", 0
        .byte 21, 2, "S SOUND, ESC TITLE", 0
        .byte 23, 2, "WARGALAGA II IS NOT WARBLADE.", 0
        .byte $FF
fr_entry_txt:
        .byte 12, 14, "NEW RECORD!", 0
        .byte 14, 8, "SCORE", 0
        .byte 17, 8, "YOUR INITIALS:", 0
        .byte 20, 4, "LETTERS, <- ERASES, RETURN", 0
        .byte 21, 4, "STICK UP / DOWN, BUTTON", 0
        .byte $FF
fr_bonus_txt:
        .byte 11, 14, "GAME BONUSES", 0
        .byte 13, 4, "CASH LEFT", 0
        .byte 13, 22, "X 100", 0
        .byte 14, 4, "RANK", 0
        .byte 14, 22, "X 10000", 0
        .byte 15, 4, "PERFECTS", 0
        .byte 15, 22, "X 5000", 0
        .byte 17, 4, "BONUS POINTS", 0
        .byte 19, 4, "SCORE", 0
        .byte $FF
fr_err_txt:
        .byte 23, 2, "  SCORES NOT SAVED: DISK LOCKED?  ", 0
        .byte $FF
title_lz4:
        .incbin "title.lz4"

LZ4FH_HERE = 1                   ; (the decoder in this overlay)
.include "lz4fh.asm"
.include "file.asm"               ; (the records' file calls, here too)

.segment "BSS"
fr_why:   .res 1
fr_panel: .res 1
fr_t:     .res 2                ; idle ticks left
fr_btn:   .res 1
fr_lock:  .res 1                ; $80: a key held since the title opened
fr_e:     .res 1
fr_k:     .res 1
fr_lv:    .res 1
fr_pos:   .res 1
fr_name:  .res 3
fb_val:   .res 3                ; GAME BONUSES: an amount (BCD, low first)
fb_sum:   .res 3                ; their sum
rec_state: .res 1               ; HIGHSCORES read (or the defaults)
rec_dirty: .res 1               ; rec_buf differs from the file
rec_err:  .res 1                ; the last write's error (tests)
.segment "LOWBSS"
rec_buf:  .res REC_SIZE         ; the file (tools/records.py)
.code
