# Projection de plans et de couloirs

Deux modules indépendants : `perspective.c` projette un plan HGR sur 280
pixels ; `corridor.asm`, extrait de Light3DBall, projette les deux axes d'une
section de couloir selon la profondeur. Chaque client choisit son module.

## Plan HGR

`a2_perspective_project(camera,x,y,&point)` projette un point du plan de jeu
dans l'écran HGR 280×192. Le calcul cible utilise des tables et un produit
16 bits ; aucune division perspective ni virgule flottante n'est nécessaire.
L'approche est inspirée des tables de
[Shufflepuck](https://github.com/colinleroy/a2tools/blob/main/src/shufflepuck/generators/gen_transform.c).
Le générateur et le runtime sont une nouvelle implémentation GPL-3.0.

```sh
python3 dev/tools/perspective.py --out build/camera.h --name camera \
  --rows 192 --focal 78 --center 140 --horizon 31 --bottom 191
```

Inclure `perspective.mk` après `apple2.mk`, ajouter `$(PERSPECTIVE_SRCS)` aux
sources et `$(PERSPECTIVE_INCS)` aux flags C. Le fichier généré appartient à
l'application ; l'inclure dans une seule unité C pour éviter de dupliquer
les tables. Une caméra de 192 lignes coûte 768 octets de tables et un
descripteur de 7 octets sur cc65. Le runtime n'alloue pas de pool ni de BSS.

```c
#include "perspective.h"
#include "camera.h"
a2_projected_t point;
if (a2_perspective_project(&camera,279,96,&point))
    hgr_plot(point.x,point.y);
```

L'abscisse d'entrée vaut 0..279 ; la profondeur va de 0 (loin) à rows-1
(près). `focal` est une distance positive, dans les mêmes unités que la
profondeur. L'horizon et le bas sont des lignes HGR. `center` est le centre
de projection horizontal, dans l'écran. Le rapport à la ligne y vaut :

```
r = focal / (focal + rows - 1 - y)
q = max(1, floor(256*r))
screen_x = floor(x*q/256) + floor(center*(256-q)/256)
screen_y = horizon + floor((bottom-horizon)*r)
```

Les tables stockent q sur un octet : zéro représente 256, donc l'identité
sur la dernière ligne. Le calcul X gère le passage 255→256 sans produit
32 bits. La quantification peut fusionner des points ou des lignes au loin.
Ce module projette un plan, pas une scène 3D arbitraire ; il n'agrandit pas
les sprites et ne gère pas l'ordre de profondeur.

Les tables sont empruntées et doivent rester valides pendant l'appel.
Les pointeurs nuls, X hors limites, profondeur hors table, nombre de lignes
invalide et résultat hors HGR sont refusés avec zéro, sans modifier le point
de sortie. Le succès vaut un. Appeler hors IRQ, en RAM/ZP principales et D=0.
L'affichage, les banques et le masque IRQ restent ceux de l'appelant.

```sh
python3 dev/tests/test_perspective.py
python3 dev/tests/test_perspective.py --iie
make -C dev/examples/perspective run
```

## Couloir 6502 / cc65

`corridor.asm` partage le noyau de Light3DBall et `corridor.h` expose son API C.
La section du monde utilise X/Y de 0 à 127. La profondeur est une distance
non signée sur 16 bits devant la caméra ; calculer cette distance avant l'appel.
Le résultat est sur un octet par axe : X/Y écran 0..255. L'application garde
le clipping HGR à 192 lignes, les occultations, les tailles de sprites et les
collisions. La bibliothèque ne connaît pas les niveaux ou les objets du jeu.

```sh
python3 dev/tools/perspective.py --kind corridor --name corridor \
  --span-x 252 --span-y 148 --focal 32 --center-x 128 --center-y 80 \
  --out build/corridor_tables.h
```

Inclure les tables générées dans une seule unité C. Ajouter un fichier
assembleur au programme, avec le chemin `PERSPECTIVE_CORRIDOR_INCS` :

```asm
PC_CENTER_X = 128
PC_CENTER_Y = 80
PC_DEPTH_SHIFT = 1
.include "corridor.asm"
```

Déclarer `PERSPECTIVE_CORRIDOR_DEPS` parmi les dépendances de cette unité et
des clients de `corridor.h`. Les centres et le pas de profondeur sont fixés à
la compilation ; les tables sont fournies par l'application. Leur nom par
défaut est `corridor_scale_x/y`. Le runtime emprunte leur contenu immuable.

```c
#include "corridor.h"
#include "corridor_tables.h" /* Une seule unité C définit les deux tables. */

a2_corridor_select(distance);
screen_x = a2_corridor_x(world_x);
screen_y = a2_corridor_y(world_y);
```

Les formules exactes sont :

```
depth = min(distance >> PC_DEPTH_SHIFT, 255)
span_x = table_x[depth]
span_y = table_y[depth]
left = PC_CENTER_X - floor(span_x/2)
top  = PC_CENTER_Y - floor(span_y/2)
screen_x = left + floor(world_x*span_x/128)
screen_y = top  + floor(world_y*span_y/128)
```

Le générateur remplit chaque table avec `floor(span*focal/(focal+depth))`.
`focal` est exprimée en **entrées de table** : avec `PC_DEPTH_SHIFT=1`, une
entrée correspond à deux unités du monde. Le pas peut aller de 0 à 8 ; au-delà
de la dernière entrée, la projection conserve les facteurs de cette entrée.
Une profondeur négative doit être traitée par le client avant conversion.

L'état actif contient cinq octets BSS (`a2_corridor_sx/sy/left/top/depth`) et
le calcul emprunte un octet ZP. Toujours appeler `select` avant de projeter.
Deux tables de 256 octets coûtent 512 octets. Pour réutiliser des allocations
existantes, définir les alias assembleur `PC_BITS`, `PC_SX`, `PC_SY`, `PC_LEFT`,
`PC_TOP`, `PC_DEPTH`, `PC_TABLE_X` et `PC_TABLE_Y` avant l'inclusion. C'est ce
que fait Light3DBall, sans allocation supplémentaire ni trampoline d'appel.

Le produit est exact en sept étapes décalage/addition, sans helper C ou
produit 32 bits. Aucun état vidéo, banque ou masque IRQ n'est modifié.
Appels non réentrants, hors IRQ, D=0, en RAM/ZP principales. Le noyau ne
valide ni les coordonnées ni les tables : les facteurs doivent garder
`center - floor(span/2)` et les points projetés dans 0..255.

```sh
python3 dev/tests/test_corridor.py
python3 dev/bench/corridor_projection.py
make -C light3dball test
```

L'extraction conserve octet pour octet le binaire et les ressources de
Light3DBall. Les coûts mesurés sur ce placement sont 65..77 cycles pour la
sélection, 135..170 pour X, 129..164 pour Y, JSR/RTS inclus : variation de
**0 %** par rapport au code local. Les franchissements de pages des tables
et des branches font varier les coûts ; ces intervalles ne sont pas un
budget universel pour d'autres placements du noyau.
