/*
 * snake.c — Snake for the Apple II+ hi-res screen (cc65, DOS 3.3).
 *
 *   Snake for the Apple II / VERHILLE Arnaud 2026
 *   Original: GEN2Snake.c (POM1, Apple-1 + Uncle Bernie's GEN2 HGR card)
 *   Licence: GPL v3 (same as the upstream sketch)
 *
 * The classic game on the 280x192 HIRES screen. Apple II port of POM1's
 * sketchs/gen2/game_snake_telemetry: gameplay and drawing are unchanged (the
 * GEN2 card is the Apple II video subsystem, so its C runtime — src/hgrc —
 * only needed the $C050 soft switches). What changed:
 *   - the POM1 telemetry side channel is gone ($C440-$C443 is slot 4's I/O
 *     space on an Apple II — a Mockingboard lives there);
 *   - keyboard through the $C000 latch (dev/lib/apple2c), arrow keys added;
 *   - the per-frame GEN2 mode re-assert (a POM1 renderer workaround) is gone.
 *
 *   Build : make            -> ../dist/SNAKE.dsk
 *   Run   : make run        (POM2, Apple ][+ profile)
 *
 * Controls: I J K L or the arrow keys (left/right on a II+, all four on a //e).
 *
 * --- Cell -> pixel mapping -------------------------------------------------
 * The 280x192 HIRES screen is divided into 8x8-pixel CELLS: 35 columns
 * (0..34, x = col*8) by 24 rows (0..23, y = row*8). A snake segment / the food
 * fills a 6x6 block inside its cell (a 1px gap on the right + bottom keeps the
 * grid readable). Top + bottom walls only (1px rules); the left/right sides are
 * OPEN — the snake wraps horizontally from one edge to the other.
 *
 * --- Visuals & gameplay ----------------------------------------------------
 * Snake = white blocks; the apple = a SOLID RED disk (orange is HIRES's warmest
 * tone — there is no true red); the bonus = a SOLID GREEN block; the score reads
 * in WHITE via the flicker-free hgr_putu_field HUD renderer (top-right);
 * the "HGR Snake" label sits top-left in cycling violet/green/orange/blue
 * (mixed case shows off BBFont's lowercase glyphs). HIRES colour
 * is a byte-pattern artifact (the tint keeps only ~half the pixels), so the game
 * sprites are drawn FILLED — a hollow outline gets halved into scattered dots.
 * Gameplay extra: every BONUS_EVERY apples a time-limited bonus gem appears for
 * BONUS_TTL ticks — grab it before it fades for BONUS_POINTS extra points (no
 * growth, so it is pure risk/reward).
 * ---------------------------------------------------------------------------
 */
#include "hgr.h"

/* --- Playfield geometry (cells) --- */
#define CELL      8u            /* pixels per cell side                          */
#define COLS      35u           /* 280 / 8                                       */
#define ROWS      24u           /* 192 / 8                                       */
#define BLOCK     6u            /* filled block size inside a cell (1px gap)     */
#define TOP_WALL  2u            /* top wall row; rows 0-1 above it are the score HUD,
                                 * which the snake (rows 3..ROWS-2) can never reach */
#define MAXLEN    ((COLS - 2u) * (ROWS - TOP_WALL - 2u)) /* 33 x 20 = 660 cells */

/* --- Bonus gem (gameplay extra) --- */
#define BONUS_EVERY  4u         /* drop a bonus every Nth apple                  */
#define BONUS_TTL    36u        /* bonus lifetime in ticks before it fades       */
#define BONUS_POINTS 20u        /* score for grabbing a bonus (4x a normal apple)*/

/* --- Direction codes --- */
#define DIR_UP    1
#define DIR_DOWN  2
#define DIR_LEFT  3
#define DIR_RIGHT 4

