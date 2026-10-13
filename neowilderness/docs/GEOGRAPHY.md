# Neowilderness — géographie fine native (lot 5) : mesures et conception

Analyse en lecture seule, sans modification du jeu. Outil :
`tools/geo_atlas.py` (sorties `build/geo/report.json` et `report.md`) ;
tests : `tests/test_geo_atlas.py` (Python pur, ~8 s). Tous les chiffres
ci-dessous viennent de `python3 tools/geo_atlas.py --jobs 8` (1 min 40 s),
sauf mention « estimé ».

## 1. Données mesurées

La géographie fine est la grille native 224 × 168 interrogée par
`cell_native` (`src/geography.s`) : un octet par case (niveau ; bit 7 eau ;
bit 6 lac pour les cases d'eau de la carte Sierra) et le masque des bois,
28 octets par ligne, soit **42 336 octets** bruts. Aujourd'hui elle n'existe
que sur les disques de comparaison (`NEOWILD.GEO`, 24 banques de 7 lignes
complétées à 2 Ko = 49 152 octets, 96 blocs ProDOS) ; `mkmap.py` ne produit
que la grille 112 × 84.

| Carte | Origine | Cases d'eau | Cases boisées | Crash → rangers (x, y) |
|---|---|---:|---:|---|
| `sierra` | TOPO.B + échantillons ROM de `$15A8` (`build/re_geography`) | 783 | 2 048 | (23, 86) → (200, 134) |
| `sierra-topo` | TOPO.B seul, interpolé par `topo.heightmap` comme `topo2map.py` | 783 | 2 048 | idem |
| `gen-sS-LL` (9) | `mkmap.Map(S, L)`, S ∈ {1985, 7, 42}, L ∈ {1, 4, 10} | 112 – 2 984 | 1 715 – 7 643 | voir `report.json` |
| `gen-s9999-L10-r120` | idem + 120 rivières supplémentaires (`Map.rivers`) | 2 684 | 6 196 | (196, 67) → (18, 38) |
| `rough-s1985-L4` | relief de `gen-s1985-L4` + bruit ±1 sur chaque case sèche | 571 | 3 381 | (68, 57) → (200, 66) |
| `noise-1` | niveaux, eau (10 %) et bois (50 %) uniformément aléatoires | 3 776 | 18 687 | (20, 20) → (200, 150) |

Contrôles : la géographie `sierra` est identique octet pour octet à la fin
de `../wilderness/build/parity-stage15/map.bin`, et la grille 112 × 84 que
l'outil en dérive (`mkmap.coarse_grid`) est identique à celle de ce fichier.
La mesure de référence du TODO (11 305 octets en 24 blocs) est reproduite
exactement : c'est le LZ actuel (`pack_boot.compress`) appliqué aux 1 764
octets utiles de chaque banque (hauteurs + bois, sans remplissage ni
gabarit). `topo2map.py` est un script (il s'exécute à l'import) : ses cinq
lignes de conversion sont reformulées sur `topo.rows`/`topo.heightmap`.
`mkmap` et `topo` sont importés, pas copiés.

Pour mémoire, la représentation de l'original (enregistrements par ligne
`$63E4-$A121`, interpolés à chaque requête par `$15A8`) occupe 15 678
octets + 402 de bois + 336 de pointeurs : plus que tous les atlas ci-dessous.
De plus, aucune des formules d'interpolation entière essayées ne reproduit
les échantillons ROM (la meilleure, plancher, diffère sur 367 cases sèches).

## 2. Codecs comparés

Chaque bloc est compressé **indépendamment** ; un bloc dont l'encodage n'est
pas plus court est stocké brut (un bit par bloc dans l'index, à côté du
décalage de 2 octets ; index = 2 n + n/8 octets, compté dans les totaux).

