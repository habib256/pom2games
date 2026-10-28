# Graphismes et textes

Comment *Robot Odyssey I* dessine ses écrans : salles en double tampon,
sprites, fils, polices, textes des salles, images du menu, de l'intro et de
la fin. Les formats ont été vérifiés en redessinant avec
`tools/re_graphics.py` et en comparant **octet par octet** avec la RAM de
l'émulateur (a2shot) ; les écarts restants sont listés. Le format du monde
(objets, salles, liens) est décrit dans [world.md](world.md), le menu et
le chargeur dans [loader.md](loader.md).

Notation : « X jeu » = abscisse en unités de 2 pixels (0-139), « Y jeu » =
ordonnée vers le haut (0 = ligne écran 191). Les adresses sans bloc sont
celles de la RAM pendant une partie de Robotropolis.

## Outil

```sh
python3 -I tools/re_graphics.py              # tout : ~20 s
python3 -I tools/re_graphics.py --only-pictures   # menu, intro, fin, polices
python3 -I tools/re_graphics.py --verify RAM.bin  # redessine la salle d'un vidage
```

Entrées : `build/<face>.po` et les descripteurs du module résident (via
`tools/loadcalls.py`) ; rien d'original n'est inclus dans le script.
Sorties (ignorées par git) :

| Sortie | Contenu |
|---|---|
| `build/original_graphics/font_room_7x8.png` | police des salles (96 caractères) |
| `…/font_room_large_14x16.png` | la même agrandie (grands titres) |
| `…/font_prompt_7x8.png` | police du pilote texte `$0300` (96 caractères) |
| `…/<monde>_sprites.png` | 64 sprites 14×16 de chaque monde (14 mondes) |
| `…/<monde>_rooms.png` | les 64 salles de chaque monde (8 par ligne, salle 0 en haut à gauche) |
| `…/robotropolis_level1_room40.png` | salle d'accueil seule, 560×384 |
| `…/engine_sprites_8440.png` | 18 sprites du bloc `$075` (pièces des robots) |
| `…/menu_picture_*.png`, `menu_frame0[1-3].png`, `menu_blit_6300.png` | 6 demi-images du menu, 3 écrans, icône robot |
| `…/intro_picture_*.png` (8), `intro_blit_*.png` (5), `intro_frame*.png` (18) | intro |
| `…/ending_40F0_picture_*.png` (3), `ending_40F0_frame*.png` | séquence de fin |
| `…/manifest.json` | sources (SHA-256), scripts décodés, en-têtes des images, textes par monde |
| `build/texts/<monde>.txt` | textes des salles en UTF-8 (930 entrées, 14 mondes) |
| `build/texts/resident_prompts.txt` | 47 fragments de messages du module résident |

