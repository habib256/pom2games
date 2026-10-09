# hello — the two starter programs for dev/lib (asm + C) on one DOS 3.3 disk
#
#   make            -> ../../../dist/HELLO.dsk   (boots into HELLOASM; then BRUN HELLOC)
#   make run        -> boot it in POM2 as an Apple II+
#
# Copy this folder to start a new Apple II program. Copied next to micro-sokoban/,
# set DEV ?= ../dev and DIST ?= ../dist so the disk joins the others.

DEV     ?= ../..
DIST    ?= ../../../dist
include $(DEV)/cc65/apple2.mk
include $(APPLE2C)/apple2c.mk

DISK    := $(DIST)/HELLO.dsk

all: $(DISK)

# --- asm track ---------------------------------------------------------------
$(BUILD)/hello_asm.o: src/hello_asm.s $(A2_ASM_DEPS)
	@mkdir -p $(BUILD)
	$(CA65) -t none $(A2_INCS) -o $@ $<

$(BUILD)/hello_asm.bin: $(BUILD)/hello_asm.o $(A2_HGR_CFG)
	$(LD65) -C $(A2_HGR_CFG) -o $@ $<

# --- C track (crt0_apple2 first) ---------------------------------------------
C_OBJS := $(BUILD)/crt0_apple2.o $(BUILD)/hello_c.o $(BUILD)/apple2io.o $(BUILD)/apple2io_asm.o

$(BUILD)/crt0_apple2.o: $(A2_CRT0)
	@mkdir -p $(BUILD)
	$(CA65) -t none -o $@ $<
$(BUILD)/apple2io_asm.o: $(APPLE2C)/apple2io_asm.s
	@mkdir -p $(BUILD)
	$(CA65) -t none -o $@ $<
$(BUILD)/apple2io.o: $(APPLE2C)/apple2io.c $(APPLE2C)/apple2io.h
	@mkdir -p $(BUILD)
	$(CL65) -t none -Oirs $(APPLE2C_INCS) -c -o $@ $<
$(BUILD)/hello_c.o: src/hello_c.c $(APPLE2C_HEADERS)
	@mkdir -p $(BUILD)
	$(CL65) -t none -Oirs $(APPLE2C_INCS) -c -o $@ $<

$(BUILD)/hello_c.bin: $(C_OBJS) $(A2_HGR_C_CFG)
	$(CL65) -t none -C $(A2_HGR_C_CFG) -o $@ $(C_OBJS)

# --- disk --------------------------------------------------------------------
$(DISK): $(BUILD)/hello_asm.bin $(BUILD)/hello_c.bin $(DOS33_DEPS)
	@mkdir -p $(DIST)
	$(DOS33) \
	    --bin HELLOASM=$(BUILD)/hello_asm.bin@$(LOAD) \
	    --bin HELLOC=$(BUILD)/hello_c.bin@$(LOAD) \
	    --catalog
