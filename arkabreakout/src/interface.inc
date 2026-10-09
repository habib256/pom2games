.import _mouse_init, _mouse_poll, _mouse_close
.import _mouse_slot, _mouse_x, _mouse_y, _mouse_buttons
.code
; Slot firmware owns Monitor ZP and screen holes. Transactions are protected
; from both the renderer and DOS, including RESET's exit hook.
mouse_start:
        lda #0
        sta mouse_context_native_mouse
        jsr mouse_context_capture_holes
        php
        sei
        jsr mouse_context_save_workspace
        jsr _mouse_init
        jsr mouse_context_restore_workspace
        plp
        lda _mouse_slot
        beq :+
        lda #2
        sta mode
:       rts
mouse_read:
        php
        sei
        jsr mouse_context_save_workspace
        jsr _mouse_poll
        jsr mouse_context_restore_workspace
        plp
        rts
mouse_shutdown:
        php
        sei
        jsr mouse_context_save_workspace
        jsr _mouse_close
        jsr mouse_context_restore_workspace
        plp
        rts

help:
        jsr clear_pages
        text help_title, 8, 24
        text help_e, 3, 48
        text help_s, 3, 64
        text help_c, 3, 80
        text help_d, 3, 96
        text help_l, 3, 112
        text help_p, 3, 128
        text help_combo, 3, 148
        text help_life, 3, 160
        text help_back, 6, 180
        jsr show_graphics
        jmp wait_key

; The title shows only play/menu. Detailed controls live on this HGR page.
title_menu:
@draw:  jsr clear_pages
        text escape_title, 11, 24
        text menu1, 10, 48
        text menu2, 5, 64
        text menu5, 5, 80
        text menu3, 5, 100
        text menu4, 5, 116
        text calibration_text, 5, 136
        text options_actions, 5, 156
        text options_back, 12, 180
        lda sound_muted
        beq @on
        text sound_off, 13, 156
        jmp @show
@on:    text sound_on, 13, 156
@show:  jsr show_graphics
title_menu_key:
        jsr wait_key
        cmp #'S'
        bne @return
        lda sound_muted
        eor #1
        sta sound_muted
        jmp title_menu
@return:cmp #'Q'
        beq @quit
        cmp #KC_ESC
        bne :+
        lda #0
:       pha
        jsr title
        pla
        rts
@quit:  jmp quit_game
.rodata
options_actions: .asciiz "S SOUND        Q QUIT"
options_back: .asciiz "ESC : TITLE"
.code

escape_menu:
        lda state
        sta menu_origin
        lda level
        cmp #60
        bcc :+
        lda #59
:       sta menu_sector
        jsr clear_menu_page
@key:   jsr menu_input
        cmp #KC_ESC
        beq @resume
        cmp #'R'
        beq @resume
        cmp #'Q'
        beq @quit
        cmp #'T'
        beq @title
        cmp #'S'
        beq @sound
        cmp #'A'
        beq @left
        cmp #KC_LEFT
        beq @left
        cmp #'D'
        beq @right
        cmp #KC_RIGHT
        beq @right
        cmp #KC_SPACE
        beq @start
        cmp #$0D
        beq @start
        jmp @key
@sound: lda sound_muted
        eor #1
        sta sound_muted
        jsr clear_menu_page
        jmp @key
@left:  lda menu_sector
        beq @key
        dec menu_sector
        jsr clear_menu_page
        jmp @key
@right: lda menu_sector
        cmp furthest
        bcs @key
        inc menu_sector
        jsr clear_menu_page
        jmp @key
@start: lda menu_sector
        sta level
        lda #1
        sta start_request
        rts
@quit:  jmp quit_game
@title: lda #0
        sta demo
        jsr title
        rts
@resume:
        lda menu_origin
        cmp #1
        bne @title
        ; Page 1 held the menu. Rebuild pages from simulation state only.
        jsr fetch_level
        jsr clear_pages
        jsr walls
        lda #$60
        sta page
        jsr walls
        lda #0
        sta page
        ldx #95
        lda #1
@dirty: sta dirty1,x
        sta dirty2,x
        dex
        bpl @dirty
        lda #96
        sta dirty_counts
        sta dirty_counts+1
        jsr hud_dirty
        jsr render
        jsr render
        rts

quit_game:
        lda furthest
        cmp record_data+4
        beq @exit
        sta record_data+4
        jsr records_save
@exit:  jmp apple2_exit

; Use page 1 for the menu, retain simulation state across the redraw.
clear_menu_page:
        jsr clear_pages
        text escape_title, 11, 24
        text escape_resume, 4, 56
        text escape_pick, 4, 76
        text escape_start, 4, 96
        text escape_sound, 4, 116
        text escape_title_key, 4, 136
        text escape_quit, 4, 156
        text escape_click, 4, 180
        jsr sector_preview
        lda #76
        sta ht_sl
        lda #22
        sta ht_col
        lda menu_sector
        clc
        adc #1
        ldx #0
