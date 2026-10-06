; ============================================================================
; chess_engine.asm -- core chess engine (separately-assembled module)
; ============================================================================
; Public symbols (see .export at end):
;   init_board          -- reset to starting position, side=white
;   piece_at            -- A = board[X], where X is a 0x88 square
;   apply_user_move     -- attempt the move (mv_from, mv_to, mv_promo)
;                          carry clear = success, carry set + A=err code = fail
;   in_check            -- A = nonzero if side_to_move's king is in check
;   game_status         -- A = 0 ongoing, 1 white-mate, 2 black-mate, 3 stalemate
;   toggle_side         -- side_to_move ^= COLOR_BLACK
;
; Public BSS (importzp / import):
;   board (256 B BSS)   -- 0x88 mailbox, only even-half occupied
;   side_to_move (BSS)  -- $00 white / $80 black
;   castling_rights, ep_square, halfmove_clock, fullmove_number
;   king_sq_white, king_sq_black
;   mv_from, mv_to, mv_promo, mv_flags  (input/output of apply_user_move)
;
; Notes:
;   - Supports: all 6 piece types, captures, promotion to queen, castling
;     (king- and queen-side, with right / occupancy / pass-through-check
;     validation in apply_castle_move) and en-passant capture (ep_square
;     tracking + MV_FLAG_ENPASSANT, removed in make_move).
;   - Check detection IS active: a move that leaves your own king in check
;     is rejected (ERR_KING_IN_CHECK).
;   - Stalemate / checkmate detection runs after every successful move via
;     a brute-force "any pseudo-legal move that leaves king safe" scan.
; ============================================================================

.include "chess_common.inc"
.include "chess_tables.inc"

; --- Public API symbols imported by variant code --------------------------
.export init_board
.export piece_at
.export apply_user_move
.export in_check
.export game_status
.export toggle_side
.export starting_position    ; re-export for variants that want to peek
.export piece_letters
; Internals exposed so variants can enumerate legal moves without duplicating
; the engine's machinery (POM1's Chess.asm used them for do_list_moves and
; do_hint; chess.s does not).
.export is_pseudo_legal
.export make_move
.export unmake_move

; --- BSS ------------------------------------------------------------------
.segment "BOARDST"
.export board
board:                  .res 128
.export side_to_move
side_to_move:           .res 1
.export castling_rights
castling_rights:        .res 1
.export ep_square
ep_square:              .res 1
.export halfmove_clock
halfmove_clock:         .res 1
.export fullmove_number
fullmove_number:        .res 1
.export king_sq_white
king_sq_white:          .res 1
.export king_sq_black
king_sq_black:          .res 1

; Move I/O (input from parser, output from gen during legality scan).
.export mv_from
mv_from:                .res 1
.export mv_to
mv_to:                  .res 1
.export mv_promo
mv_promo:               .res 1
.export mv_flags
mv_flags:               .res 1

