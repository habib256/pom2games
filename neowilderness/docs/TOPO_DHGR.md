# Neowilderness — feuille TOPO en DHGR (lot 4)

Ce document prépare les deux tâches du lot 4 « Générer TOPO depuis les
données en RAM » et « Porter les courbes, l’eau, les bois et les repères
graphiques TOPO ». La feuille est **calculée à l’affichage** depuis la carte
résidente (`MAP` à `$7000`, bois `forest_bits`), sans image stockée : les
8 Kio de TOPO en RAM auxiliaire et le BLOAD de l’image disparaissent.

| Fichier | Rôle |
|---|---|
| `tools/topo_palette.py` | rôles des couleurs, rampe hypsométrique, tables d’octets construites à l’affichage |
| `tools/topo_dhgr_ref.py` | référence (règles exactes), algorithme entier « 6502 » `Sheet6502`, modèle de cycles, PNG |
| `tests/test_topo_dhgr.py` | contrôles Python purs (≈ 4 s), dont l’égalité au bit près des deux implémentations |
| `build/topo/` (hors Git) | cartes `map_<graine>_<niveau>.bin`, captures, banques `.main/.aux`, esquisse 6502 `sketch/` |

```sh
python3 -I tests/test_topo_dhgr.py           # contrôles
python3 -I tests/test_topo_dhgr.py --refs    # cartes + captures dans build/topo/
python3 -I tools/topo_dhgr_ref.py --gallery  # idem + budget de cycles par carte
python3 -I tools/topo_dhgr_ref.py MAP.bin build/topo/x   # une carte quelconque
```

Les cartes sont générées dans le processus (`topo_dhgr_ref.make_map`, fonctions
de `tools/mkmap.py`) : `build/map.bin` n’est jamais lu ni écrit. La carte 1985
niveau 4 générée ainsi est identique octet pour octet à `build/dhgr/map.bin`.

## 1. Décisions

| Question | Choix |
|---|---|
| Mode | **DHGR mixte** : graphisme rangées 0..159, légende dans les 4 lignes texte (comme la feuille HGR) |
| Correspondance | **1 cellule = 1 pixel couleur en x, 1,916 rangée en y** ; carte en x 0..111, bandeau de légende en x 112..139 |
| Courbes | toutes les 400 ft (4 niveaux), interpolées linéairement entre rangées de cellules ; maîtresses (2 000 ft) en gras |
| Teintes | rampe hypsométrique tramée, vert → jaune → orange → brun → gris → blanc (neige) |
| Eau | bleu foncé, rive (eau touchant la terre, rivières entières) bleu moyen |
| Bois | vert foncé sur 3 pixels sur 4, la teinte d’altitude transparaît |
| Repères | C, H, R : pastille 5 × 7 colorée + lettre 3 × 5, point du site ; flèche du nord et échelle dans le bandeau |
| Joueur | **non dessiné** : la feuille HGR ne le montre pas (MAP s’en charge) ; option `you=` de la référence seulement |
| Calcul | à chaque ouverture de TOPO, ligne par ligne, ≈ **1,9 s** à 1,02 MHz (§ 6) |
| Code | ≈ 1,5 Kio, module chargé dans la fenêtre SIM ; 1,75 Kio de tables/tampons dans la même fenêtre (§ 7) |

Pourquoi le mode mixte et pas 192 rangées pleines : 140 × 192 avec
1,25 pixel par cellule donne des cellules exactement carrées, mais oblige à
dessiner la légende dans le graphisme (police, code, place prise sur la carte)
et à interpoler aussi en x. Le mode mixte garde le texte 40 colonnes déjà
utilisé par `module_graphical_topo` (aucun octet de plus en RAM principale), et
la correspondance 1 cellule = 1 pixel supprime l’interpolation horizontale :
une cellule mesure 1 × 1,916 rangée, soit 1,05 fois plus haute que large sur
un écran 4:3 (un pixel couleur DHGR vaut 1,83 rangée en largeur). La feuille
HGR avait 2 points HGR × 1,81 rangée par cellule ; la DHGR garde la même
densité verticale et la même finesse horizontale effective (le pixel couleur
DHGR vaut deux points HGR).

## 2. Correspondance

Rangée `sy` (0..159, 0 en haut = nord), position verticale en cellules
(0 = bord sud, 83 = bord nord), avec `QB` = 1 bit de fraction (demi-cellules) :

