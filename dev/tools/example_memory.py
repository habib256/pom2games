#!/usr/bin/env python3
"""Report linked example segments separately from video and reserved C stack."""
import argparse
import json
from pathlib import Path
import re


def report(directory):
    result = {}
    for name, video in (('hgr-single',8192), ('hgr-double',16384), ('dhgr-prodos',32768)):
        text = (directory / (name+'.map')).read_text()
        section = text.split('Segment list:')[1].split('Exports list')[0]
        sizes = {m[1]: int(m[2],16) for m in re.finditer(
            r'^([A-Z][A-Z0-9_]*)\s+[0-9A-F]+\s+[0-9A-F]+\s+([0-9A-F]+)',section,re.M)}
        symbols = {m[2]: int(m[1],16) for m in re.finditer(
            r'^al ([0-9A-Fa-f]+) \.(\w+)$', (directory/(name+'.lbl')).read_text(),re.M)}
        result[name] = dict(binary_bytes=(directory/(name+'.bin')).stat().st_size,
                            segments=sizes,
                            code_bytes=sum(sizes.get(k,0) for k in ('STARTUP','CODE','LOWCODE','INIT','ONCE')),
                            init_code_bytes=sum(sizes.get(k,0) for k in ('LOWCODE','INIT','ONCE')),
                            linked_main_bytes=sum(v for k,v in sizes.items() if k!='ZEROPAGE'),
                            zp_bytes=sizes.get('ZEROPAGE',0),
                            c_stack_reserved=symbols['__STACKSIZE__'],
                            video_bytes=video)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('directory',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    args = ap.parse_args()
    result = report(args.directory)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    for name,m in result.items():
        print(f'{name}: binary={m["binary_bytes"]}, linked main={m["linked_main_bytes"]}, '
              f'ZP={m["zp_bytes"]}, C stack reserved={m["c_stack_reserved"]}, video={m["video_bytes"]}')


if __name__=='__main__':
    main()
