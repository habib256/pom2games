# Set MOUSE to dev/lib/mouse. Main ROM/RAM/ZP; AppleMouse polling, no IRQ.
MOUSE_SRCS := $(MOUSE)/mouse.s
MOUSE_INCS := -I $(MOUSE)
# Optional resident context for legacy ASM callers; driver stays independent.
MOUSE_CONTEXT_SRCS := $(MOUSE)/mouse_context.asm
# `make run-iic`: POM2 as a //c, its built-in mouse in slot 4 (after
# apple2.mk, which runs the //e or II+ preset). A game may still define its
# own run-iic. Could move to apple2.mk next to `run`.
APPLE2_RUN_IIC_FLAGS ?= --slot 4=iicmouse
run-iic: all
	$(POM2) --preset iic $(APPLE2_RUN_IIC_FLAGS) $(DISK)
.PHONY: run-iic