| Codec | Format | Décodeur (estimé) | Coût de décodage |
|---|---|---:|---|
| `lz` | LZ actuel du chargeur (`tools/pack_boot.py`, `ld_decode` de `src/boot.s`) | ~140 o | compté sur `ld_decode` : 50 c par littéral, 130 + 18 n par copie, 33 par groupe de 8 |
| `overlay` | LZ en place retiré (`pack_overlay.py`/`overlay_codec.s` : en-tête 6 o, flux inversé, préfixe brut de 128 o), reconstruit sur `pack_boot` ; identique à la copie de référence sur 49 blocs | ~260 o | 93 c par littéral (`jsr unpack_get` par octet), 230 + 18 n par copie, ~7 200 fixes (préfixe + page zéro) |
| `rle` | octet de contrôle : < $80 → c+1 littéraux, ≥ $80 → répétition (3–130) | ~50 o | 45 par jeton, 18 par littéral, 13 par octet répété |
| `nib` | **conçu ici**, flux de bits : plans eau/lac et bois en longueurs de plages (4 bits, extension par octets), puis un résidu de niveau par case, code fixe **2 bits** (00 = 0, 01 = +1, 10 = −1, 11 + **quartet** −8..7 ; quartet 8 = niveau absolu sur 7 bits) ; prédicteur gauche + haut − haut-gauche dans le bloc | ~260 o | 14 c par bit lu, 46 par case, 14/16 par case pour les plans eau/bois, 30 par plage |
| `vlc` | idem avec un code 1/2/3 bits (0 → 0, 10 → ±1 fréquent, 110 → l'autre, 111 + quartet) ; un bit par bloc choisit le signe fréquent | ~280 o | idem |
| `coarse` | `vlc` dont le prédicteur est l'interpolation bilinéaire arrondie de la **grille 112 × 84 déjà résidente** à `$7040` ; les cases paires/paires d'une case grossière sèche lui sont égales et ne sont pas codées du tout | ~360 o | 63 par case codée, 20 par case déduite |

Les coûts des décodeurs à bits sont des **estimations** par décompte
d'instructions d'une boucle esquissée (lecture de bit par `asl`/`bne` avec
recharge tous les 8 bits, tampon de ligne en page zéro) : ±25 %, à
confirmer par `pcprof` sur un vrai décodeur avant tout choix définitif. Les
coûts LZ sont comptés sur le code existant, sans franchissement de page.

Entropie d'ordre 0 des résidus (exploration sur Sierra et trois cartes
générées) : 1,05–1,36 bit/case avec les prédicteurs gradient/médian,
0,74–0,98 bit/case contre la grille grossière ; conditionné aux résidus
voisins, le gradient descend à 0,88–0,90 bit/case. `vlc` est à
~1,1–1,5 bit/case : une marge de 10 à 20 % reste possible avec un code
contextuel, au prix d'un décodeur plus lent.

## 3. Taille de l'atlas

### Carte Sierra, toutes formes de bloc (octets stockés + index)

| Codec | band7 (24, actuel) | band4 (42) | band8 (21) | band14 (12) | band21 (8) | tile16 (154) | tile32 (42) | tile32×24 (49) | tile56×42 (16) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `lz` | 11 356 | 13 335 | 10 981 | 9 874 | 9 204 | 14 263 | 11 417 | 11 664 | 10 004 |
| `overlay` | 13 822 | 17 588 | 13 107 | 11 086 | 9 996 | 28 665 | 15 561 | 16 553 | 11 487 |
| `rle` | 20 622 | 20 674 | 20 607 | 20 588 | 20 563 | 23 053 | 21 922 | 21 944 | 21 289 |
| `nib` | 10 678 | 10 852 | 10 661 | 10 591 | 10 553 | 11 104 | 10 867 | 10 876 | 10 766 |
| `vlc` | 7 863 | 8 067 | 7 836 | 7 753 | 7 696 | 8 291 | 8 013 | 8 027 | 7 914 |
| `coarse` | **6 176** | 6 266 | 6 169 | 6 145 | 6 125 | **6 379** | 6 359 | 6 365 | 6 333 |

