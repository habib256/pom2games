"""verlet -- integer Verlet physics, the Python reference of dev/lib/physics.

Design a physics in Python first, then run it on the 6502 with lib/physics:
both agree bit for bit (dev/tests/test_verlet.py, DIRTBIKE's tests).

  fixed       s16, s8, clamp, floor / toward-zero shifts, 8.8 and 16.8, l2q, k8
  points      Points: x, y, ox, oy (structure of arrays) and their moves
  constraint  Constraint, constrain, con_pass, the 6502 tables
  ground      HeightMap: slope normals, probe, push, bounce, tangent hook
  segments    SegmentGround: walls, overhangs, loops (line segments)
  contact     circle contacts: pair, contact_all, boxes, sleep_check
  emit        constants and tables -> a ca65 include (written when changed)
  harness     assemble a driver, run an input script in a2run, snapshots
"""
from .fixed import s8, s16, clamp, asr, asr0, damp, fx88, fx168, l2q, k8  # noqa: F401
from .points import Points  # noqa: F401
from .constraint import Constraint, constrain, con_pass, tables  # noqa: F401
from .ground import HeightMap, normals, decompose, rebuild  # noqa: F401
from .segments import SegmentGround, near_normal, near_normals  # noqa: F401
from . import contact  # noqa: F401