; Saved state for unmake_move (single-level undo only — sufficient for
; HvH and depth=1 search; deepens to a stack in v1.2 when AI lands).
saved_captured:         .res 1      ; piece on `to` before move
saved_ep:               .res 1
saved_castling:         .res 1
saved_halfmove:         .res 1
saved_king_sq:          .res 1      ; king_sq for moving side, if king moved
scan_sq:                .res 1      ; board scan position (mat_recount)
mat_tot:                .res 2      ; material of white, black (mat_simple units)
saved_castle_rook_from: .res 1      ; rook origin square (for castling undo)
saved_castle_rook_to:   .res 1      ; rook destination square (for castling undo)
castle_passthru_save:   .res 1      ; saves king piece byte during pass-through test
castle_passthru_ksq:    .res 1      ; saves the king square cache meanwhile (NOT tmp:
                                    ; in_check's atk_* helpers use tmp as scratch)
                                    ; (in_check clobbers ce_piece, can't use that)

; --- AI / perft scratch ---
ai_scan_x:              .res 1      ; from-square iterator
ai_scan_y:              .res 1      ; to-square iterator
ai_best_from:           .res 1
ai_best_to:             .res 1
ai_best_flags:          .res 1      ; mv_flags for the best move (0, or a castle bit)
ai_best_score:          .res 1      ; signed 8-bit material score (primary)
ai_best_pos:            .res 1      ; positional score of the best move (tie-break)
cand_pos:               .res 1      ; positional score of the candidate under test
ai_best_mvvlva:         .res 1      ; (unused since v0.6 — kept for layout stability)
score_lo:               .res 1      ; evaluate_material output
perft_count_lo:         .res 1
perft_count_hi:         .res 1

; --- SMART-mode state (LFSR + strategy + SEE scratch) ---
ai_rng:                 .res 1      ; 8-bit LFSR (period 255). Seeded in init_board.
ai_strategy:            .res 1      ; AI_STRATEGY_NAIVE / _SMART
see_min_val:            .res 1      ; lowest attacker value found (find_min_attacker)
see_min_sq:             .res 1      ; that attacker's square
see_value:              .res 1      ; signed 8-bit net gain from see_estimate
see_victim:             .res 1      ; raw victim value (mat_simple lookup) for adjustment
see_mover:              .res 1      ; our piece byte at mv_to (cached for SEE)

.ifdef CHESS_SMART_EVAL
; Enriched-evaluation scratch (evaluate_positional pre-pass): pawn counts per
; file per colour + bishop counts, for doubled/isolated/open-file/bishop-pair.
wpf:                    .res 8      ; white pawns per file 0..7
bpf:                    .res 8      ; black pawns per file 0..7
wbishop:                .res 1
bbishop:                .res 1
.endif

; --- Compact undo (16 bytes; relies on unmake_move) ---
; After a successful user move, we copy the saved_* slots (which the engine
; uses for single-level undo) into user_saved_* so they survive subsequent
; game_status iterations. On 'U', restore saved_*, mv_*, side, fullmove
; from user_saved_* and call unmake_move.
user_mv_from:           .res 1
user_mv_to:             .res 1
user_mv_promo:          .res 1
user_mv_flags:          .res 1
user_saved_captured:    .res 1
user_saved_ep:          .res 1
user_saved_castling:    .res 1
user_saved_halfmove:    .res 1
user_saved_king_sq:     .res 1
user_saved_rook_from:   .res 1
user_saved_rook_to:     .res 1
user_saved_side:        .res 1
user_saved_fullmove:    .res 1
undo_avail:             .res 1      ; 1 if undo state is loaded

; --- Zero page scratch (caller-provided via standard zp.inc convention) ---
; chess_engine relies on tmp + tmp2 from dev/lib/apple2/zp.inc.
.importzp tmp, tmp2

; Local engine-only ZP (allocated in caller's ZEROPAGE segment).
.segment "ZEROPAGE"
ce_sq:          .res 1      ; current scan square
ce_dir:         .res 1      ; current direction offset
ce_target:      .res 1      ; target square being tested
ce_piece:       .res 1      ; piece-type at MOVE-GEN's from-square (set by caller)
.exportzp ce_piece          ; do_list_moves loads it before each is_pseudo_legal
ce_color:       .res 1      ; colour byte of moving side
ce_dirs_left:   .res 1      ; direction-table loop counter
ce_dir_ptr:     .res 1      ; index into knight_offsets / king_offsets etc.
ce_match:       .res 1      ; 1 if a pseudo-legal match for (mv_from,mv_to)
attacker_color: .res 1      ; colour byte of attacker (for is_attacked)
attacked_sq:    .res 1      ; square being tested for attack
ia_dir:         .res 1      ; is_attacked_runner: current ray offset
s_ply:          .res 1      ; search_node: current slot
s_leaf:         .res 1      ;   slot scored statically
s_cut:          .res 1      ;   root cut (root_cut)
s_val:          .res 1      ;   score scratch
gt_from:        .res 1      ; gen_targets: from square
gt_color:       .res 1      ;   colour of the moving piece
gt_base:        .res 1      ;   list start in tgt_buf
gt_end:         .res 1      ;   list end (one past the last entry)
gt_new:         .res 1      ;   square being inserted (gt_add)
gt_di:          .res 1      ;   direction index
gt_dend:        .res 1      ;   one past the last direction index
gt_dstep:       .res 1      ;   direction index step (sliders)
gt_dir:         .res 1      ;   current slide offset
gt_type:        .res 1      ;   piece type
gt_mode:        .res 1      ;   GT_UNSORTED / GT_MATERIAL (0 = sorted, all)

.export mv_from, mv_to, mv_promo, mv_flags  ; redeclare for textual cite

; Destination lists from gen_targets: root moves at GT_ROOT, each search
; slot at sn_base. BSS (not BOARDST: that page is nearly full).
SEARCH_PLIES = 3            ; search slots below the root (DEEP uses 2)
ROOT_SLOT    = SEARCH_PLIES ; p_* slot parking the root move
.segment "BSS"
tgt_buf:        .res 32 * (SEARCH_PLIES + 1)
ai_tend:        .res 1      ; end of the root list (gt_end is reused below)
ai_pass:        .res 1      ; root pass: 0 material moves, 1 others, AI_PASS_ALL
AI_PASS_ALL = 2
; search_node, per slot: from-square iterator, list index / end, best score,
; cut, legal-move-seen flag, pass.
n_from:         .res SEARCH_PLIES
n_idx:          .res SEARCH_PLIES
n_end:          .res SEARCH_PLIES
n_best:         .res SEARCH_PLIES
n_cut:          .res SEARCH_PLIES
n_found:        .res SEARCH_PLIES
n_pass:         .res SEARCH_PLIES   ; 0 = material moves, 1 = the others
n_stat:         .res SEARCH_PLIES   ; leaf: material as it stands
n_first:        .res SEARCH_PLIES   ; pass searched first
; save_ply / restore_ply: the move and make_move's undo slots, per slot.
p_from:         .res SEARCH_PLIES + 1
p_to:           .res SEARCH_PLIES + 1
p_flags:        .res SEARCH_PLIES + 1
p_promo:        .res SEARCH_PLIES + 1
p_cap:          .res SEARCH_PLIES + 1
p_ep:           .res SEARCH_PLIES + 1
p_castling:     .res SEARCH_PLIES + 1
p_half:         .res SEARCH_PLIES + 1
p_ksq:          .res SEARCH_PLIES + 1
p_crf:          .res SEARCH_PLIES + 1
p_crt:          .res SEARCH_PLIES + 1

; The engine code lives in its own segment so the linker can place it
; in the upper-bank ($E000-$EFFF) on stock 8 KB Apple-1 (Parmegiani's
; standard layout: 4 KB at $0000-$0FFF + 4 KB at $E000-$EFFF). Variant
; renderer code stays in the regular CODE segment in the lower bank.
.segment "ENGINE"

; ============================================================================
; init_board -- reset to starting position
; ============================================================================
; Clears the 0x88 board, copies starting_position[64] into the valid half,
; sets side_to_move=white, full castling rights, no ep square, king
; positions cached.
init_board:
        ; Zero entire 128-byte board first.
        LDX #$00
        TXA
@zlp:   STA board,X
        INX
        CPX #$80
        BNE @zlp

        ; Copy 64 squares from starting_position[] (rank-major) into the
        ; 0x88 board. starting_position[i] -> board[(i & $38) << 1 | (i & 7)]
        ; i.e. rank = i / 8 (0..7), file = i & 7. board_idx = rank*16 + file.
        LDX #$00            ; X = source index 0..63
@cplp:
        TXA
        LSR A
        LSR A
        LSR A               ; A = rank (0..7)
        ASL A
        ASL A
        ASL A
        ASL A               ; A = rank * 16
        STA tmp             ; tmp = rank * 16
        TXA
        AND #$07            ; A = file
        CLC
        ADC tmp             ; A = rank*16 + file
        TAY                 ; Y = 0x88 destination index
        LDA starting_position,X
        STA board,Y
        INX
        CPX #64
        BNE @cplp

        ; Initialise game state.
        LDA #SIDE_WHITE
        STA side_to_move
        LDA #(CR_WHITE_K | CR_WHITE_Q | CR_BLACK_K | CR_BLACK_Q)
        STA castling_rights
        LDA #$88            ; sentinel "no ep square"
        STA ep_square
        LDA #$00
        STA halfmove_clock
        LDA #$01
        STA fullmove_number
        ; King squares: white E1 = $04, black E8 = $74.
        LDA #$04
        STA king_sq_white
        LDA #$74
        STA king_sq_black

        ; Seed the 8-bit LFSR used by SMART-mode tie-break. Seeding only on
        ; init_board (not on every ai_play_move) lets the RNG state diverge
        ; through a game so AvA runs are non-deterministic by move 2-3.
        ; $AC is a fixed odd seed; the period-255 LFSR cycles through every
        ; non-zero value before repeating.
        LDA #$AC
        STA ai_rng

        ; Default strategy: SMART (1-ply + MVV-LVA + SEE + random tie-break).
        ; The 'D' command at the prompt cycles between NAIVE and SMART.
        LDA #AI_STRATEGY_SMART
        STA ai_strategy
        JMP mat_recount

; ============================================================================
; piece_at -- A = board[X]
; ============================================================================
; Cheap public read. X = 0x88 square. Caller checks (X & $88) first if needed.
piece_at:
        LDA board,X
        RTS

; ============================================================================
; toggle_side -- side_to_move ^= COLOR_BLACK
; ============================================================================
toggle_side:
        LDA side_to_move
        EOR #COLOR_BLACK
        STA side_to_move
        RTS

; ============================================================================
; apply_user_move -- attempt to make the move in (mv_from, mv_to, mv_promo)
; ============================================================================
; Input:
;   mv_from, mv_to: 0x88 squares
;   mv_promo: 0=no promotion, else PIECE_QUEEN/ROOK/BISHOP/KNIGHT
; Output:
;   carry clear = move was legal and applied; side_to_move toggled
;   carry set + A = error code:
;       1  empty source square
;       2  source piece is opponent's
;       3  pseudo-illegal move for this piece type
;       4  move would leave own king in check
;       5  reserved (ERR_NOT_IMPL — no longer returned; en-passant and
;          castling are implemented. Kept for the text-IO error switch.)
; (ERR_* constants now live in chess_common.inc so all TUs see them as
;  immediate compile-time values without 8-bit range warnings.)

apply_user_move:
        ; 0. Castling? Special validation path before generic checks.
        LDA mv_flags
        AND #(MV_FLAG_CASTLE_K | MV_FLAG_CASTLE_Q)
        BEQ @noc
        JMP apply_castle_move
@noc:
        ; 1. Validate from-square is on the board and has a piece of our colour.
        LDA mv_from
        AND #OFFBOARD_MASK
        BEQ @from_ok
        LDA #ERR_BAD_GEOMETRY
        SEC
        RTS
@from_ok:
        LDX mv_from
        LDA board,X
        BNE @has_piece
        LDA #ERR_EMPTY
        SEC
        RTS
@has_piece:
        STA ce_piece                ; full byte (colour + type)
        AND #COLOR_MASK
        CMP side_to_move
        BEQ @color_ok
        LDA #ERR_WRONG_COLOR
        SEC
        RTS
@color_ok:
        ; 2. Validate to-square is on board and not occupied by our own piece.
        LDA mv_to
        AND #OFFBOARD_MASK
        BEQ @to_ok
        LDA #ERR_BAD_GEOMETRY
        SEC
        RTS
@to_ok:
        LDX mv_to
        LDA board,X
        BEQ @dest_empty
        AND #COLOR_MASK
        CMP side_to_move
        BNE @dest_empty
        ; same colour on destination → illegal
        LDA #ERR_BAD_GEOMETRY
        SEC
        RTS
@dest_empty:

        ; 3. Pseudo-legal geometry check (does THIS piece type allow from→to?)
        JSR is_pseudo_legal
        BCC @geom_ok
        LDA #ERR_BAD_GEOMETRY
        SEC
        RTS
@geom_ok:
        ; 4. Make the move tentatively, check own-king-not-in-check, undo if so.
        JSR make_move
        JSR in_check
        BEQ @move_safe
        ; King left in check → undo and reject.
        JSR unmake_move
        LDA #ERR_KING_IN_CHECK
        SEC
        RTS
@move_safe:
        ; Move is legal. Snapshot for user-undo BEFORE toggling side
        ; (save_user_state captures side_to_move = mover, fullmove pre-bump).
        JSR save_user_state
        JSR toggle_side
        ; Bump fullmove if it's now white's turn (we just played black).
        LDA side_to_move
        BNE @done
        INC fullmove_number
@done:
        CLC
        RTS

; ============================================================================
; apply_castle_move -- validate and execute a castling move
; ============================================================================
; mv_from, mv_to set by parser to king's start and destination.
; mv_flags has CASTLE_K or CASTLE_Q.
;
; Validation:
;   1. Right granted in castling_rights for this side+side
;   2. Squares between king and rook are empty
;   3. King not currently in check
;   4. King does not pass through an attacked square (intermediate)
;   5. King's destination is not attacked (handled by post-move in_check)
; castle_try -- validate the castling move in mv_flags (CASTLE_K/Q) + mv_from/
; mv_to and, on success, MAKE it on the board WITHOUT the permanent bookkeeping
; (no save_user_state / toggle_side / fullmove bump). CC = legal and now made —
; the caller must either finalise it (apply_castle_move) or revert it with
; unmake_move (the move enumerators ai_play_move / game_status / perft1). CS =
; illegal, A = error code, board left unchanged. Factored out of the old
; apply_castle_move so the AI can actually consider castling as a candidate.
castle_try:
        ; --- 1. Right granted? ---
        LDA mv_flags
        AND #MV_FLAG_CASTLE_K
        BEQ @qs_check
        ; Kingside requested
        LDA side_to_move
        BNE @ks_b
        LDA castling_rights
        AND #CR_WHITE_K
        BEQ @no_right
        JMP @check_squares
@ks_b:  LDA castling_rights
        AND #CR_BLACK_K
        BEQ @no_right
        JMP @check_squares
@qs_check:
        LDA side_to_move
        BNE @qs_b
        LDA castling_rights
        AND #CR_WHITE_Q
        BEQ @no_right
        JMP @check_squares
@qs_b:  LDA castling_rights
        AND #CR_BLACK_Q
        BEQ @no_right
@no_right:
        LDA #ERR_BAD_GEOMETRY
        SEC
        RTS

@check_squares:
        ; --- 2. Squares between king and rook are empty ---
        LDA mv_flags
        AND #MV_FLAG_CASTLE_K
        BEQ @qs_squares
        ; KS: check mv_from+1 and mv_from+2 (F and G files)
        LDX mv_from
        INX
        LDA board,X
        BNE @blocked
        INX
        LDA board,X
        BNE @blocked
        JMP @check_in_check
@qs_squares:
        ; QS: check mv_from-1, -2, -3 (D, C, B files)
        LDX mv_from
        DEX
        LDA board,X
        BNE @blocked
        DEX
        LDA board,X
        BNE @blocked
        DEX
        LDA board,X
        BNE @blocked
        JMP @check_in_check
@blocked:
        LDA #ERR_BAD_GEOMETRY
        SEC
        RTS

@check_in_check:
        ; --- 3. King not currently in check ---
        JSR in_check
        BEQ @check_passthru
        LDA #ERR_KING_IN_CHECK
        SEC
        RTS

@check_passthru:
        ; --- 4. King does not pass through attacked square ---
        ; intermediate = (mv_from + mv_to) / 2  (since they're 2 apart on same rank)
        LDA mv_from
        CLC
        ADC mv_to
        LSR A
        STA ce_target           ; intermediate square

        ; Save the king piece byte in a BSS slot (NOT ce_piece — in_check
        ; clobbers ce_piece while iterating attackers).
        LDX mv_from
        LDA board,X
        STA castle_passthru_save
        LDA #$00
        STA board,X
        LDX ce_target
        LDA castle_passthru_save
        STA board,X

        LDA side_to_move
        BNE @pt_b
        LDA king_sq_white
        STA castle_passthru_ksq
        LDA ce_target
        STA king_sq_white
        JSR in_check
        STA tmp2
        LDA castle_passthru_ksq
        STA king_sq_white
        JMP @pt_restore
@pt_b:
        LDA king_sq_black
        STA castle_passthru_ksq
        LDA ce_target
        STA king_sq_black
        JSR in_check
        STA tmp2
        LDA castle_passthru_ksq
        STA king_sq_black
@pt_restore:
        ; Restore board: clear intermediate, put king back at mv_from.
        LDX ce_target
        LDA #$00
        STA board,X
        LDX mv_from
        LDA castle_passthru_save
        STA board,X
        ; Decision
        LDA tmp2
        BEQ @do_castle_for_real
        LDA #ERR_KING_IN_CHECK
        SEC
        RTS

@do_castle_for_real:
        ; --- 5. Execute the castle (make_move handles both pieces) ---
        JSR make_move
        ; Verify final king position not in check (paranoia — squares should
        ; have been cleared by checks above, but a sliding attack on the
        ; destination is still possible if the rook itself was in the way).
        JSR in_check
        BEQ @castle_safe
        JSR unmake_move
        LDA #ERR_KING_IN_CHECK
        SEC
        RTS
@castle_safe:
        CLC                     ; castle is legal and now made on the board
        RTS

; apply_castle_move -- the real (user/AI) castling move: validate+make via
; castle_try, then the permanent bookkeeping. Entered from apply_user_move.
apply_castle_move:
        JSR castle_try
        BCS @cfail              ; illegal — A already holds the error, CS set
        JSR save_user_state
        JSR toggle_side
        LDA side_to_move
        BNE @cdone
        INC fullmove_number
@cdone:
        CLC
@cfail:
        RTS

; try_one_castle -- A = MV_FLAG_CASTLE_K or _Q. Sets mv_from/mv_to/mv_flags for
; the side to move (king e1/e8, king-dest = from +/-2) and tail-calls castle_try.
; Returns castle_try's result: CC = legal + made (caller must unmake_move), CS =
; not available. Used by the enumerators to fold castling into move generation.
try_one_castle:
        STA mv_flags
        PHA                     ; remember which side (K vs Q)
        LDA #$00
        STA mv_promo
        LDA side_to_move
        BNE @black
        LDA #$04                ; white king e1
        JMP @setfrom
@black: LDA #$74                ; black king e8
@setfrom:
        STA mv_from
        PLA
        AND #MV_FLAG_CASTLE_K
        BEQ @qs
        LDA mv_from             ; kingside: king moves +2 (e->g)
        CLC
        ADC #$02
        STA mv_to
        JMP castle_try
@qs:    LDA mv_from             ; queenside: king moves -2 (e->c)
        SEC
        SBC #$02
        STA mv_to
        JMP castle_try

; ============================================================================
; is_pseudo_legal -- does the from→to move match this piece type's pattern?
; ============================================================================
; Input: mv_from, mv_to set; ce_piece = piece at from (full byte).
; Output: carry clear = pseudo-legal, carry set = no.
; Sets ce_match=1 if pseudo-legal.
is_pseudo_legal:
        LDA #$00
        STA ce_match
        LDA ce_piece
        AND #PIECE_MASK
        ; Dispatch by piece type.
        CMP #PIECE_PAWN
        BNE @not_p
        JMP psl_pawn
@not_p: CMP #PIECE_KNIGHT
        BNE @not_n
        JMP psl_knight
@not_n: CMP #PIECE_BISHOP
        BNE @not_b
        JMP psl_bishop
@not_b: CMP #PIECE_ROOK
        BNE @not_r
        JMP psl_rook
@not_r: CMP #PIECE_QUEEN
        BNE @not_q
        JMP psl_queen
@not_q: CMP #PIECE_KING
        BNE @bad
        JMP psl_king
@bad:   SEC
        RTS

; --- pawn ------------------------------------------------------------------
; White pawns move +$10, capture +$0F / +$11. Black pawns move -$10,
; capture -$11 / -$0F. Initial double push from rank 2 (white) or 7 (black).
psl_pawn:
        ; Determine forward step.
        LDA ce_piece
        AND #COLOR_MASK
        BEQ @white_pawn
        ; Black pawn: forward = -$10.
        LDA #$F0            ; -16 in two's complement
        STA tmp
        ; Capture diagonals: -$11 and -$0F
        LDA #$EF
        STA tmp2            ; left capture (file-1)
        ; right capture computed inline below
        JMP @check_pawn_dir
@white_pawn:
        LDA #$10
        STA tmp
        LDA #$0F
        STA tmp2            ; left capture (file-1)
@check_pawn_dir:
        ; Compute mv_from + tmp = single push square; compare to mv_to.
        LDA mv_from
        CLC
        ADC tmp
        CMP mv_to
        BNE @try_double
        ; Single push: destination must be empty.
        LDX mv_to
        LDA board,X
        BNE @bad_p          ; blocked
        ; Promotion check: if rank is 1 (black) or 8 (white), require mv_promo.
        ; (For v0.1 we auto-promote to queen if user didn't supply.)
        JSR maybe_promote
        CLC
        RTS
@try_double:
        ; Double push: only from starting rank, both intermediate and dest empty.
        LDA ce_piece
        AND #COLOR_MASK
        BEQ @wd
        ; Black double push: from rank 7 (mv_from in $60..$67) → -$20
        LDA mv_from
        AND #$70
        CMP #$60
        BNE @try_capture_pawn
        LDA mv_from
        SEC
        SBC #$20
        CMP mv_to
        BNE @try_capture_pawn
        ; Intermediate (mv_from + tmp = mv_from - $10) must be empty
        LDA mv_from
        CLC
        ADC tmp
        TAX
        LDA board,X
        BNE @bad_p
        ; Destination must be empty
        LDX mv_to
        LDA board,X
        BNE @bad_p
        CLC
        RTS
@wd:    ; White double push: from rank 2 (mv_from in $10..$17) → +$20
        LDA mv_from
        AND #$70
        CMP #$10
        BNE @try_capture_pawn
        LDA mv_from
        CLC
        ADC #$20
        CMP mv_to
        BNE @try_capture_pawn
        LDA mv_from
        CLC
        ADC tmp
        TAX
        LDA board,X
        BNE @bad_p
        LDX mv_to
        LDA board,X
        BNE @bad_p
        CLC
        RTS
@try_capture_pawn:
        ; Capture diagonals
        LDA mv_from
        CLC
        ADC tmp2            ; left capture
        CMP mv_to
        BEQ @cap
        ; Right capture: tmp2 + 2 (= -$0F for black, $11 for white)
        LDA mv_from
        CLC
        ADC tmp2
        CLC
        ADC #$02
        CMP mv_to
        BEQ @cap
@bad_p: SEC
        RTS
@cap:   ; Destination must contain an enemy piece, OR be the en-passant square.
        LDX mv_to
        LDA board,X
        BNE @cap_ok
        ; Empty destination — check en-passant.
        LDA mv_to
        CMP ep_square
        BNE @bad_p_ep
        ; En-passant capture: tag the move so make_move removes the
        ; adjacent pawn.
        LDA mv_flags
        ORA #MV_FLAG_ENPASSANT
        STA mv_flags
        JMP @cap_ok_ep
@bad_p_ep:
        SEC
        RTS
@cap_ok:
        ; Normal capture.
@cap_ok_ep:
        JSR maybe_promote
        CLC
        RTS

; If pawn lands on rank 1 or 8 and mv_promo == 0, force queen promotion.
maybe_promote:
        LDA mv_to
        AND #$70
        CMP #$00
        BEQ @do
        CMP #$70
        BEQ @do
        RTS
@do:    LDA mv_promo
        BNE @keep
        LDA #PIECE_QUEEN
        STA mv_promo
@keep:  RTS

; --- knight ----------------------------------------------------------------
psl_knight:
        ; Iterate 8 knight offsets, check if any equals (mv_to - mv_from).
        LDA mv_to
        SEC
        SBC mv_from
        STA tmp                 ; signed delta
        LDX #$08
@kl:    LDA knight_offsets-1,X
        CMP tmp
        BEQ @kok
        DEX
        BNE @kl
        SEC
        RTS
@kok:   CLC
        RTS

; --- bishop / rook / queen / king (sliding helpers) ----------------------
psl_bishop:
        LDA #<bishop_offsets
        STA ce_dir_ptr
        LDA #4
        STA ce_dirs_left
        JMP slide_check

psl_rook:
        LDA #<rook_offsets
        STA ce_dir_ptr
        LDA #4
        STA ce_dirs_left
        JMP slide_check

psl_queen:
        ; Queen = rook + bishop. Try rook first.
        JSR psl_rook
        BCC @ok
        JMP psl_bishop
@ok:    RTS

psl_king:
        ; King: any of 8 king_offsets, single step.
        LDA mv_to
        SEC
        SBC mv_from
        STA tmp
        LDX #$08
@kl:    LDA king_offsets-1,X
        CMP tmp
        BEQ @ok
        DEX
        BNE @kl
        SEC
        RTS
@ok:    CLC
        RTS

; slide_check: scan ce_dirs_left directions starting at offset table
; (low byte) ce_dir_ptr (must be in same page as bishop_offsets/rook_offsets).
; For each direction, walk from mv_from until off-board, an enemy/own piece,
; or mv_to is hit. Carry clear if mv_to reachable through empty squares
; (last square may be empty or any opponent piece — own-piece filter happened
; earlier in apply_user_move so we needn't recheck).
slide_check:
        LDX #$00
@dloop:
        ; Load offset for direction X.
        STX tmp2                ; preserve dir index across the @step walk (TAX below)
        ; Read tables[base + X] directly, forking by table low byte.
        LDA ce_dir_ptr
        CMP #<bishop_offsets
        BEQ @use_bishop
        LDA rook_offsets,X
        JMP @gotdir
@use_bishop:
        LDA bishop_offsets,X
@gotdir:
        STA ce_dir
        ; Walk from mv_from along ce_dir until we hit mv_to or a blocker.
        LDA mv_from
        STA ce_sq
@step:
        LDA ce_sq
        CLC
        ADC ce_dir
        STA ce_sq
        AND #OFFBOARD_MASK
        BNE @next_dir       ; off-board → try next direction
        LDA ce_sq
        CMP mv_to
        BEQ @found
        ; Square not yet target — must be empty to continue sliding.
        TAX
        LDA board,X
        BEQ @step           ; empty → keep stepping
        ; Blocked by some piece (not the target) → next direction.
@next_dir:
        LDX tmp2
        INX
        CPX ce_dirs_left
        BNE @dloop
        SEC
        RTS
@found: CLC
        RTS

; ============================================================================
; gen_targets -- destination squares of the piece on square X
; ============================================================================
; Walks the piece's own directions instead of testing all 64 squares with
; is_pseudo_legal. Input: X = from square (a piece of the side to move),
; Y = list base (GT_ROOT, or sn_base for a search slot), gt_mode:
;   0             every target, ascending -- the order the old from x to scan
;                 visited them, so the root meets moves (and steps the LFSR on
;                 ties) exactly as before
;   GT_UNSORTED   any order (search nodes: the order changes no score)
;   GT_MATERIAL   only targets that can change the material: captures, pawn
;                 diagonals (en passant) and pushes onto the last rank
; Output: tgt_buf[base .. gt_end-1]. Own-colour squares are left out.
; Knight / bishop / rook / queen / king entries are pseudo-legal as listed.
; Pawn entries are the 4 candidates (push, double push, 2 captures): the
; caller still runs is_pseudo_legal on them (rank, emptiness, en passant,
; promotion). Castling is not listed (try_one_castle). Clobbers A, X, Y.
GT_ROOT  = 0
GT_PLY0  = 32                   ; a queen has at most 27 targets
GT_KING  = 8                    ; gt_offsets: knight 0, king 8, pawns 16 / 20
GT_BPAWN = 20
GT_UNSORTED = $80               ; gt_mode bits
GT_MATERIAL = $40

gen_targets:
        STX gt_from
        STY gt_base
        STY gt_end              ; empty list
        LDA board,X
        AND #COLOR_MASK
        STA gt_color
        LDA board,X
        AND #PIECE_MASK
        STA gt_type
        TAX
        LDA gt_first-1,X        ; gt_offsets range for this piece type
        STA gt_di
        LDA gt_last-1,X
        STA gt_dend
        CPX #PIECE_PAWN
        BNE @notp
        BIT gt_color
        BPL gt_leap             ; white pawn
        LDA #GT_BPAWN           ; black pawn: its own 4 steps
        STA gt_di
        LDA #GT_BPAWN+4
        STA gt_dend
        BNE gt_leap             ; always
@notp:  CPX #PIECE_KNIGHT
        BEQ gt_leap
        CPX #PIECE_KING
        BEQ gt_leap
        ; Bishop / rook / queen: slide along the king steps. Rook = even
        ; entries (N E S W), bishop = odd (diagonals), queen = all 8.
        LDA gt_step-PIECE_BISHOP,X
        STA gt_dstep
@dir:   LDX gt_di
        LDA gt_offsets+GT_KING,X
        STA gt_dir
        LDA gt_from
@ray:   CLC
        ADC gt_dir
        TAX
        AND #OFFBOARD_MASK
        BNE @ndir               ; off the board
        LDA board,X
        BEQ @empty
        EOR gt_color
        BPL @ndir               ; own piece: stop before it
        TXA                     ; enemy piece: take it, then stop
        JSR gt_add
        JMP @ndir
@empty: BIT gt_mode
        BVS @pass               ; material only: an empty square never is
        TXA
        JSR gt_add
@pass:  TXA
        JMP @ray
@ndir:  LDA gt_di
        CLC
        ADC gt_dstep
        STA gt_di
        CMP gt_dend
        BCC @dir
        RTS

; Knight, king, pawn: one step per gt_offsets entry.
gt_leap:
@l:     LDX gt_di
        LDA gt_from
        CLC
        ADC gt_offsets,X
        TAX
        AND #OFFBOARD_MASK
        BNE @next
        LDA board,X
        BEQ @empty
        EOR gt_color
        BPL @next               ; own piece
@add:   TXA
        JSR gt_add
@next:  INC gt_di
        LDA gt_di
        CMP gt_dend
        BCC @l
        RTS
@empty: BIT gt_mode
        BVC @add
        LDA gt_type             ; material only: an empty square counts for a
        CMP #PIECE_PAWN         ;   pawn diagonal (en passant) or a push onto
        BNE @next               ;   the last rank (promotion)
        LDY gt_di
        LDA gt_offsets,Y
        AND #$0F
        BNE @add                ; diagonal
        TXA
        AND #$70
        BEQ @add                ; rank 1
        CMP #$70
        BEQ @add                ; rank 8
        BNE @next               ; always

; gt_add -- add square A to the list tgt_buf[gt_base..gt_end), in ascending
; order unless gt_mode has GT_UNSORTED. Keeps X.
gt_add:
        STA gt_new
        LDY gt_end
        BIT gt_mode
        BMI @put                ; unsorted: append
@shift: CPY gt_base
        BEQ @put
        LDA tgt_buf-1,Y
        CMP gt_new
        BCC @put                ; smaller entry below: insert here
        STA tgt_buf,Y
        DEY
        JMP @shift
@put:   LDA gt_new
        STA tgt_buf,Y
        INC gt_end
        RTS

; gt_check -- set up move tgt_buf[Y] from mv_from (ce_piece = its piece).
; CC = pseudo-legal (pawn candidates go through is_pseudo_legal), CS = not.
gt_check:
        LDA tgt_buf,Y
        STA mv_to
        LDA #$00
        STA mv_promo
        STA mv_flags
        LDA ce_piece
        AND #PIECE_MASK
        CMP #PIECE_PAWN
        BEQ @pawn
        CLC
        RTS
@pawn:  JMP is_pseudo_legal

; gt_offsets ranges per piece type (pawn .. king; a black pawn is patched to
; GT_BPAWN in gen_targets) and the slide step (bishop, rook, queen).
gt_offsets:
        .byte $1F, $21, $0E, $12, $E1, $DF, $F2, $EE    ;  0 knight
        .byte $10, $11, $01, $F1, $F0, $EF, $FF, $0F    ;  8 king: N NE E SE S SW W NW
        .byte $0F, $10, $11, $20                        ; 16 white pawn
        .byte $E0, $EF, $F0, $F1                        ; 20 black pawn
; Leapers index gt_offsets directly; sliders index its king block (0..7).
gt_first: .byte 16, 0, 1, 0, 0, GT_KING
gt_last:  .byte 20, 8, 8, 8, 8, GT_KING+8
gt_step:  .byte 2, 2, 1

; ============================================================================
; make_move -- apply the move (mv_from, mv_to, mv_promo, mv_flags) to the board
; ============================================================================
; Saves enough state for unmake_move (single-level undo).
; Does NOT toggle side_to_move (apply_user_move does that after legality OK).
;
; Handles:
;   - normal moves + captures + promotion
;   - en-passant capture (mv_flags bit MV_FLAG_ENPASSANT)
;   - castling (mv_flags bits MV_FLAG_CASTLE_K / Q)
;   - ep_square tracking (set after pawn double push, cleared otherwise)
;   - castling_rights updates (king move, rook move from corner, rook captured)
make_move:
        ; --- 1. Save state for undo ---
        LDX mv_to
        LDA board,X
        STA saved_captured
        LDA ep_square
        STA saved_ep
        LDA castling_rights
        STA saved_castling
        LDA halfmove_clock
        STA saved_halfmove
        LDA #$88
        STA saved_king_sq

        ; --- 2. Castling? Branch to specialised handler. ---
        LDA mv_flags
        AND #(MV_FLAG_CASTLE_K | MV_FLAG_CASTLE_Q)
        BEQ @normal
        JMP do_castle

@normal:
        ; --- 3. Pre-move bookkeeping for king/rook (castling rights) ---
        LDX mv_from
        LDA board,X
        STA tmp                 ; tmp = moving piece (full byte)
        AND #PIECE_MASK
        CMP #PIECE_KING
        BNE @not_king_move
        ; King is moving — save king_sq, update, clear both rights for this side
        LDA side_to_move
        BNE @bkm
        LDA king_sq_white
        STA saved_king_sq
        LDA mv_to
        STA king_sq_white
        ; Clear white castling rights
        LDA castling_rights
        AND #($FF ^ (CR_WHITE_K | CR_WHITE_Q))
        STA castling_rights
        JMP @not_king_move
@bkm:   LDA king_sq_black
        STA saved_king_sq
        LDA mv_to
        STA king_sq_black
        LDA castling_rights
        AND #($FF ^ (CR_BLACK_K | CR_BLACK_Q))
        STA castling_rights
@not_king_move:
        ; If a rook is moving from one of the corner squares, clear that
        ; side's castling right.
        LDA tmp
        AND #PIECE_MASK
        CMP #PIECE_ROOK
        BNE @not_rook_move
        LDA mv_from
        CMP #$00            ; A1
        BNE @nrm1
        LDA castling_rights
        AND #($FF ^ CR_WHITE_Q)
        STA castling_rights
        JMP @not_rook_move
@nrm1:  CMP #$07            ; H1
        BNE @nrm2
        LDA castling_rights
        AND #($FF ^ CR_WHITE_K)
        STA castling_rights
        JMP @not_rook_move
@nrm2:  CMP #$70            ; A8
        BNE @nrm3
        LDA castling_rights
        AND #($FF ^ CR_BLACK_Q)
        STA castling_rights
        JMP @not_rook_move
@nrm3:  CMP #$77            ; H8
        BNE @not_rook_move
        LDA castling_rights
        AND #($FF ^ CR_BLACK_K)
        STA castling_rights
@not_rook_move:
        ; If captured piece is a rook on a corner, clear that side's right.
        LDA saved_captured
        BEQ @nocap_corner
        AND #PIECE_MASK
        CMP #PIECE_ROOK
        BNE @nocap_corner
        LDA mv_to
        CMP #$00
        BNE @ncc1
        LDA castling_rights
        AND #($FF ^ CR_WHITE_Q)
        STA castling_rights
        JMP @nocap_corner
@ncc1:  CMP #$07
        BNE @ncc2
        LDA castling_rights
        AND #($FF ^ CR_WHITE_K)
        STA castling_rights
        JMP @nocap_corner
@ncc2:  CMP #$70
        BNE @ncc3
        LDA castling_rights
        AND #($FF ^ CR_BLACK_Q)
        STA castling_rights
        JMP @nocap_corner
@ncc3:  CMP #$77
        BNE @nocap_corner
        LDA castling_rights
        AND #($FF ^ CR_BLACK_K)
        STA castling_rights
@nocap_corner:

        ; --- 4. Move the piece, with optional promotion ---
        LDX mv_from
        LDA #$00
        STA board,X             ; clear from
        LDA mv_promo
        BEQ @no_promo
        ; Promotion: piece type becomes mv_promo
        LDA tmp
        AND #COLOR_MASK
        ORA mv_promo
        STA tmp
@no_promo:
        LDX mv_to
        LDA tmp
        STA board,X

        ; --- 5. En-passant capture: also clear the captured pawn ---
        LDA mv_flags
        AND #MV_FLAG_ENPASSANT
        BEQ @no_ep_cap
        ; Captured pawn sits on the same file as mv_to but the rank where
        ; the moving pawn started this turn (i.e., one rank back from mv_to
        ; in the moving side's perspective).
        LDA side_to_move
        BNE @epb
        ; White captures black: pawn is at mv_to - $10
        LDA mv_to
        SEC
        SBC #$10
        TAX
        LDA board,X
        STA saved_captured      ; record for unmake (overrides earlier $00)
        LDA #$00
        STA board,X
        JMP @no_ep_cap
@epb:
        ; Black captures white: pawn is at mv_to + $10
        LDA mv_to
        CLC
        ADC #$10
        TAX
        LDA board,X
        STA saved_captured
        LDA #$00
        STA board,X
@no_ep_cap:

        ; --- 5b. Material totals (evaluate_material) ---
        LDA saved_captured
        BEQ @no_mat_cap
        JSR mat_take            ; captured piece leaves its side's total
@no_mat_cap:
        LDA mv_promo
        BEQ @no_mat_promo
        LDA tmp                 ; the promoted piece joins, the pawn leaves
        JSR mat_give
        LDA tmp
        AND #COLOR_MASK
        ORA #PIECE_PAWN
        JSR mat_take
@no_mat_promo:

        ; --- 6. Update ep_square ---
        ; Set if this was a pawn double push, else clear.
        LDA tmp
        AND #PIECE_MASK
        CMP #PIECE_PAWN
        BNE @ep_clear
        ; Compute |delta|. White double push: mv_to - mv_from = $20.
        ; Black double push: mv_from - mv_to = $20.
        LDA mv_to
        SEC
        SBC mv_from
        CMP #$20
        BEQ @ep_set
        LDA mv_from
        SEC
        SBC mv_to
        CMP #$20
        BNE @ep_clear
@ep_set:
        ; ep_square = (mv_from + mv_to) / 2
        CLC
        LDA mv_from
        ADC mv_to
        LSR A
        STA ep_square
        JMP @ep_done
@ep_clear:
        LDA #$88
        STA ep_square
@ep_done:

        ; --- 7. halfmove clock (50-move rule) ---
        LDA saved_captured
        BNE @reset_hm
        LDA tmp
        AND #PIECE_MASK
        CMP #PIECE_PAWN
        BEQ @reset_hm
        INC halfmove_clock
        RTS
@reset_hm:
        LDA #$00
        STA halfmove_clock
        RTS

; ============================================================================
; do_castle -- execute a validated castling move
; ============================================================================
; Called from make_move when mv_flags has CASTLE_K or CASTLE_Q set.
; Assumes apply_user_move has already validated:
;   - the right is granted
;   - the squares between king and rook are empty
;   - king not in check before the move
;   - king does not pass through an attacked square
;
; mv_from = king's current square (E1=$04 or E8=$74)
; mv_to   = king's destination (G1=$06/G8=$76 KS, C1=$02/C8=$72 QS)
;
; Saves enough for unmake_move (rook from/to noted in saved_castle_rook_*).
do_castle:
        ; Save king's position for undo.
        LDA mv_from
        STA saved_king_sq

        ; Move the king
        LDX mv_from
        LDA board,X
        STA tmp                 ; the king
        LDA #$00
        STA board,X
        LDX mv_to
        LDA tmp
        STA board,X

        ; Determine rook from/to and update king_sq.
        LDA mv_flags
        AND #MV_FLAG_CASTLE_K
        BEQ @qs
        ; Kingside: rook from H-file (col 7) to F-file (col 5).
        LDA side_to_move
        BNE @ksb
        ; White kingside: H1=$07 -> F1=$05, king to G1=$06
        LDA mv_to
        STA king_sq_white
        LDX #$07
        LDA board,X
        LDY #$05
        STA board,Y
        LDA #$00
        STA board,X
        LDA #$07                ; rook from
        STA saved_castle_rook_from
        LDA #$05                ; rook to
        STA saved_castle_rook_to
        JMP @done
@ksb:
        ; Black kingside: H8=$77 -> F8=$75, king to G8=$76
        LDA mv_to
        STA king_sq_black
        LDX #$77
        LDA board,X
        LDY #$75
        STA board,Y
        LDA #$00
        STA board,X
        LDA #$77
        STA saved_castle_rook_from
        LDA #$75
        STA saved_castle_rook_to
        JMP @done
@qs:
        ; Queenside: rook from A-file (col 0) to D-file (col 3).
        LDA side_to_move
        BNE @qsb
        ; White queenside: A1=$00 -> D1=$03, king to C1=$02
        LDA mv_to
        STA king_sq_white
        LDX #$00
        LDA board,X
        LDY #$03
        STA board,Y
        LDA #$00
        STA board,X
        LDA #$00
        STA saved_castle_rook_from
        LDA #$03
        STA saved_castle_rook_to
        JMP @done
@qsb:
        ; Black queenside: A8=$70 -> D8=$73, king to C8=$72
        LDA mv_to
        STA king_sq_black
        LDX #$70
        LDA board,X
        LDY #$73
        STA board,Y
        LDA #$00
        STA board,X
        LDA #$70
        STA saved_castle_rook_from
        LDA #$73
        STA saved_castle_rook_to
@done:
        ; Clear both castling rights for the moving side.
        LDA side_to_move
        BNE @cb
        LDA castling_rights
        AND #($FF ^ (CR_WHITE_K | CR_WHITE_Q))
        STA castling_rights
        JMP @hm
@cb:    LDA castling_rights
        AND #($FF ^ (CR_BLACK_K | CR_BLACK_Q))
        STA castling_rights
@hm:    ; Castling resets ep_square but does NOT reset halfmove (it counts
        ; as a non-pawn, non-capture move).
        LDA #$88
        STA ep_square
        INC halfmove_clock
        RTS

; ============================================================================
; unmake_move -- restore state saved by the most recent make_move
; ============================================================================
unmake_move:
        ; Castling? Special path.
        LDA mv_flags
        AND #(MV_FLAG_CASTLE_K | MV_FLAG_CASTLE_Q)
        BEQ @normal
        JMP undo_castle

@normal:
        ; Restore moving piece to from-square. If promotion happened,
        ; the original piece type was a pawn — restore the pawn.
        LDX mv_to
        LDA board,X
        STA tmp                 ; current piece on to-square
        LDA mv_promo
        BEQ @no_unp
        LDA tmp                 ; promoted piece leaves, the pawn comes back
        JSR mat_take
        LDA tmp
        AND #COLOR_MASK
        ORA #PIECE_PAWN
        STA tmp
        JSR mat_give
@no_unp:
        LDX mv_from
        LDA tmp
        STA board,X
        ; Clear to-square first (default).
        LDX mv_to
        LDA #$00
        STA board,X

        ; En-passant capture: restore captured pawn to its original square.
        LDA mv_flags
        AND #MV_FLAG_ENPASSANT
        BEQ @no_ep_undo
        LDA side_to_move
        BNE @epb
        ; White ep: pawn was at mv_to - $10
        LDA mv_to
        SEC
        SBC #$10
        TAX
        LDA saved_captured
        STA board,X
        JMP @restore_state
@epb:
        ; Black ep: pawn was at mv_to + $10
        LDA mv_to
        CLC
        ADC #$10
        TAX
        LDA saved_captured
        STA board,X
        JMP @restore_state
@no_ep_undo:
        ; Normal capture (or empty): restore captured piece on to-square.
        LDX mv_to
        LDA saved_captured
        STA board,X
@restore_state:
        LDA saved_captured      ; captured piece rejoins its side's total
        BEQ @no_mat_cap
        JSR mat_give
@no_mat_cap:
        ; Restore game state.
        LDA saved_ep
        STA ep_square
        LDA saved_castling
        STA castling_rights
        LDA saved_halfmove
        STA halfmove_clock
        ; Restore king square if king moved.
        LDA saved_king_sq
        CMP #$88
        BEQ @nok
        LDA side_to_move
        BNE @bk
        LDA saved_king_sq
        STA king_sq_white
        RTS
@bk:    LDA saved_king_sq
        STA king_sq_black
@nok:   RTS

; ============================================================================
; undo_castle -- reverse the castling move
; ============================================================================
undo_castle:
        ; Move the king back from mv_to to mv_from.
        LDX mv_to
        LDA board,X
        STA tmp
        LDA #$00
        STA board,X
        LDX mv_from
        LDA tmp
        STA board,X
        ; Restore king_sq.
        LDA side_to_move
        BNE @bk
        LDA saved_king_sq
        STA king_sq_white
        JMP @rook
@bk:    LDA saved_king_sq
        STA king_sq_black
@rook:  ; Move the rook back from saved_castle_rook_to to saved_castle_rook_from.
        LDX saved_castle_rook_to
        LDA board,X
        STA tmp
        LDA #$00
        STA board,X
        LDX saved_castle_rook_from
        LDA tmp
        STA board,X
        ; Restore castling_rights, ep, halfmove.
        LDA saved_castling
        STA castling_rights
        LDA saved_ep
        STA ep_square
        LDA saved_halfmove
        STA halfmove_clock
        RTS

; ============================================================================
; in_check -- is the side_to_move king attacked by the other side?
; ============================================================================
; Returns A = nonzero if our king is attacked, A = 0 if safe.
; Z flag matches A.
in_check:
        LDA side_to_move
        BNE @bk
        LDA king_sq_white
        STA attacked_sq
        LDA #COLOR_BLACK
        STA attacker_color
        JMP is_attacked_runner
@bk:    LDA king_sq_black
        STA attacked_sq
        LDA #SIDE_WHITE
        STA attacker_color
        ; fall through

; is_attacked_runner: is attacked_sq attacked by a piece of attacker_color?
; Returns A = 0 (no) or 1 (yes), Z set accordingly. Looks outward from the
; square -- pawn and knight and king steps, then the 8 rays up to the first
; piece -- instead of scanning the board for attackers. Keeps ce_piece, tmp,
; tmp2, mv_* and the search iterators; clobbers X, Y and ia_dir.
; A board byte EOR attacker_color equals the bare piece type exactly when the
; piece has the attacker's colour (an empty square gives $80 or $00 -- never
; a piece type).
is_attacked_runner:
        ; Pawns: a white pawn attacks up (+$0F / +$11), so it sits at
        ; attacked_sq - $0F / - $11; a black one at + $0F / + $11.
        LDX #$00
        LDA attacker_color
        BEQ @pw
        LDX #$02
@pw:    LDA attacked_sq
        CLC
        ADC ia_pawn,X
        TAY
        AND #OFFBOARD_MASK
        BNE @pn
        LDA board,Y
        EOR attacker_color
        CMP #PIECE_PAWN
        BEQ @hit
@pn:    TXA
        LSR A                   ; second entry done?
        BCS @kn
        INX
        BNE @pw                 ; always
        ; Knights (entries 0-7) then king (8-15): both step sets are symmetric.
@kn:    LDX #$0F
@kl:    LDA attacked_sq
        CLC
        ADC gt_offsets,X
        TAY
        AND #OFFBOARD_MASK
        BNE @kx
        LDA board,Y
        EOR attacker_color
        CMP ia_leaper,X
        BEQ @hit
@kx:    DEX
        BPL @kl
        ; Rays: N NE E SE S SW W NW. The first piece met attacks if it is a
        ; queen, or a rook on an even ray / a bishop on an odd one.
        LDX #$07
@ray:   LDA gt_offsets+GT_KING,X
        STA ia_dir
        LDA attacked_sq
@step:  CLC
        ADC ia_dir
        TAY
        AND #OFFBOARD_MASK
        BNE @rx
        LDA board,Y
        BNE @piece
        TYA
        JMP @step
@piece: EOR attacker_color
        CMP #PIECE_QUEEN
        BEQ @hit
        CMP ia_slider,X
        BEQ @hit
@rx:    DEX
        BPL @ray
        LDA #$00                ; not attacked
        RTS
@hit:   LDA #$01                ; attacked
        RTS

ia_pawn:   .byte $F1, $EF, $0F, $11     ; white attacker, black attacker
ia_leaper: .byte PIECE_KNIGHT, PIECE_KNIGHT, PIECE_KNIGHT, PIECE_KNIGHT
           .byte PIECE_KNIGHT, PIECE_KNIGHT, PIECE_KNIGHT, PIECE_KNIGHT
           .byte PIECE_KING, PIECE_KING, PIECE_KING, PIECE_KING
           .byte PIECE_KING, PIECE_KING, PIECE_KING, PIECE_KING
ia_slider: .byte PIECE_ROOK, PIECE_BISHOP, PIECE_ROOK, PIECE_BISHOP
           .byte PIECE_ROOK, PIECE_BISHOP, PIECE_ROOK, PIECE_BISHOP

; ============================================================================
; game_status -- 0 ongoing, 1 white-mate, 2 black-mate, 3 stalemate
; ============================================================================
; Looks for any legal move of the side to move (gen_targets + own-king-safe
; test), castling included. Uses ai_scan_* and the GT_ROOT list: not callable
; from inside ai_play_move.
;
; Returns A = status code, Z reflects A.
game_status:
        ; Try every move of the side to move until one is legal.
        LDA #$00
        STA ai_scan_x
@floop:
        LDX ai_scan_x
        TXA
        AND #OFFBOARD_MASK
        BNE @nextf
        LDA board,X
        BEQ @nextf
        AND #COLOR_MASK
        CMP side_to_move
        BNE @nextf
        STX mv_from
        LDA board,X
        STA ce_piece
        LDY #GT_ROOT
        LDA #$00
        STA gt_mode             ; every target, ascending
        JSR gen_targets
        LDA #GT_ROOT
        STA ai_scan_y           ; index into tgt_buf
@tloop:
        LDY ai_scan_y
        CPY gt_end
        BCS @nextf
        JSR gt_check            ; clears mv_promo / mv_flags
        BCS @nextt
        JSR make_move
        JSR in_check
        BNE @bad
        ; Found a legal move → game ongoing.
        JSR unmake_move
        LDA #$00
        RTS
@bad:   JSR unmake_move
@nextt: INC ai_scan_y
        JMP @tloop
@nextf: INC ai_scan_x
        BNE @floop
        ; No NORMAL legal move was found. Castling isn't produced by the
        ; (from,to) scan, so a castle could still be the only legal move — test
        ; both before declaring mate/stalemate, or a castle-only position would
        ; be a false terminal.
        LDA #MV_FLAG_CASTLE_K
        JSR try_one_castle
        BCC @gs_castle_ok
        LDA #MV_FLAG_CASTLE_Q
        JSR try_one_castle
        BCS @gs_no_move
@gs_castle_ok:
        JSR unmake_move     ; revert the castle that try_one_castle made
        LDA #$00            ; a legal move exists → game ongoing
        RTS
@gs_no_move:
        ; No legal move at all → mate or stalemate.
        JSR in_check
        BEQ @stale
        ; Checkmate: side_to_move loses. White-mate=1 means white is mated.
        LDA side_to_move
        BNE @bm
        LDA #$01            ; white in checkmate
        RTS
@bm:    LDA #$02            ; black in checkmate
        RTS
@stale: LDA #$03
        RTS

; ============================================================================
; evaluate_material -- A = (our material - their material), signed 8-bit
; ============================================================================
; Simple material count, scaled to fit in signed 8-bit:
;   pawn=1, knight=3, bishop=3, rook=5, queen=9, king=0 (always equal).
; Returned in score_lo (BSS). Range +/-39 for normal positions. Read from the
; running totals mat_tot (white, black) instead of a board scan.
;
; "Our" = side_to_move at evaluation time.
.export evaluate_material
.export score_lo
evaluate_material:
        LDA side_to_move
        BNE @black
        LDA mat_tot
        SEC
        SBC mat_tot+1
        STA score_lo
        RTS
@black: LDA mat_tot+1
        SEC
        SBC mat_tot
        STA score_lo
        RTS

; mat_tot upkeep: make_move / unmake_move adjust it for captures and
; promotions; init_board (and anything else that sets up a board) calls
; mat_recount.
.export mat_recount
mat_recount:
        LDA #$00
        STA mat_tot
        STA mat_tot+1
        STA scan_sq
@l:     LDX scan_sq
        TXA
        AND #OFFBOARD_MASK
        BNE @n
        LDA board,X
        BEQ @n
        JSR mat_give
@n:     INC scan_sq
        BPL @l                  ; squares $00-$7F
        RTS

; mat_give / mat_take -- add / remove piece A (full byte) to / from its
; side's total. Clobber A, X, Y.
mat_give:
        JSR mat_split
        LDA mat_tot,X
        CLC
        ADC mat_simple,Y
        STA mat_tot,X
        RTS
mat_take:
        JSR mat_split
        LDA mat_tot,X
        SEC
        SBC mat_simple,Y
        STA mat_tot,X
        RTS
; A = piece byte -> X = 0 white / 1 black, Y = piece type.
mat_split:
        TAY
        ASL A                   ; C = colour bit
        LDA #$00
        ROL A
        TAX
        TYA
        AND #PIECE_MASK
        TAY
        RTS

; Compact material table (signed 8-bit safe sums):
; index 0..7 (NONE, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, ?)
mat_simple:
        .byte 0, 1, 3, 3, 5, 9, 0, 0

; cdist -- "distance from the edge" per file/rank index: a pyramid peaking at
; the centre files/ranks. Centralisation of a square = cdist[file] + cdist[rank].
cdist:
        .byte 0, 1, 2, 3, 3, 2, 1, 0

; ============================================================================
; evaluate_positional -- A = (our positional - their positional), signed 8-bit.
; ============================================================================
; A small, material-independent score: every piece earns its centralisation
; (cdist[file]+cdist[rank]); pawns additionally earn 2x their advance toward
; promotion (white = rank, black = 7-rank). "Our" = side_to_move. It is used
; ONLY as a tie-break between material-equal moves (see consider_move), so it
; can never outweigh material or a tactic — it just gives the search a sense of
; progress (develop, centralise, push passed pawns), which is what stops a won
; endgame stalling at the move cap.
; v0.7 piece-square logic (still a tie-break only). Per piece type:
;   PAWN   : 2*advance + cdist[file]        (push + hold central files)
;   KNIGHT : 2*centr                        (loves the centre, hates the rim)
;   BISHOP : centr
;   ROOK   : +4 on the 7th rank, else 0
;   QUEEN  : centr>>1                        (mild; don't roam out early)
;   KING   : -centr                          (SAFETY: central king is exposed)
; Scratch: tmp=piece byte, tmp2=working value, ce_target=rank, ce_dir=advance,
;   ce_dir_ptr=cdist[file], ce_dirs_left=cdist[rank]. These ce_* are re-set by
;   the reply search (best_reply_eval) before any later use, so clobbering is safe.
; Enriched-eval bonuses (pawn-equivalent-ish; small so material still dominates
; -- evaluate_positional stays a TIE-BREAK). Tuned modest to avoid 8-bit overflow.
EP_BISHOP_PAIR = 4
EP_DOUBLED_PEN = 2
EP_ISO_PEN     = 2
EP_ROOK_OPEN   = 3
EP_SHIELD_BON  = 2

evaluate_positional:
.ifdef CHESS_SMART_EVAL
        ; --- pre-pass: pawn counts per file (per colour) + bishop counts ---
        LDX #7
        LDA #$00
@ep_clr:
        STA wpf,X
        STA bpf,X
        DEX
        BPL @ep_clr
        STA wbishop
        STA bbishop
        LDX #$00
@ep_pp:
        TXA
        AND #OFFBOARD_MASK
        BNE @ep_ppn
        LDA board,X
        BEQ @ep_ppn
        STA tmp
        AND #PIECE_MASK
        CMP #PIECE_PAWN
        BEQ @ep_ppawn
        CMP #PIECE_BISHOP
        BNE @ep_ppn
        BIT tmp                 ; bishop: bump colour count
        BMI @ep_pbb
        INC wbishop
        JMP @ep_ppn
@ep_pbb:
        INC bbishop
        JMP @ep_ppn
@ep_ppawn:
        TXA
        AND #$07
        TAY                     ; file
        BIT tmp
        BMI @ep_pbp
        LDA wpf,Y               ; (INC abs,Y is not a 6502 mode) -> load/inc/store
        CLC
        ADC #1
        STA wpf,Y
        JMP @ep_ppn
@ep_pbp:
        LDA bpf,Y
        CLC
        ADC #1
        STA bpf,Y
@ep_ppn:
        INX
        BNE @ep_pp
        ; --- main pass ---
        LDA #$00
        STA score_lo            ; signed accumulator (our - their)
        LDX #$00
@ep_loop:
        TXA
        AND #OFFBOARD_MASK
        BNE @ep_skip
        LDA board,X
        BNE @ep_piece
@ep_skip:
        JMP @ep_next            ; trampoline (per-type code below is > 127 B)
@ep_piece:
        STA tmp                 ; tmp = piece byte
        ; --- geometry: rank, cdist[rank], cdist[file], centr, advance ---
        TXA
        LSR A
        LSR A
        LSR A
        LSR A
        AND #$07
        STA ce_target           ; rank
        TAY
        LDA cdist,Y
        STA ce_dirs_left        ; cdist[rank]
        TXA
        AND #$07
        TAY
        LDA cdist,Y
        STA ce_dir_ptr          ; cdist[file]
        CLC
        ADC ce_dirs_left
        STA tmp2                ; centr = cdist[rank]+cdist[file] (0..6)
        LDA ce_target           ; advance toward promotion
        BIT tmp                 ; N = colour bit (black -> set)
        BPL @ep_advw
        EOR #$07                ; black: 7 - rank
@ep_advw:
        STA ce_dir              ; adv (0..7)
        ; --- per-piece-type value -> A ---
        LDA tmp
        AND #PIECE_MASK
        CMP #PIECE_KNIGHT
        BEQ @ep_knight
        CMP #PIECE_PAWN
        BEQ @ep_jpawn
        CMP #PIECE_KING
        BEQ @ep_jking
        CMP #PIECE_ROOK
        BEQ @ep_jrook
        CMP #PIECE_QUEEN
        BEQ @ep_queen
        LDA tmp2                ; bishop: centr
        JMP @ep_val
@ep_knight:
        LDA tmp2                ; 2*centr
        ASL A
        JMP @ep_val
@ep_queen:
        LDA tmp2                ; centr>>1
        LSR A
        JMP @ep_val
@ep_jpawn:
        JMP @ep_pawn
@ep_jking:
        JMP @ep_king
@ep_jrook:
        JMP @ep_rook
@ep_val:
        STA tmp2                ; per-piece value (signed; king is negative)
        ; Accumulate signed: + for our pieces, - for theirs.
        LDA tmp
        AND #COLOR_MASK
        CMP side_to_move
        BNE @ep_their
        CLC
        LDA score_lo
        ADC tmp2
        STA score_lo
        JMP @ep_next
@ep_their:
        SEC
        LDA score_lo
        SBC tmp2
        STA score_lo
@ep_next:
        INX
        BEQ @ep_done
        JMP @ep_loop            ; trampoline (loop body > 127 B)
@ep_done:
        ; --- bishop pair (our - their) ---
        LDA wbishop
        CMP #2
        BCC @ep_nowp
        LDA side_to_move        ; white pair: + if white is us, else -
        BNE @ep_wp_them
        CLC
        LDA score_lo
        ADC #EP_BISHOP_PAIR
        STA score_lo
        JMP @ep_nowp
@ep_wp_them:
        SEC
        LDA score_lo
        SBC #EP_BISHOP_PAIR
        STA score_lo
@ep_nowp:
        LDA bbishop
        CMP #2
        BCC @ep_nobp
        LDA side_to_move        ; black pair: + if black is us, else -
        BEQ @ep_bp_them
        CLC
        LDA score_lo
        ADC #EP_BISHOP_PAIR
        STA score_lo
        JMP @ep_nobp
@ep_bp_them:
        SEC
        LDA score_lo
        SBC #EP_BISHOP_PAIR
        STA score_lo
@ep_nobp:
        LDA score_lo
        RTS

; --- per-piece cases with structural terms (out-of-line; reached via JMP) ---
@ep_pawn:
        LDA ce_dir              ; base = 2*advance + cdist[file]
        ASL A
        CLC
        ADC ce_dir_ptr
        STA tmp2
        TXA
        AND #$07
        STA ce_target           ; file (rank no longer needed)
        TAY
        BIT tmp                 ; colour -> pick wpf/bpf; ce_dirs_left = 0 white/1 black
        BMI @ep_pblk
        LDA wpf,Y
        LDY #$00
        JMP @ep_pgot
@ep_pblk:
        LDA bpf,Y
        LDY #$01
@ep_pgot:
        STY ce_dirs_left        ; colour flag
        CMP #2                  ; doubled?
        BCC @ep_pnodbl
        SEC
        LDA tmp2
        SBC #EP_DOUBLED_PEN
        STA tmp2
@ep_pnodbl:
        LDY ce_target           ; isolated? no same-colour pawn on file-1/file+1
        DEY
        BMI @ep_pleft0
        LDA ce_dirs_left
        BNE @ep_pilb1
        LDA wpf,Y
        JMP @ep_pilc1
@ep_pilb1:
        LDA bpf,Y
@ep_pilc1:
        BNE @ep_pnoiso
@ep_pleft0:
        LDY ce_target
        INY
        CPY #8
        BCS @ep_piso
        LDA ce_dirs_left
        BNE @ep_pilb2
        LDA wpf,Y
        JMP @ep_pilc2
@ep_pilb2:
        LDA bpf,Y
@ep_pilc2:
        BNE @ep_pnoiso
@ep_piso:
        SEC
        LDA tmp2
        SBC #EP_ISO_PEN
        STA tmp2
@ep_pnoiso:
        LDA tmp2
        JMP @ep_val
@ep_rook:
        LDA ce_dir              ; 7th-rank rook (advance == 6) -> +4
        CMP #6
        BNE @ep_rook0
        LDA #4
        JMP @ep_rookf
@ep_rook0:
        LDA #$00
@ep_rookf:
        STA tmp2
        TXA                     ; open file? no same-colour pawn on this file
        AND #$07
        TAY
        BIT tmp
        BMI @ep_rkb
        LDA wpf,Y
        JMP @ep_rkc
@ep_rkb:
        LDA bpf,Y
@ep_rkc:
        BNE @ep_rknoopen
        CLC
        LDA tmp2
        ADC #EP_ROOK_OPEN
        STA tmp2
@ep_rknoopen:
        LDA tmp2
        JMP @ep_val
@ep_king:
        LDA tmp2                ; base = -centr (central king is unsafe)
        EOR #$FF
        CLC
        ADC #1
        STA tmp2
        LDA #$00                ; pawn shield: count same-colour pawns in front
        STA ce_dirs_left
        LDA tmp                 ; ce_match = our pawn code (colour | PIECE_PAWN)
        AND #COLOR_MASK
        ORA #PIECE_PAWN
        STA ce_match
        BIT tmp                 ; colour -> forward offsets
        BMI @ep_kshb
        TXA
        CLC
        ADC #$0F
        JSR @ep_ksht
        TXA
        CLC
        ADC #$10
        JSR @ep_ksht
        TXA
        CLC
        ADC #$11
        JSR @ep_ksht
        JMP @ep_kshd
@ep_kshb:
        TXA
        CLC
        ADC #$EF
        JSR @ep_ksht
        TXA
        CLC
        ADC #$F0
        JSR @ep_ksht
        TXA
        CLC
        ADC #$F1
        JSR @ep_ksht
@ep_kshd:
        LDA ce_dirs_left        ; += SHIELD_BON(=2) * shieldcount
        ASL A
        CLC
        ADC tmp2
        STA tmp2
        JMP @ep_val
; @ep_ksht: A = candidate shield square. If on-board and holds our pawn, count++.
;   Preserves X (the king square); uses A, Y.
@ep_ksht:
        PHA
        AND #$88
        BNE @ep_kstno
        PLA
        TAY
        LDA board,Y
        CMP ce_match
        BNE @ep_kstd
        INC ce_dirs_left
        RTS
@ep_kstno:
        PLA
@ep_kstd:
        RTS
.else
        ; --- legacy positional (default): centralisation + pawn advance, used
        ;     as a tie-break only. Compact, so tight variants (text) still fit. ---
        LDA #$00
        STA score_lo
        LDX #$00
@epo_loop:
        TXA
        AND #OFFBOARD_MASK
        BNE @epo_next
        LDA board,X
        BEQ @epo_next
        STA tmp
        TXA
        LSR A
        LSR A
        LSR A
        LSR A
        AND #$07
        STA ce_target
        TAY
        LDA cdist,Y
        STA tmp2
        TXA
        AND #$07
        TAY
        LDA cdist,Y
        CLC
        ADC tmp2
        STA tmp2
        LDA tmp
        AND #PIECE_MASK
        CMP #PIECE_PAWN
        BNE @epo_have
        LDA ce_target
        BIT tmp
        BPL @epo_padd
        EOR #$07
@epo_padd:
        ASL A
        CLC
        ADC tmp2
        STA tmp2
@epo_have:
        LDA tmp
        AND #COLOR_MASK
        CMP side_to_move
        BNE @epo_their
        CLC
        LDA score_lo
        ADC tmp2
        STA score_lo
        JMP @epo_next
@epo_their:
        SEC
        LDA score_lo
        SBC tmp2
        STA score_lo
@epo_next:
        INX
        BNE @epo_loop
        LDA score_lo
        RTS
.endif

; ============================================================================
; ai_rng_step -- advance the 8-bit LFSR. Period 255 (Galois, taps $1D).
; ============================================================================
; Returns A = new LFSR state (and stored in ai_rng). Z reflects A.
; Bit 0 of the result is the random bit consumed by the reservoir sampler.
; Self-heals if ai_rng ever drops to zero (which kills the LFSR).
ai_rng_step:
        LDA ai_rng
        BNE @nz
        LDA #$AC
@nz:    ASL A
        BCC @done
        EOR #$1D
@done:  STA ai_rng
        RTS

; ============================================================================
; Negamax search with cutoffs. ai_strategy selects the depth: NAIVE = 1 ply
; (material after our move), SMART = 2 plies (sees the opponent's reply: stops
; hanging pieces, finds and refuses mate-in-1), DEEP = 3 plies (also sees our
; answer to that reply).
;
; The root (ai_play_move) keeps its own loop for the tie-breaks; each root move
; is scored by search_node on the opponent's side. Below the root, every ply
; has its own slot in the p_* / n_* arrays: the move and make_move's undo
; slots (saved_*) are parked there while deeper plies reuse them.
;
; Cutoffs: a node gets a cut and returns as soon as its best score exceeds it
; (the value is then only a bound, high enough for the caller to reject the
; move). A child's cut is -(parent's best)-1: past it, the parent would not
; take the move. At the root the cut comes from ai_best_score, so a cut root
; move is always strictly worse than the current best -- consider_move rejects
; it without touching the LFSR, and the chosen move is exactly the one a full
; search would pick.
; ============================================================================

; Positional bonus (pawn-equivalents) added to a castling move's score so the
; otherwise material-neutral castle is preferred over a quiet move but still
; yields to a real capture/promotion of equal-or-greater value.
CASTLE_BONUS = 1

; save_ply / restore_ply -- X = slot (ply, or ROOT_SLOT): park / restore the
; move in mv_* and make_move's undo slots.
save_ply:
        LDA mv_from
        STA p_from,X
        LDA mv_to
        STA p_to,X
        LDA mv_flags
        STA p_flags,X
        LDA mv_promo
        STA p_promo,X
        LDA saved_captured
        STA p_cap,X
        LDA saved_ep
        STA p_ep,X
        LDA saved_castling
        STA p_castling,X
        LDA saved_halfmove
        STA p_half,X
        LDA saved_king_sq
        STA p_ksq,X
        LDA saved_castle_rook_from
        STA p_crf,X
        LDA saved_castle_rook_to
        STA p_crt,X
        RTS
restore_ply:
        LDA p_from,X
        STA mv_from
        LDA p_to,X
        STA mv_to
        LDA p_flags,X
        STA mv_flags
        LDA p_promo,X
        STA mv_promo
        LDA p_cap,X
        STA saved_captured
        LDA p_ep,X
        STA saved_ep
        LDA p_castling,X
        STA saved_castling
        LDA p_half,X
        STA saved_halfmove
        LDA p_ksq,X
        STA saved_king_sq
        LDA p_crf,X
        STA saved_castle_rook_from
        LDA p_crt,X
        STA saved_castle_rook_to
        RTS

; root_cut -- A = the lowest score a root move needs to still be adopted
; (signed). Sets s_cut = -A: the reply search may stop once the opponent's
; best exceeds it. A = -128 or -127: every move counts, s_cut = +127 (never).
root_cut:
.ifdef CHESS_NO_CUTOFF
        LDA #$7F                ; test build: full search (test/Makefile exact)
        STA s_cut
        RTS
.endif
        CMP #$80
        BEQ @none
        CMP #$81
        BEQ @none
        EOR #$FF
        CLC
        ADC #$01
        STA s_cut
        RTS
@none:  LDA #$7F
        STA s_cut
        RTS

; search_node -- the side to move answers the move just made. In: A = cut,
; s_ply = this node's slot, s_leaf = the slot whose moves are scored
; statically. Out: A = the side to move's best score (their material minus
; the other side's), exact when <= cut, else some value > cut.
; Leaf score: material after the move, less the moved piece when it captured
; on a defended square (qsee_adjust). No legal move: -127 if in check (mated),
; 0 if stalemate; a castle -- only tried then -- scores its material.
; Moves come in two passes: first those that change the material (captures,
; en passant, promotions: a strong answer early means earlier cutoffs), then
; the others. At the leaf every quiet move scores the material as it stands
; (n_stat), so the quiet pass only looks for one legal quiet move, and only
; when n_stat would beat the best material move -- or first, when n_stat alone
; beats the cut.
search_node:
        LDX s_ply
        STA n_cut,X
        LDA #$80
        STA n_best,X            ; -128: any real move beats it
        LDA #$00
        STA n_found,X
        STA n_pass,X            ; material moves first: earlier cutoffs
        CPX s_leaf
        BNE @start
        JSR evaluate_material   ; leaf: score of any quiet move
        LDX s_ply
        STA n_stat,X
        EOR #$80
        STA tmp
        LDA n_cut,X
        EOR #$80
        CMP tmp
        BCS @start              ; cut >= static
        INC n_pass,X            ; static > cut: one legal quiet move is a
@start: LDA n_pass,X            ;   cutoff -- look for it first
        STA n_first,X
        JMP @newpass
@skipf: JMP @nextf              ; (loop body > 127 B)
@skipt: JMP @nextt
@floop:                         ; X = s_ply, Y = n_from = a piece of ours
        LDA n_pass,X            ; pass 0: material moves only
        BNE @allm
        LDA #GT_UNSORTED | GT_MATERIAL
        .byte $2C               ; BIT abs: skip the next LDA
@allm:  LDA #GT_UNSORTED
        STA gt_mode
        TYA
        PHA
        LDA sn_base,X
        TAY                     ; Y = this slot's list
        PLA
        TAX                     ; X = from
        JSR gen_targets
        LDX s_ply
        LDA gt_end
        STA n_end,X
        LDA sn_base,X
        STA n_idx,X
@tloop:
        LDX s_ply
        LDA n_idx,X
        CMP n_end,X
        BCS @skipf
        LDY n_from,X            ; deeper plies clobber mv_from / ce_piece
        STY mv_from
        LDA board,Y
        STA ce_piece
        LDY n_idx,X
        JSR gt_check
        BCS @skipt
        LDY mv_to               ; a capture? (also for qsee_adjust at the leaf)
        LDA board,Y
        STA see_victim
        ORA mv_promo            ; material move: capture, promotion or
        STA tmp                 ;   en passant
        LDA mv_flags
        AND #MV_FLAG_ENPASSANT
        ORA tmp
        CMP #$01                ; C = material move
        LDA #$00
        ROL A
        LDX s_ply
        EOR n_pass,X            ; pass 0 takes material moves, pass 1 the rest
        BEQ @skipt
        JSR make_move
        JSR in_check            ; own king left in check?
        BEQ @legal
        JMP @illegal
@legal: LDX s_ply
        LDA #$01
        STA n_found,X
        CPX s_leaf
        BNE @inner
        LDA n_pass,X
        BNE @leafq
        JSR evaluate_material   ; leaf: A = mover's material - other's
.ifdef CHESS_SMART_EVAL
        STA see_value
        JSR qsee_adjust
        LDA see_value
.endif
        JMP @score
@inner:
        JSR save_ply            ; X = s_ply
        LDX s_ply
        LDA n_best,X
        EOR #$FF                ; child's cut = -best - 1
.ifdef CHESS_NO_CUTOFF
        LDA #$7F
.endif
        PHA
        JSR toggle_side
        INC s_ply
        PLA
        JSR search_node
        DEC s_ply
        STA s_val
        JSR toggle_side
        LDX s_ply
        JSR restore_ply
        SEC
        LDA #$00
        SBC s_val               ; our score = -(their best)
@score:
        STA s_val
        EOR #$80                ; signed compare via the +$80 bias
        STA tmp
        LDX s_ply
        LDA n_best,X
        EOR #$80
        CMP tmp
        BCS @keep               ; best >= score
        LDA s_val
        STA n_best,X
@keep:  JSR unmake_move
        LDX s_ply
        LDA n_cut,X
        EOR #$80
        STA tmp
        LDA n_best,X
        EOR #$80
        CMP tmp
        BCC @nextt              ; best < cut
        BEQ @nextt              ; best = cut
        LDA n_best,X            ; best > cut: the caller rejects this line
        RTS
@leafq: JSR unmake_move       ; leaf, quiet move: it scores the material as
        LDX s_ply               ;   it stands, and so would every other quiet
        LDA n_stat,X            ;   move -- one legal one is enough
        STA s_val
        EOR #$80
        STA tmp
        LDA n_best,X
        EOR #$80
        CMP tmp
        BCS @lq                 ; best >= static
        LDA s_val
        STA n_best,X
@lq:    LDA n_best,X
        RTS
@illegal:
        JSR unmake_move
@nextt: LDX s_ply
        INC n_idx,X
        JMP @tloop
@newpass:
        LDA #$FF
        STA n_from,X
@nextf: LDX s_ply               ; next piece of ours; off-board squares of
        LDY n_from,X            ;   board[] are always 0
@scan:  INY
        CPY #$78                ; past h8
        BCS @pass
        LDA board,Y
        BEQ @scan
        EOR side_to_move
        BMI @scan               ; the other side's piece
        TYA
        STA n_from,X
        JMP @floop
@pass:  LDA n_pass,X
        CMP n_first,X
        BNE @done               ; both passes done
        EOR #$01
        STA n_pass,X
        BEQ @newpass            ; leaf without a legal quiet move: material now
        CPX s_leaf
        BNE @newpass
        LDA n_stat,X            ; leaf: a quiet move can only score the
        EOR #$80                ;   material as it stands -- skip them when
        STA tmp                 ;   that can't beat best
        LDA n_best,X
        EOR #$80
        CMP tmp
        BCC @newpass
@done:  LDA n_found,X
        BEQ @nomove
        LDA n_best,X
        RTS
@nomove:
        LDA #MV_FLAG_CASTLE_K   ; a castle could be the only legal move
        JSR try_one_castle
        BCC @castle
        LDA #MV_FLAG_CASTLE_Q
        JSR try_one_castle
        BCS @none
@castle:
        JSR evaluate_material   ; castle is material-neutral
        STA s_val
        JSR unmake_move
        LDA s_val
        RTS
@none:  JSR in_check
        BEQ @stale
        LDA #$81                ; -127: mated
        RTS
@stale: LDA #$00                ; stalemate ~ draw
        RTS

sn_base: .byte GT_PLY0, GT_PLY0+32, GT_PLY0+64     ; tgt_buf list per slot

; qsee_adjust — quiescence (SEE-1). The opponent's reply is MADE on the board;
;   see_victim = the piece it captured (0 if quiet), see_value = the static eval.
;   If the capture landed on a square WE defend we recapture, so the opponent
;   loses the piece it moved there: subtract that piece's value from see_value.
;   Resolves the horizon effect on exchanges with no nested search. Uses
;   is_attacked_runner (which leaves rscan_*/mv_*/best_reply untouched).
qsee_adjust:
.ifdef CHESS_SMART_EVAL
        LDA see_victim
        BEQ @qdone              ; quiet reply -> nothing to recapture
        LDA side_to_move        ; attacker_color = OUR colour (opponent ^ black)
        EOR #COLOR_BLACK
        STA attacker_color
        LDA mv_to
        STA attacked_sq
        JSR is_attacked_runner  ; A = 1 if we defend mv_to (can recapture)
        BEQ @qdone
        LDY mv_to
        LDA board,Y
        AND #PIECE_MASK
        TAY
        SEC
        LDA see_value
        SBC mat_simple,Y        ; opponent loses its recaptured piece
        STA see_value
@qdone:
.endif
        RTS

; score_move — the move in mv_* is currently MADE on the board (our king already
; verified safe). Return A = its score from our perspective. NAIVE = material
; after the move; SMART / DEEP = -(opponent's best answer), searched with the
; cut in s_cut (root_cut). The board stays MADE (caller unmakes); mv_* and
; saved_* are restored before returning.
score_move:
        LDA ai_strategy
        BNE @sm_search
        JMP evaluate_material   ; tail: A = our - their
@sm_search:
        LDX #ROOT_SLOT
        JSR save_ply
        LDA ai_strategy         ; SMART: leaf = slot 0, DEEP: slot 1
        SEC
        SBC #AI_STRATEGY_SMART
        STA s_leaf
        LDA #$00
        STA s_ply
        JSR toggle_side         ; opponent to move
        LDA s_cut
        JSR search_node
        STA s_val
        JSR toggle_side         ; back to us
        LDX #ROOT_SLOT
        JSR restore_ply
        SEC
        LDA #$00
        SBC s_val               ; A = -(opponent best) = our negamax score
        RTS

; consider_move — A = candidate score for the move in mv_*. Replace ai_best_* if
; it strictly beats ai_best_score; on an exact tie step the LFSR and replace iff
; bit 0 = 1 (keeps AvA self-play diverging). Stores mv_flags too (castle rides).
consider_move:
        PHA
        CLC
        ADC #$80
        STA tmp                 ; biased candidate material
        LDA ai_best_score
        CLC
        ADC #$80
        STA tmp2                ; biased best material
        LDA tmp
        CMP tmp2
        BCC @cm_keep            ; material < best
        BEQ @cm_tie             ; material == best -> positional tie-break
        JMP @cm_take            ; material > best
@cm_tie:
        ; Material tied: prefer the better positional score (cand_pos). This is
        ; the ONLY place positional matters, so it can never override material.
        LDA cand_pos
        CLC
        ADC #$80
        STA tmp
        LDA ai_best_pos
        CLC
        ADC #$80
        STA tmp2
        LDA tmp
        CMP tmp2
        BCC @cm_keep            ; positional < best -> keep
        BNE @cm_take            ; positional > best -> take
        JSR ai_rng_step         ; positional also tied -> LFSR coin-flip
        AND #$01
        BEQ @cm_keep
@cm_take:
        PLA
        STA ai_best_score
        LDA cand_pos
        STA ai_best_pos
        LDA mv_from
        STA ai_best_from
        LDA mv_to
        STA ai_best_to
        LDA mv_flags
        STA ai_best_flags
        RTS
@cm_keep:
        PLA
        RTS

; jitter_pos — add a small random 0..3 to cand_pos (the positional tie-break)
;   for game-to-game / move-to-move variety. Material and the search score still
;   dominate, so this only shuffles near-equal quiet moves -- never a blunder.
;   No-op unless CHESS_SMART_EVAL (keeps the default/text engine deterministic).
jitter_pos:
.ifdef CHESS_SMART_EVAL
        JSR ai_rng_step         ; advance the LFSR (seeded from key timing)
        AND #$07                ; 0..7 -- enough to reshuffle near-equal quiet
        CLC                     ;   moves, still << a pawn so tactics dominate
        ADC cand_pos
        STA cand_pos
.endif
        RTS

; ============================================================================
; ai_play_move — pick + apply the best move for side_to_move (depth per
; ai_strategy). CC if a move was made, CS if none (caller treats as mate/stale).
; ============================================================================
.export ai_play_move
.export ai_best_from, ai_best_to
.export ai_best_score
.export ai_strategy, ai_rng
ai_play_move:
        LDA #$88
        STA ai_best_from
        STA ai_best_to
        LDA #$00
        STA ai_best_flags
        LDA #$80                ; -128: worst
        STA ai_best_score
        STA ai_best_pos         ; -128: worst positional too
        LDA #AI_PASS_ALL        ; NAIVE / SMART: one pass, square order (the
        LDX ai_strategy         ;   order their games were played in)
        CPX #AI_STRATEGY_DEEP
        BNE @pass
        LDA #$00                ; DEEP: material moves first, so a good score
@pass:  STA ai_pass             ;   -- and root cutoffs -- come early
        LDA #$00
        STA ai_scan_x
        BEQ @floop              ; always
@skipf: JMP @nextf              ; (loop body > 127 B)
@floop:
        LDX ai_scan_x
        TXA
        AND #OFFBOARD_MASK
        BNE @skipf
        LDA board,X
        BEQ @skipf
        AND #COLOR_MASK
        CMP side_to_move
        BNE @skipf
        STX mv_from
        LDY #GT_ROOT
        LDA #$00
        STA gt_mode             ; every target, ascending
        JSR gen_targets
        LDA gt_end
        STA ai_tend             ; gt_end is reused by the reply search
        LDA #GT_ROOT
        STA ai_scan_y           ; index into tgt_buf
@tloop:
        LDY ai_scan_y
        CPY ai_tend
        BCS @nextf
        ; Re-establish ce_piece every destination: the reply search
        ; (search_node) overwrites it while iterating the opponent's pieces.
        LDX mv_from
        LDA board,X
        STA ce_piece
        JSR gt_check
        BCS @nextt
        LDA ai_pass
        CMP #AI_PASS_ALL
        BEQ @make
        LDY mv_to               ; material move: capture, promotion or
        LDA board,Y             ;   en passant
        ORA mv_promo
        STA tmp
        LDA mv_flags
        AND #MV_FLAG_ENPASSANT
        ORA tmp
        CMP #$01                ; C = material move
        LDA #$00
        ROL A
        EOR ai_pass             ; pass 0 takes material moves, pass 1 the rest
        BEQ @nextt
@make:  JSR make_move
        JSR in_check            ; does the move leave OUR king in check?
        BNE @bad                ; illegal — discard
        JSR evaluate_positional ; board = after our move; tie-break score
        STA cand_pos
        JSR jitter_pos          ; small random jitter for game variety
        LDA ai_best_score       ; below it the move can't be adopted
        JSR root_cut
        JSR score_move          ; A = material score (1-, 2- or 3-ply)
        JSR consider_move       ; maybe adopt as best
        JSR unmake_move
        JMP @nextt
@bad:
        JSR unmake_move
@nextt:
        INC ai_scan_y
        JMP @tloop
@nextf:
        INC ai_scan_x
        BEQ @endscan
        JMP @floop
@endscan:
        LDA ai_pass
        BNE @castles
        INC ai_pass             ; DEEP: material moves done, now the others
        LDA #$00
        STA ai_scan_x
        JMP @floop
@castles:
        ; --- Castling candidates (not produced by gen_targets). ---
        LDA #MV_FLAG_CASTLE_K
        JSR try_one_castle
        BCS @try_qs
        JSR @castle_consider
@try_qs:
        LDA #MV_FLAG_CASTLE_Q
        JSR try_one_castle
        BCS @apply
        JSR @castle_consider
@apply:
        LDA ai_best_from
        CMP #$88
        BEQ @no_move
        STA mv_from
        LDA ai_best_to
        STA mv_to
        LDA #$00
        STA mv_promo
        LDA ai_best_flags
        STA mv_flags
        JSR apply_user_move     ; routes a castle bit to apply_castle_move
        RTS
@no_move:
        SEC
        RTS

; @castle_consider — the castle in mv_* is currently MADE (try_one_castle CC).
; Score it at the same depth + CASTLE_BONUS, adopt if best, then unmake.
@castle_consider:
        JSR evaluate_positional ; board = after the castle
        STA cand_pos
        JSR jitter_pos
        LDA ai_best_score       ; the castle gets CASTLE_BONUS on top
        CMP #$80
        BEQ @cc_cut
        SEC
        SBC #CASTLE_BONUS
@cc_cut:
        JSR root_cut
        JSR score_move
        CLC
        ADC #CASTLE_BONUS
        JSR consider_move
        JMP unmake_move         ; tail: revert the castle, RTS to caller


; ============================================================================
; perft1 -- count pseudo-legal moves at the current position that pass the
;           own-king-not-in-check filter (i.e. legal moves at depth 1)
; ============================================================================
; Returns count in perft_count_lo:hi (16-bit). Stops at 65535 (overflow
; safe for chess: max ~218 legal moves in any position).
.export perft1
.export perft_count_lo, perft_count_hi
perft1:
        LDA #$00
        STA perft_count_lo
        STA perft_count_hi
        STA ai_scan_x
@floop:
        LDX ai_scan_x
        TXA
        AND #OFFBOARD_MASK
        BNE @nextf
        LDA board,X
        BEQ @nextf
        AND #COLOR_MASK
        CMP side_to_move
        BNE @nextf
        STX mv_from
        LDA board,X
        STA ce_piece
        LDY #GT_ROOT
        LDA #$00
        STA gt_mode             ; every target, ascending
        JSR gen_targets
        LDA #GT_ROOT
        STA ai_scan_y           ; index into tgt_buf
@tloop:
        LDY ai_scan_y
        CPY gt_end
        BCS @nextf
        JSR gt_check
        BCS @nextt
        JSR make_move
        JSR in_check
        BNE @illegal
        ; Legal move: increment counter
        INC perft_count_lo
        BNE @inc_done
        INC perft_count_hi
@inc_done:
        JSR unmake_move
        JMP @nextt
@illegal:
        JSR unmake_move
@nextt:
        INC ai_scan_y
        JMP @tloop
@nextf:
        INC ai_scan_x
        BNE @floop
        ; Castling isn't emitted by gen_targets — add each legal castle
        ; to the count so perft(1) matches a reference generator.
        LDA #MV_FLAG_CASTLE_K
        JSR try_one_castle
        BCS @pft_qs
        JSR unmake_move
        INC perft_count_lo
        BNE @pft_qs
        INC perft_count_hi
@pft_qs:
        LDA #MV_FLAG_CASTLE_Q
        JSR try_one_castle
        BCS @pft_end
        JSR unmake_move
        INC perft_count_lo
        BNE @pft_end
        INC perft_count_hi
@pft_end:
        RTS

; ============================================================================
; save_user_state / undo_last_move -- single-level undo (compact)
; ============================================================================
; save_user_state: called by apply_user_move right after a move is committed
; (just before the side toggle). Snapshots the per-move undo info that the
; engine's saved_* slots will lose at the next game_status iteration.
;
; undo_last_move: restore the snapshotted state and call unmake_move. Toggles
; side back, decrements fullmove if applicable. Clears undo_avail (no
; double-undo).
.export save_user_state, undo_last_move
.export undo_avail

save_user_state:
        LDA mv_from
        STA user_mv_from
        LDA mv_to
        STA user_mv_to
        LDA mv_promo
        STA user_mv_promo
        LDA mv_flags
        STA user_mv_flags
        LDA saved_captured
        STA user_saved_captured
        LDA saved_ep
        STA user_saved_ep
        LDA saved_castling
        STA user_saved_castling
        LDA saved_halfmove
        STA user_saved_halfmove
        LDA saved_king_sq
        STA user_saved_king_sq
        LDA saved_castle_rook_from
        STA user_saved_rook_from
        LDA saved_castle_rook_to
        STA user_saved_rook_to
        LDA side_to_move
        STA user_saved_side
        LDA fullmove_number
        STA user_saved_fullmove
        LDA #$01
        STA undo_avail
        RTS

undo_last_move:
        LDA undo_avail
        BNE @ok
        SEC                     ; no undo
        RTS
@ok:
        ; Restore engine saved_* from user_* so unmake_move sees the right state
        LDA user_mv_from
        STA mv_from
        LDA user_mv_to
        STA mv_to
        LDA user_mv_promo
        STA mv_promo
        LDA user_mv_flags
        STA mv_flags
        LDA user_saved_captured
        STA saved_captured
        LDA user_saved_ep
        STA saved_ep
        LDA user_saved_castling
        STA saved_castling
        LDA user_saved_halfmove
        STA saved_halfmove
        LDA user_saved_king_sq
        STA saved_king_sq
        LDA user_saved_rook_from
        STA saved_castle_rook_from
        LDA user_saved_rook_to
        STA saved_castle_rook_to
        ; side_to_move was already toggled by apply_user_move after the
        ; original move. unmake_move expects side_to_move to still be the
        ; mover's side (it uses side_to_move to identify which king to
        ; restore). So toggle BACK first.
        LDA user_saved_side
        STA side_to_move
        LDA user_saved_fullmove
        STA fullmove_number
        ; Now reverse the move on the board.
        JSR unmake_move
        LDA #$00
        STA undo_avail
        CLC
        RTS
