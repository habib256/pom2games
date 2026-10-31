; frame_end(): called once a frame, right after dhgr_spr_present (the test's
; probe point: tests/test_dhgr_action.py). An RTS.
.export _frame_end
.code
_frame_end:
        rts
