; ============================================================================
; title.inc -- title page, attract mode, demo rides
; ============================================================================
;   attract      the title (TITLE from the disk) with a blinking prompt;
;                after TITLE_SECONDS without a key: a demo ride, then the two
;                hall of fame pages, then the title again. A key or button 0
;                anywhere: the menu.
;   demo_step    in a demo race, instead of read_input: the next inputs of
;                the ride (C = 1: a key or the button stops the demo)
;   demo_end     a demo race is over: the hall of fame
;   music_tick   one tick (~1/60 s) of the playing tune, or a pause; the
;                title tune (tools/music.py, at the start of the TITLE file)
;                plays through tick_wait while the title is up
;   play_tune    A/Y = a jingle: played to its end
;
; The demo rides are tools/solver.py's proven rides (tests/solutions.txt,
; packed by tools/packtrack.py at the end of each track file, copied into
; demobuf by load_track; menu_data.inc lists the demo tracks): the physics is the
; model's bit for bit, so replaying the inputs from the start finishes the
; track exactly as the solver did.
; ============================================================================

TITLE_PROMPT  = 66              ; = tools/title.py (under the subtitle)
TITLE_SECONDS = 15
HOF_TICKS     = 180             ; x 2: each hall of fame page, ~6 s
DEMO_END_FRAMES = 90            ; after a demo's finish line

.segment "ZEROPAGE"
demo_ptr:  .res 2
mus_ptr:   .res 2               ; the note playing (hi 0: no tune)

.segment "BSS"
demo_left: .res 1               ; ticks left in the current run
mus_t:     .res 1               ; ticks of the note played
mus_loop:  .res 2               ; at the end, again from here (hi 0: stop)

.segment "DATA"                 ; (BSS is not cleared: these need a start value)
demo:      .byte 0              ; non-zero: this race is a demo
demo_next: .byte 0              ; next demo ride
titledir_t: .byte 0             ; TITLE's T/S list (dev/tools/dos33patch.py)
titledir_s: .byte 0

.segment "CODE"

attract:
        LDA     #0
        STA     demo
        JSR     title_show              ; the tune starts if the title loaded:
        LDA     #0                      ; played once, the demo when it ends
        STA     mus_loop+1
        LDA     mus_ptr+1
        STA     msel                    ; (no tune: TITLE_SECONDS)
        LDX     #TITLE_SECONDS * 2      ; the prompt on / off every 1/2 s
@blink: TXA
        PHA
        LSR     A
        LDA     #<msg_press
        LDY     #>msg_press
        BCC     @on
        LDA     #<msg_blank
        LDY     #>msg_blank
@on:    LDX     #13
        STX     ht_col
        LDX     #TITLE_PROMPT
        JSR     puts_at
        LDY     #30
        JSR     tick_wait
        TAY
        PLA
        TAX
        TYA
        BCS     @go
        DEX
        LDA     msel
        BEQ     @cnt
        LDA     mus_ptr+1               ; the tune is over: the demo
        BNE     @blink
        BEQ     @demo
@cnt:   TXA
        BNE     @blink
@demo:  JMP     demo_start
@go:    AND     #$7F                    ; H: the help page
        JSR     kbd_upcase
        CMP     #'H'
        BNE     @menu
        LDX     #0
        JSR     show_page
        JMP     attract
@menu:  JMP     to_menu

; title_read -- the TITLE file into LOADBUF: tune, text pages, picture.
; C = 1: disk error
title_read:
        LDA     titledir_t
        STA     rwts_track
        LDA     titledir_s
        STA     rwts_sector
        LDA     #>TSLBUF
        STA     rwts_tsl
        LDA     #>LOADBUF
        STA     rwts_page
        JMP     rwts_read_tslist

