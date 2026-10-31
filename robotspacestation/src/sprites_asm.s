; Robot Space Station — the room's sprites for the DHGR compositor (zone.h;
; src/sprites.c has the shapes): sprites_room() starts it on the tile map,
; sprites_doors() picks the door and plate tiles, zone_sprites() puts the
; objects in slots 0-3, the drones in 4-5 (their colours 16..19, their
; facing), the technician in 6; tech_pose() picks his shape. PLAY overlay.
.setcpu "65C02"
.export _zone_sprites, _zone_frame, _tech_pose, _pose_s, _pose_f
.export _sprites_room, _sprites_doors
.import _dhgr_spr_set, _dhgr_spr_palette, _dhgr_spr_update
.import _dhgr_spr_init, _dhgr_spr_area, _dhgr_spr_tiles
.import _drone_s, _drone_jet_s, _tech_s, _tech_step_s, _cell_s, _crate_s, _tile_s, _tile_set
.import _obj_n, _obj_kind, _obj_x, _obj_y, _drone_n, _drone_x, _drone_y, _thrust
.import _act_x, _act_y, _screen, _door_open, _tiles, _iobuf
.import pusha, pushax

ROOM_Y = 10                             ; zone.h, ui.h, dhgr.h
ROOM_H = 144
S_ZONE = 1
SHAPE = 6                               ; sizeof (dhgr_shape_t)
LIGHTBLUE = 7
AQUA = 14
YELLOW = 13
GRAY2 = 10
WHITE = 15
GRAY1 = 5
ORANGE = 9

.segment "BSS"
_pose_s: .res 2                         ; tech_pose(): his shape, facing west
_pose_f: .res 1
last_x: .res 1
last_y: .res 1
id:     .res 1                          ; put(): slot, shape, x, y, flags
sp_lo:  .res 1
sp_hi:  .res 1
sx:     .res 1
sy:     .res 1
sf:     .res 1
d:      .res 1
special: .res 4                         ; a drone's colours 16..19
west:   .res 2                          ; each drone faces west

.segment "PLAYDATA"
open_tab:                               ; a door open, a plate pressed
        .addr _tile_s + 9 * SHAPE, _tile_s + 10 * SHAPE
closed_tab:                             ; tiles 4-5 (group 0), 6-7 (group 1)
        .addr _tile_s + 4 * SHAPE, _tile_s + 5 * SHAPE
        .addr _tile_s + 6 * SHAPE, _tile_s + 7 * SHAPE

.segment "PLAYCODE"
; dhgr_spr_set(id, shape, sx, sy, sf)
put:    lda id
        jsr pusha
        lda sp_lo
        ldx sp_hi
        jsr pushax
        lda sx
        jsr pusha
        lda sy
        jsr pusha
        lda sf
        jmp _dhgr_spr_set

; void zone_frame(void): zone_sprites(), then what changed, each byte once.
_zone_frame:
        jsr _zone_sprites
        jmp _dhgr_spr_update

; void zone_sprites(void)
_zone_sprites:
        ldx #0                          ; objects: a cell or a crate (none
@obj:   stx id                          ; from obj_n on)
        stz sp_lo
        stz sp_hi
        stz sf
        cpx _obj_n
        bcs @none
        lda _obj_kind,x
        beq @crate
        lda #<_cell_s
        ldy #>_cell_s
        bra @kind
@crate: lda #<_crate_s
        ldy #>_crate_s
@kind:  sta sp_lo
        sty sp_hi
@none:  lda _obj_x,x
        sta sx
        lda _obj_y,x
        clc
        adc #ROOM_Y
        sta sy
        jsr put
        ldx id
        inx
        cpx #4
        bne @obj
        stz d                           ; the drones (none from drone_n on)
@drone: lda d
        clc
        adc #4
        sta id
        stz sp_lo
        stz sp_hi
        ldx d
        cpx _drone_n
        bcs @put
        ldy #0                          ; Y = 6 * d: thrust[d]
        txa
        beq :+
        ldy #6
:       lda _thrust+3,y                 ; thruster W pushes east, E west: it
        cmp _thrust+1,y                 ; faces that way, else as it was
        beq :+
        lda _thrust+1,y
        sta west,x
:       lda #LIGHTBLUE                  ; A light blue, B aqua
        cpx #0
        beq :+
        lda #AQUA
:       sta special
        lda #GRAY2                      ; the antenna's tip: the radio sends
        ldx _thrust+5,y
        beq :+
        lda #YELLOW
