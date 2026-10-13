"""Independent billboard projection and foreground occlusion reference.

Terrain pixels come from view_ref. Original sprite samples are composed only
above the terrain frontier reached before the billboard's distance plane.
"""
import math
from common import HERE, view_ref
from re_graphics import decode

ASSETS = {5:'wreck',6:'bear',7:'cougar',8:'rattlesnake',9:'cabin'}
IMAGES, BASES = {}, {}


def use_region(region=2):
    """Animal sprites of a region (lot 7): overlays 6..8, then module 23."""
    import dhgr_palette as P
    names = P.region_assets(region)
    ASSETS.clear()
    ASSETS.update({asset: name for asset, name in zip((5, 6, 7, 8, 9, 23), names) if name})
    IMAGES.clear()
    IMAGES.update({key: decode((HERE/f'build/original_graphics/{name}.bin').read_bytes())[0]
                   for key, name in ASSETS.items()})
    BASES.clear()
    BASES.update({key: max(y for y, row in enumerate(im) if any(c >= 0 for c in row))
                  for key, im in IMAGES.items()})


use_region(2)


def select(m, px, py, heading, animal=None):
    startx,starty=(int.from_bytes(m[o:o+2],'little') for o in (2,4))
    sites=[(5,startx,starty,int.from_bytes(m[6:8],'little'))]
    if m[16]: sites.append((9,m[17]*256+128,m[18]*256+128,int.from_bytes(m[19:21],'little')))
    locals_=sites+([animal] if animal else [])
    for asset,x,y,bearing in locals_:
        if (x>>8,y>>8)==(px>>8,py>>8):
            return geometry(asset,bearing,0,0,0,heading)
    result=None
    eye=(m[64+(py>>8)*112+(px>>8)]&127)+2
    for asset,x,y,_ in sites:
        east,north=(x-px)/256,(y-py)/256
        distance=math.hypot(east,north)
        if distance >= 8: continue
        depth=math.floor(distance)+1
        bearing=math.floor(math.atan2(east,north)*560/(2*math.pi)+.5)%560
        shift=depth.bit_length()-1
        dz=(m[64+(y>>8)*112+(x>>8)]&127)-eye
        q=(abs(dz)*256)//depth
        anchor=max(0,95-((q*3)>>4)) if dz>=0 else 95+((q*3+15)>>4)
        if anchor >= 252: continue
        g=geometry(asset,bearing,depth,shift,anchor,heading)
        if g['left']>=140 or g['left']+g['width']<=0: continue
        if result is None or depth < result['depth']: result=g
    return result


def geometry(asset,bearing,depth,shift,anchor,heading):
    width=(len(IMAGES[asset][0])+(1<<shift)-1)>>shift
    left=70-width//2+(bearing-heading+280)%560-280
    return dict(asset=asset,bearing=bearing,depth=depth,shift=shift,anchor=anchor,
                left=left,width=width)


def foreground(m,px,py,heading,col,depth):
    dx,dy=view_ref.direction(heading-70+col)
    eye=(m[64+(py>>8)*112+(px>>8)]&127)+2
    top,thr,inc=160,-32768,0
    for n in range(1,depth):
        px,py=(px+dx)&65535,(py+dy)&65535
        if px>>8>=112 or py>>8>=84: break
        dz=(m[64+(py>>8)*112+(px>>8)]&127)-eye
        thr+=inc
        if thr>32767: break
        thr=max(thr,-32768)
        if dz<=thr>>8: continue
        q=(abs(dz)*256)//n
        inc=-q if dz<0 else q
        thr=dz*256
        if inc>=512: row=0
        elif inc < -512: continue
        else:
            off=min((inc*3)>>4,95)
            if off < -64: continue
            row=95-off
        top=min(top,row)
        if top==0: break
    return top


def render(m,px,py,heading,animal=None):
    page=bytearray(view_ref.render(m,px,py,heading))
    g=select(m,px,py,heading,animal)
    if not g: return bytes(page)
    im=IMAGES[g['asset']]
    base=BASES[g['asset']]
    stride=1<<g['shift']
    for col in range(max(0,g['left']),min(140,g['left']+g['width'])):
        source=(col-g['left'])*stride
        front=foreground(m,px,py,heading,col,g['depth']) if g['depth'] else 160
        for y,row in enumerate(im):
            colour=row[source]
            if colour<0: continue
            if g['depth']:
                if (base-y)%stride: continue
                out=g['anchor']-(base-y)//stride
            else: out=y-(0 if g['asset']==5 else 10)
            if not 0<=out<front: continue
            for bit in (0,1):
                pixel=2*col+bit
                off=out*40+pixel//7
                if out<view_ref.HUD_ROWS: continue
                mask=1<<(pixel%7)
                page[off]=(page[off]&~mask)|(mask if colour&(1<<bit) else 0)
    return bytes(page)