```
v(sy) = floor((159 - sy) * 83 * 2^QB / 159)      en 1/2^QB de cellule
j = v >> QB          rangée de cellules du dessous (0..83)
q = v & (2^QB - 1)   fraction (0 ou 1 : rangée de cellules ou mi-chemin)
n = (v + 2^(QB-1)) >> QB    rangée de cellules la plus proche (eau, bois)
```

`v(0) = 166` (rangée 83), `v(159) = 0` (rangée 0) ; chaque rangée de cellules
est la plus proche d’au moins une rangée d’écran (testé), donc chaque cellule
d’eau apparaît. Le pas vaut 1 ou 2 demi-cellules (166/159 = 1,044).

Colonne `x` (0..111) = colonne de cellules `x`, sans interpolation.

**DDA sans multiplication** (celle de `Sheet6502`, testée contre la formule) :
`num = 83 << QB` (166), `step, rem = divmod(num, 159)` (1, 7), `v = num`,
`acc = 158` ; après chaque rangée : `acc += rem ; v -= step ; si acc >= 159 :
acc -= 159 ; v -= 1`.

**Altitude et palier.** Avec `h0 = MAP[j][x] & 127`, `h1 = MAP[min(j+1,83)][x] & 127` :

```
bande = floor((h0 + (h1 - h0) * q / 2^QB) / 4)
```

En 6502 : `q = 0` → `bande = h0 >> 2` ; `q = 1` → `bande = ((h0 + h1) >> 1) >> 2`
(`CLC / ADC / ROR` garde la retenue : moyenne exacte sur 9 bits). Pour
`QB` = 2 ou 3, chaque bit de `q` au-dessus du plus bas ajoute une moyenne
plancher avec `h1` (bit à 1) ou `h0` (bit à 0) ; l’identité
`floor((n + y) / 2) = floor((n + floor(y)) / 2)` rend la chaîne exacte (testée
pour tous `h0, h1, q`). La valeur ne dépasse jamais 8 bits.

**Repères.** Rangée d’un site de cellule `y` : `marker_row(y)` = première
rangée `sy` telle que `n(sy) = y` (recherche sur la DDA, une fois par site).

## 3. Palette et légende

Numéros LORES de `tools/dhgr_palette.py` (RGB POM2). Rampe sous la neige,
indexée par `i = min(9, bande * 10 // SB)`, `SB = ceil(neige / 4)` (12 pour la
Sierra, neige au niveau 48 = 7 200 ft) ; `a/b` = damier, `a` si
`(x + sy)` pair :

| i | Teinte | Courbe normale | Courbe maîtresse |
|---:|---|---|---|
| 0 | vert (12) | brun (8) | noir |
| 1 | vert/jaune (12/13) | brun | noir |
| 2 | jaune (13) | brun | noir |
| 3 | jaune/orange (13/9) | brun | noir |
| 4 | orange (9) | brun | noir |
| 5 | orange/brun (9/8) | brun | noir |
| 6 | brun (8) | noir | noir |
| 7 | brun/gris (8/5) | noir | noir |
| 8 | gris (5) | noir | noir |
| 9 | gris/blanc (5/15) | noir | noir |
| neige | blanc (15) | bleu clair (7) | gris (5) |

| Rôle | Couleur |
|---|---|
| eau libre | bleu foncé (2) |
| eau touchant la terre (rive, rivière d’une cellule) | bleu moyen (6) |
| bois (3 pixels sur 4, sous la limite des arbres) | vert foncé (4) |
| crash C | pastille magenta (1), lettre blanche |
| cabane H | pastille noire, lettre jaune (13) |
| rangers R | pastille violette (3), lettre blanche |
| bandeau, flèche, chiffres | fond noir, encre blanche |

Fenêtre des bois : le vert foncé occupe tous les pixels sauf
`x % 2 == (sy >> 1) % 2 and sy % 2 == 0` (un pixel sur quatre, en quinconce,
période 2 en x et 4 en y) : les forêts sont des masses vert foncé qui gardent
un moucheté de leur teinte d’altitude. Les bois sont montrés si
`4 × bande + base < limite des arbres` (en-tête +27, 110 = 11 000 ft) ;
`forest.s` teste le niveau de la cellule, la feuille le bas de la bande : écart
d’au plus une bande de 400 ft à la limite des arbres.

Courbes maîtresses : les niveaux `4k` tels que `(4k + base) % 20 = 0`
(multiples de 2 000 ft au-dessus de la mer ; base +10 = 24 → 4 000, 6 000,
8 000, 10 000 ft). Choix testés puis écartés : bois en damier 50 % ou en points
25 % (ils se confondent avec la trame orange/brun), rive aqua côté terre
(rivières larges de trois pixels), courbes bleu moyen sur la neige (sommets
pris pour des lacs).