Les LZ dépendent fortement de la taille du bloc (fenêtre et préfixe : le
format en place garde 128 octets bruts par bloc, ruineux pour des tuiles de
288 octets). Les codecs à bits n'en dépendent presque pas (+3 % de band21
à tile16).

### Toutes les cartes (octets stockés + index)

| Carte | `lz` band7 | `overlay` band7 | `rle` band7 | `nib` band7 | `vlc` band7 | `coarse` band7 | `coarse` tile16 | `lz` tile16 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sierra | 11 356 | 13 822 | 20 622 | 10 678 | 7 863 | 6 176 | 6 379 | 14 263 |
| sierra-topo | 12 062 | 14 445 | 21 271 | 10 615 | 7 808 | 6 066 | 6 267 | 15 061 |
| gen-s1985-L1 | 14 992 | 17 389 | 26 925 | 11 072 | 8 668 | 5 883 | 6 030 | 17 462 |
| gen-s1985-L4 | 15 895 | 18 201 | 29 167 | 10 984 | 8 776 | 5 875 | 6 052 | 18 546 |
| gen-s1985-L10 | 16 246 | 18 572 | 28 191 | 11 703 | 9 290 | 6 647 | 6 670 | 19 509 |
| gen-s7-L1 | 15 699 | 17 930 | 26 061 | 10 285 | 7 885 | 4 927 | 5 230 | 18 686 |
| gen-s7-L4 | 16 291 | 18 549 | 29 364 | 10 545 | 8 402 | 5 289 | 5 528 | 18 626 |
| gen-s7-L10 | 18 104 | 20 163 | 32 921 | 11 261 | 9 142 | 6 095 | 6 255 | 20 428 |
| gen-s42-L1 | 16 089 | 18 452 | 28 696 | 10 993 | 8 804 | 5 822 | 5 995 | 18 594 |
| gen-s42-L4 | 16 735 | 18 956 | 28 793 | 11 191 | 8 924 | 5 908 | 6 050 | 19 700 |
| gen-s42-L10 | 16 662 | 18 948 | 29 272 | 11 236 | 8 899 | 6 197 | 6 272 | 19 390 |
| gen-s9999-L10-r120 (rivières denses) | 19 696 | 21 790 | 31 558 | 13 167 | 10 929 | 8 500 | 8 484 | 22 113 |
| rough-s1985-L4 (bruit ±1) | 30 493 | 31 719 | 37 769 | 17 905 | 19 479 | 10 906 | 11 072 | 33 733 |
| noise-1 (aléatoire) | 42 387 | 42 387 | 42 387 | 42 387 | 42 387 | 42 387 | 42 664 | 42 664 |

Lecture :

- **La mesure Sierra n'est pas représentative des cartes générées** : avec
  le LZ actuel, les neuf cartes `mkmap` prennent 15,0 à 18,1 Ko en band7
  (contre 11,3 Ko pour Sierra), 19,7 Ko avec des rivières denses. Le relief
  gaussien de `mkmap` n'est pas linéaire par morceaux comme celui de TOPO,
  et le LZ n'y trouve pas de répétitions.
- `coarse` est le plus petit partout sauf sur le bruit : 4,9–6,7 Ko sur
  les cartes réalistes, 8,5 Ko avec des rivières denses (le plan d'eau y
  coûte 2,6 Ko), 10,9 Ko sur le relief bruité (contre 30 Ko en LZ).
- Données incompressibles : tous les codecs retombent sur le stockage brut
  (42 336 octets + index). **Aucune borne ne vaut sans contrôle à la
  génération** : `build_disk.py` devrait refuser une carte dont l'atlas
  dépasse le budget retenu.
- Part des plans dans `coarse` band7 : eau 696 o et bois 323 o (Sierra) ;
  eau 714–896 o et bois 341–898 o (générées) ; le reste (4,5–5,1 Ko) est
  le relief.

## 4. Pire bloc et coût de décodage

