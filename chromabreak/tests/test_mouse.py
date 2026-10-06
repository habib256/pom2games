#!/usr/bin/env python3
"""Optional integration against a built POM2 core, both real-ROM mouse models."""
import argparse
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--pom2-src',type=Path,required=True)
    ap.add_argument('--disk',type=Path,required=True)
    ap.add_argument('--labels',type=Path,required=True)
    ap.add_argument('--build',type=Path,required=True)
    ap.add_argument('--records-only',action='store_true')
    a=ap.parse_args(); src=a.pom2_src.resolve();a.build.mkdir(parents=True,exist_ok=True)
    library=src/'build/libpom2_core_test.a'
    if not library.exists(): raise SystemExit(f'Build POM2 core test library first: {library}')
    libs=['-framework','CoreAudio','-framework','AudioToolbox','-framework','AudioUnit'] if sys.platform=='darwin' else ['-pthread']
    libs+=subprocess.check_output(['pkg-config','--libs','slirp'],text=True).split()+['-lz']
    exe=(a.build/'playtest').resolve()
    subprocess.run(['c++','-std=c++17','-O2','-I',str(src/'src'),'-I',str(src/'include'),
                    '-I',str(src/'build/generated'),str(Path(__file__).with_name('playtest.cpp')),
                    str(library),*libs,'-o',str(exe)],check=True)
    with tempfile.TemporaryDirectory(prefix='chromabreak-mouse-') as tmp:
        disk=Path(tmp)/'GAME.po'
        if a.records_only:
            spec=importlib.util.spec_from_file_location('prodos_read',ROOT/'dev/tools/prodos/read_volume.py')
            reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
            def inspect():
                image=reader.Image(disk.read_bytes())
                entries={e[1:1+(e[0]&15)].decode():e for e in image.entries(2)}
                return image,entries
            def execute(variant,action):
                subprocess.run([str(exe),str(src/'roms'),str(disk),str(a.labels.resolve()),variant,action],check=True)
            shutil.copyfile(a.disk,disk);execute('applewin','records-numbers')
            execute('applewin','records-collisions')
            execute('applewin','records-smalltext')
            for variant in ('applewin','mame','iic16','iic32'):
                shutil.copyfile(a.disk,disk)
                execute(variant,'records-victory')
                execute(variant,'records-save')
                image,entries=inspect(); data=image.read(entries['HIGHSCORES'])
                assert len(data)==38 and data[:6]==b'CBR1\x01\x00'
                assert sum(data[:36])==int.from_bytes(data[36:38],'little')
                assert [int.from_bytes(data[6+i*6:8+i*6],'little') for i in range(5)]==[3200,1800,1500,1240,900]
                execute(variant,'records-load')
            shutil.copyfile(a.disk,disk); before=disk.read_bytes()
            execute('iic32','records-error');assert disk.read_bytes()==before,'write-protected disk altered'
            for missing in (False,True):
                shutil.copyfile(a.disk,disk);image,entries=inspect();entry=entries['HIGHSCORES']
                data=bytearray(image.d);key=int.from_bytes(entry[0x11:0x13],'little')
                if missing:
                    for index in range(1,13):
                        offset=1024+4+index*39
                        if data[offset+1:offset+11]==b'HIGHSCORES':data[offset]=0;break
                    offset=1024+4+0x21
                    count=int.from_bytes(data[offset:offset+2],'little');data[offset:offset+2]=(count-1).to_bytes(2,'little')
                    data[image.header()['bitmap']*512+key//8]|=0x80>>(key%8)
                else:data[key*512]^=0x80
                disk.write_bytes(data);execute('iic32','records-empty')
                execute('iic32','records-save');execute('iic32','records-load')
            print('PASS ProDOS persistence, sort, initials/modes, corruption, missing file and write protection')
            return
        failures=[]
        for variant in ('applewin','mame','iic16','iic32','mame-pal','iic32-pal'):
            for entry in ('click','space-reset'):
                shutil.copyfile(a.disk,disk)
                cmd=[str(exe),str(src/'roms'),str(disk),str(a.labels.resolve()),variant]
                if entry!='click': cmd.append(entry)
                print(f'AppleMouse {variant}, {entry}',flush=True)
                result=subprocess.run(cmd)
                if result.returncode:failures.append(f'{variant}/{entry}')
        if failures:raise SystemExit('FAIL '+', '.join(failures))
if __name__=='__main__': main()