/* Snake body as a TRUE circular ring buffer of cell coordinates. `head` is the
 * array index of segment 0 (the head); `tail` the index of the last segment.
 * Live segments walk FORWARD tail -> head (wrapping at MAXLEN). Moving the snake
 * is O(1): write the new head one slot past `head`, then advance `tail` to drop
 * the old tail (unless we grew) — no per-segment shift (was O(length)/tick). */
/* LOWBSS is free RAM at $1000-$1FFF. new_game() initializes every live body
 * entry and clears occupied, so these arrays do not need startup zeroing. */
#pragma bss-name(push, "LOWBSS")
static unsigned char sx[MAXLEN];   /* body cell columns */
static unsigned char sy[MAXLEN];   /* body cell rows    */
static unsigned char occupied[ROWS][COLS]; /* constant-time self-collision */
#pragma bss-name(pop)
#pragma bss-name(push, "LOWBSS")
static unsigned int slen;          /* current length    */
static unsigned int head;          /* array index of the head segment       */
static unsigned int tail;          /* array index of the tail segment       */
static unsigned char dir;          /* current heading   */
static unsigned char turns[2];     /* at most two turns, applied one per tick */
static unsigned char turn_count;
static unsigned char alive;        /* 1 = playing, 0 = dead */
static unsigned char won;          /* 1 = every playable cell is occupied */
static unsigned char paused;       /* P or ESC stops movement until resumed */
static unsigned char foodx, foody; /* food cell */
static unsigned int  score;        /* total points (5/apple + 20/bonus) */
static unsigned int  score_shown;  /* last score value drawn to the HUD (redraw-on-change) */
static unsigned char apples;       /* apples eaten this game (drives the bonus cadence)   */
#pragma bss-name(pop)
/* Time-limited bonus gem. Logic in tick() sets the flags; the main loop does the
 * drawing (keeps tick() free of framebuffer writes, like the rest of the game). */
#pragma bss-name(push, "LOWBSS")
static unsigned char bonus_active; /* 1 = a bonus is currently on the field */
static unsigned char bonusx, bonusy; /* bonus cell */
static unsigned char bonus_ttl;    /* ticks left before the bonus fades        */
static unsigned char bonus_new;    /* set the tick a bonus spawns  -> loop draws it  */
static unsigned char bonus_gone;   /* set the tick a bonus expires -> loop erases it */
#pragma bss-name(pop)
/* "HGR Snake" title colour, cycled through the four NTSC artifact colours on every
 * apple — a little visual reward. The recolour is all-asm: hgr_clear_pixrect
 * (hgr_pixrect_asm) wipes the label box, hgr_puts_color draws it again with
 * the one-pass tinted glyph blitter (hgr_blit_glyph_color). */
static const unsigned char title_hues[4] = { HGR_VIOLET, HGR_GREEN, HGR_ORANGE, HGR_BLUE };
static unsigned char title_hue;    /* index into title_hues, advanced per apple */
/* Throttle iterations; lower = faster, shrinks per apple. Gameplay now polls
 * the keyboard during this delay, which adds some cost per iteration. */
static unsigned int  tick_spins = 3565u;

/* 16-bit LFSR PRNG (Galois), seeded from key-press timing at startup. */
static unsigned int rng_state = 0xACE1u;

static unsigned int prng(void)
{
    unsigned int lsb = rng_state & 1u;
    rng_state >>= 1;
    if (lsb) rng_state ^= 0xB400u;     /* taps 16,14,13,11 */
    return rng_state;
}

/* Fill / erase the 6x6 block of grid cell (cx, cy) in ONE asm call. hgr_cell
 * is the dedicated 8x8-grid blitter: it does cx*8/cy*8 in asm (no cc65 aslax3)
 * and skips the pixrect clip, so the per-tick head-draw + tail-erase shed the C
 * wrapper glue. (8x8 cell / 6x6 block matches CELL=8, BLOCK=6.) */
static void draw_cell(unsigned char cx, unsigned char cy)
{
    hgr_cell(cx, cy, 1u);
}

