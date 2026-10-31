#!/usr/bin/env python3
"""CHROMABREAK on the POM2 core facade (tests/playtest_probe.cpp, built as
build/playtest_probe): both real-ROM mouse models, the //c, PAL, and the
ProDOS records (--records-only), the sixty sectors played by a mouse
pilot (--campaign, ~2.5 min a machine)."""
import argparse
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev/tools'))
import a2test
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--probe',type=Path,required=True)
    ap.add_argument('--roms',type=Path,required=True)
    ap.add_argument('--disk',type=Path,required=True)
    ap.add_argument('--labels',type=Path,required=True)
    ap.add_argument('--records-only',action='store_true')
    ap.add_argument('--campaign',action='store_true')
    a=ap.parse_args(); exe=a.probe.resolve(); roms=a.roms.resolve()
    with tempfile.TemporaryDirectory(prefix='chromabreak-mouse-') as tmp:
        disk=Path(tmp)/'GAME.po'
        if a.campaign:
            for variant in ('mame','iic32'):
                shutil.copyfile(a.disk,disk);print(f'Campaign {variant}',flush=True)
                subprocess.run([str(exe),str(roms),str(disk),str(a.labels.resolve()),variant,'records-campaign'],check=True)
            return
        if a.records_only:
            spec=importlib.util.spec_from_file_location('prodos_read',ROOT/'dev/tools/prodos/read_volume.py')
            reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
            def inspect():                  # raw entries: key blocks, the bitmap
                image=reader.Image(disk.read_bytes())
                entries={e[1:1+(e[0]&15)].decode():e for e in image.entries(2)}
                return image,entries
            def execute(variant,action):
                subprocess.run([str(exe),str(roms),str(disk),str(a.labels.resolve()),variant,action],check=True)
            shutil.copyfile(a.disk,disk);execute('applewin','records-numbers')
            execute('applewin','records-collisions')
            execute('applewin','records-finetext')
            execute('iie-nmos','records-nmos')
            for variant in ('applewin','mame','iic16','iic32'):
                shutil.copyfile(a.disk,disk)
                execute(variant,'records-help')
                execute(variant,'records-music')
                execute(variant,'records-victory')
                execute(variant,'records-save')
                data=a2test.prodos_files(disk)['HIGHSCORES'][2]
                assert len(data)==38 and data[:5]==b'CBR1\x02' and data[5]==59,'sector 60 reached is saved'
                assert sum(data[:36])==int.from_bytes(data[36:38],'little')
                assert [int.from_bytes(data[6+i*6:8+i*6],'little') for i in range(5)]==[3200,1800,1500,1240,900]
                execute(variant,'records-load')
            # '?' with the ENDING overlay missing from the volume (entry renamed).
            for variant in ('applewin','iic32'):
                shutil.copyfile(a.disk,disk);data=bytearray(disk.read_bytes())
                name=data.index(b'ENDING',1024,1536);data[name:name+6]=b'ENDINX'
                disk.write_bytes(data);execute(variant,'records-nohelp')
            # A format 1 file (scores in points) is converted, then saved as format 2.
            shutil.copyfile(a.disk,disk);image,entries=inspect();entry=entries['HIGHSCORES']
            old=bytearray(b'CBR1\x01\x07')
            for points,mode in zip((3200,1800,1500,1240,900),(2,1,0,0,1)):old+=points.to_bytes(2,'little')+b'ABC'+bytes([mode])
            old+=sum(old).to_bytes(2,'little')
            data=bytearray(image.d);key=int.from_bytes(entry[0x11:0x13],'little');data[key*512:key*512+38]=old
            disk.write_bytes(data);execute('applewin','records-v1')
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
                cmd=[str(exe),str(roms),str(disk),str(a.labels.resolve()),variant]
                if entry!='click': cmd.append(entry)
                print(f'AppleMouse {variant}, {entry}',flush=True)
                result=subprocess.run(cmd)
                if result.returncode:failures.append(f'{variant}/{entry}')
        if failures:raise SystemExit('FAIL '+', '.join(failures))
if __name__=='__main__': main()
