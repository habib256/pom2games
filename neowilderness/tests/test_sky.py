#!/usr/bin/env python3
"""Geographic bearings, astronomical altitude, lunar motion, occlusion and pans.

DHGR: sun_alt8 / moon_alt8 (round(128 sin altitude)) follow the model too, and
frames are compared pixel for pixel with tools/dhgr_ref.view in the mood of
the frame, the sun or Moon drawn at the bearing/row the game computed.
"""
import math
import tempfile
from common import HERE,L,DISK,a2test,fp,hgr_rows,disk_with,dhgr,dhgr_view,dhgr_scene,mood_name
from test_thermal import call,poke
from sky_ephemeris import entry

TAU=2*math.pi

def model(latitude,date,hour,moon=False,longitude=-120):
    h=(hour-12)*math.pi/12
    if moon:
        interval=(math.floor(date*365)+hour/24-longitude/360)/2
        sample=math.floor(interval); f=interval-sample
        first,second=entry(sample*2),entry((sample+1)*2)
        values=[]
        for i,(a,b) in enumerate(zip(first,second)):
            delta=(b-a+128)%256-128
            if i==1: a=(a+128)%256-128
            values.append(a+delta*f)
        h-=values[0]*TAU/256
        dec=math.radians(values[1]/4)
    else:
        dec=math.asin(.398*math.sin(TAU*date-1.378))
    lat=math.radians(latitude)
    east=-math.cos(dec)*math.sin(h)
    north=math.sin(dec)*math.cos(lat)-math.cos(dec)*math.cos(h)*math.sin(lat)
    up=math.sin(dec)*math.sin(lat)+math.cos(dec)*math.cos(h)*math.cos(lat)
    if moon: up-=math.sqrt(max(0,1-up*up))*math.pi/180
    bearing=round(math.atan2(east,north)/TAU*560)%560
    height=48*up/math.hypot(east,north) if math.hypot(east,north)>1e-9 else 1e9
    y=255 if up<=0 or height>=96 else 95-int(height)
    model.alt8=max(-127,min(127,round(128*up)))
    return bearing,y


def positions():
    idle=L.until('idle',20000);done=f'until:{L["idle"]+3:04X}:6000'
    steps=[idle]+call(['env_hour'])+[done,idle]+call(['sky_position'])
    cases=[]
    for moon in (False,True):
        for lat in (-38,0,38):
            for date in (.1,.34442,.5,.9):
                for hour in (0,5,7,10,12,14,17,19,22):
                    cases.append((lat,date,hour,moon))
                    steps+=poke('s_date',date)+poke('s_hour',hour)
                    steps += [f'poke:700C:{lat&255:02X}','poke:7019:88',
                              L.poke('night',int(moon)),done,L.peek('sky_bearing',3),L.peek('sun_alt8',3),idle]
    result=a2test.run(DISK,steps,emulator=a2test.A2SHOT,timeout=1800)
    for k,case in enumerate(cases):
        data,alt=result.dumps[2*k:2*k+2]
        b,y=model(*case)
        actual=int.from_bytes(data[:2],'little');ay=data[2]
        assert ay==y or (ay!=255 and y!=255 and abs(ay-y)<=1),(case,data.hex(),(b,y))
        if y!=255:
            assert abs((actual-b+280)%560-280)<=1,(case,actual,b)
        body,other=(alt[1],alt[0]) if case[3] else (alt[0],alt[1])
        assert other==0x80,(case,alt.hex(),'the other body is not computed')
        assert abs(((body+128)&255)-128-model.alt8)<=1,(case,alt.hex(),model.alt8)
    print(f'  {len(cases)} solar/lunar positions and S8 altitudes, hemispheres, seasons and hours: OK')