static void erase_cell(unsigned char cx, unsigned char cy)
{
    hgr_cell(cx, cy, 0u);
}

/* Draw the apple as a SOLID round RED disk. HIRES colour is a byte-pattern
 * artifact: the tint ANDs each byte with a half-density carrier, so it KEEPS
 * only ~half the pixels. A FILLED, symmetric disk stays a full red blob through
 * that; the old "fill block + knock the corners off" left an asymmetric pattern
 * the carrier turned into a half-circle. Built as filled rows (orange = HIRES's
 * warmest tone, the closest it has to red). */
static void draw_food(unsigned char cx, unsigned char cy)
{
    unsigned px = (unsigned)cx * CELL;
    unsigned char py = cy * (unsigned char)CELL;
    hgr_fill_pixrect(px + 2u, py,                       2u, 1u);  /* ..##.. */
    hgr_fill_pixrect(px + 1u, (unsigned char)(py + 1u), 4u, 1u);  /* .####. */
    hgr_fill_pixrect(px,      (unsigned char)(py + 2u), 6u, 2u);  /* ###### */
    hgr_fill_pixrect(px + 1u, (unsigned char)(py + 4u), 4u, 1u);  /* .####. */
    hgr_fill_pixrect(px + 2u, (unsigned char)(py + 5u), 2u, 1u);  /* ..##.. */
    hgr_colorize(px, py, BLOCK, BLOCK, HGR_ORANGE);
}

/* Draw the bonus gem as a SOLID GREEN block. The old hollow diamond outline was
 * halved by the tint into a few scattered dots — "not very visible, not a closed
 * figure". A filled cell stays a clearly visible, closed green gem: its GREEN
 * tells it apart from the white snake, and the round RED apple is its own shape. */
static void draw_bonus(unsigned char cx, unsigned char cy)
{
    unsigned px = (unsigned)cx * CELL;
    unsigned char py = cy * (unsigned char)CELL;
    hgr_fill_pixrect(px, py, BLOCK, BLOCK);
    hgr_colorize(px, py, BLOCK, BLOCK, HGR_GREEN);
}

/* Top and bottom walls only — the left/right sides are OPEN so the snake wraps
 * horizontally (see the wrap in tick()). Each wall is a 1px rule hugging the
 * outermost playable row (so the snake dies exactly when it reaches it, with no
 * empty-cell gap), drawn with a whole-byte fill_rect across the interior byte
 * columns — entirely on the asm fast path, no per-pixel plot loop. */
static void draw_border(void)
{
    const unsigned char top = (unsigned char)((TOP_WALL + 1u) * CELL - 1u);  /* y = 23  */
    const unsigned char bot = (unsigned char)((ROWS - 1u) * CELL);           /* y = 184 */
    hgr_fill_rect(top, 1u, 1u, (COLS * CELL) / 7u - 2u, 0x7Fu);         /* top rule    */
    hgr_fill_rect(bot, 1u, 1u, (COLS * CELL) / 7u - 2u, 0x7Fu);         /* bottom rule */
}

/* Occupancy lookup. skip_tail=1 permits entering the tail cell only when the
 * tail will move on this tick. */
static unsigned char body_hits(unsigned char cx, unsigned char cy, unsigned char skip_tail)
{
    if (!occupied[cy][cx]) return 0u;
    return !(skip_tail && sx[tail] == cx && sy[tail] == cy);
}

