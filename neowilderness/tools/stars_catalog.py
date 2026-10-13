#!/usr/bin/env python3
"""stars_catalog.py: the star catalogue of the night sky (lot 7).

Sources of the embedded tables (positions J2000.0):
  - STARS, the 79 brightest: ESA, The Hipparcos and Tycho Catalogues, ESA
    SP-1200 (1997), positions as given by SIMBAD (CDS, Strasbourg) for each
    star; D. Hoffleit & W. H. Warren, The Bright Star Catalogue, 5th revised
    edition (Yale, 1991), V magnitudes and B-V colours (combined light for
    close pairs such as Acrux, Alpha Centauri, Castor). The 78 stars of
    V <= 2.31 (Eta Centauri), plus Delta Crucis (V = 2.79) so that the
    Southern Cross has its four arms.
  - EXTRA, 203 others: the Bright Star Catalogue, 5th revised edition
    (CDS V/50): J2000 (FK5) positions, V, B-V; the stars of V <= 3.50 less
    44 lone faint ones, plus the 44 stars that complete the figures of
    FIGURES (to V 4.95); see the comment of the table.
282 stars, 3 bytes each: 846 bytes.

Epoch: the tables are J2000.0. encode() precesses them to 1985.0 (equinox
of date of the game's ephemerides, tools/sky_ephemeris.py) with the IAU 1976
precession angles (Meeus, Astronomical Algorithms, eq. 21.2-21.4). The shift
is at most 15 yr x 50.3"/yr = 12.6' (0.21 deg) on the sky, a third of a
view column (1/560 turn = 0.64 deg) and a quarter of a row near the horizon:
J2000 positions would draw the same picture to within one pixel; proper
motions over 15 years (Arcturus: 34") are ignored.

Record (3 bytes per star; order: Polaris and the Cross, then class 0, 1, 2,
each by magnitude):
  +0     right ascension in quarter view units (2240 = 24 h, 0.16 deg), bits 7-0
  +1     bit 7 south (declination < 0); bit 6 first magnitude (V < 1.5: the
         module lists the star twice, one row apart, a 3-row pixel); bits
         5-4 look (0 white, 1 pale yellow B-V >= 0.70, 2 pale blue B-V <=
         -0.10: two rows; 3 faint, V >= 3.0: one grey row); bits 3-0 right
         ascension bits 11-8 (0..8)
  +2     |declination| in view units (1/560 turn = 0.643 deg), 0..140
The selection class (0: the stars of a figure of FIGURES and every star
brighter than 2.0; 1: other stars brighter than 3.0; 2: the rest) is not
stored: it follows from the index, the catalogue being in class order after
the five priority stars (CLASS_STARTS, PRIORITY_CLASSES). Night bright
(full Moon) draws class 0, night dim classes 0-1, night dark every star.
The declination is stored as a magnitude in the view's own angle unit, with
its sign apart, rather than as an S8 of 90/128 deg: one rounding instead of
two before the sine table, and |dec| up to 140 units (Polaris, 139) does not
fit a signed byte in view units. The right ascension in quarter units makes
the hour angle a subtraction (tools/stars_ref.py).
"""
import math

