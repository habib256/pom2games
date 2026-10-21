# annotations.py -- names, comments and data layout for the PHYSICS disassembly.
# Everything here was derived by reading the code; names marked "?" in the
# comments are guesses about intent that the code does not prove.

# ---------------------------------------------------------------- hardware
HW = {
    0xC000: 'KBD', 0xC010: 'KBDSTRB', 0xC019: 'RDVBLBAR',
    0xC050: 'TXTCLR', 0xC052: 'MIXCLR', 0xC054: 'LOWSCR', 0xC055: 'HISCR',
    0xC057: 'HIRES', 0xC08B: 'LCRAM1RW', 0xC004: 'RAMWRTOFF', 0xC005: 'RAMWRTON',
    0xFCA8: 'WAIT',
    # Disk II, indexed by slot*16 (X) or slot*16+phase*2 (Y)
    0xC080: 'PHASE0OFF', 0xC081: 'PHASE0ON', 0xC088: 'MOTOROFF', 0xC08C: 'Q6L',
}

# self-modified operands: operand byte address -> symbol defined there
SMC_DEF = {
    # erase_ball: three LDA abs,X whose base address is patched per ball
    0x0D48: 'ers_rowlo', 0x0D4F: 'ers_rowhi', 0x0D54: 'ers_bufhi',
    # draw_ball: two row-address loads and three sprite-column ORAs
    0x0DF6: 'drw_rowlo', 0x0DFB: 'drw_rowhi',
    0x0E04: 'drw_spr0', 0x0E0C: 'drw_spr1', 0x0E14: 'drw_spr2',
    # mul8x8: low bytes of the four square-table bases are patched with A
    0x0F88: 'm8_sqp_lo', 0x0F8B: 'm8_sqm_lo', 0x0F90: 'm8_sqp_hi', 0x0F93: 'm8_sqm_hi',
    # mul8x16: same trick, two products
    0x0FB6: 'm16a_sqp_lo', 0x0FB9: 'm16a_sqm_lo', 0x0FBE: 'm16a_sqp_hi', 0x0FC1: 'm16a_sqm_hi',
    0x0FC9: 'm16b_sqp_lo', 0x0FCC: 'm16b_sqm_lo', 0x0FD1: 'm16b_sqp_hi', 0x0FD4: 'm16b_sqm_hi',
    # loader: text-record destination
    0x91AB: 'txt_dst',
}

# ---------------------------------------------------------------- zero page
ZP_BOOT = {
    0x00: 'ld_dst', 0x02: 'ld_htrack', 0x03: 'ld_ntracks', 0x04: 'ld_page',
    0x05: 'ld_aux', 0x06: 'ld_lastcnt', 0x07: 'ld_want', 0x08: 'ld_left',
    0x09: 'ld_tmp', 0x0A: 'ld_tmp2', 0x0B: 'ld_tmp3', 0x0C: 'ld_entry',
    0x0D: 'ld_track', 0x0E: 'ld_ticks', 0x0F: 'ld_secs', 0x10: 'ld_addr',
    0x11: 'ld_addr_trk', 0x12: 'ld_addr_sec', 0x1A: 'ld_lastsec',
    0x1B: 'ld_scr', 0x1D: 'ld_txt', 0x1F: 'ld_trkcount', 0x30: 'ld_secmap',
    0x40: 'ld_done', 0xA0: 'ld_aux2',
    0x26: 'prom_buf', 0x27: 'prom_bufhi', 0x2B: 'prom_slot16',
    0x3D: 'prom_sector', 0x3E: 'prom_vec',
}
ZPDOC_BOOT = {
    0x00: 'ptr: destination page of the sector being decoded',
    0x02: 'current head position in half-tracks',
    0x03: 'tracks left in the current load-table entry',
    0x04: 'destination page for physical sector 0 of the current track',
    0x05: 'nonzero = write to auxiliary RAM (unused: all entries are 0)',
    0x06: 'number of sectors to read on the LAST track of the entry',
    0x07: 'sectors wanted on this track (16, or ld_lastcnt)',
    0x08: 'sectors still to read on this track',
    0x09: 'scratch / nibble index',
    0x0A: 'target half-track / checksum',
    0x0B: 'scratch (4&4 decode)',
    0x0C: 'offset of the current entry in load_table',
    0x0D: 'current track number',
    0x0E: 'elapsed-time accumulator, in sector times (80 = one second)',
    0x0F: 'elapsed seconds shown on screen (max 99)',
    0x10: 'address field: volume, track, sector, checksum ($10-$13)',
    0x11: 'address field track',
    0x12: 'address field sector (physical)',
    0x1A: 'sector number of the previous address field',
    0x1B: 'ptr: text-screen row for print_dec2',
    0x1D: 'ptr: walks the text records',
    0x1F: 'tracks started so far (shown as "Track nn")',
    0x30: '16 flags, one per physical sector: 1 = still wanted',
    0x40: 'sectors loaded so far (drives the progress bar)',
    0xA0: '$A0-$F5: the 86 "2-bit" nibbles of a 6&2 sector',
    0x26: 'boot PROM data-buffer pointer (lo)', 0x27: 'boot PROM buffer pointer (hi)',
    0x2B: 'boot slot * 16 (left by the PROM)',
    0x3D: 'sector the PROM is asked to read next', 0x3E: 'PROM read-sector entry ($Cn5C)',
}

