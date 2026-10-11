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
