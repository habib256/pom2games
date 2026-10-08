# Set MOUSE to dev/lib/mouse. Main ROM/RAM/ZP; AppleMouse polling, no IRQ.
MOUSE_SRCS := $(MOUSE)/mouse.s
MOUSE_INCS := -I $(MOUSE)
# Optional resident context for legacy ASM callers; driver stays independent.
MOUSE_CONTEXT_SRCS := $(MOUSE)/mouse_context.asm