Mondes exportés (appels du chargeur appliqués dans l'ordre) :

| Nom | Face | Appels | Textes |
|---|---|---|---|
| `robotropolis_level1` | A | `$45EF`, `$4602` | 34 |
| `robotropolis_level2` … `5` | A | idem + `$40B6` / `$40C2` / `$40CE` / `$40DA` | 33, 34, 39, 71 |
| `preview_45D5` | B | `$45D5` | 24 |
| `innovation_lab_4630` | B | `$4630` | 100 |
| `chip_design_46A6` | B | `$46A6` | 117 |
| `tutorial_1` … `6` | C | `$4590` + `$4662` / `$466E` / `$467A` / `$4684` / `$4690` / `$469C` | 92, 77, 71, 98, 70, 70 |

Les niveaux 2-5 ne rechargent pas la table des objets : leurs cartes sont
dessinées **sans objets** (sinon on verrait ceux du niveau 1).

## Écran de jeu

### Double tampon par bascule de page

Pas de copie page 2 → page 1 : le jeu **alterne** les pages. Chaque tour de
la boucle principale (code du niveau, `$085B-$0939` au niveau 1) redessine
toute la salle dans la page cachée, puis `$AEED` bascule :

| Adresse | Rôle |
|---|---|
| `$9C47` | page affichée (0 = page 1 par `$C054`, 1 = page 2 par `$C055`) |
| `$AEED` | `$9C47 ^= 1`, affiche la page `$9C47`, prépare l'autre pour le dessin |
| `$16/$17` | table des octets hauts de ligne de la page de dessin : `$99B9` (page 2) ou `$98F9` (page 1) |
| `$9839` | octets bas de ligne, indexés par **Y jeu** (Y = 0 → ligne 191) |
| `$AEEB` | vecteur du dessin du fond : `$B6B8` (page 2) ou `$B450` (page 1), appelé par `JMP $AF1C` |
| `$9CA1` | initialisation : page 1 visible, `$B8B9`, HGR plein écran |

Ordre de dessin dans la boucle (niveau 1) : `$9D03` fond de la salle,
`$A2A2` textes, `$1322`… code du niveau, `$9D18` objets, puis robots
(`$D2BC`, `$D72B`, LC), fils (`$FC62`), etc., enfin `$AEED`. La « page 2
qui change régulièrement » est donc la page de dessin d'un tour sur deux.

L'aire de jeu est **tout l'écran** HGR, 280×192 : aucune zone d'état ni
inventaire ; les textes sont des objets de la salle.

### Fond de salle (`$9D03` → `$9CD0` → `$B450`/`$B6B8`)

- Murs : 30 octets par salle en `$7000 + 30·salle` (`$9D56`). Grille de
  **20 × 12 cases de 14 × 16 pixels** : l'octet *i* (0-29) couvre le tiers
  d'écran *i* div 10, colonnes d'octet 4·(*i* mod 10) à +3 ; bits 0-3 =
  les 4 cases (lignes 0-15, 16-31, 32-47, 48-63 du tiers) de la paire de
  colonnes gauche, bits 4-7 celles de droite. Bit 1 = mur.
- Couleurs : `$6E40[salle]` (cases à 0) et `$6E80[salle]` (cases à 1),
  index dans les 4 tables de motifs `$9B91`, `$9BB1`, `$9BD1`, `$9BF1`
  (octet pair / impair des lignes paires, puis des lignes impaires), copiées
  en `$9C3F-$9C46` puis entrelacées en `$B496-$B4A1` (`$B4A2`). La moitié
  droite d'un octet décale les motifs d'une case (effet de trame continue).
- Motif `$F0` (index 20) : case non dessinée.
- Écriture directe (STA), routines déroulées de 600 octets par page.

Table des 21 couleurs (`$9B91`+i … `$9BF1`+i) :

| i | octets | aspect |
|---|---|---|
| 0 / 4 | `00` / `80` | noir (bit 7 à 0 / 1) |
| 1, 2 | `2A 55` / `55 2A` | vert, violet |
| 3 / 7 | `7F` / `FF` | blanc |
| 5, 6 | `AA D5` / `D5 AA` | orange, bleu |
| 8-11 | `91 A2 C4 88`… | trames diagonales claires (1 point sur 4) |
| 12-15 | `EE DD BB F7`… | trames foncées (3 points sur 4) : murs bleu-blanc |
| 16-19 | `E6 CC 99 B3`… | trames diagonales 2 sur 4 |
| 20 | `F0` | transparent (fond seulement) |

Niveau 1 : intérieur 4 (noir à bit 7 levé, d'où les textes orange/bleu),
murs 13 ; les salles d'accueil utilisent aussi 0/13.

### Sprites (`$AF1F`)

- **16 octets par sprite, rangée 0 = rangée du bas**, bits 6…0 = 7 points de
  gauche à droite, chacun **2 pixels** HGR : 14 × 16 pixels. Bit 7 ignoré.
  Rangées nulles sautées.
- Position : `$18` = X jeu (< `$86`), `$14` = Y jeu de la rangée du bas
  (< `$B1`). Colonne d'octet `$9B05[X]` (= 2X div 7), décalage
  `$9A79[X]` (= 2X mod 7), sept routines non décalées par la table
  `$AF4C` : `$AF5A` (0), `$B13B` (1), `$AFD3` (2), `$B1B3` (3),
  `$B04B` (4), `$B22B` (5), `$B0C3` (6) ; tables d'expansion `$B2A5-$B3A9`.
- Écriture **masquée**, ni XOR ni pré-décalage stocké :
  `octet = (octet & ¬m) | (m & couleur)`, où le masque *m* contient toujours
  le bit 7. La couleur est un couple d'octets `$0F` (colonnes paires) /
  `$10` (impaires) : la couleur ne dépend donc pas de la position.
  3 octets écrits, 2 pour le décalage 0, qui met en plus `$80 & couleur`
  dans le 3e octet s'il est nul.
- Objets du monde (`$9D18`) : liste chaînée de la salle (`$6E00[salle]`,
  suivant `$6000[o]`), sprite `$6A00 + 16·$6100[o]`, couleur
  `$6200[o]` → `$9B91`/`$9BB1`, X `$6400[o]`, Y `$6500[o]`.
- Autres appelants de `$9CC3` (couleur X + sprite `$0D/$0E`) : pièces des
  robots en LC (`$D2BC-$D830`, sprites `$84C0-$8550` du bloc `$075`,
  « engine_sprites »), créatures du niveau 1 (`$1322`, `$12D2`, `$1312`),
  joueur animé (`$DFA3`, voir world.md), etc.

### Lignes et fils

- `$A04C` : ligne horizontale Y = `$14`, de X `$9C35` à `$9C37` ;
  `$9FC4` : verticale X = `$18`, de Y `$9C36` à `$9C38` ; couleur
  `$9C34` (tables `$A13C/$A144`, masques `$A181-$A280`) ; `$A14D` point.
- **Les fils sont tracés en équerre**, horizontale puis verticale
  (`$FC62`, `$FCA4`, `$F547`) : extrémités `$8718/$8818` (X) et
  `$8918/$8A18` (Y) par objet, couleur `$6200`.
- `$A281` : rectangle (2 horizontales + 2 verticales), p. ex. pare-chocs.
- `$B3AB`/`$B40B` : met à 0 / 1 un bit d'une grille 20 × 12 en `($00)` (la
  grille des murs) ; appelé par `$AEB0` et le LC `$D1AD-$D29C` (édition de
  murs ? **non vérifié**).

### Vérification

`--verify` redessine fond + textes + objets de la salle du joueur
(`$6300`) dans la page affichée d'un vidage a2shot :

| Vidage | Salle | Résultat |
|---|---|---|
| après l'intro (`wait:6500`) | 40 (accueil) | **0 octet différent** sur 7 680 |
| 12 × `M` puis 30 × `K` | 2 (trois robots) | 340 octets différents, lignes 64-152 : antennes, propulseurs, pinces, faces des robots (LC, non reproduits) |

## Polices

### Police des salles (`$9500-$97FF`, bloc `$05B` +0)

8 tables de 96 octets : rangée *r* du caractère *c* (`$A0-$FF`) en
`$9460 + $60·r + c`. **Rangée 0 = bas** (jambages), rangée 7 en haut ;
bits 0-6 = pixels de gauche à droite, bit 7 à 0. Chasse fixe de 7 pixels
(un octet). Caractères propres :

| Code | Glyphe |
|---|---|
| `` ` `` / `"` | guillemets ouvrant / fermant (“ ”) |
| `^` | disque plein |
| `{` `}` `~` DEL | flèches ← → ↑ ↓ |

### Petit texte (`$A2EA` type 0 → `$A2FA`)

Octets ORés à des colonnes d'octet entières (`$9B05[X]`), Y = ligne du bas
de la première ligne de texte, interligne 9. `$A0` espace, `$00` fin, tout
autre code < `$A0` (en pratique `$8D`) = retour à la ligne. Pas de couleur
propre : **la couleur vient du bit 7 du fond** (fond 4 = `$80` → pixels
isolés orange/bleus ; fond 0 → violet/vert). Coupé à `Y ≥ $B9`.

### Grand texte (`$A3E1`, type 2)

Chaque glyphe devient un sprite 14 × 16 (rangées doublées, table de
renversement de bits `$A4C9`, assemblé en `$A3D1`) dessiné par `$AF1F` dans
la couleur `$7B00[t]` (tables `$A4B9/$A4C1` : 8 couleurs pleines).
Avance 7 X jeu (14 pixels), `$8D` = ligne suivante 18 pixels plus bas.
Ex. « The City Sewer », « ROBOT ANATOMY », « SHORT CUT ».

### Police des messages (`$0300`, page texte)

Le pilote texte HGR et sa police occupent la **page texte `$0300-$07FF`**,
copiée par l'amorce depuis `$5A00-$5EFF` (piste 0, blocs 5-7). Ce n'est
**pas un écran de chargement** : le mode texte n'est jamais affiché.
(`build/ref/game_robots.png`, écran texte, est un artefact : un
`peek:0000:0x10000` lit `$C051` (mode texte) et les autres commutateurs `$C0xx`, ce qui dérègle
moteur du lecteur ; il faut vider `0000:C000` et `D000:3000` séparément.)

- Glyphe *c* (`$20-$7F`) : 8 octets à `((c|$80)>>5)·256 + (c&$1F)·8`, soit
  `$0500-$07FF` ; rangée 0 en haut. Les glyphes `$xF` tomberaient dans les
  trous d'écran : l'amorce les range en `$04B8 + (c&$70)/2`.
- `$0300` : affiche A en (`$24` colonne, `$25` rangée), EOR `$F6`
  (vidéo inverse), codes < `$1B` par la table `$044B` (non détaillée).
- Chaînes en ligne du module résident : `JSR $4913` (efface, rangée A,
  colonne Y), `$491E` (positionne), `$4920` (continue), texte ASCII bas
  terminé par un octet à bit 7 levé. Les mots variables (« game »/« lab »,
  `$4973`) sont insérés par du code.
- Sert aux écrans « To go to the game, press RETURN », « Insert Robot
  Odyssey … disk », sauvegardes (voir `resident_prompts.txt`).

### Grandes polices du menu

Il n'y en a pas : les titres proportionnels du menu (« Robot Odyssey »,
« Robotropolis Preview »…) et le logo sont des **images**.

