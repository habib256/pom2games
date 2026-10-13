"""Independent Sierra predicates and fixtures at both sides of every bound."""
def eligible(species, e):
    season,hour,terrain,altitude,slope,climate = e
    if not 10 <= climate <= 50:
        return False
    if species == 0:
        return (16 <= season <= 84 and (hour < 7 or hour > 15)
                and terrain in (10,20) and 30 <= altitude <= 80 and slope <= 50)
    if species == 1:
        return ((hour < 7 or hour > 17) and terrain in (0,10,20)
                and 10 <= altitude <= 90 and slope <= 70)
    return (33 <= season <= 83 and 6 <= hour <= 18 and terrain in (0,10)
            and altitude <= 80 and slope <= 60)


def cases():
    result = []
    for species, base in enumerate(([50,6,10,50,0,31], [50,6,10,50,0,31], [50,12,10,50,0,31])):
        # Adjacent boundary values, all five terrain groups and extremes.
        for index, values in enumerate((
                (0,15,16,32,33,83,84,85,100),
                (0,5,6,7,15,16,17,18,19,23),
                (0,10,20,30,40),
                (0,9,10,29,30,79,80,81,89,90,91,149),
                (0,49,50,51,59,60,61,69,70,71,125),
                (0,9,10,31,50,51,140))):
            for value in values:
                env = list(base)
                env[index] = value
                result.append((species, env, eligible(species,env)))
    return result


# ---------------------------------------------------------------------------
# Lot 7: the probed records of the six regions (build/regions/fauna.json,
# tools/re_region_fauna_probe.py), read independently of tools/build_disk.py.
TERRAINS = (0, 10, 20, 30, 40)      # rock, clear, woods (high woods), water


def region_records(region):
    import json
    from common import HERE
    doc = json.loads((HERE / 'build/regions/fauna.json').read_text())
    return doc['regions'][str(region)]


def accepts(centre, width, e):
    """Original filter: d = |e - c|; w > 0 needs d <= w, w < 0 d > -w, w = 0 d > 0."""
    d = abs(e - centre)
    return d <= width if width > 0 else d > -width if width < 0 else d > 0


def region_eligible(record, env):
    """Filters of the record, and byte 29: never in water (terrain 40)."""
    pairs = [(f['centre'], f['width']) for f in record['filters']]
    if record['water_gate'] and env[2] == 40:
        return False
    return all(accepts(c, w, e) for (c, w), e in zip(pairs, env))


def region_cases(region):
    """(species index, env, expected) at both sides of every bound of every
    probed species of a region; terrain takes the five codes of the port."""
    result = []
    for k, record in enumerate(region_records(region)['species']):
        pairs = [(f['centre'], f['width']) for f in record['filters']]
        base = []
        for index, (c, w) in enumerate(pairs):
            if index == 2:
                ok = [t for t in TERRAINS if accepts(c, w, t) and not (record['water_gate'] and t == 40)]
                base.append(ok[0])
            else:
                base.append(c if w > 0 else min(255, c - w + 1) if w < 0 else c + 1)
        assert region_eligible(record, base), (region, record['name'], base)
        for index, (c, w) in enumerate(pairs):
            if index == 2:
                values = TERRAINS
            else:
                a = abs(w)
                values = sorted({v for v in (0, c - a - 1, c - a, c - a + 1, c, c + a - 1, c + a,
                                             c + a + 1, 255) if 0 <= v <= 255})
            for value in values:
                env = list(base)
                env[index] = value
                result.append((k, env, region_eligible(record, env)))
    return result
