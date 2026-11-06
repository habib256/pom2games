"""Private real-client checks for test_verlet_clamp.py --bench."""
import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import re
import statistics
import subprocess
import sys
from test_hgr import DEV, a2test
from test_verlet_integrate_all import game_budgets
from verlet import harness

ROOT = DEV.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def work_report(measured):
    return {phase: dict(cases=len(costs), median=statistics.median(costs),
                        maximum=max(costs), cycles=costs)
            for phase, costs in measured.items()}


def compile_example(work, include, name):
    game = DEV / 'examples' / name
    target = work / name
    target.mkdir()
    includes = [include, game / 'src', *(DEV / 'lib' / part
                for part in ('apple2', 'hgr', 'font', 'math', 'physics'))]
    arguments = [str(value) for directory in includes for value in ('-I', directory)]
    obj, binary, labels = (target / (name+suffix) for suffix in ('.o', '.bin', '.lbl'))
    subprocess.run(['ca65', '-t', 'none', '-g', *arguments, '-o', str(obj),
                    str(game / 'src' / (name+'.s'))], check=True)
    subprocess.run(['ld65', '-C', str(DEV / 'cc65/apple2_hgr.cfg'),
                    '-m', str(target / (name+'.map')), '-Ln', str(labels),
                    '-o', str(binary), str(obj)], check=True)
    disk = target / (name.upper()+'.dsk')
    subprocess.run([sys.executable, str(DEV / 'tools/dos33.py'), '--master',
                    str(DEV / 'tools/dos33_system.bin'), '--out', str(disk),
                    '--bas', f'HELLO={game}/src/hello.bas',
                    '--bin', f'{name.upper()}={binary}@0x6000'], check=True, capture_output=True)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        model = load('clamp_model_'+name, game / 'tests' / ('test_'+name+'.py'))
        model.check_model()
        test = load('clamp_disk_'+name, game / 'tests' / ('test_'+name+'_disk.py'))
        test.DISK, test.LBL = disk, labels
        captured, original = {}, test.check_cycles

        def capture(label, by_state):
            captured.update(by_state)
            return original(label, by_state)

        test.check_cycles = capture
        measured = test.main() or captured
    print(stream.getvalue(), end='', flush=True)
    return dict(cpu='NMOS6502', binary_bytes=binary.stat().st_size,
                binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                work=work_report(measured))