**Bandeau (x 112..139, rangées 0..159).** Fond noir. Nord : lettre N (x 124..126,
rangées 3..7), flèche blanche (pointe rangées 10..13, hampe x 125 jusqu’à 25).
Échelle : colonnes 115..120, 4 rangées par bande de 0 (rangée 157 en bas) à la
bande la plus haute (en-tête +21), teintes et courbes comme sur la carte
(normale sur la rangée sud de la transition, maîtresse sur les deux) ; à
chaque courbe maîtresse, un trait blanc en x 121 et les milliers de pieds en
chiffres 3 × 5 à partir de x 123 (4, 6, 8, 10).

**Lignes texte (rangées 20..23, `t_home` + `puts`, ≤ 40 caractères) :**

```
TOPO  N UP  CONTOURS 400 FT, BOLD 2000
C CRASH  H CABIN  R RANGERS  SCALE KFT
MAP: PLAYER MAP
ESC/RETURN/SPACE: VIEW
```

## 4. Règles de la feuille

Pour chaque pixel `p` de la carte, `K(p)` = eau (cellule la plus proche,
bit 7), sinon `(bande, bois)`. Voisins : les 4 voisins dans la carte.

1. eau avec un voisin terre → **rive** (bleu moyen) ; autre eau → **eau libre** ;
2. terre séparée d’un voisin terre par une courbe maîtresse (`IDX(bande)`
   diffère, `IDX(b)` = nombre de niveaux maîtres `4k`, `1 ≤ k ≤ b`) →
   **maîtresse** de sa bande. Les deux pixels de la transition sont marqués :
   trait de deux pixels ;
3. terre dont le voisin **est** ou **nord** (terre) a une autre bande →
   **courbe** de sa bande : un pixel, du côté ouest/sud de la transition ;
4. sinon teinte tramée, ou vert foncé si bois et fenêtre.

Les pixels de terre ignorent leurs voisins d’eau (les courbes s’arrêtent à la
rive). Puis le bandeau, puis les repères dans l’ordre R, H, C (le crash
dessus). Repère : point du site `(x, marker_row(y))` couleur de pastille ;
pastille de 5 × 7 en `x+1..x+5`, rangées `r-7..r-1` (au nord-est, touchant le
point en diagonale), à l’ouest (`x-5..x-1`) si `x + 5 > 111`, au sud (`r+1..r+7`)
si `r < 7` ; lettre aux colonnes 1..3, rangées 1..5 de la pastille. Sites lus
dans l’en-tête : crash `(+3, +5)` (octets forts 8.8), rangers `(+8, +9)`,
cabane `(+17, +18)` si `+16`.

La règle 3 (côté ouest/sud seulement) est volontaire : c’est elle qui rend
l’écriture rétroactive idempotente au § 5. La règle « côté haut » essayée
d’abord donnait la même image à un pixel près mais demandait une priorité par
pixel (≈ 1 M de cycles de chemin lent).

## 5. Algorithme 6502

Balayage par rangées, `x` de 111 à 0 (`DEY/BPL`), voisins causaux : **est**
(`kr`, pixel traité juste avant) et **nord** (`KP[x]`, rangée précédente).
Les tampons de la rangée nord ne sont emballés vers l’écran qu’après la
rangée courante, si bien qu’une règle qui marque le voisin (maîtresse, rive)
peut encore l’écrire.

### 5.1 Codes et tables

`K` = `bande | $20` (bois, cellule la plus proche) ou `$40` (eau). Rangée
`sy`, colonne `x` :

| Table | Octets | Contenu |
|---|---:|---|
| `FILL{r}{p}`, r = sy & 3, p = x & 1 | 8 × 65 = 520 | couleur d’un pixel ordinaire de code K (teinte tramée, fenêtre des bois, `FILL[$40]` = eau libre) |
| `MARK` | 65 | couleur de courbe de la bande de K ; `MARK[$40]` = rive |
| `INDEXK` | 64 | couleur de maîtresse de la bande de K |
| `IDXK` | 64 | `IDX(bande)` : maîtresse entre deux pixels terre ssi `IDXK` diffère |
| `T0 T1a T1b T2 T3a T3b T4 T5a T5b T6` | 10 × 16 = 160 | emballage d’un groupe de 7 couleurs (ci-dessous) |
| glyphes C H R N 0-9 | 14 × 5 = 70 | 3 bits par rangée (dans le code) |
| `RAMP`, `LINE`, `INDEX`, repères | ≈ 40 | constantes d’où les tables sont construites (dans le code) |

