; Three independent DOS 3.3 checkpoints. The unused DFS stack packs player
; state; the entire $1000 page is a self-contained, checksummed snapshot.
; Loaded after title decompression; narrator ends exactly before STATECODE.
SAVE_MAGIC = $104D
SAVE_PLAYER = $1051
SAVE_PRNG = SAVE_PLAYER + (ev_dmg-p_col+1)
SAVE_CHECK = $109F
PREFS = $1F10
.segment "STATECODE"

profiles_init:
        LDA profiles_ready
        BNE @done
        INC profiles_ready
        LDA PREFS
        CMP #'M'
        BNE @done
        LDA PREFS+1
        CMP #'Z'
        BNE @done
        LDA PREFS+2
        CMP #'P'
        BNE @done
        LDA PREFS+3
        CMP #1
        BNE @done
        LDA PREFS+4
        EOR PREFS+5
        EOR PREFS+6
        CMP PREFS+7
        BNE @done
        LDA PREFS+4
        BEQ @done
        CMP #4
        BCS @done
        STA active_profile
        LDA PREFS+5
        CMP #2
        BCS @done
        STA sound_enabled
        LDA PREFS+6
        CMP #4
        BCC @done
        CMP #11
        BCS @done
        AND #1
        BNE @done
        LDA PREFS+6
        STA configured_depth
@done:  RTS

preferences_save:
        LDA preferences_dirty
        BEQ @done
        JSR disk_protected
        BCS @done
        LDA #0
        STA preferences_dirty
        LDA #'M'
        STA PREFS
        LDA #'Z'
        STA PREFS+1
        LDA #'P'
        STA PREFS+2
        LDA #1
        STA PREFS+3
        LDA active_profile
        STA PREFS+4
        EOR sound_enabled
        EOR configured_depth
        STA PREFS+7
        LDA sound_enabled
        STA PREFS+5
        LDA configured_depth
        STA PREFS+6
        LDA #<prefs_command
        LDY #>prefs_command
        JMP checkpoint_command
@done:  RTS

profile_load:
        LDA #0
        STA save_available
        STA active_game
        LDA active_profile
        CLC
        ADC #'0'
        STA load_command+14
        LDA #<load_command
        LDY #>load_command
        JSR checkpoint_command
        LDA SAVE_MAGIC
        CMP #'M'
        BNE @invalid
        LDA SAVE_MAGIC+1
        CMP #'Z'
        BNE @invalid
        LDA SAVE_MAGIC+2
        CMP #'S'
        BNE @invalid
        LDA SAVE_MAGIC+3
        CMP #1
        BNE @invalid
        JSR checkpoint_sum
        BNE @invalid
        JMP @validate
@invalid:
        RTS
@validate:
        ; Reject impossible player coordinates/HP/state before restoring.
        LDA SAVE_PLAYER+(p_col-p_col)
        CMP #NCOLS
        BCS @done
        LDA SAVE_PLAYER+(p_row-p_col)
        CMP #NROWS
        BCS @done
        LDA SAVE_PLAYER+(p_face-p_col)
        CMP #4
        BCS @done
        LDA SAVE_PLAYER+(p_hp-p_col)
        BEQ @done
        CMP #31
        BCS @done
        LDA SAVE_PLAYER+(p_floor-p_col)
        BEQ @done
        CMP #4
        BCS @done
        LDA SAVE_PLAYER+(gstate-p_col)
        CMP #ST_PLAY3D
        BCC @done
        CMP #ST_COMBAT+1
        BCS @done
        LDA SAVE_PRNG
        ORA SAVE_PRNG+1
        BEQ @done
        LDX #NUM_MOBS-1
@mobs:  LDA mob_col,X
        CMP #NCOLS
        BCS @done
        LDA mob_row,X
        CMP #NROWS
        BCS @done
        LDA mob_type,X
        CMP #MOB_DEAD
        BEQ @next_mob
        CMP #4
        BCS @done
        LDA mob_hp,X
        BEQ @done
@next_mob:
        DEX
        BPL @mobs
        LDA SAVE_PLAYER+(gstate-p_col)
        CMP #ST_COMBAT
        BNE @valid
        LDX SAVE_PLAYER+(cur_mob-p_col)
        CPX #NUM_MOBS
        BCS @done
        LDA mob_type,X
        CMP #MOB_DEAD
        BEQ @done
@valid: INC save_available
@done:  RTS

resume_game:
        JSR prepare_text
        LDX #(ev_dmg-p_col)
@player:
        LDA SAVE_PLAYER,X
        STA p_col,X
        DEX
        BPL @player
        LDA SAVE_PRNG
        STA prng_lo
        LDA SAVE_PRNG+1
        STA prng_hi
        LDA #0
        STA quit_flag
        LDA #0
        STA combat_resuming
        LDA gstate
        CMP #ST_COMBAT
        BNE @ready
        INC combat_resuming
@ready: LDA #1
        STA active_game
        LDA #HUD_BOTH
        STA hud_dirty
        LDA #<str_resumed
        LDX #>str_resumed
        JSR set_msg
        ; A shop checkpoint resumes its purchases before descending.
        LDA p_col
        CMP #NCOLS-1
        BNE @play
        LDA p_row
        CMP #NROWS-1
        BNE @play
        LDA p_floor
        CMP #LAST_FLOOR
        BEQ @play
        LDA p_relic
        BEQ @play
        JSR floor_shop
        LDA quit_flag
        BNE @done
        INC p_floor
        JSR start_floor
@play:  JMP play_loop
@done:  RTS

prepare_text:
        LDA #<str_text_load
        LDY #>str_text_load
        JMP checkpoint_command

manual_save:
        LDA active_game
        BEQ @unavailable
        JSR disk_protected
        BCS @unavailable
        LDX #(ev_dmg-p_col)
@player:
        LDA p_col,X
        STA SAVE_PLAYER,X
        DEX
        BPL @player
        LDA #0
        STA SAVE_PLAYER+(quit_flag-p_col)
        LDA prng_lo
        STA SAVE_PRNG
        LDA prng_hi
        STA SAVE_PRNG+1
        LDA #'M'
        STA SAVE_MAGIC
        LDA #'Z'
        STA SAVE_MAGIC+1
        LDA #'S'
        STA SAVE_MAGIC+2
        LDA #1
        STA SAVE_MAGIC+3
        LDA #0
        STA SAVE_CHECK
        JSR checkpoint_sum
        STA SAVE_CHECK
        JSR checkpoint_write
        LDA #1
        STA save_available
        SEC
        RTS
@unavailable:
        CLC
        RTS

; Ending a run leaves its last manual checkpoint available on disk.
finish_game:
        LDA #0
        STA active_game
        RTS

checkpoint_write:
        LDA active_profile
        CLC
        ADC #'0'
        STA save_command+14
        LDA #<save_command
        LDY #>save_command
checkpoint_command:
        PHA
        TYA
        PHA
        JSR dos_cmd_new
        PLA
        TAY
        PLA
        JSR dos_cmd_add
        JMP dos_cmd_run

checkpoint_sum:
        LDX #0
        LDA #0
@xor:   EOR grid,X
        INX
        BNE @xor
        CMP #0
        RTS

load_command:  .byte "BLOAD MAZESAVE1",0
save_command:  .byte "BSAVE MAZESAVE1,A$1000,L$0100",0
prefs_command: .byte "BSAVE MAZEPREFS,A$1F10,L$0008",0
str_resumed:   .byte "YOUR JOURNEY CONTINUES",0
