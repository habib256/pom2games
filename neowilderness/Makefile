# Neowilderness — Wilderness for the Apple IIe enhanced / IIc 128 KB, ProDOS 8,
# every module preloaded in auxiliary RAM (lots 1-2), DHGR landscape (lot 3),
# DHGR interface, 80-column text and TOPO computed in RAM (lot 4); start
# menu, six scenarios, night stars, score and hall of fame (lot 7).
#
#   make            -> ../dist/NEOWILDERNESSXL.po (ProDOS 8, 800 KB volume)
#   make run        -> boot it in POM2 (IIe enhanced preset)
#   make inspect    -> list the volume and the auxiliary-memory placement
#   make test       -> in a2shot (enhanced //e), through the start menu (Sierra
#                      Nevada, level 4; tests/test_menu.py drives the six
#                      scenarios): the DHGR view pixel for pixel against
#                      tools/dhgr_ref.py (band events of tools/view_ref.py)
#                      (turns, random positions, random commands against a
#                      model of the player) and the simulation (tests/test_sim.py)
#   make fuzz       -> longer random positions / synthetic maps
#
# Analysis of the original (docs/ANALYSE.md). Its images are copyrighted and
# stay out of git (original/ is ignored): `make originals` fetches them from
# archive.org, `make extract` decodes them into build/.

DEV ?= ../dev
APPLE2_PRESET := iie
include $(DEV)/cc65/apple2.mk
PRODOS := $(DEV)/lib/prodos

DISK := $(DIST)/NEOWILDERNESSXL.po
# Records of NEOWILD.DAT and the packs: lz (default since lot 7 step 5: 23
# blocks fewer than auto and a shorter choice -> first view, measured), auto
# (LZ where the 200/46 cycles-per-byte model says it shortens the boot) or
# raw; see docs/MEMORY.md 9.5.
BOOT_PACKING ?= lz
# Active edition since 16 October 2026: XL, 800 KB, six scenarios.
# The 140 KB edition is archived and has no build target here.
DISKXL := $(DIST)/NEOWILDERNESSXL.po
BIN  := $(BUILD)/wild.bin
MAPBIN := $(BUILD)/map.bin
# Reconstituted maps of the five other regions (lot 7, docs/REGIONS.md).
REGION_MAPS := $(foreach r,1 3 4 5 6,$(BUILD)/maps/r$(r).bin)
SEED ?= 1985
LEVEL ?= 4

all: $(DISKXL)

$(BUILD)/wild.o: src/medical.s src/hazards.s src/care.s src/alerts.s
$(BUILD)/wild.o: src/object_menu.s src/equipment.s
$(BUILD)/wild.o: src/ui_event.s src/ui_choice.inc src/clock.inc
$(BUILD)/wild.o: src/memory.s
$(BUILD)/wild.o: src/geography.s src/geoaux.s
$(BUILD)/wild.o: src/water.s src/camp.s src/menu.s
$(BUILD)/wild.o: src/prepare.s
$(BUILD)/wild.o: src/save.s src/pages.s
$(BUILD)/wild.o: src/orient.s $(BUILD)/textbank.inc
$(BUILD)/wild.o: src/forage.s src/frg.s src/craft.s
$(BUILD)/wild.o: src/fire.s $(BUILD)/fire.inc
$(BUILD)/wild.o: src/grid.s src/mousetext.inc src/mt_pages.s

# The animated campfire (docs/CAMP.md 8): art and layers of src/fire.s.
$(BUILD)/fire.inc: tools/genfire.py tools/dhgr_palette.py
	@mkdir -p $(@D)
	$(PYTHON) -I $< $@

$(BUILD)/textbank.inc: tools/gentextbank.py src/textbank.txt
	@mkdir -p $(@D)
	$(PYTHON) -I tools/gentextbank.py src/textbank.txt $@

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

$(BUILD)/hud.inc: tools/genhud.py tools/dhgr_font.py
	@mkdir -p $(@D)
	$(PYTHON) -I $< $@

$(BUILD)/summary_font.inc: tools/gen_summary_font.py tools/dhgr_font.py
	$(PYTHON) -I $< $@

$(BUILD)/sky_ephemeris.inc: tools/sky_ephemeris.py
	$(PYTHON) -I $< $@

$(BUILD)/forest_profiles.inc: tools/genforest.py
	$(PYTHON) -I $< $@

# The Sierra tables are linked into WILDGAME; every region's tables (lot 7,
# docs/DHGR.md) go to build/dhgr/dhgr_tables_rN.bin for its pack.
$(BUILD)/dhgr_tables.inc: tools/gendhgr.py tools/dhgr_palette.py
	@mkdir -p $(@D)
	$(PYTHON) -I $< --regions $(BUILD)/dhgr $@