# name, Bayer, RA (h m s), Dec (sign d m s), V, B-V   -- J2000.0
STARS = (
    ('SIRIUS', 'alf CMa', (6, 45, 8.92), (-16, 42, 58.0), -1.46, 0.00),
    ('CANOPUS', 'alf Car', (6, 23, 57.11), (-52, 41, 44.4), -0.74, 0.15),
    ('RIGIL KENT', 'alf Cen', (14, 39, 36.49), (-60, 50, 2.3), -0.27, 0.71),
    ('ARCTURUS', 'alf Boo', (14, 15, 39.67), (19, 10, 56.7), -0.05, 1.23),
    ('VEGA', 'alf Lyr', (18, 36, 56.34), (38, 47, 1.3), 0.03, 0.00),
    ('CAPELLA', 'alf Aur', (5, 16, 41.36), (45, 59, 52.8), 0.08, 0.80),
    ('RIGEL', 'bet Ori', (5, 14, 32.27), (-8, 12, 5.9), 0.13, -0.03),
    ('PROCYON', 'alf CMi', (7, 39, 18.12), (5, 13, 30.0), 0.34, 0.42),
    ('ACHERNAR', 'alf Eri', (1, 37, 42.85), (-57, 14, 12.3), 0.46, -0.16),
    ('BETELGEUSE', 'alf Ori', (5, 55, 10.31), (7, 24, 25.4), 0.50, 1.85),
    ('HADAR', 'bet Cen', (14, 3, 49.41), (-60, 22, 22.9), 0.61, -0.23),
    ('ALTAIR', 'alf Aql', (19, 50, 47.00), (8, 52, 6.0), 0.77, 0.22),
    ('ACRUX', 'alf Cru', (12, 26, 35.90), (-63, 5, 56.7), 0.77, -0.24),
    ('ALDEBARAN', 'alf Tau', (4, 35, 55.24), (16, 30, 33.5), 0.85, 1.54),
    ('ANTARES', 'alf Sco', (16, 29, 24.46), (-26, 25, 55.2), 0.96, 1.83),
    ('SPICA', 'alf Vir', (13, 25, 11.58), (-11, 9, 40.8), 0.97, -0.23),
    ('POLLUX', 'bet Gem', (7, 45, 18.95), (28, 1, 34.3), 1.14, 1.00),
    ('FOMALHAUT', 'alf PsA', (22, 57, 39.05), (-29, 37, 20.1), 1.16, 0.09),
    ('DENEB', 'alf Cyg', (20, 41, 25.91), (45, 16, 49.2), 1.25, 0.09),
    ('MIMOSA', 'bet Cru', (12, 47, 43.27), (-59, 41, 19.6), 1.25, -0.23),
    ('REGULUS', 'alf Leo', (10, 8, 22.31), (11, 58, 2.0), 1.35, -0.11),
    ('ADHARA', 'eps CMa', (6, 58, 37.55), (-28, 58, 19.5), 1.50, -0.21),
    ('CASTOR', 'alf Gem', (7, 34, 35.86), (31, 53, 17.8), 1.58, 0.03),
    ('SHAULA', 'lam Sco', (17, 33, 36.52), (-37, 6, 13.8), 1.62, -0.22),
    ('GACRUX', 'gam Cru', (12, 31, 9.96), (-57, 6, 47.6), 1.63, 1.59),
    ('BELLATRIX', 'gam Ori', (5, 25, 7.86), (6, 20, 58.9), 1.64, -0.22),
    ('ELNATH', 'bet Tau', (5, 26, 17.51), (28, 36, 26.8), 1.65, -0.13),
    ('MIAPLACIDUS', 'bet Car', (9, 13, 11.98), (-69, 43, 1.9), 1.67, 0.07),
    ('ALNILAM', 'eps Ori', (5, 36, 12.81), (-1, 12, 6.9), 1.69, -0.18),
    ('ALNAIR', 'alf Gru', (22, 8, 13.98), (-46, 57, 39.5), 1.74, -0.13),
    ('ALNITAK', 'zet Ori', (5, 40, 45.53), (-1, 56, 33.3), 1.77, -0.21),
    ('ALIOTH', 'eps UMa', (12, 54, 1.75), (55, 57, 35.4), 1.77, -0.02),
    ('DUBHE', 'alf UMa', (11, 3, 43.67), (61, 45, 3.7), 1.79, 1.07),
    ('MIRFAK', 'alf Per', (3, 24, 19.37), (49, 51, 40.2), 1.79, 0.48),
    ('REGOR', 'gam2 Vel', (8, 9, 31.95), (-47, 20, 11.7), 1.83, -0.22),
    ('WEZEN', 'del CMa', (7, 8, 23.48), (-26, 23, 35.5), 1.84, 0.68),
    ('KAUS AUSTR', 'eps Sgr', (18, 24, 10.32), (-34, 23, 4.6), 1.85, -0.03),
    ('AVIOR', 'eps Car', (8, 22, 30.84), (-59, 30, 34.1), 1.86, 1.28),
    ('ALKAID', 'eta UMa', (13, 47, 32.44), (49, 18, 47.8), 1.86, -0.19),
    ('SARGAS', 'tet Sco', (17, 37, 19.13), (-42, 59, 52.2), 1.87, 0.40),
    ('MENKALINAN', 'bet Aur', (5, 59, 31.72), (44, 56, 50.8), 1.90, 0.03),
    ('ATRIA', 'alf TrA', (16, 48, 39.90), (-69, 1, 39.8), 1.91, 1.44),
    ('ALHENA', 'gam Gem', (6, 37, 42.71), (16, 23, 57.4), 1.93, 0.00),
    ('PEACOCK', 'alf Pav', (20, 25, 38.86), (-56, 44, 6.3), 1.94, -0.20),
    ('ALSEPHINA', 'del Vel', (8, 44, 42.23), (-54, 42, 31.8), 1.96, 0.04),
    ('MIRZAM', 'bet CMa', (6, 22, 41.99), (-17, 57, 21.3), 1.98, -0.24),
    ('ALPHARD', 'alf Hya', (9, 27, 35.24), (-8, 39, 31.0), 1.98, 1.44),
    ('POLARIS', 'alf UMi', (2, 31, 49.09), (89, 15, 50.8), 1.98, 0.60),
    ('HAMAL', 'alf Ari', (2, 7, 10.41), (23, 27, 44.7), 2.00, 1.15),
    ('ALGIEBA', 'gam Leo', (10, 19, 58.35), (19, 50, 29.4), 2.01, 1.13),
    ('DIPHDA', 'bet Cet', (0, 43, 35.37), (-17, 59, 11.8), 2.04, 1.02),
    ('NUNKI', 'sig Sgr', (18, 55, 15.93), (-26, 17, 48.2), 2.05, -0.13),
    ('MENKENT', 'tet Cen', (14, 6, 40.95), (-36, 22, 11.8), 2.06, 1.01),
    ('MIRACH', 'bet And', (1, 9, 43.92), (35, 37, 14.0), 2.06, 1.58),
    ('ALPHERATZ', 'alf And', (0, 8, 23.26), (29, 5, 25.6), 2.06, -0.11),
    ('SAIPH', 'kap Ori', (5, 47, 45.39), (-9, 40, 10.6), 2.06, -0.17),
    ('TIAKI', 'bet Gru', (22, 42, 40.05), (-46, 53, 4.5), 2.07, 1.60),
    ('RASALHAGUE', 'alf Oph', (17, 34, 56.07), (12, 33, 36.1), 2.08, 0.15),
    ('KOCHAB', 'bet UMi', (14, 50, 42.33), (74, 9, 19.8), 2.08, 1.47),
    ('ALGOL', 'bet Per', (3, 8, 10.13), (40, 57, 20.3), 2.12, -0.05),
    ('DENEBOLA', 'bet Leo', (11, 49, 3.58), (14, 34, 19.4), 2.14, 0.09),
    ('ALMACH', 'gam And', (2, 3, 53.95), (42, 19, 47.0), 2.17, 1.37),
    ('MUHLIFAIN', 'gam Cen', (12, 41, 31.04), (-48, 57, 35.5), 2.20, -0.01),
    ('NAOS', 'zet Pup', (8, 3, 35.05), (-40, 0, 11.3), 2.21, -0.27),
    ('ASPIDISKE', 'iot Car', (9, 17, 5.41), (-59, 16, 30.8), 2.21, 0.18),
    ('SUHAIL', 'lam Vel', (9, 7, 59.76), (-43, 25, 57.3), 2.21, 1.66),
    ('ALPHECCA', 'alf CrB', (15, 34, 41.27), (26, 42, 52.9), 2.23, -0.02),
    ('MIZAR', 'zet UMa', (13, 23, 55.54), (54, 55, 31.3), 2.23, 0.02),
    ('SADR', 'gam Cyg', (20, 22, 13.70), (40, 15, 24.0), 2.23, 0.67),
    ('MINTAKA', 'del Ori', (5, 32, 0.40), (-0, 17, 56.7), 2.23, -0.22),
    ('SCHEDAR', 'alf Cas', (0, 40, 30.44), (56, 32, 14.4), 2.24, 1.17),
    ('ELTANIN', 'gam Dra', (17, 56, 36.37), (51, 29, 20.0), 2.24, 1.52),
    ('CAPH', 'bet Cas', (0, 9, 10.69), (59, 8, 59.2), 2.28, 0.34),
    ('DSCHUBBA', 'del Sco', (16, 0, 20.01), (-22, 37, 18.1), 2.29, -0.12),
    ('LARAWAG', 'eps Sco', (16, 50, 9.81), (-34, 17, 35.6), 2.29, 1.15),
    ('EPS CEN', 'eps Cen', (13, 39, 53.26), (-53, 27, 59.0), 2.30, -0.22),
    ('ALF LUP', 'alf Lup', (14, 41, 55.76), (-47, 23, 17.5), 2.30, -0.15),
    ('ETA CEN', 'eta Cen', (14, 35, 30.42), (-42, 9, 28.2), 2.31, -0.19),
    ('IMAI', 'del Cru', (12, 15, 8.72), (-58, 44, 56.1), 2.79, -0.19),
)
# Additions (lot 7, "Ciel plus peuple", then "Constellations entieres"):
# the Bright Star Catalogue entries of V <= 3.50 more than 0.3 deg from the
# stars above (the close pairs listed separately there, such as Acrux or
# Castor, are already above with their combined light), except T CrB (HR
# 5958: its catalogued V = 2.0 is the 1946 outburst) and Mira (HR 681: V
# 2..10), less the 44 faintest stars outside the figures of FIGURES (V 3.21
# to 3.50, lone stars of Cetus, Puppis, Hydra, Ursa Major's legs...), plus
# the 44 stars that complete those figures (V 3.39 to 4.95: the bowl of the
# Little Dipper, the Hyades, the Twins, the Sickle, the Keystone, the Lyre,
# the Northern Crown...). Combined light of the close pairs lam Ori (HR 1879
# + 1880), gam Vir (HR 4825 + 4826), gam Ari (HR 545 + 546) and nu Sco (HR
# 6026 + 6027). J2000 positions, V and B-V from the BSC5 (Hoffleit & Warren
# 1991, CDS catalogue V/50), as (HR number, Bayer or Flamsteed designation,
# RA, Dec, V, B-V): 203 stars.
EXTRA = (
    (39, 'gam Peg', (0, 13, 14.2), (15, 11, 1), 2.83, -0.23),
    (98, 'bet Hyi', (0, 25, 45.1), (-77, 15, 15), 2.80, +0.62),
    (99, 'alf Phe', (0, 26, 17.0), (-42, 18, 22), 2.39, +1.09),
    (165, 'del And', (0, 39, 19.7), (30, 51, 39), 3.27, +1.28),
    (264, 'gam Cas', (0, 56, 42.5), (60, 43, 0), 2.47, -0.15),
    (322, 'bet Phe', (1, 6, 5.0), (-46, 43, 7), 3.31, +0.89),
    (403, 'del Cas', (1, 25, 49.0), (60, 14, 7), 2.68, +0.13),
    (429, 'gam Phe', (1, 28, 21.9), (-43, 19, 6), 3.41, +1.57),
    (542, 'eps Cas', (1, 54, 23.7), (63, 40, 12), 3.38, -0.15),
    (546, 'gam Ari', (1, 53, 31.8), (19, 17, 37), 4.04, -0.04),
    (553, 'bet Ari', (1, 54, 38.4), (20, 48, 29), 2.64, +0.13),
    (591, 'alf Hyi', (1, 58, 46.2), (-61, 34, 11), 2.86, +0.28),
    (622, 'bet Tri', (2, 9, 32.6), (34, 59, 14), 3.00, +0.14),
    (911, 'alf Cet', (3, 2, 16.8), (4, 5, 23), 2.53, +1.64),
    (915, 'gam Per', (3, 4, 47.8), (53, 30, 23), 2.93, +0.70),
    (921, 'rho Per', (3, 5, 10.6), (38, 50, 25), 3.39, +1.65),
    (1122, 'del Per', (3, 42, 55.5), (47, 47, 15), 3.01, -0.13),
    (1165, 'eta Tau', (3, 47, 29.1), (24, 6, 18), 2.87, -0.09),
    (1203, 'zet Per', (3, 54, 7.9), (31, 53, 1), 2.85, +0.12),
    (1208, 'gam Hyi', (3, 47, 14.3), (-74, 14, 20), 3.24, +1.62),
    (1220, 'eps Per', (3, 57, 51.2), (40, 0, 37), 2.89, -0.18),
    (1231, 'gam Eri', (3, 58, 1.8), (-13, 30, 31), 2.95, +1.59),
    (1346, 'gam Tau', (4, 19, 47.6), (15, 37, 39), 3.65, +0.99),
    (1373, 'del1 Tau', (4, 22, 56.1), (17, 32, 33), 3.76, +0.98),
    (1409, 'eps Tau', (4, 28, 37.0), (19, 10, 49), 3.53, +1.01),
    (1412, 'tet2 Tau', (4, 28, 39.7), (15, 52, 15), 3.40, +0.18),
    (1577, 'iot Aur', (4, 56, 59.6), (33, 9, 58), 2.69, +1.53),
    (1605, 'eps Aur', (5, 1, 58.1), (43, 49, 24), 2.99, +0.54),
    (1641, 'eta Aur', (5, 6, 30.9), (41, 14, 4), 3.17, -0.18),
    (1654, 'eps Lep', (5, 5, 27.7), (-22, 22, 16), 3.19, +1.46),
    (1666, 'bet Eri', (5, 7, 51.0), (-5, 5, 11), 2.79, +0.13),
    (1702, 'mu Lep', (5, 12, 55.9), (-16, 12, 20), 3.31, -0.11),
    (1829, 'bet Lep', (5, 28, 14.7), (-20, 45, 34), 2.84, +0.82),
    (1865, 'alf Lep', (5, 32, 43.8), (-17, 49, 20), 2.58, +0.21),
    (1879, 'lam Ori', (5, 35, 8.3), (9, 56, 3), 3.39, -0.18),
    (1899, 'iot Ori', (5, 35, 26.0), (-5, 54, 36), 2.77, -0.24),
    (1910, 'zet Tau', (5, 37, 38.7), (21, 8, 33), 3.00, -0.19),
    (1956, 'alf Col', (5, 39, 38.9), (-34, 4, 27), 2.64, -0.12),
    (2095, 'tet Aur', (5, 59, 43.3), (37, 12, 45), 2.62, -0.08),
    (2216, 'eta Gem', (6, 14, 52.6), (22, 30, 24), 3.28, +1.60),
    (2282, 'zet CMa', (6, 20, 18.8), (-30, 3, 48), 3.02, -0.19),
    (2286, 'mu Gem', (6, 22, 57.6), (22, 30, 49), 2.88, +1.64),
    (2473, 'eps Gem', (6, 43, 55.9), (25, 7, 52), 2.98, +1.40),
    (2484, 'ksi Gem', (6, 45, 17.4), (12, 53, 44), 3.36, +0.43),
    (2540, 'tet Gem', (6, 52, 47.3), (33, 57, 40), 3.60, +0.10),
    (2553, 'tau Pup', (6, 49, 56.2), (-50, 36, 53), 2.93, +1.20),
    (2650, 'zet Gem', (7, 4, 6.5), (20, 34, 13), 3.79, +0.79),
    (2653, 'omi2 CMa', (7, 3, 1.5), (-23, 50, 0), 3.02, -0.08),
    (2697, 'tau Gem', (7, 11, 8.4), (30, 14, 43), 4.41, +1.26),
    (2763, 'lam Gem', (7, 18, 5.6), (16, 32, 25), 3.58, +0.11),
    (2773, 'pi Pup', (7, 17, 8.6), (-37, 5, 51), 2.70, +1.62),
    (2777, 'del Gem', (7, 20, 7.4), (21, 58, 56), 3.53, +0.34),
    (2821, 'iot Gem', (7, 25, 43.6), (27, 47, 53), 3.79, +1.03),
    (2827, 'eta CMa', (7, 24, 5.7), (-29, 18, 11), 2.45, -0.08),
    (2845, 'bet CMi', (7, 27, 9.0), (8, 17, 22), 2.90, -0.09),
    (2905, 'ups Gem', (7, 35, 55.3), (26, 53, 45), 4.06, +1.54),
    (2985, 'kap Gem', (7, 44, 26.8), (24, 23, 53), 3.57, +0.93),
    (3185, 'rho Pup', (8, 7, 32.6), (-24, 18, 15), 2.81, +0.43),
    (3734, 'kap Vel', (9, 22, 6.8), (-55, 0, 39), 2.50, -0.18),
    (3873, 'eps Leo', (9, 45, 51.1), (23, 46, 27), 2.98, +0.80),
    (3890, 'ups Car', (9, 47, 6.1), (-65, 4, 19), 3.01, +0.28),
    (3905, 'mu Leo', (9, 52, 45.8), (26, 0, 25), 3.88, +1.22),
    (3975, 'eta Leo', (10, 7, 20.0), (16, 45, 46), 3.52, -0.03),
    (4031, 'zet Leo', (10, 16, 41.4), (23, 25, 2), 3.44, +0.31),
    (4037, 'ome Car', (10, 13, 44.2), (-70, 2, 17), 3.32, -0.08),
    (4199, 'tet Car', (10, 42, 57.4), (-64, 23, 40), 2.76, -0.22),
    (4216, 'mu Vel', (10, 46, 46.2), (-49, 25, 12), 2.69, +0.90),
    (4295, 'bet UMa', (11, 1, 50.5), (56, 22, 57), 2.37, -0.02),
    (4335, 'psi UMa', (11, 9, 39.8), (44, 29, 55), 3.01, +1.14),
    (4357, 'del Leo', (11, 14, 6.5), (20, 31, 25), 2.56, +0.12),
    (4359, 'tet Leo', (11, 14, 14.4), (15, 25, 46), 3.34, -0.01),
    (4540, 'bet Vir', (11, 50, 41.7), (1, 45, 53), 3.61, +0.55),
    (4554, 'gam UMa', (11, 53, 49.8), (53, 41, 41), 2.44, 0.00),
    (4621, 'del Cen', (12, 8, 21.5), (-50, 43, 21), 2.60, -0.12),
    (4623, 'alf Crv', (12, 8, 24.8), (-24, 43, 44), 4.02, +0.32),
    (4630, 'eps Crv', (12, 10, 7.5), (-22, 37, 11), 3.00, +1.33),
    (4660, 'del UMa', (12, 15, 25.6), (57, 1, 57), 3.31, +0.08),
    (4662, 'gam Crv', (12, 15, 48.4), (-17, 32, 31), 2.59, -0.11),
    (4689, 'eta Vir', (12, 19, 54.4), (0, 40, 1), 3.89, +0.02),
    (4700, 'eps Cru', (12, 21, 21.6), (-60, 24, 4), 3.59, +1.42),
    (4757, 'del Crv', (12, 29, 51.9), (-16, 30, 56), 2.95, -0.05),
    (4786, 'bet Crv', (12, 34, 23.2), (-23, 23, 48), 2.65, +0.89),
    (4798, 'alf Mus', (12, 37, 11.0), (-69, 8, 8), 2.69, -0.20),
    (4825, 'gam Vir', (12, 41, 39.6), (-1, 26, 58), 2.91, +0.36),
    (4844, 'bet Mus', (12, 46, 16.9), (-68, 6, 29), 3.05, -0.18),
    (4910, 'del Vir', (12, 55, 36.2), (3, 23, 51), 3.38, +1.58),
    (4915, 'alf2 CVn', (12, 56, 1.7), (38, 19, 6), 2.90, -0.12),
    (4932, 'eps Vir', (13, 2, 10.6), (10, 57, 33), 2.83, +0.94),
    (5020, 'gam Hya', (13, 18, 55.3), (-23, 10, 18), 3.00, +0.92),
    (5028, 'iot Cen', (13, 20, 35.8), (-36, 42, 44), 2.75, +0.04),
    (5107, 'zet Vir', (13, 34, 41.6), (0, 35, 45), 3.37, +0.11),
    (5231, 'zet Cen', (13, 55, 32.4), (-47, 17, 18), 2.55, -0.22),
    (5235, 'eta Boo', (13, 54, 41.1), (18, 23, 52), 2.68, +0.58),
    (5429, 'rho Boo', (14, 31, 49.8), (30, 22, 17), 3.58, +1.30),
    (5435, 'gam Boo', (14, 32, 4.7), (38, 18, 30), 3.03, +0.19),
    (5506, 'eps Boo', (14, 44, 59.2), (27, 4, 27), 2.70, +0.97),
    (5531, 'alf2 Lib', (14, 50, 52.7), (-16, 2, 30), 2.75, +0.15),
    (5571, 'bet Lup', (14, 58, 31.9), (-43, 8, 2), 2.68, -0.22),
    (5602, 'bet Boo', (15, 1, 56.8), (40, 23, 26), 3.50, +0.97),
    (5649, 'zet Lup', (15, 12, 17.1), (-52, 5, 57), 3.41, +0.92),
    (5671, 'gam TrA', (15, 18, 54.6), (-68, 40, 46), 2.89, 0.00),
    (5681, 'del Boo', (15, 15, 30.2), (33, 18, 53), 3.47, +0.95),
    (5685, 'bet Lib', (15, 17, 0.4), (-9, 22, 59), 2.61, -0.11),
    (5695, 'del Lup', (15, 21, 22.3), (-40, 38, 51), 3.22, -0.22),
    (5708, 'eps Lup', (15, 22, 40.9), (-44, 41, 22), 3.37, -0.18),
    (5735, 'gam UMi', (15, 20, 43.7), (71, 50, 2), 3.05, +0.05),
    (5744, 'iot Dra', (15, 24, 55.8), (58, 57, 58), 3.29, +1.16),
    (5747, 'bet CrB', (15, 27, 49.7), (29, 6, 21), 3.68, +0.28),
    (5776, 'gam Lup', (15, 35, 8.5), (-41, 10, 1), 2.78, -0.20),
    (5778, 'tet CrB', (15, 32, 55.8), (31, 21, 33), 4.14, -0.13),
    (5849, 'gam CrB', (15, 42, 44.6), (26, 17, 44), 3.84, 0.00),
    (5854, 'alf Ser', (15, 44, 16.1), (6, 25, 32), 2.65, +1.17),
    (5889, 'del CrB', (15, 49, 35.7), (26, 4, 6), 4.63, +0.80),
    (5897, 'bet TrA', (15, 55, 8.5), (-63, 25, 50), 2.85, +0.29),
    (5903, 'zet UMi', (15, 44, 3.5), (77, 47, 40), 4.32, +0.04),
    (5944, 'pi Sco', (15, 58, 51.1), (-26, 6, 51), 2.89, -0.19),
    (5947, 'eps CrB', (15, 57, 35.3), (26, 52, 40), 4.15, +1.23),
    (5948, 'eta Lup', (16, 0, 7.3), (-38, 23, 49), 3.41, -0.22),
    (5984, 'bet1 Sco', (16, 5, 26.2), (-19, 48, 20), 2.62, -0.07),
    (6027, 'nu Sco', (16, 11, 59.7), (-19, 27, 38), 3.89, +0.04),
    (6056, 'del Oph', (16, 14, 20.7), (-3, 41, 40), 2.74, +1.58),
    (6075, 'eps Oph', (16, 18, 19.3), (-4, 41, 33), 3.24, +0.96),
    (6084, 'sig Sco', (16, 21, 11.3), (-25, 35, 34), 2.89, +0.13),
    (6116, 'eta UMi', (16, 17, 30.3), (75, 45, 19), 4.95, +0.37),
    (6132, 'eta Dra', (16, 23, 59.5), (61, 30, 51), 2.74, +0.91),
    (6148, 'bet Her', (16, 30, 13.2), (21, 29, 23), 2.77, +0.94),
    (6165, 'tau Sco', (16, 35, 53.0), (-28, 12, 58), 2.82, -0.25),
    (6175, 'zet Oph', (16, 37, 9.5), (-10, 34, 2), 2.56, +0.02),
    (6212, 'zet Her', (16, 41, 17.2), (31, 36, 11), 2.81, +0.65),
    (6220, 'eta Her', (16, 42, 53.8), (38, 55, 20), 3.53, +0.92),
    (6247, 'mu1 Sco', (16, 51, 52.2), (-38, 2, 51), 3.08, -0.20),
    (6271, 'zet2 Sco', (16, 54, 35.0), (-42, 21, 41), 3.62, +1.37),
    (6285, 'zet Ara', (16, 58, 37.2), (-55, 59, 25), 3.13, +1.60),
    (6299, 'kap Oph', (16, 57, 40.1), (9, 22, 30), 3.20, +1.15),
    (6322, 'eps UMi', (16, 45, 58.1), (82, 2, 14), 4.23, +0.89),
    (6324, 'eps Her', (17, 0, 17.4), (30, 55, 35), 3.92, -0.01),
    (6378, 'eta Oph', (17, 10, 22.7), (-15, 43, 29), 2.43, +0.06),
    (6380, 'eta Sco', (17, 12, 9.2), (-43, 14, 21), 3.33, +0.41),
    (6396, 'zet Dra', (17, 8, 47.2), (65, 42, 53), 3.17, -0.12),
    (6406, 'alf1 Her', (17, 14, 38.9), (14, 23, 25), 3.48, +1.44),
    (6410, 'del Her', (17, 15, 1.9), (24, 50, 21), 3.14, +0.08),
    (6418, 'pi Her', (17, 15, 2.8), (36, 48, 33), 3.16, +1.44),
    (6461, 'bet Ara', (17, 25, 18.0), (-55, 31, 48), 2.85, +1.46),
    (6462, 'gam Ara', (17, 25, 23.6), (-56, 22, 39), 3.34, -0.13),
    (6508, 'ups Sco', (17, 30, 45.8), (-37, 17, 45), 2.69, -0.22),
    (6510, 'alf Ara', (17, 31, 50.5), (-49, 52, 34), 2.95, -0.17),
    (6536, 'bet Dra', (17, 30, 26.0), (52, 18, 5), 2.79, +0.98),
    (6580, 'kap Sco', (17, 42, 29.3), (-39, 1, 48), 2.41, -0.22),
    (6603, 'bet Oph', (17, 43, 28.4), (4, 34, 2), 2.77, +1.16),
    (6615, 'iot1 Sco', (17, 47, 35.1), (-40, 7, 37), 3.03, +0.51),
    (6623, 'mu Her', (17, 46, 27.5), (27, 43, 14), 3.42, +0.75),
    (6630, 'HR 6630', (17, 49, 51.5), (-37, 2, 36), 3.21, +1.17),
    (6698, 'nu Oph', (17, 59, 1.6), (-9, 46, 25), 3.34, +0.99),
    (6746, 'gam2 Sgr', (18, 5, 48.5), (-30, 25, 27), 2.99, +1.00),
    (6789, 'del UMi', (17, 32, 12.9), (86, 35, 11), 4.36, +0.02),
    (6832, 'eta Sgr', (18, 17, 37.6), (-36, 45, 42), 3.11, +1.56),
    (6859, 'del Sgr', (18, 20, 59.7), (-29, 49, 41), 2.70, +1.38),
    (6913, 'lam Sgr', (18, 27, 58.2), (-25, 25, 18), 2.81, +1.04),
    (7039, 'phi Sgr', (18, 45, 39.4), (-26, 59, 27), 3.17, -0.11),
    (7056, 'zet1 Lyr', (18, 44, 46.4), (37, 36, 18), 4.36, +0.19),
    (7106, 'bet Lyr', (18, 50, 4.8), (33, 21, 46), 3.45, 0.00),
    (7139, 'del2 Lyr', (18, 54, 30.2), (36, 53, 56), 4.30, +1.68),
    (7178, 'gam Lyr', (18, 58, 56.6), (32, 41, 22), 3.24, -0.05),
    (7194, 'zet Sgr', (19, 2, 36.7), (-29, 52, 49), 2.60, +0.08),
    (7234, 'tau Sgr', (19, 6, 56.4), (-27, 40, 14), 3.32, +1.19),
    (7235, 'zet Aql', (19, 5, 24.6), (13, 51, 48), 2.99, +0.01),
    (7236, 'lam Aql', (19, 6, 14.9), (-4, 52, 57), 3.44, -0.09),
    (7264, 'pi Sgr', (19, 9, 45.8), (-21, 1, 25), 2.89, +0.35),
    (7310, 'del Dra', (19, 12, 33.3), (67, 39, 42), 3.07, +1.00),
    (7377, 'del Aql', (19, 25, 29.9), (3, 6, 53), 3.36, +0.32),
    (7417, 'bet1 Cyg', (19, 30, 43.3), (27, 57, 35), 3.08, +1.13),
    (7525, 'gam Aql', (19, 46, 15.6), (10, 36, 48), 2.72, +1.52),
    (7528, 'del Cyg', (19, 44, 58.5), (45, 7, 51), 2.87, -0.03),
    (7570, 'eta Aql', (19, 52, 28.4), (1, 0, 20), 3.90, +0.89),
    (7602, 'bet Aql', (19, 55, 18.8), (6, 24, 24), 3.71, +0.86),
    (7710, 'tet Aql', (20, 11, 18.3), (0, 49, 17), 3.23, -0.07),
    (7754, 'alf2 Cap', (20, 18, 3.3), (-12, 32, 41), 3.57, +0.94),
    (7776, 'bet Cap', (20, 21, 0.7), (-14, 46, 53), 3.08, +0.79),
    (7913, 'bet Pav', (20, 44, 57.5), (-66, 12, 11), 3.42, +0.16),
    (7949, 'eps Cyg', (20, 46, 12.7), (33, 58, 13), 2.46, +1.03),
    (8115, 'zet Cyg', (21, 12, 56.2), (30, 13, 37), 3.20, +0.99),
    (8162, 'alf Cep', (21, 18, 34.8), (62, 35, 8), 2.44, +0.22),
    (8232, 'bet Aqr', (21, 31, 33.5), (-5, 34, 16), 2.91, +0.83),
    (8238, 'bet Cep', (21, 28, 39.6), (70, 33, 39), 3.23, -0.22),
    (8278, 'gam Cap', (21, 40, 5.5), (-16, 39, 44), 3.68, +0.32),
    (8308, 'eps Peg', (21, 44, 11.2), (9, 52, 30), 2.39, +1.53),
    (8322, 'del Cap', (21, 47, 2.4), (-16, 7, 38), 2.87, +0.29),
    (8353, 'gam Gru', (21, 53, 55.7), (-37, 21, 54), 3.01, -0.12),
    (8414, 'alf Aqr', (22, 5, 47.0), (0, 19, 11), 2.96, +0.98),
    (8450, 'tet Peg', (22, 10, 12.0), (6, 11, 52), 3.53, +0.08),
    (8465, 'zet Cep', (22, 10, 51.3), (58, 12, 4), 3.35, +1.57),
    (8502, 'alf Tuc', (22, 18, 30.1), (-60, 15, 35), 2.86, +1.39),
    (8556, 'del1 Gru', (22, 29, 16.2), (-43, 29, 44), 3.97, +1.03),
    (8571, 'del Cep', (22, 29, 10.3), (58, 24, 55), 3.75, +0.60),
    (8634, 'zet Peg', (22, 41, 27.7), (10, 49, 53), 3.40, -0.09),
    (8650, 'eta Peg', (22, 43, 0.1), (30, 13, 17), 2.94, +0.86),
    (8675, 'eps Gru', (22, 48, 33.3), (-51, 19, 1), 3.49, +0.08),
    (8684, 'mu Peg', (22, 50, 0.2), (24, 36, 6), 3.48, +0.93),
    (8694, 'iot Cep', (22, 49, 40.8), (66, 12, 2), 3.52, +1.05),
    (8709, 'del Aqr', (22, 54, 39.0), (-15, 49, 15), 3.27, +0.05),
    (8775, 'bet Peg', (23, 3, 46.5), (28, 4, 58), 2.42, +1.67),
    (8781, 'alf Peg', (23, 4, 45.7), (15, 12, 19), 2.49, -0.04),
    (8974, 'gam Cep', (23, 39, 20.8), (77, 37, 57), 3.21, +1.03),
)
# Declinations of -0 deg: the sign is carried by the minutes.
NEGATIVE_ZERO = {'MINTAKA', 'ZET VIR', 'TET AQL', 'ALF AQR', 'ETA VIR'}

