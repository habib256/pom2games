# La simulation : boucle principale, circuits, robots, joueur

*[← ANALYSE](../ANALYSE.md)* · structures : [world.md](world.md)

Tout est décrit d'après le code Apple II (désassemblé avec
`tools/disasm.py` sur `build/eng.bin` : vidage en jeu + bloc `$080` en
`$D000` banque 2). Les points vérifiés dans l'émulateur sont signalés
**[vérifié]** avec la commande a2shot correspondante.

## Principe : le signal est une couleur

Il n'y a pas de tableau des niveaux logiques : **la couleur d'un objet
(`$6200`) est son niveau**. 5 (orange) = 1, toute autre couleur = 0.
Deux tables de conversion : `$8389[couleur]` → bit (seul l'index 5 vaut 1),
`$8391[bit]` → couleur (`$07`, `$05`). Un fil est dessiné de la couleur de sa
source (`$FC62`), d'où les fils « chauds » orange de l'écran.

## Cadence

Une itération de la boucle principale = **un tour** de simulation. Mesuré
**[vérifié]** (`until:085B` répété) : ≈ 203 000 cycles dans la salle
d'accueil (≈ 5 tours/s), 228 000 à 267 000 dans la salle des trois robots
(≈ 4 tours/s) : la durée dépend du dessin, il n'y a pas d'horloge fixe. Les
touches tapées dans le même tour se remplacent (une seule est vue).

## Boucle principale (niveau 1, `$085B-$0939`)

Le code est dans le bloc du niveau ; l'ordre est le même aux niveaux 2-5,
avec les routines du niveau intercalées (voir [world.md](world.md#niveaux-2-à-5)).

| # | Appel | Rôle |
|---|---|---|
| 1 | `$A90C` (si `$8ED4 ≠ 0`) | lecture clavier/manette, calcul du pas du joueur `$9C22/$9C23`, murs, déplacement `$9DB3` |
| 2 | `$0980` | touches du niveau : `?`/`/` indices (salle `$01`), `ESC` menu (salle `$00`), `L` labo de puce, triche `$03FF` |
| 3 | `$DFA3` | image de marche du joueur (sprite 0) |
| 4 | `$BE6C` | front du bouton (`$8E3A` : 1 au tour de l'appui) |
| 5 | `$1AB0` | touche `T` : boîte à outils (l'amener, l'ouvrir/fermer) |
| 6 | `$FE18` | mémorise le pas du tour (`$8E84/$8E85`) pour déplacer les fils |
| 7 | `$1B10`, `$A5CD` (outil = joueur) | boîte à outils ouverte ; **prendre/poser** |
| 8 | `$093D` | son de prise/dépose |
| 9 | `$9C53` | **objets attachés** suivent leur porteur |
| 10 | `$BE86` | touche `R` : télécommande (`$8DA7`) |
| 11 | `$BDE1` | touches `C`/`S` : joueur ↔ fer à souder |
| 12 | `$FE25` (si `$8ED4 = $FF`) | **entrer / sortir d'un robot** |
| 13 | `$DE95`, `$DF81` | cristaux : recharge des batteries, chargeur, clignotement |
| 14 | `$0CC5`, `$918E`, `$1115` | niveau 1 : Ampire Bot, (données `$918E`), placement aléatoire |
| 15 | `$D000` | **robots : propulseurs, murs, pare-chocs, mouvement** |
| 16 | si `$8DA7 = 1` : `$D832` | **capteurs** (salle, direction, contact) |
| 17 | `$DA90` | **pinces**, puis antennes (`$DCF7`) |
| 18 | `$DE10` | **batteries** : décharge de base |
| 19 | `$F0CC` | **fils** : propagation |
| 20 | `$F04B` | **portes**, puis **bascules** (`$F17B`) |
| 21 | `$F56B` | **puces** (programmes en banque 1), broches `$F44D` |
| 22 | `$F5A9` | couleur des puces (6, sauf celle en édition) |
| 23 | `$1740` | niveau 1 : dalles et portes |
| 24 | `$DD59` | salle affichée `$9C2D` (fenêtre d'un robot), interrupteur des propulseurs |
| 25 | `$9D03`, `$A2A2`, `$1322`, `$9D18`, `$1037`, `$D2BC`, `$D72B`, `$187C`, `$0C23`, `$8F6C`, `$0FB0`, `$DDD0`, `$1E58` | dessin : fond et murs, textes, objets, sortie du niveau (`$1037`), robots, tableau de bord intérieur, Ampire Bot… |
| 26 | `$F7BE`, `$F5C2` (outil = fer) | **soudure** |
| 27 | `$FC62`, `$18E2`, `$F44D`, `$DA44`, `$A6AD` | fils de la salle, broches de puces, cadres des capteurs, contour de l'objet visé |
| 28 | `$AEED` | affichage (copie de la page de composition) |
| 29 | `$9F3C` | sons en attente (`Ctrl-S` coupe le son, `$9F3B`) |

Conséquence de l'ordre : un capteur ou un pare-chocs mis à jour au tour *t*
est recopié par les fils au même tour (19 après 15-16), mais la sortie d'une
porte calculée en 20 n'atteint sa destination qu'au tour *t+1*.

## La télécommande (`$8DA7`)

`R` inverse `$8DA7` (`$BE86`) et change le sprite de l'objet `$FC` (`$36`
télécommande visible, `$1A` vide). Quand `$8DA7 = 0`, les étapes 16 à 21 ne
sont pas exécutées et `$D000` met à 0 l'animation de tous les propulseurs :
**tout le monde s'arrête** (capteurs, pinces, batteries, fils, portes, puces,
robots). Au chargement d'un niveau, `$8DA7` est ramené à 0 ou 1 (`$0841` :
5 → 1, autre valeur → 0). **[vérifié]** `build/goto_robots.sh peek:64F0:6
wait:60 peek:64F0:6 key:R wait:10 peek:64F0:6 wait:60 peek:64F0:6` : les
robots bougent (`62→58`, `29→33`), puis plus du tout après `R`.

## Fils (`$F0CC`)

```
pour n = 0 .. $FE :                     ; un seul passage, ordre croissant
    d = $8618[n]
    si d ≠ 0 :
        si $25 ≤ d < $39 : $8B07[d] = bit(couleur(n))   ; entrée de bascule
        sinon            : couleur(d) = couleur(n)
pour chaque nœud n = $D1 .. $DF :       ; nœuds, avec file d'attente
    recopie couleur(n) vers $8618[n] et vers $8A7E[n] (2ᵉ sortie)
    si une destination est elle-même un nœud (sprite $19) : la mettre en
    file ($8E65) pour la propager dans le même tour
```

- Un passage unique en ordre croissant : une chaîne A → B → C se propage en
  un tour si les numéros croissent, sinon il faut un tour par maillon.
- Le joueur (`$00`) ne peut pas être destination (0 = pas de fil).
- Les nœuds sont les seuls objets à deux sorties ; la file évite qu'une
  chaîne de nœuds prenne plusieurs tours.

## Portes (`$F04B`)

Pour chaque corps de porte `y = $67, $6A … $CD` dont le type
`$8CB3+y` n'est pas 0 :

| Type | Sortie = couleur de `y` |
|---|---|
| 1 | `in1 ET in2` (`$F090`) |
| 2 | `in1 OU in2` (`$F0A4`) |
| 3 | `in1 OUX in2` (`$F0B8`) |
| 4 (ou autre) | `NON in1` (`$F07E`) |

avec `in1 = couleur(y+1)`, `in2 = couleur(y+2)`. **[vérifié]**
`goto_robots.sh peek:6273:3 poke:8D26:01 wait:10 peek:6273:3 …` : la porte 5
(`$73`, NON, entrées à 0, sortie 5) passe à 7 dès qu'on change son type en ET
(`$8D26 = 1`), et revient à 5 quelques tours après le retour à 4.

## Bascules (`$F17B`)

10 bascules, moitiés `L = $25+2k`, `R = $26+2k`. Chaque moitié a un état
(`$8AF3+objet`, 0/1, toujours complémentaires) et une entrée
(`$8B07+objet`, écrite par les fils). À chaque tour :

```
e = entrée(R)·2 + entrée(L)
e = 1 (seule L active) et état(L) = 0  -> inverser les deux moitiés
e = 2 (seule R active) et état(R) = 0  -> inverser
e = 0 ou 3                             -> rien
couleur(L) = état(L) ; couleur(R) = état(R)
```

C'est une bascule RS : un 1 sur l'entrée d'une moitié met cette moitié à 1.
Les fils qui *partent* d'une moitié transportent son état (les moitiés sont
à la fois entrée et sortie).

## Puces (`$F56B`, `$F44D`)

Pour chaque puce (`$F56A` = 7 … 0), le programme compilé en banque 1
(pointeur `$F000+puce`, interprète `$F208` : codes 1 ET, 2 OU, 3 OUX, 4 NON,
5-7 bascules, sous-puces, fin) est exécuté, puis `$F44D` échange les valeurs
entre les 8 broches et les objets câblés (`$8C9A/$8CDA`) : broche d'entrée →
lit la couleur de l'objet, broche de sortie → écrit la couleur (ou l'entrée
de bascule si l'objet est une moitié de bascule). Le détail du format des
programmes relève de l'analyse du labo et des puces.

## Robots (`$D000`, banque 2)

Pour chaque enregistrement `$8DC9 + 26·r` jusqu'au `$FF` (`$D01B`), les
champs sont copiés en `$8EA0-$8EBA`, traités, puis réécrits :

1. **Propulseurs** (`$D152`, pour chaque côté 3, 2, 1, 0) : le pare-chocs du
   côté repasse à 7 ; si batterie > 0, interrupteur fermé et broche du
   propulseur chaude : animation 1→2→3→1 et **+60 ($3C) à la consommation
   du tour** ; sinon animation 0.
2. **Mur devant** (même boucle) : test de cases (`$B40B`) juste au-delà du
   bord correspondant — côté 3 à `X+8` de la moitié droite, côté 2 à `Y+20`,
   côté 1 à `X−2`, côté 0 à `Y−4`. Mur → **pare-chocs chaud** (couleur 5,
   son 2 la première fois) et pas de mouvement de ce côté.
3. **Mouvement** (`$D1D7`) : sinon, si le propulseur est actif, le robot
   avance de `$8361/$8365[côté]` — côté 0 (0,−4) bas, 1 (−2,0) gauche,
   2 (0,+4) haut, 3 (+2,0) droite — par `$9DB3` (passage de salle compris),
   la moitié droite suit (`+5,0`). Un robot tenu par le joueur ou égal à
   `$8ED4` ne bouge pas. Plusieurs propulseurs s'additionnent (un pas par
   côté et par tour).