static void place_food(void)
{
    unsigned int n;
    foodx = (unsigned char)(1u + prng() % (COLS - 2u));
    foody = (unsigned char)((TOP_WALL + 1u) + prng() % (ROWS - TOP_WALL - 2u));
    /* Scan from a random starting cell. This always terminates, even when
     * the board is almost full or the PRNG never picks its last empty cell. */
    for (n = 0u; n < MAXLEN; ++n) {
        if (!body_hits(foodx, foody, 0u) &&
            !(bonus_active && foodx == bonusx && foody == bonusy)) return;
        if (++foodx == COLS - 1u) {
            foodx = 1u;
            if (++foody == ROWS - 1u) foody = TOP_WALL + 1u;
        }
    }
    /* The bonus occupies the sole free cell. Retire it and put the apple
     * there; bonus_gone makes the renderer erase it before drawing the apple. */
    if (bonus_active) {
        foodx = bonusx;
        foody = bonusy;
        bonus_active = 0u;
        bonus_gone = 1u;
    }
}

/* Place the bonus on an empty playable cell — same bounds as place_food, but it
 * must also avoid the apple. */
static unsigned char place_bonus(void)
{
    unsigned int n;
    bonusx = (unsigned char)(1u + prng() % (COLS - 2u));
    bonusy = (unsigned char)((TOP_WALL + 1u) + prng() % (ROWS - TOP_WALL - 2u));
    for (n = 0u; n < MAXLEN; ++n) {
        if (!body_hits(bonusx, bonusy, 0u) &&
            !(bonusx == foodx && bonusy == foody)) return 1u;
        if (++bonusx == COLS - 1u) {
            bonusx = 1u;
            if (++bonusy == ROWS - 1u) bonusy = TOP_WALL + 1u;
        }
    }
    return 0u;
}

/* Reset to a fresh game (3-segment snake heading right, mid-field). */
static void new_game(void)
{
    unsigned char i, x, y;
    for (y = 0u; y < ROWS; ++y)
        for (x = 0u; x < COLS; ++x) occupied[y][x] = 0u;
    slen = 3u;
    tail = 0u;
    head = slen - 1u;            /* ring: index 0 = tail .. slen-1 = head */
    for (i = 0; i < slen; ++i) {
        /* i=0 is the tail (leftmost); i=slen-1 the head (rightmost), heading right */
        sx[i] = (unsigned char)(COLS / 2u - (slen - 1u) + i);
        sy[i] = (unsigned char)(ROWS / 2u);
        occupied[sy[i]][sx[i]] = 1u;
    }
    dir = DIR_RIGHT;
    turn_count = 0u;
    alive = 1;
    won = 0u;
    paused = 0u;
    score = 0;
    score_shown = 0;           /* redraw() draws score 0; the loop redraws only on change */
    tick_spins = 3565u;        /* reset to the starting speed */
    apples = 0;
    title_hue = 0;             /* HGR Snake starts violet, shifts colour per apple */
    bonus_active = 0;          /* no bonus until the cadence drops one */
    bonus_new = 0;
    bonus_gone = 0;
    place_food();
}

/* Queue a turn relative to the last queued heading. This accepts two quick
 * perpendicular turns while still forbidding a reversal on either tick. */
static void set_dir(unsigned char d)
{
    unsigned char last = turn_count ? turns[turn_count - 1u] : dir;
    if (d == last || turn_count == 2u) return;
    if (d == DIR_UP    && last == DIR_DOWN)  return;
    if (d == DIR_DOWN  && last == DIR_UP)    return;
    if (d == DIR_LEFT  && last == DIR_RIGHT) return;
    if (d == DIR_RIGHT && last == DIR_LEFT)  return;
    turns[turn_count++] = d;
}

/* Read the keyboard: I J K L (the same physical keys on QWERTY and AZERTY) or
 * the arrow keys. apple2_readkey already folds lower case. */
static void read_input(void)
{
    unsigned char k = apple2_readkey();
    if (k == 'P' || k == KC_ESC) {
        paused = 1u;
        turn_count = 0u;           /* do not apply old turns after resuming */
    } else if (k == 'I' || k == KC_UP) set_dir(DIR_UP);
    else if (k == 'K' || k == KC_DOWN)  set_dir(DIR_DOWN);
    else if (k == 'J' || k == KC_LEFT)  set_dir(DIR_LEFT);
    else if (k == 'L' || k == KC_RIGHT) set_dir(DIR_RIGHT);
}

