; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; hof_test.s -- standalone bench of the score and the hall of fame (lot 7)
; ============================================================================
; HOFTEST, loaded at $4000 by NEOHOF.SYSTEM (src/hof_boot.s) with the case
; records SCENE at $8000. The volume also holds NEOWILD.END (the module,
; src/hof.s assembled with HOF_BENCH, linked at $9600) and NEOWILD.HOF.
; The bench plays the game's part:
;   - the resident labels the module reads (won, dead, s_elap, s_health,
;     f_hmax, region_name, geo_path, MAP+22/+32/+33), filled from each case;
;   - goal_pct (returns the case's progress), overlay_load (records its
;     argument), module_restart and the exit hook bench_next;
;   - mli_call: the game's interface, plus a log of (command, result) pairs
;     and a one-shot fault (command, error, number of calls let through);
;   - module_end from src/hof_load.inc, exactly as INPUT runs it;
;   - the ProDOS bitmap protected like the game's (boot.s game_pages), and
;     the Applesoft zero page of the loader ($50-$FF), for the ROM floats;
;   - a copy of the loader fragment src/hof_menu.s (HOF_LOADER, buffer at
;     $2000 like STAGE, the loader's own READ block) for hm_load, hm_best and
;     hm_hall, drawn over a menu skeleton.
; Each case ends at `checkpoint`, where tests/test_hof.py reads the text page,
; the buffers and the log, then pokes dt_go.
; Case record (CASE_SIZE bytes): mode (0 end, 1 module, 2 loader), won,
; dead, level, region, kind, progress, s_elap[5], s_health[5], f_hmax[5],
; fault command, fault error, fault skip, region name[16], demo flag.
; ============================================================================
        .include "apple2.inc"
        .macpack longbranch
.export won, dead, s_elap, s_health, f_hmax, region_name, geo_path
.export mli_call, goal_pct, overlay_load, module_restart, bench_next, io_buffer
.export checkpoint, cp_resume, dt_go

MLI      = $BF00
DEVNUM   = $BF30
BITMAP   = $BF58
MAP      = $7000
CASES    = $8000
CASE_SIZE = 48
io_buffer = $BA00
LOG_MAX  = 64                   ; bytes: 32 (command, result) pairs

.segment "ZEROPAGE"
bench_zp: .res 4                ; HOF_ZP of the loader fragment
cp:       .res 2                ; current case record

.segment "CODE"
bench_start:
        cld
        ldx     #0              ; the loader's Applesoft zero page
:       lda     applesoft_hi,x
        sta     $50,x
        inx
        cpx     #$B0
        bne     :-
        bit     $C082           ; ROM in the language card space
        sta     STORE80OFF
        sta     COL80OFF
        sta     $C00E
        bit     TXTSET
        bit     LOWSCR
        lda     DEVNUM          ; geo_path = "/VOLUME/NEOWILD.GEO"
        sta     online+1
        jsr     MLI
        .byte   $C5             ; ON_LINE
        .word   online
        jcs     halt
        lda     volume
        and     #$0F
        jeq     halt
        sta     volume
        ldy     #1
        lda     #'/'
        sta     geo_path,y
        ldx     #0
:       iny
        lda     volume+1,x
        sta     geo_path,y
        inx
        cpx     volume
        bne     :-
        ldx     #0
:       iny
        lda     geo_name,x
        sta     geo_path,y
        inx
        cpx     #12
        bne     :-
        sty     geo_path
        ldx     #23             ; the game's protected pages
:       lda     BITMAP,x
        sta     saved_bitmap,x
        ora     game_pages,x
        sta     BITMAP,x
        dex
        bpl     :-
        lda     #<CASES
        sta     cp
        lda     #>CASES
        sta     cp+1
next_case:
        ldy     #CASE_SIZE-1
:       lda     (cp),y
        sta     case,y
        dey
        bpl     :-
        lda     case_mode
        jeq     all_done
        lda     case_won
        sta     won
        lda     case_dead
        sta     dead
        lda     case_level
        sta     MAP+22
        lda     case_region
        sta     MAP+32
        lda     case_kind
        sta     MAP+33
        ldx     #4
:       lda     case_elap,x
        sta     s_elap,x
        lda     case_health,x
        sta     s_health,x
        lda     case_hmax,x
        sta     f_hmax,x
        dex
        bpl     :-
        ldx     #15
:       lda     case_name,x
        sta     region_name,x
        dex
        bpl     :-
        lda     case_demo
        ora     demo
        sta     demo
        lda     case_fault
        sta     fault_cmd
        lda     case_fault+1
        sta     fault_code
        lda     case_fault+2
        sta     fault_skip
        lda     #0
        sta     mli_n
        sta     bench_flag
        sta     last_overlay
        ldx     #LOG_MAX-1
:       sta     mli_log,x
        dex
        bpl     :-
        lda     case_mode
        cmp     #2
        beq     loader_case
        tsx
        stx     bench_sp
        jmp     module_end      ; as INPUT does after `quit`

module_restart:                 ; module_end could not read NEOWILD.END
        lda     #2
        bne     after_module
bench_next:                     ; the module's exit
        lda     #1
after_module:
        sta     bench_flag
        ldx     bench_sp
        txs
        bit     $C082
        jsr     checkpoint
        jmp     advance

loader_case:
        lda     #1
        sta     bench_flag
        ldx     #23             ; the menu runs before the game protects
:       lda     BITMAP,x        ; its pages (STAGE = $2000 is free)
        pha
        lda     saved_bitmap,x
        sta     BITMAP,x
        pla
        sta     game_bitmap,x
        dex
        bpl     :-
        jsr     hm_load
        ldx     #23
:       lda     game_bitmap,x
        sta     BITMAP,x
        dex
        bpl     :-
        jsr     skeleton
        jsr     hm_best
        jsr     checkpoint      ; the menu with its best scores
        jsr     hm_hall
        jsr     checkpoint      ; the H screen
advance:
        clc
        lda     cp
        adc     #CASE_SIZE
        sta     cp
        bcc     :+
        inc     cp+1
:       jmp     next_case
all_done:
        lda     #3
        sta     bench_flag
        jsr     checkpoint
        lda     demo            ; the demo starts over
        jeq     all_done
        lda     #<CASES
        sta     cp
        lda     #>CASES
        sta     cp+1
        jmp     next_case
halt:   jmp     halt

; skeleton -- the menu rows the loader prints (tools/genmenu.py): "s NAME"
; at column 0 and "BEST -" at column 33 of rows 2, 5 ... 17.
skeleton:
        jsr     hm_clear
        lda     #1
        sta     sk_scen
@scen:  lda     sk_scen
        asl     a
        adc     sk_scen
        sbc     #0              ; row 3s - 1
        sta     sk_row
        ldy     #0
        jsr     hm_at
        lda     sk_scen
        ora     #'0'
        jsr     hm_char
        lda     #' '
        jsr     hm_char
        ldx     sk_scen
        lda     names_lo-1,x
        ldy     names_hi-1,x
        jsr     hm_print
        lda     sk_row
        ldy     #33
        jsr     hm_at
        lda     #<m_best
        ldy     #>m_best
        jsr     hm_print
        inc     sk_scen
        lda     sk_scen
        cmp     #7
        bne     @scen
        rts
sk_scen: .byte 0
sk_row:  .byte 0
m_best:  .byte "BEST -", 0

; checkpoint -- tests/test_hof.py reads memory here, then pokes dt_go.
; A demo case (tests/test_hof.py --demo-po) also goes on with any key.
checkpoint:
        lda     dt_go
        bne     cp_resume
        lda     demo
        beq     checkpoint
        lda     KBD
        bpl     checkpoint
        bit     KBDSTRB
cp_resume:
        lda     #0
        sta     dt_go
        rts

goal_pct:
        lda     case_progress
        rts
overlay_load:
        sta     last_overlay
        rts

; mli_call -- the game's interface (A = command, X/Y = parameters, C/A),
; logged; the case's fault replaces one call by its error.
mli_call:
        sta     mc_cmd
        stx     mc_parm
        sty     mc_parm+1
        cmp     fault_cmd
        bne     @real
        lda     fault_skip
        beq     @fail
        dec     fault_skip
        jmp     @real
@fail:  lda     #0              ; one shot
        sta     fault_cmd
        lda     fault_code
        sec
        bcs     mli_logged
@real:  jsr     MLI
mc_cmd: .byte   0
mc_parm: .word  0
mli_logged:
        php
        pha
        ldx     mli_n
        cpx     #LOG_MAX
        bcs     @full
        lda     mc_cmd
        sta     mli_log,x
        pla
        pha
        sta     mli_log+1,x
        inx
        inx
        stx     mli_n
@full:  pla
        plp
        rts

; The loader's copy of the fragment (boot.s integration).
HOF_ZP    = bench_zp
HOF_BUF   = $2000
HOF_MLI   = mli_call
HOF_IOBUF = io_buffer
HOF_PATH  = geo_path
HOF_READ_PARMS = bench_read
HOF_NAMES_LO = names_lo
HOF_NAMES_HI = names_hi
HOF_LOADER = 1
        .include "hof_menu.s"
bench_read: .byte 4, 0
        .word   0, 0, 0

HL_BENCH = 1
        .include "hof_load.inc"

names_lo: .byte <n1, <n2, <n3, <n4, <n5, <n6
names_hi: .byte >n1, >n2, >n3, >n4, >n5, >n6
; Menu order of the loader (tools/genmenu.py MENU_ORDER: the Sierra first).
menu_regions: .byte 2, 1, 3, 4, 5, 6
menu_rows: .byte 3, 2, 4, 5, 6, 7
n1: .byte "BRITISH COLUMBIA", 0
n2: .byte "SIERRA NEVADA", 0
n3: .byte "BURMA", 0
n4: .byte "NEW GUINEA", 0
n5: .byte "BOLIVIA", 0
n6: .byte "CHILE", 0
geo_name: .byte "/NEOWILD.GEO"
online: .byte   2, 0
        .word   volume

; Pages protected while the game runs (boot.s game_pages).
game_pages:
        .repeat 24, I
        .scope
        bits .set 0
        .repeat 8, J
        page .set I * 8 + J
        .if ((page >= $02) .and (page <= $03)) .or ((page >= $08) .and (page <= $57)) .or ((page >= $60) .and (page <= $B9)) .or (page = $BE)
        bits .set bits | ($80 >> J)
        .endif
        .endrep
        .byte   bits
        .endscope
        .endrep

; The zero page $50-$FF that the loader sets before `start` (boot.s), less
; the bench's own bytes at $E0-$E5 (set afterwards).
applesoft_hi:
        .byte   $00, $C0, $55, $52, $00, $0D, $8D, $0A, $00, $FF, $00, $FF, $00, $FF, $8D, $0A
        .byte   $00, $FF, $00, $FF, $00, $FF, $00, $01, $08, $9E, $0A, $9E, $0A, $9E, $0A, $00
        .byte   $96, $FF, $95, $00, $96, $D2, $00, $FF, $00, $81, $0A, $FF, $00, $00, $08, $FF
        .byte   $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $00, $00, $FF, $00, $FF, $00, $03
        .byte   $4C, $46, $E6, $FF, $00, $FF, $00, $FF, $00, $00, $00, $00, $00, $0D, $8D, $0A
        .byte   $55, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $8D, $0A, $9B, $0A, $9E
        .byte   $0A, $E6, $B8, $D0, $02, $E6, $B9, $AD, $9B, $0A, $C9, $3A, $B0, $0A, $C9, $20
        .byte   $F0, $EF, $38, $E9, $30, $38, $E9, $D0, $60, $80, $4F, $C7, $52, $FF, $00, $FF
        .byte   $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF
        .byte   $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF
        .byte   $00, $01, $00, $00, $00, $FF, $00, $FF, $F8, $FF, $00, $FF, $00, $FF, $00, $FF

; Game state read by the module.
won:      .byte 0
dead:     .byte 0
s_elap:   .res 5
s_health: .res 5
f_hmax:   .res 5
region_name: .res 16
geo_path: .res 40
volume:   .res 16
saved_bitmap: .res 24
game_bitmap:  .res 24
; Bench state (tests/test_hof.py).
dt_go:      .byte 0
demo:       .byte 0             ; 1 once a demo case ran: keys resume
bench_flag: .byte 0             ; 1 module ran / loader case, 2 module_restart, 3 done
bench_sp:   .byte 0
last_overlay: .byte 0
fault_cmd:  .byte 0
fault_code: .byte 0
fault_skip: .byte 0
mli_n:      .byte 0
mli_log:    .res LOG_MAX
case:
case_mode:  .byte 0
case_won:   .byte 0
case_dead:  .byte 0
case_level: .byte 0
case_region: .byte 0
case_kind:  .byte 0
case_progress: .byte 0
case_elap:  .res 5
case_health: .res 5
case_hmax:  .res 5
case_fault: .res 3
case_name:  .res 16
case_demo:  .byte 0
            .res CASE_SIZE - (* - case)
