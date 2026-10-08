# Bill Budge's Pinball Construction Set — DEVBENCH CC65 / Apple II+ and //c.
DEV ?= ../dev
include $(DEV)/cc65/apple2.mk
MOUSE := $(DEV)/lib/mouse
include $(MOUSE)/mouse.mk
APPLE2_RUN_FLAGS := --slot 4=mouseaw
DISK := $(DIST)/FLIPPER.dsk
MODULES := CDRAW EDIT PPAK RUN2 BOOT2 DISK RUN SWAP WIRE
BINS := $(addprefix $(BUILD)/,$(addsuffix .bin,$(MODULES)))
vpath %.S upstream/source_disc1 upstream/source_disc2
all: $(DISK)
$(BUILD)/%.s: %.S tools/translate.py
	$(PYTHON) tools/translate.py $< $@
$(BUILD)/%.bin: $(BUILD)/%.s
	$(CA65) -o $(BUILD)/$*.o $<
	$(LD65) -C $(BUILD)/$*.cfg -o $@ -Ln $(BUILD)/$*.lbl $(BUILD)/$*.o
$(BUILD)/boot.bin: src/boot.s src/boot.cfg $(SYSTEM)
	@mkdir -p $(BUILD)
	$(CA65) --bin-include-dir $(DEV)/tools -o $(BUILD)/boot.o src/boot.s
	$(LD65) -C src/boot.cfg -o $@ $(BUILD)/boot.o
$(BUILD)/mouse.bin: src/mouse.s src/mouse.cfg $(MOUSE_SRCS)
	@mkdir -p $(BUILD)
	$(CA65) -o $(BUILD)/mouse_adapter.o src/mouse.s
	$(CA65) -o $(BUILD)/mouse_driver.o $(MOUSE)/mouse.s
	$(LD65) -C src/mouse.cfg -o $@ -Ln $(BUILD)/mouse.lbl $(BUILD)/mouse_adapter.o $(BUILD)/mouse_driver.o
$(DISK): $(BINS) $(BUILD)/boot.bin $(BUILD)/mouse.bin tools/build_disk.py $(wildcard assets/*.bin) $(DEV)/tools/dos33.py $(SYSTEM)
	$(PYTHON) tools/build_disk.py --build $(BUILD) --master $(SYSTEM) --out $@
.PRECIOUS: $(BUILD)/%.s
test: all $(A2RUN)
	$(PYTHON) tests/test_flipper.py
.PHONY: test
POM2_SRC ?= ../../pom2
test-mouse: all
	$(PYTHON) tests/test_mouse.py --pom2-src $(POM2_SRC)
.PHONY: test-mouse

run-iic: all
	$(POM2) --preset iic --slot 4=iicmouse $(DISK)
.PHONY: run-iic
