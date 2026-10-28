# Niveau 5 : les voies aériennes, et la fin du jeu

*[← ANALYSE](../ANALYSE.md)* · structures : [world.md](world.md) ·
simulation : [simulation.md](simulation.md) · images de fin :
[graphics.md](graphics.md)

« Travel the Skyways to freedom! » : code `$0803-$1A2F` (bloc `$0F8`),
données `$8EF0-$94EA` (bloc `$102`), monde `$0EE`. Tout est lu sur
`build/lvl5.bin` (`tools/disasm.py`, entrées supplémentaires `8F9A` et
`7294`). Les points vus dans a2shot sont marqués **[vérifié]** ; la
méthode est en fin de document.

## Vue d'ensemble

| Routine | Appel dans la boucle | Énigme |
|---|---|---|
| `$17B9` | 2 (touches) | touches du niveau, comme `$0980` au niveau 1 |
| `$09D5` | après `$D000` | 7 portes coulissantes, dont 5 à serrure (objet posé sur une dalle) |
| `$0B1A` | après `$09D5` | **Disk-O-Tek** : tapis roulant forcé, salles `$32-$39` |
| `$0C23` | après `$0B1A` | minuterie de garde (`$0C33`), fils chauds et grille bleue (`$0D22`), boutons « Odd before Even » (`$0E59`), serrure sonore (`$0F4F`), boutons du transporteur (`$0F92`) |
| `$0E18` | après `$DD59` | salle `$29` : bouton « Open Door », vue de la salle du dessous |
| `$10D6` | après `$9D03` | **trafic** des voies aériennes (4 files de véhicules) |
| `$8F9A` | après `$10D6` | 3 véhicules gardiens (salles `$0F`, `$1F`, `$0E`) |
| `$7294` | après `$8F9A` | **transporteur** : fin du jeu |
| `$13B3` | après `$D72B` | décor par salle (dalles, boutons, grille, fils) |

Variables principales (`$8F2D-$8F99`) :

| Adresse | Rôle |
|---|---|
| `$8F26+p` / `$8F34+p` / `$8F2D+p` | porte *p* : position, état voulu (1 ouverte), front de la dalle |
| `$8F3D` | étape du tapis roulant (0-17) |
| `$8F48` / `$8F4A` / `$8F49` | minuterie (BCD), sous-compteur de 9 tours, interrupteurs encore appuyés |
| `$8F4B` | 1 = dalle de la salle `$0E` inactive (bascule par les boutons) |
| `$8F4C` / `$8F4E` | serrure sonore : bits restant à reconnaître / bit affiché |
| `$8F3F-$8F42`, `$8F84` | boutons de `$0E` : appuyés, précédents, dernier, délai, STARTER |
| `$8F43-$8F47`, `$8F8D` | boutons du transporteur : idem |
| `$8F55` / `$8F56` | clignotement après un choc (99 tours), objet touché |
| `$8F71-$8F74` | ordonnée du premier véhicule de chaque file |
| `$8F78-$8F95` | couleur des 30 éléments de décor (`$13B3`) |
| `$8F99` | transporteur armé (≠ 0) |
| `$8EF0-$8F0B` | 3 véhicules gardiens (salle, X, Y, sens, cible, état, type, couleur) |

## Démarrage (`$0816`)

- table des touches `$0809` → `$9C11` ; `$A66D` ← `JSR $B8E6` ; `$1DFE`
  (compteur de la boîte à outils) ;
- **chargeur de cristaux** en salle `$15` (« SKYWAY REST STOP »),
  (119,20) : `$8454-$8456` ← `15 77 14`.