/* Advance one logical tick: move the head, resolve collisions / food. */
static void tick(void)
{
    unsigned char nx, ny, grow;

    if (turn_count) {
        dir = turns[0];
        if (turn_count == 2u) turns[0] = turns[1];
        --turn_count;
    }
    nx = sx[head];
    ny = sy[head];
    switch (dir) {
        case DIR_UP:    --ny; break;
        case DIR_DOWN:  ++ny; break;
        case DIR_LEFT:  --nx; break;
        case DIR_RIGHT: ++nx; break;
        default: break;
    }

    /* Horizontal WRAP — no left/right walls: cols 1..COLS-2 form a ring, so a
     * head leaving one side reappears on the other. (nx is unsigned char, so
     * --nx from col 1 gives 0 and ++nx from col COLS-2 gives COLS-1.) */
    if (nx < 1u)                                   nx = (unsigned char)(COLS - 2u);
    else if (nx > (unsigned char)(COLS - 2u))      nx = 1u;
    /* Top and bottom walls still kill. */
    if (ny <= TOP_WALL || ny >= (unsigned char)(ROWS - 1u)) {
        alive = 0;
        return;
    }
    grow = (nx == foodx && ny == foody) ? 1u : 0u;
    /* The tail is safe only when it vacates its cell this tick. */
    if (body_hits(nx, ny, (unsigned char)!grow)) { alive = 0; return; }

    /* Bonus pickup: worth BONUS_POINTS but no growth. The new head lands on the
     * gem and draw_cell() will paint over it, so just clear the flag (no erase). */
    if (bonus_active && nx == bonusx && ny == bonusy) {
        score += BONUS_POINTS;
        bonus_active = 0u;
    }

    /* O(1) ring move: append the new head one slot past `head`; drop the old
     * tail by advancing `tail` (the main loop erased its cell) — unless we grew,
     * in which case the tail stays and the body gets one segment longer. */
    if (++head == MAXLEN) head = 0u;
    sx[head] = nx;
    sy[head] = ny;
    if (grow) {
        ++slen;                                   /* grew: keep the tail */
    } else {
        occupied[sy[tail]][sx[tail]] = 0u;
        if (++tail == MAXLEN) tail = 0u;          /* moved: drop the old tail */
    }
    occupied[ny][nx] = 1u;

    if (grow) {
        score += 5u;                  /* each apple is worth 5 points */
        ++apples;
        /* Each apple speeds the snake up: shorten the throttle. Low floor + a
         * gentle step so the speed keeps climbing for many apples instead of
         * capping early (3565 -> ~365 over ~16 apples) — the end game gets
         * genuinely fast. The floor stays > 0 so the throttle never vanishes. */
        if (tick_spins > 400u) tick_spins -= 200u;
        if (slen == MAXLEN) {
            won = 1u;                 /* no empty cell remains for a new apple */
            return;
        }
        place_food();
        /* Every BONUS_EVERY apples, drop a time-limited bonus gem (if one is not
         * already out). Drawing is the main loop's job, so just flag it. */
        if (!bonus_active && (apples % BONUS_EVERY) == 0u && place_bonus()) {
            bonus_active = 1u;
            bonus_ttl    = BONUS_TTL;
            bonus_new    = 1u;
        }
    }

    /* Age an active bonus; when its timer runs out, flag it for erasure. */
    if (bonus_active) {
        --bonus_ttl;
        if (bonus_ttl == 0u) { bonus_active = 0u; bonus_gone = 1u; }
    }
}

/* Draw the score HUD (top-right) with the OPTIMIZED number renderer:
 * hgr_putu_field is the flicker-free HUD path — it wipes EXACTLY its own
 * 5-cell field (no separate hgr_clear_pixrect — the self-bounded wipe
 * can't bleed into the HGR Snake label that ends at x=170) and draws the
 * digits right-aligned in one pass. We pick width 5 so 0..65535 always fits
 * with no leading-zero leak from the shrinking case. Field width = 4*18+16 =
 * 88px; x=184 leaves an 8px right margin (mirrors the title's left margin). */
