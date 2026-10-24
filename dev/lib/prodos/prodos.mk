# Set PRODOS to dev/lib/prodos. Use crt0_prodos.s and its linker config.
PRODOS_SRCS := $(PRODOS)/mli.s $(PRODOS)/video.s
PRODOS_INCS := -I $(PRODOS)
# Whole-file load / save for C (prodos.h); assembly includes file.asm.
PRODOS_FILE_SRCS := $(PRODOS)/file.s

# The .SYSTEM shim: src/boot.s defines SYSBOOT_FILE / SYSBOOT_TITLE and
# includes sysboot.s (see its header). A SYS image in one piece at $2000
# links with PRODOS_SYS_CFG.
PRODOS_SYSBOOT_CFG  := $(PRODOS)/../../cc65/prodos_sysboot.cfg
PRODOS_SYS_CFG      := $(PRODOS)/../../cc65/prodos_sys.cfg
PRODOS_SYSBOOT_DEPS := $(PRODOS)/sysboot.s $(PRODOS_SYSBOOT_CFG)