; show_page -- X = text page (0 help, 1 congratulations, tools/pages.py),
; read again from TITLE, on page 1; back on a key or the button
show_page:
        TXA
        PHA
        JSR     title_read
        PLA
        TAX
        BCS     @rts
        LDA     page_lo,X
        STA     sptr
        LDA     page_hi,X
        STA     sptr+1
        JSR     page1_text
        JSR     page_lines
@wait:  LDY     #0
        JSR     tick_wait
        BCC     @wait
@rts:   RTS

; page_lines -- print the lines at sptr: row, column, text, 0 ... $FF
page_lines:
@line:  LDY     #0
        LDA     (sptr),Y
        CMP     #$FF
        BEQ     @wait
        STA     ht_sl
        INY
        LDA     (sptr),Y
        STA     ht_col
        CLC
        LDA     sptr
        ADC     #2
        STA     ht_src_lo
        LDA     sptr+1
        ADC     #0
        STA     ht_src_hi
        JSR     hgr_puts8
        LDY     #1
@sk:    INY
        LDA     (sptr),Y
        BNE     @sk
        INY
        TYA
        CLC
        ADC     sptr
        STA     sptr
        BCC     @line
        INC     sptr+1
        BNE     @line
@wait:  RTS

; title_show -- page 1: the title picture, or the name if the disk fails
title_show:
        JSR     page1_text
        JSR     title_read
        BCS     @plain
        LDA     #<(LOADBUF+4)           ; after DOS's header: the tune,
        LDY     #>(LOADBUF+4)
        JSR     music_start
        LDA     #<PICTURE               ; then (after the text pages) the picture
        STA     lz4fh_src
        LDA     #>PICTURE
        STA     lz4fh_src+1
        LDA     #0
        STA     lz4fh_dst
        LDA     #$20
        STA     lz4fh_dst+1
        JMP     lz4fh_unpack
@plain: JSR     music_stop
        LDA     #<msg_title
        LDY     #>msg_title
        LDX     #16
        STX     ht_col
        LDX     #64
        JMP     puts_at

; tick_wait -- Y ticks of ~1/60 s (Y = 0: 256); C = 1 as soon as a key
; (strobe cleared, A = it) or button 0 (released) is pressed; C = 0 at the
; end, or as soon as the tune playing ends. Keeps nothing.
tick_wait:
@t:     TYA
        PHA
        LDA     mus_ptr+1               ; a tune before this tick
        PHA
        JSR     music_tick
        PLA
        BEQ     @nt
        LDA     mus_ptr+1               ; and none after: it ended (C = 0)
        BNE     @nt
        PLA
        CLC
        RTS
@nt:    PLA
        TAY
        LDA     KBD
        BMI     @key
        JSR     stick_button
        BCC     @n
        RTS
@n:     DEY
        BNE     @t
        CLC
        RTS
@key:   BIT     KBDSTRB
        SEC
        RTS

; demo_start -- the next demo ride, from the start of its track
demo_start:
        JSR     music_stop              ; (load_track overwrites the tune)
        LDX     demo_next
        LDA     #<demobuf               ; the ride comes with the track
        STA     demo_ptr
        LDA     #>demobuf
        STA     demo_ptr+1
        LDA     demo_track,X
        INX
        CPX     #NDEMOS
        BCC     @n
        LDX     #0
@n:     STX     demo_next
        LDX     #0
        STX     demo_left
        JSR     load_track
        BCS     demo_end                ; disk error: skip the ride
        LDA     #1
        STA     demo
        JMP     new_race

demo_end:
        LDA     #0
        STA     demo
        JSR     hof_page                ; A = 0: tracks 1-15
        JSR     hof_pause
        BCS     @menu
        LDA     #15
        JSR     hof_page
        JSR     hof_pause
        BCS     @menu
        JMP     attract
@menu:  JMP     to_menu

hof_pause:
        LDY     #HOF_TICKS
        JSR     tick_wait
        BCS     @rts
        LDY     #HOF_TICKS
        JMP     tick_wait
@rts:   RTS