- aucun objet n'est placé : c'est la sortie du niveau 4 (`$0AFF` du bloc
  du niveau 4) qui l'a fait. Observé en a2shot en exécutant cette sortie
  **[vérifié]** : seul le **disque `$08`** est placé, en salle `$37`
  (63,160) ; le joueur reste dans la salle où il était (au vrai jeu, la
  salle `$02` de la sortie du niveau 4) en (14,32), couleur 7 ; les
  robots non tenus sont envoyés en `$3F` comme tout objet libre (voir
  [Points ouverts](#points-ouverts)).

Boucle : même squelette qu'au niveau 1. Différence : tant que `$8F55 ≠ 0`
(joueur sonné après un choc), `T` (`$1AB0`), `R` (`$BE86`) et `C`/`S`
(`$BDE1`) sont ignorés.

## `$17B9` : touches

Identique au niveau 1 : `?` ou `/` montre la salle `$01` (indices) jusqu'à
RETURN ; ESC montre la salle `$00`, puis ESC → menu (`$0994`, `$02D0 = 1`),
`S` → sauvegarde (`$099C`, `$02D0 = 4`, Y = 4) ; `L` en tenant une puce
`$E7-$EE` → salle `$3E` puis édition de la puce (`$0989`, `$02D0 = 5`) ;
touche = `$03FF` → passe-muraille `$9C30`. Écrans et textes : table
`$1854` (salle) / `$1858` (texte en plus), routine `$185D`, attente
`$18CD`.

## `$09D5` : portes coulissantes

Sept portes, une par salle. Chaque porte est un bloc de 4 cases de mur
(`$941E = 4`) qui se déplace le long d'une liste de cases : position 0 =
fermée, position `$9417` = ouverte, pas de 4 par tour (`$0A60`, effacement
puis pose par `$B3AA`, `$0AAE`). Une dalle (`$0A00`) inverse l'état voulu
`$8F34` **au moment où l'objet y arrive** (front `$8F2D`) : l'objet tolère
±1 unité autour de (X,Y).

| p | Salle | Objet-clé `$9425` | Dalle (X,Y) | Ouverte | Cases (colonnes `$943A/$9441`, rangées `$9448/$944F`) | Rôle |
|---|---|---|---|---|---|---|
| 0 | `$02` | `$FA` (clé) | (94,48) | 8 | col. 15, rangées 4-7 → 16-17 | sortie droite de la salle de départ |
| 1 | `$20` | `$08` (disque) | (53,16) | 8 | rangée 1, col. 2-5 | plancher vers `$11` |
| 2 | `$0E` | `$08` | (53,16) | 8 | rangée 1, col. 2-5 | plancher vers `$29` ; dalle active seulement si `$8F4B = 0` |
| 3 | `$2A` | `$08` | (60,160) | 8 | rangée 9, col. 8-11 | couloir du haut → centre du transporteur |
| 4 | `$10` | `$08` | (117,160) | 8 | col. 15, rangées 4-7 | serrure sonore (dalle dans le compartiment de droite) |
| 5 | `$29` | aucun (`$FF`) | – | 12 | rangée 0, col. 2-4 | plancher de `$29` |
| 6 | `$28` | aucun | – | 12 | rangée 11, col. 2-4 | plafond de `$28` |

Commandes par le code : `$0AE2` ouvrir, `$0AED` fermer, `$0AF8` inverser
la porte de la salle A (`$0B07` cherche *p*). Utilisées par la minuterie
(5 et 6), le bouton de `$29` (5 et 6), la serrure sonore (4) et le trafic
(un choc **referme la porte 0**).

**[vérifié]** clé `$FA` posée en (94,48) salle `$02` : `$8F34 = 1`, porte 0
en position 8 ; disque `$08` en (60,160) salle `$2A` : porte 3 ouverte,
retiré puis reposé : refermée.

## `$10D6` : le trafic des voies aériennes

Salles concernées : `$196E` = `04 0C 06 05 08 07` (« The Skyways of
Robotropolis »). Toutes ont le même plan : on entre à gauche par les
rangées 2-3, on sort à droite par les rangées 7-8, entre les deux une
bande de 4 files verticales.

On suit le joueur, ou le robot dans lequel il se trouve (`$9405` = salles
intérieures). Un robot seul n'est ni bloqué ni heurté.

- **Garde-fous** (`$1152`) : dans la bande X 28-105, Y < 17 ou Y ≥ 158
  est ramené à 18 / 157 : on ne quitte pas la bande par le haut ou le
  bas. Deux sprites décoratifs (`$11A9`, `$8F57-$8F5C`) patrouillent le
  long des bords et sautent à l'endroit heurté.
- **Files** (`$120C`, 4 files) :

  | File | X `$19C5` | Vitesse `$19C9` | Écart `$19CD` |
  |---|---|---|---|
  | 0 | 35 | +3 | 48 |
  | 1 | 77 | +1 | 48 |
  | 2 | 56 | −1 | 48 |
  | 3 | 98 | −3 | 48 |

  Chaque file porte un véhicule tous les 48 Y entre Y = 8 et 167 ; 5
  formes par file (`$19D1/$19D5`, sprites `$15C9…`, animation `$19A1`,
  couleurs `$19A9`). Les véhicules existent dans les six salles à la fois.
- **Choc** : objet à moins de 3 unités en X de la file et 8 en Y d'un
  véhicule. Effet : X ← 29, **porte 0 refermée**, objet envoyé dans la
  salle `$1974` correspondant à la salle **affichée**, clignotement de
  99 tours (`$8F55`), son `$0C`.

  | Salle | `$04` | `$0C` | `$06` | `$05` | `$08` | `$07` |
  |---|---|---|---|---|---|---|
  | renvoi | `$02` | `$04` | `$0C` | `$06` | `$05` | `$08` |

  **[vérifié]** joueur posé en (35,80) salle `$06` : choc, X = `$1D`,
  `$8F55 = $63`, salle `$0C`.

À faire : traverser chaque salle en diagonale en passant entre les
véhicules. Un choc en `$04` ramène dans la salle de départ, porte fermée :
il faut reposer la clé.

## `$8F9A` : véhicules gardiens

Trois véhicules de deux sprites (corps `$7A90/$7AA0/$7AB0` en 3 images,
dessus `$7A80` couleur `$8F0B`) : ces sprites et les tables de sons
`$7AC0-$7AFF` occupent le champ « police » des textes (`$7A80-$7AFF`), qui
n'a donc pas de sens au niveau 5.

| # | Salle | Type `$8F02` | Ronde (`$93F4/$93FA` ↔ `$93F7/$93FD`) | Qui il chasse |
|---|---|---|---|---|
| 0 | `$0F` | 2 | (77,16) ↔ (77,128) | le joueur seul (`$00`), pas un joueur dans un robot |
| 1 | `$1F` | 3 | (14,80) ↔ (84,80) | le joueur ou le robot qui le contient ; jamais pendant la minuterie |
| 2 | `$0E` | 3 | (100,128) ↔ (100,32) | idem, seulement si X ≥ 93 (zone des boutons) |

- Ronde (`$901D`) : 2 unités par tour vers le point visé, puis demi-tour.
- `$918D` mémorise le **bord d'entrée** (gauche X < 7, droite X ≥ 127,
  bas Y < 16, haut Y ≥ 161) et sa position. Le véhicule attaque quand
  l'objet s'est éloigné de ce bord (`$91FB` : X ≥ 28 depuis la gauche,
  X < 105 depuis la droite, Y ≥ 48 depuis le bas, Y < 128 depuis le haut).
- Attaque (`$9287`) : pas jusqu'à (28,39) par tour (`$ACF8`) ; quand le pas
  du tour fait moins de 29 (|dx| + |dy|), l'objet est saisi :
  **`$8ED4` ← objet** (le joueur ne lit plus le clavier, un robot ne bouge
  plus) ; sous 9, le retour commence, son `$0A`. C'est le rôle de `$8ED4`,
  laissé ouvert dans [simulation.md](simulation.md).
- Retour (`$9332`) : véhicule et prise reviennent de 2 unités par tour au
  point d'entrée ; libération (`$8ED4 = $FF`), son `$0B`.

**[vérifié]** salle `$0F`, joueur entré par la gauche en (3,80) puis
porté en X = 48 : saisi au tour suivant (`$8ED4 = 0`), ramené à (3,80) en
23 tours, relâché.

À faire : traverser `$0F` **à l'intérieur d'un robot** (le véhicule 0 ne
voit que l'objet `$00`) ; passer `$1F` pendant la minuterie ; laisser un
robot seul presser les boutons de `$0E`.

## `$0B1A` : le Disk-O-Tek (« On a clear disk you can seek forever »)

Salles `$32-$39` (`$18D9`) : un lecteur de disquette géant (« Robart »,
« RO400 Disk Drive »), le disque est le cercle `$34-$37`. Le joueur, ou le
robot qui le contient, y est **poussé chaque tour** le long d'un parcours
de 18 étapes ; `$9C30 = 1` (passe-muraille annulé). Rien ne se passe à
l'étape 0 tant que X < 56.

Étape *i* : salle `$18E1`, seuil `$18F3`, octet de direction `$1905` (bit 0
axe X/Y, bit 1 « < » ou « ≥ », puis un pas de ±7 en X et ±16 en Y codé en
longueur variable). L'étape suivante commence quand le seuil est franchi
dans sa salle ; le pas est limité par les murs (`$AD40`), on glisse le long
des parois.

| Étapes | Salles | Trajet |
|---|---|---|
| 0-1 | `$32` → `$33` | monter (Y ≥ 140), puis vers la droite |
| 2-4 | `$39` | haut, gauche, haut |
| 5-6 | `$37` | droite en haut (Y = 160, passe près du disque `$08`), puis diagonale vers le bas |
| 7-8 | `$36` | droite, monter |
| 9-10 | `$35` | monter, gauche |
| 11-12 | `$34` | gauche, diagonale vers le bas (si l'on tombe en `$37` à ces étapes : retour à l'étape 6) |
| 13-15 | `$38` | gauche, monter, droite |
| 16-17 | `$33` → `$32` | monter, gauche ; puis étape 0 |

**[vérifié]** joueur posé en (58,82) salle `$32` : tour complet
`32 → 33 → 39 → 37 → 36 → 35 → 34 → 38 → 33 → 32` en moins de 260 tours, et
il recommence (X = 63 ≥ 56 en fin de tour).

À faire : se laisser porter jusqu'en `$37`, prendre le disque `$08`
(63,160) en marchant vers lui (les pas du joueur s'ajoutent à la poussée),
et à la fin du tour revenir à X < 56 dans `$32` pour sortir vers `$20`.

## `$0F4F` : serrure sonore (salle `$10`)

« This lock is wired for sound. Beep in time to the flashing receiver. »
« The Disk-O-Tek key is a sonic pattern. Read it from left to right.
Repeat it once. »

- Motif : `$1962` lu de l'indice 11 à 0 : **1 0 0 1 1 0 1 0 0 1 1 0**
  (deux fois `100110`), un bit par tour.
- Le récepteur (décor 7, (126,88), couleur `$8F7F`) clignote ce motif en
  boucle (`$8F4E`) : orange = 1.
- Le bit émis est `$8E7F`, la radio des antennes : 1 si l'entrée d'antenne
  d'un robot alimenté était chaude au tour précédent (`$DCF7`).
- `$8F4C` avance si le bit émis égale le bit attendu, sinon revient à 11
  (aucune tolérance, `$8F4D` reste 0). Après 12 bits justes, la porte 4
  est **inversée** (`$0AF8`).

**[vérifié]** récepteur échantillonné tour par tour :
`1 0 0 1 1 0 1 0 0 1 1 0` ; `$8E7F` forcé selon le motif avant chaque appel
de `$0C23` : `$8F4C` 10 → 0, porte 4 ouverte (position 8).

À faire : câbler un robot (puce horloge, bascules ou enregistreur) pour
que son entrée d'antenne suive 100110100110 au tour près, en commençant
par un 1. Le robot peut être n'importe où (la radio est globale). La dalle
de `$10` est du côté droit : elle ne sert que pour revenir.

## `$0E59` : « Odd before Even, in order! » (salle `$0E`)

- **STARTER** : le joueur en X 75-80, Y < 24 → `$8F84 = 5`, boutons à 7.
- Boutons (décors 8-11, X = 119) : seuls les **robots** comptent (X ≥ 110),
  pas le joueur. Fenêtres Y `$1932`-`$192E` : 125-130 (« 1 »), 93-98
  (« 2 »), 61-66 (« 3 »), 29-34 (« 4 »).
- Ordre (`$1936` = bouton précédent attendu) : **1, 3, 2, 4**. À chaque
  changement de l'ensemble appuyé, chaque bouton appuyé est contrôlé : un
  bouton resté enfoncé pendant qu'on presse le suivant est une faute
  (« Don't linger on the buttons »). Délai : 30 tours entre deux boutons
  (`$8F42 = $1D`).
- Faute ou délai : STARTER éteint, son 4.
- Réussite : **`$8F4B` est inversé** (1 → 0 au premier succès) : la dalle de
  la porte 2 devient active. Un second succès la désactive.

**[vérifié]** télécommande coupée, Sparky porté en X = 112 dans `$0E`,
joueur sur STARTER, Y = 127, 63, 95, 31 avec un tour hors bouton entre
chaque : `$8F41` 0, 2, 1, 3 puis `$8F4B = 0`.

À faire : le joueur reste sur STARTER (hors de portée du véhicule 2) ; un
robot seul monte la colonne de droite en touchant 1, 3, 2, 4 sans
s'attarder ; puis poser le disque `$08` en (53,16) : le plancher (porte 2)
s'ouvre vers `$29`. On peut reprendre le disque, la porte reste ouverte.

## `$0C33`, `$0D22`, `$0E18` : minuterie, fils chauds, grille bleue

### Minuterie de garde (`$0C33`)

Deux interrupteurs, actifs quand `$8F48 = 0` :

| Salle | Zone | Qui | Texte |
|---|---|---|---|
| `$1E` | X < 11, Y 61-67 (mur de gauche) | joueur ou robot | « Deactivate Guard Switch » |
| `$28` | Y < 24 et X ≥ 116 (joueur) / ≥ 109 (robot) | joueur ou robot | « Blue Grid Switch » |

Appui (si `$8F49 = 0`, c'est-à-dire tout le monde a quitté les
interrupteurs depuis la dernière fois) : `$8F48 = $21`, décompte BCD d'une
unité tous les 9 tours (**189 tours**), affiché dans le texte `$2C`
(« 00 ← Timer », déplacé en `$1E` ou `$28` par `$15C3`) ; **portes 5 et 6
ouvertes**. À zéro : portes refermées, couleurs remises.

Tant que la minuterie tourne : le véhicule 1 ne chasse plus, les fils
chauds et la grille ne font rien.

**[vérifié]** joueur posé en (8,64) salle `$1E` : `$8F48` 21, 20, 19…,
portes 5 et 6 en position 12, murs `$74B0`/`$74E3` effacés.

### Fils chauds (salle `$1F`, `$0D3F`)

« Hot wires burn batteries.. » Un **robot** (pas le joueur) hors du
couloir en L (X 56-83 et Y < 120, ou X < 56 et Y 56-119) a sa batterie mise
à 0 (`$1917/$191C` → `$8DE1`…), son `$0E`. Fils dessinés couleur `$8F96`
(5 chauds, 7 pendant la minuterie).

### Grille bleue (salle `$28`, `$0D8F` et `$0DDB`)

Grille 4 × 4 (lignes X 16, 42, 70, 98, 124 et Y 44, 76, 108, 140, 172),
bleue (6) hors minuterie, blanche pendant (`$14AB`).

- Un **robot** touche la grille hors de ce chemin → batterie à 0 :

  | Y du robot | X sûr |
  |---|---|
  | ≥ 172 ou < 28 | partout |
  | 140-171 (rangée du haut) | < 88 |
  | 93-139 | 70-87 |
  | 76-92 | 42-87 |
  | 28-75 | 42-58 |

  C'est le chemin des flèches dessiné dans la salle `$29` : → → → en haut,
  descendre en colonne 3, ← en colonne 2, descendre.
- Le **joueur**, ou le robot qui le contient, entré dans la grille
  (Y 44-171) est renvoyé en salle `$29`, même position, son `$0D`
  (« Your 'bot must ride it alone »).

**[vérifié]** joueur en (64,80) salle `$28` : passé en `$29`. Checkers en
(48,144) : batterie intacte ; en (96,144) : batterie 0. Sparky en (96,80)
salle `$1F` : batterie 0.

### Salle `$29` (`$0E18`)

Hors minuterie : joueur en X ≥ 117, Y < 24 (« Open Door → ») → portes 5 et
6 ouvertes tant qu'il y reste, refermées dès qu'il en sort ; en X < 19,
Y < 24 (« View room ← below ») la salle affichée devient `$28`. La salle
`$29` montre la grille en blanc avec les flèches et les croix.

**[vérifié]** (117,16) : `$8F95 = 5`, portes en position 12 ; X = 64 :
refermées. (10,16) : `$9C2D = $28`.

À faire : depuis `$29`, tenir « Open Door » pendant qu'un robot câblé pour
suivre les flèches descend seul dans `$28` ; il traverse la grille et
appuie sur « Blue Grid Switch » ; pendant les 189 tours, le joueur descend
`$29 → $28 → $3A → $2A`.

## `$0F92` et `$7294` : le transporteur (salle `$2A`)

### Boutons (`$0F92`)

- **STARTER** : le joueur en X 75-80, Y 152-167 (couloir du haut) →
  `$8F8D = 5`, et `$10B5` **pose deux cases de mur** (6,5) et (13,5) : le
  centre est coupé des deux compartiments latéraux.
- 8 boutons (`$193A-$1959`), pressés par n'importe quel objet suivi
  (joueur ou robot) :

  | Bouton | X | Y | Côté |
  |---|---|---|---|
  | 1 / 2 | 14-18 / 110-125 | 94-103 | gauche / droite |
  | 3 / 4 | 14-18 / 110-125 | 126-135 | gauche / droite |
  | 5 / 6 | 14-18 / 110-125 | 46-55 | gauche / droite |
  | 7 / 8 | 32-36 / 95-99 | 32-39 | gauche / droite |

- Ordre **1 à 8** (`$195A`), mêmes règles qu'en `$0E` : pas de bouton
  resté enfoncé, 30 tours au plus entre deux (`$8F47`). Faute ou délai :
  cases rouvertes, STARTER éteint, son 4.
- Après le 8, tant que le délai court : si le joueur est sur « Press
  last » (X 56-60, Y < 24), **`$8F99` augmente** à chaque tour. Rien ne le
  remet à 0.

### Fin (`$7294`, dans les murs des salles `$16-$1D`)

`$7294-$7376` est rangé à `$7000 + 30·$16` : la place des murs des salles
`$16-$1D`, inutilisées au niveau 5 (intérieurs de puces au niveau 1).
`world.py` y dessine donc des murs sans signification.

1. Si `$8F99 ≠ 0` et la salle affichée est `$2A` : `$7343` dessine la
   plate-forme, silhouette du joueur (sprite 0) en (70,20) et cadre
   orange X 67-78, Y 17-39.
2. Si le joueur est **exactement** en X = 70, Y = 20 et a le sprite 0
   (pas le fer à souder) : couleur 4, puis une boucle prévue pour
   disperser le sprite (`$D6BD`, écart `$8E97` croissant) avec une note
   montante tous les 6 tours (`$8ED2`), jusqu'à `$8E7E ≥ 9`.
3. Son 9 (fanfare), puis `$09C4` : salle `$3D` « CONGRATULATIONS! Be sure
   the Robot Odyssey I disk is in the drive. Then press ESC. », attente de
   ESC seulement.
4. `$097E` : `$02D0 = 2`, `$02D1 = 5` ; `$09A7` : `$02CF = $A7`,
   `$02D2 = 4`, saut au vecteur RESET.

**Dispersion jamais vue** : `$8E7E` et `$8ED2` sont des temporaires
communs. `$8F9A` traite le véhicule 0 en dernier et, joueur hors de `$0F`,
finit par `$923C` qui laisse `$8E7E = $FF`. `$FF ≥ 9` : on passe
directement à la fanfare. Au niveau 4, la même boucle (`$174A`) utilise des
variables à elle (`$8F0C/$8F0D`). **Défaut de l'original [vérifié]** (voir
la fin du document).

**[vérifié]** `$8F99 = 1`, joueur en (70,20) salle `$2A` : `$72D3` avec
`$8E7E = $FF`, saut immédiat en `$7324`, écran « CONGRATULATIONS! » ;
ESC → `$02CF-$02D2 = A7 02 05 04` au saut. Séquence complète aussi
jouée par pokes : joueur sur STARTER puis sur les boutons 1 à 8, un tour
dehors entre chaque, `$8F46` 0 → 7, puis « Press last » : `$8F99 = 2`.

### Après la requête : la séquence de fin

Le module résident (état 2, `$02D1 = 5`) charge la fin (`$40F0`,
programme `$02E` en `$6000`, images `$009` en `$6300`, bitmap `$6200` du
bloc `$03E`, voir [graphics.md](graphics.md)). **[vérifié]** images
successives : écran noir, Robotropolis (`$9332`) puis le trou (`$8BBA`),
traversés par le petit robot (bitmap XOR `$6200`, l'icône du menu), puis
la chambre avec le dormeur et sa bulle « Z ». Enfin, en police `$0300` :
« Congratulations!! You are one of the few, true Robot Masters. Send in
your name and address to register in the ROBOT MASTERS' CLUB. » avec le
robot. Le programme (`$6163` : `JSR $0803`, op 6 bitmap `$6200` ligne
`$88` colonne `$1E`, op 2) finit par `JMP $6169` : **boucle infinie**,
aucune touche n'en sort (PC = `$6169` après ESPACE). Seul RESET ou
l'extinction relancent le jeu.

## `$13B3` : décor par salle

Sprites `$19DA` (index pair Y) posés en (`$19EA`, `$1A08`) avec la couleur
`$8F78+x` :

| Salle | Éléments |
|---|---|
| `$02` | 0 : serrure de la clé (98,48) |
| `$20`, `$0E`, `$2A`, `$10` | 1-4 : dalle du disque (sprite `$2D`) |
| `$10` | 5, 6 : haut-parleurs ; 7 : récepteur clignotant (126,88) |
| `$0E` | 8-11 : boutons 1-4 ; 12 : STARTER (77,16) ; trait blanc X = 98 |
| `$2A` | 13-20 : boutons 1-8 ; 21 : STARTER (77,160) ; 22 : « Press last » (56,16) |
| `$1E` / `$28` | 23 / 24 : interrupteurs ; texte de minuterie |
| `$28`, `$29` | grille (`$1571`) ; `$29` : 28 « View », 29 « Open Door » |
| `$1F` | fils chauds en L (`$14D2`) |
| `$37` | 25-27 : voyants du disque, alternés tous les 2 tours |
| `$15` | chargeur (sprite `$20`) |

## Solution imposée par le code

Ordre des passages obligés ; d'autres chemins existent entre les salles
(`$13`, `$22-$25`, `$1E`).

1. Salle `$02` : poser la clé `$FA` sur (94,48) → porte 0.
2. `$03 → $04` : traverser les files (choc en `$04` = retour en `$02`,
   porte fermée).
3. `$0F` : traverser **dans un robot** (le véhicule 0 ignore alors le
   joueur).
4. `$0C → $20 → $32` : le Disk-O-Tek ; prendre le disque `$08` en `$37`,
   ressortir en `$32` avec X < 56.
5. `$20` : disque sur (53,16) → plancher (porte 1) ; `$11 → $21 → $06`.
6. `$10` : faire émettre 100110100110 par une antenne → porte 4 ; puis
   `$05 → $12 → $15` (chargeur de cristaux).
7. `$0E` : joueur sur STARTER, un robot seul presse 1, 3, 2, 4 ; disque sur
   (53,16) → plancher (porte 2) ; descendre en `$29`.
8. `$29` : tenir « Open Door » ; le robot seul descend dans `$28`, suit les
   flèches et appuie sur « Blue Grid Switch ». Pendant 189 tours : joueur
   `$29 → $28 → $3A → $2A` (en emportant le disque).
9. `$2A` : disque sur (60,160) → porte 3. Un robot dans chaque compartiment
   latéral, joueur sur STARTER (les compartiments se ferment), boutons 1 à
   8 en alternant gauche/droite, sans traîner ; le joueur court sur
   « Press last », puis se place exactement en (70,20) → fin.

Conséquence du code non essayée en jeu : l'interrupteur de garde de `$1E`
neutralise aussi la grille et ouvre les portes 5 et 6 ; un joueur assez
rapide (`$1E → $15 → $0E → $29 → $28`, porte 2 ouverte) passerait la
grille sans robot **(?)**.

## Méthode (a2shot)

Ce qui marche pour arriver au niveau 5 avec ses objets : depuis la
première salle du niveau 1, sauter au niveau 4 par `$0AA0` (Y = 3), lancer
la sortie du niveau 4 (`$0AFF` : tri, placement du disque), ESC :

```sh
A=../dev/tools/a2shot/a2shot
$A --disk original/A_ROBOTROPOLIS.woz wait:2500 key:"\r" wait:900 key:"\r" \
   wait:6500 regs:00:00:03 go:0AA0 wait:1500 go:0AFF wait:100 \
   key:$'\e' wait:1500 shot:niveau5.png
```

Le joueur est alors en salle `$28` (celle du niveau 1, la sortie du
niveau 4 ne change pas sa salle), les robots en `$3F`. Poser
`$02D0 = 2`, `$02D1 = 4` (et `$02CF = $A7`) puis `reset` **ne marche
pas** : le code reste celui du niveau 1. `regs:00:00:04 go:0AA0` charge le
niveau 5 directement, mais avec les objets du niveau 1.

Déplacer un objet : `poke:9C2F:OBJ poke:9C2E:SALLE call:9E07:5` puis
`poke` de X/Y. Avancer d'un tour : `until:08A6:300 until:0853:300`.
`watch:` et `storewatch:` ne rapportent rien après un `until:` ; seul
`wait:` les fait jouer.

## Points ouverts

- **Robots au niveau 5** : la sortie du niveau 4 envoie en `$3F` tout objet
  libre, robots compris ; seul l'objet tenu passe (constaté sur un
  passage forcé). Or `$0E` demande un robot et `$2A` deux (un par
  compartiment). D'où viennent-ils au vrai jeu ? À recouper avec le
  décodage de la sortie du niveau 4 **(?)**.
- **Clé `$FA`** : rien ne la place au niveau 5 ; elle doit venir avec le
  joueur (tenue, ou dans un intérieur de robot) **(?)**.
- Sprites que la sortie du niveau 4 recopie (`$1808 → $6A30`,
  `$1828 → $6CC0`, `$1858 → $6BF0`) : dalles, boutons, disque ; le disque
  `$08` garde le sprite `$2F`, non recopié **(?)**.
- Dispersion du transporteur jamais jouée : **défaut de l'original
  [vérifié]**. La boucle `$72D3` n'initialise ni `$8E7E` ni `$8ED2` ; elle
  n'avancerait `$8E7E` de `$FF` à 1 que si `$8ED2 > 5`. Mesuré à quatre
  instants différents : toujours `$8E7E = $FF`, `$8ED2 = 0`, saut direct à
  la fanfare (`$7324`).
- `$8F99` repasse à 0 après 256 tours sur « Press last » (incrément sans
  borne) : sans effet en pratique.
- Renvois après un choc (`$1974`) : la logique de la table n'est pas
  évidente ; elle utilise la salle affichée, pas celle de l'objet.
- Chemin exact de sortie du Disk-O-Tek et piège `$37` aux étapes 11-12 :
  déduits du code, seul le tour complet a été vérifié.
- Raccourci par l'interrupteur de `$1E` : non essayé.
- Sentinelle `$22/$23` trouvée en salle `$07` dans le passage forcé : le
  code du niveau 5 ne s'en sert pas.