ZP_MAIN = {
    0x00: 'ptr', 0x02: 'ptr2', 0x04: 'tmp',
    0x10: 'bx', 0x12: 'by', 0x14: 'bvx', 0x16: 'bvy',
    0x18: 'boxi', 0x19: 'cptx', 0x1B: 'cpty', 0x1D: 'dx', 0x1F: 'dy',
    0x21: 'sgnx', 0x22: 'sgny', 0x23: 'dxs', 0x24: 'dys', 0x25: 'dist',
    0x26: 'nx', 0x27: 'ny', 0x28: 'vn', 0x2A: 'vt', 0x2C: 'slip',
    0x2E: 'bspin', 0x36: 'bangle', 0x38: 'barate', 0x3A: 'hitflag',
    0x3B: 'force', 0x3D: 'deepflag', 0x3F: 'side',
    0x42: 'prod', 0x44: 'mtmp', 0x45: 'msign', 0x46: 'marg', 0x48: 'mres',
    0x4A: 'prod24', 0x4B: 'prod24m', 0x4C: 'prod24h', 0x4D: 'num', 0x4E: 'numhi',
    0x51: 'root', 0x52: 'divisor', 0x54: 'hitpos', 0x55: 'hitdepth',
    0x59: 'sdisp', 0x5B: 'svel', 0x5D: 'soft', 0x5E: 'wobble',
    0x60: 'seed', 0x62: 'bstill', 0x63: 'bage', 0x65: 'drawpg', 0x66: 'paused',
    0x67: 'frames', 0x6F: 'scol', 0x70: 'srow', 0x71: 'sshift', 0x73: 'pgoff',
    0x74: 'dbox', 0x75: 'dside', 0x76: 'dpos', 0x77: 'ddepth',
    0x79: 'nside', 0x7A: 'npos', 0x7B: 'ndepth', 0x7C: 'shown_soft', 0x7D: 'shown_wob',
    0x7E: 'dirty_cnt', 0x80: 'rtmp', 0x81: 'rcnt',
    0x86: 'ry0', 0x87: 'ry1', 0x88: 'rx0', 0x89: 'rx1', 0x8A: 'px0', 0x8B: 'px1',
    0x8C: 'setbits', 0x8D: 'prow', 0x8E: 'pxend', 0x8F: 'pmask', 0x90: 'pcnt',
    0x91: 'adepth', 0x92: 'bleft', 0x93: 'btop', 0x94: 'bright', 0x95: 'bbottom',
    0x96: 'dsign', 0x97: 'dtmp', 0x98: 'dlen1', 0x99: 'dlen2',
    0x9A: 'src', 0x9C: 'stride', 0x9D: 'rmaskv', 0x9E: 'colofs',
    0xA0: 'vblprev', 0xA1: 'vblcount', 0xA2: 'vblwant', 0xA3: 'curball',
    0xA4: 'ball_a', 0xA5: 'ball_b', 0xA6: 'nballs', 0xA7: 'spawntmr',
    0xA8: 'boxloop', 0xA9: 'spawnidx', 0xAA: 'pgslot', 0xAB: 'gridptr',
    0xAC: 'rowhi_tab', 0xAE: 'steps', 0xAF: 'stepcnt', 0xB0: 'rect',
}
ZPDOC_MAIN = {
    0x00: 'generic pointer (dst)', 0x02: 'generic pointer (src)', 0x04: 'scratch',
    0x10: 'ball x, 8.8 fixed point pixels (lo=fraction)', 0x12: 'ball y, 8.8',
    0x14: 'ball x velocity, signed 8.8 px/step', 0x16: 'ball y velocity, signed 8.8',
    0x18: 'index of the box being tested', 0x19: 'closest point on box, x (8.8)',
    0x1B: 'closest point on box, y (8.8)', 0x1D: '|dx| ball-to-contact (8.8)',
    0x1F: '|dy| (8.8)', 0x21: 'sign of dx (-1/0/+1)', 0x22: 'sign of dy',
    0x23: '|dx| rescaled to 8 bits (4.4 vs box, 5.3 vs ball)', 0x24: '|dy| rescaled',
    0x25: 'distance, same scale as dxs/dys',
    0x26: 'contact normal x, signed, $40 = 1.0', 0x27: 'contact normal y, $40 = 1.0',
    0x28: 'normal velocity (16-bit signed)', 0x2A: 'tangential velocity (16-bit)',
    0x2C: 'slip = surface speed - spin (16-bit)',
    0x2E: 'ball spin (angular velocity, 16-bit signed)',
    0x36: 'ball rotation angle (16-bit, hi byte: 256 = full turn)',
    0x38: 'angle increment per step derived from spin (16-bit)',
    0x3A: 'set when a box contact changed the spin this step',
    0x3B: 'soft-box spring force (16-bit)', 0x3D: '1 = ball sank > 4 px into a soft box',
    0x3F: 'box side hit: 0 top, 1 bottom, 2 left, 3 right',
    0x42: '16-bit result of mul8x8', 0x44: 'mul scratch', 0x45: 'mul sign (bit 7)',
    0x46: '16-bit signed multiplicand', 0x48: '16-bit signed result',
    0x4A: '24-bit product of mul8x16 ($4A-$4C)', 0x4D: '16-bit dividend / isqrt input',
    0x51: 'isqrt result', 0x52: 'divisor', 0x54: 'contact coordinate along the box side',
    0x55: 'how deep the ball presses the side, 0-4 px',
    0x59: 'spring displacement temp (16-bit)', 0x5B: 'spring velocity temp (16-bit)',
    0x5D: 'left slider 0-7 (up/down arrows): box softness', 0x5E: 'right slider 0-7 (left/right arrows): box wobble',
    0x60: '16-bit LFSR random seed', 0x62: 'steps the ball has been (nearly) still',
    0x63: 'ball age in steps (16-bit)', 0x65: 'page being drawn: 0 = HGR1, 1 = HGR2',
    0x66: 'pause flag (P key)', 0x67: '16-bit frame counter (written, never read)',
    0x6F: 'sprite byte column', 0x70: 'sprite top row', 0x71: 'sprite pre-shift offset (shift*12)',
    0x73: '$00 or $20: added to row-hi bytes to address the draw page',
    0x74: 'box being redrawn', 0x75: 'its dent side', 0x76: 'dent position', 0x77: 'dent depth (signed)',
    0x79: 'new dent side', 0x7A: 'new dent position', 0x7B: 'new dent depth',
    0x7C: 'softness value the sliders were last drawn with', 0x7D: 'wobble value last drawn',
    0x7E: 'dirty-rect count for HGR1 ($7E) and HGR2 ($7F)',
    0x80: 'dirty-rect index', 0x81: 'dirty-rect counter',
    0x86: 'rect top row', 0x87: 'rect bottom row', 0x88: 'rect left byte', 0x89: 'rect right byte',
    0x8A: 'span left x (px)', 0x8B: 'span right x (px)', 0x8C: '1 = set pixels, 0 = clear',
    0x8D: 'current row', 0x8E: 'span end byte', 0x8F: 'pixel mask', 0x90: 'loop counter',
    0x91: '|dent depth|', 0x92: 'box left', 0x93: 'box top', 0x94: 'box right', 0x95: 'box bottom',
    0x96: '0 = dent pushed inwards, 2 = outwards', 0x97: 'scratch', 0x98: 'scratch', 0x99: 'scratch',
    0x9A: 'source pointer', 0x9C: 'source stride / list base', 0x9D: 'width / right mask', 0x9E: 'byte offset',
    0xA0: 'last RDVBLBAR bit 7 seen', 0xA1: 'vertical blanks counted since last flip',
    0xA2: 'blanks to wait for', 0xA3: 'current ball 0-2', 0xA4: 'pair: first ball', 0xA5: 'pair: second ball',
    0xA6: 'balls in play (1-3)', 0xA7: 'steps since last auto-spawn', 0xA8: 'box loop index 4-10',
    0xA9: 'ball index being (re)spawned', 0xAA: '0 or 3: per-page slot in the drawn-ball arrays',
    0xAB: 'index into grid_lists', 0xAC: 'ptr to the row-hi table of the draw page',
    0xAE: 'physics steps to run next frame (= blanks elapsed, 2-4)', 0xAF: 'step counter', 0xB0: 'ball rect: top, bottom, left, right ($B0-$B3)',
}

