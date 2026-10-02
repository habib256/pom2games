; Boot-only LZ unpacker at $0800. Its data occupies transient low/HGR RAM.
; Restore every borrowed zero-page byte before entering the game at $6000.
.setcpu "6502"
.segment "CODE"
src = $06
dst = $08
ref = $0A
; The disk builder patches a read-only sector map for MICRODATA. This avoids
; DOS byte-at-a-time BLOAD for the large compressed stream. Runtime saves
; still discover their real catalog/T/S chains; they never use this map.
start:
        LDX #0
@save_zp:
        LDA $00,X
        STA $5000,X
        INX
        BNE @save_zp
        JSR $03E3
        STY $80
        STA $81
        LDY #2
        LDA #1
        STA ($80),Y
        INY
        LDA #0
        STA ($80),Y
        LDY #8
        STA ($80),Y
        INY
        LDA #$10
        STA ($80),Y
        LDY #12
        LDA #1
        STA ($80),Y
        LDA #0
        STA boot_index
@sector:
        LDX boot_index
        LDY #4
        LDA boot_sectors,X
        STA ($80),Y
        INY
        LDA boot_sectors+1,X
        STA ($80),Y
        JSR $03E3
        JSR $03D9
        BCS @failed
        LDY #9
        LDA ($80),Y
        CLC
        ADC #1
        STA ($80),Y
        INC boot_index
        INC boot_index
        LDA boot_index
        CMP boot_count
        BCC @sector
        LDX #3
@magic: LDA $1004,X
        CMP boot_magic,X
        BNE @failed
        DEX
        BPL @magic
        JSR restore_zp
        JMP unpack_start
@failed:
        JSR restore_zp
        JMP $03D0
restore_zp:
        LDX #0
@byte:  LDA $5000,X
        STA $00,X
        INX
        BNE @byte
        RTS
boot_magic: .byte "MSL1"
boot_index: .byte 0
boot_count: .byte 0
boot_sectors: .res 120, 0
unpack_start:
        LDX #5
@save: LDA src,X
        PHA
        DEX
        BPL @save
        LDA #<$1008
        STA src
        LDA #>$1008
        STA src+1
        LDA #0
        STA dst
        LDA #$60
        STA dst+1
@token:
        JSR get
        BEQ @done
        BMI @match
        TAX
@literal:
        JSR get
        JSR put
        DEX
        BNE @literal
        JMP @token
@match:
        AND #$7F
        CLC
        ADC #3
        TAX
        JSR get
        STA ref
        JSR get
        STA ref+1
        SEC
        LDA dst
        SBC ref
        STA ref
        LDA dst+1
        SBC ref+1
        STA ref+1
@copy: LDY #0
        LDA (ref),Y
        JSR put
        INC ref
        BNE @next
        INC ref+1
@next: DEX
        BNE @copy
        JMP @token
@done: LDX #0
@restore:
        PLA
        STA src,X
        INX
        CPX #6
        BCC @restore
        JMP $6000
get:    LDY #0
        LDA (src),Y
        INC src
        BNE @ret
        INC src+1
@ret:   ORA #0
        RTS
put:    LDY #0
        STA (dst),Y
        INC dst
        BNE @ret
        INC dst+1
@ret:   RTS
payload:
