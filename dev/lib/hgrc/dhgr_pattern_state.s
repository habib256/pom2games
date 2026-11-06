; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Independently linked DHGR parameter state.
; Four-byte order: aux even / main even / aux odd / main odd.
.export _dhgr_pattern
.bss
_dhgr_pattern: .res 4