Construction à l’ouverture depuis l’en-tête : base `+10`, neige `+11`,
plus haut niveau + 1 `+21` (0 : maximum de la grille), limite des arbres `+27`
(0 : 110). Coût ≈ 25 000 cycles (tables, sites).

Emballage d’un groupe de 7 pixels `c0..c6`, `r = rot(c)` (4 octets aux pair,
main pair, aux impair, main impair) :

```
b0 = T0[c0]  | T1a[c1]               T0 = r            T1a = (r & 7) << 4
b1 = T1b[c1] | T2[c2]  | T3a[c3]     T1b = r >> 3      T2 = r << 1     T3a = (r & 3) << 5
b2 = T3b[c3] | T4[c4]  | T5a[c5]     T3b = r >> 2      T4 = r << 2     T5a = (r & 1) << 6
b3 = T5b[c5] | T6[c6]                T5b = r >> 1      T6 = r << 3     (& $7F)
```

### 5.2 Tampons et page zéro

| Zone | Octets |
|---|---:|
| `KA`, `KB` (K courante / nord, permutées par patch) | 2 × 112 |
| `CA`, `CB` (couleurs courante / nord, 140 dont bandeau) | 2 × 140 |
| `WROW` (bois de la rangée la plus proche, `$20` ou 0) | 112 |
| tables du § 5.1 | 1 008 (+ alignement) |
| **total en fenêtre SIM** | **≈ 1 730** (1 750 avec FILL alignées sur pages) |
| page zéro : `r0 r1` (2 + 2), `h1 kr kc f`, `b0 b1 b2 gb` | 12 (scratch du rendu, la vue est arrêtée) |

`r0`/`r1` viennent de `grid_lo`/`grid_hi` (`wild.s`). `WROW` est recalculé
quand `n >> 1` change (42 fois) : 56 bits de `forest_bits` → 112 octets.

### 5.3 Boucles chaudes

Esquisse assemblée (`build/topo/sketch/topo_hot.s`, ca65, non liée) ; `P` =
opérande patché une fois par rangée (permutation des tampons, table FILL de
la rangée, adresse de la rangée d’écran). Deux variantes de rangée
(`q = 0` rangée de cellules, `q = 1` mi-chemin), chacune déroulée deux fois
(x impair, x pair : table `FILL` différente).

```
; rangée de cellules : K = (h0 >> 2) | bois            cycles
cell:   lda (r0),y        ; cellule la plus proche     5
        bmi @eau          ;                            2
        lsr a             ;                            2
        lsr a             ;                            2
        ora WROW,y        ;                            4   = 15
; rangée mi-chemin : K = (floor((h0+h1)/2) >> 2) | bois
mid:    lda (r1),y        ; la plus proche = j+1       5
        bmi @eau          ;                            2
        sta h1            ;                            3
        lda (r0),y        ;                            5
        and #$7F          ;                            2
        clc               ;                            2
        adc h1            ;                            3
        ror a             ; moyenne exacte sur 9 bits  2
        lsr a             ;                            2
        lsr a             ;                            2
        ora WROW,y        ;                            4   = 32
@eau:   lda #$40 / bne @k ; eau : 5+3+2+3              = 13
; queue commune
@k:     sta KC,y   P      ;                            5
        cmp KP,y   P      ; nord                       4
        bne slow          ;                            2
        cmp kr            ; est                        3
        bne slow          ;                            2
        tax               ;                            2
        lda FILL,x P      ; FILL{sy&3}{x&1}            4
        sta CC,y   P      ;                            5
        dey               ;                            2
        (bpl une fois pour deux pixels)                1,5  = 30,5 (31 au modèle)
```

Chemin lent (entré par l’un des deux `BNE`, A = K), par paire de voisins
différents, sans sous-programme :

