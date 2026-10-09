# VERHILLE Arnaud — GPL-3.0. Three standalone integration examples.
DEV ?= ../..
include $(DEV)/cc65/apple2.mk
include $(HGRC)/hgrc.mk
include $(APPLE2C)/apple2c.mk
PRODOS := $(DEV)/lib/prodos
include $(PRODOS)/prodos.mk
HGRC_EXTRA_SRCS := $(APPLE2C_SRCS) $(APPLE2C_FRAME_SRCS) $(PRODOS_SRCS)
HGRC_CFLAGS := -t none -Oirs $(HGRC_INCS) $(APPLE2C_INCS) $(PRODOS_INCS)
CFLAGS := $(HGRC_CFLAGS)
IMAGES := $(BUILD)/hgr-single.dsk $(BUILD)/hgr-double.dsk $(BUILD)/dhgr-prodos.po

all: $(IMAGES) $(BUILD)/memory.json

$(BUILD)/crt0_apple2.o: $(A2_CRT0)
	@mkdir -p $(@D)
	$(CA65) -t none -o $@ $<
$(BUILD)/crt0_prodos.o: $(DEV)/cc65/crt0_prodos.s
	@mkdir -p $(@D)
	$(CA65) -t none -o $@ $<
$(BUILD)/hgr-single.o: src/hgr_minimal.c Makefile $(HGRC_HEADERS)
	@mkdir -p $(@D)
	$(CL65) $(CFLAGS) -D DOUBLE_BUFFERED=0 -c -o $@ $<
$(BUILD)/hgr-double.o: src/hgr_minimal.c Makefile $(HGRC_HEADERS)
	@mkdir -p $(@D)
	$(CL65) $(CFLAGS) -D DOUBLE_BUFFERED=1 -c -o $@ $<
$(BUILD)/dhgr-prodos.o: src/dhgr_prodos.c Makefile $(HGRC_HEADERS) $(PRODOS)/prodos.h
	@mkdir -p $(@D)
	$(CL65) $(CFLAGS) -c -o $@ $<
$(BUILD)/hgr-%.bin: $(BUILD)/hgr-%.o $(BUILD)/crt0_apple2.o $(HGRC_LIB) $(A2_HGR_C_CFG)
	$(CL65) -t none -C $(A2_HGR_C_CFG) -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) -o $@ $(BUILD)/crt0_apple2.o $< $(HGRC_LIB)
$(BUILD)/dhgr-prodos.bin: $(BUILD)/dhgr-prodos.o $(BUILD)/crt0_prodos.o $(HGRC_LIB) $(DEV)/cc65/apple2_dhgr_prodos_c.cfg
	$(CL65) -t none -C $(DEV)/cc65/apple2_dhgr_prodos_c.cfg -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) -o $@ $(BUILD)/crt0_prodos.o $< $(HGRC_LIB)
$(BUILD)/hgr-%.dsk: $(BUILD)/hgr-%.bin $(SYSTEM) $(DEV)/tools/dos33.py
	@printf '10 PRINT CHR$$(4);"BRUN DEMO"\n' > $(BUILD)/hello.bas
	$(PYTHON) $(DEV)/tools/dos33.py --master $(SYSTEM) --out $@ --bas HELLO=$(BUILD)/hello.bas --bin DEMO=$<@$(LOAD)
$(BUILD)/DEMO.SYSTEM: src/loader.s src/loader.cfg
	@mkdir -p $(@D)
	$(CA65) -o $(BUILD)/loader.o $<
	$(LD65) -C src/loader.cfg -o $@ $(BUILD)/loader.o
$(BUILD)/dhgr-prodos.po: $(BUILD)/dhgr-prodos.bin $(BUILD)/DEMO.SYSTEM $(DEV)/tools/prodos/PRODOS $(DEV)/tools/prodos/boot.bin $(DEV)/tools/prodos/build_volume.py
	@mkdir -p $(BUILD)/stage
	cp $(DEV)/tools/prodos/PRODOS $(BUILD)/stage/PRODOS#FF0000
	cp $(BUILD)/DEMO.SYSTEM $(BUILD)/stage/DEMO.SYSTEM#FF2000
	cp $(BUILD)/dhgr-prodos.bin $(BUILD)/stage/DEMO.BIN#066000
	$(PYTHON) $(DEV)/tools/prodos/build_volume.py $(BUILD)/stage $@ --volume MINIMAL --boot $(DEV)/tools/prodos/boot.bin --blocks 280
$(BUILD)/memory.json: $(IMAGES) $(DEV)/tools/example_memory.py
	$(PYTHON) $(DEV)/tools/example_memory.py $(BUILD) --out $@

include $(HGRC)/hgrc_build.mk

# Keep linked binaries available alongside the maps and disk images.
.SECONDARY:
