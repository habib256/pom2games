/*
 * Copyright (C) 2025 Colin Leroy-Mira <colin@colino.net>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sound.h"

int sampling_hz = DEFAULT_SAMPLING_HZ;

static unsigned char fast_steps[] = {43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32, 31, 30, 29, 28, 27, 26, 25, 24, 23,
                                     22, 21, 20, 19, 18, 17, 16, 15, 14, 12};

int allow_inline = 0;
/* No paddle/accelerator softswitch access in the library player. */
int do_ptrig = 0;

#define BYTE_LOAD_CYCLES 7
#define BACKUP_X_CYCLES 5
#define RESTORE_X_CYCLES 3
#define INLINE_TARGET_SET_CYCLES 7
#define SLOW_SOUND_CYCLES 23
#define SLOW_SOUND_AND_JUMP_CYCLES 20
#define SET_TARGET_CYCLES 26
#define SET_TARGET_AND_JUMP_CYCLES 22
#define SET_TARGET_AND_INCR_POINTER_CYCLES 35
#define SLOW_SOUND_SET_TARGET_AND_JUMP_CYCLES 33
#define INCR_POINTER_CYCLES 22
#define INCR_POINTER_AND_JUMP_CYCLES 18
#define SLOW_SOUND_AND_INCR_POINTER_CYCLES 32
#define SLOW_SOUND_AND_SET_TARGET_CYCLES 37
#define JUMP_CYCLES 6

typedef struct _Action {
  const char *instruction;
  const int doable_between_speaker_access;
  const int only_if_allow_inline;
  const int cycles;
  const int actions[8];
} Action;

/* Different combinations of what we have to do, sorted by order of priority,
 * with optionals limits so some don't get picked up when they shouldn't.
 * Those which are commented out are never needed by the algorithm, so they
 * don't need to be shipped in the assembly.
 */
Action actions[] = {
  {"         lda (ptr1),y\n"
   "         tax                                ", 1, 0, BYTE_LOAD_CYCLES,                      {1, 0, 0, 0, 0, 0, 0, 0}},
  {"         stx tmp3\n"
   "         ldx #"PAGE_CROSS_STR"+2                         "
                                                 , 0, 0, BACKUP_X_CYCLES,                       {0, 0, 0, 0, 0, 0, 1, 0}},
  {"         ldx tmp3                           ", 0, 0, RESTORE_X_CYCLES,                      {0, 0, 0, 0, 0, 0, 0, 1}},
  {"         lda sound_levels+0,x\n"
   "         sta target+1+0                     ", 1, 1, INLINE_TARGET_SET_CYCLES,              {0, 0, 1, 0, 0, 0, 0, 0}},
  {"         lda sound_levels+1,x\n"
   "         sta target+1+1                     ", 1, 1, INLINE_TARGET_SET_CYCLES,              {0, 0, 0, 1, 0, 0, 0, 0}},
  {"         jsr slow_sound                     ", 0, 0, SLOW_SOUND_CYCLES,                     {0, 0, 0, 0, 1, 0, 0, 0}},
  {"         jsr set_target                     ", 1, 0, SET_TARGET_CYCLES,                     {0, 0, 1, 1, 0, 0, 0, 0}},
  {"         jsr incr_pointer                   ", 1, 0, INCR_POINTER_CYCLES,                   {0, 1, 0, 0, 0, 0, 0, 0}},
  {"         jmp target                         ", 0, 0, JUMP_CYCLES,                           {0, 0, 0, 0, 0, 1, 0, 0}},
};
#define NUM_ACTIONS (sizeof(actions)/sizeof(Action))

enum {
  LOAD_BYTE,
  INCR_POINTER,
  SET_TARGET_LOW,
  SET_TARGET_HIGH,
  SLOW_SOUND,
  JUMP,
  BACKUP_X,
  RESTORE_X,
  NUM_TASKS
};

int actions_done[NUM_TASKS] = {0};

static int emit_instruction(const char *instruction, int cycles, int cycles_avail) {
  cycles_avail -= cycles;
  printf("%s; %d cycles, %d remain\n", instruction, cycles, cycles_avail);
  return cycles_avail;
}

