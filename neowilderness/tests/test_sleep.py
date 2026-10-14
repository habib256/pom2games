#!/usr/bin/env python3
"""Real-keyboard sleep: no disk read, bounded module loads, unchanged survival/display."""
from common import DISK, L, a2test, fp, hgr_rows, text_screen


def sleep(prompted):
    with a2test.Session(DISK) as s:
        s.step(L.until('idle', 20000))
        s.step(L.poke('nature_frequency', 0))
        if prompted:
            s.step('key:REST')
            s.step('press:\\r')
            s.step(L.until('input_number_idle', 20000))
            s.step('key:8')
        else:
            s.step('key:SLEEP 8 H')
        s.step('press:\\r')
        if not prompted:
            s.step(L.until('do_command', 20000))
            before = int.from_bytes(s.step(L.peek('overlay_reads', 2)).data, 'little')
            calls = s.step(L.peek('mli_calls', 2)).data
        s.step(L.until('idle', 20000))
        if not prompted:
            after = int.from_bytes(s.step(L.peek('overlay_reads', 2)).data, 'little')
            # Module loads are RAM copies now, never disk reads. 14 is the
            # count of the frozen HGR build (its former 4 was stale there too),
            # + 2: the health alerts module (lot 13, ID 27) after each health
            # update (docs/MEMORY.md 13).
            assert after - before == 16, (before, after)
            assert s.step(L.peek('mli_calls', 2)).data == calls, 'disk access during SLEEP'
        assert fp(s.step(L.peek('s_elap', 5)).data) == 8
        assert fp(s.step(L.peek('s_hour', 5)).data) == 15
        assert 'YOU RESTED 8 HOURS.' in '\n'.join(text_screen(s.step('peek:0400:1024').data))
        # Clock, deficits, health cadence, body temperature, insulation,
        # metabolism and astronomical/air state are contiguous resident data.
        state = s.step(L.peek('s_hour', L['s_t0'] + 5 - L['s_hour'])).data
        items = tuple(s.step(L.peek(name, 76)).data for name in
                      ('it_place', 'it_pack_lo', 'it_pack_hi', 'it_gnd_lo', 'it_gnd_hi'))
        view = hgr_rows(s.step('peek:2000:8192').data)
        return state, items, view


def wait_results():
    from test_input import command, screen
    from test_thermal import poke
    for duration,label in (('10 MIN','10 MINUTES'),('1 H','1 HOURS')):
        results=[]
        for word in ('WAIT','PAUSE','REST'):
            with a2test.Session(DISK) as s:
                s.step(L.until('idle',20000))
                s.step(L.poke('nature_frequency',0))
                for step in poke('s_defr',10):
                    s.step(step)
                command(s,f'{word} {duration}')
                expected='RESTED' if word=='REST' else 'WAITED'
                assert f'YOU {expected} {label}.' in screen(s),(word,duration,screen(s))
                state=s.step(L.peek('s_hour',L['s_t0']+5-L['s_hour'])).data
                results.append((state,fp(s.step(L.peek('s_elap',5)).data),
                                fp(s.step(L.peek('s_defr',5)).data)))
                # Cancellation must not reuse the preceding success message.
                command(s,f'{word} 0 MIN')
                assert 'ACTION CANCELLED.' in screen(s)
                assert s.step(L.peek('s_hour',L['s_t0']+5-L['s_hour'])).data==state
        assert results[0]==results[1], 'WAIT and PAUSE must have identical survival effects'
        assert results[0][1]==results[2][1], 'waiting and resting must spend the same duration'
        assert results[0][2]>results[2][2], 'waiting must not receive a rest credit'
    print('  WAIT/PAUSE report waiting in hours/minutes; survival unchanged, REST credit distinct, zero cancelled')


def main():
    assert sleep(False) == sleep(True), 'inline sleep changed simulation or view'
    print('  SLEEP 8 H: 14 RAM module loads, no disk read; exact eight hours; survival, inventory and view match prompted REST')
    with a2test.Session(DISK) as s:
        s.step(L.until('idle', 20000))
        s.step(L.poke('nature_frequency', 0))
        reads = int.from_bytes(s.step(L.peek('overlay_reads', 2)).data, 'little')
        s.step('key:SLEEP')
        s.step('press:\\r')
        s.step(L.until('input_number_idle', 20000))
        assert int.from_bytes(s.step(L.peek('overlay_reads', 2)).data, 'little') == reads + 1
        s.step('key:\\e')
        s.step(L.until('idle', 20000))
        assert fp(s.step(L.peek('s_elap', 5)).data) == 0
        for word, verb in (('REST', 20), ('SLEEP', 20), ('CAMP', 21),
                           ('EXERCISE', 44), ('WAIT', 19), ('PAUSE', 19)):
            before = s.step(L.peek('overlay_reads', 2)).data
            s.step(f'key:{word} 1 MIN')
            s.step('press:\\r')
            s.step(L.until('do_rest', 20000))
            assert s.step(L.peek('verb')).data[0] == verb, word
            if word in ('REST', 'SLEEP'):
                assert s.step(L.peek('input_argument')).data[0] == 2, word
                assert s.step(L.peek('overlay_reads', 2)).data == before, word
            else:
                assert s.step(L.peek('overlay_current')).data[0] == 13, word
            s.step(L.until('idle', 20000))
        assert abs(fp(s.step(L.peek('s_elap', 5)).data) * 60 - 6) < 1e-6
    print('  Prompted SLEEP: one RAM module load and atomic ESC; all six rest/wait verbs retain minute durations')
    wait_results()


if __name__ == '__main__':
    main()
