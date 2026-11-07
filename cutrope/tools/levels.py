"""CUTROPE -- the levels (data only: tools/cutrope.py compiles them, the
solver checks them).

A level:
  candy     its start (whole px)
  ropes     (pin x, pin y, links, slack): the rope runs from the pin to the
            candy's start, its length slack x the distance, its inner points
            on a sag (whole px); 3 ropes, 8 links in all at most (the budget:
            a tick of 2 video frames, README)
  stars     3 centres
  frog      top left of its 14 x 14 box
  segs      (x0, y0, x1, y1, kind) whole px, kind 0 = a platform (free side
            above: drawn left to right), 1 = spikes (horizontal: the line is
            the teeth's tips), 2 = a trampoline (horizontal: the candy
            bounces off it as fast as it came, 2 px a tick at least)
  bubble    (x, y) its centre (optional, one at most)
  cushions  (x, y, dir) the body's centre, dir R D L U (optional, two at most)
  solution  [(tick, mask)]: the keys at those ticks -- mask bits 0-2 cut ropes
            1-3 (keys 1-3), bits 3-4 puff cushions 1-2 (keys 4-5), bit 5 pops
            the bubble (key 6); the candy into the frog with the three stars
            (tests/test_cutrope.py replays every one on the model and the 6502)
  windows   what `tools/cutrope.py --solve` found (a note, not checked)
"""
L1, L2, L3, P4, P5, POP = 1, 2, 4, 8, 16, 32
TRAMP = 2


