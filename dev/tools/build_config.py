#!/usr/bin/env python3
"""Update the archive configuration signature only when its inputs change.

Make passes individually quoted values, including flags and the source list.
Tool identity includes its resolved path, size and modification timestamp.
"""
import json
import argparse
from pathlib import Path
import shlex
import shutil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('values', nargs=7)
    args = parser.parse_args()
    target = Path(args.values[0])
    names = ('HGRC_CFLAGS', 'HGRC_ASMFLAGS', 'CL65', 'CA65', 'AR65',
             'HGRC_ARCHIVE_SRCS')
    config = dict(zip(names, args.values[1:]))
    config['tools'] = {}
    for name in ('CL65', 'CA65', 'AR65'):
        command = shlex.split(config[name])
        executable = shutil.which(command[0]) if command else None
        if executable:
            path = Path(executable).resolve()
            stat = path.stat()
            config['tools'][name] = [str(path), stat.st_size, stat.st_mtime_ns]
    data = json.dumps(config, indent=2, sort_keys=True) + '\n'
    if target.exists() and target.read_text() == data:
        return
    if args.check:
        print('changed')
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    temporary.write_text(data)
    temporary.replace(target)


if __name__ == '__main__':
    main()
