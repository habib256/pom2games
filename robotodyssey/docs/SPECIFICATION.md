# Moteur : spécification pour une réimplémentation

Jeu de logique en salles. Le joueur se déplace, saisit des objets, entre
dans trois robots (Sparky, Checkers, Scanner) et les programme en câblant
des portes, des bascules, des capteurs et des puces. Cinq mondes se
succèdent. Le même format de monde sert aussi au bac à sable, aux leçons
et à l'atelier de puces.

Un tour de simulation est l'unité de temps. Toute la ville est simulée à
chaque tour ; seule la salle du joueur est dessinée. La cadence d'origine
suit le coût du dessin, environ 4 à 5 tours par seconde. Les énigmes sont
réglées pour cette vitesse.

## Mondes

| Id | Rôle |
|---|---|
| 0 | égouts, premier monde |
| 1 | métro |
| 2 | rues |
| 3 | centre de l'ordinateur central (carte plus lente, textes clignotants, commandes différentes) |
| 4 | passerelles (sections où un choc fait clignoter le joueur, couleur d'indice `0x87`) |
| 21 | leçon : anatomie |
| 22 | leçon : câblage |
| 23 | leçon : capteurs |
| 24 | leçon : boîte à outils |
| 25 | leçon : circuits |
| 26 | leçon : travail d'équipe |
| 27 | atelier de conception de puces |
| 30 | bac à sable (trois robots, boîte complète, puce prototype) |
| 40 | démonstration |

L'aventure charge quatre robots (les trois du joueur et un robot hostile).
Les leçons et le bac à sable en chargent trois. Les sprites de pinces ne
sont pas aux mêmes indices dans les deux cas (voir plus bas).

Le passage d'un monde au suivant joue une animation de transporteur, range
hors du monde les objets qui ne sont pas tenus, place les objets du monde
suivant, puis recharge salles, textes et code propre au niveau. Objets,
robots, circuits et puces persistent d'un monde à l'autre. La fin du
cinquième monde enchaîne une scène de conclusion.

## Coordonnées

Repère du **coin bas-gauche du sprite**, Y vers le haut.

- X : 0 à 133, une unité = 2 pixels. Le sprite fait 7 unités de large
  (14 pixels). X ≥ 134 envoie dans la salle de droite (X − 134). Une
  soustraction qui retombe à 216 ou plus (arithmétique sur 8 bits) envoie
  dans la salle de gauche (X + 134).
- Y : 0 à 176, une unité = 1 pixel, Y = 0 sur la ligne écran 191. Le
  sprite fait 16 pixels de haut. Y ≥ 177 envoie dans la salle du haut
  (Y − 177). Y ≥ 216 envoie dans la salle du bas (Y + 177).
- Pas du joueur : 7 en X et 16 en Y (une case). Pas fin : 1 unité.
- Les fils qui sortent du rectangle X ∈ [1, 131], Y ∈ [1, 174] sont coupés.

## Monde (13 568 octets, `0x3500`)

Dix tableaux de 256 octets, un octet par objet :

| Décalage | Champ | Sens |
|---|---|---|
| `0x0000` | suivant | prochain objet de la même salle, `0xFF` fin de liste. Les listes sont triées par numéro d'objet |
| `0x0100` | sprite | 0 à 63 |
| `0x0200` | couleur | indice de motif ; **c'est aussi le niveau logique** |
| `0x0300` | salle | `0x3F` = absent |
| `0x0400` | x | |
| `0x0500` | y | |
| `0x0600` | porteur | `0xFF` si libre ; sinon l'objet suit ce porteur |
| `0x0700` | décalage x | signé, relatif au porteur |
| `0x0800` | décalage y | signé |
| `0x0900` | saisie | `0x00` saisissable, `0xFF` non |

Puis :

| Décalage | Taille | Contenu |
|---|---|---|
| `0x0A00` | 64 × 16 | sprites |
| `0x0E00` | 64 | tête de liste d'objets de chaque salle |
| `0x0E40` | 64 | couleur de fond |
| `0x0E80` | 64 | couleur des murs |
| `0x0EC0` | 64 | salle au-dessus |
| `0x0F00` | 64 | salle au-dessous |
| `0x0F40` | 64 | salle à droite |
| `0x0F80` | 64 | salle à gauche |
| `0x0FC0` | 64 | réservé, à zéro |
| `0x1000` | 64 × 30 | murs |
| `0x1780` | 256 | bloc réservé (motifs de 16 octets, rôle non utilisé par le moteur) |
| `0x1880` | textes | voir plus bas |

Un lien de salle qui pointe vers la salle elle-même est un bord fermé.
La salle `0x3F` n'existe pas : y placer un objet le retire du niveau.

### Salles fixes

| Salle | Rôle |
|---|---|
| `0x00` | écran de pause (quitter, sauver) |
| `0x01` | titre et indices |
| `0x09` | intérieur de Sparky |
| `0x0A` | intérieur de Checkers |
| `0x0B` | intérieur de Scanner |
| `0x0D` | intérieur du quatrième robot |
| `0x15` | aide de l'atelier de puces |
| `0x16`–`0x1D` | intérieurs des huit petites puces |
| `0x3F` | nulle part |

### Murs

Grille de **20 × 12** cases. Une case fait 7 unités sur 16 (14 × 16 pixels).
Trente octets par salle, trois bandes de quatre rangées, dix octets par
bande. Chaque octet décrit deux colonnes sur quatre rangées :

```
rangée R comptée vers le haut (0 en bas)
octet = 10 × (R div 4) + (colonne div 2)
bit   = 4 × (colonne mod 2) + (R mod 4)     bit à 1 = mur
```

Le test de mur du joueur regarde les quatre coins du sprite (X+0, X+6,
Y+0, Y+15). Un mur raccourcit le pas jusqu'au bord de la case, axe par
axe : on glisse le long du mur. Les robots ne testent qu'une case devant
chaque pare-chocs, et ignorent le drapeau de passe-muraille.

L'indice de couleur 20 ne dessine pas la case (réservé au fond).

### Sprites

Soixante-quatre images de 16 octets. L'octet 0 est la rangée du bas.
Les bits 6 à 0 sont les sept points de gauche à droite ; le bit 7 est
ignoré. Chaque point fait deux pixels. Un sprite qui dépasserait l'écran
n'est pas dessiné du tout.

| Indice | Image |
|---|---|
| `0x00` | curseur / joueur |
| `0x01`–`0x02` | broche entrée-sortie gauche, droite |
| `0x03`–`0x05` | aplats noirs |
| `0x06` | broche entrée vers le bas |
| `0x07`–`0x08` | ET, haut puis bas |
| `0x09`–`0x0A` | OU |
| `0x0B`–`0x0C` | OU exclusif |
| `0x0D`–`0x0E` | NON |
| `0x0F`–`0x12` | broches d'entrée 2 et 3, bas puis haut |
| `0x13`–`0x14` | bascule, droite puis gauche |
| `0x15`–`0x16` | broche entrée gauche, droite |
| `0x17`–`0x18` | broche sortie gauche, droite |
| `0x19` | nœud |
| `0x1A` | vide |
| `0x1B` | boîte à outils |
| `0x1C`–`0x1D` | fer à souder, panne |
| `0x1E` | haut de batterie |
| `0x1F` | pinceau |
| `0x20` | chargeur de cristal |
| `0x21`–`0x28` | petites puces 1 à 8 |
| `0x29` | puce vierge |
| `0x2A`–`0x2B` | propulseur droite, gauche |
| `0x2C`–`0x2F` | animation du propulseur |
| `0x30`–`0x31` | interrupteur fermé, ouvert |
| `0x32` | corps de sentinelle |
| `0x33` | serrure |
| `0x34`–`0x35` | broche sortie haut, bas |
| `0x36` | télécommande |
| `0x37` | bouton |
| `0x38` | clé |
| `0x39` | cristal |
| `0x3A`–`0x3D` | pinces haut, droite, gauche, bas (leçons et bac à sable) |
| `0x3E`–`0x3F` | libres dans les leçons |

Dans l'aventure, les pinces sont décalées : haut = `0x3B`, droite = `0x3C`,
gauche = `0x3E`. Copier un monde de leçon vers l'aventure (ou l'inverse)
recopie ces trois sprites vers les indices de l'autre jeu.