4. **Batterie** (`$D120` → `$DE21…`) : la consommation du tour est ajoutée
   à l'accumulateur 16 bits du robot ; à chaque débordement, batterie −1.

Les pare-chocs ne détectent que **les murs** (cases) : il n'y a pas de test
robot/robot ni robot/objet dans `$D000`.

### Batteries et cristaux

- `$DE10` ajoute en plus **30 ($1E) par tour** à chaque robot dont la
  batterie n'est pas vide. Durée : 15 × 65 536 / 30 ≈ 32 800 tours à vide
  (≈ 2 h à 4-5 tours/s), ≈ 10 900 tours avec un propulseur allumé.
- Batterie 0 : propulseurs, pinces et antennes inactifs (les capteurs
  continuent de fonctionner).
- `$DE95` : un cristal (sprite `$39`, objets `$F6-$FB`) **chargé** (couleur
  ≠ 7) posé dans la prise de batterie d'un intérieur de robot (X 19-23,
  Y 25-41, salles `$09/$0A/$0B/$0D`) recharge à 15 une batterie **vide**,
  remet l'accumulateur à 0 et se décharge (couleur 7, son 7). Un cristal
  **déchargé** posé près du chargeur (`$8454` salle, `$8455/$8456` position,
  ±4/8 unités) devient chaud (son 8). `$DF81` fait clignoter les cristaux
  chargés (5 ↔ 6).