LANDMARKS = {'POLARIS': 1, 'ACRUX': 2}
LANDMARK_NAMES = {1: 'POLARIS', 2: 'SOUTHERN CROSS'}
CROSS = ('ACRUX', 'MIMOSA', 'GACRUX', 'IMAI')
PRIORITY = ('POLARIS',) + CROSS
# Figures the player steers by (docs/STARS.md section 14): every star of a
# figure is class 0, selected and drawn in every night mood, whatever its
# magnitude; the other stars are fillers (class 1 below V 3.0, else 2).
FIGURES = {
    'UMa': ['alf UMa', 'bet UMa', 'gam UMa', 'del UMa', 'eps UMa', 'zet UMa', 'eta UMa'],
    'UMi': ['alf UMi', 'bet UMi', 'gam UMi', 'del UMi', 'eps UMi', 'zet UMi', 'eta UMi'],
    'Cas': ['alf Cas', 'bet Cas', 'gam Cas', 'del Cas', 'eps Cas'],
    'Cep': ['alf Cep', 'bet Cep', 'gam Cep', 'del Cep', 'zet Cep', 'iot Cep'],
    'Dra': ['bet Dra', 'gam Dra', 'del Dra', 'zet Dra', 'eta Dra', 'iot Dra'],
    'Per': ['alf Per', 'bet Per', 'gam Per', 'del Per', 'eps Per', 'zet Per', 'rho Per'],
    'And': ['alf And', 'bet And', 'gam And', 'del And'],
    'Peg': ['alf Peg', 'bet Peg', 'gam Peg', 'eps Peg', 'zet Peg', 'eta Peg', 'tet Peg', 'mu Peg'],
    'Ari': ['alf Ari', 'bet Ari', 'gam Ari'],
    'Tau': ['alf Tau', 'bet Tau', 'gam Tau', 'del1 Tau', 'eps Tau', 'zet Tau', 'tet2 Tau', 'eta Tau'],
    'Aur': ['alf Aur', 'bet Aur', 'eps Aur', 'eta Aur', 'tet Aur', 'iot Aur'],
    'Ori': ['alf Ori', 'bet Ori', 'gam Ori', 'del Ori', 'eps Ori', 'zet Ori', 'kap Ori', 'lam Ori', 'iot Ori'],
    'Gem': ['alf Gem', 'bet Gem', 'gam Gem', 'del Gem', 'eps Gem', 'zet Gem', 'eta Gem', 'tet Gem', 'iot Gem', 'kap Gem', 'lam Gem', 'mu Gem', 'ksi Gem', 'tau Gem', 'ups Gem'],
    'CMa': ['alf CMa', 'bet CMa', 'del CMa', 'eps CMa', 'zet CMa', 'eta CMa', 'omi2 CMa'],
    'CMi': ['alf CMi', 'bet CMi'],
    'Lep': ['alf Lep', 'bet Lep', 'eps Lep', 'mu Lep'],
    'Leo': ['alf Leo', 'bet Leo', 'gam Leo', 'del Leo', 'eps Leo', 'zet Leo', 'eta Leo', 'tet Leo', 'mu Leo'],
    'Boo': ['alf Boo', 'bet Boo', 'gam Boo', 'del Boo', 'eps Boo', 'eta Boo', 'rho Boo'],
    'CrB': ['alf CrB', 'bet CrB', 'gam CrB', 'del CrB', 'eps CrB', 'tet CrB'],
    'Vir': ['alf Vir', 'bet Vir', 'gam Vir', 'del Vir', 'eps Vir', 'zet Vir', 'eta Vir'],
    'Crv': ['alf Crv', 'bet Crv', 'gam Crv', 'del Crv', 'eps Crv'],
    'Her': ['alf1 Her', 'bet Her', 'del Her', 'eps Her', 'zet Her', 'eta Her', 'mu Her', 'pi Her'],
    'Oph': ['alf Oph', 'bet Oph', 'del Oph', 'eps Oph', 'zet Oph', 'eta Oph', 'kap Oph', 'nu Oph'],
    'Lyr': ['alf Lyr', 'bet Lyr', 'gam Lyr', 'del2 Lyr', 'zet1 Lyr'],
    'Cyg': ['alf Cyg', 'bet1 Cyg', 'gam Cyg', 'del Cyg', 'eps Cyg', 'zet Cyg'],
    'Aql': ['alf Aql', 'bet Aql', 'gam Aql', 'del Aql', 'zet Aql', 'eta Aql', 'tet Aql', 'lam Aql'],
    'Sco': ['alf Sco', 'bet1 Sco', 'del Sco', 'eps Sco', 'zet2 Sco', 'eta Sco', 'tet Sco', 'iot1 Sco', 'kap Sco', 'lam Sco', 'mu1 Sco', 'nu Sco', 'pi Sco', 'sig Sco', 'tau Sco', 'ups Sco', 'HR 6630'],
    'Sgr': ['gam2 Sgr', 'del Sgr', 'eps Sgr', 'zet Sgr', 'eta Sgr', 'lam Sgr', 'pi Sgr', 'sig Sgr', 'tau Sgr', 'phi Sgr'],
    'Cap': ['alf2 Cap', 'bet Cap', 'gam Cap', 'del Cap'],
    'Aqr': ['alf Aqr', 'bet Aqr', 'del Aqr'],
    'Cru': ['alf Cru', 'bet Cru', 'gam Cru', 'del Cru', 'eps Cru'],
    'Cen': ['alf Cen', 'bet Cen', 'gam Cen', 'del Cen', 'eps Cen', 'zet Cen', 'eta Cen', 'tet Cen', 'iot Cen'],
    'Lup': ['alf Lup', 'bet Lup', 'gam Lup', 'del Lup', 'eps Lup', 'zet Lup', 'eta Lup'],
    'Ara': ['alf Ara', 'bet Ara', 'gam Ara', 'zet Ara'],
    'TrA': ['alf TrA', 'bet TrA', 'gam TrA'],
    'Car': ['alf Car', 'bet Car', 'eps Car', 'iot Car', 'tet Car', 'ups Car', 'ome Car'],   # False Cross: eps, iot Car + kap, del Vel
    'Vel': ['gam2 Vel', 'del Vel', 'kap Vel', 'lam Vel', 'mu Vel'],
    'Gru': ['alf Gru', 'bet Gru', 'gam Gru', 'del1 Gru', 'eps Gru'],
    'Phe': ['alf Phe', 'bet Phe', 'gam Phe'],
    'Hyi': ['alf Hyi', 'bet Hyi', 'gam Hyi'],
    'Pav': ['alf Pav', 'bet Pav'],
    'Mus': ['alf Mus', 'bet Mus'],
}
FIGURE_STARS = frozenset(b for l in FIGURES.values() for b in l)
WHITE, YELLOW, BLUE, FAINT = 0, 1, 2, 3   # looks: tints of the 2-row stars, grey 1-row star
FIRST_MAGNITUDE, TINTED = 1.5, 3.0       # V limits: 3 rows (two entries); tinted 2 rows
UNITS = 560                     # view azimuth units per turn (src/wild.s)
RA_UNITS = 4 * UNITS            # right ascension: quarter view units per turn
RECORD = 3
EPOCH = 1985.0


