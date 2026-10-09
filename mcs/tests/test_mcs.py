#!/usr/bin/env python3
"""Boot and exercise the actual cc65 editor, disk persistence and speaker bus."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'mcs'
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test
import dos33

L = a2test.labels(GAME / 'build/mcs.lbl', strip=True)
DISK = ROOT / 'dist/MCS.dsk'


def boot(disk=DISK, steps=(), **kwargs):
    return a2test.run(disk, ['wait:1500', *steps], **kwargs)


def idle():
    return L.until('apple2_getkey', 1200)


def key(text):
    return ['key:' + text, 'wait:1', idle()]


def check(work):
    original = dos33.read_file(DISK.read_bytes(), 'SONG')
    r = boot(steps=[idle(), 'peek:1000:200', L.peek('ready'), 'peek:2000:8192'])
    assert r.mem(0x1000, 200) == original, 'startup song not loaded'
    assert r.mem(L['ready'], 1) == b'\x01', 'editor not ready'
    assert sum(bool(v) for v in a2test.hgr_visible(r.mem(0x2000,8192))) > 500

    saved = work / 'saved.dsk'
    r = boot(steps=[idle(), *key('I\rV+\rD]S'), 'peek:1000:200',
                    L.peek('dirty'), f'dsk:{saved}'])
    edited = r.mem(0x1000,200)
    assert edited[8] == 62 and edited[72] == 49, 'two voices not independently editable'
    assert edited[136] == 4 and edited[5] == 125, 'duration/tempo edit lost'
    assert r.mem(L['dirty'],1) == b'\0', 'successful save still dirty'
    assert dos33.read_file(saved.read_bytes(),'SONG') == edited, 'disk payload differs'
    r = boot(saved, [idle(), 'peek:1000:200', *key('RLO'), 'peek:1000:200'])
    assert r.mem(0x1000,200,0) == edited and r.mem(0x1000,200,1) == edited

    r = boot(steps=[idle(), *key('NO'), *key('K'*63+'\rF'),
                    'peek:1000:200', L.peek('cursor'), *key('K'), L.peek('cursor')])
    song = r.mem(0x1000,200)
    assert song[6] == 64 and song[8+63] == 60, 'last page/extension broken'
    assert r.mem(L['cursor'],1,0) == r.mem(L['cursor'],1,1) == b'\x3f'

    # Decline destructive commands and leave cleanly after explicit acceptance.
    r = boot(steps=[idle(), *key('I\rNN'), 'peek:1000:200',
                    *key(r'\eN'), L.peek('ready'), r'key:\eO', 'wait:30', 'text'])
    assert r.mem(0x1000,200)[8] == 62, 'declined New erased song'
    assert r.mem(L['ready'],1) == b'\x01', 'declined Quit left editor'
    assert ']' in r.out, 'quit did not return to DOS'

    protected = work/'protected.dsk'
    r = boot(steps=[idle(), *key('I\rS'), L.peek('dirty'), f'dsk:{protected}'], wp=True)
    assert r.mem(L['dirty'],1) == b'\x01'
    assert protected.read_bytes() == DISK.read_bytes(), 'write-protected disk changed'

    # A malformed song is rejected before replacing a currently edited song.
    bad = bytearray(DISK.read_bytes())
    broken = bytearray(original)
    broken[72] = 255
    dos33.replace_file(bad, 'SONG', broken)
    malformed = work / 'malformed.dsk'
    malformed.write_bytes(bad)
    r = boot(malformed, [idle(), 'peek:1000:200', *key('I\rLO'), 'peek:1000:200'])
    assert r.mem(0x1000,200,0)[8] == 0, 'invalid startup data accepted'
    assert r.mem(0x1000,200,1)[8] == 62, 'invalid reload replaced edits'

    # Verify oscillator pitch from actual $C030 access times, not a mock.
    mono = work/'mono.spk'
    r = boot(steps=[idle(), L.poke('selected',69), f'spklog:{mono}', *key('A')])
    times = list(map(int,mono.read_text().splitlines()))
    gaps = [b-a for a,b in zip(times,times[1:])]
    assert len(times) > 150, 'no audition audio'
    assert sum(g in (17*68,18*68) for g in gaps) > len(gaps)*0.85, 'DDS timing/pitch'
    hz = (len(times)-1)*a2test.CPU_HZ/(2*(times[-1]-times[0]))
    assert abs(hz-440) < 8, ('A4 tuning',hz)

    duet, rest = work/'duet.spk', work/'rest.spk'
    r = boot(steps=[idle(), 'poke:1006:01', f'spklog:{duet}', *key(' '),
                    'poke:1008:00', 'poke:1048:00', f'spklog:{rest}', *key(' ')])
    assert len(duet.read_text().splitlines()) > 100, 'two-voice playback silent'
    assert len(rest.read_text().splitlines()) <= 1, 'rest toggles speaker'

    # Playback can be interrupted without making the score dirty.
    r = boot(steps=[idle(), 'key: ', 'wait:20', 'key:X', 'wait:1', idle(),
                    L.peek('playing'), L.peek('dirty'), *key('? '), L.peek('ready')])
    assert r.mem(L['playing'],1) == b'\0' and r.mem(L['dirty'],1) == b'\0'
    assert r.mem(L['ready'],1) == b'\x01'
    print('MCS: boot/HGR, editing both voices, 64 steps, durations/tempo, save/reboot/reload,')
    print(f'confirmation, protected/invalid disk, speaker A4={hz:.1f} Hz, duet/rest/abort and DOS exit OK.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='mcs-test-') as tmp:
        check(Path(tmp))