- Jauge et interrupteur dessinés dans l'intérieur par `$D72B`.

### Interrupteur des propulseurs

`$DD59` : si le joueur est dans un intérieur de robot en `X ≥ $74`,
`Y < $26` au tour où il appuie sur le bouton (`$8E3A = 1`), l'octet 25 de
l'enregistrement (`$8DE2`…) est inversé. En `X ≥ $74`, `Y ≥ $8C` (coin
haut droit, la « fenêtre »), la salle **affichée** devient celle où se
trouve le robot : on voit dehors tout en restant dedans.

### Capteurs (`$D832`)

Un capteur est un objet-corps dont le **sprite est celui de l'objet
cherché** (clé, cristal…) ; il cherche, parmi les objets `$FB…$F6` puis
`$08…$03`, un objet libre (ni attaché ni tenu) de même sprite **dans la salle
du robot** s'il est posé dans un intérieur (`$D8CA`), sinon dans sa propre
salle.

| Capteur | Corps → sorties | Sortie chaude quand… |
|---|---|---|
| de salle (`$D83C`) | `$10-$12` → `$19-$1B` | l'objet cherché est dans la salle |
| de direction (`$D910`) | `$0D-$0F` → 4 sorties `$5A+4k…` | sortie 0 : objet plus haut (`Y > Yrobot+7`) ; 1 : plus bas (`Y ≤ Yrobot−8`) ; 2 : à droite (`X > Xrobot+8`) ; 3 : à gauche (`X < Xrobot−4`) |
| de contact (`$D9A4`) | `$13-$15` → `$1F-$21` | l'objet touche une moitié du robot (`$A835`, collision au pixel) |