## Textes des salles (`$7880-$7C7F`, données jusqu'à `$81FF`)

128 entrées, 8 tableaux de 128 octets, parcourues par `$A2A2` à chaque
image pour la salle `$9C2D` :

| Tableau | Champ |
|---|---|
| `$7880` | salle (`$FF` = libre) |
| `$7900` | X jeu |
| `$7980` | Y jeu (bas de la 1re ligne) |
| `$7A00` | type : 0 petit texte, 2 grand texte (1 et autres : rien) |
| `$7A80` | lu puis ignoré (le `STA` a été remplacé par trois `NOP` en `$A2BB`) |
| `$7B00` | couleur du grand texte (0-7) |
| `$7B80` / `$7C00` | adresse du texte, octet bas / haut |

Texte en ASCII à bit 7 levé, `$8D` = ligne, `$00` = fin. Les chaînes sont
en général en `$7C80-$81FF`, mais certaines pointent ailleurs (données du
niveau `$8EF0+`, LC `$E470+` pour la Preview) : l'outil charge tout le mode.
Les entrées de la salle 63 et les entrées qui pointent sur des octets non
textuels (code, tables) sont des restes : l'outil écarte celles qui
contiennent un octet < `$A0` autre que `$8D` (liste dans le manifeste ;
niveaux 4-5 et Preview surtout).

