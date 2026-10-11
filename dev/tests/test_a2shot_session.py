#!/usr/bin/env python3
"""Live emulator framing, alternative breakpoints, paging traces and failures."""
import hashlib
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import a2test


def main():
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        binary = work/'fixture.bin'
        # STA $4000 then NOP/JMP loop: no game state or original code needed.
        binary.write_bytes(bytes.fromhex('A9 5A 8D 00 40 EA 4C 05 60'))
        disk = a2test.build_disk(work, 'SESSION', binary)
        original_hash = hashlib.sha256(disk.read_bytes()).digest()
        with a2test.Session(disk) as session:
            reply = session.step('until:6006,6005:4000')
            assert 'PC=6005' in reply.out
            assert session.step('peek:4000:1').mem(0x4000, 1) == b'Z'
            session.step('watch:6005:4000:4096')
            trace = session.step('until:6006:1')
            observed = re.search(r'watch 6005 .* mem=([0-9A-F]+)', trace.out)
            assert observed and len(observed[1]) == 8192
            assert bytes.fromhex(observed[1])[0] == 0x5A
            assert session.step('pc').out.strip() == 'PC=6006'
        assert session.process.returncode == 0
        batch = a2test.run(disk, ['until:6006,6005:4000', 'peek:4000:1'],
                           emulator=a2test.A2SHOT)
        assert batch.mem(0x4000, 1) == b'Z'

        for step, exit_code in [('until:DEAD:1', 3), ('until:6005,:1', 2),
                                ('until:10000:1', 2), ('watch:6005:4000:4097', 2),
                                ('watch:6005:FFFF:2', 2), ('unknown', 2)]:
            with a2test.Session(disk) as failed:
                failed.step('until:6005:4000')
                try:
                    failed.step(step)
                except RuntimeError as error:
                    assert f'exit {exit_code}' in str(error), error
                else:
                    raise AssertionError(f'failed step accepted: {step}')
            assert failed.process.poll() == exit_code
            if exit_code == 3:
                assert 'PC=' in failed.out, 'failure evidence must remain in the log'
        assert hashlib.sha256(disk.read_bytes()).digest() == original_hash
    print('Interactive/batch replies, multiple breakpoints, 4 KB trace, failures and private disk: OK')


if __name__ == '__main__':
    main()