def scenes():
    # Flat land, no sites: isolate the sky and its geographic anchor.
    m=bytearray((HERE/'build/map.bin').read_bytes());m[64:]=bytes([10])*9408
    m[16]=0;m[21]=11;m[2:6]=bytes((0,20,0,20));m[6:8]=(140).to_bytes(2,'little')
    steps=[L.until('idle',20000),L.poke('scenes_enabled',0),
           L.poke('heading',140),L.poke('heading',0,1),'key:V\\r','wait:1',
           L.until('idle',20000),L.peek('sky_bearing',3),L.peek('sky_mood'),'peek:2000:8192',
           f'shot:{HERE}/build/sky-sun.png']
    # Pan a full turn, then compare with a full redraw at each bearing.
    for _ in range(16):
        steps += ['press:\\>',L.until('idle',20000),'peek:2000:8192',
                  'key:V\\r','wait:1',L.until('idle',20000),'peek:2000:8192']
    # Clouds must erase the sun; return to clear weather restores it.
    steps += [L.poke('weather_sky',1),'key:V\\r','wait:1',L.until('idle',20000),
              L.peek('sky_mood'),'peek:2000:8192',L.poke('weather_sky',0)]
    # A high foreground ridge blocks every sky row containing the sun.
    steps += [f'poke:{0x7000+64+x*112+21:04X}:7D' for x in range(84)]
    steps += ['key:V\\r','wait:1',L.until('idle',20000),'peek:2000:8192']
    with tempfile.TemporaryDirectory() as tmp:
        disk=disk_with(tmp,bytes(m));result=a2test.run(disk,steps,emulator=a2test.A2SHOT,timeout=1800)
    R=dhgr()
    b,y=model(38,.34442,7)
    sky=result.dumps[0]
    assert abs(int.from_bytes(sky[:2],'little')-b)<=1
    mood=mood_name(result.dumps[1])
    sun=R.Sky(mood_name=mood,body=(int.from_bytes(sky[:2],'little'),sky[2]))
    base=dhgr_scene(m,20*256,20*256,140,mood,sprites=False)
    page=dhgr_view(result.dumps[2])
    assert page!=base,'visible sun missing'
    assert page==dhgr_scene(m,20*256,20*256,140,mood,sprites=False,sky=sun),'sun pixels'
    for i in range(16):
        assert result.dumps[3+2*i]==result.dumps[4+2*i],('pan/full sky mismatch',i)
    cloudy=mood_name(result.dumps[-3])
    assert dhgr_view(result.dumps[-2])==dhgr_scene(m,20*256,20*256,140,cloudy,sprites=False),'clouds did not mask sun'
    ridge=bytearray(m)
    for x in range(84):ridge[64+x*112+21]=125
    assert dhgr_view(result.dumps[-1])==dhgr_scene(ridge,20*256,20*256,140,mood,sprites=False),'sun leaks through ridge'
    print(f'  sun drawn ({mood}), cloud ({cloudy})/terrain masks and full-turn pan/full redraw equality: OK')