### Objets fixes

`0xFF` veut dire « aucun objet ». `0x00` est toujours le joueur.

Aventure :

| Objets | Rôle |
|---|---|
| `0x01`, `0x02` | moitiés gauche et droite du quatrième robot |
| `0x03` | aimant, ou bouton selon le monde |
| `0x04` | jeton |
| `0x09`–`0x0C` | pince et antenne du quatrième robot, entrée puis sortie |
| `0x22`, `0x23` | sentinelle, gauche et droite |
| `0x24` | poignée de distributeur |
| `0x39`–`0x40` | propulseurs puis pare-chocs du quatrième robot, quatre côtés chacun |

Atelier (les mêmes numéros y ont un autre sens) :

| Objets | Rôle |
|---|---|
| `0x01`–`0x04` | broches extérieures 1 à 4 de la puce prototype (colonne gauche, de haut en bas) |
| `0x05`–`0x08` | broches extérieures 8, 7, 6, 5 (colonne droite, de haut en bas) |
| `0x09`–`0x0C` | quatre quarts du corps du prototype |
| `0x39`–`0x40` | broches intérieures, même ordre : 1, 2, 3, 4, 8, 7, 6, 5 |

Communs :

| Objets | Rôle |
|---|---|
| `0x0D`–`0x0F` | corps des trois capteurs de direction |
| `0x10`–`0x12` | corps des trois capteurs de salle |
| `0x13`–`0x15` | corps des trois capteurs de contact |
| `0x19`–`0x1B` | sorties des capteurs de salle |
| `0x1C`–`0x1E` | entrées de pince de Sparky, Checkers, Scanner |
| `0x1F`–`0x21` | sorties des capteurs de contact |
| `0x25`–`0x38` | dix bascules, moitié gauche puis droite (`0x25`/`0x26` … `0x37`/`0x38`) |
| `0x41`–`0x48` | propulseurs puis pare-chocs de Scanner |
| `0x49`–`0x50` | Checkers |
| `0x51`–`0x58` | Sparky |
| `0x59`, `0x66` | antenne de Sparky, entrée puis sortie |
| `0x5A`–`0x65` | douze sorties des capteurs de direction (quatre par capteur) |
| `0x67`–`0xCF` | 35 portes : corps, entrée 1, entrée 2, de trois en trois (`0x67`, `0x6A`, … `0xCD`) |
| `0xD0` | sortie de pince de Sparky |
| `0xD1`–`0xDF` | quinze nœuds |
| `0xE1` | boîte à outils |
| `0xE2`, `0xE3` | antenne de Scanner |
| `0xE4` | sortie de pince de Scanner, et aussi celle de Checkers |
| `0xE5`, `0xE6` | antenne de Checkers |
| `0xE7`–`0xEE` | huit petites puces |
| `0xF0`/`0xF1` | Sparky, gauche / droite |
| `0xF2`/`0xF3` | Checkers |
| `0xF4`/`0xF5` | Scanner |
| `0xF6`–`0xFB` | six formes libres (cristaux, clé). Dans l'aventure, `0xFA` est la clé bleue |
| `0xFC` | télécommande |
| `0xFD` | curseur du fer |
| `0xFE` | curseur |