def star_class_of(v, figure):
    """Selection class: 0 figures and every star brighter than 2.0 (the lone
    landmarks: Canopus, Achernar, Fomalhaut...), 1 fillers below 3.0, else 2."""
    return 0 if figure or v < 2.0 else 1 if v < 3.0 else 2


def look(v, bv):
    """Pixel of the star (src/stars_draw.s): 2 rows in the tint of B-V
    below V 3.0 (the first magnitude adds a second entry one row below:
    3 rows), else one grey row."""
    if v >= TINTED:
        return FAINT
    return YELLOW if bv >= 0.70 else BLUE if bv <= -0.10 else WHITE


def degrees(name, ra, dec):
    """J2000 (RA, Dec) in degrees."""
    h, m, s = ra
    d, dm, ds = dec
    sign = -1 if d < 0 or (d == 0 and name in NEGATIVE_ZERO) else 1
    return 15 * (h + m / 60 + s / 3600), sign * (abs(d) + dm / 60 + ds / 3600)


def precess(ra, dec, epoch=EPOCH):
    """J2000.0 -> mean equinox of `epoch` (IAU 1976; Meeus eq. 21.3/21.4)."""
    t = (epoch - 2000.0) / 100.0
    zeta = (2306.2181 * t + 0.30188 * t * t + 0.017998 * t ** 3) / 3600
    z = (2306.2181 * t + 1.09468 * t * t + 0.018203 * t ** 3) / 3600
    theta = (2004.3109 * t - 0.42665 * t * t - 0.041833 * t ** 3) / 3600
    a, d = math.radians(ra), math.radians(dec)
    zr, tr = math.radians(zeta), math.radians(theta)
    A = math.cos(d) * math.sin(a + zr)
    B = math.cos(tr) * math.cos(d) * math.cos(a + zr) - math.sin(tr) * math.sin(d)
    C = math.sin(tr) * math.cos(d) * math.cos(a + zr) + math.cos(tr) * math.sin(d)
    return (math.degrees(math.atan2(A, B)) + z) % 360, math.degrees(math.asin(C))


