; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Compatibility initializer. Only this entry extracts the default pool.
; A=raw double-buffer flag. Tail-call with the six-byte init_pool frame;
; its state and defaults retain independent C compilation settings.
.export _hgr_spr_init
.import _hgr_spr_init_pool,_spr_default_pool,_spr_default_bytes,_spr_default_capacity,_spr_default_count
.import pusha,pushax
.code
_hgr_spr_init:
 jsr pusha
 lda #<_spr_default_pool
 ldx #>_spr_default_pool
 jsr pushax
 lda _spr_default_bytes
 ldx _spr_default_bytes+1
 jsr pushax
 lda _spr_default_count
 jsr pusha
 lda _spr_default_capacity
 jmp _hgr_spr_init_pool