Les quatre côtés d'un robot, dans les tableaux de propulseurs, de
pare-chocs et de pinces :

| Indice | Côté | Déplacement si le propulseur est actif |
|---|---|---|
| 0 | bas | (0, −4) |
| 1 | gauche | (−2, 0) |
| 2 | haut | (0, +4) |
| 3 | droite | (+2, 0) |

La moitié droite d'un robot est collée à la moitié gauche, décalée de
(+5, 0).

### Textes

128 entrées, puis un tas de chaînes de `0x1880` octets.

| Décalage | Champ |
|---|---|
| `0x1880` | salle |
| `0x1900` | x |
| `0x1980` | y |
| `0x1A00` | style : 0 normal, 2 grand (caractères doublés) |
| `0x1A80` | police (une seule police est utilisée) |
| `0x1B00` | couleur |
| `0x1B80` | octet bas du pointeur |
| `0x1C00` | octet haut |
| `0x1C80` | tas |

Les chaînes sont en ASCII bit 7 : espace `0xA0`, fin `0x00`, retour
`0x8D`. La police tient en 768 octets, 96 caractères sur 8 rangées.
La rangée 0 est le bas du glyphe (jambages). Les bits 0 à 6 vont de
gauche à droite, le bit 7 est à 0. L'octet de la rangée `R` du
caractère `C` est à `0x9460 + 0x60·R + C` (donc `0x9500` pour l'espace,
rangée du bas). Glyphes propres : l'apostrophe inverse et le guillemet
sont les guillemets courbes, `^` est un disque plein, `{` `}` `~` et
`0x7F` sont les flèches.

Le petit texte (style 0) est posé par union sur des colonnes d'octet
entières, chasse 7 pixels, interligne 9. Il n'a pas de couleur à lui :
les pixels prennent la teinte imposée par le bit 7 du fond (fond 4,
bit 7 levé, donne des points orange et bleus ; fond 0, des points
violets et verts). Il est coupé dès que Y atteint 185.

Le grand texte (style 2) fabrique pour chaque glyphe un sprite 14 × 16
(rangées doublées, bits renversés) et le dessine dans la couleur de
l'entrée, parmi huit aplats. Il avance de 7 unités et descend de 18
pixels au retour à la ligne.

## Circuit (zone utile, calée sur 2 560 octets dans une sauvegarde)

Décalages relatifs au début du circuit.

Fils d'objets ordinaires, un fil au plus par objet source. La destination
0 veut dire « pas de fil » (le joueur ne peut donc pas être une destination) :

| Décalage | Champ |
|---|---|
| `0x0000` | objet piloté |
| `0x0100` | x1 |
| `0x0200` | x2 |
| `0x0300` | y1 |
| `0x0400` | y2 |

Bascules, 20 octets (une moitié chacune) :

| Décalage | Champ |
|---|---|
| `0x0500` | état, 0 ou 1, les deux moitiés sont complémentaires |
| `0x0514` | niveau présent sur l'entrée |

Second fil des nœuds (15 nœuds) :