# ---------------------------------------------------------------- loader
LABELS_BOOT = {
    0x0800: 'boot_nsect', 0x0801: 'boot_entry', 0x0816: 'boot_next', 0x0825: 'relocate',
    0x9045: 'loader', 0x905C: 'next_entry', 0x907C: 'next_track', 0x9091: 'build_map',
    0x909E: 'read_loop', 0x90BF: 'loader_done', 0x90C7: 'seek_track', 0x910B: 'phase_y',
    0x9115: 'read_one', 0x9164: 'tick_clock', 0x9179: 'draw_screen', 0x9194: 'next_record',
    0x91BC: 'draw_bar', 0x91D7: 'show_status', 0x9212: 'print_dec2_r4', 0x921A: 'print_dec2',
    0x9230: 'screen_text', 0x928E: 'read_address', 0x92DA: 'read_data', 0x9339: 'post_nibble',
    0x9351: 'total_tracks', 0x9352: 'bar_width', 0x9353: 'load_table',
    0x9396: 'denib_tab',
}
HDR_BOOT = {
    0x0800: """BOOT SECTOR (track 0, sector 0) and the fast loader it pulls in.

The Disk II boot PROM reads T0/S0 to $0800 and jumps to $0801 with
X = slot*16.  The first byte ($01) is the customary sector count.

boot_entry re-enters the PROM's read-sector routine ($Cn5C) three times
to load physical sectors 2, 4 and 6 of track 0 into $0900, $0A00 and
$0B00 (DOS-order logical sectors 14, 13, 12).  It then copies the four
pages $0800-$0BFF to $9000-$93FF and continues there, freeing $0800 for
the program itself.""",
    0x0825: """relocate -- still running at $0825: copy $0800-$0BFF to $9000-$93FF,
then continue in the copy.""",
    0x9045: """loader -- read the program described by load_table with a
custom track-at-a-time RWTS, drawing a progress screen as it goes.

For each 5-byte load_table entry (first track, number of tracks, first
page, aux flag, sectors on the last track) it seeks to each track and
reads sectors in whatever order they pass under the head; PHYSICAL
sector n of a track goes to page (first page + 16*track index + n).
When the table's 0 terminator is reached the motor is turned off and
control passes to the program at $0800.""",
    0x90C7: """seek_track -- step the head to track ld_track (one half-track at a
time with the monitor WAIT delay) and charge the move to the
elapsed-time accumulator.""",
    0x910B: 'phase_y -- Y = slot*16 + 2*(half-track & 3): the phase switch offset.',
    0x9115: """read_one -- read the next address field that passes; if it belongs to
this track and its sector is still wanted, read + decode the sector into
its page.  Every address field also advances the elapsed-time clock by
the number of sector times that went by.""",
    0x9179: """draw_screen -- clear text page 1, print the text records, draw the
progress-bar brackets and the "of nn" total.""",
    0x91D7: """show_status -- refresh "Track nn", "Pages left nn",
"Elapsed nn seconds" and the progress bar.""",
    0x9212: 'print_dec2_r4 -- print A (0-99) as two digits at $04A8+Y.',
    0x921A: 'print_dec2 -- print A (0-99) as two high-bit ASCII digits at (ld_scr)+Y.',
    0x9230: """Text records: target address (lo, hi), screen bytes, $00.
A $00 in place of an address ends the list.""",
    0x928E: """read_address -- wait for D5 AA 96, decode the 4&4 volume/track/sector/
checksum into $10-$13.  C=0 if the checksum and the DE epilogue are good.""",
    0x92DA: """read_data -- find D5 AA AD within 32 nibbles, read the 342 6&2
nibbles (86 to $A0-$F5 backwards, 256 to $0200) XOR-chained through
denib_tab.  C=0 on a good checksum + DE epilogue.""",
    0x9339: 'post_nibble -- merge the 2-bit and 6-bit halves into 256 bytes at (ld_dst).',
    0x9351: """Loader parameters.  load_table entries:
  first track, track count, first page, aux flag, sectors on last track""",
    0x9396: """denib_tab -- 6&2 disk-byte -> 6-bit value, indexed by the disk byte
($96-$FF).  The code addresses it as denib_tab-$96, i.e. $9300."""
}
CMT_BOOT = {
    0x0801: 'PROM leaves the next buffer page in $27',
    0x0805: 'first entry ($27=9): build the PROM vector',
    0x080D: '$Cn',
    0x0810: '$Cn5C = PROM read-sector entry',
    0x0816: 'four pages loaded?',
    0x0819: 'phys sector = (page-8)*2: 2, 4, 6',
    0x0822: 'PROM reads it and comes back to $0801',
    0x9064: 'track count', 0x9069: 'first page', 0x906E: 'aux flag',
    0x9073: 'sectors on last track',
    0x9085: 'last track of the entry?',
    0x90C2: 'motor off',
    0x90C4: 'run the program',
    0x90D3: 'phase off (current)',
    0x90E7: 'phase on (next)',
    0x90EC: '~1.3 ms', 0x90F7: 'settle', 0x9103: 'release the phase',
    0x9107: '+3 time units per seek',
    0x911C: 'sector times elapsed since the last address field',
    0x914C: 'aux write?', 0x9150: 'RAMWRT on',
    0x9156: 'RAMWRT off',
    0x9166: '80 sector times = 1 second (5 rev/s)',
    0x91AA: 'self-modified: target address',
    0x91BE: "'['", 0x91CB: "']'",
    0x91F8: 'bars = (sectors+7)/8',
    0x9202: 'inverse space = filled', 0x9206: "'.' = empty",
}
OPOV_BOOT = {
    0x9306: 'denib_tab-$96,y', 0x9317: 'denib_tab-$96,y', 0x9327: 'denib_tab-$96,y',
    0x0827: '$0800,y', 0x082D: '$0900,y', 0x0833: '$0A00,y', 0x0839: '$0B00,y',
    0x082A: '$9000,y', 0x0830: '$9100,y', 0x0836: '$9200,y', 0x083C: '$9300,y',
    0x918C: '#<screen_text', 0x9190: '#>screen_text',
}
PRE_BOOT = {
    0x9045: '        .org    $9045            ; from here on we run in the $9000 copy',
}
DATA_BOOT = [
    (0x0800, 0x0801, 'bytes', 1),
    (0x9230, 0x928E, 'gen', '''
        .byte   <$058A, >$058A           ; text row 3, column 10: inverse title
        invtxt  " P H Y S I C S "
        .byte   0
        .byte   <$0708, >$0708           ; row 6, column 8
        hiasc   "Loading, please wait..."
        .byte   0
        .byte   <$04AB, >$04AB           ; row 9, column 3 (numbers at $04B1, $04B7)
        hiasc   "Track    of"
        .byte   0
        .byte   <$04C0, >$04C0           ; row 9, column 24 (number at $04CB)
        hiasc   "Pages left"
        .byte   0
        .byte   <$05AB, >$05AB           ; row 11, column 3 (number at $05B3)
        hiasc   "Elapsed    seconds"
        .byte   0
        .byte   0                        ; end of records
        .byte   0                        ; (unused)'''),
    (0x9351, 0x9353, 'bytes', 1),
    (0x9353, 0x936D, 'gen', '''
;               trk  n  page aux last
        .byte   $01,$02,$20,$00,$10      ; T1-T2   -> $2000-$3FFF  HGR background
        .byte   $03,$02,$60,$00,$0E      ; T3-T4   -> $6000-$7DFF  tables + box art
        .byte   $05,$01,$94,$00,$07      ; T5      -> $9400-$9AFF  box/dirty-rect code
        .byte   $06,$02,$A0,$00,$01      ; T6-T7.0 -> $A000-$B0FF  sprites (copied to LC $D000)
        .byte   $08,$02,$08,$00,$05      ; T8-T9.4 -> $0800-$1CFF  main program
        .byte   $00                      ; end'''),
    (0x936D, 0x9396, 'res0', None),
    (0x9396, 0x9400, 'bytes', 8),
]