### Pinces (`$DA90` → `$DAEA`)

Par robot, si l'entrée de pince (`$82DF`) est chaude et la batterie non
vide : si le robot ne tient rien (`$8DAD+r`), chercher un objet saisissable
qui touche le robot (`$DC82` → `$A7EE` avec le test `$DCD7` :
objets `$03-$08` et `$F6-$FB` seulement, ni attaché ni tenu par le joueur),
l'attacher au robot (`$DC48` : porteur = moitié gauche, décalage pris dans
`$82E7/$82EB` selon le côté touché, saisissable `$FF`), sortie de pince
chaude (`$82E3`), son 3. Si l'entrée retombe : l'objet est relâché
(porteur `$FF`, saisissable `$00`), sortie à 7, son 4. Le sprite de pince
affiché par côté est dans `$8DB9+4r`.

Tenir coûte : tant que l'entrée est chaude et que le robot tient un objet,
`$DB64` ajoute **30 (`$1E`)** à son accumulateur (`$DE21`), en plus de la
décharge de base ; si la batterie tombe à 0, l'objet est lâché (`$DB26`).

Sprites des pinces : dans l'aventure, haut `$3B`, droite `$3C`, bas `$3D`,
gauche `$3E` (le `$3A` du monde est un autre dessin) ; dans le labo et les
leçons, `$3A-$3D` (vérifié sur les images de sprites des blocs `$090`,
`$0C6` face B, `$06D` face C).

### Antennes (`$DCF7`)

Les antennes forment une **radio commune** : si, à un tour, l'entrée
d'antenne (`$82F3`) d'un robot alimenté est chaude, `$8E7F` passe à 1 et
le son 5 est joué ; au tour suivant, **toutes** les sorties d'antenne
(`$82EF`) des robots alimentés sont chaudes pendant un tour.

## Joueur

### Déplacement et murs (`$A90C`, `$AD40`)

- Clavier (`$AA25`, table `$9C13` copiée par le niveau : `I M J K`,
  Ctrl-`I M J K`, espace, etc.) ou manette (`$AACB`, palettes `$C064/$C065`)
  → pas `$9C22/$9C23`. **[vérifié]** pas de 7 unités en X, 16 en Y ;
  Ctrl : 1 unité.
- Si `$9C30 ≠ 0` (défaut), `$AD40` teste les 4 coins du sprite
  (décalages `$AEDF/$AEE3` : X+0/+6, Y+0/+15) contre les cases ; en cas de
  mur, le pas est raccourci jusqu'au bord de la case, axe par axe (on
  glisse le long des murs). `$9C30` est inversé par une touche égale à
  `$03FF` (`$0996` au niveau 1). Par défaut `$03FF` vaut `$03`, qu'aucune
  touche ne produit (bit 7 toujours mis). La séquence Ctrl-A, Ctrl-L, `T`
  du menu y écrit `$85` : Ctrl-E devient alors le **passe-muraille** du
  joueur. **[vérifié]** salle `$28`, 15 × `I` : arrêt sous le mur (Y=`$A0`)
  sans triche ; avec, le joueur traverse le mur, ressort par le bas (bord
  fermé) et finit en Y=`$10`. Les robots ne lisent pas `$9C30`. Au PC,
  c'est aussi Ctrl-E, autorisé par un octet de `joyfile.dat`.
- `$A934` : un pas qui sort de la salle est ramené au bord exact (`X=$86`
  ou `Y=$B1`, `$A979`), puis `$9DB3` fait passer dans la salle voisine
  (liens `$6EC0-$6F80`).

### Prendre et poser (`$A5CD`)

Au front du bouton / de l'espace (`$9C3B|$9C3C`) : si le joueur tient un
objet (`$9C26`), il le lâche ; sinon `$A8FC` cherche dans la salle un objet
saisissable (`$6900 = 0`) qui touche le joueur (`$A7EE` + `$A835`,
collision au pixel des sprites). L'objet tenu est attaché au joueur avec le
décalage du moment (remonté jusqu'à la racine si on a saisi une pièce
attachée : on prend le robot entier par sa moitié droite, une porte par son
entrée…). Pendant le transport, `$B8E6` déplace les extrémités de fils
attachées à ses broches ; si une extrémité sortirait de la salle
(X ∉ 1..`$83`, Y ∉ 1..`$AE`), le fil est coupé (`$F5D3`).

