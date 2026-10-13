# Comparaison des aventures avec l'original

La parité d'une aventure complète n'est **pas validée**. La suite compare les mêmes
commandes dans les deux jeux Apple II. Les cinq scénarios courts et une marche
native jusqu’à x70/y86 concordent, mais ils ne couvrent pas encore
le trajet complet crash → rangers. Les tests du port contre un
modèle Python ne suffisent pas à établir cette parité.

## Exécution

Depuis `wilderness/`, avec les disques originaux déjà extraits localement :

```sh
make test
make test-original
python3 tests/test_adventure.py --scenario overnight
```

Les prérequis sont `build/SIERRA.woz`, `build/JOURNEY.dsk`,
`build/files/TOPO.B`, les modules du port et a2shot. `make extract` prépare
les données originales ; elles restent hors git. Les nouvelles sondes de géographie préparent aussi
`build/re_geography/heights.bin` et `types.bin`. Un prérequis absent,
une question inattendue, un délai dépassé ou une différence fait échouer
la commande. Aucun scénario en erreur n'est présenté comme réussi.

## Méthode et preuves

L'original démarre depuis Sierra, puis utilise Journey sur une copie privée.
Le port démarre avec une carte convertie depuis le même TOPO. Une commande
est envoyée à chacun, puis le pilote attend l'invite ou une question,
inspecte l'écran et fournit sa réponse. Les questions de conteneur de
l'original sont des touches seules ; les quantités et durées se terminent
par RETURN. Le port sélectionne actuellement certains conteneurs implicitement :
cette différence d'interface est consignée dans les événements du rapport.
Le pilote ne force ni position, ni santé, ni équipement dans la RAM du jeu.

Chaque étape conserve mémoire, capture d'écran et état normalisé. On compare
heure, date, temps écoulé, santé, température corporelle, frissons/sueur,
compteurs de boisson/repas/repos, déficits, énergie, position, direction,
objets et stocks accessibles, charge, hasard partagé, cadence de santé,
air, vent, ressenti et intérieur/extérieur. Les flottants
ont une tolérance de 0,000002 ; la direction admet une demi-unité du port
(560 azimuts contre 360 degrés). Les autres différences sont rapportées.

L'original réutilise `$4000-$4FFF` comme seconde page HGR après avoir
sauvegardé l'état sur Journey T04. Le pilote observe `$103E` avant cette
pagination et restaure ce bloc **dans l'observation Python**, jamais dans
le jeu. La provenance de chaque état et les dumps bruts paginés sont conservés.
Voir [ENGINE.md](logic/ENGINE.md).

`build/adventure/` contient `index.json`, puis par scénario `report.json`,
`labels.json`, `manifest.json`, journaux et fichiers `original-*.bin/.png`
et `port-*.bin/.png`. Les symboles et empreintes SHA-256 permettent de relire
les observations après une recompilation. La suite utilise un seul disque
du port figé pour ses scénarios. Ne pas recompiler pendant les tests.

## Scénarios et résultat actuel

Le départ commun utilise la boussole, porte la parka, boit 10 oz à la gourde,
mange 8 oz de fromage depuis le sac puis se repose une heure.

| Scénario | Points observés | Résultat |
|---|---:|---|
| `opening` | 6 | 0 différence |
| `camp` | 12 | 0 différence |
| `overnight` | 10 | 0 différence |
| `travel` | 10 | 0 différence |
| `discovery` | 10 | 0 différence |
| `march` | 61 | 0 différence ; crash → x70/y86 |
| `encounter` | 83 | 0 différence ; ours, crotale, SCARE échoués, venin et soins |

Les cinq scénarios courts sont conservés dans `build/comparison-stage17/`,
la marche dans `build/comparison-stage16/`. Ils utilisent la géographie Sierra
native, sans cabane ajoutée ni déplacement imposé dans la mémoire du jeu.

Le vent et le ressenti concordent désormais sur ces aventures, avec les
mêmes tirages aléatoires et la même cadence de santé. WALK utilise la charge,
la santé, la météo et la pente originales, avec des pas d’une unité native
(une demi-case du port). Un dernier pas admis peut dépasser la durée demandée.
Les actions sans déplacement conservent leurs propres tirages de ressources.

## Géographie et portée des preuves

Les interactions natives consultent les 224 × 168 positions originales,
y compris les cellules impaires, le type rivière/lac et les bois.
`test_geography.py --original` compare 37 632 positions à la routine originale.
Le rendu reste une carte de 112 × 84 cellules ; les images ne sont donc pas
une reproduction exacte de la géographie fine. La cabane native doit être
trouvée pendant l’aventure ; elle n’est pas préplacée sur la carte de comparaison.

`test_journey.py` utilise une carte artificielle pour éprouver la condition
d’arrivée et le bilan de victoire. Ce test valide le mécanisme du port ; il
ne prouve pas la parité d’une aventure Sierra native.

Les tests ROM isolés de nage vérifient l’effort, la cadence et le raster
(2 880 positions, 360 caps). Ils ne remplacent pas une traversée réelle avec
collecte d’eau, rencontre, nuit et sortie sur la rive opposée.

## Validation encore à terminer

Le prolongement de `march` vers la rivière et les rangers est en cours.
Les 83 premiers points concordent, y compris la marche après l’ours,
SCARE RATTLER, le venin, USE SNAKEBITE KIT et le hasard partagé.
Le repos suivant diverge : l’original interrompt après quatre heures
quand la météo se dégrade, alors que le port poursuit deux heures de plus
avant une découverte. Le dernier
rapport est `build/parity-native-prefix/report.json`, arrêté à la différence.
Les réactions animales, la collecte/consommation d’eau sauvage, la vie des
rencontres et les transitions rive/eau doivent concorder dans ce trajet.
Il doit aussi inclure une cabane découverte naturellement, les nuits,
les repas et l’hydratation, puis une victoire observée dans les deux jeux.
Les variantes de mort, blessures/soins et reprise de sauvegarde restent
à compléter. Voir [TODO.md](../TODO.md).

Les nuits de pleine lune constituent une règle visuelle du port : le ciel
reste noir, mais le relief, les arbres, les sites et les animaux sont visibles.
La pleine lune suit le disque entièrement éclairé de l’éphéméride 1985 ;
les autres phases gardent le paysage sombre. Cette visibilité ne change pas
la nuit utilisée par la survie. `test_moonlight.py` contrôle le rendu séparément
et ne constitue pas une preuve de parité astronomique avec l’original.
