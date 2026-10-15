"""Independent billboard projection and foreground occlusion reference.

Terrain pixels come from view_ref. Original sprite samples are composed only
above the terrain frontier reached before the billboard's distance plane.
"""
import math
from common import HERE, view_ref
from re_graphics import decode

ASSETS = {5:'wreck',6:'bear',7:'cougar',8:'rattlesnake',9:'cabin'}
# Site sprites (lot 6, src/project.s): the shelter, MAP+16 = 1 log, 2 rock
# (the found shelter of a native map, the fixed cabin of a generated one,
# tools/mkmap.py), the ranger outpost at the goal. Asset 9 (the hut of the
# region slots) is no longer drawn: the hut of MAKE HUT is site sprite 37.
SITES = {33:'log',34:'rock',35:'outpost'}
# Lot 3 step 3 (XL only): the built shelters, site sprites 36-39, the tent,
# the hut (cabin.bin), the igloo, the trench, centred on their cell.
SHELTERS = {36:'tent',37:'cabin',38:'igloo',39:'trench'}
SITES.update(SHELTERS)
GROUND = (5,35)                 # local sprites standing on the ground (origin 0)
IMAGES, BASES = {}, {}


def use_region(region=2):
    """Animal sprites of a region (lot 7): overlays 6..8, then module 23."""
    import dhgr_palette as P
    names = P.region_assets(region)
    ASSETS.clear()
    ASSETS.update({asset: name for asset, name in zip((5, 6, 7, 8, 9, 23), names) if name})
    ASSETS.update(SITES)
    IMAGES.clear()
    IMAGES.update({key: decode((HERE/f'build/original_graphics/{name}.bin').read_bytes())[0]
                   for key, name in ASSETS.items()})
    BASES.clear()
    BASES.update({key: max(y for y, row in enumerate(im) if any(c >= 0 for c in row))
                  for key, im in IMAGES.items()})


use_region(2)


def built_shelters(m, cr_sx=(255,)*3, cr_sy=(255,)*3, tent=None):
    """The built shelters PROJECT draws on XL (src/project.s project_site):
    (asset, cell x, cell y) of the hut, igloo and trench made (cr_sx, cr_sy,
    255: never), and of the tent lying on the ground (tent = (x, y), its
    it_x, it_y with it_place 0; None: not on the ground) unless that is the
    cell of the wreck."""
    built=[(37+k,x,y) for k,(x,y) in enumerate(zip(cr_sx,cr_sy)) if x!=255]
    if tent and tuple(tent)!=(m[3],m[5]):
        built.append((36,)+tuple(tent))
    return sorted(built)


def select(m, px, py, heading, animal=None, built=()):
    """The single billboard of the main pass (PROJECT module_project): the
    local site of the cell, else the nearest visible distant site. The
    animal is not a candidate (since 15 October 2026): animal_geometry,
    drawn last over the whole view (PROJECT module_animal); `animal` is
    accepted and ignored. built: built_shelters() (XL; the 140 KB edition
    draws none)."""
    startx,starty=(int.from_bytes(m[o:o+2],'little') for o in (2,4))
    sites=[(5,startx,starty,int.from_bytes(m[6:8],'little'))]
    shelter=32+m[16]
    if m[16]: sites.append((shelter,m[17]*256+128,m[18]*256+128,int.from_bytes(m[19:21],'little')))
    # The outpost: the corner of the goal cell on a native map, else its
    # centre; seen locally from its cell, in front of the player.
    frac=0 if m[37] else 128
    outpost=(35,m[8]*256+frac,m[9]*256+frac,heading)
    made={a:(a,x*256+128,y*256+128,heading) for a,x,y in built}
    # Local order of the original (SURV3D T0D/SE $5F4C): the igloo, the hut,
    # the tent, the natural shelter, the trench, after the wreck and outpost.
    locals_=(sites[:1]+[outpost]+[made[a] for a in (38,37,36) if a in made]+sites[1:]
             +[made[a] for a in (39,) if a in made])
    sites.append(outpost)
    sites+=[made[a] for a in (36,37,38,39) if a in made]   # ties: the first
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


