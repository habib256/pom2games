#!/usr/bin/env python3
"""Run the fast tests of the programs a change affects (make test-changed).

    python3 dev/tools/test_changed.py [--base REF] [--long] [--sources-only]
                                      [--dry-run] PROGRAM...

The working tree (tracked files, staged or not, plus untracked files that
.gitignore keeps) is compared with BASE (default: origin/main if it exists,
else HEAD). A program is affected when

  * its folder holds a changed file ("sources changed"; *.md and docs/
    are ignored), or
  * its disk image, built from scratch from the working tree, differs from
    the same image built from scratch from BASE ("binary changed": a change
    in dev/lib, dev/cc65, the root Makefile... that reaches its bytes).

Both images are built in temporary copies under the system temp dir, never
in dist/ (dist/ images may hold the player's saves, e.g. PINBALL.dsk). The
hashes of BASE are cached per commit, so only the working tree is rebuilt on
the next run. A change to the test harness (dev/tools/a2test.py, a2run,
a2shot) affects every program. A change anywhere under dev/ also runs the
quick dev/ checks (make test-dev: libraries, tools, bench-check).

Each affected program then runs `make -C PROGRAM test` (with --long,
`test-long` as well). Every program is run even if one fails; the summary
lists the failures and the exit status is non-zero.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Ignored local inputs that some builds read (copyrighted originals).
LOCAL_INPUTS = ['wilderness/original', 'neowilderness/original', 'physics/orig']
# Changes here invalidate every program's tests, whatever their binaries.
HARNESS = ['dev/tools/a2test.py', 'dev/tools/a2run/', 'dev/tools/a2shot/']
CACHE = Path(tempfile.gettempdir()) / 'pom2games-test-changed'


def git(*args, cwd=ROOT):
    return subprocess.run(['git', *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout


def resolve_base(ref):
    if ref is None:
        ok = subprocess.run(['git', 'rev-parse', '--verify', '-q', 'origin/main'],
                            cwd=ROOT, capture_output=True).returncode == 0
        ref = 'origin/main' if ok else 'HEAD'
    return ref, git('rev-parse', '--verify', ref + '^{commit}').strip()


def changed_files(sha):
    files = set(git('diff', '--name-only', '--no-renames', sha).split('\n'))
    files |= set(git('ls-files', '--others', '--exclude-standard').split('\n'))
    files.discard('')
    return sorted(files)


def disk_of(tree, prog):
    """The DISK variable of PROGRAM's Makefile, relative to the tree root."""
    out = subprocess.run(['make', '-s', '-C', prog, '-pn', 'all'], cwd=tree,
                         capture_output=True, text=True).stdout
    for line in out.split('\n'):
        if line.startswith(('DISK := ', 'DISK = ')):
            disk = line.split('=', 1)[1].strip()
            return os.path.normpath(os.path.join(prog, disk))
    return None


def build_hashes(tree, programs, log):
    """make distclean-free fresh build of TREE; {program: sha256 of its disk}."""
    for img in (tree / 'dist').glob('*'):
        if img.suffix in ('.dsk', '.po'):
            img.unlink()          # rebuilt from the sources, not trusted
    with open(log, 'w') as out:
        rc = subprocess.run(['make', 'all'], cwd=tree, stdout=out,
                            stderr=subprocess.STDOUT).returncode
    hashes = {}
    for prog in programs:
        disk = disk_of(tree, prog)
        path = tree / disk if disk else None
        hashes[prog] = (hashlib.sha256(path.read_bytes()).hexdigest()
                        if path and path.exists() else None)
    return rc, hashes


def link_local_inputs(tree):
    for rel in LOCAL_INPUTS:
        src = ROOT / rel
        if src.exists() and not (tree / rel).exists():
            (tree / rel).parent.mkdir(parents=True, exist_ok=True)
            (tree / rel).symlink_to(src)


def snapshot_worktree(dest):
    """Copy the working tree's tracked and untracked (not ignored) files."""
    names = git('ls-files', '-z', '--cached', '--others', '--exclude-standard')
    for name in sorted(set(names.split('\0')) - {''}):
        src = ROOT / name
        if not os.path.lexists(src) or src.is_dir() and not src.is_symlink():
            continue
        dst = dest / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            dst.symlink_to(os.readlink(src))
        else:
            shutil.copy2(src, dst)


def base_hashes(ref, sha, programs, tmp):
    cache = CACHE / f'{sha}.json'
    try:
        data = json.loads(cache.read_text())
        if all(p in data for p in programs):
            return data, 'cached'
    except (OSError, ValueError):
        pass
    tree = tmp / 'base'
    git('worktree', 'add', '--detach', '-q', str(tree), sha)
    try:
        link_local_inputs(tree)
        rc, data = build_hashes(tree, programs, tmp / 'base-build.log')
    finally:
        git('worktree', 'remove', '--force', str(tree))
    if rc:
        tail = (tmp / 'base-build.log').read_text()[-1500:]
        print(f'{tail}\ntest-changed: {ref} does not build; comparing sources only')
        return None, 'failed'
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data))
    return data, 'built'


