# pom2games — build every disk
#
#   make            -> dist/*.dsk et dist/*.po (every disk lands in this one folder)
#   make test       -> build, test HGR, then play MICRO-SOKOBAN in a2run
#   make check      -> rebuild every disk from scratch and fail if one differs
#                      from the committed dist/*.dsk et dist/*.po (sources and disks agree)
#   make clean      -> remove the build/ folders (the disks stay)
#   make distclean  -> remove the build/ folders and dist/*.dsk et dist/*.po
#
# Each folder builds on its own too: make -C chess [run], still into ./dist.

II_PLUS_GAMES := arkabreakout micro-sokoban chess maze3d snake pinball light3dball
IIE_PRODOS_GAMES := chromabreak
DIRS := $(II_PLUS_GAMES) $(IIE_PRODOS_GAMES) logo demos dev/examples/hello dev/examples/hgr dev/examples/dhgr

all:
	@for d in $(DIRS); do $(MAKE) -C $$d || exit 1; done

test: all test-pinball test-chromabreak test-arkabreakout test-chess test-hgr test-frame test-hgr-example test-assets bench-check
	$(MAKE) -C micro-sokoban test

test-hgr:
	python3 dev/tests/test_asm_boundaries.py
	python3 dev/tests/test_dos_reuse.py
	python3 dev/tests/test_exit_modes.py
	python3 dev/tests/test_hgr_host.py
	python3 dev/tests/test_hgr_x2.py
	python3 dev/tests/test_gfx_boundaries.py
	python3 dev/tests/test_gfx_outlines.py
	python3 dev/tests/test_hgr_logo.py
	python3 dev/tests/test_hgr_glyph8.py
	python3 dev/tests/test_logo_glyphs.py
	python3 dev/tests/test_hgr_sprite_update.py
	python3 dev/tests/test_video_memory.py
	python3 dev/tests/test_lores_modes.py
	python3 dev/tests/test_preshift_bounds.py
	python3 dev/tests/test_sprmask_bounds.py
	python3 dev/tests/test_sprite16_bounds.py
	python3 dev/tests/test_text8_strings.py
	python3 dev/tests/test_hgr_native.py
	python3 dev/tests/test_hgr_wireframe.py
	python3 dev/tests/test_hgr_lines.py
	python3 dev/tests/test_hgr_hud.py
	python3 dev/tests/test_hgr_hud.py --compact
	python3 dev/tests/test_presentation_strategies.py
	python3 dev/tests/test_hgr.py
	python3 dev/tests/test_hgr_glyphs.py
	python3 dev/tests/test_sprengine.py
	python3 dev/tests/test_sprengine_stress.py
	python3 dev/tests/test_sprengine_dirty.py
	python3 dev/tests/test_tilemap.py

test-frame:
	python3 dev/tests/test_frame.py

test-hgr-example:
	python3 dev/tests/test_hgr_example.py

test-dhgr:
	$(MAKE) -C dev/examples/dhgr test
	python3 dev/tests/test_dhgr_extended.py
	python3 dev/tests/test_dhgr_spans.py
	python3 dev/tests/test_dhgr_clear_rows.py
	python3 dev/tests/test_gfx_dhgr_lines.py
	python3 dev/tests/test_minimal_examples.py --dhgr
	python3 dev/tests/test_stack_profile.py --iie
	python3 dev/tests/test_hgr_hud.py --iie
	python3 dev/tests/test_presentation_strategies.py --iie
	python3 dev/tests/test_sprengine_dirty.py --iie
	python3 dev/tests/test_frame.py --iie
	python3 dev/tests/test_cadence.py
	python3 dev/tests/test_game_cadence.py
	python3 dev/tests/test_tilemap.py --iie
	python3 dev/tests/test_hgr_hud.py --compact --iie
	python3 dev/tests/test_sprengine_dirty.py --damage --iie
	python3 dev/tests/test_sprengine_damage.py
	python3 dev/tests/test_hgr_example.py --iie

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
	python3 dev/tools/fonts.py --check
	python3 dev/tests/test_assets.py

bench:
	python3 dev/bench/run.py

bench-dhgr:
	python3 dev/bench/run.py --dhgr

bench-check:
	python3 dev/bench/run.py --check

.PHONY: test-assets bench bench-dhgr bench-check

test-arkabreakout:
	$(MAKE) -C arkabreakout test

test-chess:
	$(MAKE) -C chess test

.PHONY: test-arkabreakout test-chess

profile-ii-plus:
	@for d in $(II_PLUS_GAMES); do $(MAKE) -C $$d || exit 1; done

profile-iie-prodos:
	$(MAKE) -C chromabreak

test-chromabreak:
	$(MAKE) -C chromabreak test

.PHONY: profile-ii-plus profile-iie-prodos test-chromabreak

test-pinball:
	$(MAKE) -C pinball test

.PHONY: test-pinball

test: test-light3dball
test-light3dball:
	$(MAKE) -C light3dball test
.PHONY: test-light3dball

test: test-techniques

test-techniques:
	$(MAKE) -C arkabreakout
	$(MAKE) -C micro-sokoban
	python3 dev/tests/techniques/run.py

.PHONY: test-techniques

# Native HGR lookup tables and checked fixed-sector DOS construction.
test: test-tools
test-tools:
	python3 dev/tests/test_stack_profile.py
	python3 dev/tests/test_build_config.py
	python3 dev/tests/test_prodos_video.py
	python3 dev/tests/test_apple2game.py
	python3 dev/tests/test_mouse_context.py
	python3 dev/tests/test_hgr_tables_disk.py
.PHONY: test-tools

# Optional RGB and Mockingboard ASM primitives, with traced hardware buses.
test-tools: test-hardware
test-hardware:
	python3 dev/tests/test_rgb_mockingboard.py
.PHONY: test-hardware

test: test-minimal
test-minimal:
	python3 dev/tests/test_minimal_examples.py
.PHONY: test-minimal

test: test-logo
test-logo:
	$(MAKE) -C logo test
.PHONY: test-logo

# Compiler-derived shared-library usage and transitive build dependencies.
audit-libs:
	python3 dev/tools/audit_lib_usage.py
.PHONY: audit-libs
