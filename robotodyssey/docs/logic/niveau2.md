# Niveau 2 : « Ride the Subway to the Town! »

*[← ANALYSE](../ANALYSE.md)* · structures : [world.md](world.md) · boucle : [simulation.md](simulation.md)

Code `$0803-$1907` (bloc `$0B7`), données et un peu de code `$8EF0-$9031`
(bloc `$0C0`), salles et textes `$0AD`. Désassemblage : `build/c_lvl2.txt`
(`$0803-$1FFF`) et, pour `$8EF0`, `tools/disasm.py build/lvl2.bin 8F54 9032
--entry 8F54` avec `--region 8F54-9032` plus les régions par défaut. Les
points **[vérifié]** l'ont été dans a2shot (voir [Méthode](#méthode-a2shot)).

## Vue d'ensemble

Le monde du niveau est un **tore de 8 × 4 salles** (les liens rebouclent
dans les deux sens). La rangée du bas est une **ligne de métro circulaire**
de 8 stations :

```
38    34    30    2C    28    24    20    3C      (rangée du haut)
37    33    2F    2B    27    23    1F    3B
36    32    2E    2A    26    22    1E    3A      ($2A = départ)
39    35    31    2D    29    25    21    3D      (stations ; $3D = dépôt)
```

Le joueur arrive salle `$2A` (32,32), là où il a quitté le niveau 1. La
sortie est salle `$02`, l'escalator, à laquelle on n'accède que par le haut
de la station `$29` (`$29` haut = `$02` ; `$02` n'est sur aucune autre
liaison). Les salles `$04-$08`, `$0C` et les tunnels `$0E-$15` ne sont
reliés au tore que dans un sens et ne sont pas accessibles (vestiges ?).

| # | Énigme | Salles | Routines |
|---|---|---|---|
| 1 | clé sur la plaque, porte, garde 0, jeton | `$2B`, `$2C` | `$1426` (`$1448`), `$0FE9`, `$1570` |
| 2 | tourniquet à jeton | `$38` (→ `$3C`, `$3D`) | `$0BFF`, `$1426`, `$0BE2` |
| 3 | dépôt : poignée, bouton d'appel, train | `$3D` | `$0E55`, `$0C9E`, `$0D25`, `$0D80`, `$0D42` |
| 4 | trajet en métro, 8 stations | `$3D $39 $35 $31 $2D $29 $25 $21` | `$0D80` |
| 5 | portes de la station `$29` | `$29`, `$25` | `$0F29` |
| 6 | boutons de retour (portes 22 tours) | `$1F`, `$24`, `$27`, `$34` | `$0C9E`, `$1426` |
| 7 | ticket de sortie, garde 2 | `$20` | `$0FE9` |
| 8 | fente du ticket, escalator, sortie | `$02` | `$0F29`, `$0F74`, `$8F54`, `$0AEC` |
| – | gardes 1 et 2, jeton recyclé | `$37`, `$20` | `$0FE9` |
| – | aimant de la salle `$28` | `$28` | `$0ED7` |
| – | salle secrète | `$23`/`$22` → `$03` | `$0DFC` |
| – | placement des puces 3, 4 et du capteur | `$32`, `$30`, `$28` | `$1784` |

## Boucle principale (`$0847-$092F`)

Même squelette qu'au niveau 1 ([simulation.md](simulation.md)), avec ces
différences :

| Appel | Place | Rôle |
|---|---|---|
| `$0D80` | juste après `$FE18`, **avant** prendre/poser `$A5CD` | montée dans le train, train en marche, descente |
| test `$9C26 = $24` | avant `$FE25` | on n'entre pas dans un robot en tenant la poignée |
| `$1784` | après le bloc du circuit | placement des puces au premier départ de `$2A` |
| `$0C9E` | | boutons (dépôt et portes de retour) |
| `$0E55` | | poignée du dépôt et ses murs |
| `$0ED7` | | aimant de la salle `$28` |
| `$1426` | | les 9 portes |
| `$0BFF` | | fente du tourniquet ; enchaîne sur `$0DFC` (salle secrète) |
| `$0FE9` | dessin, après les textes | **trois gardes** : mise à jour et dessin |
| `$1570` | dessin | plaque de la clé (`$2C`) |
| `$0BD2` | dessin | fente `$38`, boutons, train, fente `$02`, chargeur |
| `$0F29` | dessin | portes de `$29`, ticket, escalator, **sortie** |
| `$186F` | | curseur de la boîte à outils (commun) |

Toutes ces routines sont hors du bloc conditionné par la télécommande
(`$0892`) : les énigmes tournent même robots arrêtés. `$0986` (touches
`?`, `/`, `ESC`, `L`, triche) est identique à celle du niveau 1.

