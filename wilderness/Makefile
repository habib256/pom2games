# Wilderness: A Survival Adventure (Electric Transit, 1985), reimplementation.
#
#   make            -> ../dist/WILDERNESS.dsk (Apple II+ 48 KB, DOS 3.3)
#   make run        -> boot it in POM2
#   make test       -> 6502 view vs tools/view_ref.py, in a2shot (+ short fuzz,
#                      key sequences against a model, walk to the west edge)
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

$(BUILD)/wild.o: src/wild.s $(BUILD)/tables.inc $(BUILD)/rowtab.inc $(A2_ASM_DEPS) Makefile
	$(CA65) -g -t none $(A2_INCS) -I $(BUILD) -l $(BUILD)/wild.lst -o $@ $<

$(BIN): $(BUILD)/wild.o src/wild.cfg
	$(LD65) -C src/wild.cfg -m $(BUILD)/wild.map -Ln $(BUILD)/wild.lbl -o $@ $<

$(DISK): $(BIN) $(MAPBIN) $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin WILDERNESS=$(BIN)@0x6000 --bin WILDLO=$(BUILD)/wildlo.bin@0x1000 --bin WILDMAP=$(MAPBIN)@0x7000

test: all $(A2SHOT)
	$(PYTHON) tests/test_view.py
	$(PYTHON) tests/test_fuzz.py 1 3 8
	$(PYTHON) tests/test_keys.py 1 200
	$(PYTHON) tests/test_keys.py --keys AAAJIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIMMIIIZZZZZZZZKKKK

# longer differential fuzz: make fuzz FUZZ_SEED=7
FUZZ_SEED ?= 2
fuzz: all $(A2SHOT)
	$(PYTHON) tests/test_fuzz.py $(FUZZ_SEED) 6 16

.PHONY: test fuzz originals extract run-original dump-game topo FORCE
FORCE:

# ---------------------------------------------------------------- analysis
IA := https://archive.org/download
WOZADAY := $(IA)/wozaday_Wilderness_A_Survival_Adventure
DEMO_ID := Wilderness_A_Survival_Adventure_Demonstration_Disk_Apple_II_Series_Electric_Tran

PROGRAM_WOZ := original/WILDERNESS.woz
JOURNEY_A2R := original/extras/Wilderness - Journey.a2r
DEMO_DSK := original/WILDERNESS_DEMO.dsk

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

