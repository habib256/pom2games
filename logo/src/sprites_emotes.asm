; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; The emote patterns LOGO draws, as one of its modules: the data is
; dev/lib/tms9918/sprites_emotes.asm (RODATA), which assembles the patterns
; named here only.
.export serious_pat, happy_pat, excited_pat, sad_pat, hurt_pat, angry_pat
.export upset_pat, smug_pat, sick_pat, sleeping_pat, yarr_pat, nerd_pat
.export bird1_pat, bird2_pat, heart_pat
.include "../../dev/lib/tms9918/sprites_emotes.asm"