def dirtbike(work, include):
    game = ROOT / 'dirtbike'
    target = work / 'dirtbike'
    target.mkdir()
    # Only the MENUOVL output filename changes; addresses and segment layout
    # are the actual game's, including copied text-page kernels and MAIN fill.
    cfg = target / 'dirtbike.cfg'
    cfg.write_text((game / 'src/dirtbike.cfg').read_text().replace(
        '"build/menu.bin"', f'"{target}/menu.bin"'))
    includes = [include, game / 'src', *(DEV / 'lib' / part
                for part in ('apple2', 'hgr', 'font', 'math', 'physics')), game / 'build/tracks']
    arguments = [str(value) for directory in includes for value in ('-I', directory)]
    obj, binary, labels = (target / ('dirtbike'+suffix) for suffix in ('.o', '.bin', '.lbl'))
    subprocess.run(['ca65', '-t', 'none', '-g', *arguments, '-o', str(obj),
                    str(game / 'src/dirtbike.s')], check=True, cwd=game)
    subprocess.run(['ld65', '-C', str(cfg), '-m', str(target / 'dirtbike.map'),
                    '-Ln', str(labels), '-o', str(binary), str(obj)], check=True, cwd=game)
    subprocess.run([sys.executable, str(game / 'tools/titlefile.py'), str(target / 'TITLE.bin'),
                    str(game / 'build/tune.bin'), str(game / 'build/pages.bin'),
                    str(target / 'menu.bin'), str(game / 'build/title.lz4')],
                   check=True, capture_output=True)
    disk = target / 'DIRTBIKE.dsk'
    names = [f'T{index:02}' for index in range(1, 31)]
    command = [sys.executable, str(DEV / 'tools/dos33.py'), '--master',
               str(DEV / 'tools/dos33_system.bin'), '--out', str(disk),
               '--bas', f'HELLO={game}/src/hello.bas', '--bin', f'DIRTBIKE={binary}@0x6000',
               '--bin', f'TITLE={target}/TITLE.bin@0x9600',
               '--bin', f'DIRTHOF={game}/build/hof.bin@0xB500']
    for name in names:
        command += ['--bin', f'{name}={game}/build/tracks/{name}.bin@0x9600']
    subprocess.run(command, check=True, capture_output=True)
    subprocess.run([sys.executable, str(DEV / 'tools/dos33patch.py'), str(disk), 'DIRTBIKE',
                    str(labels), '--tslist', 'trackdir_t', 'trackdir_s', *names,
                    '--tslist', 'titledir_t', 'titledir_s', 'TITLE',
                    '--sectors', 'hof_t', 'hof_s', 'DIRTHOF'], check=True, capture_output=True)
    lab = a2test.labels(labels)
    model = load('clamp_dirtbike_physics', game / 'tests/test_physics.py')
    heights, _ = model.tracks.build(1)
    bike = model.physics.Bike(heights)
    steps = ['wait:1000', 'key: ', 'wait:60', 'key:\r', lab.until('new_race', 900),
             lab.until('main_loop', 900)]
    expected = []
    for count, throttle, brake, lean in model.SCRIPT:
        steps += [lab.poke('in_throttle', throttle), lab.poke('in_brake', brake),
                  lab.poke('in_lean', lean&255)]
        for _ in range(count):
            bike.tick(throttle, bool(brake), lean)
            expected.append(model.state(bike))
            steps += [f'call:{lab["phys_tick"]:04X}:20', lab.peek('pt_xf', len(expected[-1]))]
    result = a2test.run(disk, steps, timeout=240)
    assert result.dumps == expected, 'actual Dirtbike state differs from model'
    # call: includes the RTS but injects its return address without a JSR;
    # include the real caller's six JSR cycles in the reported cost.
    cycles = [int(value)+6 for value in re.findall(
        r'call [0-9A-F]+ cycles=\d+ elapsed=(\d+)', result.out)]
    assert len(cycles) == len(expected)
    fake = target / 'game'
    (fake / 'build').mkdir(parents=True)
    (fake / 'build/dirtbike.lbl').write_bytes(labels.read_bytes())
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        for name in ('test_input', 'test_tracks'):
            test = load('clamp_dirtbike_'+name, game / 'tests' / (name+'.py'))
            test.GAME, test.DISK = fake, disk
            arguments = sys.argv
            try:
                # test_tracks accepts track numbers on its own CLI; keep the
                # enclosing clamp test's --reference/--bench flags separate.
                sys.argv = [str(game / 'tests' / (name+'.py'))]
                test.main()
            finally:
                sys.argv = arguments
    print(stream.getvalue(), end='', flush=True)
    mapping = (target / 'dirtbike.map').read_text()
    code = re.search(r'^CODE\s+[0-9A-F]+\s+[0-9A-F]+\s+([0-9A-F]+)', mapping, re.M)
    return dict(cpu='NMOS6502', binary_bytes=binary.stat().st_size,
                binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                code_bytes=int(code[1], 16), menu_bytes=(target / 'menu.bin').stat().st_size,
                scope='actual-game phys_tick JSR/RTS after track load; 645 scripted ticks',
                snapshot_sha256=hashlib.sha256(result.data).hexdigest(),
                work=work_report({'script': cycles}))


def check_clients(work, include):
    report = game_budgets(work, include)
    original = harness.INCLUDES[:]
    harness.INCLUDES[:] = [include, *original]
    try:
        for name in ('lander', 'rope', 'halfpipe'):
            report[name] = compile_example(work, include, name)
        report['dirtbike'] = dirtbike(work, include)
    finally:
        harness.INCLUDES[:] = original
    return report