def work_hashes(programs, tmp):
    tree = tmp / 'work'
    snapshot_worktree(tree)
    link_local_inputs(tree)
    log = tmp / 'work-build.log'
    rc, data = build_hashes(tree, programs, log)
    if rc:
        sys.stdout.write(log.read_text()[-3000:])
        raise SystemExit('test-changed: the working tree does not build')
    return data


def under(path, prefix):
    return path == prefix or path.startswith(prefix.rstrip('/') + '/')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('programs', nargs='+')
    ap.add_argument('--base', default=None)
    ap.add_argument('--long', action='store_true', help='also run test-long')
    ap.add_argument('--sources-only', action='store_true',
                    help='skip the binary comparison (no builds)')
    ap.add_argument('--dry-run', action='store_true', help='decide, do not test')
    ap.add_argument('--dev-target', default='test-dev')
    args = ap.parse_args()
    t0 = time.time()
    ref, sha = resolve_base(args.base)
    files = changed_files(sha)
    print(f'test-changed: working tree vs {ref} ({sha[:10]}): {len(files)} changed file(s)')
    for f in files[:30]:
        print(f'    {f}')
    if len(files) > 30:
        print(f'    ... and {len(files) - 30} more')

    docs = [f for f in files if f.endswith('.md') or '/docs/' in f'/{f}']
    if docs:
        print(f'test-changed: {len(docs)} documentation file(s) ignored (*.md, docs/)')
    files = [f for f in files if f not in docs]
    reasons = {}
    harness = [f for f in files if any(under(f, h) for h in HARNESS)]
    for prog in args.programs:
        own = [f for f in files if under(f, prog)]
        if own:
            reasons[prog] = f'sources changed ({len(own)} file(s), e.g. {own[0]})'
        elif harness:
            reasons[prog] = f'test harness changed ({harness[0]})'
    dev = [f for f in files if under(f, 'dev')]

    rest = [p for p in args.programs if p not in reasons]
    compared = {}
    if files and rest and not args.sources_only:
        with tempfile.TemporaryDirectory(prefix='pom2games-test-changed-') as t:
            tmp = Path(t)
            print(f'test-changed: building {ref} and the working tree from scratch'
                  f' in {tmp} to compare disk images...')
            with ThreadPoolExecutor(2) as pool:
                base_job = pool.submit(base_hashes, ref, sha, args.programs, tmp)
                work_job = pool.submit(work_hashes, args.programs, tmp)
                base, how = base_job.result()
                work = work_job.result()
            if base is not None:
                print(f'test-changed: images compared ({ref} build {how},'
                      f' {time.time() - t0:.0f} s)')
                for prog in rest:
                    compared[prog] = work.get(prog) != base.get(prog)
                    if compared[prog]:
                        reasons[prog] = 'binary changed (disk image differs)'

    print('\ntest-changed: decision')
    for prog in args.programs:
        if prog in reasons:
            why = reasons[prog]
        elif args.sources_only or not files:
            why = 'unchanged sources -> skipped'
        elif prog in compared:
            why = 'unchanged (same sources, same disk image) -> skipped'
        else:
            why = 'unchanged sources, image not compared -> skipped'
        print(f'    {prog:14s} {"TEST" if prog in reasons else "skip"}  {why}')
    print(f'    {"dev/":14s} {"TEST" if dev else "skip"}  '
          + (f'dev/ changed ({dev[0]}) -> make {args.dev_target}' if dev
             else 'dev/ unchanged -> skipped'))

    targets = []
    if dev:
        targets.append((args.dev_target, ['make', args.dev_target]))
    for prog in args.programs:
        if prog in reasons:
            targets.append((f'{prog} test', ['make', '-C', prog, 'test']))
            if args.long:
                targets.append((f'{prog} test-long', ['make', '-C', prog, 'test-long']))
    if args.dry_run or not targets:
        print('test-changed: nothing to test' if not targets else
              'test-changed: dry run, would run: ' + ', '.join(t for t, _ in targets))
        return 0

    results = []
    for name, cmd in targets:
        print(f'\n===== {name}', flush=True)
        s = time.time()
        rc = subprocess.run(cmd, cwd=ROOT).returncode
        results.append((name, rc, time.time() - s))
    print('\ntest-changed: summary')
    for name, rc, secs in results:
        print(f'    {"ok  " if rc == 0 else "FAIL"} {name:28s} {secs:6.0f} s')
    print(f'    total {time.time() - t0:.0f} s')
    return 1 if any(rc for _, rc, _ in results) else 0


if __name__ == '__main__':
    sys.exit(main())
