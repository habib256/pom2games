# Set PRODOS to dev/lib/prodos. Use crt0_prodos.s and its linker config.
PRODOS_SRCS := $(PRODOS)/mli.s $(PRODOS)/video.c
PRODOS_INCS := -I $(PRODOS)
