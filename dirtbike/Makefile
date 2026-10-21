# DIRTBIKE — Apple II+ 48 KB / DOS 3.3 build
#
#   make            -> ../dist/DIRTBIKE.dsk
#   make run        -> boot it in POM2 as an Apple II+
#   make test       -> the 30 tracks have solutions, 6502 physics == model,
#                      game checks
#   tools/solver.py --all tests/solutions.txt   after changing tracks or physics
#   make clean / distclean
#
# The shared rules and tool variables come from ../dev/cc65/apple2.mk.

DEV ?= ../dev
include $(DEV)/cc65/apple2.mk
include $(DEV)/cc65/fhpack.mk
MOUSE := $(DEV)/lib/mouse
include $(MOUSE)/mouse.mk

DISK := $(DIST)/DIRTBIKE.dsk
GEN  := src/physconst.inc src/sprites.inc src/music.inc src/pages.inc
SRCS := src/dirtbike.s src/input.inc src/physics.inc src/render.inc \
        src/menu.inc src/loader.inc src/tricks.inc src/hof.inc src/title.inc src/mainmenu.inc
TRACKS := $(foreach k,01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 \
            21 22 23 24 25 26 27 28 29 30,$(BUILD)/tracks/T$(k).bin)

all: $(DISK)

src/physconst.inc: tools/physconst.py tools/physics.py
	$(PYTHON) tools/physconst.py $@

src/music.inc $(BUILD)/tune.bin: tools/music.py
	@mkdir -p $(BUILD)
	$(PYTHON) tools/music.py src/music.inc $(BUILD)/tune.bin

src/pages.inc $(BUILD)/pages.bin: tools/pages.py
	@mkdir -p $(BUILD)
	$(PYTHON) tools/pages.py src/pages.inc $(BUILD)/pages.bin

src/sprites.inc: tools/sprites.py
	$(PYTHON) tools/sprites.py $@

$(TRACKS) $(BUILD)/tracks/menu_data.inc &: tools/packtrack.py tools/tracks.py tools/track.py \
		tools/trackcheck.py tests/solutions.txt $(FHPACK)
	$(PYTHON) tools/packtrack.py $(FHPACK) $(BUILD)/tracks

$(BUILD)/title.hgr: tools/title.py
	@mkdir -p $(BUILD)
	$(PYTHON) tools/title.py $@

$(BUILD)/TITLE.bin: $(BUILD)/title.hgr $(BUILD)/tune.bin $(BUILD)/pages.bin $(BUILD)/dirtbike.bin \
		tools/titlefile.py $(FHPACK)
	$(FHPACK) -c -9 -h $< $(BUILD)/title.lz4
	$(PYTHON) tools/titlefile.py $@ $(BUILD)/tune.bin $(BUILD)/pages.bin $(BUILD)/menu.bin $(BUILD)/title.lz4

$(BUILD)/hof.bin: tools/hof.py
	@mkdir -p $(BUILD)
	$(PYTHON) tools/hof.py $@

$(BUILD)/dirtbike.o: $(SRCS) $(GEN) $(BUILD)/tracks/menu_data.inc $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none -g $(A2_INCS) -I $(BUILD)/tracks -l $(BUILD)/dirtbike.lst -o $@ $<

$(BUILD)/mouse.o: $(MOUSE_SRCS)
	@mkdir -p $(BUILD)
	$(CA65) -t none -D MOUSE_INIT_BOOT -o $@ $<

$(BUILD)/dirtbike.bin: $(BUILD)/dirtbike.o $(BUILD)/mouse.o src/dirtbike.cfg
	$(LD65) -C src/dirtbike.cfg -m $(BUILD)/dirtbike.map -Ln $(BUILD)/dirtbike.lbl -o $@ \
		$(BUILD)/dirtbike.o $(BUILD)/mouse.o

$(DISK): $(BUILD)/dirtbike.bin $(TRACKS) $(BUILD)/TITLE.bin $(BUILD)/hof.bin tools/patchdir.py $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) --bin DIRTBIKE=$(BUILD)/dirtbike.bin@$(LOAD) \
		--bin TITLE=$(BUILD)/TITLE.bin@0x9600 --bin DIRTHOF=$(BUILD)/hof.bin@0xB500 \
		$(foreach t,$(TRACKS),--bin $(basename $(notdir $(t)))=$(t)@0x9600)
	$(PYTHON) tools/patchdir.py $@ $(BUILD)/dirtbike.lbl

test: all $(A2RUN)
	$(PYTHON) tools/trackcheck.py
	$(PYTHON) tests/test_physics.py
	$(PYTHON) tests/test_tracks.py
	$(PYTHON) tests/test_attract.py

.PHONY: test

POM2_SRC ?= ../../pom2
test-mouse: all
	$(PYTHON) tests/test_mouse.py --pom2-src $(POM2_SRC)
.PHONY: test-mouse