# Night stars (lot 7 step 5, docs/STARS.md): catalogue and tables of the
# hourly module wildsky.bin.
$(BUILD)/stars_tables.inc: tools/genstars.py tools/stars_ref.py tools/stars_catalog.py tools/sky_ephemeris.py tools/dhgr_palette.py
	@mkdir -p $(@D)
	$(PYTHON) -I $< $@

$(BUILD)/wild.o: src/wild.s src/adventure.s src/outdoor.s src/game.s src/input.s src/weather.s src/travel.s src/survival.s src/sprites.s src/thermal.s src/sites.s src/topo_dhgr.s src/project.s src/fauna.s src/hud.s src/sky.s src/forest.s src/tree.s src/status.s src/inventory.s src/summary.s src/ui_monitor.s src/transitions.s src/dhgr.s src/stars.s src/stars_draw.s $(BUILD)/stars_tables.inc src/hof.s src/hof_menu.s src/hof_load.inc src/messages.inc $(BUILD)/dhgr_tables.inc $(BUILD)/tables.inc $(BUILD)/rowtab.inc $(BUILD)/gamedata.inc $(BUILD)/hud.inc $(BUILD)/summary_font.inc $(BUILD)/sky_ephemeris.inc $(BUILD)/forest_profiles.inc $(A2_ASM_DEPS) Makefile
	$(CA65) -g -t none $(A2_INCS) -I $(BUILD) -l $(BUILD)/wild.lst -o $@ $<

# Start menu texts (lot 7): region names, climate words and fauna sentences
# from the decoded region headers and the six map headers.
$(BUILD)/menu.inc: tools/genmenu.py $(BUILD)/regions/regions.json $(MAPBIN) $(REGION_MAPS)
	$(PYTHON) -I $< $@

$(BUILD)/boot.o: src/boot.s src/hof_menu.s src/mousetext.inc $(BUILD)/menu.inc $(A2_ASM_DEPS)
	@mkdir -p $(@D)
	$(CA65) -g -t none $(A2_INCS) -I $(BUILD) -l $(BUILD)/boot.lst -o $@ $<

# One link: the game images, the resident layer and NEOWILD.SYSTEM share
# build/wild.lbl, so tests and tools see every symbol. dev/lib/prodos is not
# linked (docs/MEMORY.md 15): the loader claims /RAM (src/boot.s ld_claim),
# the exit path formats it again (src/memory.s prodos_restore).
LINK_OBJS := $(BUILD)/wild.o $(BUILD)/boot.o
$(BIN): $(LINK_OBJS) src/wild.cfg
	$(LD65) -C src/wild.cfg -m $(BUILD)/wild.map -Ln $(BUILD)/wild.lbl -o $@ $(LINK_OBJS)

# Sprites of the trunk (wreck, cabin) and of the six region packs.
SPRITE_NAMES := wreck cabin bear cougar rattlesnake grizzly_bc wolf_bc moose_bc \
	tiger elephant cobra python dani adder crocodile puma jaguar ferdelance anaconda cat
SPRITE_BINS := $(addprefix $(BUILD)/original_graphics/,$(addsuffix .bin,$(SPRITE_NAMES)))

# GNU make 3.81 on macOS: one extraction, then timestamp its five outputs.
$(BUILD)/original_graphics/.done: tools/re_graphics.py tools/smalldos.py $(BUILD)/JOURNEY.dsk
	$(PYTHON) tools/re_graphics.py
	@touch $@

$(SPRITE_BINS): $(BUILD)/original_graphics/.done
	@test -f "$@" || $(PYTHON) tools/re_graphics.py
	@touch "$@"


# Empty hall of fame (lot 7 step 6, docs/HOF.md): one 512-byte block.
$(BUILD)/NEOWILD.HOF: tools/genhof.py tools/score_ref.py
	@mkdir -p $(@D)
	$(PYTHON) -I tools/genhof.py $@

$(BUILD)/JOURNEY.dsk: original/extras/Wilderness\ -\ Journey.a2r
	$(PYTHON) -I tools/flux2dsk.py "$<" $@

$(DISKXL): $(BIN) $(BUILD)/NEOWILD.HOF $(BUILD)/dhgr_tables.inc $(MAPBIN) $(REGION_MAPS) $(BUILD)/regions/regions.json $(SPRITE_BINS) $(DEV)/tools/prodos/PRODOS $(DEV)/tools/prodos/boot.bin $(DEV)/tools/prodos/build_volume.py tools/build_disk.py tools/pack_boot.py tools/geo_atlas.py Makefile
	@mkdir -p $(DIST)
	$(PYTHON) -I tools/build_disk.py --out $(DISKXL) --build $(BUILD) --packing $(BOOT_PACKING) --edition xl --layout $(BUILD)/layout.json