Pire bloc (octets stockés), cycles par octet produit et pire décodage
(ms à 1,023 MHz). « Réalistes » = Sierra, sierra-topo et les 9 cartes
`mkmap` ; entre parenthèses rivières denses / relief bruité. Bruit : copie
brute à 17 c/o (`mem_fetch`).

| Forme (décodé) | Codec | Pire bloc | c/o réalistes | Pire décodage ms |
|---|---|---:|---:|---:|
| band7 (1 764) | `lz` | 913 (1 045 / 1 407) | 31,5–39,1 | 73,9 (78,2 / 92,6) |
| | `overlay` | 996 (1 076 / 1 444) | 44,1–57,6 | 111,5 (118,5 / 145,1) |
| | `rle` | 1 507 | 19,7–21,4 | 41,2 |
| | `nib` | 561 (633 / 779) | 82,6–98,8 | 183,4 (197,1 / 216,1) |
| | `vlc` | 441 (519 / 846) | 76,3–92,5 | 169,4 (184,6 / 223,4) |
| | `coarse` | 358 (451 / 523) | 73,8–92,0 | 176,4 (191,9 / 190,6) |
| tile16 (288) | `lz` | 258 (260 / 279) | 34,4–41,0 | 15,4 (15,1 / 15,7) |
| | `rle` | 288 | 20,6–21,8 | 8,1 |
| | `vlc` | 100 (123 / 172) | 67,4–79,9 | 32,6 (35,7 / 41,8) |
| | `coarse` | **87** (104 / 108) | 64,6–78,9 | **33,4** (38,0 / 35,3) |
| tile32×24 (864) | `lz` | 625 (557 / 770) | 32,2–38,9 | 41,0 (40,8 / 46,1) |
| | `coarse` | 229 (292 / 287) | 66,5–84,9 | 94,6 (106,6 / 97,6) |
| tile32 (1 152) | `coarse` | 288 (402 / 373) | 67,9–85,2 | 123,2 (145,6 / 129,4) |
| band21 (5 292) | `lz` | 2 029 (2 369 / 3 597) | 29,7–36,4 | 200,4 (214,7 / 267,9) |
| | `coarse` | 982 (1 280 / 1 423) | 75,4–92,9 | 510,0 (564,4 / 551,9) |

Le tableau complet (9 formes × 6 codecs × 14 cartes) est dans
`build/geo/report.md`. Les codecs à bits sont 2 à 3 fois plus lents par
octet que le LZ mais traitent 2 à 3 fois moins de données ; la différence
utile est le coût par **changement de bloc**, donc par la taille du bloc.

## 5. Localité des requêtes

Modèle (d'après `src/game.s`, `src/travel.s`, `src/fauna.s`,
`src/water.s`) : un pas de WALK/SWIM avance d'une demi-case (une unité fine
sur l'axe majeur) et interroge `native_next` (case suivante),
`native_here` (case courante) et, majorant, le 3 × 3 de
`fauna_environment` autour de la case courante. FILL/REFILL natif
n'interroge que `native_here` ; `swim_land` ajoute `native_next` ; le 3 × 3
de la faune suit dans `stationary_resources`. Itinéraires : `direct`
(trame rectiligne crash → rangers, en-tête TOPO `$6083`/`$6080` ou
`Map.start`/`Map.goal`), `detour` (en L), `meander` (marche aléatoire
déterministe vers le but, segments de 5 à 20 pas), `scenario`
(`tests/scenario.py` : WALK 1 H, SWIM 1 H, WALK 30 MIN au cap 128° depuis
le crash, ~15 demi-pas), `walk-fixture` (`test_walk.py` : 25 demi-pas
vers l'est depuis la case 10,40) et `shore-fixture-*` (`test_shore.py` :
caps E, O, N, S, NE, ~28 demi-pas). Les rives sont toutes les cases sèches
ayant de l'eau dans leur 3 × 3. La trame est arrondie (pas le calcul flottant
exact du jeu) : ce sont des ordres de grandeur, pas une relecture du jeu.

### Blocs touchés par une requête