```
slow:  sta kc
       ; paire nord (si KP[x] != K), puis paire est (si kr != K)
       eor KP,y ; tax ; and #$40 ; bne @eau      ; exactement un des deux est de l'eau
       txa ; and #$1F ; beq @suite               ; bois seulement : rien
       ldx KP,y ; lda IDXK,x ; ldx kc ; cmp IDXK,x
       bne @maitresse                            ; sinon : courbe (f |= 1)
@maitresse: f |= 3 ; ldx KP,y ; lda INDEXK,x ; sta CP,y   ; rétroactif, idempotent
@eau:  K = $40 ? f |= 1 (rive) : lda #6 / sta CP,y        ; le voisin d'eau devient rive
       ... même bloc pour l'est, cible CC+1,y ...
fin:   ldx kc ; lda {FILL|MARK|INDEXK},x (selon f) ; sta CC,y ; stx kr ; jmp retour
```

Les écritures rétroactives ne demandent aucun test de priorité : une
maîtresse n’écrit que sur de la terre (couleur maîtresse de la bande du
voisin, déjà la plus forte), une rive que sur de l’eau, et un pixel déjà
traité n’est jamais recalculé.

Emballage d’une rangée (après le bandeau et les repères), boucle de 20 groupes :

```
@g:  ldx CP+0,y / lda T0,x / ldx CP+1,y / ora T1a,x / sta b0
     lda T1b,x / ldx CP+2,y / ora T2,x / ldx CP+3,y / ora T3a,x / sta b1
     lda T3b,x / ldx CP+4,y / ora T4,x / ldx CP+5,y / ora T5a,x / sta b2
     lda T5b,x / ldx CP+6,y / ora T6,x            ; A = b3
     ldx gb / sta $C054 / sta ROW+1,x / lda b1 / sta ROW,x        ; principale
     sta $C055 / lda b0 / sta ROW,x / lda b2 / sta ROW+1,x        ; auxiliaire (IRQ masquées)
     inx / inx / stx gb / tya / clc / adc #7 / tay / cpy #140 / bcc @g
```

137 cycles par groupe (68 de tables, 40 d’écriture, 20 de boucle), 104 octets.
Version entièrement déroulée (`ldx CP+k` absolus, `ldy #2g / sta (scr),y`) :
≈ 110 cycles, ≈ 1,4 Kio de code (−86 000 cycles par feuille).

### 5.4 Pilote

```
topo_sheet:  topo_tables ; topo_sites ; prime (rangée 0 → KP, son propre nord)
  pour sy = 0..159 :
      DDA → j, q ; r0 = grid[j], r1 = grid[min(j+1,83)]
      si n >> 1 change : topo_wrow
      patches (≈ 30 opérandes, par une liste d'adresses) ; kr = K(111)
      boucle cell ou mid (x = 111..0)
      si sy > 0 : topo_flush(sy - 1)          ; bandeau + repères dans CP, emballage
      permuter KA/KB et CA/CB
  topo_flush(159)
```

Le bandeau se calcule par rangée : 28 octets noirs, puis pour la barre
`d = 157 - sy`, `b = d >> 2`, `sub = d & 3` : teinte `FILL{sy&3}{x&1}[b]`,
maîtresse si `sub` est la rangée haute (3) ou basse (0) d’une transition où
`IDXK` change, courbe `MARK[b]` si `sub = 3` sous une bande supérieure ;
chiffres, trait, N et flèche par plages de rangées ; pastilles des repères
(3 × 7 octets précalculés : x, rangée, couleurs, glyphe, point).

## 6. Budget de temps

Comptes d’événements de `Sheet6502` (opérations du Python) × cycles des
esquisses ci-dessus (`topo_dhgr_ref.CYCLES`), à 1 020 484 cycles/s (POM2 IIe).
En milliers de cycles :

| Carte | Rapides | Lents | dont courbes/rives | Échantillon | Classement rapide | Chemin lent | Emballage | Rangées, bois, bandeau | Total | Secondes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1985 niv. 4 | 10 740 | 7 180 | 6 397 | 416 | 332 | 548 | 438 | 151 | 1 912 459 | **1,87** |
| 7 niv. 1 | 10 612 | 7 308 | 7 002 | 422 | 328 | 572 | 438 | 151 | 1 938 517 | **1,90** |
| 2026 niv. 7 | 10 551 | 7 369 | 6 660 | 398 | 327 | 558 | 438 | 151 | 1 898 792 | **1,86** |
| 42 niv. 10 | 10 645 | 7 275 | 6 330 | 415 | 329 | 555 | 438 | 151 | 1 915 591 | **1,88** |
| synthétique (sans bois) | 16 314 | 1 606 | 1 450 | 417 | 505 | 115 | 438 | 146 | 1 648 674 | 1,62 |

