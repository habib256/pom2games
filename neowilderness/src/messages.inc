; messages.inc -- the game's own texts (the original's are not reused).
; A message is a NUL-terminated string; "|" starts a new line, "^" inserts the
; inventory name (or typed noun), "#" the number in msgnum, "$" accessible
; stock, "!" the travel stop reason, "~" the first unknown word (12 chars).
; Three lines, 37 characters after the indicator/indent; the last column is
; reserved and expanded names are clipped to prevent scrolling.

m_edge:     .byte   "STOP HERE. THE MAP ENDS AHEAD.", 0
m_water:    .byte   "WATER AHEAD. USE SWIM TO CROSS.", 0
m_shore:    .byte   "YOU HAVE REACHED LAND. USE WALK.", 0
m_no_water: .byte   "NO WATER AHEAD. USE WALK.", 0
m_dark:     .byte   "IT IS TOO DARK TO TRAVEL.", 0
.segment "ENVIRON"
; Meals and drinks already have the simulation loaded when printing results.
m_ate:      .byte   "YOU ATE # OUNCES.|ACCESSIBLE BEFORE: $ OZ.", 0
m_drank:    .byte   "YOU DRANK # OUNCES.|ACCESSIBLE BEFORE: $ OZ.", 0
.segment "TEXT"

; Written by module_fauna_cause (PROJECT) before it is shown: what stopped
; the action, an animal or a resource found (27 bytes: the longest is
; "RATTLESNAKE IN YOUR AREA!").
m_fauna_stop: .byte "WILDLIFE IN YOUR AREA!",0
        .res    27 - 23

m_duration_end: .byte "REQUESTED TRAVEL TIME ENDED.",0
m_pace: .byte "TERRAIN OR PACE PREVENTS THIS STEP.",0
m_escape_end: .byte "STOPPED BY ESC.",0
m_short_end: .byte "NOT ENOUGH TIME FOR THE NEXT STEP.",0
.segment "RODATA"
travel_reason_lo: .byte <m_duration_end,<m_water,<m_shore,<m_dark,<m_edge,<m_fauna_stop,<m_escape_end,<m_pace,<m_no_water,<m_short_end
.segment "TEXT"
travel_reason_hi: .byte >m_duration_end,>m_water,>m_shore,>m_dark,>m_edge,>m_fauna_stop,>m_escape_end,>m_pace,>m_no_water,>m_short_end

.segment "ITEMS"
m_taken:    .byte   "PACK: ^", 0
m_carried:  .byte   "HAND: ^", 0
m_worn:     .byte   "WEARING: ^", 0
m_notwear:  .byte   "^|YOU CAN'T WEAR THAT.", 0
m_dropped:  .byte   "GROUND: ^", 0
m_pile:     .byte   "COLLECT THE OTHER GROUND STOCK FIRST.", 0
m_notthere: .byte   "^|NOT ACCESSIBLE HERE.|CHECK INVENTORY OR MOVE CLOSER.", 0
m_object: .byte "NAME AN ITEM. EXAMPLES:|GET HAT / WEAR PARKA / DROP AXE.",0
m_selfpack: .byte "BACKPACK CANNOT HOLD ITSELF.|USE CARRY BACKPACK.",0
m_needpack: .byte "BACKPACK NEEDED.|PICK IT UP WITH CARRY BACKPACK.",0
m_needcan: .byte "CANTEEN NEEDED.|PICK IT UP WITH GET CANTEEN.",0
m_empty_pack: .byte "EMPTY THE BACKPACK BEFORE DROPPING.|DROP ITS CONTENTS FIRST.",0
m_empty_can: .byte "EMPTY THE CANTEEN BEFORE DROPPING.|DRINK WATER OR DROP WATER.",0
m_weight: .byte "TRANSFER REFUSED: WEIGHT.",0
m_volume: .byte "TRANSFER REFUSED: VOLUME.",0
m_both: .byte "TRANSFER REFUSED: WEIGHT + VOLUME.",0
m_overflow: .byte "TRANSFER REFUSED: VALUE TOO LARGE.|REDUCE THE AMOUNT OR THE LOAD.",0
.segment "TEXT"

 .segment "STATUS"
; STATUS and INVENTORY words
w_months:   .byte   "JANFEBMARAPRMAYJUNJULAUGSEPOCTNOVDEC"
.segment "TEXT"
.segment "STATUS"
w_gauge:    .byte   "VERY  SO-SO OKAY  FILLED"
w_enrg:     .byte   "BEAT  TIRED OKAY  GREAT "
w_player:   .byte   "MISERABLEPOOR     OKAY     GOOD     FANTASTIC"
w_period:   .byte   "NIGHTDAWN AM   PM   DUSK "



.segment "TEXT"
.segment "GDATA"
.segment "TEXT"