| Forme | Blocs par pas (max) | Pas touchant > 1 bloc (Sierra direct) | Rives touchant > 1 bloc (max sur les cartes) | Rives touchant 4 blocs |
|---|---:|---:|---:|---:|
| band7 | 2 | 29,9 % | 30,5 % | 0 |
| band14 | 2 | 13,0 % | 18,1 % | 0 |
| band21 | 2 | 8,5 % | 13,9 % | 0 |
| tile16 | 4 | 23,2 % | 25,0 % | 1,8 % (Sierra) |
| tile32 | 4 | 14,7 % | 17,7 % | 0,6 % |
| tile32×24 | 4 | 15,3 % | 16,5 % | 0,1 % |

Une collecte près d'une rive touche donc au plus 2 bandes ou 4 tuiles ;
un cache d'au moins 2 bandes ou 4 tuiles garantit qu'un pas ou une collecte
ne décode jamais deux fois le même bloc.

### Décodages sur un itinéraire complet (cache LRU de N blocs décodés)

Sierra ; puis maximum sur les neuf cartes générées et les rivières denses.

| Forme | Itinéraire | Demi-pas | Blocs distincts | N = 1 | N = 2 | N = 3 | N = 4 |
|---|---|---:|---:|---:|---:|---:|---:|
| band7 | direct | 177 | 8 | 100 | 8 | 8 | 8 |
| | meander | 282 | 9 | 154 | 18 | 11 | 9 |
| | max générées (direct / meander) | ≤ 180 / ≤ 306 | ≤ 12 / ≤ 14 | 105 / 209 | 13 / 27 | 13 / 18 | 13 / 14 |
| tile16 | direct | 177 | 15 | 159 | 22 | 19 | 16 |
| | meander | 282 | 17 | 223 | 29 | 27 | 24 |
| | max générées (direct / meander) | | ≤ 16 / ≤ 21 | 187 / 376 | 48 / 64 | 43 / 55 | 21 / 24 |
| tile32×24 | direct | 177 | 9 | 95 | 9 | 9 | 9 |
| | meander | 282 | 10 | 131 | 12 | 11 | 11 |
| | max générées (direct / meander) | | ≤ 10 / ≤ 11 | 115 / 167 | 21 / 26 | 21 / 21 | 12 / 13 |

Avec un seul bloc en cache (le schéma actuel), une trajectoire qui longe une
frontière fait osciller le cache à presque chaque pas. Avec 4 tuiles, le
nombre de décodages reste à 1,0–1,3 fois le nombre de blocs distincts.

### Coût actuel, pour comparaison

`NEOWILD.GEO` est lue par MLI dans la fenêtre `$5800`, partagée avec TRAVEL :
`native_*_travel` recharge le module 12 juste après chaque requête, donc
**au moins une lecture disque de 2 Ko par pas** (≈ 410 000 cycles à
200 c/o mesurés, soit ≥ 0,4 s plus le positionnement). Sur le trajet direct
Sierra : ≥ 177 lectures, ≥ 70 s de disque. Avec un atlas résident tile16 +
`coarse` + 4 blocs : 16 décodages × ≤ 33 ms ≈ 0,5 s, aucune lecture disque.

## 6. Conception recommandée

1. **Atlas `coarse`, tuiles 16 × 16 (154 blocs), résident en RAM
   auxiliaire** : 5,2–6,7 Ko sur les cartes réalistes (Sierra 6 379 octets,
   index compris). Le prédicteur réutilise la grille 112 × 84 déjà
   résidente (constante pendant la partie), ce qui conserve les 224 × 168
   positions, les rivières/lacs et les cases impaires exactement (tests de
   round-trip sur toutes les cartes).