(+ 25 000 cycles de préparation.) 17 920 pixels de carte, 3 200 groupes
emballés. Un tiers des pixels de carte est une courbe ou une rive : relief de
8 400 ft, courbes de 400 ft sur 112 colonnes ; le chemin lent est le dessin
des courbes lui-même (≈ 70 cycles contre 31).

Variantes mesurées sur la carte 1985 (même modèle) :

| Précision verticale | Échantillonnage | Total |
|---|---:|---:|
| `QB` = 1, demi-cellules (retenu) | 416 000 | **1,87 s** |
| `QB` = 2, quarts | 549 000 | 2,00 s |
| `QB` = 3, huitièmes | 676 000 | 2,13 s |

À l’œil, les trois précisions donnent la même feuille (écart de position
≤ 1/4 de cellule ≈ 0,5 rangée) ; `QB` = 1 gagne 7 % sur `QB` = 2.

Marges disponibles si la mesure réelle dépasse 2 s : emballage déroulé
(−86 000, +1,3 Kio dans la fenêtre SIM), groupes du bandeau sans contenu écrits
à zéro (−25 000), boucle de rangée sans `JMP` entre les deux copies (−5 000).
Le budget est à **valider sur POM2** (`pcprof` d’a2shot) dès l’intégration :
les chiffres ci-dessus sont des comptes d’esquisses, pas une mesure.

Affichage pendant le calcul : effacer les rangées 0..159 (≈ 84 000 cycles,
comme `clear_rows` pour une vue), passer en DHGR mixte avec la légende, puis laisser la
feuille se dévoiler de haut en bas (une rangée toutes les 12 ms) ; l’original
dessinait aussi sa carte progressivement.

## 7. Mémoire et placement

**Code estimé** (octets ; boucles chaudes assemblées, le reste estimé) :

| Partie | Octets |
|---|---:|
| boucles `cell`/`mid` × 2 parités (assemblées : 78 + 98) | 176 |
| chemin lent (deux paires en ligne, deux parités) | ≈ 260 |
| emballage en boucle (assemblé) | 104 |
| pilote, DDA, liste de patches, amorce, `kr` | ≈ 180 |
| construction des tables + constantes (rampe, courbes, repères) | ≈ 250 |
| `topo_wrow` | ≈ 40 |
| bandeau, chiffres, flèche, repères + glyphes (70) | ≈ 370 |
| sites, en-tête, modes vidéo, IRQ | ≈ 100 |
| **total** | **≈ 1 480** |

Il tient dans un module de 2 Kio. Proposition : module `TOPOGEN` stocké en
RAM auxiliaire (≈ 1,5 Kio pris sur les 8 Kio libérés par l’image TOPO),
copié par `mem_fetch` dans la **fenêtre SIM** (`$9600`, ≈ 26 ms) avec ses
tables et tampons (`$9C00-$A2FF`, ≈ 1,75 Kio). `module_graphical_topo` (SITES,
fenêtre `$5800`) l’appelle sans quitter SITES ; il met déjà `sim_loaded` à 0,
la simulation est rechargée comme aujourd’hui. RAM principale : 0 octet de
plus (le texte de la légende remplace celui de SITES, même longueur à
± 20 octets). RAM auxiliaire : 8 192 − 1 500 ≈ **6,7 Kio libérés**.

**Cache ou recalcul.** La feuille n’existe que sur la page DHGR (rangées
0..159 = 12 800 octets des deux banques) ; elle écrase la vue.

| Stratégie | RAM aux. | Ouvrir TOPO | Revenir à la vue |
|---|---:|---|---|
| A. recalcul à chaque fois (recommandé pour le lot 4) | 0 | ≈ 1,9 s | rendu complet comme aujourd’hui (`show_view_hidden` : 1,9 s LOOK, 5,8 s VIEW avec l’épave) |
| B. A + instantané de la vue, rangées 16..175 (deux banques) | 12 800 | ≈ 1,9 s + 0,18 s (sauvegarde) | ≈ 0,18 s (copie, pas de lancer de rayons) |
| C. feuille en cache (rangées 0..159) | 12 800 | 1re fois 1,9 s, puis ≈ 0,18 s | rendu complet |
| D. profils de colonnes de la vue (segments `dspan`) | 6 600 à 11 400 mesurés¹ | ≈ 1,9 s | peinture seule, 0,6 à 1 s (DHGR.md § 6) |

¹ `dhgr_ref.column_runs` sur six vues de la carte 1985 (départ, trois caps,
trois positions au hasard) : 3 240 à 5 609 segments de rangées 16..175 à
2 octets + 140 compteurs ; un segment tramé compté comme une paire (moteur)
réduit le bas de la fourchette vers 6,5 Kio.

