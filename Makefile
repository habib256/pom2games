# pom2games — build every disk
#
#   make            -> dist/*.dsk (every disk lands in this one folder)
#   make test       -> build, then play MICRO-SOKOBAN levels in a2run (headless)
#   make check      -> rebuild every disk from scratch and fail if one differs
#                      from the committed dist/*.dsk (sources and disks agree)
#   make clean      -> remove the build/ folders (the disks stay)
#   make distclean  -> remove the build/ folders and dist/*.dsk
#
# Each folder builds on its own too: make -C chess [run], still into ./dist.

DIRS := micro-sokoban chess maze3d snake logo demos dev/examples/hello

all:
	@for d in $(DIRS); do $(MAKE) -C $$d || exit 1; done

test: all
	$(MAKE) -C micro-sokoban test

check: distclean
	$(MAKE) all
	@git diff --stat --exit-code -- dist || \
	    { echo "dist/*.dsk differ from a fresh build: run make and commit dist/"; exit 1; }
	@test -z "$$(git ls-files --others --exclude-standard -- dist)" || \
	    { echo "untracked disks in dist/:"; git ls-files --others --exclude-standard -- dist; exit 1; }

clean:
	@for d in $(DIRS); do $(MAKE) -C $$d clean; done

distclean:
	@for d in $(DIRS); do $(MAKE) -C $$d distclean; done

.PHONY: all test check clean distclean