| Décalage | Champ |
|---|---|
| `0x0528` | objet qui pilote le nœud |
| `0x0537` | deuxième objet piloté |
| `0x0546` | x1 |
| `0x0555` | x2 |
| `0x0564` | y1 |
| `0x0573` | y2 |

Fils de petites puces, 64 au plus :

| Décalage | Champ |
|---|---|
| `0x0582` | y1 |
| `0x05C2` | y2 |
| `0x0602` | x1 |
| `0x0642` | x2 |
| `0x0682` | objet piloté |
| `0x06C2` | broche 0–7, ou `0xFF` si la destination n'est pas une puce |

Réservation des pièces encore dans la boîte :

| Décalage | Champ |
|---|---|
| `0x0702` | 105 octets, type de porte ; seule une case sur trois est utilisée |
| `0x076B` | 15 nœuds |
| `0x077A` | 20 moitiés de bascule, par indice de sprite ; seules les cases paires sont utilisées |
| `0x078E` | sprite de curseur mémorisé, normalement 0 |
| `0x078F` | télécommande : 0 arrêt, 1 marche |
| `0x0790` | nombre de bascules restantes |
| `0x0791` | nombre de nœuds |
| `0x0792` | nombre de portes |
| `0x0793` | boîte fermée |

Types de porte : 0 absente, 1 ET, 2 OU, 3 OU exclusif, 4 NON.

Le format de circuit des leçons diffère légèrement de celui de l'aventure
et du bac à sable. Une sauvegarde d'aventure ou de bac à sable suit le
format décrit ici.

## Robots

La table des pinces précède la table d'état. Chaque pince tient quatre
octets : 0 si ce côté n'a pas de pince, sinon l'indice du sprite à montrer.

Chaque robot occupe 26 octets :

| Octets | Champ |
|---|---|
| 0, 1 | objet de la moitié gauche, en double |
| 2, 3 | objet de la moitié droite, en double |
| 4–7 | objets des quatre propulseurs |
| 8–11 | objets des quatre pare-chocs |
| 12–15 | animation du propulseur : 0 éteint, puis le cycle 1 → 2 → 3 → 1 |
| 16–19 | couleur du pare-chocs |
| 20–23 | état de la pince |
| 24 | jauge de batterie, 0 à 15 |
| 25 | interrupteur des propulseurs, 0 ou 1 |

La table se termine par l'octet `0xFF`. Juste après, un accumulateur de
16 bits par robot, **poids fort d'abord**. Le nombre de robots est la
taille de la table des pinces : 3 ou 4. Le quatrième enregistrement est
celui du robot hostile.

## Signal

Il n'y a pas de tableau de bits séparé. La couleur d'un objet est son
niveau : **l'indice 5 (orange) vaut 1, toute autre couleur vaut 0**. La
couleur froide posée par une porte est 7 (blanc). Un fil est dessiné de
la couleur de sa source.

Les indices utiles sur un objet sont ceux de la table de motifs : 5
orange, 6 bleu, 7 blanc, 0 noir. Les cristaux chargés alternent 5 et 6.
Le corps d'une petite puce est repeint en 6, sauf la puce en cours de
gravure. L'indice 4, sur un fond de salle, est le noir avec le bit 7
levé : il ne change pas le mur, il change la teinte du petit texte.

## Un tour

Ordre fixe. Les étapes marquées « si marche » ne s'exécutent que lorsque
la télécommande vaut 1. À 0, les propulseurs sont forcés à l'animation 0 :
robots, capteurs, pinces, antennes, batteries, fils, portes et puces sont
figés. Au chargement d'un monde, une télécommande qui valait 5 est ramenée
à 1 ; toute autre valeur hors 1 est ramenée à 0.

1. Lecture clavier ou manette, murs, déplacement du joueur.
2. Touches propres au monde (indices, menu, atelier, triche).
3. Image de marche du joueur.
4. Front du bouton d'action.
5. Touche de la boîte à outils.
6. Mémoriser le pas du tour, pour faire suivre les fils.
7. Boîte ouverte, puis prendre ou poser.
8. Son de prise ou de dépose.
9. Les objets portés suivent leur porteur.
10. Touche de la télécommande.
11. Échange joueur / fer à souder.
12. Entrer dans un robot ou en sortir.
13. Cristaux : recharge, chargeur, clignotement.
14. Acteurs propres au monde.
15. Robots : propulseurs, murs, mouvement.
16. Si marche : capteurs.
17. Pinces, puis antennes.
18. Décharge de base des batteries.
19. Fils.
20. Portes, puis bascules.
21. Si marche : puces, puis couleur des puces.
22. Acteurs propres au monde (portes, dalles).
23. Salle affichée, interrupteur intérieur, fenêtre.
24. Dessin du fond, des textes, des objets, des robots, du tableau de bord.
25. Soudure, si le fer est en main.
26. Fils, broches, cadres de capteurs, contour de l'objet visé.
27. Bascule d'écran.
28. Sons en attente. Une touche coupe le son pour le reste de la partie.