static int emit_wait(int cycles, int avail, int between, int can_jump) {
  int i, j;
  if (avail == 0) {
    return 0;
  }
  if (cycles == 1) {
    printf("                                   ; Nothing to waste 1 cycle\n");
    return avail;
  }

  /* See if we can fit something useful according to the cycles and rules */
  for (i = 0; i < (int)NUM_ACTIONS; i++) {
    int already_done = 0;
    if (between && !actions[i].doable_between_speaker_access) {
      continue;
    }
    if (!can_jump && actions[i].actions[JUMP]) {
      continue;
    }
    if (!allow_inline && actions[i].only_if_allow_inline) {
      continue;
    }
    for (j = 0; j < NUM_TASKS; j++) {
      if (actions[i].actions[j] == 1 && actions_done[j] > 0) {
        already_done = 1;
        break;
      }
    }
    if (already_done) {
      continue;
    }

    /* It fits the bill! */
    if (cycles == actions[i].cycles || cycles > actions[i].cycles + 1) {
      if (actions[i].actions[JUMP] == 1) {
        /* If we're goint to jump, emit final wait before
         * but mark actions done. */
        for (j = 0; j < NUM_TASKS; j++) {
          if (actions[i].actions[j]) {
            actions_done[j]++;
          }
        }
        cycles -= actions[i].cycles;
        avail = emit_wait(cycles, avail, 0, 0);

        emit_instruction(actions[i].instruction, actions[i].cycles, avail);
        cycles -= actions[i].cycles;
        avail -= actions[i].cycles;

      } else {
        emit_instruction(actions[i].instruction, actions[i].cycles, avail);
        cycles -= actions[i].cycles;
        avail -= actions[i].cycles;
        for (j = 0; j < NUM_TASKS; j++) {
          if (actions[i].actions[j]) {
            actions_done[j]++;
          }
        }
      }
      /* We did fit something, so call ourselves back for the remainder
       * of the cycles to be wasted.
       */
      return emit_wait(cycles, avail, between, can_jump);
    }
  }

  if (do_ptrig && cycles > 7) {
add_ptrig:
      cycles -= 4;
      avail -= 4;
      printf("         bit $C070  ; PTRIG (accl)          ; %d cycles, %d remain\n", 4, avail);
      do_ptrig = 0;
  }
  /* Nothing useful did fit. Just waste the cycles. */
  for (i = 0; i < (int)sizeof(fast_steps); i++) {
    if (cycles > fast_steps[i]+1 || cycles == fast_steps[i]) {
      cycles -= fast_steps[i];
      avail -= fast_steps[i];
      printf("         jsr waste_%d                       ; %d cycles, %d remain\n", fast_steps[i], fast_steps[i], avail);
      return emit_wait(cycles, avail, between, can_jump);
    }
  }

  while (cycles > 0) {
    if (cycles % 2 != 0) {
      cycles -= 3;
      avail -= 3;
      printf("         bit $FF                            ; %d cycles, %d remain\n", 3, avail);
    } else if (cycles == 4 && do_ptrig) {
      goto add_ptrig;
    } else {
      cycles -= 2;
      avail -= 2;
      printf("         nop                                ; %d cycles, %d remain\n", 2, avail);
    }
  }
  return avail;
}