static void draw_score(void)
{
    hgr_putu_field(184u, 0u, score, 5u);
}

/* Draw the "HGR Snake" label, top-left, in the current cycling colour. 9 glyphs
 * x 18px pitch = 162px wide; x=8 ends it at pixel 170, leaving 14px of gap
 * before the right-hand score field. Mixed-case showcases BBFont's lowercase
 * glyphs. Wipe the box first so the new colour's pixels do not OR-mix with
 * the old one's (both passes are asm). */
static void draw_title(void)
{
    hgr_clear_pixrect(8u, 0u, 162u, 16u);
    hgr_puts_color(8, 0, "HGR Snake", title_hues[title_hue]);
}

/* Full draw — clear + walls/border + food + whole snake + score. Called ONCE
 * per game (start / restart), NOT per tick: the per-tick loop only erases the
 * vacated tail and draws the new head, so the expensive clear + border don't
 * run every frame. */
static void redraw(void)
{
    unsigned int idx = tail, k;
    hgr_clear(0);
    draw_border();
    draw_food(foodx, foody);
    if (bonus_active) draw_bonus(bonusx, bonusy);
    for (k = 0; k < slen; ++k) {        /* walk the ring tail -> head */
        draw_cell(sx[idx], sy[idx]);
        if (++idx == MAXLEN) idx = 0u;
    }
    draw_score();                       /* score, top-right, WHITE via optimized putu_field */
    draw_title();                       /* "HGR Snake", top-left, current cycling hue */
}

/* The pause card covers only the middle of the field. Resuming calls redraw()
 * once to restore any snake, food or bonus cells hidden beneath it. */
static void draw_pause(void)
{
    hgr_fill_rect(56u, 80u, 0u, 40u, 0x00u);
    hgr_puts_color(86, 64, "PAUSED", HGR_GREEN);
    hgr_puts_color(14, 88, "P/ESC CONTINUE", HGR_BLUE);
    hgr_puts_color(95, 112, "Q DOS", HGR_ORANGE);
}

/* Plain CPU-spin throttle for a playable tick rate (the Apple II has no
 * V-blank to pace against, and the blocky snake doesn't need it). */
static void throttle(unsigned char playing)
{
    unsigned int n;
    unsigned char poll_count = 0u;
    unsigned int lim = tick_spins;   /* local bound avoids a global reload on each spin */
    if (!playing) {
        for (n = 0; n < lim; ++n) { /* title and game-over timing */ }
    } else {
        for (n = 0; n < lim; ++n) {
            /* The Apple II latch only retains one key. Poll throughout the
             * delay so two turns can reach the queue before the next move. */
            if (++poll_count == 64u) {
                poll_count = 0u;
                read_input();
                if (paused) return;
            }
        }
    }
}

