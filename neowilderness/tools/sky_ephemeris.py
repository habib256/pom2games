#!/usr/bin/env python3
"""Low precision Sun/Moon equatorial coordinates, Paul Schlyter's algorithm.
Source: https://stjarnhimlen.se/comp/ppcomp.html (sections 4-9, 12).
Lunar perturbations included. Tables use 1985 as a documented reference year.
"""
import datetime as dt
import math
import sys
from pathlib import Path

YEAR = 1985
TAU = 2 * math.pi

def sind(x): return math.sin(math.radians(x))
def cosd(x): return math.cos(math.radians(x))

def orbit(d, lunar=False):
    if lunar:
        node, inc, peri, a, e, mean = (125.1228-.0529538083*d, 5.1454,
            318.0634+.1643573223*d, 60.2666, .0549, 115.3654+13.0649929509*d)
    else:
        node, inc, peri, a, e, mean = (0, 0, 282.9404+.0000470935*d,
            1, .016709-.000000001151*d, 356.0470+.9856002585*d)
    m = math.radians(mean % 360)
    ecc = m
    for _ in range(8):
        ecc -= (ecc-e*math.sin(ecc)-m)/(1-e*math.cos(ecc))
    xv, yv = a*(math.cos(ecc)-e), a*math.sqrt(1-e*e)*math.sin(ecc)
    v, r = math.degrees(math.atan2(yv,xv)), math.hypot(xv,yv)
    x = r*(cosd(node)*cosd(v+peri)-sind(node)*sind(v+peri)*cosd(inc))
    y = r*(sind(node)*cosd(v+peri)+cosd(node)*sind(v+peri)*cosd(inc))
    z = r*sind(v+peri)*sind(inc)
    lon, lat = math.degrees(math.atan2(y,x)), math.degrees(math.atan2(z,math.hypot(x,y)))
    if lunar:
        ms = 356.0470+.9856002585*d
        ls = ms+282.9404+.0000470935*d
        lm = mean+peri+node
        elong, arg = lm-ls, lm-node
        lon += (-1.274*sind(mean-2*elong)+.658*sind(2*elong)-.186*sind(ms)
            -.059*sind(2*mean-2*elong)-.057*sind(mean-2*elong+ms)
            +.053*sind(mean+2*elong)+.046*sind(2*elong-ms)+.041*sind(mean-ms)
            -.035*sind(elong)-.031*sind(mean+ms)-.015*sind(2*arg-2*elong)
            +.011*sind(mean-4*elong))
        lat += (-.173*sind(arg-2*elong)-.055*sind(mean-arg-2*elong)
            -.046*sind(mean+arg-2*elong)+.033*sind(arg+2*elong)+.017*sind(2*mean+arg))
        r += -.58*cosd(mean-2*elong)-.46*cosd(2*elong)
    obliq = 23.4393-.0000003563*d
    x, y, z = cosd(lon)*cosd(lat), sind(lon)*cosd(lat), sind(lat)
    ye, ze = y*cosd(obliq)-z*sind(obliq), y*sind(obliq)+z*cosd(obliq)
    return math.atan2(ye,x)%TAU, math.atan2(ze,math.hypot(x,ye)), math.radians(lon)%TAU, r

def entry(day):
    d = (dt.date(YEAR,1,1)-dt.date(1999,12,31)).days + day
    sun, moon = orbit(d), orbit(d,True)
    return (round((moon[0]-sun[0])%TAU/TAU*256)%256,
            round(math.degrees(moon[1])*4)&255,
            round((moon[2]-sun[2])%TAU/TAU*256)%256)

def write(path):
    lines = ['; Generated lunar ephemeris: 1985, UT, every two days; RA offset, quarter-degree declination, phase.']
    data = [v for day in range(0,369,2) for v in entry(day)]
    lines.append('sky_ephemeris:')
    for i in range(0,len(data),15):
        lines.append('        .byte '+','.join(str(v) for v in data[i:i+15]))
    Path(path).write_text('\n'.join(lines)+'\n')

if __name__ == '__main__': write(sys.argv[1])
