#!/usr/bin/env python3
"""Audit dev/lib usage and incremental dependencies of every shipped program.

Uses real ca65/cc65 dependency files and the expanded make build graph. Compile
outputs are temporary; game objects and disks are not modified. Archive source
families count as build resources, including members the linker may not extract.
The minimal examples supplement the top-level DIRS list. Run after make all and
make -C dev/examples/minimal so generated assets and translated sources exist.
"""
from pathlib import Path
import argparse,json,re,shlex,subprocess,tempfile
R=Path(__file__).resolve().parents[2];LIB=R/'dev/lib'
def call(args,cwd):
    return subprocess.run(args,cwd=cwd,text=True,capture_output=True)
def path(s,cwd):return (cwd/s).resolve()
def shared(p):return p.is_relative_to(LIB)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--json',type=Path,help='write the detailed audit to this file')
options=parser.parse_args()
db=call(['make','-qp'],R).stdout
projects=re.search(r'^DIRS := (.+)$',db,re.M).group(1).split()+['dev/examples/minimal']
report=[]
with tempfile.TemporaryDirectory(prefix='lib-audit-') as tmp:
    for project in projects:
        cwd=R/project
        query=call(['make','-Bpn'],cwd)
        if query.returncode not in (0,1):raise RuntimeError(query.stderr)
        graph={}
        for line in query.stdout.splitlines():
            if line and not line.startswith(('#','\t',' ')) and ': ' in line:
                target,deps=line.split(': ',1)
                if any(c in target for c in ('=','%')):continue
                graph.setdefault(path(target,cwd),set()).update(path(s,cwd) for s in deps.split() if s!='|')
        plan=query
        if plan.returncode:raise RuntimeError(plan.stderr)
        units=[];seen=set()
        for line in plan.stdout.replace('\\\n',' ').splitlines():
            try:args=shlex.split(line)
            except ValueError:continue
            if not args or Path(args[0]).name not in ('ca65','cl65') or '-o' not in args:continue
            sources=[p for s in args[1:] if s.endswith(('.c','.s','.asm')) and (p:=path(s,cwd)).is_file()]
            if not sources:continue
            src=sources[-1]
            if src.name.endswith('.o.s'):continue
            target=path(args[args.index('-o')+1],cwd)
            if (src,target) in seen:continue
            seen.add((src,target))
            dep=Path(tmp)/'deps.d';out=Path(tmp)/('unit.s' if src.suffix=='.c' else 'unit.o')
            updated=[];i=0
            while i<len(args):
                if args[i] in ('-l','--create-dep'):i+=2;continue
                if args[i]=='-o':updated+=['-o',str(out)];i+=2;continue
                if src.suffix=='.c' and args[i]=='-c':updated+=['-S'];i+=1;continue
                updated.append(args[i]);i+=1
            updated[1:1]=['--create-dep',str(dep)]
            dep.unlink(missing_ok=True)
            compiled=call(updated,cwd)
            if compiled.returncode:raise RuntimeError(f'{project}: {src}\n{compiled.stderr}')
            dependencies={src}
            if dep.exists():
                text=dep.read_text().replace('\\\n',' ')
                for line in text.splitlines():
                    if ':' in line:dependencies.update(path(s,cwd) for s in shlex.split(line.split(':',1)[1]))
            resources={p for p in dependencies if shared(p)}
            actual_target=target
            if target not in graph:
                candidates=[t for t,deps in graph.items() if src in deps]
                candidates.sort(key=lambda t:(t.suffix!='.bin',len(str(t))))
                if candidates:actual_target=candidates[0]
            closure=set();queue=[actual_target]
            while queue:
                node=queue.pop()
                if node in closure:continue
                closure.add(node);queue.extend(graph.get(node,()))
            units.append({'source':str(src.relative_to(R)),'target':str(actual_target.relative_to(cwd)),
                          'resources':sorted(str(p.relative_to(R)) for p in resources),
                          'missing':sorted(str(p.relative_to(R)) for p in resources-closure)})
        used=sorted({p for u in units for p in u['resources']})
        missing=[u for u in units if u['missing']]
        print(f'{project}: {len(units)} compilation units, {len(used)} shared source/header resources, {len(missing)} missing build dependencies.',flush=True)
        for unit in missing: print(' ',unit['source'],unit['target'],unit['missing'],flush=True)
        report.append({'project':project,'resources':used,'units':units})
if options.json:
    options.json.write_text(json.dumps(report,indent=2)+'\n')
failed=any(not p['resources'] or any(u['missing'] for u in p['units']) for p in report)
raise SystemExit(1 if failed else 0)