## Images du menu, de l'intro et de la fin

### Interpréteur de scènes (`$0803` → `$0986`, bloc `$039`)

Appelé par `JSR $0803` suivi d'un programme en ligne :

| Op | Routine | Paramètres | Effet |
|---|---|---|---|
| 0 | `$09F7` | adresse | dessine une image (`$0A74`) |
| 1 | `$0BD4` | – | fondu en losange du tampon `$D000-$EFFF` (LC) vers la page 1, par blocs de 4 lignes et demi-octets (`$0C45`) |
| 2 | `$09C2` | – | retour au code natif après le programme |
| 3 | `$09DF` | adresse, A | appel natif (temporisation `$609E`…) |
| 4 / 5 | `$0A07` / `$0A0F` | – | abandon par touche permis / interdit |
| 6 | `$0A17` → `$0D24` | adresse, ligne, colonne | **bitmap en XOR** (`| $80`) : deux appels successifs l'affichent puis l'effacent |
| 7 | `$0A3C` | – | efface la page 1, HGR plein écran |
| 8 | `$0A5E` | adresse | vecteur d'abandon (`$C9`) |
| 9 | `$0D73` | adresse | mélodie : couples (période, durée) jusqu'à 0, haut-parleur `$C030` |
| 10 | `$0A6B` | octet | décalage de hauteur `$0D72` |

### Format des images (`$0A74`) : tuiles 7 × 8 compressées

En-tête de 16 octets :