Conséquence : un capteur ou un pare-chocs mis à jour dans le tour est
recopié par les fils **du même tour**. La sortie d'une porte n'atteint sa
destination qu'au tour suivant. Chaque porte d'une puce ajoute elle aussi
exactement un tour.

Une seule touche est vue par tour : deux frappes dans le même tour se
remplacent.

### Fils

Un seul passage, par numéro d'objet croissant de 0 à `0xFE` :

- destination vide : rien ;
- destination dans `0x25`–`0x38` : écrire le bit dans l'entrée de cette
  moitié de bascule ;
- sinon : copier la couleur de la source vers la destination.

Puis, pour chaque nœud `0xD1`–`0xDF`, recopier sa couleur vers ses deux
sorties. Si une destination est elle-même un nœud (sprite `0x19`),
l'enfiler et la propager dans le même tour. Une chaîne de nœuds tient
donc en un tour. Une chaîne d'objets ordinaires tient en un tour seulement
si les numéros croissent le long du fil ; sinon il faut un tour par maillon.

### Portes

Pour chaque corps dont le type n'est pas 0, `entrée1` est la couleur de
l'objet suivant, `entrée2` celle d'encore après :

| Type | Sortie |
|---|---|
| 1 | ET |
| 2 | OU |
| 3 | OU exclusif |
| 4 | NON de l'entrée 1 |

La sortie est écrite dans la couleur du corps.

### Bascules

Dix bascules RS. À chaque tour, pour chaque paire :

```
e = entrée(droite) × 2 + entrée(gauche)
e = 1 et état(gauche) = 0    → inverser les deux moitiés
e = 2 et état(droite) = 0   → inverser
e = 0 ou e = 3               → rien
couleur(gauche) = état(gauche)
couleur(droite) = état(droite)
```

Un 1 sur l'entrée d'une moitié met cette moitié à 1. Les deux entrées à 1
en même temps ne changent rien. Les fils qui partent d'une moitié
transportent son état : la moitié est à la fois entrée et sortie.

### Puces

Huit programmes d'un Kio, exécutés de la puce 7 vers la puce 0. Ensuite
les huit broches sont échangées avec les objets câblés :

- broche d'entrée : lire la couleur de l'objet relié et la convertir en 0/1 ;
- autre broche reliée : écrire la couleur (5 ou 7), ou l'entrée d'une
  bascule si l'objet est une moitié, ou l'octet de broche d'une autre puce.

Sens d'une broche, vu de l'extérieur : 0 aucune, 1 entrée, 2 sortie.

Numérotation d'un boîtier vu de dessus : 1 à 4 en descendant à gauche,
8 à 5 en descendant à droite. L'indice en mémoire suit l'écran, colonne
gauche puis colonne droite, de haut en bas :

| Indice | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| Broche | 1 | 2 | 3 | 4 | 8 | 7 | 6 | 5 |

Les références dans un programme sont des décalages de 16 bits, octet haut
d'abord, relatifs à la base de la puce en cours d'exécution. Les huit
premiers octets sont les valeurs des broches. La base d'une puce est donc
l'adresse de sa broche d'indice 0.

```
+0..+7          valeurs des 8 broches
puis des enregistrements :
  01 a b  SORTIES FF          ET
  02 a b  SORTIES FF          OU
  03 a b  SORTIES FF          OU exclusif
  04 a    SORTIES FF          NON
  05 s r q nq  SORTIES(q) FF  SORTIES(nq) FF     bascule
  06 <programme imbriqué entier>
  07 { SRC DST DST … FF } … FF                   copies, puis fin
SORTIES = suite de décalages de 16 bits terminée par FF
```

Un opcode inconnu est sauté. Le NON est `(a XOR 1) AND 1`.

La bascule (code 5) lit ses deux entrées puis les remet à 0. `s=1, r=0`
pose `q=1` et `nq=0`. `s=0, r=1` pose l'inverse, si `q` et `nq` étaient
déjà complémentaires. `s=r` ne change rien. Puis elle émet `q`, puis `nq`.

Une puce imbriquée (code 6) est une copie intégrale collée dans le
programme. L'interpréteur empile la base du parent, applique les écritures
en attente, exécute la puce imbriquée, puis reprend le parent juste après.

La section 7 copie, tout de suite, l'octet `SRC` vers chaque `DST`. Un
`FF` en tête de groupe termine la puce. La gravure s'en sert pour
distribuer les broches d'entrée et les sorties des puces imbriquées. Les
portes écrivent elles-mêmes vers les broches de sortie et vers les entrées
des puces imbriquées.