static void sub_level(int l, int repeat) {
  int cycles = AVAIL_CYCLES;
  int i, orig_cycles;
  int cycles_available_between_skpr = l;
  int cycles_available_after_spkr   = cycles              /* what we have */
                                      - l                 /* minus between the two STA $C030 */
                                      - 8;                /* minus the two STA */
  orig_cycles = cycles;

  printf("; %d cycles available between speaker access,\n"
         "; %d cycles available after speaker access.\n",
         cycles_available_between_skpr,
         cycles_available_after_spkr);

  actions_done[LOAD_BYTE] = 0;
  actions_done[INCR_POINTER] = 0;
  actions_done[SET_TARGET_LOW] = 0;
  actions_done[SET_TARGET_HIGH] = 0;
  actions_done[JUMP] = 0;
  /* Only to be done at level 1 */
  actions_done[BACKUP_X] = 1;
  actions_done[RESTORE_X] = 1;

  do_ptrig = 0;
  allow_inline = 0;

  for (i = 0; i < repeat; i++) {
    cycles = orig_cycles;
    actions_done[SLOW_SOUND] = 1;

    if (l == 1) {
      /* At level 1, we will use sta SPRK_OFF,x to have an extra cycle.
       * But X will change as soon as we LOAD_BYTE, which will make the
       * second (/third/fourth) repeats wrong. Add BACKUP_X to the things
       * to do on first repeat, right after BYTE_LOAD. Mark target updated
       * on first repeats, even if it's false, to avoid setting it with X at
       * level 1. Unmark it done on last repeat. */
      actions_done[SET_TARGET_LOW] = 1;
      actions_done[SET_TARGET_HIGH] = 1;
      if (i == 0) {
        actions_done[BACKUP_X] = 0;
      } else if (i == repeat -1) {
        actions_done[RESTORE_X] = 0;
        actions_done[SET_TARGET_LOW] = 0;
        actions_done[SET_TARGET_HIGH] = 0;
      }
    }

    printf(".proc sound_level_%d_%d\n", l, i);
    cycles = emit_instruction("         sta SPKR                           ", 4, cycles);
    if (l == 1) {
      cycles = emit_instruction("         sta SPKR_OFF,x                     ", 5, cycles);
    } else {
      cycles = emit_wait(l, cycles, 1, 0);
      cycles = emit_instruction("         sta SPKR                           ", 4, cycles);
    }

    cycles = emit_wait(cycles, cycles, 0, i == repeat - 1);

    if (actions_done[SLOW_SOUND] != 1) {
      fprintf(stderr, "%d SLOW_SOUND on level %d step %d\n", actions_done[SLOW_SOUND], l, i);
      exit(1);
    }
    printf(".endproc\n");
  }
  if (actions_done[LOAD_BYTE] != 1) {
    fprintf(stderr, "Missing LOAD_BYTE on level %d\n", l);
    exit(1);
  }
  if (actions_done[SET_TARGET_LOW] != 1) {
    fprintf(stderr, "Missing SET_TARGET_LOW on level %d\n", l);
    exit(1);
  }
  if (actions_done[SET_TARGET_HIGH] != 1) {
    fprintf(stderr, "Missing SET_TARGET_HIGH on level %d\n", l);
    exit(1);
  }
  if (actions_done[INCR_POINTER] != 1) {
    fprintf(stderr, "Missing INCR_POINTER on level %d\n", l);
    exit(1);
  }
  if (actions_done[JUMP] != 1) {
    fprintf(stderr, "Missing JUMP on level %d\n", l);
    exit(1);
  }

  printf("\n\n");
}

static void level(int l) {
  int repeat = CARRIER_HZ/sampling_hz;
  if (CARRIER_HZ % sampling_hz != 0) {
    fprintf(stderr, "CARRIER_HZ %d is not a multiple of SAMPLING_HZ %d\n",
            CARRIER_HZ, sampling_hz);
    exit(1);
  }
  sub_level(l, repeat);
  // if (!target_set[0] || !target_set[1] ||
  //     !pointer_incremented || !byte_loaded) {
  //       fprintf(stderr, "Error: not enough cycles to do everything at level %d: \n%s%s%s%s\n", l,
  //               !byte_loaded ? "Could not load byte\n":"",
  //               !pointer_incremented ? "Could not increment pointer\n":"",
  //               !target_set[0] ? "Could not set low target\n":"",
  //               !target_set[1] ? "Could not set high target\n":"");
  //       exit(1);
  // }
}

static char *segment = "DATA";