# ---------------------------------------------------------------- main
LABELS_MAIN = {
    0x0800: 'start', 0x0803: 'main_loop', 0x0815: 'render', 0x0824: 'physics_step',
    0x0848: 'step_ball_loop', 0x08C5: 'collide_all_pairs', 0x08E2: 'check_ball_life',
    0x0924: 'is_slow', 0x0935: 'load_ball_all', 0x098B: 'save_ball_all',
    0x09E1: 'load_ball', 0x0A2D: 'save_ball', 0x0A79: 'spawn_ball', 0x0ADF: 'key_spawn',
    0x0B13: 'random', 0x0B22: 'render_frame', 0x0C54: 'ball_rect', 0x0C69: 'rect_overlap',
    0x0C8A: 'check_unchanged', 0x0CC7: 'sprite_pos', 0x0D05: 'erase_ball', 0x0D47: 'erase_row',
    0x0D6E: 'draw_ball', 0x0DF5: 'draw_row', 0x0E1E: 'wait_and_flip', 0x0E2C: 'wait_vbl',
    0x0E61: 'set_draw_page', 0x0E6A: 'read_keyboard', 0x0EC8: 'init',
    0x0F5A: 'copy_hgr1', 0x0F78: 'mul8x8', 0x0F98: 'mul8x16', 0x0FE4: 'abs_marg',
    0x0FF6: 'fix_sign', 0x1008: 'mul_dir', 0x1057: 'apply_msign', 0x1072: 'mul_frac',
    0x109A: 'mul_k73', 0x10EA: 'mul_k183', 0x113A: 'mul_k252', 0x118A: 'mul_k230',
    0x11DA: 'mul_int', 0x11FE: 'isqrt16', 0x121B: 'div16by8', 0x1261: 'integrate_ball',
    0x1314: 'collide_boxes', 0x1357: 'collide_box', 0x1458: 'no_contact', 0x1506: 'hard_contact',
    0x15A0: 'contact', 0x15B3: 'normal_speed', 0x15E5: 'friction', 0x168C: 'rebuild_velocity',
    0x1703: 'soft_contact', 0x17D1: 'record_hit', 0x1897: 'round_x', 0x18A0: 'round_y',
    0x18A9: 'box_spring', 0x1993: 'is_small', 0x19A4: 'collide_pair', 0x1C98: 'spin_to_rate',
    0x1CC8: 'main_pad',
    # $9400 module
    0x9400: 'update_boxes', 0x947F: 'get_dent', 0x94B3: 'load_box', 0x94DD: 'dent_rect',
    0x95AD: 'restore_box', 0x9628: 'add_dirty', 0x963F: 'add_rect', 0x96C1: 'restore_dirty',
    0x972B: 'draw_sliders', 0x974E: 'slider_row', 0x9770: 'slider_tick', 0x9782: 'draw_dent',
    0x97F2: 'profile_index', 0x97FC: 'dent_hspan', 0x9825: 'draw_vdent', 0x98D9: 'vdent_corner',
    0x99A0: 'bg_row_ptr', 0x99AF: 'dead_bytes', 0x99B2: 'hspan', 0x99F9: 'plot_masked',
    0x9A0D: 'boxes_pad',
    # tables ($6000)
    0x6000: 'sqr_lo', 0x6200: 'sqr_hi', 0x6400: 'sqrm_lo', 0x6600: 'sqrm_hi',
    0x6800: 'sqrt_seed', 0x6825: 'x_col', 0x6925: 'x_shift',
    0x6A25: 'row_lo', 0x6AE5: 'row_hi1', 0x6BA5: 'row_hi2', 0x6C65: 'row_hibg',
    0x6D25: 'spr_c0_lo', 0x6D35: 'spr_c0_hi', 0x6D45: 'spr_c1_lo', 0x6D55: 'spr_c1_hi',
    0x6D65: 'spr_c2_lo', 0x6D75: 'spr_c2_hi',
    0x6D85: 'box_left', 0x6D90: 'box_top', 0x6D9B: 'box_right', 0x6DA6: 'box_bottom',
    0x6DB1: 'grid_cell', 0x6EB1: 'grid_lists',
    0x6EF7: 'soft_tab', 0x6EFF: 'damp_tab', 0x6F07: 'stiff_tab',
    0x6F0F: 'dent_halfw', 0x6F14: 'dent_rows', 0x6F3C: 'dent_cornA', 0x6F8C: 'dent_cornB',
    0x6FDC: 'xbyte', 0x70DC: 'xbit', 0x71DC: 'lmask', 0x71E3: 'rmask',
    0x71EA: 'bimg_row', 0x71F5: 'bimg_col', 0x7200: 'bimg_w', 0x720B: 'bimg_lo', 0x7216: 'bimg_hi',
    0x7221: 'box_img4', 0x72B7: 'box_img5', 0x731F: 'box_img6', 0x73EB: 'box_img7',
    0x7453: 'box_img8', 0x74E9: 'box_img9', 0x756B: 'box_img10',
    0x75D3: 'vdent_col', 0x75E9: 'vdent_lo', 0x7699: 'vdent_hi', 0x7749: 'vdent_shapes',
    0x7D85: 'tables_pad',
    # LC data (runs at $D000)
    0xD000: 'sprites', 0xDFC0: 'recip_lo', 0xE020: 'recip_hi', 0xE080: 'lc_pad',
}
TABLE_SYMS = [(a, n, LABELS_MAIN[a]) for a, n in [
    (0x6000, 512), (0x6200, 512), (0x6400, 512), (0x6600, 512), (0x6800, 37),
    (0x6825, 256), (0x6925, 256), (0x6A25, 192), (0x6AE5, 192), (0x6BA5, 192), (0x6C65, 192),
    (0x6D25, 16), (0x6D35, 16), (0x6D45, 16), (0x6D55, 16), (0x6D65, 16), (0x6D75, 16),
    (0x6D85, 11), (0x6D90, 11), (0x6D9B, 11), (0x6DA6, 11), (0x6DB1, 256), (0x6EB1, 70),
    (0x6EF7, 8), (0x6EFF, 8), (0x6F07, 8), (0x6F0F, 5), (0x6F14, 40), (0x6F3C, 80), (0x6F8C, 80),
    (0x6FDC, 256), (0x70DC, 256), (0x71DC, 7), (0x71E3, 7), (0x71EA, 11), (0x71F5, 11),
    (0x7200, 11), (0x720B, 11), (0x7216, 11), (0x75D3, 22), (0x75E9, 176), (0x7699, 176),
    (0xD000, 4032), (0xDFC0, 96), (0xE020, 96)]] + [
    # per-ball state arrays (3 entries each) and box/page arrays in page 2/3
    (0x9353, 26, 'load_table'),
    (0x0200, 3, 'ob_xlo'), (0x0203, 3, 'ob_xhi'), (0x0206, 3, 'ob_ylo'), (0x0209, 3, 'ob_yhi'),
    (0x020C, 3, 'ob_vxlo'), (0x020F, 3, 'ob_vxhi'), (0x0212, 3, 'ob_vylo'), (0x0215, 3, 'ob_vyhi'),
    (0x0218, 3, 'ob_spinlo'), (0x021B, 3, 'ob_spinhi'), (0x021E, 3, 'ob_anglo'), (0x0221, 3, 'ob_anghi'),
    (0x0224, 3, 'ob_ratelo'), (0x0227, 3, 'ob_ratehi'), (0x022A, 3, 'ob_still'),
    (0x022D, 3, 'ob_agelo'), (0x0230, 3, 'ob_agehi'),
    (0x0233, 6, 'dr_valid'), (0x0239, 6, 'dr_col'), (0x023F, 6, 'dr_row'), (0x0245, 6, 'dr_frame'),
    (0x024B, 6, 'dr_shift'),
    (0x0251, 3, 'nw_col'), (0x0254, 3, 'nw_row'), (0x0257, 3, 'nw_frame'), (0x025A, 3, 'nw_shift'),
    (0x025D, 3, 'nw_keep'), (0x0260, 3, 'ob_asleep'), (0x0263, 3, 'ob_hitbox'),
    (0x0266, 3, 'ob_hitside'), (0x0269, 3, 'ob_hitpos'), (0x026C, 3, 'ob_hitdepth'),
    (0x030C, 7, 'bx_hit'), (0x0313, 7, 'bx_hitside'), (0x031A, 7, 'bx_hitpos'), (0x0321, 7, 'bx_hitdepth'),
    (0x0328, 7, 'bx_active'), (0x032F, 7, 'bx_side'), (0x0336, 7, 'bx_pos'),
    (0x033D, 7, 'bx_displo'), (0x0344, 7, 'bx_disphi'), (0x034B, 7, 'bx_vello'), (0x0352, 7, 'bx_velhi'),
    (0x0359, 7, 'bx_dside'), (0x0360, 7, 'bx_dpos'), (0x0367, 7, 'bx_ddepth'),
    (0x0380, 16, 'dl_y0'), (0x0390, 16, 'dl_y1'), (0x03A0, 16, 'dl_x0'), (0x03B0, 16, 'dl_x1'),
]

