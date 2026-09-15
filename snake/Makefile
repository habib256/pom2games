# Snake — Apple II+ / DOS 3.3 build (cc65 C)
#
#   make            -> dist/SNAKE.dsk (bootable 5.25" DOS 3.3 image)
#   make run        -> boot it in POM2 as an Apple II+
#   make clean
#
# Needs cc65 (cl65/ca65) and python3 only: the shared ../dev tree has the rest,
# DOS 3.3 system tracks included. `make run` uses the installed POM2 app.

CL65    ?= cl65
CA65    ?= ca65
PYTHON  ?= python3
DEV     ?= ../dev
POM2    ?= /Applications/POM2.app/Contents/MacOS/POM2
SYSTEM  ?= $(DEV)/tools/dos33_system.bin

APPLE2C := $(DEV)/lib/apple2c
GEN2C   := src/gen2c
CFG     := $(DEV)/cc65/apple2_hgr_c.cfg
BUILD   := build
DIST    := dist
DISK    := $(DIST)/SNAKE.dsk
BIN     := $(BUILD)/snake.bin
LOAD    := 0x6000

CFLAGS  := -t none -Oirs -I $(GEN2C) -I $(APPLE2C)
AFLAGS  := -t none -I $(DEV)/lib/apple2 -I $(GEN2C)

# crt0_apple2 FIRST: it provides __STARTUP__ / _exit instead of none.lib's crt0.
C_SRCS  := snake.c gen2_init.c gen2_rect.c gen2_text.c gen2_text_num.c \
           gfx_num_hex.c apple2io.c
S_SRCS  := crt0_apple2.s gen2_blit.s apple2io_asm.s
OBJS    := $(BUILD)/crt0_apple2.o $(addprefix $(BUILD)/,$(filter-out crt0_apple2.o,$(S_SRCS:.s=.o)) $(C_SRCS:.c=.o))

vpath %.c src $(GEN2C) $(APPLE2C)
vpath %.s $(DEV)/cc65 $(GEN2C) $(APPLE2C)

all: $(DISK)

$(BUILD)/%.o: %.c $(GEN2C)/gen2.h $(GEN2C)/gen2_internal.h $(GEN2C)/gen2_bbfont.inc $(APPLE2C)/apple2io.h
	@mkdir -p $(BUILD)
	$(CL65) $(CFLAGS) -c -o $@ $<

$(BUILD)/%.o: %.s $(wildcard $(DEV)/lib/apple2/*.inc $(DEV)/lib/apple2/*.asm)
	@mkdir -p $(BUILD)
	$(CA65) $(AFLAGS) -o $@ $<

$(BIN): $(OBJS) $(CFG)
	$(CL65) -t none -C $(CFG) -m $(BUILD)/snake.map -o $@ $(OBJS)
	@echo "binary: $$(wc -c < $@) bytes at $(LOAD)"

$(DISK): $(BIN) src/hello.bas $(DEV)/tools/dos33.py $(SYSTEM)
	@mkdir -p $(DIST)
	$(PYTHON) $(DEV)/tools/dos33.py --master $(SYSTEM) --out $@ \
	    --bas HELLO=src/hello.bas \
	    --bin SNAKE=$(BIN)@$(LOAD) \
	    --catalog

run: $(DISK)
	$(POM2) --preset ii+ $(DISK)

clean:
	rm -rf $(BUILD) $(DIST)

.PHONY: all run clean