Copie de 12 800 octets : ≈ 14 cycles par octet (`LDA abs,X / STA abs,X /
INX / BNE`), soit ≈ 0,18 s ; la moitié auxiliaire exige `RAMRD`+`RAMWRT`, donc
la boucle de copie en pile (`$0120`) déjà utilisée par les transferts. Après
retrait de l’image TOPO, la RAM auxiliaire libre est ≈ 17,9 Kio (8 192 + 284 +
5 260 + 4 096 + 89) mais fragmentée : B ou C tiennent (bloc de 8 Kio + carte
langage banque 1 + 512 octets de la banque 2), pas les deux. **B** donne le
meilleur aller-retour (2,3 s au lieu de 3,8 à 7,7 s) ; à décider après mesure
du lot 4, la règle « aucune avance du temps, état inchangé » étant la même.

## 8. Ce que le moteur doit implémenter

1. **Supprimer** l’image : `tools/graphical_topo.py` du build et de
   `build_disk.py` (bloc TOPO de 8 Kio en aux), le `mem_fetch` n° 0 de
   `module_graphical_topo`.
2. **Module `TOPOGEN`** (`src/topo_dhgr.s`, segment chargé à `$9600`) :
   - `topo_sheet` — entrée sans paramètre ; lit `MAP` (`$7000` : +3, +5, +8, +9,
     +10, +11, +16..+18, +21, +26, +27 ; grille `$7040`), `forest_bits`,
     `grid_lo/grid_hi` ; écrit les rangées 0..159 des deux banques, ne touche
     pas 160..191 ; sort banque principale, `80STORE` actif, IRQ rétablies ;
     détruit `$9600-$A2FF` et 12 octets de page zéro de rendu.
   - `topo_tables` — `FILL{r}{p}[65]`, `MARK[65]`, `INDEXK[64]`, `IDXK[64]`,
     `T0..T6[16]` depuis `RAMP` (10 entrées `a<<4|b`), `LINE`/`INDEX` (11 + 11),
     la fenêtre des bois et l’en-tête (`topo_palette.tables` en est l’oracle).
   - `topo_sites` — trois repères : rangée (`marker_row`), pastille (x, rangée),
     couleurs, glyphe.
   - `topo_wrow` (A = rangée de bois 0..41) → `WROW[112]`.
   - `topo_row_cell`, `topo_row_mid` — boucles du § 5.3 (x = 111..0).
   - `topo_flush` (A = rangée d’écran) — bandeau + repères dans `CP`, puis
     `topo_pack` (20 groupes, `PAGE2` sous `80STORE`, IRQ masquées).
3. **`module_graphical_topo`** (sites.s) : `view_hide`, `mem_fetch` de
   TOPOGEN, effacement des rangées 0..159, `show_dhgr` (mixte, `80COL`), légende
   à `WNDTOP` = 20 (les quatre lignes du § 3), `jsr topo_sheet`, puis l’attente
   de touche actuelle (Échap, Retour, Espace) et `show_view_hidden`. Plus
   d’appel à `show_hgr` (TOPO reste en DHGR).
4. **Tests** : `tests/test_graphical_topo.py` lit les deux banques
   (`peek:2000:8192`, `poke:C055:00`, `peek:2000:8192`, `poke:C054:00`) et
   compare les rangées 0..159 à `topo_dhgr_ref.encode(sheet(carte), range(160))` ;
   `RD80VID` ≥ `$80` pendant TOPO ; texte « TOPO » rangées 20..23 ; vue
   redessinée et état inchangé au retour (inchangé) ; mesurer le temps
   d’ouverture (`pcprof`) contre le budget du § 6 et les lectures disque (0).
   `test_topo_dhgr.py` reste l’oracle Python.

## 9. Captures (`build/topo/`, hors Git)

`python3 -I tests/test_topo_dhgr.py --refs` écrit, pour 1985/4, 7/1, 2026/7,
42/10 et la carte synthétique de `test_graphical_topo` (`topo_legacy`) :

- `topo_<g>_<n>.png` — page 280 × 192 (pixel couleur doublé), convention de
  `build/dhgr/` ;
- `topo_<g>_<n>_x2.png` — rangées 0..159 en 560 × 320 (proportions de l’écran) ;
- `topo_<g>_<n>_screen.png` — écran mixte complet avec les quatre lignes de
  légende (police bbfont, cellules impaires) ;
