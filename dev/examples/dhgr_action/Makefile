# VERHILLE Arnaud — GPL-3.0. DHGR ACTION: an action demo on the DHGR
# compositor, two pages (DHGR_SPR_DOUBLE), ProDOS 8, //e enhanced 128K or
# //c. Built into build/ (not dist/): build/DHGRACTION.po.
DEV ?= ../..
APPLE2_PRESET := iie
include $(DEV)/cc65/apple2.mk
include $(HGRC)/hgrc.mk
include $(APPLE2C)/apple2c.mk
PRODOS := $(DEV)/lib/prodos
MOUSE := $(DEV)/lib/mouse
include $(PRODOS)/prodos.mk
include $(MOUSE)/mouse.mk
DISK := $(BUILD)/DHGRACTION.po
SRCS := src/action.c src/hooks.s
# The compositor's two-page option: the same define for every member.
SPR_DEFS := -D DHGR_SPR_DOUBLE=1
LIB_SRCS := $(sort $(HGRC_DHGR_SRCS) $(HGRC_DHGR_SMALL_TEXT_SRCS) $(HGRC_DHGR_SPR_SRCS)) \
            $(APPLE2C_SRCS) $(APPLE2C_FRAME_SRCS) $(APPLE2C_VBL_SRCS) $(APPLE2C_GAME_SRCS) \
            $(PRODOS_SRCS) $(MOUSE_SRCS)
OBJS := $(BUILD)/crt0_prodos.o $(addprefix $(BUILD)/,$(notdir $(SRCS:.c=.o)))
OBJS := $(OBJS:.s=.o)
LIB_OBJS := $(addprefix $(BUILD)/,$(notdir $(LIB_SRCS:.c=.o)))
LIB_OBJS := $(LIB_OBJS:.s=.o)
GAME_LIB := $(BUILD)/platform.lib
CFLAGS := -t none -Oirs $(HGRC_INCS) $(APPLE2C_INCS) $(PRODOS_INCS) $(MOUSE_INCS)
vpath %.c src $(HGRC) $(APPLE2C) $(GFX)
vpath %.s src $(DEV)/cc65 $(HGRC) $(APPLE2C) $(PRODOS) $(MOUSE)

all: $(DISK)

$(BUILD)/%.o: %.c $(HGRC_HEADERS) $(wildcard $(PRODOS)/*.h $(MOUSE)/*.h)
	@mkdir -p $(@D)
	$(CL65) $(CFLAGS) -c -o $@ $<
$(BUILD)/%.o: %.s $(HGRC_ASM_DEPS)
	@mkdir -p $(@D)
	$(CA65) -t none $(SPR_DEFS) -I $(HGRC) -I $(APPLE2) -I $(PRODOS) -o $@ $<
$(GAME_LIB): $(LIB_OBJS) Makefile
	$(PYTHON) -c 'from pathlib import Path; Path("$@").unlink(missing_ok=True)'
	$(AR65) a $@ $(LIB_OBJS)
$(BUILD)/action.bin: $(OBJS) $(GAME_LIB) Makefile $(DEV)/cc65/apple2_dhgr_prodos_c.cfg
	$(CL65) -t none -C $(DEV)/cc65/apple2_dhgr_prodos_c.cfg -m $(BUILD)/action.map -Ln $(BUILD)/action.lbl -o $@ $(OBJS) $(GAME_LIB)
$(BUILD)/ACTION.SYS: $(BUILD)/action.bin src/startup.s $(PRODOS_SYS_CFG) $(PRODOS_SYSRELOC_DEPS)
	$(CA65) --bin-include-dir $(BUILD) -I $(PRODOS) -o $(BUILD)/startup.o src/startup.s
	$(LD65) -C $(PRODOS_SYS_CFG) -o $@ $(BUILD)/startup.o
$(DISK): $(BUILD)/ACTION.SYS $(BUILD)/ACTION.SYSTEM $(PRODOS_VOLUME_DEPS)
	$(call prodos_volume,$@,DHGR.ACTION,$(BUILD)/ACTION.SYSTEM=ACTION.SYSTEM#FF2000 \
		$(BUILD)/ACTION.SYS=ACTION.SYS#FF2000)

# //e and //c (a2shot): boot, frames against the model, write-once per page.
test: all
	$(PYTHON) $(DEV)/tests/test_dhgr_action.py

.PHONY: test
