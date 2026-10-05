# pom2games — build every disk
#
#   make            -> dist/*.dsk (every disk lands in this one folder)
#   make test       -> build, test HGR, then play MICRO-SOKOBAN in a2run
#   make check      -> rebuild every disk from scratch and fail if one differs
#                      from the committed dist/*.dsk (sources and disks agree)
#   make clean      -> remove the build/ folders (the disks stay)
#   make distclean  -> remove the build/ folders and dist/*.dsk
#
# Each folder builds on its own too: make -C chess [run], still into ./dist.

DIRS := micro-sokoban chess maze3d snake logo demos dev/examples/hello dev/examples/hgr dev/examples/dhgr

all:
	@for d in $(DIRS); do $(MAKE) -C $$d || exit 1; done

test: all test-hgr test-frame test-hgr-example test-assets bench-check
	$(MAKE) -C micro-sokoban test

test-hgr:
	python3 dev/tests/test_hgr.py
	python3 dev/tests/test_sprengine.py

test-frame:
	python3 dev/tests/test_frame.py

test-hgr-example:
	python3 dev/tests/test_hgr_example.py

test-dhgr:
	$(MAKE) -C dev/examples/dhgr test
	python3 dev/tests/test_dhgr_extended.py
	python3 dev/tests/test_frame.py --iie
	python3 dev/tests/test_hgr_example.py --iie

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

.PHONY: all test test-hgr test-frame test-hgr-example test-dhgr check clean distclean

test-assets:
	python3 dev/tests/test_assets.py

bench:
	python3 dev/bench/run.py

bench-dhgr:
	python3 dev/bench/run.py --dhgr

bench-check:
	python3 dev/bench/run.py --check

.PHONY: test-assets bench bench-dhgr bench-check