- `topo_<g>_<n>.main` / `.aux` — les deux banques de 8 Kio (rangées 0..159),
  à comparer aux octets du jeu ;
- `map_<g>_<n>.bin` — les cartes générées.

`build/topo/sketch/topo_hot.s` et `.lst` : esquisse des boucles chaudes du § 5.3.

## 10. Contrôles (`tests/test_topo_dhgr.py`)

- correspondance : `v(0)`, `v(159)`, DDA = formule, chaque rangée de cellules
  est la plus proche d’une rangée, moyennes plancher = interpolation exacte
  (tous `h0`, `h1`, `q`, `QB` = 1..3), proportions des cellules ;
- octets : pixels connus lus bit à bit dans les deux banques, motifs TN #3,
  tables d’emballage contre l’encodeur ;
- par carte (1985/4, 7/1, 2026/7, synthétique sans bois) : déterminisme,
  rangées 160..191 non écrites, **`Sheet6502` identique au bit près**, flèche
  et fond du bandeau, échelle, repères aux positions de l’en-tête (rangée la
  plus proche = y du site, glyphe complet, crash au-dessus), eau exactement
  sur les cellules d’eau les plus proches et chaque cellule d’eau montrée, rive
  = eau touchant la terre, bois seulement sur les cellules boisées et partout
  où un pixel ordinaire est dans la fenêtre ;
- `QB` = 2 et 3 également identiques au bit près ;
- courbes : chaque transition maîtresse marque ses deux pixels, chaque
  transition normale son pixel sud ; libellés 4, 6, 8, 10 ;
- repères aux bords (crash au coin nord-est, rangers au sud-ouest, sans cabane) ;
- tailles des tables (943 octets) et budget < 2 s pour chaque carte, légende
  ≤ 40 colonnes.

## 11. Intégration au jeu (lot 4)

`src/topo_dhgr.s` (module 0 TOPOGEN, segment `TOPOGEN` à `$9600`, tables
et tampons `TOPOBSS` alignés sur des pages `$A100-$AEBB`) reprend
`Sheet6502` : DDA, boucles `cell`/`mid` déroulées par parité (macro
`TP_PIXEL`, opérandes de page patchés par `tp_patch`, ≈ 30 écritures directes
par rangée), chemin lent en sous-programme, bandeau et repères dans la rangée
nord, emballage en boucle de 20 groupes (tables `T0..T6` de
`topo_palette.pack_tables`). La feuille du jeu est **identique au bit près** à
`topo_dhgr_ref.sheet` sur la carte du disque et sur la carte synthétique sans
bois (`tests/test_graphical_topo.py`, qui lit les deux banques).

Choix d'intégration : pas d'effacement des rangées 0..159 ni de rideau ; la
feuille balaie la vue de haut en bas (le DHGR mixte et la légende sont
affichés avant le premier pixel). Avant cela, `tp_save` copie la vue
(rangées 0..159, 12 800 octets) en carte langage auxiliaire ; `topo_close`
la recopie au retour (option B du § 7, `docs/MEMORY.md` § 8.4).

Mesures POM2 (`tools/profile_actions.py`, `pcprof` par zone) :

| Étape | Secondes |
|---|---:|
| copie de TOPOGEN (2 681 octets) | 0,05 |
| instantané de la vue | 0,23 |
| boucles `cell`/`mid` (échantillon + classement rapide) | 0,96 |
| chemin lent (courbes, rives, maîtresses) | 0,85 |
| bandeau, repères et emballage (`tp_flush`) | 0,60 |
| patches, rangées de bois, tables, sites | 0,30 |
| **ouverture totale (commande → attente de touche)** | **2,99** |
| retour (recopie de l'instantané) | **0,24** |

L'estimation du § 6 (1,9 s pour la feuille) supposait un chemin lent
de ≈ 70 cycles et un emballage de 137 cycles par groupe ; le code mesure
≈ 120 cycles par pixel lent (entrée par `JSR`, drapeaux en mémoire) et
≈ 150 par groupe. Pistes restantes si l'ouverture doit descendre sous 2,5 s :
chemin lent recopié dans chaque boucle (−0,15 s, ≈ +600 octets), emballage
déroulé (−0,09 s, +1,3 Kio) ; le stock auxiliaire n'a plus que 1 738 octets
libres. Aller-retour TOPO : 3,2 s contre ≈ 6 s au lot 3 (copie de l'image
puis rendu complet au retour).