### Entrer dans un robot

`$FE25` (appelé quand `$8ED4 = $FF`, et pas pendant une soudure en cours) :
si le joueur touche un robot (`|Xj − Xr| < 6`, `Yr+4−Yj < 9`) qui n'est pas celui qu'il
tient, il passe dans la salle intérieure (`$8204`) à une entrée qui dépend
de la direction de marche : depuis la gauche X=8, depuis la droite X=`$7B`
(Y=`$5F`), par le haut ou le bas X=`$46`, Y=`$12` ou `$A0` — sauf si
`$FEEB` trouve un mur sous le robot. Sortie (`$FF23`) : quand le joueur
franchit un bord de l'intérieur (X < 7 vers la gauche, X ≥ `$7F` vers la
droite, Y ≥ `$A1` vers le haut, Y < `$10` vers le bas), il est posé à côté
du robot (décalages −2/+7, ±6) dans la salle du robot, si la place est
libre. Les objets tenus suivent (ils sont attachés au joueur).

### Outils : boîte, soudure

- `T` (`$1AB0`) : amène la boîte à outils `$E1` dans la main du joueur, ou
  l'ouvre/ferme s'il est dans sa salle (`$8DAC`). Boîte ouverte (`$1B10`) :
  on en sort des portes, nœuds et bascules (compteurs `$8DA8-$8DAA`,
  affichés par `$1DFE` dans le texte `$0F`).
- `S` / `C` (`$BDE1`) : échange sprite et couleur du joueur avec le fer
  `$FD` (`$8DA6 = $FD`) ou les reprend (`$8DA6 = 0`). Avec le fer, `$F7BE`
  mémorise une première broche touchée au bouton (`$8E40-$8E46`, son 6),
  puis relie la seconde et crée le fil dans la bonne table (`$8618`, 2ᵉ
  sortie de nœud ou fil de puce) selon le type de broche (`$8393`) ;
  `$F5D3` efface les fils d'une broche (par type : nœud `$F674`, entrée
  `$F704`, sortie `$F72A`, puce `$1F27`, bascule). *Détail de la création
  non relu instruction par instruction.*

## Changement de salle et affichage

La salle affichée `$9C2D` est celle du joueur (recopiée à chaque tour en
`$08C4`), sauf par la fenêtre d'un robot. Le moteur ne simule pas « la
salle courante » : toute la boucle porte sur les 256 objets et les 4 robots,
quelle que soit leur salle ; seul le dessin est limité à `$9C2D`. Les robots
continuent donc de se déplacer, de saisir et de se décharger hors de vue.
Les sons (`$0806` → `$0961`) sont associés à une salle et ne sont joués que
si elle est celle du joueur (`$9F65`).

Numéros de sons utilisés (`X` à l'appel de `$0806`) : 0 poser, 1 prendre,
2 pare-chocs, 3 pince saisit, 4 pince relâche, 5 antenne, 6 soudure,
7 batterie rechargée, 8 cristal chargé, 9 montée de niveau, `$0A` Ampire Bot.
Les effets sont décrits par quatre tables de 12 octets dans le code du
niveau (niveau 1 : `$18B2`, `$18BE`, `$18CA`, `$18D6`, copiées vers
`$9F02/$9EEA/$9EF2/$9EFA` par `$0961`) : 12 effets sur Apple II (le PC en
a 28).

## Questions ouvertes

- `$8ED4` : objet immobilisé (`$FF` en jeu normal). Les gardes des
  niveaux 2 et 3 et les véhicules du niveau 5 y mettent le joueur saisi :
  il ne lit plus le clavier et ne peut entrer dans un robot
  ([niveau5.md](niveau5.md)).
- L'ordre exact des tests quand deux propulseurs opposés sont allumés
  (déplacements successifs dans le même tour) n'a pas été vérifié en jeu.
- Collision pixel `$A835` : décrite d'après le code (sprites superposés sur
  la zone commune), pas mesurée.
- Création d'un fil au fer à souder et cas particuliers (fil vers une
  moitié de bascule, vers une puce) : routines identifiées
  (`$F7BE`, `$F86A`, `$FC2C`, `$F674-$F72A`), non décodées en détail.
- Programmes des puces et format en banque 1 : hors de ce document.