| Octet | Sens |
|---|---|
| 0, 1 | hauteur (rangées de 8 lignes), largeur (octets) |
| 2 | page de destination (`$20` page 1, `$D0` tampon LC) |
| 3, 4 | rangée et colonne de départ |
| 5, 6 | `08`/`02`, `00` (**?** non lus) |
| 7 | dernière colonne (non lu) |
| 8-9 | décalage **gros-boutien** du jeu de tuiles 2 depuis +`$10` |
| 10-11 | décalage gros-boutien de la carte depuis le jeu 2 |
| 12-13 | longueur de la carte (taille totale = `$10` + 8 + 9 + 12) |

Jeu de tuiles 1 en +`$10`, tuiles de 8 octets (ligne 0 en haut, octets HGR
bruts, bit 7 compris). La carte se lit **colonne par colonne**, de haut en
bas : *t* < `$FB` = tuile *t* du jeu courant ; `$FF n t` = *n* fois *t* ;
`$FE k` = colonne suivante, et si *k* > 1 la colonne qui vient de finir est
rejouée jusqu'à *k* fois ; `$FD` = fin ; `$FC`/`$FB` = jeu 2 / jeu 1
(quirk reproduit : la reprise d'une colonne ne restaure que l'octet haut de
la base). Écriture directe, pas de masque.

### Écrans

| Séquence | Données | Programme | Contenu |
|---|---|---|---|
| menu (`$4070`) | `$03E` en `$6300` | `$6029` (bloc `$03C`) | images `$63C6`+`$6D6A` (« The Learning Company presents »), `$7734`+`$8146` (titre, auteurs, ©1984-1985), `$8BA3`+`$93DB` (menu) : demi-écrans de 20 colonnes dans le tampon LC puis fondu |
| intro (`$456D`) | `$009` en `$6300` (face A) | `$6003` puis `$60AC` (bloc `$008`) | `$6300` chambre (fondu), `$6CE3` « Z », `$71C2` rêve, `$7842` réveil « ? », `$806D` bras, `$86CE` chute, `$8BBA` trou, `$9332` Robotropolis ; personnage qui tombe = 5 bitmaps XOR `$A396`, `$A544`, `$A71E`, `$A8E6`, `$AADC` (8-12 octets × 39-62 lignes) |
| fin (`$40F0`) | `$009`, programme `$02E` | `$6003`, `$6072`, `$6163` | reprend `$9332`, `$8BBA`, `$6300` avec un bitmap XOR en `$6200` hors des données chargées (**?** modifié à l'exécution ; non rendu) |

Icône robot du menu : bitmap XOR `$6300` du bloc `$03E` (6 octets × 32
lignes), posé par le programme `$60B4` à la ligne `$609B[entrée]` ; cadre
vert de l'entrée tracé en XOR par `$60E7` (motifs `$2A/$55`). Les
« Insert … disk » et « To go to the game » ne sont pas des images (police
`$0300`).

Seule la face A contient des programmes de scènes ; le bloc `$009` des faces
B et C est autre chose (bibliothèque de puces sur B).

### Vérification

- Intro : arrêt sur la fin de chaque image (`until:0AF0`), page 1 de
  l'émulateur comparée à la reconstruction : **0 octet différent** pour les
  8 images (la 1re vérifiée à travers le fondu).
- Menu (vidage à `wait:2500`) : après les 6 images, le fondu et l'icône
  XOR, il reste 84 octets différents, lignes 34-49 = le cadre vert natif.

## Rendu PNG

`hgr_rgb` est un modèle NTSC simple (pixel allumé à côté d'un autre =
blanc, isolé = couleur selon parité de colonne et bit 7, trou entre deux
pixels allumés = leur couleur). Les trames de murs y sont plus « pointillées »
que dans a2shot ; les octets, eux, sont exacts.

## Points ouverts

- Pièces des robots (LC `$D2BC-$D830`) et animation du joueur : routines
  repérées, non reproduites dans `--verify`.
- Octets 5-7 des en-têtes d'image ; octets 0-2 des bitmaps XOR (0-1 ≈
  taille, 2 = `$6F`).
- Bitmap XOR `$6200` de la séquence de fin.
- Table de contrôle `$044B` du pilote `$0300` (inverse, clignotant…).
- `$B8B9` met à 0 les octets `$xx7F/$xxFF` de `$2000-$5FFF` (protection
  des octets lus par le 3e octet des sprites ? **?**).
- Usage de `$B3AB/$B40B` (grille des murs : éditeur du labo ?).