inspect: all
	$(PYTHON) -I $(DEV)/tools/prodos/read_volume.py $(DISKXL)
	$(PYTHON) -I tools/inspect_disk.py $(BUILD)/layout.json

# Active XL regression suite. Cross-edition historical tests are explicit.
test: test-xl
test-xl: all $(A2SHOT)
	$(PYTHON) tests/test_transfers.py
	$(PYTHON) tests/test_pack_boot.py
	$(PYTHON) tests/test_reference_state.py
	$(PYTHON) tests/test_input.py
	$(PYTHON) tests/test_navigation.py
	$(PYTHON) tests/test_object_actions.py
	$(PYTHON) tests/test_action_filter.py
	$(PYTHON) tests/test_use_requirements.py
	$(PYTHON) tests/test_camp_requirements.py
	$(PYTHON) tests/test_lighting_requirements.py
	$(PYTHON) tests/test_instrument_requirements.py
	$(PYTHON) tests/test_quick_quantities.py
	$(PYTHON) tests/test_transfer_weight_preview.py
	$(PYTHON) tests/test_object_care.py
	$(PYTHON) tests/test_object_taste.py
	$(PYTHON) tests/test_hung_preview.py
	$(PYTHON) tests/test_equipment.py
	$(PYTHON) tests/test_crafted_refusals.py
	$(PYTHON) tests/test_craft.py
	$(PYTHON) tests/test_craft_page.py
	$(PYTHON) tests/test_objects.py
	$(PYTHON) tests/test_focus.py
	$(PYTHON) tests/test_transitions.py
	$(PYTHON) tests/test_grid_play.py
	$(PYTHON) tests/test_grid_catch.py
	$(PYTHON) tests/test_joystick_journey.py
	$(PYTHON) tests/test_feedback.py
	$(PYTHON) tests/test_load.py
	$(PYTHON) tests/test_care.py
	$(PYTHON) tests/test_orientation.py
	$(PYTHON) tests/test_tree.py
	$(PYTHON) tests/test_view.py

test-all-editions: all $(A2SHOT)
	$(PYTHON) tests/test_journey.py
	$(PYTHON) tests/test_pack_boot.py
	$(PYTHON) tests/test_boot.py
	$(PYTHON) tests/test_editions.py
	$(PYTHON) tests/test_prodos.py
	$(PYTHON) tests/test_menu.py
	$(PYTHON) tests/test_prepare.py
	$(PYTHON) tests/test_transfers.py
	$(PYTHON) tests/test_resident.py
	$(PYTHON) tests/test_save.py
	$(PYTHON) tests/test_geo_resident.py
	$(PYTHON) tests/test_geo_atlas.py
	$(PYTHON) tests/test_journey_resident.py
	$(PYTHON) tests/test_reference_state.py
	$(PYTHON) tests/test_optimizations.py
	$(PYTHON) tests/test_fast_duration.py
	$(PYTHON) tests/test_input.py
	$(PYTHON) tests/test_navigation.py
	$(PYTHON) tests/test_menu_bar.py
	$(PYTHON) tests/test_altcharset.py
	$(PYTHON) tests/test_grid_play.py
	$(PYTHON) tests/test_grid_catch.py
	$(PYTHON) tests/test_sleep.py
	$(PYTHON) tests/test_clock.py
	$(PYTHON) tests/test_feedback.py
	$(PYTHON) tests/test_mapgen.py
	$(PYTHON) tests/test_regions.py
	$(PYTHON) tests/test_forest.py
	$(PYTHON) tests/test_tree.py
	$(PYTHON) tests/test_fauna.py
	$(PYTHON) tests/test_fauna_steps.py
	$(PYTHON) tests/test_boundary.py
	$(PYTHON) tests/test_walk.py
	$(PYTHON) tests/test_compass.py
	$(PYTHON) tests/test_orientation.py
	$(PYTHON) tests/test_hud.py
	$(PYTHON) tests/test_interface.py
	$(PYTHON) tests/test_transitions.py
	$(PYTHON) tests/test_focus.py
	$(PYTHON) tests/test_objects.py
	$(PYTHON) tests/test_screen_returns.py
	$(PYTHON) tests/test_sky.py
	$(PYTHON) tests/test_moonlight.py
	$(PYTHON) tests/test_site_directions.py
	$(PYTHON) tests/test_projection.py
	$(PYTHON) tests/test_graphical_topo.py
	$(PYTHON) -I tests/test_topo_dhgr.py
	$(PYTHON) tests/test_sites.py
	$(PYTHON) tests/test_scene_render.py
	$(PYTHON) tests/test_render_memory.py
	$(PYTHON) tests/test_sprites.py
	$(PYTHON) tests/test_animal_view.py
	$(PYTHON) tests/test_view.py
	$(PYTHON) tests/test_dhgr_mood.py
	$(PYTHON) tests/test_dhgr_video.py
	$(PYTHON) tests/test_dhgr_ref.py
	$(PYTHON) tests/test_stars_ref.py
	$(MAKE) -f stars.mk test
	$(PYTHON) tests/test_stars_game.py
	$(PYTHON) tests/test_pan.py
	$(PYTHON) tests/test_tilt.py
	$(PYTHON) tests/test_fuzz.py 1 3 8
	$(PYTHON) tests/test_play.py 1 30
	$(PYTHON) tests/test_play.py 2 30
	$(PYTHON) tests/test_sim.py
	$(PYTHON) tests/test_items.py
	$(PYTHON) tests/test_load.py
	$(PYTHON) tests/test_overlays.py
	$(PYTHON) tests/test_memory_cache.py
	$(PYTHON) tests/test_thermal.py
	$(PYTHON) tests/test_camp.py
	$(PYTHON) tests/test_fire.py
	$(PYTHON) tests/test_forage.py
	$(PYTHON) tests/test_craft.py
	$(PYTHON) tests/test_craft_page.py
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
	$(MAKE) -f hof.mk test
	$(PYTHON) tests/test_hof_game.py
	$(PYTHON) tests/test_hof_volume.py

