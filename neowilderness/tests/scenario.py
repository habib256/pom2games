"""Ordinary-play script shared by the residency and reference-state tests.

Each step is (keys, checkpoint label, exit keys). The same keystrokes drive
the frozen HGR/DOS reference (its own label file) and the ProDOS build.
The script covers the screens, both rotations, WALK and SWIM, meals, care,
TOPO and MAP, then rests and sleeps across hourly health updates and
midnight (the journey starts at 7:00).
"""

SCRIPT = [
    ('STATUS\r', 'status_key', '\\e'),
    ('INVENTORY\r', 'inventory_key', '\\e'),
    ('HELP\r', 'help_key', '\\e'),
    ('\\<', 'idle', None),
    ('\\>', 'idle', None),
    ('\\>', 'idle', None),
    ('WALK 1 H\r', 'idle', None),
    ('SWIM 1 H\r', 'idle', None),
    ('EAT CHEESE 4 OZ\r', 'idle', None),
    ('DRINK WATER 4 OZ\r', 'idle', None),
    ('USE SUNSCREEN\r', 'idle', None),
    ('USE FIRSTAID KIT\r', 'idle', None),
    ('TOPO\r', 'graphical_topo_key', '\\e'),
    ('MAP\r', 'topo_key', '\\e'),
    ('LOOK R\r', 'idle', None),
    ('REST 3 H\r', 'idle', None),
    ('WALK 30 MIN\r', 'idle', None),
    ('SLEEP 8 H\r', 'idle', None),
    ('SLEEP 8 H\r', 'idle', None),
    # Discoveries and animals interrupt rests: repeat until past midnight.
    ('SLEEP 8 H\r', 'idle', None),
    ('SLEEP 8 H\r', 'idle', None),
    ('SLEEP 8 H\r', 'idle', None),
    ('SLEEP 8 H\r', 'idle', None),
    ('STATUS\r', 'status_key', '\\e'),
]
# The HGR reference (../wilderness HEAD) loads SIM before SWIM's shore
# probes; the whole script is compared.
REFERENCE_SCRIPT = SCRIPT
LIMIT = 40000


def play(session, labels, script=SCRIPT, each=None):
    """Run the script in an a2test.Session; each(step) after every step."""
    session.step(labels.until('idle', LIMIT))
    session.step(labels.poke('nature_frequency', 0))
    for step in script:
        keys, target, leave = step
        text = keys[:-1] if keys.endswith('\r') else keys
        session.step(f'key:{text}')
        if keys.endswith('\r'):
            session.step('press:\\r')
            session.step(labels.until('do_command', LIMIT))
        if target == 'idle':
            # Messages such as a refused SWIM wait for a key: acknowledge
            # them with SPACE, identically in both builds.
            stops = f'until:{labels["idle"]:04X},{labels["wait_key"]:04X}:{LIMIT}'
            while session.step(stops).out.rstrip().endswith(f'PC={labels["wait_key"]:04X}'):
                session.step('press: ')
                session.step('wait:1')
        else:
            session.step(labels.until(target, LIMIT))
        if leave:
            session.step(f'press:{leave}')
            session.step(labels.until('idle', LIMIT))
        if each:
            each(step)
