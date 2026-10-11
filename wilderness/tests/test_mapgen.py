#!/usr/bin/env python3
"""Hydrology invariants: actual pits, outlets, connected conversion and dry sites."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import mkmap


class Source:
    def __init__(self,x,y):self.values=iter(((x-20+.25)/184,(y-20+.25)/128))
    def random(self):return next(self.values)


def terrain(height=10):
    m=mkmap.Map.__new__(mkmap.Map)
    m.seed=7;m.start=(190,145);m.goal=(185,140)
    m.h=[[height]*mkmap.W for _ in range(mkmap.H)]
    m.water=[[False]*mkmap.W for _ in range(mkmap.H)]
    return m


def check_paths(m):
    for path in m.river_paths:
        assert len(path)==len(set(path)), 'river loop'
        for (x,y),(xx,yy) in zip(path,path[1:]):
            assert max(abs(x-xx),abs(y-yy))==1
            assert m.water[y][x] and m.water[yy][xx]
            assert m.h[yy][xx]<=m.h[y][x], ('uphill',x,y,xx,yy)
        x,y=path[-1]
        assert m.water[y][x]
        assert x in (0,mkmap.W-1) or y in (0,mkmap.H-1) or len(path)>1
    grid=mkmap.coarse_grid(m.h,m.water)
    for x,y in (m.start,m.goal):
        assert not grid[(y//2)*mkmap.GW+x//2]&128
    if m.river_paths:
        # Every traced river also remains connected after the 2x2 conversion.
        for path in m.river_paths:
            coarse=[(x//2,y//2) for x,y in path]
            for (x,y),(xx,yy) in zip(coarse,coarse[1:]):
                assert max(abs(x-xx),abs(y-yy))<=1
                assert grid[y*mkmap.GW+x]&128 and grid[yy*mkmap.GW+xx]&128
                assert (grid[yy*mkmap.GW+xx]&127)<=(grid[y*mkmap.GW+x]&127)
    remaining={(x,y) for y,row in enumerate(m.water) for x,wet in enumerate(row) if wet}
    while remaining:
        first=remaining.pop();pending=[first];reaches_edge=False
        while pending:
            x,y=pending.pop()
            reaches_edge |= x in (0,mkmap.W-1) or y in (0,mkmap.H-1)
            for dx,dy in mkmap.NEIGHBORS:
                p=(x+dx,y+dy)
                if p in remaining:
                    remaining.remove(p);pending.append(p)
        assert reaches_edge, 'water component disconnected from its drainage outlet'


def main():
    m=terrain(0);m.rnd=Source(100,80);m.rivers(1)
    assert sum(map(sum,m.water))<200, 'flat plateau incorrectly became a lake'
    assert set(v for row in m.h for v in row)=={0}
    check_paths(m)
    print('flat terrain drains to an edge without an artificial lake: OK')

    for width in (3,41):
        m=terrain();m.rnd=Source(60,60)
        for y in range(59,59+width):
            for x in range(59,59+width):m.h[y][x]=2
        m.rivers(1)
        assert all(m.water[y][x] and m.h[y][x]==10
                   for y in range(59,59+width) for x in range(59,59+width))
        check_paths(m)
    print('small and >300-unit basins fill entirely to a flat spill surface: OK')

    m=terrain()
    # Source must fit the original source rectangle; protect an interior site.
    m.start=(100,80);m.rnd=Source(100,80);m.rivers(1)
    assert not any(map(any,m.water)), 'protected source was erased after breaking a river'
    print('streams covering crash/rangers are rejected before changing the terrain: OK')

    m=terrain(30)
    for x in range(21,182):m.water[81][x]=True;m.h[81][x]=5
    grid=mkmap.coarse_grid(m.h,m.water)
    assert all(grid[40*mkmap.GW+x]==133 for x in range(10,91))
    assert sum(bool(v&128) for v in grid)==81
    assert grid[39*mkmap.GW+50]==30
    b=mkmap.map_bin(m.h,m.water,(40,40),(180,140),0)
    assert not b[64+b[18]*mkmap.GW+b[17]]&128, 'cabin placed in converted water'
    print('one-unit river at odd coordinates survives conversion at its water height: OK')

    for seed in (1,2,7,42,1985,9999):
        for level in (1,4,10):
            m=mkmap.Map(seed,level);check_paths(m)
            assert m.river_paths, (seed,level,'no rivers')
            first=mkmap.map_bin(m.h,m.water,m.start,m.goal,0,level)
            n=mkmap.Map(seed,level)
            assert first==mkmap.map_bin(n.h,n.water,n.start,n.goal,0,level)
    print('18 seed/difficulty maps: deterministic, downhill connected rivers and dry sites: OK')


if __name__=='__main__':main()