; demo_step -- in_throttle / in_brake / in_lean of this tick. One run =
; count, then throttle / 4 (bits 5-6), brake (bit 7), lean + 8 (bits 0-4).
demo_step:
        LDA     KBD
        BMI     @key
        JSR     stick_button
        BCC     @in
        RTS
@in:    LDA     demo_left
        BNE     @same
        LDY     #0
        LDA     (demo_ptr),Y
        BEQ     @hold                   ; end of the ride: keep the inputs
        STA     demo_left
        INY
        LDA     (demo_ptr),Y
        PHA
        AND     #$1F
        SEC
        SBC     #LEAN_MAX
        STA     in_lean
        PLA
        ASL     A                       ; C = brake (bit 7)
        PHA
        LDA     #0
        ROL     A
        STA     in_brake
        PLA                             ; throttle / 4 now in bits 6-7
        LSR     A
        LSR     A
        LSR     A
        LSR     A
        AND     #$0C                    ; (throttle / 4) * 4
        STA     in_throttle
        CLC
        LDA     demo_ptr
        ADC     #2
        STA     demo_ptr
        BCC     @same
        INC     demo_ptr+1
@same:  DEC     demo_left
@hold:  CLC
        RTS
@key:   BIT     KBDSTRB
        SEC
        RTS

; music_start -- A/Y = a tune, from its first note, looping
music_start:
        STA     mus_ptr
        STA     mus_loop
        STY     mus_ptr+1
        STY     mus_loop+1
        LDA     #0
        STA     mus_t
        RTS

music_stop:
        LDA     #0
        STA     mus_ptr+1
        RTS

; play_tune -- A/Y = a tune, played once (muted: its length in silence)
play_tune:
        JSR     music_start
        LDA     #0
        STA     mus_loop+1
@n:     JSR     music_tick
        LDA     mus_ptr+1
        BNE     @n
        RTS

; music_tick -- one ~1/60 s tick: a slice of the note (the last tick of a
; note is silent), or a pause without a tune. Keeps nothing.
music_tick:
        LDA     mus_ptr+1
        BEQ     @wait
        LDY     #0
        LDX     mus_t
        INX
        TXA
        CMP     (mus_ptr),Y
        BEQ     @rest
        LDA     snd_on
        BEQ     @rest
        INY
        LDA     (mus_ptr),Y             ; half period (0: a rest)
        BEQ     @rest
        TAX
        INY
        LDA     (mus_ptr),Y             ; flips in a tick
        JSR     tone
        JMP     @next
@rest:  JSR     @wait
@next:  INC     mus_t
        LDY     #0
        LDA     mus_t
        CMP     (mus_ptr),Y
        BCC     @rts
        STY     mus_t                   ; the next note
        CLC
        LDA     mus_ptr
        ADC     #3
        STA     mus_ptr
        BCC     @n1
        INC     mus_ptr+1
@n1:    LDA     (mus_ptr),Y
        BNE     @rts
        LDA     mus_loop                ; the end: again, or stop
        STA     mus_ptr
        LDA     mus_loop+1
        STA     mus_ptr+1
@rts:   RTS
@wait:  LDA     #79
        JMP     WAIT

.import __MENUOVL_SIZE__
PICTURE = MENU_AT + __MENUOVL_SIZE__    ; tools/titlefile.py: after the menu
.segment "RODATA"
page_lo:   .byte <(LOADBUF + 4 + TUNE_LEN + PAGE_HELP), <(LOADBUF + 4 + TUNE_LEN + PAGE_CONGRATS)
page_hi:   .byte >(LOADBUF + 4 + TUNE_LEN + PAGE_HELP), >(LOADBUF + 4 + TUNE_LEN + PAGE_CONGRATS)
msg_press: .byte "PRESS ANY KEY", 0
msg_blank: .byte "             ", 0
msg_demo:  .byte "DEMO", 0
.segment "CODE"
