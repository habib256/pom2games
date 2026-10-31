; ============================================================================
; shadowcast.asm -- Recursive shadowcasting field-of-view (Björn Bergström,
;                   RogueBasin 2002), display-agnostic 6502 implementation.
; ============================================================================
;
; Partitions the plane around the player into 8 octants. Each octant is
; processed by `cast_octant`, which scans rows of increasing depth and
; columns from outer (slope ≈ 1) to inner (slope = 0). Walls encountered
; mid-row narrow the visible cone for deeper rows via JSR-recursion. The
; result is mathematically symmetric — no slope artifacts, no coverage
; holes, every cell visible from the player iff the player is visible
; from it (within the radius).
;
; The library reads/writes nothing display-specific — it walks an abstract
; 1-byte-per-cell map and fires two caller-supplied callbacks per cell:
; one to mark visibility, one to test opacity. Use it for any grid-based
; fog-of-war: roguelikes (TMS9918, HGR, GT-6144), stealth games, board
; games with line-of-sight.
;
; ----------------------------------------------------------------------------
; Caller responsibilities -- declare these BEFORE `.include "shadowcast.asm"`
; ----------------------------------------------------------------------------
;
; Constants (scalar `.equ`-style):
;
;   SHADOW_COLS         = grid width  (1..127)  — playfield X dimension
;   SHADOW_ROWS         = grid height (1..127)  — playfield Y dimension
;
; Zero-page bytes (declare in your `.zeropage` block):
;
;   player_col          = player's grid X (0..SHADOW_COLS-1)
;   player_row          = player's grid Y (0..SHADOW_ROWS-1)
;   fov_r               = active radius (1..15)
;
; Subroutines (define in your CODE segment):
;
;   mark_visible_at_cur  = side-effect: mark cell (cur_x, cur_y) lit in your
;                          vis buffer. Caller may assume cur_x < SHADOW_COLS
;                          and cur_y < SHADOW_ROWS (the lib OOR-tests before
;                          calling). Clobbers A, Y; preserves X.
;
;   is_opaque_at_cur     = predicate: A = $01 (Z clear) iff cell at
;                          (cur_x, cur_y) blocks sight, else A = $00 (Z set).
;                          Walls AND opaque doors should both return $01.
;                          Clobbers A, Y; preserves X.
;
; Slopes (ROGUE, APPLE II): POM1 compared the slope fractions n / d by
; cross-multiplication (umul4). Every slope here is one of n / d with
; n in 0..15 and d in 1..15 (fov_r <= 7: 2c + 1, 2d + 1 <= 15), so each is
; kept as its RANK = how many of those 240 fractions are smaller: a < b iff
; rank a < rank b, a = b iff equal ranks (equal fractions, 1/3 and 3/9, get
; the same rank). The ranks of every cell's left / right slope are tables
; (sc_lrank / sc_rrank by 8 * depth + col): a cone test is one compare,
; with the very same outcomes as the products.
;
; ----------------------------------------------------------------------------
; Lib-owned ZP (allocated via `.ifndef` guard so callers can pre-alias
; if they need to share these slots with their own scratch — most don't).
; ----------------------------------------------------------------------------

; Two .ifndef guards: cur_x/cur_y often double as throwaway scratch in
; the rest of the project (the rogue's dagger animation reuses them),
; so the caller may pre-declare them in its own .zeropage. The cast_*
; / oct_* slots are private to the shadowcaster and almost nobody
; pre-declares them.
.ifndef cur_x
.zeropage
cur_x:           .res 1          ; cell currently being marked / opacity-tested
cur_y:           .res 1
.endif
.ifndef cast_depth
.zeropage
oct_xs:          .res 1          ; canonical (col, depth) → grid offset:
oct_xm:          .res 1          ;   cur_x = (src EOR m) + b, src = depth
oct_xb:          .res 1          ;   (s = 0) or col (s = 1), m = 0 / $FF (-),
oct_ys:          .res 1          ;   b = player_col - m (octant_* tables)
oct_ym:          .res 1
oct_yb:          .res 1
oct_idx:         .res 1          ; outer 0..7 octant counter
cast_depth:      .res 1          ; current row depth (1..fov_r)
cast_col:        .res 1          ; current col cursor inside row (depth..0)
cast_blocked:    .res 1          ; non-zero while inside a wall chain
cast_idx:        .res 1          ; 8 * depth + col: the slope tables' index
cast_start:      .res 1          ; live cone, high-slope edge (a rank, below)
cast_end:        .res 1          ; live cone, low-slope edge
cast_save:       .res 1          ; "new_start" — narrowed start that
                                 ;   takes effect at next wall→floor
cast_li:         .res 1          ; cast_idx of the last cell scanned
.endif

; ----------------------------------------------------------------------------
; Public entry: shadowcast_octants
; ----------------------------------------------------------------------------
; Casts the FOV cone from (player_col, player_row) over all 8 octants.
; The caller is responsible for:
;   - wiping its vis buffer beforehand (the lib doesn't know where the
;     buffer lives or how big it is)
;   - lighting the player's own cell (cast_octant starts at depth=1, so
;     the player's depth=0 cell is never marked by the lib)
;   - any post-pass cleanup (e.g. stripping pit reveals out of FOV)
;
; Reads:  player_col, player_row, fov_r
; Calls:  mark_visible_at_cur, is_opaque_at_cur (per cell, in-bounds only)
; Stack:  recursion ≤ fov_r levels, 9 B per frame, ~63 B peak at fov_r=7
; ----------------------------------------------------------------------------

.segment "CODE"

shadowcast_octants:
        LDA     #0
        STA     oct_idx
@oct_lp:
        LDX     oct_idx
        LDA     octant_xs,X
        STA     oct_xs
        LDA     octant_xm,X
        STA     oct_xm
        LDA     player_col
        SEC
        SBC     oct_xm          ; player_col - m (+1 when m = -1)
        STA     oct_xb
        LDA     octant_ys,X
        STA     oct_ys
        LDA     octant_ym,X
        STA     oct_ym
        LDA     player_row
        SEC
        SBC     oct_ym
        STA     oct_yb

        ; Initial cone: start = 1/1, end = 0/1, depth = 1.
        LDA     #1
        STA     cast_depth
        LDA     #SC_RANK_ONE
        STA     cast_start
        LDA     #0                      ; rank of 0/1
        STA     cast_end
        JSR     cast_octant

        INC     oct_idx
        LDA     oct_idx
        CMP     #8
        BCC     @oct_lp
        RTS


; ----------------------------------------------------------------------------
; cast_octant -- internal recursive shadowcast for one octant.
; Reads cast_depth / cast_start / cast_end (ranks) from ZP; iterates rows
; of increasing depth and inside each row scans cols from outer (col =
; depth, slope ≈ 1) to inner (col = 0, slope = 0). For each in-cone cell:
;   - mark visible
;   - if the cell is opaque (wall / door):
;       * floor → wall transition: recurse one row deeper with the cone
;         narrowed to (start, leftSlope) — the wall's high edge, which
;         is the steepest slope the wall occludes at deeper rows.
;       * cache rightSlope as cast_save ("new_start"). This is what
;         the row's `start` becomes if we cross back to floor later in
;         the same row.
;   - if the cell is floor and we just exited a wall chain, rewind
;     start to cast_save.
; If the row ends with cast_blocked still set (an unbroken wall chain
; across the cone tail), the routine returns — every deeper row is
; entirely shadowed.
; ----------------------------------------------------------------------------

cast_octant:
        ; --- Empty cone? if start <= end -> return.
        LDA     cast_end
        CMP     cast_start
        BCC     @row_lp                 ; end < start -> real cone
        RTS                             ; start <= end -> empty cone
@row_lp:
        LDA     cast_depth
        CMP     fov_r
        BEQ     @row_ok
        BCC     @row_ok                 ; depth < fov_r -> process row
        RTS                             ; depth > fov_r -> done with octant
@row_ok:
        ; --- Per-row state ---
        LDA     #0
        STA     cast_blocked
        LDA     cast_start
        STA     cast_save               ; "new_start" — initial value =
                                        ;   current start; updated as we
                                        ;   discover wall chains.
        LDA     cast_depth
        STA     cast_col                ; outer-most cell in row
        ASL
        ASL
        ASL
        ORA     cast_depth
        STA     cast_idx                ; 8 depth + col

@col_lp:
        ; --- the cell's slopes: leftSlope = (2c + 1) / (2d - 1), rightSlope
        ; = max(0, 2c - 1) / (2d + 1) (sc_lrank / sc_rrank). It is
        ; remembered (cast_li): a parent reads the rightSlope of the last
        ; cell its child scanned (POM1's order, kept). ---
        LDX     cast_idx
        STX     cast_li
        ; --- Cone test (a): if cast_start < rightSlope, skip cell.
        LDA     sc_rrank,X
        CMP     cast_start
        BEQ     @in_cone_a              ; equal: still in cone (boundary)
        BCC     @in_cone_a              ; rslope < start -> in cone
        JMP     @next_col               ; rslope > start -> too steep, skip
@in_cone_a:
        ; --- Cone test (b): if leftSlope < cast_end, break (past cone).
        LDA     cast_end
        CMP     sc_lrank,X
        BEQ     @in_cone_b              ; equal: keep
        BCC     @in_cone_b              ; end < lslope -> in cone
        JMP     @break_row              ; lslope < end -> past cone
@in_cone_b:
        ; --- Resolve cell to grid (cur_x, cur_y) and OOR-test. ---
        ; cur_x = player_col + col * xx + depth * xy (one term, +-1),
        ; cur_y likewise: (src EOR m) + b, both before the test as before.
        LDX     oct_ys
        LDA     cast_depth,X            ; depth (s = 0) or col (s = 1)
        EOR     oct_ym
        CLC
        ADC     oct_yb
        STA     cur_y
        LDX     oct_xs
        LDA     cast_depth,X
        EOR     oct_xm
        CLC
        ADC     oct_xb
        STA     cur_x
        CMP     #SHADOW_COLS
        BCS     @to_oor
        LDA     cur_y
        CMP     #SHADOW_ROWS
        BCC     @in_grid
@to_oor:
        JMP     @oor_cell
@in_grid:
        ; In-bounds: mark visible + check opacity.
        JSR     mark_visible_at_cur
        JSR     is_opaque_at_cur
        BEQ     @floor
        JMP     @cell_blocks            ; opaque → wall handling
@floor:

        ; --- Floor cell ---
        LDA     cast_blocked
        BNE     @rewind
        JMP     @next_col               ; not blocked -> just continue
@rewind:
        ; Wall→floor transition: rewind start to cast_save.
        LDA     #0
        STA     cast_blocked
        LDA     cast_save
        STA     cast_start
        JMP     @next_col

@cell_blocks:
        ; --- Wall cell ---
        LDA     cast_blocked
        BNE     @wall_extend            ; already in wall chain — just
                                        ; track new_start, no recursion.

        ; Floor → wall transition. Recurse one row deeper with cone
        ; (start, l_slope), then cache new_start = r_slope.
        LDA     #1
        STA     cast_blocked
        LDA     cast_depth
        CMP     fov_r
        BCS     @save_new_start         ; depth >= fov_r -> deepest row,
                                        ; nothing past the wall to scan.

        ; --- Save 9-byte frame, set up child params, recurse, restore.
        LDA     cast_depth
        PHA
        LDA     cast_col
        PHA
        LDA     cast_idx
        PHA
        LDA     cast_blocked
        PHA
        LDA     cast_save
        PHA
        LDA     cast_start
        PHA
        LDA     cast_end
        PHA

        LDX     cast_idx                ; cone narrowed to (start, lslope)
        LDA     sc_lrank,X
        STA     cast_end
        INC     cast_depth              ; child row = depth + 1

        JSR     cast_octant

        PLA
        STA     cast_end
        PLA
        STA     cast_start
        PLA
        STA     cast_save
        PLA
        STA     cast_blocked
        PLA
        STA     cast_idx
        PLA
        STA     cast_col
        PLA
        STA     cast_depth

@save_new_start:
@wall_extend:
        ; Cache rightSlope as new_start (latest wall in chain wins): the
        ; last scanned cell's (this one, or the child's last).
        LDX     cast_li
        LDA     sc_rrank,X
        STA     cast_save
        JMP     @next_col

@oor_cell:
        ; Treat off-grid as wall; runs the wall-state machine but skips
        ; mark_visible / opacity (the cell is unreachable anyway).
        LDA     cast_blocked
        BNE     @oor_extend
        LDA     #1
        STA     cast_blocked
@oor_extend:
        LDX     cast_li
        LDA     sc_rrank,X
        STA     cast_save

@next_col:
        LDA     cast_col
        BEQ     @col_done               ; col already 0 -> row scan done
        DEC     cast_col
        DEC     cast_idx
        JMP     @col_lp

@break_row:
@col_done:
        ; If the row ended while still inside a wall chain, every
        ; deeper row would be entirely shadowed by it -> return.
        LDA     cast_blocked
        BNE     @rt

        INC     cast_depth
        JMP     @row_lp
@rt:
        RTS


; ----------------------------------------------------------------------------
; Octant transforms (POM1's table, as source / sign per axis). Each octant
; maps canonical (col, depth) to a grid (dx, dy) offset from the player:
;     dx = col * xx + depth * xy,   dy = col * yx + depth * yy
; with exactly one nonzero (+-1) in {xx, xy} and in {yx, yy}:
;     xx  0  1 -1  0  0 -1  1  0      yx -1  0  0 -1  1  0  0  1
;     xy  1  0  0 -1 -1  0  0  1      yy  0 -1 -1  0  0  1  1  0
; octant_xs = 1 when the x term is col's (else depth's), octant_xm = $FF
; when it is negative; the same for y.
; ----------------------------------------------------------------------------
.assert cast_col = cast_depth + 1, error, "cast_depth,X: X = 0 depth, 1 col"
octant_xs:      .byte   0,    1,    1,    0,    0,    1,    1,    0
octant_xm:      .byte   0,    0,  $FF,  $FF,  $FF,  $FF,    0,    0
octant_ys:      .byte   1,    0,    0,    1,    1,    0,    0,    1
octant_ym:      .byte $FF,  $FF,  $FF,  $FF,    0,    0,    0,    0

; Slope ranks (see the header): SC_RANK n, d = how many n' / d' (n' 0..15,
; d' 1..15) are < n / d. sc_lrank / sc_rrank, by 8 * depth + col: the ranks
; of (2c + 1) / (2d - 1) and max(0, 2c - 1) / (2d + 1) (depth 0 unused).
.macro SC_RANK n, d
        sc_acc .set 0
        .repeat 16, nn
        .repeat 15, dd
        sc_acc .set sc_acc + ((nn) * (d) < (n) * (dd + 1))
        .endrepeat
        .endrepeat
        .byte   sc_acc
.endmacro
SC_RANK_ONE = 120               ; rank of 1/1: the n' < d', 1 + 2 + .. + 15

.segment "RODATA"
sc_lrank:
        .repeat 8, d
        .repeat 8, c
        .if d = 0
        .byte   0
        .else
        SC_RANK 2 * c + 1, 2 * d - 1
        .endif
        .endrepeat
        .endrepeat
sc_rrank:
        .repeat 8, d
        .repeat 8, c
        .if c = 0
        .byte   0
        .else
        SC_RANK 2 * c - 1, 2 * d + 1
        .endif
        .endrepeat
        .endrepeat
.segment "CODE"
