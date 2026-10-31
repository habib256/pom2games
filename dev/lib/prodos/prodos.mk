# Set PRODOS to dev/lib/prodos. Use crt0_prodos.s and its linker config.
PRODOS_SRCS := $(PRODOS)/mli.s $(PRODOS)/video.s $(PRODOS)/mli_cmd.s
PRODOS_INCS := -I $(PRODOS)
# Whole-file load / save for C (prodos.h); assembly includes file.asm.
PRODOS_FILE_SRCS := $(PRODOS)/file.s
PRODOS_FILE_DEPS := $(PRODOS)/file.asm
# The same plus prodos_load_aux() (a file into aux memory): instead of
# PRODOS_FILE_SRCS, with $(APPLE2C_AUX_SRCS) for aux_store.
PRODOS_FILE_AUX_SRCS := $(PRODOS)/file_aux.s
PRODOS_FILE_AUX_DEPS := $(PRODOS)/file.asm $(PRODOS)/file.s
# Either of the two plus prodos_load_at() (a record at an offset), instead.
PRODOS_FILE_AT_SRCS := $(PRODOS)/file_at.s
PRODOS_FILE_AT_DEPS := $(PRODOS_FILE_DEPS) $(PRODOS)/file.s
PRODOS_FILE_AUX_AT_SRCS := $(PRODOS)/file_aux_at.s
PRODOS_FILE_AUX_AT_DEPS := $(PRODOS_FILE_AUX_DEPS) $(PRODOS)/file_aux.s

# The .SYSTEM shim: src/boot.s defines SYSBOOT_FILE / SYSBOOT_TITLE and
# includes sysboot.s (see its header). A SYS image in one piece at $2000
# links with PRODOS_SYS_CFG.
PRODOS_SYSBOOT_CFG  := $(PRODOS)/../../cc65/prodos_sysboot.cfg
PRODOS_SYS_CFG      := $(PRODOS)/../../cc65/prodos_sys.cfg
PRODOS_SYSBOOT_DEPS := $(PRODOS)/sysboot.s $(PRODOS_SYSBOOT_CFG)
# The SYS relocator macros (sysreloc.inc), for src/startup.s: assemble it
# with -I $(PRODOS) and make the SYS file depend on PRODOS_SYSRELOC_DEPS.
PRODOS_SYSRELOC_DEPS := $(PRODOS)/sysreloc.inc

# The .SYSTEM shim of a game, from its src/boot.s: `make build/NAME.SYSTEM`.
$(BUILD)/%.SYSTEM: src/boot.s $(PRODOS_SYSBOOT_DEPS)
	@mkdir -p $(@D)
	$(CA65) -I $(PRODOS) -o $(BUILD)/boot.o src/boot.s
	$(LD65) -C $(PRODOS_SYSBOOT_CFG) -o $@ $(BUILD)/boot.o

# A bootable ProDOS volume, PRODOS first, without a stage directory:
#   $(DISK): <its files> $(PRODOS_VOLUME_DEPS)
#   	$(call prodos_volume,$@,VOLNAME,$(BUILD)/X.SYS=X.SYS#FF2000 ...[,BLOCKS])
# Each SRC=NAME#TTAAAA puts host file SRC on the volume as NAME, type TT,
# auxtype AAAA (build_volume.py --file): same image as a stage holding
# those names (alphabetical entries, fixed date). BLOCKS defaults to 280.
PRODOS_TOOLS := $(PRODOS)/../../tools/prodos
PRODOS_VOLUME_DEPS := $(PRODOS_TOOLS)/PRODOS $(PRODOS_TOOLS)/boot.bin $(PRODOS_TOOLS)/build_volume.py
prodos_volume = $(PYTHON) $(PRODOS_TOOLS)/build_volume.py $(1) --volume $(2) \
	--boot $(PRODOS_TOOLS)/boot.bin --blocks $(or $(4),280) \
	--file $(PRODOS_TOOLS)/PRODOS=PRODOS\#FF0000 $(foreach f,$(3),--file $(f))