HDR_MAIN = {
    0x0800: """PHYSICS -- main program, loaded at $0800-$1CFF from tracks 8-9.

Up to three spinning balls fall under gravity, bounce off each other,
off the screen walls and off seven boxes that dent and wobble when hit.
Animation is double-buffered on HGR pages 1/2, timed by the //e vertical
blank flag RDVBLBAR ($C019).""",
    0x0803: """main_loop -- once per displayed frame:
  read_keyboard; unless paused run `steps` physics steps (one per
  vertical blank since the last flip, 2-4), so the simulation runs at
  the display's field rate even though frames take 2+ fields to draw;
  render_frame into the hidden page; wait_and_flip.""",
    0x0824: """physics_step -- one simulation tick for every ball:
  1. integrate_ball for every awake ball (gravity, clamp, move, rotate);
  2. collide_all_pairs (ball/ball);
  3. per ball: collide_boxes (awake) or re-assert its resting contact
     (asleep), check_ball_life, write back;
  4. box_spring for boxes 4-10 (dents relax as damped springs);
  5. while fewer than 3 balls exist, spawn one every 90 steps.""",
    0x08C5: 'collide_all_pairs -- collide_pair for every pair (a < b) of balls in play.',
    0x08E2: """check_ball_life -- age the ball; count steps where |vx| and |vy| are
both under 1/8 px/step.  30 still steps -> put it to sleep (no more
integration); 90 still steps or an age of 1500 steps -> respawn it.""",
    0x0924: """is_slow -- C=0 when the 16-bit signed value at $00,X lies within
+-$20 (+-1/8 px/step).""",
    0x0935: """load_ball_all -- copy ball X's state (incl. rotation angle) from the
object arrays at $0200 into zero page.""",
    0x098B: 'save_ball_all -- inverse of load_ball_all.',
    0x09E1: 'load_ball -- as load_ball_all but without the rotation angle.',
    0x0A2D: 'save_ball -- inverse of load_ball.',
    0x0A79: """spawn_ball -- (re)create ball X at a random x (16-239), y = 10, with a
small random horizontal speed (+-1/8 px) and a random spin.""",
    0x0ADF: """key_spawn -- SPACE: add a ball if fewer than 3, else respawn the
oldest one.""",
    0x0B13: """random -- 16-bit Galois LFSR (taps $B400), returns the low byte in A.
Seeded with $AD3C at init, so every run plays the same sequence.""",
    0x0B22: """render_frame -- draw the hidden page:
  * update_boxes ($9400) redraws changed dents/sliders into the clean
    background copy at $A000 and queues dirty rectangles;
  * work out each ball's sprite position; a ball whose sprite is
    identical to what this page already shows, and that no dirty rect
    touches, is left alone (nw_keep) -- a moved ball overlapping it
    forces it to be redrawn too;
  * restore_dirty copies the dirty rects from $A000 to the page;
  * erase_ball (copy back from $A000) then draw_ball for the others.
The VBL counter is polled throughout because nothing else watches it.""",
    0x0C54: 'ball_rect -- $B0-$B3 = row span (12 rows) and byte span (3 bytes) of nw_* ball X.',
    0x0C69: 'rect_overlap -- C=1 if the drawn sprite in slot Y overlaps the rect in $B0-$B3.',
    0x0C8A: """check_unchanged -- ball X's sprite is unchanged on this page; mark it
nw_keep unless one of this page's pending dirty rects overlaps it.""",
    0x0CC7: """sprite_pos -- from ball X (8.8 position in $10-$13, angle in $36/$37)
compute rotation frame (0-15), byte column, pre-shift and top row.""",
    0x0D05: """erase_ball -- if slot Y holds a drawn sprite on this page, copy its
12x3 bytes back from the clean background at $A000.  The three LDA
operands are patched with the row tables offset by the sprite row.""",
    0x0D6E: """draw_ball -- remember ball X's sprite in this page's slot, then OR its
12 rows x 3 bytes into the page.  The sprite comes from the pre-shifted,
pre-rotated set in language-card RAM ($D000): the three ORA operands are
patched to point at frame/column/shift.""",
    0x0E1E: """wait_and_flip -- wait for the start of a vertical blank, and for at
least two blanks since the last flip (so 30 fps max on NTSC, 25 on PAL),
then show the page just drawn and switch drawing to the other one.
The number of blanks that elapsed (2-4, capped) becomes the next
frame's physics step count: one step per field.

wait_vbl is the frame clock.  It depends on the //e meaning of
RDVBLBAR: bit 7 toggles every frame and is 0 during vertical blank;
each 1->0 edge increments vblcount.  On a //c, $C019 bit 7 is the
VBL *interrupt* flag, which only latches when VBL interrupts are enabled
through the IOU (this program never does, and runs with SEI).  The bit
never changes, vblcount stays 0, and this loop spins forever: the
program freezes on its first frame.""",
    0x0E61: 'set_draw_page -- pgoff = $20 when drawing HGR2, $00 for HGR1.',
    0x0E6A: """read_keyboard --
  up / down arrows   : softness slider -/+ (and wake all balls)
  left / right arrows: wobble slider -/+
  SPACE              : spawn a ball (key_spawn)
  P                  : pause / resume""",
    0x0EC8: """init -- copy the sprite + reciprocal data ($A000-$B0FF) into
language-card RAM bank 1 at $D000-$E0FF, copy the HGR background to
page 2 and to the clean copy at $A000, switch to full-screen HGR page 1,
clear the object arrays, set the sliders (softness 3, wobble 5), spawn
the first ball and enter main_loop.""",
    0x0F5A: 'copy_hgr1 -- copy $2000-$3FFF to page A*256 ($4000 or $A000).',
    0x0F78: """mul8x8 -- unsigned A*X -> prod (16 bit), by quarter squares:
  A*X = sq(X+A) - sq(X-A),  sq(n) = floor(n^2/4)
The table bases are patched with A so indexing by X gives X+A and X-A.""",
    0x0F98: """mul8x16 -- unsigned A * marg (16 bit) -> prod24 ($4A-$4C), two
quarter-square products added with the middle byte aligned.""",
    0x0FE4: 'abs_marg -- marg = |marg|.',
    0x0FF6: 'fix_sign -- negate mres if msign bit 7 is set.',
    0x1008: """mul_dir -- mres = marg * A / 64, A a signed direction component
($40 = +1.0, $C0 = -1.0).  0, +1 and -1 are short-cut.""",
    0x1057: 'apply_msign -- mres = +-(prod24 bits 8-23) according to msign.',
    0x1072: 'mul_frac -- mres = marg * A / 256 (marg signed, A unsigned fraction).',
    0x109A: """mul_k73 / mul_k183 / mul_k252 / mul_k230 -- mres = marg * k / 256
for a fixed k, using quarter-square tables pre-offset by k (one table
lookup pair per byte instead of patching).""",
    0x11DA: 'mul_int -- mres = marg * A (signed 16 x unsigned 8, low 16 bits kept).',
    0x11FE: """isqrt16 -- root = floor(sqrt(num)): start from sqrt_seed[num hi] and
step up while (root+1)^2 <= num.""",
    0x121B: """div16by8 -- num = num / A (8-bit quotient), via the 65536/A reciprocal
table in LC RAM, then a one-step correction.""",
    0x1261: """integrate_ball -- vy += $18 (gravity, 0.094 px/step^2); clamp vx and
vy to +-4 px/step; x += vx; y += vy; angle += angle rate.""",
    0x1314: """collide_boxes -- look up the ball's 16x16-pixel grid cell, walk that
cell's $FF-terminated list of boxes (0-3 are the screen walls, 4-10
the boxes) and collide_box with each.  If any contact touched the
ball's spin, recompute its angle rate.""",
    0x1357: """collide_box -- closest point of box X to the ball, distance by
quarter squares; contact when closer than 6 px (the ball radius).
Computes the unit normal (nx, ny) then goes to `contact`.""",
    0x1506: """hard_contact -- push the ball out to exactly 6 px from the contact
point; if moving into the box, reflect the normal velocity (x 0.5625,
or stop it below ~0.18 px/step) and apply surface friction/spin.""",
    0x15A0: """contact -- boxes 4-10 behave as soft springs when the softness
slider is above 0 (soft_contact); walls and rigid boxes use hard_contact.""",
    0x15B3: 'normal_speed -- vn = v . n  (returns N = sign).',
    0x15E5: """friction -- tangential speed vt = v . t (t = n rotated), slip =
vt - spin; vt -= slip*73/256, spin += slip*183/256, then both
x 252/256.  Rolling friction that couples spin and travel.""",
    0x168C: 'rebuild_velocity -- v = vn*n + vt*t; flag the spin change (hitflag).',
    0x1703: """soft_contact -- spring contact with a box: penetration p = 6 px - dist.
Deeper than 4 px: put the ball centre 2 px from the surface, use p = 4
and (deepflag) cancel any outward normal speed.  Then
vn = vn*230/256 + p*soft_tab[soft]/256 (a spring pushing out, with
loss), friction as usual, rebuild_velocity, and record_hit stores
which side was hit, where and how deep (0-4 px) so the box can be
drawn dented.""",
    0x1897: 'round_x / round_y -- A = ball x (or y) rounded to a whole pixel.',
    0x18A9: """box_spring -- box X (4-10).  When hit this step, its dent jumps to the
recorded depth (and its spring velocity keeps the difference).  Else,
while active: vel = vel*damp_tab[wobble]/256 - disp*stiff_tab[soft]/256,
disp += vel; when both are within +-1/8 the box comes to rest.""",
    0x1993: 'is_small -- same test as is_slow.',
    0x19A4: """collide_pair -- balls ball_a / ball_b closer than 12 px: wake both,
push each apart along the normal by half the overlap, and if they
approach apply an impulse J = -vn*k along the normal (equal masses):
k = 200/256 when fast (restitution about 0.56), 128/256 when slower
than ~0.18 px/step (fully inelastic).  No spin transfer.""",
    0x1C98: 'spin_to_rate -- angle rate = spin * 6.79 (6 + 202/256).',
    0x1CC8: 'unused tail of the last loaded sector',
    # $9400
    0x9400: """$9400 MODULE (track 5): box dents, slider display, dirty rectangles.

The visible boxes are drawn in the clean background at $A000-$BFFF
(an HGR page that is never displayed).  A changed box is redrawn
there and the changed area queued as a dirty rectangle for EACH of
the two display pages, which copy it on their next render.

update_boxes -- redraw the sliders if a setting changed; for boxes
4-10 compare the current dent (side, position, depth) with the one
drawn: if different, restore the box's pristine image, draw the new
dent and queue the rectangles.""",
    0x947F: """get_dent -- current dent of box X: nside, npos, ndepth = displacement
rounded and clamped to -3..+4 (0 = flat).""",
    0x94B3: 'load_box -- box dbox geometry to $92-$95, |ddepth| and its direction.',
    0x94DD: 'dent_rect -- bounding rectangle (rows ry0-ry1, bytes rx0-rx1) of the dent.',
    0x95AD: 'restore_box -- copy the pristine box image back into $A000 over that rectangle.',
    0x9628: 'add_dirty -- queue rect ry0/ry1/rx0/rx1 for both pages.',
    0x963F: """add_rect -- add the rect to the list at dl_*+X (8 entries); merge with
the last entry if they touch, or into entry 7 when the list is full.
C=1 if a new entry was used.""",
    0x96C1: 'restore_dirty -- copy every queued rect of page X from $A000 to the page, empty the list.',
    0x972B: 'draw_sliders -- draw both 7-tick sliders on rows 6 and 7 of the background.',
    0x974E: 'slider_row -- one pixel row of both sliders.',
    0x9770: 'slider_tick -- store $3E (dash) when C=0, i.e. tick index < setting, else $08 (dot).',
    0x9782: """draw_dent -- draw box dbox's side bent by ddepth at dpos: top/bottom
sides as horizontal spans row by row, left/right sides from the
pre-drawn shapes at vdent_shapes.""",
    0x99A0: 'bg_row_ptr -- ptr = address of row prow in the $A000 background.',
    0x99AF: 'three unreferenced bytes (look like a stray JSR bg_row_ptr)',
    0x99B2: 'hspan -- set (setbits=1) or clear pixels px0..px1 on the row at ptr.',
    0x9A0D: 'unused rest of the last loaded sector',
    # tables
    0x6000: """TABLES (tracks 3-4, $6000-$7DFF).

Quarter squares for mul8x8: sqr = floor(n*n/4) for n = 0..511,
sqrm = floor((n-255)^2/4), so sqrm+X+(~A) = sq(X-A).""",
    0x6800: 'sqrt_seed -- floor(sqrt(h*256)) for h = 0..36 (isqrt16 start values).',
    0x6825: 'x_col / x_shift -- sprite byte column and pre-shift*12 for a ball centre x.',
    0x6A25: 'HGR row address tables: low byte, high byte for page 1, page 2 and the $A000 copy.',
    0x6D25: 'sprite column pointers: 16 rotation frames x 3 byte columns, into LC RAM.',
    0x6D85: 'boxes: left, top, right, bottom.  0-3 are the walls, 4-10 the seven boxes.',
    0x6DB1: """grid_cell -- one byte per 16x16 cell (index = y/16*16 + x/16): offset
into grid_lists of the boxes worth testing in that cell.""",
    0x6EF7: """slider tables, index = slider value 0-7:
  soft_tab  (softness): spring force factor, 0 = rigid boxes
  damp_tab  (wobble):   velocity kept per step by a dent (x/256)
  stiff_tab (softness): dent spring stiffness (x/256)""",
    0x6F0F: 'dent drawing profiles (indexed by |depth|).',
    0x6FDC: 'xbyte / xbit -- byte column and bit of pixel x-12 (x biased by 12).',
    0x71DC: 'lmask / rmask -- HGR pixel masks from bit n to the right/left edge.',
    0x71EA: 'per-box pristine image: top row, left byte, width, pointer.',
    0x7221: 'pristine box images (width x height bytes, rows consecutive).',
    0x75D3: 'left/right side dent shapes: byte offset per (box, side), pointers per (box, side, depth).',
    0x7D85: 'unused tail of the last sector',
    0xD000: """LANGUAGE-CARD DATA: loaded at $A000-$B0FF (tracks 6-7), copied by init
to bank-1 RAM at $D000-$E0FF, assembled here at its run address.

sprites -- the ball, 16 rotation frames x 3 byte columns x 7 pixel
shifts x 12 rows.  Frame f, column c, shift s, row r is at
sprites + f*252 + c*84 + s*12 + r.""",
    0xDFC0: 'reciprocals: 65536/n (n=1 saturates to $FFFF), n = 0..95.',
    0xE080: 'unused',
}
CMT_MAIN = {
    0x0806: 'paused?', 0x081A: 'frames++ (never read)',
    0x084A: 'VBL edge counting (see wait_vbl)',
    0x0862: 'asleep?', 0x0867: 'resting on a box: keep the box pressed',
    0x08B5: '90 steps', 0x08FA: '90 still steps', 0x0907: 'age >= 1500?',
    0x0918: '30 still steps -> sleep',
    0x0A7E: 'x = 16 + rnd*224/256', 0x0AA1: 'y = 10', 0x0AA5: 'vx = (rnd & 63) - 32',
    0x0AC2: 'spin = rnd (signed) * 3',
    0x0B1B: 'LFSR taps',
    0x0B47: 'pick this page\'s slot and row table',
    0x0CD5: 'frame = (angle hi + 8) / 16',
    0x0CF6: 'top row = y - 6',
    0x0D47: 'self-modified: row_lo + row',
    0x0D4E: 'self-modified: row_hi of page + row',
    0x0D53: 'self-modified: row_hibg + row',
    0x0DF5: 'self-modified: row_lo + row',
    0x0DFA: 'self-modified: row_hi of page + row',
    0x0E03: 'self-modified: sprite column 0',
    0x0E0B: 'self-modified: sprite column 1',
    0x0E13: 'self-modified: sprite column 2',
    0x0E20: 'target = max(2, blanks so far + 1)',
    0x0E2C: '//e: bit 7 = 0 during vertical blank',
    0x0E37: 'count 1 -> 0 transitions',
    0x0E45: 'cap the catch-up at 4 steps',
    0x0E53: 'show HGR1',
    0x0E58: 'show HGR2',
    0x0E6F: 'clear strobe', 0x0E72: 'up arrow', 0x0E76: 'down arrow',
    0x0E9E: 'left arrow', 0x0EA9: 'right arrow',
    0x0EB6: 'SPACE ($A0) -> 0', 0x0EBD: "'P' / 'p'",
    0x0ECD: 'LC bank 1: read RAM, write RAM', 0x0EE3: '17 pages $A000 -> $D000',
    0x0EF5: 'background -> HGR2', 0x0EFA: 'background -> clean copy at $A000',
    0x0EFF: 'graphics', 0x0F02: 'full screen', 0x0F05: 'hi-res', 0x0F08: 'page 1',
    0x0F2E: 'force the sliders to be drawn', 0x0F3A: 'random seed $AD3C',
    0x1261: 'gravity', 0x1281: 'vx > 4 -> 4', 0x129A: 'vx < -4 -> -4',
    0x1318: 'grid cell = (y & $F0) | x>>4',
    0x1454: 'dist^2 < 36 px^2 ?',
    0x1587: 'restitution 144/256',
    0x15A6: 'box 4-10: soft if slider > 0',
    0x1C20: 'fast: x 200/256', 0x1C24: 'slow: x 128/256',
    0x1CA0: 'spin * 6', 0x1CB5: '+ spin * 202/256',
    0x9733: 'row 6', 0x9738: 'row 7',
    0x95FF: '$A000 copy row', 0x96FF: 'draw page row (+pgoff)', 0x9707: 'source: $A000 copy',
}
OPOV_MAIN = {
    0x0924: '$00,x', 0x092A: '$01,x', 0x1993: '$00,x', 0x1999: '$01,x',
    0x0ED7: '#>$A000', 0x0EDF: '#>sprites', 0x0EF5: '#$40', 0x0EFA: '#$A0',
    0x0B4F: '#<row_hi1', 0x0B51: '#>row_hi1', 0x0B57: '#<row_hi2', 0x0B59: '#>row_hi2',
    0x0D19: '#<row_lo', 0x0D20: '#>row_lo', 0x0D29: '#<row_hibg', 0x0D30: '#>row_hibg',
    0x0DA3: '#<row_lo', 0x0DAA: '#>row_lo',
    0x0F3A: '#<$AD3C', 0x0F3E: '#>$AD3C',
}
PRE_MAIN = {}
# sprite set: one comment per (frame, column)
for f in range(16):
    for c in range(3):
        PRE_MAIN[0xD000 + f * 252 + c * 84] = (
            '; frame %d (%.1f deg), byte column %d: 7 shifts x 12 rows' % (f, f * 22.5, c))