FIRE_WIDTH = 28                 # src/fire.s: the campfire's columns


def animal_geometry(px, py, heading, animal, fire=None, tilt=0):
    """The animal of the player's cell (PROJECT module_animal), or None: no
    animal, another cell, LOOK UP. animal = (asset, x, y, _) in 8.8 cells,
    its bearing ignored: always facing the player, centred (left = 70 -
    width // 2). fire = (cell x, cell y, bearing) of a campfire burning
    (camp.s fire_on, fire_pos): when its 28 columns from 56 + bearing -
    heading (wrapped to -279..280) overlap the animal, the animal goes to
    their right if the fire starts at column 56 or before, else to their
    left (src/project.s animal_fire)."""
    if not animal or tilt > 0:
        return None
    asset, x, y = animal[:3]
    if (x >> 8, y >> 8) != (px >> 8, py >> 8):
        return None
    g = geometry(asset, heading, 0, 0, 0, heading)
    assert g['width'] <= 72, 'OUTDOOR ab_copy keeps 22 bytes per bank and row (AB_MAXN)'
    if fire and (fire[0], fire[1]) == (px >> 8, py >> 8):
        fl = 70 - FIRE_WIDTH // 2 + (fire[2] - heading + 280) % 560 - 280
        al, w = g['left'], g['width']
        assert al >= 30, 'animal_fire: widths up to 80'
        if 0 <= fl < 256:
            if fl <= 56:
                g['left'] = max(al, fl + FIRE_WIDTH)
            elif fl - w < al:
                g['left'] = fl - w
    return g


def geometry(asset,bearing,depth,shift,anchor,heading):
    width=(len(IMAGES[asset][0])+(1<<shift)-1)>>shift
    left=70-width//2+(bearing-heading+280)%560-280
    return dict(asset=asset,bearing=bearing,depth=depth,shift=shift,anchor=anchor,
                left=left,width=width)


def foreground(m,px,py,heading,col,depth,tilt=0):
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
        row=view_ref.sample_row(inc,tilt)
        if row is None: continue
        top=min(top,row)
        if top==0: break
    return top


def render(m,px,py,heading,animal=None,tilt=0,built=(),fire=None):
    """tilt (LOOK UP / DOWN): no sprite looking up; looking down a distant
    billboard follows its terrain (96 rows up), a local one stays put. The
    animal of the cell is drawn last, over everything (animal_geometry)."""
    page=bytearray(view_ref.render(m,px,py,heading,tilt))
    g=None if tilt>0 else select(m,px,py,heading,animal,built)
    if g: paint(page,m,px,py,heading,g,tilt)
    a=animal_geometry(px,py,heading,animal,fire,tilt)
    if a: paint(page,m,px,py,heading,a,tilt)
    return bytes(page)


def paint(page,m,px,py,heading,g,tilt):
    im=IMAGES[g['asset']]
    base=BASES[g['asset']]
    stride=1<<g['shift']
    for col in range(max(0,g['left']),min(140,g['left']+g['width'])):
        source=(col-g['left'])*stride
        front=foreground(m,px,py,heading,col,g['depth'],tilt) if g['depth'] else 160
        for y,row in enumerate(im):
            colour=row[source]
            if colour<0: continue
            if g['depth']:
                if (base-y)%stride: continue
                out=g['anchor']-(base-y)//stride
                if out<0: continue
                out+=view_ref.TILT_ROWS*tilt
            else: out=y-(0 if g['asset'] in GROUND else 10)
            if not 0<=out<front: continue
            for bit in (0,1):
                pixel=2*col+bit
                off=out*40+pixel//7
                if out<view_ref.HUD_ROWS: continue
                mask=1<<(pixel%7)
                page[off]=(page[off]&~mask)|(mask if colour&(1<<bit) else 0)
