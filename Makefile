# pom2games — build every disk
#
#   make            -> dist/*.dsk et dist/*.po (every disk lands in this one folder),
#                      plus dist/woz/: a .woz twin of each 140K one for the MiSTer core
#   make test       -> build, then the FAST tier: each program's `make test`
#                      plus the quick dev/ checks (libraries, tools, bench-check)
#   make test-long  -> the LONG tier: each program's `make test-long` (full
#                      campaigns, every level, journeys...)
#   make test-all   -> both tiers (what `make test` ran before the split)
#   make test-changed [BASE=<ref>] [LONG=1] [SOURCES_ONLY=1]
#                   -> only the programs the working tree changes vs BASE
#                      (default origin/main, else HEAD): their sources or
#                      their freshly built disk image differ; dev/ checks
#                      when dev/ changed (dev/tools/test_changed.py)
#   make check      -> rebuild every disk from scratch and fail if one differs
#                      from the committed dist/*.dsk et dist/*.po (sources and disks agree)
#   make clean      -> remove the build/ folders (the disks stay)
#   make distclean  -> remove the build/ folders and dist/*.dsk et dist/*.po
#
# Each folder builds on its own too: make -C chess [run], still into ./dist.
# Test tiers, the convention for every program (and a new game):
#   make -C <game> test       fast (a minute or two): run it after each change
#   make -C <game> test-long  long campaigns; may be empty
# test-<game> runs the first, test-<game>-long the second.

PYTHON ?= python3

II_PLUS_GAMES := arkabreakout micro-sokoban chess maze3d snake pinball light3dball wilderness dirtbike
IIE_PRODOS_GAMES := chromabreak wargalagaii robotspacestation mbtracker
DIRS := $(II_PLUS_GAMES) $(IIE_PRODOS_GAMES) logo dev/examples/hello dev/examples/hgr dev/examples/dhgr dev/examples/perspective
# DHGR compositor action demo: its disk stays in its build/ (not dist/).
DIRS += dev/examples/dhgr_action
# Verlet lunar lander, the lib/physics demo: its disk stays in its build/.
DIRS += dev/examples/lander
# Verlet skate half-pipe, the segment-ground demo: its disk stays in its build/.
DIRS += dev/examples/halfpipe
# Verlet rope toy (pins, fixed-gain links, ground) and catapult (circle
# contacts), lib/physics demos: their disks stay in their build/.
DIRS += dev/examples/rope dev/examples/catapult
# Programs whose own `make test` / `make test-long` belong to the root tiers.
TESTED := pinball chromabreak arkabreakout chess micro-sokoban light3dball wilderness logo mbtracker dirtbike \
          wargalagaii snake robotspacestation

all:
	@for d in $(DIRS); do $(MAKE) -C $$d || exit 1; done

# Quick dev/ checks: shared libraries, examples, tools, performance budgets.
DEV_CHECKS := test-hgr test-frame test-hgr-example test-assets bench-check \
              test-techniques test-tools test-minimal test-woz
DEV_CHECKS += test-dhgr-action
DEV_CHECKS += test-lander-example
DEV_CHECKS += test-halfpipe-example
DEV_CHECKS += test-rope-example test-catapult-example test-verlet-contact