GEN_SQR = '''
sqr_lo:
        .repeat 512, N
        .byte   <(N*N/4)
        .endrepeat
sqr_hi:
        .repeat 512, N
        .byte   >(N*N/4)
        .endrepeat
sqrm_lo:
        .repeat 512, N
        .byte   <((N-255)*(N-255)/4)
        .endrepeat
sqrm_hi:
        .repeat 512, N
        .byte   >((N-255)*(N-255)/4)
        .endrepeat'''
GEN_ROWS = '''
; HGR row address = $2000 + (y & 7)*$400 + ((y >> 3) & 7)*$80 + (y >> 6)*$28
row_lo:
        .repeat 192, ROW
        .byte   <($2000 + (ROW & 7) * $400 + ((ROW >> 3) & 7) * $80 + (ROW >> 6) * $28)
        .endrepeat
row_hi1:
        .repeat 192, ROW
        .byte   >($2000 + (ROW & 7) * $400 + ((ROW >> 3) & 7) * $80 + (ROW >> 6) * $28)
        .endrepeat
row_hi2:                                ; page 2 = page 1 + $2000
        .repeat 192, ROW
        .byte   >(($2000 + (ROW & 7) * $400 + ((ROW >> 3) & 7) * $80 + (ROW >> 6) * $28) + $2000)
        .endrepeat
row_hibg:                               ; clean copy = page 1 + $8000
        .repeat 192, ROW
        .byte   >(($2000 + (ROW & 7) * $400 + ((ROW >> 3) & 7) * $80 + (ROW >> 6) * $28) + $8000)
        .endrepeat'''