def spikes(x0, x1, y):
    """A row of spikes from x0 to x1 at row y, in pieces of 76 px at most
    (a segment's box: 88 px)."""
    n = -(-(x1 - x0) // 76)
    xs = [x0 + (x1 - x0) * k // n for k in range(n + 1)]
    return [(a, y, b, y, 1) for a, b in zip(xs, xs[1:])]


LEVELS = [
    dict(name='SWING', candy=(60, 60), ropes=[(110, 26, 4, 1.0)], stars=[(99, 90), (158, 99), (183, 121)], frog=(200, 150),
         segs=[(190, 164, 230, 164, 0)],
         solution=[(45, L1)], windows='key 1 43-48'),
    dict(name='LET GO', candy=(198, 52), ropes=[(172, 34, 3, 1.0)], stars=[(146, 56), (142, 68), (140, 82)], frog=(132, 92),
         segs=[(119, 107, 159, 107, 0)],
         solution=[(59, L1)], windows='key 1 55-63'),
    dict(name='TWO ROPES', candy=(128, 48), ropes=[(100, 24, 3, 1.0), (164, 24, 4, 1.3)], stars=[(74, 52), (132, 81), (148, 108)], frog=(156, 140),
         segs=[(146, 154, 186, 154, 0)],
         solution=[(6, L2), (105, L1)], windows='key 2 0-16, key 1 101-109'),
    dict(name='BACKSWING', candy=(137, 44), ropes=[(105, 25, 3, 1.0)], stars=[(77, 52), (79, 76), (80, 93)], frog=(74, 108),
         segs=[(61, 123, 101, 123, 0)],
         solution=[(73, L1)], windows='key 1 67-76'),
    dict(name='SPIKES', candy=(100, 60), ropes=[(66, 24, 4, 1.0), (134, 24, 4, 1.0)], stars=[(134, 80), (176, 82), (193, 105)], frog=(202, 128),
         segs=[(4, 182, 80, 182, 1), (80, 182, 156, 182, 1), (156, 182, 200, 182, 1), (190, 142, 232, 142, 0)],
         solution=[(4, L1), (52, L2)], windows='key 1 0-11, key 2 44-62'),
    dict(name='FIRST PUFF', candy=(116, 76), ropes=[(97, 52, 3, 1.0)], cushions=[(72, 77, 'R')], stars=[(90, 84), (65, 97), (59, 109)], frog=(42, 130),
         segs=spikes(4, 251, 182) + [(29, 145, 69, 145, 0)],
         solution=[(5, P4), (51, L1)], windows='key 4 0-9, key 1 45-61'),
    dict(name='SLACK', candy=(150, 69), ropes=[(129, 36, 4, 1.0), (170, 44, 3, 1.3)], stars=[(140, 79), (120, 79), (108, 72)], frog=(102, 119),
         segs=[(89, 134, 129, 134, 0)],
         solution=[(10, L2), (71, L1)], windows='key 2 0-24, key 1 64-76'),
    dict(name='SIDE WIND', candy=(115, 57), ropes=[(101, 27, 3, 1.0)], cushions=[(62, 73, 'R')], stars=[(95, 74), (103, 104), (106, 119)], frog=(105, 151),
         segs=spikes(4, 251, 182) + [(92, 166, 132, 166, 0)],
         solution=[(21, L1), (39, P4)], windows='key 1 17-34, key 4 35-45'),
    dict(name='BUBBLE', candy=(96, 72), ropes=[(53, 47, 4, 1.0)], bubble=(23, 101), stars=[(47, 100), (31, 100), (14, 73)], frog=(7, 37),
         segs=spikes(4, 251, 182) + [(4, 52, 34, 52, 0)],
         solution=[(44, L1)], windows='key 1 41-49'),
    dict(name='BOUNCE', candy=(201, 62), ropes=[(162, 26, 4, 1.0)], stars=[(175, 80), (127, 76), (110, 67)], frog=(74, 67),
         segs=[(122, 92, 160, 92, 2), (61, 82, 101, 82, 0)],
         solution=[(40, L1)], windows='key 1 38-42'),
    dict(name='TUG', candy=(88, 73), ropes=[(60, 48, 3, 1.0), (110, 47, 3, 1.2)], stars=[(106, 87), (129, 84), (120, 102)], frog=(106, 128),
         segs=[(93, 143, 133, 143, 0)],
         solution=[(6, L1), (82, L2)], windows='key 1 0-9, key 2 77-87'),
    dict(name='BLOW AND GO', candy=(158, 56), ropes=[(134, 32, 3, 1.0)], cushions=[(111, 57, 'R')], stars=[(132, 68), (105, 68), (94, 82)], frog=(75, 102),
         segs=spikes(4, 251, 182) + [(62, 117, 102, 117, 0)],
         solution=[(5, P4), (54, L1)], windows='key 4 0-12, key 1 46-60'),
    dict(name='BALLOON', candy=(71, 90), ropes=[(105, 71, 4, 1.0)], bubble=(136, 101), stars=[(135, 100), (136, 78), (136, 66)], frog=(129, 32),
         segs=spikes(4, 251, 182) + [(116, 47, 156, 47, 0)],
         solution=[(73, L1)], windows='key 1 53-96'),
    dict(name='CROSSWIND', candy=(142, 60), ropes=[(128, 25, 3, 1.0)], cushions=[(97, 76, 'R'), (159, 101, 'L')], stars=[(130, 81), (138, 101), (129, 128)], frog=(115, 154),
         segs=spikes(4, 251, 182) + [(102, 169, 142, 169, 0)],
         solution=[(18, L1), (36, P4), (48, P5)], windows='key 1 14-25, key 4 31-40, key 5 45-51'),
    dict(name='LATE PUFF', candy=(85, 54), ropes=[(100, 24, 3, 1.0)], cushions=[(155, 73, 'L')], stars=[(121, 73), (114, 90), (108, 120)], frog=(96, 146),
         segs=spikes(4, 251, 182) + [(83, 161, 123, 161, 0)],
         solution=[(40, L1), (60, P4)], windows='key 1 37-42, key 4 57-65'),
    dict(name='PUFF AND POP', candy=(59, 54), ropes=[(60, 19, 3, 1.0)], bubble=(59, 85), cushions=[(39, 90, 'R')],
         stars=[(62, 88), (71, 84), (82, 89)], frog=(83, 141),
         segs=spikes(4, 251, 182) + [(70, 156, 110, 156, 0)],
         solution=[(23, L1), (61, P4), (73, POP)], windows='key 1 16-37, key 4 49-64, key 6 70-113'),
    dict(name='LEFT FIRST', candy=(137, 50), ropes=[(83, 25, 4, 1.0), (170, 25, 3, 1.0)], stars=[(145, 59), (172, 68), (201, 54)], frog=(190, 126),
         segs=spikes(4, 251, 182) + [(177, 141, 217, 141, 0)],
         solution=[(4, L1), (72, L2)], windows='key 1 0-10, key 2 70-76'),
    dict(name='NUDGE', candy=(198, 63), ropes=[(205, 33, 3, 1.0)], cushions=[(228, 67, 'L')], stars=[(198, 65), (208, 75), (227, 124)], frog=(229, 154),
         segs=[(216, 169, 251, 169, 0)],
         solution=[(14, P4), (58, L1)], windows='key 4 11-16, key 1 55-63'),
    dict(name='RELAY', candy=(160, 58), ropes=[(156, 29, 3, 1.0)], cushions=[(186, 69, 'L'), (133, 129, 'U')], stars=[(145, 75), (120, 103), (109, 118)], frog=(83, 150),
         segs=spikes(4, 251, 182) + [(70, 165, 110, 165, 0)],
         solution=[(29, L1), (44, P4), (56, P5)], windows='key 1 23-37, key 4 39-49, key 5 45-65'),
    dict(name='STEPPING STONES', candy=(192, 68), ropes=[(168, 45, 3, 1.0)], stars=[(134, 112), (118, 91), (77, 93)], frog=(17, 110),
         segs=[(118, 117, 150, 117, 2), (61, 101, 99, 101, 2), (4, 125, 44, 125, 0)],
         solution=[(33, L1)], windows='key 1 29-36'),
    dict(name='HOP', candy=(196, 43), ropes=[(157, 28, 4, 1.0)], stars=[(167, 75), (135, 95), (80, 73)], frog=(41, 92),
         segs=[(112, 101, 166, 101, 2), (28, 107, 68, 107, 0)],
         solution=[(33, L1)], windows='key 1 31-36'),
    dict(name='DOUBLE BOUNCE', candy=(106, 54), ropes=[(131, 29, 3, 1.0)], stars=[(135, 74), (191, 78), (212, 59)], frog=(236, 77),
         segs=spikes(4, 251, 182) + [(122, 83, 156, 83, 2), (176, 87, 210, 87, 2), (223, 92, 251, 92, 0)],
         solution=[(27, L1)], windows='key 1 22-29'),
    dict(name='DOUBLE SNAP', candy=(66, 53), ropes=[(37, 26, 4, 1.0), (100, 25, 4, 1.3)], stars=[(88, 82), (128, 88), (139, 98)], frog=(156, 136),
         segs=spikes(4, 251, 182) + [(143, 151, 183, 151, 0)],
         solution=[(9, L1), (51, L2)], windows='key 1 0-11, key 2 48-54'),
    dict(name='STORM', candy=(128, 51), ropes=[(132, 24, 3, 1.0)], cushions=[(108, 61, 'R'), (158, 115, 'U')], stars=[(143, 65), (175, 94), (191, 114)], frog=(204, 145),
         segs=spikes(4, 251, 182) + [(191, 160, 231, 160, 0)],
         solution=[(26, L1), (43, P4), (55, P5)], windows='key 1 23-35, key 4 38-47, key 5 44-62'),
    dict(name='SKY FROG', candy=(138, 87), ropes=[(163, 59, 4, 1.0)], bubble=(185, 96), stars=[(188, 69), (188, 56), (189, 44)], frog=(183, 26),
         segs=[(170, 41, 210, 41, 0)],
         solution=[(72, L1)], windows='key 1 44-81'),
]

# the cycle bench (not played: the tests load it): one 10-link rope and two of 6
BENCH = dict(name='BENCH', candy=(128, 96), ropes=[(128, 20, 10, 1.0), (60, 40, 6, 1.0), (196, 40, 6, 1.0)],
             stars=[(20, 30), (30, 30), (40, 30)], frog=(230, 20), segs=[(4, 182, 76, 182, 1)])

SOLUTIONS = [lv['solution'] for lv in LEVELS]