@tens: cmp #10
        bcc @number
        sec
        sbc #10
        inx
        bne @tens
@number:pha
        txa
        clc
        adc #'0'
        jsr hgr_putc8
        pla
        clc
        adc #'0'
        jsr hgr_putc8
        lda sound_muted
        beq @on
        text sound_off, 22, 116
        jmp show_graphics
@on:    text sound_on, 22, 116
        jmp show_graphics

; Keyboard has priority; a mouse click selects the menu row. Sector clicks
; to the left/right of the screen select the previous/next unlocked board.
menu_input:
        jsr poll_key
        bne menu_input_done
        lda _mouse_slot
        beq menu_input_done
        jsr mouse_read
        lda _mouse_buttons
        and #$80
        cmp button_old
        sta button_old
        beq menu_input_none
        cmp #0
        beq menu_input_none
menu_click:
        lda _mouse_y
        sec
        sbc #100
        asl
        clc
        adc #32
        cmp #70
        bcc @resume
        cmp #90
        bcc @sector
        cmp #110
        bcc @start
        cmp #130
        bcc @sound
        cmp #150
        bcc @title
        lda #'Q'
        rts
@resume:lda #'R'
        rts
@sector:lda _mouse_x
        cmp #70
        lda #'A'
        bcc menu_input_done
        lda #'D'
        rts
@start: lda #$0D
        rts
@sound: lda #'S'
        rts
@title: lda #'T'
menu_input_done:  rts
menu_input_none:  lda #0
        rts

; Render packed cells directly: never change the live brick grid, score,
; dirty flags or progress while browsing, including across disk packs.
sector_preview:
        lda level
        pha
        lda menu_sector
        sta level
        jsr fetch_level
        pla
        sta level
        text level_name, 26, 104
        lda #48
        sta row
        lda #26
        sta col
        lda #0
        sta idx
@cell:  lda idx
        lsr
        tay
        lda (level_ptr),y
        ldx idx
        pha
        txa
        and #1
        bne @high
        pla
        and #15
        jmp @color
@high:  pla
        lsr
        lsr
        lsr
        lsr
@color: tax
        lda preview_colors,x
        sta paint
        ldx row
        ldy col
        lda #3
        sta scratch
@line:  lda hgr_lo,x
        sta ptr
        lda hgr_hi,x
        sta ptr+1
        lda paint
        sta (ptr),y
        inx
        dec scratch
        bne @line
        inc col
        lda col
        cmp #38
        bcc @next
        lda #26
        sta col
        lda row
        clc
        adc #6
        sta row
@next:  inc idx
        lda idx
        cmp #96
        bcc @cell
        rts
.rodata
preview_colors: .byte $00,$2a,$55,$3f,$00,$00,$00,$00
                .byte $00,$00,$00,$00,$00,$00,$00,$bf
.code

autopilot:
        lda frames+1
        cmp #9
        bcs @stop
        ldx difficulty
        lda lives
        cmp starting_lives,x
        bcc @stop
        lda ball_x
        sec
        sbc #12
        bcs :+
        lda #2
:       sta pad_x
        jsr clamp_pad
        lda #1
        sta ball_live
        rts
@stop:  lda #0
        sta demo
        sta idle
        sta idle+1
        jsr title
        rts
.rodata
help_title: .asciiz "ARKABREAKOUT - BONUS HELP"
help_e: .asciiz "E ENLARGE : A WIDER PADDLE"
help_s: .asciiz "S SLOW    : REDUCE BALL SPEED"
help_c: .asciiz "C CATCH   : HOLD THEN RELEASE"
help_d: .asciiz "D DISRUPT : THREE BALLS"
help_l: .asciiz "L LASER   : BUTTON/SPACE FIRES"
help_p: .asciiz "P PIERCE  : THROUGH HIT TILES"
help_combo: .asciiz "COMBO X2..X8 EVERY 3 TILES"
help_life: .asciiz "EXTRA LIFE EVERY 5000 POINTS"
help_back: .asciiz "PRESS A KEY TO RETURN"
escape_click: .asciiz "CLICK ROW / SECTOR LEFT-RIGHT"
escape_title: .asciiz "ARKABREAKOUT MENU"
escape_resume: .asciiz "R / ESC : RESUME"
escape_pick: .asciiz "A / D   : SECTOR"
escape_start: .asciiz "ENTER   : START SECTOR"
escape_sound: .asciiz "S       : SOUND"
escape_title_key: .asciiz "T       : TITLE"
escape_quit: .asciiz "Q       : QUIT TO DOS"
sound_on: .asciiz "ON "
sound_off: .asciiz "OFF"