Écritures différées : si une sortie vise un octet situé à partir de
l'enregistrement courant (porte pas encore évaluée), l'écriture est
empilée et appliquée à la fin de la puce, dernière empilée en premier, ou
juste avant d'entrer dans une puce imbriquée. Sinon elle est immédiate.
La comparaison se fait octet par octet, haut puis bas. Effet voulu :
**chaque porte retarde d'exactement un tour**, quel que soit l'ordre des
enregistrements.

Taille maximale acceptée par la gravure : `0x3DE` octets. Au-delà, la
gravure abandonne. Une puce vide fait 11 octets : huit zéros, `07 FF FF`.

Graver recopie les puces imbriquées telles qu'elles sont à cet instant.
Recharger ensuite l'originale ne met pas à jour les copies déjà gravées.

### Gravure

Elle a lieu dans la salle du four, quand tout ceci est vrai en même temps :

- le joueur est dans cette salle ;
- le prototype est dans la zone du four, et aucune de ses huit broches
  extérieures n'a de fil ; il est alors recalé sur le socle ;
- une petite puce est dans la zone du logement, sans fil sur ses broches ;
  elle est recalée ;
- le joueur est sur le bouton et confirme.

Puis : animation, parcours du circuit intérieur depuis les broches, liste
des portes, des bascules et des puces imbriquées, calcul des tailles,
écriture des enregistrements (opcode selon le type de pièce, valeurs
d'entrée courantes, sorties vers les entrées suivantes et vers les
broches), copie des puces imbriquées, section 7, longueur, copie de l'état
des broches intérieures dans les huit premiers octets, sens des broches
déduit du type des objets-broches intérieurs.

### Bibliothèque

Dix puces fournies. Une nouvelle partie précharge le compteur jusqu'à N
et le longe-mur.

| Puce | Broches | Rôle |
|---|---|---|
| Horloge | 8 sorties | quatre horloges, deux sorties chacune : anneaux de 1, 3, 7 et 5 NON. Périodes 2, 6, 14 et 10 tours |
| Compteur 4 bits | 1 horloge, 2 remise à zéro, 5–8 les bits 0 à 3 | compte de 0 à 15 |
| Bus | 1 entrée, 2–8 sorties | recopie l'entrée, sans porte |
| Ligne à retard | 1 entrée, 2–8 sorties | la broche *k* retarde l'entrée de *k* − 1 tours |
| Additionneur | 1–3 entrées, 7 somme, 8 retenue | additionneur complet |
| Monostable | quatre paires entrée / sortie | une impulsion par front montant |
| Bascule RS | 1 mise à 1, 2 remise à 0, 7 et 8 les deux sorties | bascule avec retour |
| Compte jusqu'à N | 1 impulsions, 2 remise à zéro, 3–8 six sorties | chaque impulsion allume la sortie suivante |
| Longe-mur | 1, 3, 5, 7 propulseurs ; 2, 4, 6, 8 pare-chocs | suit les murs |
| Enregistreur stéréo | 1–2 lectures, 5–6 effacements, 7–8 entrées | 35 tours par canal |

Beaucoup de OU à une seule entrée servent de relais : ils ne font qu'ajouter
un tour de retard.

## Robots, en détail

Pour chaque robot, côtés traités de 3 vers 0 :

1. Le pare-chocs de ce côté repasse à la couleur froide. Si la batterie
   n'est pas vide, l'interrupteur est fermé et la broche du propulseur est
   chaude : lancer l'animation si elle était à 0, et ajouter 60 à la
   consommation du tour. Sinon, animation 0.
2. Tester la case juste au-delà du bord. Côté droit : X+8 de la moitié
   droite. Côté haut : Y+20. Côté gauche : X−2. Côté bas : Y−4. Un mur
   allume le pare-chocs (couleur 5, son la première fois) et interdit le
   mouvement de ce côté.
3. Sinon, si le propulseur est actif, avancer du vecteur de ce côté, en
   changeant de salle si le bord est franchi. La moitié droite suit.
   Plusieurs propulseurs du même tour s'additionnent. Un robot tenu par
   le joueur, ou celui dans lequel le joueur se trouve, ne bouge pas.

Il n'y a pas de collision entre robots, ni entre un robot et un objet,
sauf la pince et les capteurs de contact.

La décharge de base ajoute 30 par tour à chaque robot dont la jauge n'est
pas à 0. La consommation du tour est ajoutée à l'accumulateur. Chaque
débordement retire un cran de jauge. À vide, 15 crans durent
15 × 65 536 / 30 tours. Avec un propulseur allumé en permanence,
diviser par 90 au lieu de 30. Batterie vide : propulseurs, pinces et
antennes s'arrêtent. Les capteurs continuent.

Un cristal (sprite `0x39`, objets `0xF6`–`0xFB`) chargé, posé dans la prise
d'un intérieur (X de 19 à 23, Y de 25 à 41, salles `0x09`, `0x0A`, `0x0B`,
`0x0D`), recharge à 15 une batterie **vide**, remet l'accumulateur à 0, et
se décharge (couleur 7). Un cristal déchargé posé près du chargeur du monde
redevient chaud. Les cristaux chargés clignotent entre 5 et 6.