GEN_SPRP = '''
spr_c0_lo:
        .repeat 16, F
        .byte   <(sprites + F*252 + 0*84)
        .endrepeat
spr_c0_hi:
        .repeat 16, F
        .byte   >(sprites + F*252 + 0*84)
        .endrepeat
spr_c1_lo:
        .repeat 16, F
        .byte   <(sprites + F*252 + 1*84)
        .endrepeat
spr_c1_hi:
        .repeat 16, F
        .byte   >(sprites + F*252 + 1*84)
        .endrepeat
spr_c2_lo:
        .repeat 16, F
        .byte   <(sprites + F*252 + 2*84)
        .endrepeat
spr_c2_hi:
        .repeat 16, F
        .byte   >(sprites + F*252 + 2*84)
        .endrepeat'''
GEN_RECIP = '''
recip_lo:                               ; 65536/n, n = 0..95 (0 -> 0, 1 -> $FFFF)
        .repeat 96, N
        .if N = 0
        .byte   0
        .elseif N = 1
        .byte   $FF
        .else
        .byte   <(65536 / N)
        .endif
        .endrepeat
recip_hi:
        .repeat 96, N
        .if N = 0
        .byte   0
        .elseif N = 1
        .byte   $FF
        .else
        .byte   >(65536 / N)
        .endif
        .endrepeat'''