# The dev/ checks run on the portable headless II+ (a fresh checkout has to
# build it first; the program Makefiles already list it, see apple2.mk).
A2RUN := dev/tools/a2run/a2run
$(A2RUN): $(wildcard dev/tools/a2run/*.[ch] dev/tools/a2run/Makefile)
	$(MAKE) -C dev/tools/a2run
$(DEV_CHECKS) test-dhgr: $(A2RUN)

test: all $(DEV_CHECKS) $(TESTED:%=test-%)
# LONG_SKIP=<programs> leaves their long tier out (CI runs wilderness's,
# half an hour, in a job of its own).
LONG_SKIP ?=
test-long: all $(patsubst %,test-%-long,$(filter-out $(LONG_SKIP),$(TESTED)))
test-all: test test-long
test-dev: $(DEV_CHECKS)

$(TESTED:%=test-%):
	$(MAKE) -C $(@:test-%=%) test
$(TESTED:%=test-%-long):
	$(MAKE) -C $(@:test-%-long=%) test-long

BASE ?=
test-changed:
	$(PYTHON) dev/tools/test_changed.py $(if $(BASE),--base $(BASE)) \
	    $(if $(LONG),--long) $(if $(SOURCES_ONLY),--sources-only) $(TESTED)

.PHONY: test test-long test-all test-dev test-changed \
        $(TESTED:%=test-%) $(TESTED:%=test-%-long)

test-hgr:
	$(PYTHON) dev/tests/test_asm_boundaries.py
	$(PYTHON) dev/tests/test_dos_reuse.py
	$(PYTHON) dev/tests/test_math.py
	$(PYTHON) dev/tests/test_verlet.py
	$(PYTHON) dev/tests/test_rwts.py
	$(PYTHON) dev/tests/test_lib_options.py
	$(PYTHON) dev/tests/test_hgr_pages.py
	$(PYTHON) dev/tests/test_joy_fast.py
	$(PYTHON) dev/tests/test_stick_key.py
	$(PYTHON) dev/tests/test_initials.py
	$(PYTHON) dev/tests/test_rwts_sectors.py
	$(PYTHON) dev/tests/test_tune.py
	$(PYTHON) dev/tests/test_bcd.py
	$(PYTHON) dev/tests/test_aysong.py
	$(PYTHON) dev/tests/test_mb_irq.py
	$(PYTHON) dev/tests/test_pt3_import.py
	$(PYTHON) dev/tests/test_savehdr.py
	$(PYTHON) dev/tests/test_vapor.py
	$(PYTHON) dev/tests/test_exit_modes.py
	$(PYTHON) dev/tests/test_hgr_host.py
	$(PYTHON) dev/tests/test_hgr_x2.py
	$(PYTHON) dev/tests/test_gfx_boundaries.py
	$(PYTHON) dev/tests/test_gfx_outlines.py
	$(PYTHON) dev/tests/test_hgr_logo.py
	$(PYTHON) dev/tests/test_hgr_glyph8.py
	$(PYTHON) dev/tests/test_logo_glyphs.py
	$(PYTHON) dev/tests/test_hgr_sprite_update.py
	$(PYTHON) dev/tests/test_video_memory.py
	$(PYTHON) dev/tests/test_lores_modes.py
	$(PYTHON) dev/tests/test_preshift_bounds.py
	$(PYTHON) dev/tests/test_sprmask_bounds.py
	$(PYTHON) dev/tests/test_sprite16_bounds.py
	$(PYTHON) dev/tests/test_text8_strings.py
	$(PYTHON) dev/tests/test_hgr_native.py
	$(PYTHON) dev/tests/test_hgr_wireframe.py
	$(PYTHON) dev/tests/test_hgr_lines.py
	$(PYTHON) dev/tests/test_hgr_hud.py
	$(PYTHON) dev/tests/test_hgr_hud.py --compact
	$(PYTHON) dev/tests/test_presentation_strategies.py
	$(PYTHON) dev/tests/test_hgr.py
	$(PYTHON) dev/tests/test_hgr_glyphs.py
	$(PYTHON) dev/tests/test_sprengine.py
	$(PYTHON) dev/tests/test_sprengine_stress.py
	$(PYTHON) dev/tests/test_sprengine_dirty.py
	$(PYTHON) dev/tests/test_tilemap.py

test-frame:
	$(PYTHON) dev/tests/test_frame.py

test-hgr-example:
	$(PYTHON) dev/tests/test_hgr_example.py

test-dhgr:
	$(PYTHON) dev/tests/test_audio.py --iie
	$(PYTHON) dev/tests/test_perspective.py --iie
	$(PYTHON) dev/tests/test_shufflepuck_example.py --iie
	$(MAKE) -C dev/examples/dhgr test
	$(PYTHON) dev/tests/test_dhgr_extended.py
	$(PYTHON) dev/tests/test_dhgr_spans.py
	$(PYTHON) dev/tests/test_dhgr_clear_rows.py
	$(PYTHON) dev/tests/test_dhgr_spr.py
	$(PYTHON) dev/tests/test_gfx_dhgr_lines.py
	$(PYTHON) dev/tests/test_minimal_examples.py --dhgr
	$(PYTHON) dev/tests/test_stack_profile.py --iie
	$(PYTHON) dev/tests/test_hgr_hud.py --iie
	$(PYTHON) dev/tests/test_presentation_strategies.py --iie
	$(PYTHON) dev/tests/test_sprengine_dirty.py --iie
	$(PYTHON) dev/tests/test_frame.py --iie
	$(PYTHON) dev/tests/test_cadence.py
	$(PYTHON) dev/tests/test_game_cadence.py
	$(PYTHON) dev/tests/test_tilemap.py --iie
	$(PYTHON) dev/tests/test_hgr_hud.py --compact --iie
	$(PYTHON) dev/tests/test_sprengine_dirty.py --damage --iie
	$(PYTHON) dev/tests/test_sprengine_damage.py
	$(PYTHON) dev/tests/test_hgr_example.py --iie

check: distclean
	$(MAKE) all
	@git diff --stat --exit-code -- dist || \
	    { echo "dist/*.dsk et dist/*.po differ from a fresh build: run make and commit dist/"; exit 1; }
	@test -z "$$(git ls-files --others --exclude-standard -- dist)" || \
	    { echo "untracked disks in dist/:"; git ls-files --others --exclude-standard -- dist; exit 1; }

clean:
	@for d in $(DIRS); do $(MAKE) -C $$d clean; done

distclean:
	@for d in $(DIRS); do $(MAKE) -C $$d distclean; done

.PHONY: all test test-hgr test-frame test-hgr-example test-dhgr check clean distclean

test-assets:
	$(PYTHON) dev/tools/fonts.py --check
	$(PYTHON) dev/tests/test_assets.py

bench:
	$(PYTHON) dev/bench/run.py

bench-dhgr:
	$(PYTHON) dev/bench/run.py --dhgr

bench-check:
	$(PYTHON) dev/bench/run.py --check

# Every 140K disk in dist/ has its MiSTer WOZ twin, byte for byte up to date
# (make skips a twin newer than its disk even when it was built from another).
test-woz:
	$(PYTHON) dev/tools/dsk2woz.py --check dist

.PHONY: test-assets bench bench-dhgr bench-check test-woz

profile-ii-plus:
	@for d in $(II_PLUS_GAMES); do $(MAKE) -C $$d || exit 1; done

profile-iie-prodos:
	@for d in $(IIE_PRODOS_GAMES); do $(MAKE) -C $$d || exit 1; done

.PHONY: profile-ii-plus profile-iie-prodos

test-techniques:
	$(MAKE) -C arkabreakout
	$(MAKE) -C micro-sokoban
	$(PYTHON) dev/tests/techniques/run.py

.PHONY: test-techniques

# Native HGR lookup tables and checked fixed-sector DOS construction.
test-tools:
	$(PYTHON) dev/tests/test_corridor.py
	$(PYTHON) dev/tests/test_audio.py
	$(PYTHON) dev/tests/test_perspective.py
	$(PYTHON) dev/tests/test_shufflepuck_example.py
	$(PYTHON) dev/tests/test_stack_profile.py
	$(PYTHON) dev/tests/test_build_config.py
	$(PYTHON) dev/tests/test_prodos_video.py
	$(PYTHON) dev/tests/test_prodos_file.py
	$(PYTHON) dev/tests/test_prodos_sysreloc.py
	$(PYTHON) dev/tests/test_apple2game.py
	$(PYTHON) dev/tests/test_mouse_context.py
	$(PYTHON) dev/tests/test_mouse_noslot.py
	$(PYTHON) dev/tests/test_hgr_tables_disk.py
.PHONY: test-tools

bench-corridor:
	$(PYTHON) dev/bench/corridor_projection.py
.PHONY: bench-corridor

# Optional RGB and Mockingboard ASM primitives, with traced hardware buses.
test-tools: test-hardware
test-hardware:
	$(PYTHON) dev/tests/test_rgb_mockingboard.py
.PHONY: test-hardware

test-minimal:
	$(PYTHON) dev/tests/test_minimal_examples.py
.PHONY: test-minimal

# DHGR ACTION (dev/examples/dhgr_action): the compositor on two pages,
# //e and //c (a2shot; skipped where it does not run).
test-dhgr-action:
	$(MAKE) -C dev/examples/dhgr_action test
.PHONY: test-dhgr-action

# LANDER (dev/examples/lander): its 6502 physics == tools/lander.py, and the
# disk in a2run (a landing, a crash).
test-lander-example:
	$(MAKE) -C dev/examples/lander test
.PHONY: test-lander-example

# ROPE (dev/examples/rope): its 6502 physics == tools/rope.py, and the disk in
# a2run (swing, floor, cut, reset, frame rates).
test-rope-example:
	$(MAKE) -C dev/examples/rope test
.PHONY: test-rope-example

# CATAPULT (dev/examples/catapult): its 6502 physics == tools/catapult.py
# (circle contacts, sleep), and the disk in a2run (a shot, a round).
test-catapult-example:
	$(MAKE) -C dev/examples/catapult test
.PHONY: test-catapult-example

# lib/physics circle contacts (verlet_circ.asm) == dev/tools/verlet/contact.py.
test-verlet-contact:
	$(PYTHON) dev/tests/test_verlet_contact.py
.PHONY: test-verlet-contact

# HALFPIPE (dev/examples/halfpipe): its 6502 physics == tools/halfpipe.py, and
# the disk in a2run (pumping above a lip, a crash, R); lib/physics segments.
test-halfpipe-example:
	$(PYTHON) dev/tests/test_verlet_seg.py
	$(MAKE) -C dev/examples/halfpipe test
.PHONY: test-halfpipe-example

# Compiler-derived shared-library usage and transitive build dependencies.
audit-libs:
	$(PYTHON) dev/tools/audit_lib_usage.py
.PHONY: audit-libs

