#!/usr/bin/env python3
"""Run independent Python test scripts in parallel (a game's `make test`).

    python3 dev/tools/run_tests.py [-j N] [--python PY] 'tests/a.py' 'tests/b.py --opt' ...

Each argument is one test: a script path and its arguments (split like a
shell would). The tests run N at a time (default: every CPU; each one drives
its own a2shot/a2run process, so they must not share output files). The
output of a test is printed whole when it ends, so logs never interleave;
a summary gives the failures and the slowest tests. The exit status is
non-zero if any test failed. Every test is run even if one fails.

The schedule starts the longest tests first when their previous durations
are known (a JSON cache next to the build, --times FILE): the wall time then
tends to max(longest test, total / N).
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def run_one(python, test):
    start = time.monotonic()
    proc = subprocess.run([python] + shlex.split(test), stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True)
    return test, proc.returncode, proc.stdout, time.monotonic() - start


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('-j', '--jobs', type=int, default=os.cpu_count() or 1)
    ap.add_argument('--python', default=sys.executable)
    ap.add_argument('--times', type=Path, help='JSON cache of the last durations (longest first)')
    ap.add_argument('tests', nargs='+')
    args = ap.parse_args()

    times = {}
    if args.times and args.times.exists():
        try:
            times = json.loads(args.times.read_text())
        except ValueError:
            times = {}
    order = sorted(args.tests, key=lambda t: -times.get(t, 0.0))

    start = time.monotonic()
    failed, took = [], {}
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        for future in as_completed([pool.submit(run_one, args.python, t) for t in order]):
            test, rc, out, seconds = future.result()
            took[test] = round(seconds, 1)
            sys.stdout.write(f'--- {test}  ({seconds:.1f} s){"  FAILED" if rc else ""}\n{out}')
            sys.stdout.flush()
            if rc:
                failed.append(test)

    if args.times:
        args.times.parent.mkdir(parents=True, exist_ok=True)
        args.times.write_text(json.dumps({**times, **took}, indent=1, sort_keys=True) + '\n')
    slow = sorted(took.items(), key=lambda kv: -kv[1])[:3]
    print(f'{len(args.tests)} tests, {args.jobs} at a time, {time.monotonic() - start:.0f} s'
          f' (slowest: {", ".join(f"{t} {s} s" for t, s in slow)})')
    if failed:
        print('FAILED:\n  ' + '\n  '.join(failed))
        sys.exit(1)
    print('OK')


if __name__ == '__main__':
    main()