def moon_scene():
    m=bytearray((HERE/'build/map.bin').read_bytes());m[64:]=bytes([10])*9408
    m[16]=0;m[21]=11;m[2:6]=bytes((0,20,0,20))
    # A partial phase with the Moon above the horizon; the saved May date
    # is now allowed to reveal the landscape when its disk is full.
    date=.01/365
    bearing,y=model(38,date,0,True)
    original=(HERE/'build/wildgame.bin').read_bytes()[L['idle']-0x4000:L['idle']-0x4000+9]
    steps=[L.until('idle',20000),L.poke('scenes_enabled',0)]
    steps+=poke('s_date',date)+poke('s_hour',0)+[L.poke('heading',bearing),L.poke('heading',bearing>>8,1)]
    steps+=call(['env_hour','show_view'])+[f'until:{L["idle"]+6:04X}:20000',
        L.peek('sky_bearing',3),L.peek('sky_mood'),L.peek('sun_alt8',3),L.peek('sky_waxing'),'peek:2000:8192',
        f'shot:{HERE}/build/sky-moon.png',L.until('idle',20000)]
    steps += [L.poke('idle',b,i) for i,b in enumerate(original)]+[L.poke('sim_loaded',0)]
    for _ in range(16):
        steps+=['press:\\>',L.until('idle',20000),'peek:2000:8192',
                'key:V\\r','wait:1',L.until('idle',20000),'peek:2000:8192']
    steps += [L.poke('weather_sky',1),'key:V\\r','wait:1',L.until('idle',20000),'peek:2000:8192']
    with tempfile.TemporaryDirectory() as tmp:
        result=a2test.run(disk_with(tmp,bytes(m)),steps,emulator=a2test.A2SHOT,timeout=1800)
    actual=int.from_bytes(result.dumps[0][:2],'little')
    assert abs(actual-bearing)<=1,(actual,bearing)
    assert abs(result.dumps[0][2]-y)<=1
    mood=mood_name(result.dumps[1]);alt=result.dumps[2];waxing=result.dumps[3][0]
    assert mood=='night dark' and alt[2]<11,(mood,alt.hex(),'a partial phase leaves the night dark')
    R=dhgr()
    # Lot 7 step 5: the stars of that night (1 January 0 h) are drawn too,
    # with the Moon's disc removed from the list (tools/stars_ref).
    import stars_ref
    lat,lon=((b+128)%256-128 for b in (m[12],m[25]))
    stars=tuple(stars_ref.visible(0,0,lat,lon,(actual,result.dumps[0][2])))
    moon=R.Sky(night=True,mood_name=mood,body=(actual,result.dumps[0][2]),phase=alt[2],
               waxing=bool(waxing),moon8=(alt[1]+128)%256-128,stars=stars)
    page=dhgr_view(result.dumps[4])
    assert any(any(row) for row in page),'moon missing above horizon'
    assert not any(any(row) for row in page[100:]),'moon revealed terrain at night'
    assert page==R.view(m,20*256,20*256,bearing,moon,forest=True,sprites=False),'moon pixels'
    for i in range(16):assert hgr_rows(result.dumps[5+2*i])==hgr_rows(result.dumps[6+2*i]),('moon pan/full',i)
    # Under clouds only the dark-blue sky of the dark night remains (no Moon, no star).
    import dhgr_palette as P
    assert {c for row in dhgr_view(result.dumps[-1]) for c in row} <= {P.BLACK, P.DARK_BLUE},'clouds did not hide moon'
    print('  dated Moon drawn at its own bearing with the stars of the night, dark terrain, '
          'cloud mask and night rotations: OK')

def afternoon_travel():
    # The real clock with forest rendering catches scratch corruption that
    # isolated sky-position calls cannot detect.
    from test_forest import map_fixture
    steps=[L.until('idle',20000),'key:NATURE 0\\r','wait:1',L.until('idle',20000),
           'key:WALK 456 MIN\\r','wait:1',L.until('idle',60000),
           'key:REST 11 MIN\\r','wait:1',L.until('idle',20000),
           L.peek('s_hour',5),L.peek('s_date',5),L.peek('sky_bearing',3),L.peek('s_elap',5)]
    with tempfile.TemporaryDirectory() as tmp:
        result=a2test.run(disk_with(tmp,map_fixture()),steps,emulator=a2test.A2SHOT,timeout=900)
    hour,date=fp(result.dumps[0]),fp(result.dumps[1])
    assert 14 < hour < 16 and abs(hour-(7+fp(result.dumps[3])))<1e-7,'afternoon travel clock'
    bearing,y=model(38,date,hour)
    actual=result.dumps[2]
    assert abs(int.from_bytes(actual[:2],'little')-bearing)<=1 and abs(actual[2]-y)<=1
    assert actual[2]<50,'afternoon sun incorrectly near the horizon'
    print('  afternoon after real travel through woods: solar position and clock preserved OK')

if __name__=='__main__':
    positions()
    scenes()
    moon_scene()
    afternoon_travel()
