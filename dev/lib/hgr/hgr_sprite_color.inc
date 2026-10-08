; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Artifact-colour attributes shared by packed and TMS sprite engines.
; Caller owns sp_cm_ev, sp_cm_od, sp_cbit (zero page). A=HSPR_*; clobbers A,Y.
.ifndef _HGR_SPRITE_COLOR_LOADED_
_HGR_SPRITE_COLOR_LOADED_ = 1
HSPR_WHITE=0
HSPR_GREEN=1
HSPR_ORANGE=2
HSPR_VIOLET=3
HSPR_BLUE=4
.code
hgr_spr16_color_a:
        TAY
        LDA hspr_cmask_ev,Y
        STA sp_cm_ev
        LDA hspr_cmask_od,Y
        STA sp_cm_od
        LDA hspr_cbit,Y
        STA sp_cbit
        RTS
hspr_cmask_ev: .byte $7F,$2A,$2A,$55,$55
hspr_cmask_od: .byte $7F,$55,$55,$2A,$2A
hspr_cbit: .byte $00,$00,$80,$00,$80
.endif