Initialisation (`$0816`) : table des touches, `$1DFE`, puis `$0976` place
le **chargeur de cristal** salle `$32` en (110,96) (`$8454-$8456`).
Rien ne place le joueur ni les robots.

## Ce qui arrive du niveau 1

La sortie du niveau 1 (`$0AE6`) envoie en `$3F` tout objet qui n'est ni tenu
(`$9C26`), ni attaché (`$6600 ≠ $FF`), ni dans une salle intérieure de robot.
**Les robots eux-mêmes ne sont pas épargnés** : leur moitié gauche est libre
et posée dans une salle ordinaire. **[vérifié]** sortie forcée depuis la
salle de départ : Sparky, Checkers et Scanner (`$F0-$F5`) sont en `$3F` au
niveau 2 ; leurs intérieurs (`$09-$0B`), câblage et contenu (la clé `$FA`
dans Checkers ce jour-là) sont toujours là, mais inaccessibles. Seul un
robot **tenu par le joueur** à la sortie passe (« You CAN take it with you
(if you hold on tight) ») ; ce qu'il a dans son intérieur passe avec lui.

Or le niveau 2 exige un robot (bouton du dépôt, garde 0) et la clé `$FA`
(porte de `$2C`). La clé est posée par le niveau 1 **dans un intérieur de
robot** (« The key to success lies within ») : tenir ce robot-là à la
sortie du niveau 1 apporte les deux.

Objets du niveau placés par la sortie du niveau 1 (table `$0B98…`) et par
`$1784`. Relevé en RAM au chargement **[vérifié]** :

| Objet | Rôle | Salle | X,Y | Sprite | Note |
|---|---|---|---|---|---|
| `$04` | **jeton** (pièce « 5 ») | `$2C` | 43,57 | `$01` | derrière la porte 1 |
| `$F7` | **ticket de sortie** | `$20` | 99,70 | `$02` | gardé par le garde 2 |
| `$24` | **poignée** du dépôt | `$3D` | 91,112 | `$04` | « Pull here » |
| `$E9`, `$EA`, `$14` | puce 3, puce 4, capteur de contact 2 | `$32` / `$30` / `$28` | voir `$1784` | | permutés |
| `$22`/`$23` | sentinelle | `$14` | 84,65 | `$2D`/`$3E` | salle inaccessible (?) |
| `$E1` | boîte à outils | `$26` | 43,45 | `$1B` | |
| `$FA` | clé | intérieur d'un robot | | `$38` | si le robot a été tenu |
| `$03` | aimant (sprite `$37`, fer à cheval) | | | | seulement s'il a suivi |

Le sprite `$37` est un **aimant** (fer à cheval à pôles rayés), comme
l'objet 3 du PC ; world.md l'appelle « bouton ».

### Placement des puces (`$1784`)

Tant que le joueur est dans `$2A`, `$8F53` tourne 0 → 1 → 2 à chaque tour.
Au premier tour hors de `$2A` (`$8F52` passe à 1), les trois objets de
`$1778` (`$E9 $EA $14`) sont posés dans les trois emplacements de
`$177B/$177E/$1781`, décalés de `$8F53` (rotation, pas de tirage
pseudo-aléatoire) :

| Emplacement | Salle | X,Y | Accès à pied |
|---|---|---|---|
| 0 | `$32` | 51,29 | depuis la station `$35` |
| 1 | `$30` | 41,143 | depuis la station `$2D` |
| 2 | `$28` | 91,88 | depuis le départ (dans le grand « C » de murs) |

`$14` prend l'emplacement `s`, `$EA` `s+1`, `$E9` `s+2` (modulo 3).
**[vérifié]** avec `s = 1` : `$14` en `$30`, `$EA` en `$28`, `$E9` en `$32`.
La sortie du niveau 1 les avait déjà mis dans ces salles (Y `$51` au lieu
de `$58` pour `$EA`) ; `$1784` les écrase.

## Les portes (`$1426`)

Neuf portes, chacune un **bloc de cases de mur qui glisse** le long d'un
chemin. Tables indexées par la porte `y = 0-8` :