# longer differential fuzz: make fuzz FUZZ_SEED=7
# The original disks must already be available locally (make extract).
# This is strict: known gameplay differences and unfinished commands fail.
test-original: all $(A2SHOT)
	$(PYTHON) ../dev/tests/test_a2shot_session.py
	$(PYTHON) tests/test_medical.py --original
	$(PYTHON) tests/test_care.py --original
	$(PYTHON) tools/re_orientation_probe.py
	$(PYTHON) tests/test_exposure.py --original
	$(PYTHON) tests/test_temperature_wave.py --original
	$(PYTHON) tests/test_weather_cycle.py --original
	$(PYTHON) tests/test_weather_front.py --original
	$(PYTHON) tests/test_weather_frequency.py --original
	$(PYTHON) tools/re_animal_reactions_probe.py
	$(PYTHON) tools/re_thermal_probe.py
	$(PYTHON) tools/re_camp_probe.py
	$(PYTHON) tools/re_forage_probe.py
	$(PYTHON) tests/test_forage.py --original
	$(PYTHON) tools/re_craft_probe.py
	$(PYTHON) tests/test_craft.py --original
	$(PYTHON) tools/re_load_probe.py
	$(PYTHON) tests/test_objects.py --original
	$(PYTHON) tests/test_swim_energy.py --original
	$(PYTHON) tests/test_swim_cadence.py --original
	$(PYTHON) tests/test_swim_raster.py --original
	$(PYTHON) tests/test_prepare.py --original
	$(PYTHON) tests/test_adventure.py --scenario all

FUZZ_SEED ?= 2
fuzz: all $(A2SHOT)
	$(PYTHON) tests/test_fuzz.py $(FUZZ_SEED) 6 16

.PHONY: test test-original fuzz inspect originals extract run-original dump-game topo FORCE
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


# ---------------------------------------------------------------- lot 7 data
# Original data of the six scenarios (docs/REGIONS.md), all in ignored build/:
#   make regions       -> build/regions/rN.bin + regions.json (checked against
#                         docs/regions.sha256), the 27 Journey sprites and
#                         their contact sheet, the five reconstituted maps
#                         build/maps/rN.bin (fixed seeds, mkmap.REGION_SEEDS)
#   make region-probe  -> encounter rules of every region on the original
#                         (a2shot), build/re_regions/ and build/regions/fauna.json

$(BUILD)/SIERRA.dsk: $(PROGRAM_WOZ)
	$(PYTHON) -I tools/flux2dsk.py $< $@

$(BUILD)/regions/regions.json: tools/regions.py tools/smalldos.py $(BUILD)/SIERRA.dsk
	$(PYTHON) -I tools/regions.py

$(BUILD)/maps/r%.bin: tools/mkmap.py tools/regions.py tools/topo.py $(BUILD)/regions/regions.json
	$(PYTHON) -I tools/mkmap.py --region $* $@ $(BUILD)/maps/r$*.png

regions: $(BUILD)/regions/regions.json $(BUILD)/original_graphics/.done $(REGION_MAPS)

region-probe: $(BUILD)/regions/regions.json $(A2SHOT)
	$(PYTHON) -I tools/re_region_fauna_probe.py

# Fidelity lot 1: the original's journey preparation (GO1, GO2) with fixed
# answers and an imposed RND -> build/re_prepare/cases.json (tests/test_prepare.py).
prepare-probe: $(A2SHOT)
	$(PYTHON) -I tools/re_prepare_probe.py

.PHONY: regions region-probe prepare-probe