def sources():
    """(name, bayer, ra, dec, v, bv, source) of both tables, J2000."""
    out = [(name, bayer, ra, dec, v, bv, 'Hipparcos') for name, bayer, ra, dec, v, bv in STARS]
    for hr, bayer, ra, dec, v, bv in EXTRA:
        out.append((bayer.upper(), bayer, ra, dec, v, bv, f'BSC5 HR {hr}'))
    return out


def stars():
    """[dict] in selection order (PRIORITY, then class, then magnitude):
    name, ra/dec (1985.0, degrees), v, bv, figure, cls, look, big, landmark,
    ra_q, dec_u, south and the 3 encoded bytes."""
    out = []
    for name, bayer, ra, dec, v, bv, source in sources():
        r0, d0 = degrees(name, ra, dec)
        r, d = precess(r0, d0)
        ra_q = round(r / 360 * RA_UNITS) % RA_UNITS
        dec_u = round(abs(d) * UNITS / 360)
        assert 0 <= dec_u <= 140
        figure = bayer in FIGURE_STARS
        cls, lk, big = star_class_of(v, figure), look(v, bv), int(v < FIRST_MAGNITUDE)
        mark, south = LANDMARKS.get(name, 0), int(d < 0)
        out.append(dict(name=name, bayer=bayer, source=source, ra=r, dec=d, ra2000=r0, dec2000=d0,
                        v=v, bv=bv, figure=figure, cls=cls, look=lk, big=big, landmark=mark,
                        ra_q=ra_q, dec_u=dec_u, south=south,
                        record=bytes((ra_q & 255, south << 7 | big << 6 | lk << 4 | ra_q >> 8,
                                      dec_u))))
    # Selection priority: Polaris and the four stars of the Cross first (when
    # more stars are up than the list holds, Delta Crucis would otherwise be
    # dropped before the brighter ones), then the figures and the stars
    # brighter than 2.0 (class 0), the fillers of class 1, then 2, each by
    # magnitude (stable): a crowded sky drops fillers, never a figure.
    out.sort(key=lambda s: (s['name'] not in PRIORITY, s['cls'], s['v']))
    return out