2. **Cache de 4 tuiles décodées (1 152 octets) en carte langage
   auxiliaire**, étiquettes et LRU en 8 octets. 4 = nombre maximal de
   tuiles qu'un pas ou une collecte touche : aucun décodage répété dans une
   même commande. Requête : n° de tuile (x/16, y/16 → table de 14 × 11),
   recherche d'étiquette, décalage (y mod 16) × 16 + x mod 16, puis lecture
   par un court tronçon `SEI`/`ALTZP`/banque LC/`lda abs,x`/retour ROM
   (adressage absolu indexé : la page zéro auxiliaire ne sert pas de
   pointeur), ~110 cycles estimés contre ~45 aujourd'hui ; ≤ 11 requêtes
   par pas, négligeable.
3. **Décodeur (~360 octets estimés) en carte langage auxiliaire**, exécuté
   avec `ALTZP` actif : il lit l'atlas et écrit la tuile dans la même
   carte, utilise librement la page zéro auxiliaire (jamais utilisée), lit
   la grille grossière en RAM principale (`RAMRD` inactif).
4. **Coût par changement de bloc** : ≤ 33 ms (réalistes), ≤ 42 ms (relief
   bruité) estimés ; **changements attendus** : 16–24 décodages sur un
   trajet crash → rangers (Sierra 16 direct, 24 en errance ; ≤ 21/24 sur
   les cartes générées), soit < 1 s de décodage pour tout le voyage, réparti
   à ≤ 4 décodages (≤ 0,17 s) dans le pire pas.
5. **Zéro lecture disque en partie** : l'atlas est chargé avec
   `NEOWILD.DAT` (un enregistrement de plus) ; `geo_load`, le chemin MLI de
   `NEOWILD.GEO` et l'usage de la fenêtre `$5800` par la géographie
   disparaissent.
6. **Garde-fou** : `build_disk.py` refuse une carte dont l'atlas dépasse le
   budget (§7) ; `mkmap` doit exporter sa grille fine (aujourd'hui calculée
   puis réduite).

Variante : tile32×24 + 4 blocs (3 456 octets de cache) fait 9–13 décodages
de ≤ 95 ms par trajet ; même temps total, 2,3 Ko de RAM de plus. Le band7
actuel demanderait 3,5 Ko de cache pour 2 bandes et décode 2 à 3 fois plus
lentement par changement.

## 7. Budget mémoire et réponse : est-ce que ça tient en 128 Ko ?

Libre d'après `docs/MEMORY.md` (après les lots 1–2, page DHGR réservée en
`$2000-$3FFF` dans les deux banques) : **9 725 octets en RAM auxiliaire**
(369 en `$0800-$BFFF`, 5 260 en carte langage banque 2, 4 096 en banque 1) ;
**~1,4 Ko en RAM principale** (938 + 294 + 173 + 37), déjà convoités par le
code DHGR qui ne peut pas s'exécuter en RAM auxiliaire.

| Poste (tile16, `coarse`, N = 4) | Sierra | Générées réalistes | Rivières denses | Relief bruité |
|---|---:|---:|---:|---:|
| Atlas + index | 6 379 | 5 230–6 670 | 8 484 | 11 072 |
| Cache 4 × 288 + étiquettes | 1 160 | 1 160 | 1 160 | 1 160 |
| Décodeur (estimé) | 360 | 360 | 360 | 360 |
| **Total RAM auxiliaire** | **7 899** | **6 750–8 190** | **10 004** | **12 592** |
| Reste sur 9 725 | 1 826 | 1 535–2 975 | −279 | −2 867 |

**Réponse honnête : non, pas avec le plan mémoire actuel et la page DHGR.**

- Seule, la géographie tient dans les 9,7 Ko auxiliaires libres pour Sierra
  et les neuf cartes générées mesurées (6,8–8,2 Ko), mais pas pour des
  rivières denses ni un relief bruité, et elle ne laisse que 1,5–3,0 Ko.
- Or les sprites DHGR (~12 Ko bruts, `docs/MEMORY.md` §6) ne tiennent déjà
  pas dans ces 9,7 Ko. Géographie + sprites demandent ~19–20 Ko pour 9,7 Ko
  disponibles.