void main(void)
{
    unsigned int t;
    unsigned char start_key = 0u;

    /* ---- Title page: the name + the controls. Any key starts; with no key
     * the title times out after ~4 s and the game starts on its own. Every
     * line in a different artifact colour (violet / green / orange / blue). */
    hgr_init();
    hgr_clear(0);
    hgr_puts_color(68,  12, "APPLE II",      HGR_GREEN);   /* line 1, centred */
    hgr_puts_color(42,  40, "\"SNAKE HGR\"", HGR_VIOLET);  /* line 2: game name */
    hgr_puts_color(10,  72, "MOVE  I J K L", HGR_BLUE);
    hgr_puts_color(10,  96, "  OR ARROWS",   HGR_BLUE);
    hgr_puts_color(40, 120, "P/ESC PAUSE", HGR_ORANGE);
    hgr_puts_color(38, 150, "PRESS ANY KEY", HGR_GREEN);

    /* Short poll delay (~22 ms, ~45 polls/s so a quick tap is never missed),
     * 180 polls = ~4 s. new_game() resets tick_spins to the game speed. */
    tick_spins = 240u;
    for (t = 0; t < 180u; ++t) {
        start_key = apple2_readkey();
        if (start_key) break;           /* any key starts */
        throttle(0u);
    }

    /* Key timing varies between launches; automatic starts retain a stable
     * sequence. SNAKE_FIXED_SEED makes playtests reproducible. */
#ifdef SNAKE_FIXED_SEED
    rng_state = SNAKE_FIXED_SEED;
#else
    if (start_key) rng_state ^= (unsigned int)(t + 1u) * 257u + start_key;
#endif
    if (rng_state == 0u) rng_state = 0xACE1u; /* an LFSR must not start at zero */

    new_game();
    redraw();

    for (;;) {
        if (paused) {
            unsigned char k;
            draw_pause();
            do {
                k = apple2_getkey();
                if (k == 'Q') {
                    a2_home();
                    a2_dos();
                }
            } while (k != 'P' && k != KC_ESC);
            paused = 0u;
            redraw();
        } else if (alive && !won) {
            /* Remember the tail BEFORE the move so we can erase exactly the cell
             * it vacates — the only cell that changes besides the new head. */
            unsigned char otx = sx[tail], oty = sy[tail];
            unsigned int olen = slen;
            read_input();
            if (paused) continue;
            tick();
            if (alive) {
                /* INCREMENTAL redraw — walls/border were drawn once in redraw();
                 * here we only touch the snake, the food, and the score. */
                if (bonus_gone) { erase_cell(bonusx, bonusy); bonus_gone = 0u; }
                if (slen == olen) {
                    erase_cell(otx, oty);          /* snake moved: clear old tail */
                } else {
                    if (!won) draw_food(foodx, foody); /* grew: show the new food */
                    title_hue = (unsigned char)((title_hue + 1u) & 3u);
                    draw_title();                  /* apple eaten: shift HGR Snake colour */
                }
                draw_cell(sx[head], sy[head]);     /* draw the new head           */
                /* Bonus gem: tick() flags a spawn or a time-out; do the drawing
                 * here. (Eating it needs no erase — the head already covers it.) */
                if (bonus_new)  { draw_bonus(bonusx, bonusy); bonus_new  = 0u; }
                /* Score: redraw ONLY when it actually changes — not every frame. */
                if (score != score_shown) {
                    draw_score();
                    score_shown = score;
                }
            }
            throttle(1u);
        } else {
            /* Death: show GAME OVER, hold ~4 s, then let a key restart early.
             * The full-width band of grid rows 8..13 (y=64..111) is wiped first
             * so the banner is not OR'd over the snake / apple (cell-aligned, so
             * no half-erased block stays glued to the letters). */
            unsigned int hold;
            hgr_fill_rect(64u, 48u, 0u, 40u, 0x00u);
            if (won) hgr_puts_color(68, 80, "YOU WIN", HGR_GREEN);
            else     hgr_puts_color(40, 80, "GAME OVER", HGR_ORANGE);
            tick_spins = 3565u;             /* pin the throttle to its slow cadence */
            /* One throttle at 3565 spins lasts ~0.33 s (measured: a tick every
             * 18-20 frames). Upstream held 40 + up to 50 of them — ~13 s deaf,
             * ~30 s in all, not the ~4 s its comment promised. */
            for (hold = 0; hold < 12u; ++hold) {
                throttle(0u);               /* phase 1: ~4 s mandatory hold */
            }
            for (hold = 0; hold < 15u; ++hold) {  /* phase 2: ~5 s key window */
                if (apple2_readkey() != 0) break;   /* phase 2: key restarts */
                throttle(0u);
            }
            new_game();
            redraw();
        }
    }
}
