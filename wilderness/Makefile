# Wilderness: A Survival Adventure (Electric Transit, 1985), reimplementation.
#
#   make            -> ../dist/WILDERNESS.dsk (Apple II+ 48 KB, DOS 3.3)
#   make run        -> boot it in POM2
#   make test       -> in a2shot: the view bit for bit against tools/view_ref.py
#                      (turns, random positions, random commands against a
#                      model of the player) and the simulation (tests/test_sim.py)
#   make fuzz       -> longer random positions / synthetic maps
#
# Analysis of the original (docs/ANALYSE.md). Its images are copyrighted and
# stay out of git (original/ is ignored): `make originals` fetches them from
# archive.org, `make extract` decodes them into build/.

DEV ?= ../dev
include $(DEV)/cc65/apple2.mk

DISK := $(DIST)/WILDERNESS.dsk
BIN  := $(BUILD)/wild.bin
MAPBIN := $(BUILD)/map.bin
SEED ?= 1985
LEVEL ?= 4

all: $(DISK)

$(BUILD)/wild.o: src/medical.s src/hazards.s src/care.s
$(BUILD)/wild.o: src/clock.inc
$(BUILD)/wild.o: src/overlay_codec.s
$(BUILD)/wild.o: src/geography.s
$(BUILD)/wild.o: src/water.s

$(BUILD)/tables.inc $(BUILD)/rowtab.inc: tools/gentables.py
	@mkdir -p $(@D)
	$(PYTHON) -I $< $(BUILD)/tables.inc $(BUILD)/rowtab.inc

# map.args changes only when SEED or LEVEL do, so the map follows them.
$(BUILD)/map.args: FORCE
	@mkdir -p $(@D)
	@echo "$(SEED) $(LEVEL)" | cmp -s - $@ || echo "$(SEED) $(LEVEL)" > $@

$(MAPBIN): tools/mkmap.py tools/topo.py $(BUILD)/map.args
	@mkdir -p $(@D)
	$(PYTHON) -I $< --seed $(SEED) --level $(LEVEL) $@ $(BUILD)/map.png

$(BUILD)/gamedata.inc: tools/gendata.py
	@mkdir -p $(@D)
	$(PYTHON) -I $< $@

$(BUILD)/hud.inc: tools/genhud.py $(DEV)/tools/fonts.py $(DEV)/lib/font/bbfont_glyphs.inc
	@mkdir -p $(@D)
	$(PYTHON) -I $< $@

$(BUILD)/summary_font.inc: tools/gen_summary_font.py $(DEV)/tools/fonts.py
	$(PYTHON) -I $< $@

$(BUILD)/sky_ephemeris.inc: tools/sky_ephemeris.py
	$(PYTHON) -I $< $@

$(BUILD)/forest_profiles.inc: tools/genforest.py
	$(PYTHON) -I $< $@

$(BUILD)/wild.o: src/wild.s src/adventure.s src/outdoor.s src/game.s src/input.s src/weather.s src/travel.s src/survival.s src/sprites.s src/thermal.s src/sites.s src/project.s src/fauna.s src/hud.s src/sky.s src/forest.s src/tree.s src/status.s src/inventory.s src/summary.s src/ui_monitor.s src/transitions.s src/messages.inc $(BUILD)/tables.inc $(BUILD)/rowtab.inc $(BUILD)/gamedata.inc $(BUILD)/hud.inc $(BUILD)/summary_font.inc $(BUILD)/sky_ephemeris.inc $(BUILD)/forest_profiles.inc $(A2_ASM_DEPS) Makefile
	$(CA65) -g -t none $(A2_INCS) -I $(BUILD) -l $(BUILD)/wild.lst -o $@ $<

$(BIN): $(BUILD)/wild.o src/wild.cfg
	$(LD65) -C src/wild.cfg -m $(BUILD)/wild.map -Ln $(BUILD)/wild.lbl -o $@ $<

SPRITE_NAMES := wreck bear cougar rattlesnake cabin
SPRITE_BINS := $(addprefix $(BUILD)/original_graphics/,$(addsuffix .bin,$(SPRITE_NAMES)))

# GNU make 3.81 on macOS: one extraction, then timestamp its five outputs.
$(BUILD)/original_graphics/.done: tools/re_graphics.py tools/smalldos.py $(BUILD)/JOURNEY.dsk
	$(PYTHON) tools/re_graphics.py
	@touch $@

