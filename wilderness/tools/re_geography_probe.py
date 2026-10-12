"""Extract every terrain sample through the original game's own lookup.

Local Sierra disks only; generated heights/types remain in ignored build/.
The small injected driver calls the original $15A8 without changing TOPO.
"""
import sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'tests'), str(Path(__file__).resolve().parent)]
from common import HERE,a2test
from test_weather_cycle import probe_disk
code=bytes.fromhex('A2 00 8E 00 09 AE 00 09 86 F5 20 A8 15 AE 00 09 9D 00 20 A5 C0 9D 00 21 EE 00 09 AE 00 09 E0 E0 D0 E3 4C 00 08')
from re_surv_run import boot
steps=boot()+['poke:B0E2:4C','poke:B0E3:00','poke:B0E4:08']
steps += [f'poke:{0x0800+i:04X}:{v:02X}' for i,v in enumerate(code)]
steps += ['until:0800:20000']
d=HERE/'build/SIERRA.woz'
for y in range(168):steps += [f'poke:00F7:{y:02X}','until:0822:1000','peek:2000:224','peek:2100:224','until:0800:1000']
r=a2test.run(d,steps,emulator=a2test.A2SHOT,timeout=900,cwd=HERE)
(HERE/'build/re_geography/heights.bin').write_bytes(b''.join(r.mem(0x2000,224,y) for y in range(168)))
(HERE/'build/re_geography/types.bin').write_bytes(b''.join(r.mem(0x2100,224,y) for y in range(168)))
print('37632 native terrain samples extracted')
