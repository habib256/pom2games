# DEMO — five Apple II demos on one DOS 3.3 disk, with a menu
#
#   make            -> dist/DEMO.dsk
#   make run        -> boot it in POM2 as an Apple II+
#   make clean
#
# Needs cc65 (cl65/ca65/ld65/ar65) and python3 only: the shared ../dev tree has
# the rest. The C demos rebuild the hgrc runtime with their own -D HGRC_NO_*
# flags so each one links only the routine families it calls (ANIMALS would not
# fit under DOS otherwise).

CL65    ?= cl65
CA65    ?= ca65
LD65    ?= ld65
AR65    ?= ar65
PYTHON  ?= python3
DEV     ?= ../dev
POM2    ?= /Applications/POM2.app/Contents/MacOS/POM2
SYSTEM  ?= $(DEV)/tools/dos33_system.bin

HGRC    := $(DEV)/lib/hgrc
GFX     := $(DEV)/lib/gfx
APPLE2C := $(DEV)/lib/apple2c
APPLE2  := $(DEV)/lib/apple2
HGR     := $(DEV)/lib/hgr
BUILD   := build
DIST    := dist
DISK    := $(DIST)/DEMO.dsk
LOAD    := 0x6000

CFLAGS  := -t none -Oirs -I src -I $(HGRC) -I $(APPLE2C) -I $(GFX)
AFLAGS  := -t none -I $(APPLE2) -I $(HGRC)

# The runtime, compiled once per C demo (with that demo's flags).
LIB_C   := gen2_init.c gen2_rect.c gen2_text.c gen2_text_num.c gen2_pixel.c \
           gen2_sprites.c gen2_preshift.c gen2_geom.c \
           gfx_line.c gfx_rect.c gfx_num_hex.c gfx_backend_gen2.c gfx_backend_gen2_rect.c \
           apple2io.c
LIB_S   := gen2_blit.s apple2io_asm.s
LIB_O   := $(LIB_C:.c=.o) $(LIB_S:.s=.o)
HDRS    := $(wildcard $(HGRC)/*.h $(HGRC)/*.inc $(APPLE2C)/*.h $(GFX)/*.h src/*.h)

vpath %.c src $(HGRC) $(GFX) $(APPLE2C)
vpath %.s src $(HGRC) $(APPLE2C) $(DEV)/cc65

# Routine families each C demo leaves out (see dev/lib/hgrc/gen2_blit.s).
FLAGS_bounces  := -DHGRC_NO_BLIT -DHGRC_NO_PRESHIFT -DHGRC_NO_COLORIZE \
                  -DHGRC_NO_CIRCLE -DHGRC_NO_ELLIPSE
FLAGS_animals  := -DHGRC_NO_TEXT16 -DHGRC_NO_UTOA -DHGRC_NO_BLIT -DHGRC_NO_PRESHIFT \
                  -DHGRC_NO_PLOT -DHGRC_NO_PIXRECT -DHGRC_NO_COLORIZE \
                  -DHGRC_NO_CIRCLE -DHGRC_NO_ELLIPSE
FLAGS_preshift := -DHGRC_NO_TEXT16 -DHGRC_NO_TEXT8 -DHGRC_NO_UTOA -DHGRC_NO_BLIT \
                  -DHGRC_NO_PLOT -DHGRC_NO_CIRCLE -DHGRC_NO_ELLIPSE

C_DEMOS   := bounces animals preshift
ASM_DEMOS := life font

all: $(DISK)

# --- C demos -----------------------------------------------------------------
$(BUILD)/crt0_apple2.o: crt0_apple2.s
	@mkdir -p $(BUILD)
	$(CA65) -t none -o $@ $<

define c_demo
$(BUILD)/$(1)/%.o: %.c $(HDRS)
	@mkdir -p $$(@D)
	$(CL65) $(CFLAGS) $$(FLAGS_$(1)) -c -o $$@ $$<

$(BUILD)/$(1)/%.o: %.s $(wildcard $(APPLE2)/*.inc $(APPLE2)/*.asm)
	@mkdir -p $$(@D)
	$(CA65) $(AFLAGS) $$(FLAGS_$(1)) -o $$@ $$<

$(BUILD)/$(1)/hgrc.lib: $(addprefix $(BUILD)/$(1)/,$(LIB_O))
	rm -f $$@
	$(AR65) a $$@ $$^

$(BUILD)/$(1).bin: $(BUILD)/crt0_apple2.o $(BUILD)/$(1)/$(1).o $(BUILD)/$(1)/hgrc.lib src/demo_c.cfg
	$(CL65) -t none -C src/demo_c.cfg -m $(BUILD)/$(1).map -o $$@ \
	    $(BUILD)/crt0_apple2.o $(BUILD)/$(1)/$(1).o $(BUILD)/$(1)/hgrc.lib
	@echo "$(1): $$$$(wc -c < $$@) bytes at $(LOAD)"
endef
$(foreach d,$(C_DEMOS),$(eval $(call c_demo,$(d))))

# --- assembly demos ----------------------------------------------------------
$(BUILD)/%.o: src/%.s $(wildcard $(APPLE2)/*.inc $(APPLE2)/*.asm $(HGR)/*.inc $(HGR)/*.asm)
	@mkdir -p $(BUILD)
	$(CA65) -t none -I $(APPLE2) -I $(HGR) -l $(BUILD)/$*.lst -o $@ $<

$(addprefix $(BUILD)/,$(ASM_DEMOS:=.bin)): $(BUILD)/%.bin: $(BUILD)/%.o $(DEV)/cc65/apple2_hgr.cfg
	$(LD65) -C $(DEV)/cc65/apple2_hgr.cfg -m $(BUILD)/$*.map -o $@ $<
	@echo "$*: $$(wc -c < $@) bytes at $(LOAD)"

# --- disk --------------------------------------------------------------------
BINS := $(addprefix $(BUILD)/,$(C_DEMOS:=.bin) $(ASM_DEMOS:=.bin))

$(DISK): $(BINS) src/hello.bas $(DEV)/tools/dos33.py $(SYSTEM)
	@mkdir -p $(DIST)
	$(PYTHON) $(DEV)/tools/dos33.py --master $(SYSTEM) --out $@ \
	    --bas HELLO=src/hello.bas \
	    --bin BOUNCES=$(BUILD)/bounces.bin@$(LOAD) \
	    --bin ANIMALS=$(BUILD)/animals.bin@$(LOAD) \
	    --bin LIFE=$(BUILD)/life.bin@$(LOAD) \
	    --bin PRESHIFT=$(BUILD)/preshift.bin@$(LOAD) \
	    --bin FONT=$(BUILD)/font.bin@$(LOAD) \
	    --catalog

run: $(DISK)
	$(POM2) --preset ii+ $(DISK)

clean:
	rm -rf $(BUILD) $(DIST)

.PHONY: all run clean
