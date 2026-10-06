# Set MOUSE to dev/lib/mouse. Main ROM/RAM/ZP; AppleMouse polling, no IRQ.
MOUSE_SRCS := $(MOUSE)/mouse.s
MOUSE_INCS := -I $(MOUSE)