Dans un intérieur, le bouton d'action dans la zone X ≥ 116 et Y < 38
inverse l'interrupteur des propulseurs. Dans la zone X ≥ 116 et Y ≥ 140,
la salle dessinée devient celle où se trouve le robot : on regarde dehors
sans sortir.

### Capteurs

Le corps porte le **sprite de l'objet cherché**. Il parcourt les objets
`0xFB`…`0xF6` puis `0x08`…`0x03`, et retient le premier qui est libre
(ni porté, ni tenu) et de même sprite. S'il est posé dans un intérieur, il
cherche dans la salle du robot ; sinon dans sa propre salle.

| Capteur | Sortie chaude quand |
|---|---|
| de salle | l'objet cherché est dans la salle |
| de direction, quatre sorties | 0 l'objet est plus haut (Y > Yrobot+7) ; 1 plus bas (Y ≤ Yrobot−8) ; 2 à droite (X > Xrobot+8) ; 3 à gauche (X < Xrobot−4) |
| de contact | l'objet touche une moitié du robot, au pixel des sprites |

### Pinces

Si l'entrée est chaude et la batterie n'est pas vide : quand le robot ne
tient rien, chercher un objet saisissable qui le touche, parmi `0x03`–`0x08`
et `0xF6`–`0xFB` seulement, ni déjà porté ni tenu par le joueur. L'attacher
à la moitié gauche, avec le décalage du côté touché, et le marquer non
saisissable. La sortie de pince devient chaude. Quand l'entrée retombe,
relâcher (porteur `0xFF`, à nouveau saisissable) et refroidir la sortie.

### Antennes

Radio commune à tous les robots. Si, pendant un tour, l'entrée d'antenne
d'un robot alimenté est chaude, le tour **suivant** allume pendant un tour
la sortie d'antenne de chaque robot encore alimenté.

## Joueur

Touches de déplacement : `I` haut, `M` bas, `J` gauche, `K` droite, et les
flèches. Le modificateur de pas fin (contrôle, ou les chiffres 8, 2, 4, 6
avec le scan des flèches) réduit le pas à une unité. Espace ou bouton :
prendre ou poser. `R` inverse la télécommande et échange son sprite entre
la télécommande visible et le sprite vide. `C` et `S` échangent le joueur
avec le fer. `T` amène la boîte dans la main, ou l'ouvre et la ferme si le
joueur est dans sa salle. `?` et `/` montrent les indices. Échap ouvre
l'écran de pause. `L` ouvre le chargeur de puce quand une petite puce est
en main.

La manette fournit les mêmes axes et le même bouton. Le centre et les
diviseurs d'axe sont réglables ; le centre par défaut est 128, le diviseur
1.

Prendre : au front du bouton, si le joueur tient déjà un objet, il le lâche.
Sinon, chercher dans la salle un objet saisissable dont le sprite touche
celui du joueur. Saisir une pièce attachée remonte jusqu'à la racine de la
chaîne de porteurs : on emporte le robot entier par sa moitié droite, une
porte par une entrée. Le décalage au moment de la saisie est conservé.
Pendant le transport, les extrémités de fils suivent ; une extrémité qui
sortirait de la salle coupe le fil.

Entrer : si le joueur touche un robot (`|Xj − Xr| < 6` et `Yr + 4 − Yj < 9`)
qu'il ne tient pas, et qu'il n'y a pas de mur sous le point d'entrée, il
passe dans l'intérieur. La position d'arrivée dépend du sens de la marche :
depuis la gauche X = 8, depuis la droite X = 123, Y = 95 dans les deux cas ;
par le haut ou le bas, X = 70, Y = 18 ou 160. Sortir : franchir un bord de
l'intérieur (X < 7, X ≥ 127, Y ≥ 161, Y < 16) repose le joueur à côté du
robot (décalages −2 ou +7 en X, ±6 en Y) si la place est libre. Les objets
tenus suivent, puisqu'ils sont attachés au joueur.

Le passe-muraille ne concerne que le joueur. Il s'arme par une séquence au
menu, puis une touche l'inverse. Les robots et les sentinelles gardent
leurs murs. Dans le fichier de réglages de 16 octets, l'octet de triche
vaut `0x5E` quand cette touche est autorisée.

La boîte ouverte laisse sortir des portes, des nœuds et des bascules, dans
la limite des compteurs. Les compteurs sont affichés dans un texte de la
salle de la boîte.

Le fer mémorise une première broche au bouton, puis relie la seconde. Le
fil est rangé dans la table qui correspond au type de broche : fil
d'objet, deuxième sortie de nœud, ou fil de puce. Un nouveau contact sur
une broche déjà reliée efface ses fils. Le tracé est un L : un segment
horizontal et un segment vertical, dans la couleur de la source.