- Cela ne devient possible que si le lot 4 libère les 8 192 octets de TOPO
  (génération en RAM) **et** si les sprites DHGR se compressent sous
  ~9,7 Ko (17 917 libres − 8 190 de géographie au pire réaliste) : condition
  non mesurée. Et seulement avec le garde-fou de taille à la génération.

Options mesurées si le budget ne suffit pas :

| Option | Coût mémoire | Coût en temps | Conséquences |
|---|---|---|---|
| **Extension RAM** (RamWorks IIe via `$C073` ; carte mémoire IIc à registres `$C0C0+`) | 42 336 o bruts hors des 128 Ko ; ~200 o de pilotes | 0 décodage ; +20–30 c par requête | Matériel exigé ; une machine 128 Ko de base garde besoin d'un repli : ne peut pas être la seule voie |
| **Chargements exceptionnels aux bornes de voyage** (atlas sur disque, ~6–9 Ko = 12–18 blocs sur les 132 libres ; tuiles de la trame prévue lues au début de chaque WALK/SWIM) | cache 1,2 Ko seulement | 15–21 lectures par trajet (tuiles distinctes), ~0,1–0,25 s chacune (latence Disk II ~0,1 s + 200 c/o × ~40 o) : 2–5 s par trajet, au début des commandes | Contraire au « zéro lecture disque pendant le jeu courant » du lot 6 : exception à documenter et à instrumenter |
| **Résolution réduite** : plans eau/lac et bois fins exacts (plages), relief interpolé depuis la grille 112 × 84 | 1,0–1,7 Ko réalistes, 3,5 Ko rivières denses (ou listes de plages par ligne, accès direct sans cache) | ~ requête actuelle | Rivières, lacs, cases impaires d'eau et bois exacts ; relief exact sur 80–84 % des cases, ±1 sur ≥ 98 %, écart max 3–5 niveaux : `test_geography.py` (hauteurs exactes) échoue, la pente de marche et le 3 × 3 de la faune peuvent différer |
| Statu quo (banques de 2 Ko lues à la demande) | 0 o | ≥ 1 lecture de 2 Ko par pas (≥ 70 s sur le trajet direct Sierra) | Disques de comparaison seulement ; incompatible avec le lot 6 |

Recommandation : implémenter l'atlas `coarse` en tuiles 16 × 16 avec
4 tuiles en cache, conditionné à la libération de TOPO (lot 4) ; si les
sprites DHGR compressés dépassent ~9,7 Ko, prendre la résolution réduite
(plans fins exacts + relief interpolé, ~1–2 Ko) comme repli de base et
réserver la géographie exacte aux machines avec extension. Ne pas retenir
les chargements exceptionnels sans décision explicite sur le lot 6.

## 8. Limites et suites

- Coûts de décodage des codecs à bits **estimés** : écrire le décodeur
  `coarse` et le mesurer (`a2test` `pcprof`) avant de figer la forme.
- La trame des itinéraires est un modèle (arrondi, 3 × 3 de la faune à
  chaque pas) ; valider par le comptage réel des décodages et des appels
  MLI sur un trajet complet (validation du lot 5).
- Le prédicteur `coarse` exige que la grille 112 × 84 résidente reste
  identique à `coarse_grid(géographie fine)` : vrai aujourd'hui pour Sierra
  (vérifié) et par construction pour `mkmap`.
- `pack_boot.compress` est très lent sur des données uniformes (70 s pour
  une carte plate) : temps d'outil seulement.

## Reproduction

```
python3 tools/geo_atlas.py --jobs 8     # build/geo/report.{json,md}, ~2 min
python3 tools/geo_atlas.py --quick      # deux formes, une carte générée
python3 tests/test_geo_atlas.py         # round-trips, tailles figées, ~8 s
```

Entrées locales : `build/files/TOPO.B` (`make extract`) et
`build/re_geography/{heights,types}.bin` (`tools/re_geography_probe.py`) ;
sans elles, seules les cartes générées et synthétiques sont mesurées.