def class_layout(cat):
    """(PRIORITY_CLASSES, CLASS_STARTS): the classes of the priority stars,
    and the first index of class 1 and of class 2 after them."""
    n = len(PRIORITY)
    rest = [s['cls'] for s in cat[n:]]
    assert rest == sorted(rest), 'classes follow the selection order'
    return (tuple(s['cls'] for s in cat[:n]),
            tuple(n + next(i for i, c in enumerate(rest) if c >= k) for k in (1, 2)))


def star_class(index, layout):
    """Selection class of the star at `index` (what the 6502 derives)."""
    prio, (k1, k2) = layout
    if index < len(prio):
        return prio[index]
    return 0 if index < k1 else 1 if index < k2 else 2


def encode():
    """The catalogue bytes, 3 per star, in selection order."""
    return b''.join(s['record'] for s in stars())


if __name__ == '__main__':
    cat = stars()
    print(f'{len(cat)} stars, {len(encode())} bytes, classes {class_layout(cat)}')
    for k, s in enumerate(cat):
        print(f"{k:3} {s['name']:12} V={s['v']:5.2f} cls={s['cls']} look={s['look']} big={s['big']} "
              f"RA={s['ra']:7.3f} Dec={s['dec']:+7.3f}  {s['record'].hex()}  {s['source']}")