| Table | Contenu |
|---|---|
| `$15C8` | salle |
| `$15D1` | position d'ouverture maximale |
| `$15DA` | longueur du bloc = pas par tour |
| `$15E3` | objet surveillé (`$FF` aucun ; `$FA` pour la porte 1) |
| `$15EC`, `$15EE` (+y) | X et Y de la plaque (seule l'entrée 1 sert : `$73`, `$21`) |
| `$15F0/$15F9` | pointeur vers les colonnes du chemin |
| `$1602/$160B` | pointeur vers les rangées du chemin |
| `$8F26+y` | position courante (au chargement = la longueur : le premier tour ferme tout) |
| `$8F2F+y` | front de la plaque |
| `$8F38+y` | consigne : 1 ouvrir, 0 fermer |

À chaque tour, la position avance de `+longueur` vers le maximum si la
consigne est 1, de `−longueur` vers 0 sinon ; `$1505` efface les cases du
bloc à l'ancienne position (`$B3AA`, A=0) et les pose à la nouvelle (A=1).
Une porte s'ouvre donc en `max/longueur` tours. Commandes : `$1539` ouvre,
`$1544` ferme, `$154F` inverse, la porte étant désignée par sa salle
(`$155D`).

Cases (colonne, ligne d'écran 0-11 comme dans `world.py --rooms`) :

| Porte | Salle | Max/pas | Fermée (position 0) | Ouverte | Commande |
|---|---|---|---|---|---|
| 0 | `$38` | 20/10 | « + » : col 4 lignes 4,5,7,8 ; ligne 6 col 1-3, 5-7 | position 10 = « × », position 20 = « + » | jeton (`$0BFF`) |
| 1 | `$2C` | 6/3 | col 14 lignes 3-5 | col 14 ligne 3 | clé `$FA` sur la plaque |
| 2 | `$1F` | 24/8 | ligne 10 col 5-8 ; col 10 lignes 2-5 | (8,10), (10,2) | boutons 1 et 2 |
| 3 | `$34` | 6/3 | col 16 lignes 1-3 | (16,1) | bouton 4 |
| 4 | `$24` | 6/3 | ligne 4 col 1-3 | (3,4) | bouton 3 |
| 5 | `$29` | 16/8 | col 18 lignes 7-9 ; ligne 0 col 8-12 | (18,7), (12,0) | `$0F29`, une fois |
| 6 | `$02` | 6/3 | (11,8), (14,5), (17,2) | (12,7)(15,4)(18,1) puis (13,6)(16,3) | ticket (escalator) |
| 7 | `$27` | 3/3 | (14,2), (15,2), (17,1) | (17,1) | bouton 5 |
| 8 | `$25` | 5/5 | col 0 lignes 6-10 | (0,6) | `$0F29`, une fois |

Seule la porte 1 a une plaque (`$1448`) : si `$FA` est en `$2C` avec
`X ∈ [$72,$74]` et `Y ∈ [$20,$22]`, le premier tour où elle y est inverse
la consigne (front `$8F2F`) ; dès qu'elle n'y est plus, la porte se ferme.
**[vérifié]** clé posée en (115,33) : position `0 → 3 → 6` ; clé retirée :
`6 → 3 → 0` ; reposée : rouvre.

## Énigme 1 : la clé et le jeton (`$2C`)

La salle `$2C` a deux parties séparées par la porte 1 (colonne 14) :

- à droite, un **couloir** (colonnes 15-17) ouvert en bas sur `$2B` ;
  la plaque y est en (115,33), dessinée par `$1570` (sprite `$1768`,
  couleur 6, en (119,32)) ;
- à gauche, la grande salle fermée où est le **jeton** `$04` (43,57) et où
  patrouille le **garde 0**.

Le garde 0 (comportement 2, voir [Gardes](#les-trois-gardes-0fe9)) ne
s'occupe que du **joueur à pied** : passé `Y = $20` dans le couloir (entrée
par le bas), il le ramène à son point d'entrée. **[vérifié]** joueur monté
de `$2B` : capturé à `Y = $20`, figé (`$8ED4 = 0`), redescendu à `Y = 0`.
La plaque est exactement au seuil (`Y ∈ [$20,$22]`) : la clé doit y être
posée sans que le joueur la dépasse. Le jeton, lui, est hors de portée du
joueur à pied ; un robot (programmé, ou piloté de l'intérieur : le garde 0
ignore le joueur qui est dans un robot) doit aller le chercher.

## Énigme 2 : le tourniquet (`$38`, `$0BFF`)

La salle `$38` (« Bay Area Robot Transport ») est coupée en deux par un
tourniquet (porte 0) : la partie gauche mène à `$3C` puis au dépôt `$3D`.

- Condition (`$0BFF`) : joueur dans `$38`, jeton `$04` dans `$38` à
  `|X − $50| < 5` et `|Y − $10| < 8`, **ni tenu** (`$9C26 ≠ 4`) **ni
  attaché** (`$6604 = $FF`). La fente est dessinée en (80,16) par `$0BE2`
  (sprite `$1810`, couleur 6), sous « Insert token, please. ».
- Effet : le jeton part en `$37`, `Y = $8E` (X inchangé, ≈ 80) ; `$8F50 = 8`
  ; puis tous les 6 tours (`$8F51` = 5 → 0) la consigne de la porte 0 est
  inversée et `$8F50` décrémenté : **8 demi-tours**, chacun en 2 tours
  (« + » → « × » → « + »). Le tourniquet finit fermé.
- Pendant la position « × », la colonne 4 est libre : le joueur passe.

**[vérifié]** jeton posé : il passe en `$37`, `$8F26` suit
`00 0A 14 14 14 14 0A 00…` ; joueur dans le quart bas-gauche tenant `K` :
il traverse (`X $15 → $1C → … → $85`) et sort à droite vers `$34`. Sans
jeton, il reste bloqué à `X = $15`.

Le jeton n'est pas perdu : il attend en `$37`, gardé par le garde 1. Il
faut le reprendre pour chaque nouveau passage du tourniquet.

## Énigme 3 : le dépôt et le train (`$3D`)

Le dépôt (« SUBWAY DEPOT ») a en haut à gauche une **boîte** fermée où se
trouve le **bouton d'appel** (13,160) (« Push this button to call train. »).

### La poignée (`$0E55`)

- Non tenue : la poignée `$24` est ramenée à `X = $5B` à chaque tour (ressort).
- Tenue (`$9C26 = $24`) : décalage de prise remis à 0, poignée **et
  joueur** forcés à `Y = $70`, X borné à `[$5B,$6B]`. Le joueur ne peut
  qu'aller et venir sur 16 unités et ne peut pas entrer dans un robot.
- À chaque tour, l'indice `i = (X − $5B) / 8` (0, 1 ou 2) écrit 4 cases de
  la ligne 4 (`$1820/$1823/$1826/$1829`, colonnes 1, 2, 13, 14) :

| `i` | X poignée | Col 1 | Col 2 | Col 13 | Col 14 |
|---|---|---|---|---|---|
| 0 | `$5B-$62` | mur | mur | – | – |
| 1 | `$63-$6A` | – | mur | mur | – |
| 2 | `$6B` | – | – | mur | mur |

Tirer à fond ouvre le plancher de la boîte (colonnes 1-2) et ferme le
passage de droite ; lâcher referme. **[vérifié]** `$7730-$7737` changent
avec X = `$62`, `$69`, `$6B`, et reviennent à l'état initial au lâcher.

### Le bouton et le train (`$0C9E`, `$0D25`)

Six boutons (`$182C` salle, `$1833` X, `$1839` Y ; dessin `$0C6E`, sprite
`$1800`, couleur 7). Un bouton est enfoncé si le **joueur** ou un **robot**
(`$F0-$F5`, l'une ou l'autre moitié) est à `|dX| < 5`, `|dY| < 8`
(`$0CE4`).

Le bouton 0 (`$3D`, 13,160) appelle `$0D25` : décroche le joueur
(`$0DF1`), puis, **si le joueur est dans `$3D`**, met le train en attente
en (32,64) : `$8F47/$8F48` = position du train, `$8F49 = 1` (train actif),
`$8F4A = 1` (à quai). Tant que le bouton reste enfoncé, cela recommence à
chaque tour : le robot doit le quitter, sinon le joueur est sans cesse
redescendu du train.

Comme le joueur reste coincé sur la poignée, c'est **un robot** qui doit
monter par le trou (colonnes 1-2, 14 unités : juste la largeur d'un robot)
et toucher le bouton pendant que le joueur tient la poignée tirée.

### Monter, rouler, descendre (`$0D80`)

- Monter : train à quai, joueur dans `$3D` à `|X − $1C| < 6`,
  `|Y − $40| < 14`, front du bouton (`$9C3B ⊕ $9C3C`) → `$8F4A = 0` ; les
  drapeaux du bouton sont effacés, si bien que `$A5CD` (appelé après) ne
  lâche pas l'objet tenu.
- Rouler : le joueur devient **son propre porteur** (`$6600 = 0`, décalage
  `+3, 0`) : `$9C53` l'avance de 3 unités par tour, **sans test de murs**,
  d'une salle à la suivante ; le train est dessiné à `X+6, Y−5`
  (`$0D42` : sprites `$17F0` et `$17E0` à 7 unités à gauche).
- Descendre : une touche de déplacement (`$8E84/$8E85 ≠ 0`) → `$0DF1`
  (`$6600 = $FF`, `$8F49 = 0`). Le train disparaît.

**[vérifié]** joueur posé sur le bouton : train en (32,64), `$8F49 = $8F4A =
1` ; joueur en (28,64) + espace : X `$22 → $25 → $28…` (+3 par tour), salle
`$3D → $39` (Robotoplatz) `→ $35`. Un tour de salle dure ≈ 45 tours.

Le trajet suit les liens « droite » de la rangée du bas, en boucle :

| Station | Texte |
|---|---|
| `$3D` | SUBWAY DEPOT |
| `$39` | Robotoplatz Station |
| `$35` | Cobble 'Bot Square Station |
| `$31` | Picadilly Circuit Station |
| `$2D` | Seer's and Robot Station |
| `$29` | Jack in the 'Bot Station |
| `$25` | Muse Robotique Station |
| `$21` | Laundrobot Station |

On ne peut appeler le train que du dépôt : après une descente, il faut
revenir à pied, repasser le tourniquet (donc reprendre le jeton) et
rappeler le train.

## Énigme 5 : la station `$29` (`$0F29`)

La première fois que la salle affichée est `$29` alors que le train n'est
pas actif (`$8F49 = 0`, donc après en être descendu), `$0F29` ouvre la
porte 5 (haut de `$29` vers l'escalator `$02`, et colonne 18 vers l'est)
et la porte 8 (mur ouest de `$25`). `$8F45 = 1` : c'est définitif.
**[vérifié]** joueur posé en `$29` : `$8F2B = $10`, `$8F2E = 5`,
`$8F45 = 1`.

## Énigme 6 : les boutons de retour (`$0C9E`)

Les boutons 1 à 5 ouvrent une porte de leur salle pour **22 tours**
(`$8F4E = $16`, salle dans `$8F4D`) :

| Bouton | Salle | X,Y | Porte |
|---|---|---|---|
| 1 | `$1F` | 112,112 | 2 |
| 2 | `$1F` | 7,16 | 2 |
| 3 | `$24` | 7,160 | 4 |
| 4 | `$34` | 130,160 | 3 |
| 5 | `$27` | 130,144 | 7 |

Le premier bouton enfoncé (plus petit numéro) gagne. Tant que le compteur
tourne, **aucun** bouton n'est testé (le bouton 0 non plus). À 0, la porte
est refermée (`$1544`) puis les boutons sont relus : un robot posé sur un
bouton tient la porte ouverte (fermeture et réouverture dans le même tour,
avant que `$1426` ne bouge le bloc). **[vérifié]** joueur sur le bouton 3
puis éloigné : `$8F2A = 6` pendant que `$8F4E` descend de `$13` à 2, puis
`3 → 0`.

Chaque bouton est du côté d'une station : ce sont des **portes de retour**
vers la zone de départ (voir [Zones](#zones-accessibles-à-pied)).

## Énigme 7 : le ticket (`$20`)

Le ticket `$F7` est en (99,70) dans la salle `$20`, gardée par le garde 2
(comportement 3 : il attrape le joueur, **ou le robot dans lequel est le
joueur**). Un robot seul n'est jamais visé. `$20` n'est accessible à pied
que depuis la station `$21` (Laundrobot), par le haut.

## Énigme 8 : la sortie (`$02`, `$0F29`, `$8F54`)

La salle `$02` est un escalier en diagonale (« Insert { Exit Ticket »).

- Fente : dessinée en (49,16) par `$0FAC` (sprite `$1810`, couleur 6).
- Condition : salle affichée `$02`, ticket `$F7` dans `$02` à
  `|X − $31| < 5`, `|Y − $10| < 8`. **Ni l'état « tenu » ni « attaché »
  n'est testé** (?).
- Escalator (`$0F74`, compteur `$8F46`) : la porte 6 (trois cases de mur
  sur la diagonale) monte d'une case par tour (`0 → 3 → 6`) puis retombe
  d'un coup à 0 (trois appels de `$0F9E` dans le même tour) : cycle de
  4 tours. Ticket absent, ces trois « marches » restent en position 0 et
  bouchent l'escalier. **[vérifié]** `$8F2C` : `00 03 06 00 00 06…`,
  `$8F46` : `FF 02 01 FF 02 01`.
- `$8F54` (dans le bloc de données) : dessine la cible, une silhouette du
  joueur (sprite 0, couleur 5) en (123,154) dans un cadre (`$A281`, X
  `$78-$83`, Y `$97-$AD`). Si le joueur est **exactement** en `X = $7B`,
  `Y = $9A`, sous sa forme normale (sprite 0) : montée (`$8F8E`) — joueur
  couleur 4, une note tous les 7 passages (`$8F43`), `$8F44 += 2` jusqu'à ≥ 9
  (5 notes), son 9, puis `$0AEC`.
- La case (17,2) où doit se tenir le joueur est l'une des marches : elle
  n'est libre que lorsque l'escalator tourne.

**[vérifié]** ticket posé en (49,16), joueur posé en (123,154) : cadre et
silhouette affichés, montée, écran `$3E` (« Be sure the Robot Odyssey disk
is in the disk drive. Then press ESC. »), puis `ESC` charge le niveau 3
(`$02D0 = 2`, `$02D1 = 2`).

### Passage au niveau 3 (`$0AEC`)

1. Comme au niveau 1 : objet tenu mis en (0,0) le temps de `$B8E6`, tri des
   objets (tenus, attachés, intérieurs de robots gardés ; le reste en `$3F`).
2. Joueur couleur 7 en `X = $4D`, `Y = $91` (77,145), salle inchangée `$02`.
3. 16 objets placés (`$0B39` objet, `$0B49` salle, `$0B59` X, `$0B69` Y),
   de l'entrée 15 à 0 :

| Objet | Salle | X,Y | | Objet | Salle | X,Y |
|---|---|---|---|---|---|---|
| `$04` | `$3C` | 61,95 | | `$18` | `$2A` | 16,51 |
| `$05` | `$07` | 43,78 | | `$22` | `$2A` | 53,105 |
| `$06` | `$12` | 77,111 | | `$EB` | `$2B` | 39,87 |
| `$07` | `$12` | 22,145 | | `$F7` | `$06` | 46,66 |
| `$0D` | `$11` | 49,96 | | `$F8` | `$0F` | 24,22 |
| `$0E` | `$1F` | 77,125 | | `$F9` | `$2A` | 114,92 |
| `$15` | `$26` | 24,52 | | `$FB` | `$16` | 67,99 |
| `$17` | `$05` | 27,38 | | `$EC` | `$19` | 10,40 |

4. `$F7` prend le sprite `$2F`, `$F7` et `$04` deviennent non saisissables
   (`$6900 = $FF`).
5. `$0A2A` (X=2) affiche la salle `$3E`, attente d'`ESC`, puis `$0AA6` :
   `$02D0 = 2`, `$02D1 = 2`, saut au vecteur RESET.

**[vérifié]** au début du niveau 3 : joueur `$02` (77,145) et 14 des 16
objets aux places de la table ; `$05` et `$07` sont déjà en `$3F` (le code
du niveau 3 les déplace ?). Pas de boîte à outils replacée ici, contrairement
au niveau 1.

## Les trois gardes (`$0FE9`)

Trois robots-gardiens (tête à un œil animée sur 3 images `$1738/$1748/$1758`,
lampe `$1728` au-dessus), chacun attaché à une salle. `$0FE9` est appelé
dans la phase de dessin : pour `x = 2, 1, 0`, mise à jour (`$1005`) puis
dessin si la salle est affichée (`$1021`).

| Garde | Salle | Comportement `$8F02` | Patrouille A ↔ B | Tête `$8F05` |
|---|---|---|---|---|
| 0 | `$2C` | 2 : le **joueur à pied** seulement | (10,144) ↔ (89,32) | 7 |
| 1 | `$37` | 3 : le joueur, ou le robot qui le contient | (78,16) ↔ (101,16) | 6 |
| 2 | `$20` | 3 : idem | (78,65) ↔ (89,68) | 6 |

Variables par garde : `$8EF0` salle, `$8EF3/$8EF6` X/Y, `$8EF9` sens de
patrouille, `$8EFC` victime (`$FF` aucune), `$8EFF` état de la capture.
Par cible (`$15B8` : `$00` joueur, `$F0`, `$F2`, `$F4`, `$01` robots ;
intérieurs `$15BD` : –, `$09`, `$0A`, `$0B`, `$0D`) : `$8F16` bord
d'entrée, `$8F0C/$8F11` point d'entrée, `$8F1B/$8F20` position figée. Ces
tables par cible sont communes aux trois gardes.

1. **Patrouille** (`$106C`, comportement 1 ou aucune victime) : pas de ±2
   en X et Y vers A ou B (`$15AC/$15B2`, `$15AF/$15B5`) ; à l'arrivée,
   lampe orange (`$8F0B = 5`) et demi-tour ; sinon lampe blanche.
2. **Entrée** (`$11AF`, `$11DC`) : pour chaque cible dans la salle du garde
   et proche d'un bord, on note le bord (1 gauche `X < 7`, 2 droite
   `X ≥ $7F`, 3 bas `Y < $10`, 4 haut `Y ≥ $A1`) et la position. Un joueur
   dans un robot hérite du bord de son robot (`$128A`).
3. **Seuil** (`$121C`) : la cible est capturée si elle s'éloigne de son
   bord : `X ≥ $15` (entrée à gauche), `X < $70` (à droite), `Y ≥ $20` (en
   bas), `Y < $90` (en haut ou bord inconnu).
4. **Poursuite** (`$12C9`) : le garde fonce (pas bornés à ±28 en X, ±39 en
   Y, sans murs). À moins de 29 (`|dX| + |dY|`), la victime est **figée** :
   `$8ED4` = son numéro (joueur : plus de commandes, `$A90C` sauté ; robot :
   immobile dans `$D000`), `$8EFF = 2`. À moins de 9 : `$8EFF = 1`, son
   `$0A` (celui de l'Ampire Bot).
5. **Reconduite** (`$1374`) : garde et victime reviennent ensemble, ±2 par
   tour, au point d'entrée ; un robot est remis en deux moitiés (`$9C88`,
   `+5,0`). Arrivée : son `$0B`, `$8ED4 = $FF`, victime libérée.

Le garde ne prend rien : ce que tient la victime revient avec elle. Il ne
quitte jamais sa salle. Le comportement 2 ne regarde que le joueur
(`$8F09 = 0`) ; le comportement 3 (`$116E`) remonte de l'intérieur de robot
où est le joueur au robot lui-même. Un robot sans joueur n'est jamais
poursuivi.

**[vérifié]** garde 0 : voir énigme 1. Garde 1 : joueur entré par la
gauche de `$37` (X=2) et poussé vers la droite : capturé à `X = $17`, figé,
ramené à `X = 4`. Entré par le haut (couloir colonnes 17-18), le joueur
bute sur un mur à `Y = $90` sans franchir le seuil.

## L'aimant (`$0ED7`)

À chaque tour, si l'objet `$03` est dans la salle `$28` — ou s'il est dans
un intérieur de robot et que ce robot (en remontant les robots imbriqués,
`$0F15`) est dans `$28` — l'objet ou le robot est **attiré** vers (90,81) :
pas bornés à ±9 en X, ±11 en Y (`$ACF8`), déplacement `$9DB3` sans murs,
puis `$9C53`. (90,81) est dans le grand « C » de murs de `$28`, à côté de
l'emplacement de puce (91,88).

**[vérifié]** `$03` posé libre en (20,40) dans `$28` : `(29,51) → (47,73)
→ (56,81) … → (90,81)`.

`$03` n'est placé par aucune table du niveau 2 : il n'y est que si le
joueur l'a apporté (tenu, ou dans l'intérieur du robot tenu). Rôle exact
dans l'énigme : (?).

## La salle secrète (`$0DFC`)

Appelée à chaque tour en fin de `$0BFF`. Les salles `$23` (au-dessus) et
`$22` ont une ouverture d'une case à la colonne 5 dans leur mur commun. Si
le joueur passe de `$23` à `$22` **exactement en `X = $23`** avec un pas
vertical de −1 (`$8E85 = $FF`, Ctrl-M), ou de `$22` à `$23` avec +1
(Ctrl-I), il est envoyé salle `$03` : « Congratulations!! You have reached
the Secret Room of Public Knowledge. This game is dedicated to Warren
Robinett… ». `$8F4F` garde la salle du tour précédent. La salle `$03` a
deux sorties colonne 5 (haut `$23`, bas `$22`).

**[vérifié]** joueur en `$23`, X=`$23`, Y=2, trois RETURN : salle `$03` ;
même essai en X=`$24` : salle `$22`.

## Zones accessibles à pied

Calcul sur la grille des cases (inondation case par case depuis le départ,
portes fermées, murs relevés en RAM au niveau 2 ; le joueur traité comme
une case : approximation) :

| Zone | Salles | Contient | Retour vers la base |
|---|---|---|---|
| base (départ `$2A`) | `$1E $1F $20` (bas) `$22 $23 $24 $26 $27 $28 $2A $2B $2C` (couloir) `$2E $2F $30 $32 $33 $34 $36 $37 $38` (droite) `$39 $3A $3B $3C` (poche) | plaque de `$2C`, emplacement de `$28`, jeton recyclé (`$37`), fente du tourniquet, station `$39` | – |
| + tourniquet | `$3C`, `$3D` | dépôt, poignée, bouton 0 | tourniquet |
| station `$35` | `$1E $1F $22 $23 $32 $35 $36 $3A` | emplacement `$32` (51,29) | porte 2 (bouton 2) |
| station `$31` | `$1F $2E $31 $32 $36 $3A $3B` | chargeur `$32` (110,96) | porte 2 (bouton 1) |
| station `$2D` | `$2D $30 $31 $34` | emplacement `$30` (41,143) | porte 3 (bouton 4) |
| station `$29`/`$25` | `$02 $24 $25 $29` (portes 5, 8 ouvertes) | **sortie** | porte 4 (bouton 3) |
| station `$21` | `$20 $21 $23 $24 $25 $27` | **ticket** | porte 7 (bouton 5) |

Toutes les sorties de station ramènent dans la base, **hors** du
tourniquet : chaque nouveau trajet demande de reprendre le jeton en `$37`.
Le ticket (zone `$21`) et la sortie (zone `$29`) sont dans deux zones
différentes, reliées seulement par la base et les portes 7 et 4.

## Séquence de solution imposée par le code

0. Au niveau 1 : quitter la salle `$2A` **en tenant un robot**, de préférence
   celui dont l'intérieur contient la clé `$FA`.
1. Quitter `$2A` (placement des puces 3, 4 et du capteur de contact 2,
   utiles pour programmer le robot).
2. `$2C` (par `$2B`) : clé `$FA` sur la plaque (115,33) → porte 1 ouverte
   tant qu'elle y reste ; le jeton (43,57) est pris par le robot (le
   garde 0 refoule le joueur à pied).
3. `$38` : jeton posé libre sur la fente (80,16), joueur dans la salle →
   passer le tourniquet vers la gauche pendant ses 8 demi-tours → `$3C` →
   dépôt `$3D`. Le robot doit passer aussi (porté ?).
4. `$3D` : tenir la poignée tirée à fond (X=`$6B`) ; le robot monte par
   les colonnes 1-2 et touche le bouton (13,160) ; le train attend en
   (32,64) ; le robot quitte le bouton ; lâcher la poignée, monter dans le
   train (bouton/espace en (28,64)).
5. Descendre à `$21` (Laundrobot) → `$20` : ticket `$F7` (garde 2 : y aller
   à pied le fait refouler ; un robot seul n'est pas visé) → retour à la
   base par le bouton 5 (`$27`) et la porte 7, ticket en main.
6. Reprendre le jeton en `$37` (garde 1), repasser le tourniquet, rappeler
   le train (robot sur le bouton 0), descendre à `$29` : portes 5 et 8
   ouvertes.
7. Monter en `$02`, poser le ticket sur la fente (49,16), monter l'escalator
   et se placer **exactement** en (123,154) sous sa forme normale (pas
   fins Ctrl) → niveau 3.

Variante : `$29` d'abord (portes 5/8), puis un robot posé sur le bouton 3
de `$24` tient la porte 4 ouverte et relie la zone de sortie à la base ;
le ticket peut alors être ramené à pied (?).

## Méthode a2shot

Pour arriver au niveau 2, on exécute le **code de sortie du niveau 1**
depuis la boucle principale, ce qui marche :

```sh
S=…/scratchpad/niv2   # fichiers temporaires
A=../dev/tools/a2shot/a2shot
$A --disk original/A_ROBOTROPOLIS.woz wait:2500 key:"\r" wait:900 key:"\r" \
   wait:6500 until:085B:100 go:0AE6 wait:300 key:"\e" wait:3000 \
   until:0847:100 …étapes…
```

`go:0AE6` saute le test de victoire et la fanfare ; l'écran `$3E` attend
`ESC`, puis le module résident charge le niveau 2. Le joueur reste dans la
salle de même numéro où il était (ici `$28`, 114,67), les robots non tenus
sont en `$3F`. La voie « `$02D0 = 2`, `$02D1 = 1`, RESET » n'a pas été
essayée. Pour déplacer un objet de salle : `poke:9C2F:OBJ poke:9C2E:SALLE
call:9E07:5`, puis `poke` de X (`$64xx`) et Y (`$65xx`). Un tour de jeu
≈ 13 images. En zsh, une liste d'étapes dans une variable se passe avec
`${=P}`.

## Points non compris

- **Aimant `$03`** : attiré vers (90,81) dans `$28` (vérifié), mais son rôle
  dans la solution et la façon normale de l'apporter restent à établir.
- **Robot et tourniquet / train** : d'après le code, un robot tenu suit le
  joueur sans test de murs (`$9C53`) et la montée dans le train ne lâche pas
  l'objet tenu ; non vérifié en jeu.
- **Clé et seuil du garde 0** : la plaque est exactement au seuil de capture ;
  la manière prévue de poser la clé (joueur, robot, pas fins) n'est pas
  vérifiée.
- **Ticket tenu** : `$0F47` ne teste pas que le ticket soit libre.
- **Zones** : calcul case par case, sans les déplacements fins ni les
  passages en diagonale ; à confirmer en jouant.
- **Sentinelle `$22/$23`** : garée en `$14` (tunnel inaccessible) au niveau 2 ;
  pourquoi le niveau 1 l'y laisse.
- **Salles `$04-$08`, `$0C`, `$0E-$15`** : reliées au tore dans un seul sens,
  inaccessibles ; vestiges d'un plan antérieur ?
- **`$1570`** dessine aussi la plaque en salle `$3F` (code mort ?).
- **`$05` et `$07`** placés par `$0AEC` mais en `$3F` au début du niveau 3.
- Partie complète du niveau 2 non jouée de bout en bout.
