; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; fm.asm -- DOS 3.3 files by name through the file manager ($03D6)
; ============================================================================
;   fm_open    A/Y = name (lo/hi; ASCII, ends with 0 or ','; 30 characters
;              at most), X = the type to give the file if it must be
;              created (FM_TEXT, FM_BINARY...), or FM_MUST_EXIST: a missing
;              file is then error 6. Takes a free DOS file buffer (one of
;              MAXFILES) and keeps its address in fm_file. Position 0.
;              Out: C = 0 with A = 0 (the file was there) or A =
;              FM_ERR_NOT_FOUND (6: it was created, empty: the file
;              manager's own answer); fm_type = the file's type (an
;              existing file keeps its own; FM_LOCKED bit included).
;   fm_read    A/Y = destination, fm_len = byte count: reads from the
;              position, which moves on. fm_len = 0 does nothing.
;   fm_write   A/Y = source, fm_len = byte count. The same.
;   fm_seek    A/Y = byte position (lo/hi) in the file. A position past
;              the file's last sector is accepted; a read there answers
;              FM_ERR_END.
;   fm_close   writes what is still in the buffers, updates the catalog
;              (sector count) and frees the DOS buffer, even on an error.
;   fm_delete, fm_lock, fm_unlock, fm_verify
;              A/Y = name, as fm_open (they borrow a free DOS buffer).
; All return C = 0 on success, or C = 1 and A = the error:
;   FM_ERR_PROTECTED 4, FM_ERR_END 5 (end of data: a read past the file's
;   last sector), FM_ERR_NOT_FOUND 6, FM_ERR_VOLUME 7, FM_ERR_IO 8,
;   FM_ERR_FULL 9, FM_ERR_LOCKED 10 (DELETE or a write of a locked file),
;   FM_ERR_NO_BUFFER 12 (all MAXFILES buffers in use: DOS's own message
;   number). DOS prints nothing and the program keeps running: unlike a
;   DOS command (dos.asm), a full or protected disk is just a code. On
;   FM_ERR_FULL the file keeps what fitted: fm_close it, then fm_delete it
;   if half a save is worse than none.
; Clobber A, X, Y.
;
; Write length: the file manager's WRITE range writes ONE BYTE MORE than
; its range length (READ range is exact; cc65-apple2-dosio met it too).
; fm_write asks for fm_len - 1, so fm_len is the true count both ways.
;
; A DOS binary file (BLOAD / BRUN) starts with a 4-byte header, the load
; address then the length: write it first, or skip it when reading. The
; file manager stores bytes only and keeps no length (a file is whole
; sectors; the last one's tail reads as zeros), so a reader needs the
; length from the header or from its own data.
;
; One open file at a time, or more: fm_file is the handle. Save it after
; fm_open and put it back before fm_read / fm_write / fm_seek / fm_close
; of that file (each open file holds one DOS buffer). Close every file
; before the program goes back to DOS.
;
; Drive: fm_slot / fm_drive (DATA, default 0 = the slot and drive of
; DOS's last access, RWTS IOB bytes 15-16: the disk the program came
; from); any volume. Set both (slot 1-7, drive 1-2) to name another one.
;
; Why: dos.asm's commands stop the program at the BASIC prompt on any
; error; rwts.asm reads and writes sectors placed when the disk is built.
; The file manager creates files of any size, finds them by name and
; reports its errors. It is DOS's own slow path (BLOAD's: one byte at a
; time). Every call goes through DOS's parameter list ($03DC) and its
; file buffers (the chain from ($03D2) * 256): no fixed DOS address, so a
; relocated DOS works too. The file manager must still be in memory.
; Learnt from tsupplis/cc65-apple2-dosio (MIT) and Beneath Apple DOS,
; pages 6-7 to 6-17.
;
; Zero page: none of its own, and the file manager needs nothing there
; (dev/tests/test_fm.py runs every call with $00-$FF full of garbage).
; The calls write $26-$27, $2A-$2F, $35, $3C-$3F and $42-$49 (measured;
; the test fails if another byte changes). FM_KEEP_ZP = 1 saves and
; restores DOS_ZP_START .. +DOS_ZP_LEN around each call, in fm_zp_buf
; (BSS unless defined before the include; defaults $00 / 256).
; Interrupts: FM_SEI = 1 masks them during each call (RWTS's disk timing),
; the caller's I flag put back: for programs that enable IRQs.
;
; Size: 401 bytes for fm_open + fm_write (fm_read) + fm_close, 451 with
; everything; BSS 25 bytes (fm_len, fm_type, fm_file, fm_pl, fm_call_x,
; fm_op), DATA 2 (fm_slot, fm_drive). The name, the DOS buffer and DOS's
; parameter list are reached through patched absolute operands.
; .ifref: include after the callers. C mirror: ../apple2c/apple2fm.h.
; ============================================================================

.ifndef _FM_ASM_LOADED_
_FM_ASM_LOADED_ = 1

FM_ENTRY    = $03D6             ; X = 0 (OPEN may create) / 1: run the list
FM_PARMS    = $03DC             ; -> A/Y = DOS's parameter list (hi/lo)
FM_IOB      = $03E3             ; -> A/Y = DOS's RWTS IOB (hi/lo)
FM_DOS_PAGE = $03D2             ; DOS's first page: (page * 256) -> buffer 1

FM_TEXT       = $00             ; file types (catalog letters T I A B)
FM_INTEGER    = $01
FM_APPLESOFT  = $02
FM_BINARY     = $04
FM_LOCKED     = $80             ; in fm_type after fm_open
FM_MUST_EXIST = $80             ; fm_open's X: never create

FM_ERR_PROTECTED = 4
FM_ERR_END       = 5
FM_ERR_NOT_FOUND = 6
FM_ERR_VOLUME    = 7
FM_ERR_IO        = 8
FM_ERR_FULL      = 9
FM_ERR_LOCKED    = 10
FM_ERR_NO_BUFFER = 12

FM_OP_OPEN     = 1              ; file manager calls
FM_OP_CLOSE    = 2
FM_OP_READ     = 3
FM_OP_WRITE    = 4
FM_OP_DELETE   = 5
FM_OP_LOCK     = 7
FM_OP_UNLOCK   = 8
FM_OP_POSITION = 10
FM_OP_VERIFY   = 12

.ifndef FM_SEI                  ; options: 1 = on, 0 or undefined = off
FM_SEI = 0
.endif
.ifndef FM_KEEP_ZP
FM_KEEP_ZP = 0
.endif
.if FM_KEEP_ZP
.ifndef DOS_ZP_START
DOS_ZP_START = 0
.endif
.ifndef DOS_ZP_LEN
DOS_ZP_LEN = 256
.endif
.endif

.if .referenced(fm_open) .or .referenced(fm_close) .or .referenced(fm_read) .or .referenced(fm_write) .or .referenced(fm_seek) .or .referenced(fm_delete) .or .referenced(fm_lock) .or .referenced(fm_unlock) .or .referenced(fm_verify)

.segment "BSS"
.ifndef fm_len
fm_len:     .res 2
.endif
.ifndef fm_type
fm_type:    .res 1
.endif
fm_file:    .res 2              ; the open file: its DOS buffer's name field
fm_pl:      .res 18             ; the parameter list, copied in and out
fm_call_x:  .res 1
fm_op:      .res 1
.if FM_KEEP_ZP
.ifndef fm_zp_buf
fm_zp_buf:  .res DOS_ZP_LEN
.endif
.endif
.segment "DATA"
fm_slot:    .byte 0             ; 0: DOS's last access
fm_drive:   .byte 0

.segment "CODE"

; ---------------------------------------------------------------- open/close
.ifref fm_open
fm_open:
        STX     fm_type
        JSR     fm_take                 ; a free buffer, the name, the drive
        BCS     @rts
        LDA     #1                      ; record length 1: POSITION's
        STA     fm_pl+2                 ; record number is a byte number
        LDA     #0
        STA     fm_pl+3
        LDX     #0                      ; X = 0: OPEN may create the file
        LDA     fm_type
        BPL     @new
        INX
        LDA     #FM_BINARY              ; (any type: an existing file keeps
@new:   STA     fm_pl+7                 ; its own)
        LDA     #FM_OP_OPEN
        JSR     fm_call
        BCC     @ok
        LDX     fm_call_x               ; a created file answers "not found"
        BNE     @fail                   ; (DOS's own commands ignore it)
        CMP     #FM_ERR_NOT_FOUND
        BEQ     @made
@fail:  SEC
        JMP     fm_drop
@made:  CLC                             ; A = 6: a new file
@ok:    LDX     fm_pl+7                 ; the file's type
        STX     fm_type
@rts:   RTS
.endif

.ifref fm_close
fm_close:
        JSR     fm_use
        LDA     #FM_OP_CLOSE
        JSR     fm_call
        JMP     fm_drop
.endif

; ---------------------------------------------------------------- read/write
.if .referenced(fm_read) .or .referenced(fm_write)
fm_write:
        LDX     #FM_OP_WRITE
        .byte   $2C                     ; BIT abs: skips the LDX
fm_read:
        LDX     #FM_OP_READ
        STA     fm_pl+8                 ; the range: address, length
        STY     fm_pl+9
        LDA     fm_len
        STA     fm_pl+6
        ORA     fm_len+1
        BEQ     @none
        LDA     fm_len+1
        STA     fm_pl+7
        CPX     #FM_OP_WRITE            ; the file manager writes one byte
        BNE     @range                  ; more than its range length (READ
        LDA     fm_pl+6                 ; is exact): ask for fm_len - 1
        BNE     @lo
        DEC     fm_pl+7
@lo:    DEC     fm_pl+6
@range: LDA     #2                      ; subcode 2: a range of bytes
        STA     fm_pl+1
        STX     fm_op
        JSR     fm_use
        LDA     fm_op
        JMP     fm_call
@none:  CLC                             ; A = 0
        RTS
.endif

.ifref fm_seek
fm_seek:
        STA     fm_pl+2                 ; record number (record length 1)
        STY     fm_pl+3
        LDA     #0                      ; byte offset in the record
        STA     fm_pl+4
        STA     fm_pl+5
        JSR     fm_use
        LDA     #FM_OP_POSITION
        JMP     fm_call
.endif

; ---------------------------------------------------------------- by name
.if .referenced(fm_delete) .or .referenced(fm_lock) .or .referenced(fm_unlock) .or .referenced(fm_verify)
.ifref fm_delete
fm_delete:
        LDX     #FM_OP_DELETE
        BNE     fm_named                ; always
.endif
.ifref fm_lock
fm_lock:
        LDX     #FM_OP_LOCK
        BNE     fm_named
.endif
.ifref fm_unlock
fm_unlock:
        LDX     #FM_OP_UNLOCK
        BNE     fm_named
.endif
.ifref fm_verify
fm_verify:
        LDX     #FM_OP_VERIFY
.endif
fm_named:
        STX     fm_op
        JSR     fm_take
        BCS     fm_rts
        LDA     fm_op
        JSR     fm_call
        ; falls into fm_drop
.endif

; The DOS buffer of fm_file is free again: its name's first byte = 0.
; Keeps C and A (the call's result).
fm_drop:
        PHP
        PHA
        LDA     #0
        TAY
        JSR     fm_put
        PLA
        PLP
fm_rts: RTS

; ---------------------------------------------------------------- the call
; A = call type, fm_pl the rest. Copies fm_pl into DOS's list, runs the
; file manager with X = fm_call_x, copies the list back.
; Out: A = return code, C = 1 if not 0.
fm_call:
        STA     fm_pl
        STX     fm_call_x
.if FM_KEEP_ZP
        LDY     #0
@save:  LDA     DOS_ZP_START,Y
        STA     fm_zp_buf,Y
        INY
        CPY     #<DOS_ZP_LEN
        BNE     @save
.endif
        JSR     FM_PARMS                ; A/Y = the list (hi/lo)
        STY     @to+1
        STA     @to+2
        STY     @from+1
        STA     @from+2
        LDY     #17
@in:    LDA     fm_pl,Y
@to:    STA     $FFFF,Y                 ; patched: DOS's list
        DEY
        BPL     @in
        LDX     fm_call_x
.if FM_SEI
        PHP                             ; no interrupt in the disk's timing
        SEI
.endif
        JSR     FM_ENTRY
.if FM_SEI
        PLP
.endif
        LDY     #17
@out:
@from:  LDA     $FFFF,Y                 ; patched: DOS's list
        STA     fm_pl,Y
        DEY
        BPL     @out
.if FM_KEEP_ZP
        LDY     #0
@rest:  LDA     fm_zp_buf,Y
        STA     DOS_ZP_START,Y
        INY
        CPY     #<DOS_ZP_LEN
        BNE     @rest
.endif
        LDA     fm_pl+10                ; return code
        CMP     #1                      ; C = 1 unless 0
        RTS

; ---------------------------------------------------------------- buffers
; fm_take: A/Y = name. Finds a free DOS buffer (fm_file), writes the name
; into it (which marks it in use for DOS too), fills fm_pl with the name,
; the buffers and the drive. C = 1, A = FM_ERR_NO_BUFFER if none is free.
fm_take:
        STA     @name+1
        STY     @name+2
        LDA     FM_DOS_PAGE             ; ($03D2) * 256: buffer 1's name field
        STA     @lo+2
        STA     @hi+2
@lo:    LDA     $FF00                   ; patched: DOS's first page
        STA     fm_file
@hi:    LDA     $FF01
        STA     fm_file+1
@buf:   JSR     fm_patch
        LDY     #0
        JSR     fm_get
        BEQ     @free                   ; name byte 0 = 0: free
        LDY     #36                     ; next buffer's name field
        JSR     fm_get
        TAX
        INY
        JSR     fm_get
        BEQ     @full                   ; 0: that was the last buffer
        STX     fm_file
        STA     fm_file+1
        BNE     @buf                    ; always
@full:  LDA     #FM_ERR_NO_BUFFER
        SEC
        RTS
@free:  LDY     #0                      ; the name: high bit set, spaces
@ch:
@name:  LDA     $FFFF,Y                 ; patched: the caller's name
        BEQ     @pad
        CMP     #','
        BEQ     @pad
        ORA     #$80
        JSR     fm_put
        INY
        CPY     #30
        BNE     @ch
        BEQ     @named                  ; always
@pad:   LDA     #$A0
@sp:    JSR     fm_put
        INY
        CPY     #30
        BNE     @sp
@named: LDA     fm_file                 ; the name for the file manager
        STA     fm_pl+8
        LDA     fm_file+1
        STA     fm_pl+9
        JSR     fm_bufs
        LDA     #0                      ; any volume
        STA     fm_pl+4
        LDX     fm_slot
        LDA     fm_drive
        BNE     @drive
        JSR     FM_IOB                  ; DOS's last access: IOB bytes 15-16
        STY     @iob+1
        STA     @iob+2
        LDY     #16
        JSR     @iob
        PHA
        DEY
        JSR     @iob
        LSR     A                       ; slot * 16 -> slot
        LSR     A
        LSR     A
        LSR     A
        TAX
        PLA
@drive: STA     fm_pl+5
        STX     fm_pl+6
        CLC
        RTS
@iob:   LDA     $FFFF,Y                 ; patched: the IOB
        RTS

; fm_use: the open file fm_file, its buffers in fm_pl.
fm_use:
        JSR     fm_patch
        ; falls into fm_bufs
; fm_bufs: the buffer's three pointers (after its name) -> fm_pl+12..17.
fm_bufs:
        LDY     #30
@b:     JSR     fm_get
        STA     fm_pl+12-30,Y
        INY
        CPY     #36
        BNE     @b
        RTS

fm_patch:
        LDA     fm_file
        STA     fm_get+1
        STA     fm_put+1
        LDA     fm_file+1
        STA     fm_get+2
        STA     fm_put+2
        RTS
fm_get: LDA     $FFFF,Y                 ; patched: the buffer's name field
        RTS
fm_put: STA     $FFFF,Y
        RTS

.endif  ; any fm_* referenced
.endif  ; _FM_ASM_LOADED_