$(SPRITE_BINS): $(BUILD)/original_graphics/.done
	@test -f "$@" || $(PYTHON) tools/re_graphics.py
	@touch "$@"


$(BUILD)/JOURNEY.dsk: original/extras/Wilderness\ -\ Journey.a2r
	$(PYTHON) -I tools/flux2dsk.py "$<" $@

$(BUILD)/boot.o: src/boot.s $(A2_ASM_DEPS)
	@mkdir -p $(@D)
	$(CA65) -g -t none $(A2_INCS) -o $@ $<

$(BUILD)/boot.bin: $(BUILD)/boot.o src/boot.cfg
	$(LD65) -C src/boot.cfg -m $(BUILD)/boot.map -Ln $(BUILD)/boot.lbl -o $@ $<

$(DISK): $(BIN) $(MAPBIN) $(BUILD)/boot.bin $(SPRITE_BINS) $(DOS33_DEPS) tools/build_disk.py tools/graphical_topo.py tools/pack_boot.py tools/pack_overlay.py tools/smalldos.py Makefile
	@mkdir -p $(DIST)
	$(PYTHON) -I tools/build_disk.py --out $(DISK) --build $(BUILD) --master $(SYSTEM)

test: all $(A2SHOT)
	$(PYTHON) tests/test_journey.py
	$(PYTHON) tests/test_pack_boot.py
	$(PYTHON) tests/test_overlay_codec.py
	$(PYTHON) tests/test_boot.py
	$(PYTHON) tests/test_optimizations.py
	$(PYTHON) tests/test_fast_duration.py
	$(PYTHON) tests/test_input.py
	$(PYTHON) tests/test_sleep.py
	$(PYTHON) tests/test_clock.py
	$(PYTHON) tests/test_feedback.py
	$(PYTHON) tests/test_mapgen.py
	$(PYTHON) tests/test_forest.py
	$(PYTHON) tests/test_tree.py
	$(PYTHON) tests/test_fauna.py
	$(PYTHON) tests/test_fauna_steps.py
	$(PYTHON) tests/test_boundary.py
	$(PYTHON) tests/test_walk.py
	$(PYTHON) tests/test_compass.py
	$(PYTHON) tests/test_hud.py
	$(PYTHON) tests/test_interface.py
	$(PYTHON) tests/test_sky.py
	$(PYTHON) tests/test_moonlight.py
	$(PYTHON) tests/test_site_directions.py
	$(PYTHON) tests/test_projection.py
	$(PYTHON) tests/test_graphical_topo.py
	$(PYTHON) tests/test_transitions.py
	$(PYTHON) tests/test_sites.py
	$(PYTHON) tests/test_scene_render.py
	$(PYTHON) tests/test_render_memory.py
	$(PYTHON) tests/test_sprites.py
	$(PYTHON) tests/test_view.py
	$(PYTHON) tests/test_pan.py
	$(PYTHON) tests/test_fuzz.py 1 3 8
	$(PYTHON) tests/test_play.py 1 30
	$(PYTHON) tests/test_play.py 2 30
	$(PYTHON) tests/test_sim.py
	$(PYTHON) tests/test_items.py
	$(PYTHON) tests/test_load.py
	$(PYTHON) tests/test_overlays.py
	$(PYTHON) tests/test_memory_cache.py
	$(PYTHON) tests/test_thermal.py
	$(PYTHON) tests/test_medical.py
	$(PYTHON) tests/test_care.py
	$(PYTHON) tests/test_exposure.py
	$(PYTHON) tests/test_wind_energy.py
	$(PYTHON) tests/test_temperature_wave.py
	$(PYTHON) tests/test_weather_cycle.py
	$(PYTHON) tests/test_weather_front.py
	$(PYTHON) tests/test_weather_frequency.py
	$(PYTHON) tests/test_swim_energy.py
	$(PYTHON) tests/test_swim_cadence.py
	$(PYTHON) tests/test_swim_raster.py
	$(PYTHON) tests/test_shore.py
	$(PYTHON) tests/test_wet.py