int main(int argc, char *argv[]) {
  int c;

  if (argc < 2) {
    fprintf(stderr, "Usage: %s [sampling hz]\n", argv[0]);
    exit(1);
  }

  if (argc == 3) {
    segment = argv[2];
  }

  sampling_hz = atoi(argv[1]);
  if (strcmp(argv[1], "8000") != 0) {
    fprintf(stderr, "Only the fixed 8000 Hz format is supported\n");
    return 1;
  }

  printf("; Settings for this sound generator:\n"
         "; CYCLES_PER_SEC = %d\n"
         "; CARRIER_HZ = %d\n"
         "; SAMPLING_HZ = %d\n"
         "; DUTY_CYCLE_LENGTH = %d\n"
         "; AVAIL_CYCLES = %d\n"
         "; NUM_LEVELS = %d\n"
         "; STEP = %d\n\n",
         CYCLES_PER_SEC,
         CARRIER_HZ,
         sampling_hz,
         DUTY_CYCLE_LENGTH,
         AVAIL_CYCLES,
         NUM_LEVELS,
         STEP);

  printf("; Adapted for pom2games: fixed rate, main RAM, D=0, nominal 1 MHz.\n"
         "; Blocking, non-reentrant; IRQ mask preserved. No video/bank changes.\n"
         "; A/X = encoded sample pointer. Null pointer is a no-op.\n"
         "; Clobbers A/X/Y, ptr1, ptr3 and ptr4 low byte (3-byte JMP), tmp3.\n"
         "; Source must end with $92, contain only even $32..$90 codes,\n"
         "; and remain in main RAM without crossing $FFFF.\n"
         "         .export _a2_sample_play\n"
         "         .importzp ptr1, ptr3, tmp3\n"
         "SPKR = $C030\n"
         "target = ptr3\n\n");

  printf(".segment \"%s\"\n", segment);
  printf(".align $100\n");
  printf("START_SOUND_PLAYER = *\n");

  printf(
         "; Total cost 22 cycles\n"
         "; Could be 21 but we need to fit between SPKR access at level 22\n"
         "; if slower is enabled, so we waste one cycle with INC absolute.\n"
         ".proc incr_pointer\n"
         "         iny                         ; 2\n"
         "         bne :+                      ; 4   (5)\n"
         "         .byte $EE                   ; INC abs\n"
         "         .byte ptr1+1                ; 10\n"
         "         .byte $00\n"
         "         rts                         ; 16\n"
         ":        nop                         ; 7\n"
         "         bit $FF                     ; 10\n"
         "         rts                         ; 16\n"
         ".endproc\n"
         "\n"
         "; Total cost 26 cycles\n"
         ".proc set_target\n"
         "         lda sound_levels+0,x        ; 4\n"
         "         sta target+1+0              ; 7\n"
         "         lda sound_levels+1,x        ; 11\n"
         "         sta target+1+1              ; 14\n"
         "         rts                         ; 20\n"
         ".endproc\n"
       );

  /* Wasters */
  printf("\n"
         "waste_42: nop\n"
         "waste_40: nop\n"
         "waste_38: nop\n"
         "waste_36: nop\n"
         "waste_34: nop\n"
         "waste_32: nop\n"
         "waste_30: nop\n"
         "waste_28: nop\n"
         "waste_26: nop\n"
         "waste_24: nop\n"
         "waste_22: nop\n"
         "waste_20: nop\n"
         "waste_18: nop\n"
         "waste_16: nop\n"
         "waste_14: nop\n"
         "waste_12: rts\n\n");

  printf("\n"
         "waste_43: nop\n"
         "waste_41: nop\n"
         "waste_39: nop\n"
         "waste_37: nop\n"
         "waste_35: nop\n"
         "waste_33: nop\n"
         "waste_31: nop\n"
         "waste_29: nop\n"
         "waste_27: nop\n"
         "waste_25: nop\n"
         "waste_23: nop\n"
         "waste_21: nop\n"
         "waste_19: nop\n"
         "waste_17: nop\n"
         "waste_15: bit $FF\n"
         "          rts\n\n");

  printf(".proc _a2_sample_play\n"
         "         php\n"
         "         sei\n"
         "         sta ptr1\n"
         "         stx ptr1+1\n"
         "         ora ptr1+1\n"
         "         bne :+\n"
         "         plp\n"
         "         rts\n"
         ":        lda #$4C\n"
         "         sta target\n"
         "         ldy ptr1\n"
         "         lda #$00\n"
         "         sta ptr1\n"
         "         lda (ptr1),y\n"
         "         tax\n"
         "         jsr set_target\n"
         "         jsr incr_pointer\n"
         "         jmp target\n"
         ".endproc\n\n"
         ".proc play_done\n"
         "         plp\n"
         "         rts\n"
         ".endproc\n\n");

  /* Jump table, aligned on a page to make sure we don't get extra cycles */
  printf(".assert <* > $%02X, error ; for the page crosser\n", PAGE_CROSSER);
  printf(".proc sound_levels_off\n");
  for (c = 0; c < NUM_LEVELS; c+=STEP) {
    printf("         .addr sound_level_%d_0\n", c);
  }
  printf("         .addr play_done\n");
  printf(".endproc\n\n");
  printf("sound_levels = sound_levels_off - $%02X\n", PAGE_CROSSER);
  printf("SPKR_OFF = SPKR - $%02X\n", PAGE_CROSSER);
  /* Assert we're still on the same page. */
  printf("sound_player_end_header = *\n");
  printf(".assert >START_SOUND_PLAYER = >*, error\n");

  /* Levels */
  for (c = 0; c < NUM_LEVELS; c+=STEP) {
    level(c);
  }
}
