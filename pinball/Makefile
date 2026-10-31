# Bill Budge's Pinball Construction Set — DEVBENCH CC65 / Apple II+ and //c.
DEV ?= ../dev
include $(DEV)/cc65/apple2.mk
MOUSE := $(DEV)/lib/mouse
include $(MOUSE)/mouse.mk
APPLE2_RUN_FLAGS := --slot 4=mouseaw
DISK := $(DIST)/PINBALL.dsk
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
$(BUILD)/mouse.bin: src/mouse.s src/mouse.cfg $(MOUSE_SRCS) $(MOUSE_CONTEXT_SRCS)
	@mkdir -p $(BUILD)
	$(CA65) $(MOUSE_INCS) -o $(BUILD)/mouse_adapter.o src/mouse.s
	$(CA65) -o $(BUILD)/mouse_driver.o $(MOUSE)/mouse.s
	$(LD65) -C src/mouse.cfg -o $@ -Ln $(BUILD)/mouse.lbl $(BUILD)/mouse_adapter.o $(BUILD)/mouse_driver.o
$(DISK): $(BINS) $(BUILD)/boot.bin $(BUILD)/mouse.bin tools/build_disk.py $(wildcard assets/*.bin) $(DEV)/tools/dos33.py $(DEV)/tools/hgr_tables.py $(SYSTEM)
	$(PYTHON) tools/build_disk.py --build $(BUILD) --master $(SYSTEM) --out $@
.PRECIOUS: $(BUILD)/%.s
test: all $(A2RUN) $(if $(A2SHOT_HOST),$(BUILD)/mouse_probe)
	$(PYTHON) tests/test_pinball.py
ifneq ($(A2SHOT_HOST),)
	$(PYTHON) tests/test_mouse.py --probe $(BUILD)/mouse_probe --roms $(DEV)/tools/a2shot/roms
endif

# Long tier (convention of ../dev/cc65/apple2.mk): nothing slow yet.
test-long:
	@echo "pinball: no long tests"
.PHONY: test-long
.PHONY: test