## Dessin

Chaque tour redessine toute la salle dans un tampon caché, puis l'affiche.
L'aire de jeu est l'écran entier, 280 × 192, sans bandeau. L'ordre est :
fond, textes, objets, robots et tableau de bord intérieur, fils, broches,
cadres, contour de l'objet sous le curseur.

Le fond est la grille de murs. Chaque indice de couleur choisit un motif
de 14 × 16 (quatre masques de lignes paires et impaires, octets pairs et
impairs). La moitié droite d'un octet de mur décale le motif d'une case,
pour que la trame reste continue. Vingt et un indices sont définis :

| Indice | Aspect |
|---|---|
| 0, 4 | noir |
| 1, 2 | vert, violet |
| 3, 7 | blanc |
| 5, 6 | orange, bleu |
| 8–11 | trames claires, un point sur quatre |
| 12–15 | trames foncées, trois points sur quatre |
| 16–19 | trames diagonales, deux points sur quatre |
| 20 | non dessiné |

Un sprite est posé par masque puis union :
`pixel = (pixel AND NOT masque) OR (masque AND couleur)`. Le masque
garde toujours le bit 7. La couleur est un couple d'octets, colonnes
paires et impaires, indépendant de la position. Sept routines couvrent
le décalage `2·X mod 7`. Les fils sont une horizontale puis une
verticale. Le petit texte n'utilise pas la couleur de son entrée.

La salle affichée est celle du joueur, sauf par la fenêtre d'un intérieur.
Les sons sont associés à une salle et ne jouent que si cette salle est
celle du joueur.

## Sons

File d'effets en attente. Chaque effet a un mode, une durée, un balayage
et une hauteur, puis le numéro de salle. Vingt-huit effets existent ; les
numéros utilisés par le moteur sont :

| N° | Moment |
|---|---|
| 0 | poser |
| 1 | prendre |
| 2 | pare-chocs |
| 3 | la pince saisit |
| 4 | la pince lâche |
| 5 | antenne |
| 6 | soudure |
| 7 | batterie rechargée |
| 8 | cristal chargé |
| 9 | montée de monde |
| 10 | robot hostile |

Le haut-parleur est un canal carré dont la période évolue pendant la durée
de l'effet. Les scènes d'introduction et de fin ont leurs propres délais
(environ une seconde et quatre secondes) et peuvent être interrompues par
une touche.

## Sauvegarde

Une partie est la juxtaposition brute des structures, sans en-tête :

| Bloc | Taille |
|---|---|
| monde | 13 568 |
| circuit, complété jusqu'à | 2 560 |
| huit programmes de puces | 8 × 1 024 |
| sens des broches | 8 × 8 |
| cinq octets | voir ci-dessous |

Les cinq octets sont : l'objet touché, la racine de sa chaîne de porteurs
(ce qui bouge réellement), le décalage X de la prise, le décalage Y, et
l'identifiant de monde. Taille totale : 24 389 octets.

Une puce seule fait 1 333 octets : 1 024 de programme, 8 de sens de
broches, 2 de longueur (poids faible d'abord), puis une fiche de 299 octets
(titre de 19, huit lignes de 35). Le catalogue de puces tient 26 noms de
18 octets. Sur une disquette, treize emplacements suffisent ; un support
plus grand en offre vingt-six.

Le fichier de réglages fait 16 octets : manette activée, port, centre X,
centre Y, quatre diviseurs, octet de triche, un mot de cadence (la valeur
usuelle est `0x0238` ; à partir de `0x0500` la boucle des passerelles
ajoute une attente), lecteur, trois octets réservés.

Le tirage du premier monde (place de la clé et du cristal) dépend de
l'instant des premières entrées. Deux parties rejouées avec les mêmes
instants d'entrée suivent le même cours.

## Premier monde

La sortie est le joueur en (32, 32) dans la salle `0x2A`. Une fanfare de
neuf notes suit, les objets non tenus partent en salle `0x3F`, les objets
du monde suivant sont placés.

La clé et un cristal sont placés au hasard. Le robot hostile vide les
batteries qu'il touche et ouvre des portes quand un objet repose sur une
dalle : ces portes sont des cases de mur posées ou effacées, pas des
objets. Les trois robots commencent déjà câblés. Sparky porte la puce
longe-mur.

Les mondes suivants ont chacun leur condition de sortie, leurs dalles et
leurs acteurs, dans le code rechargé avec les salles. Le centre de
l'ordinateur a un mode carte sur la même boucle. Les passerelles ont des
couloirs où un choc remplace la couleur du joueur par l'indice `0x87`
(deux fines bandes colorées). Le détail des énigmes des mondes 2 à 5 reste
à transcrire salle par salle depuis les données de monde : la simulation,
elle, ne change pas.
