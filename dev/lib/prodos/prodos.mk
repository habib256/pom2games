# Set PRODOS to dev/lib/prodos. Use crt0_prodos.s and its linker config.
PRODOS_SRCS := $(PRODOS)/mli.s $(PRODOS)/video.s
PRODOS_INCS := -I $(PRODOS)