:       sta special+1
        lda #GRAY1                      ; the claw grabs
        ldx _thrust+4,y
        beq :+
        lda #WHITE
:       sta special+2
        lda _thrust,y                   ; the jets: a motor runs
        ora _thrust+1,y
        ora _thrust+2,y
        ora _thrust+3,y
        beq :+
        lda #ORANGE-GRAY1
:       clc
        adc #GRAY1
        sta special+3
        ldx #>_drone_s                  ; pushed sideways: the exhaust
        lda _thrust+3,y
        cmp _thrust+1,y
        beq :+
        lda #<_drone_jet_s
        ldx #>_drone_jet_s
        bra :++
:       lda #<_drone_s
:       sta sp_lo
        stx sp_hi
        lda id
        jsr pusha
        lda #<special
        ldx #>special
        jsr _dhgr_spr_palette
        ldx d
@put:   lda west,x
        sta sf
        lda _drone_x,x
        sta sx
        lda _drone_y,x
        clc
        adc #ROOM_Y
        sta sy
        jsr put
        inc d
        lda d
        cmp #2
        beq :+
        jmp @drone
:
        jsr _tech_pose                  ; the technician, in the room only
        lda #6
        sta id
        lda _pose_f
        sta sf
        lda _act_x
        sta sx
        lda _act_y
        sta sy
        stz sp_lo
        stz sp_hi
        lda _screen
        cmp #S_ZONE
        bne :+
        lda _pose_s
        sta sp_lo
        lda _pose_s+1
        sta sp_hi
:       jmp put

; void tech_pose(void): at act_x, act_y he faces the way he last walked;
; walking, his legs swap every two pixels.
_tech_pose:
        ldx #0                          ; X: he moved
        lda _act_x
        cmp last_x
        beq @y
        inx
        lda #0                          ; west if x < last x
        bcs :+
        inc a
:       sta _pose_f
@y:     lda _act_y
        cmp last_y
        beq :+
        inx
:       lda #<_tech_s
        ldy #>_tech_s
        cpx #0
        beq @set
        lda _act_x
        clc
        adc _act_y
        and #2
        beq @stand
        lda #<_tech_step_s
        ldy #>_tech_step_s
        bra @set
@stand: lda #<_tech_s
@set:   sta _pose_s
        sty _pose_s+1
        lda _act_x
        sta last_x
        lda _act_y
        sta last_y
        rts

; void sprites_doors(void): the door and plate tiles after door_open.
_sprites_doors:
        ldx #0
        jsr @group
        ldx #1
@group: txa                             ; tile_set[4 + 2g], [5 + 2g]: bytes
        asl a                           ; 8 + 4g on
        asl a
        tay
        lda _door_open,x
        beq @closed
        ldx #0
:       lda open_tab,x
        sta _tile_set+8,y
        iny
        inx
        cpx #4
        bne :-
        rts
@closed:
        ldx #4
:       lda closed_tab,y
        sta _tile_set+8,y
        iny
        dex
        bne :-
        rts

; void sprites_room(void): the compositor on the room's tile map, the
; canvas in iobuf (idle meanwhile): dhgr_spr_init(iobuf, 1024, 4),
; dhgr_spr_area(0, ROOM_Y, 139, ROOM_Y + ROOM_H - 1),
; dhgr_spr_tiles(0, ROOM_Y, 8, tiles, 20, tile_set).
_sprites_room:
        lda #<_tile_s                   ; tile_set[k] = &tile_s[k]
        ldx #>_tile_s
        ldy #0
@k:     sta _tile_set,y
        pha
        txa
        sta _tile_set+1,y
        pla
        clc
        adc #SHAPE
        bcc :+
        inx
:       iny
        iny
        cpy #18
        bne @k
        jsr _sprites_doors
        lda #<_iobuf
        ldx #>_iobuf
        jsr pushax
        lda #<1024
        ldx #>1024
        jsr pushax
        lda #4
        jsr _dhgr_spr_init
        lda #0
        jsr pusha
        lda #ROOM_Y
        jsr pusha
        lda #139
        jsr pusha
        lda #ROOM_Y + ROOM_H - 1
        jsr _dhgr_spr_area
        lda #0
        jsr pusha
        lda #ROOM_Y
        jsr pusha
        lda #8
        jsr pusha
        lda #<_tiles
        ldx #>_tiles
        jsr pushax
        lda #20
        jsr pusha
        lda #<_tile_set
        ldx #>_tile_set
        jmp _dhgr_spr_tiles