# longer differential fuzz: make fuzz FUZZ_SEED=7
# The original disks must already be available locally (make extract).
# This is strict: known gameplay differences and unfinished commands fail.
test-original: all $(A2SHOT)
	$(PYTHON) ../dev/tests/test_a2shot_session.py
	$(PYTHON) tests/test_medical.py --original
	$(PYTHON) tests/test_care.py --original
	$(PYTHON) tests/test_exposure.py --original
	$(PYTHON) tests/test_temperature_wave.py --original
	$(PYTHON) tests/test_weather_cycle.py --original
	$(PYTHON) tests/test_weather_front.py --original
	$(PYTHON) tests/test_weather_frequency.py --original
	$(PYTHON) tools/re_animal_reactions_probe.py
	$(PYTHON) tests/test_swim_energy.py --original
	$(PYTHON) tests/test_swim_cadence.py --original
	$(PYTHON) tests/test_swim_raster.py --original
	$(PYTHON) tests/test_adventure.py --scenario all

FUZZ_SEED ?= 2
fuzz: all $(A2SHOT)
	$(PYTHON) tests/test_fuzz.py $(FUZZ_SEED) 6 16

.PHONY: test test-original fuzz originals extract run-original dump-game topo FORCE
FORCE:

# ---------------------------------------------------------------- analysis
IA := https://archive.org/download
WOZADAY := $(IA)/wozaday_Wilderness_A_Survival_Adventure
DEMO_ID := Wilderness_A_Survival_Adventure_Demonstration_Disk_Apple_II_Series_Electric_Tran

PROGRAM_WOZ := original/WILDERNESS.woz
JOURNEY_A2R := original/extras/Wilderness - Journey.a2r
DEMO_DSK := original/WILDERNESS_DEMO.dsk

original/extras/Wilderness\ -\ Journey.a2r: original/extras/.done
	@test -f "$@"

originals: $(PROGRAM_WOZ) $(DEMO_DSK) original/extras/.done

$(PROGRAM_WOZ):
	mkdir -p original
	curl -sfLo $@ "$(WOZADAY)/00playable.woz"

$(DEMO_DSK):
	mkdir -p original
	curl -sfLo $@ "$(IA)/$(DEMO_ID)/Wilderness_A_Survival_Adventure_Demonstration_Disk_Apple_II_Series_Electric_Transit.dsk"

original/extras/.done:
	mkdir -p original/extras
	curl -sfLo original/extras.zip "$(WOZADAY)/Wilderness-%20A%20Survival%20Adventure%20extras%20(woz-a-day%20collection).zip"
	unzip -qjo original/extras.zip -d original/extras && rm original/extras.zip
	touch $@

# build/SIERRA.dsk  program side (boots only from the .woz: copy protection)
# build/JOURNEY.dsk data side (no catalog, read by track/sector)
# build/files/      SMALLDOS files of the program side
extract: originals
	mkdir -p build
	python3 -I tools/flux2dsk.py $(PROGRAM_WOZ) build/SIERRA.dsk
	python3 -I tools/flux2dsk.py "$(JOURNEY_A2R)" build/JOURNEY.dsk
	cp $(PROGRAM_WOZ) build/SIERRA.woz
	python3 -I tools/smalldos.py build/SIERRA.dsk --extract build/files
	python3 -I tools/smalldos.py $(DEMO_DSK) --extract build/demo

# Boot the original to the main menu and dump the menu program.
run-original: extract
	$(A2SHOT) --disk build/SIERRA.woz wait:5400 shot:build/menu.png peek:0000:0xC000 2>/dev/null \
	  | python3 -I tools/peek2bin.py > build/menu.bin
	python3 -I -c 'import sys; sys.path.insert(0, "tools"); import applesoft as A; \
	  m = open("build/menu.bin", "rb").read(); e = m[0x69] | m[0x6A] << 8; \
	  print("\n".join(A.listing(m[0x800:e])))' > build/MENU.bas

# Start a first journey (menu 1, swap in the Journey disk, skip the intro)
# and dump RAM with the first view on screen.
dump-game: extract
	$(A2SHOT) --disk build/SIERRA.woz wait:5400 key:"1\r" wait:3000 insert:build/JOURNEY.dsk \
	  key:"\r" wait:3000 key:"\r" wait:600 key:"\r" wait:1800 shot:build/game.png \
	  peek:0000:0xC000 2>/dev/null | python3 -I tools/peek2bin.py > build/game.bin

# Decoded supplied map and the first view from the crash site (heading 128).
topo: extract
	python3 -I tools/topo.py build/files/TOPO.B build/topo.png
	python3 -I tools/view3d.py build/files/TOPO.B 23 86 128 build/view.png