GEN_BIMG = '''
bimg_lo:
        .byte   <box_img4, <box_img4, <box_img4, <box_img4  ; walls: unused
        .byte   <box_img4, <box_img5, <box_img6, <box_img7
        .byte   <box_img8, <box_img9, <box_img10
bimg_hi:
        .byte   >box_img4, >box_img4, >box_img4, >box_img4
        .byte   >box_img4, >box_img5, >box_img6, >box_img7
        .byte   >box_img8, >box_img9, >box_img10'''

DATA_MAIN = [
    (0x1CC8, 0x1D00, 'res0', None),
    (0x6000, 0x6800, 'gen', GEN_SQR),
    (0x6800, 0x6825, 'bytes', 8),
    (0x6825, 0x6A25, 'bytes', 16),
    (0x6A25, 0x6D25, 'gen', GEN_ROWS),
    (0x6D25, 0x6D85, 'gen', GEN_SPRP),
    (0x6D85, 0x6DB1, 'bytes', 11),
    (0x6DB1, 0x6EB1, 'bytes', 16),
    (0x6EB1, 0x6EF7, 'bytes', 16),
    (0x6EF7, 0x6F14, 'bytes', 8),
    (0x6F14, 0x6F3C, 'bytes', 8),
    (0x6F3C, 0x6FDC, 'bytes', 16),
    (0x6FDC, 0x71DC, 'bytes', 16),
    (0x71DC, 0x720B, 'bytes', 11),
    (0x720B, 0x7221, 'gen', GEN_BIMG),
    (0x7221, 0x75D3, 'bytes', 10),
    (0x75D3, 0x75E9, 'bytes', 11),
    (0x75E9, 0x7749, 'ptrs', (176, 'vdent_shapes', 0x7749)),
    (0x7749, 0x7D85, 'bytes', 16),
    (0x7D85, 0x7E00, 'res0', None),
    (0x99AF, 0x99B2, 'bytes', 3),
    (0x9A0D, 0x9B00, 'res0', None),
    (0xD000, 0xDFC0, 'bytes', 12),
    (0xDFC0, 0xE080, 'gen', GEN_RECIP),
    (0xE080, 0xE100, 'res0', None),
]
# 'gen' entries print their own labels; suppress the generic label line
for s, e, kind, arg in DATA_MAIN:
    if kind == 'gen':
        pass

HEAD_MAIN = '''; main.s -- PHYSICS main program ($0800-$1CFF, tracks 8-9)
; Regenerated by tools/gen.py from the original disk; see README.md.
; Included by physics.s (segment MAIN).
'''

FILES = {
    'boot.s': dict(boot=True, zp=ZP_BOOT, head='''; boot.s -- PHYSICS boot sector + fast loader (track 0, physical sectors 0,2,4,6)
; Regenerated by tools/gen.py from the original disk; see README.md.
; Assembles to 1024 bytes: page 0 = T0 phys 0, page 1 = phys 2, 2 = phys 4, 3 = phys 6.

        .setcpu "6502"
        .include "hw.inc"
        .include "zp_boot.inc"

; high-bit ASCII string (normal video on the text screen)
.macro  hiasc str
        .repeat .strlen(str), I
        .byte   .strat(str, I) | $80
        .endrepeat
.endmacro
; inverse-video string (character & $3F)
.macro  invtxt str
        .repeat .strlen(str), I
        .byte   .strat(str, I) & $3F
        .endrepeat
.endmacro

        .segment "BOOT"
        .org    $0800
''', parts=[('boot1', 0x800, 0x845), ('boot2', 0x9045, 0x9400)]),
    'main.s': dict(zp=ZP_MAIN, head=HEAD_MAIN, parts=[('main', 0x800, 0x1D00)]),
    'boxes.s': dict(zp=ZP_MAIN, head='''; boxes.s -- box dents, sliders and dirty rectangles ($9400-$9AFF, track 5)
; Regenerated by tools/gen.py from the original disk; see README.md.
''', parts=[('main', 0x9400, 0x9B00)]),
    'tables.s': dict(zp=ZP_MAIN, head='''; tables.s -- lookup tables and box artwork ($6000-$7DFF, tracks 3-4)
; Regenerated by tools/gen.py from the original disk; see README.md.
''', parts=[('main', 0x6000, 0x7E00)]),
    'lcdata.s': dict(zp=ZP_MAIN, head='''; lcdata.s -- ball sprites + reciprocal table.  Loaded at $A000-$B0FF
; (tracks 6-7), copied to language-card RAM by init; runs at $D000-$E0FF.
; Regenerated by tools/gen.py from the original disk; see README.md.
''', parts=[('main', 0xD000, 0xE100)]),
}

TABLE_SYMS = [(a, a + n, name) for a, n, name in TABLE_SYMS]
