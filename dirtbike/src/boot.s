; HELLO runs this at $1000. Read the DOS binary, including its four-byte
; header, into the unused graphics pages before starting it at $6000.
GAME = $6000
BUFFER = $2000
SECTORS = (GAME_BYTES + 4 + 255) / 256
.assert GAME_BYTES > 0 .and GAME_BYTES <= $9600-GAME, error, "DIRTBIKE must fit below DOS"
RWTS_RETRIES = 4

.code
boot:
        LDA     #>BUFFER
        STA     rwts_page
        LDA     #1                      ; read
        LDX     #SECTORS
        JSR     rwts_sectors
        BCS     read_error
        LDY     #0
        LDX     #>GAME_BYTES
        BEQ     tail
page:   LDA     BUFFER+4,Y
        STA     GAME,Y
        INY
        BNE     page
        INC     page+2
        INC     page+5
        DEX
        BNE     page
tail:
.if <GAME_BYTES
        LDA     BUFFER+4+(GAME_BYTES & $FF00),Y
        STA     GAME+(GAME_BYTES & $FF00),Y
        INY
        CPY     #<GAME_BYTES
        BNE     tail
.endif
        JMP     GAME

read_error:
        LDX     #0
print:  LDA     error_text,X
        BEQ     wait_key
        ORA     #$80
        JSR     $FDED                   ; monitor COUT
        INX
        BNE     print
wait_key:
        BIT     $C010
wait:   LDA     $C000
        BPL     wait
        BIT     $C010
        JMP     boot
error_text: .byte 13,"CHECK DISK, PRESS A KEY TO RETRY",13,0

; dos33patch fills these from the final disk allocation.
RWTS_SEC_T: .res SECTORS
RWTS_SEC_S: .res SECTORS
.include "rwts.asm"
