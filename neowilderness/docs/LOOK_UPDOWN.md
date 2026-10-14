# Neowilderness — plan : LOOK UP / LOOK DOWN (trois angles)

Demande du 13 octobre 2026 : regarder vers le haut et vers le bas, sur
trois angles au plus. L'original les a déjà : `LOOK U`, `LOOK D` et
`LOOK F` (noms 149, 150 et 156 du parseur, [parser.md](logic/parser.md)
§ 5 et verbe 16). Ce plan décrit ce que fait l'original, ce que le port
doit faire en DHGR, où le code peut vivre et comment le tester. Les
sections 1 et 2 sont le plan du 13 octobre (estimations) ; la réalisation
du 14 octobre, ses sondes et ses écarts au plan sont au § 3 (vers le bas,
le décalage mesuré est de 96 lignes, pas 64).

## 1. Ce que fait l'original (sondé le 13 octobre 2026)

Sondes sur `build/SIERRA.woz` + `build/JOURNEY.dsk` dans a2shot (première
vue du crash, cap 128), captures et vidages de RAM comparés, désassemblage
de `build/files/SURV3D.CODE.B` (chargé en `$0800`).

### 1.1 État : un octet, trois valeurs

L'inclinaison est l'octet de page zéro **`$E7`** : 0 à niveau, `$01`
après `LOOK U`, `$FF` après `LOOK D`. C'est la seule variable de jeu qui
change (vidage `$0000-$BFFF` hors page HGR : 33 octets de différence,
tous dans la page zéro du parseur, `$0300` et la pile) ; **l'horloge
n'avance pas** (le cœur `$5000` n'est pas appelé, parser.md § 7).

Routine `$0FA9` (après `$0F21`, réorientation de la vue) :

| Commande | Effet sur `$E7` | Détail |
|---|---|---|
| `LOOK U` (nom `$95`) | `$E7 = 1` | absolu ; si déjà 1, rien |
| `LOOK D` (nom `$96`) | `$E7 = $FF` | absolu ; si déjà −1, rien |
| `LOOK F` / `AHEAD` / `FORWARD` (nom `$9C`) | `$E7 = 0` | retour à niveau |
| `PAN U` / `SCAN U` (verbe `$24`) | `$E7 += 1`, borné à 1 | relatif |
| `PAN D` | `$E7 −= 1`, borné à −1 | relatif |
| `PAN F` | rien | `$0FD7` : `BEQ` vers le `RTS` |

Il n'y a donc que **trois angles** : haut, niveau, bas. Un changement
redessine la vue (`$109E`) ; une valeur inchangée ne redessine rien
(`CPX $E7 / BEQ rts`).

Refus (`$0FDF`) : une inclinaison **négative** est refusée par le message
court 64 (`$0EB4` avec X = `$40`) quand le bit 7 de `$0D80` est levé.
`$0D80` est le drapeau du premier sprite de la vue (`$1C57`) ; **à
confirmer** par sonde (texte du message 64, situations : dans l'arbre,
dans la cabane, animal au contact, nage).

### 1.2 Rendu : un décalage vertical, asymétrique

Le moteur projette chaque échantillon à la ligne 95 − q·96/256 puis
convertit en indice de table i = 191 − ligne (i = 32 ↔ ligne 159, i = 191
↔ ligne 0). L'inclinaison s'applique **après** la projection, sur l'indice
(`$1A7A`) :

| `$E7` | Terrain (`$1A7A`) | Lignes écran | Horizon |
|---|---|---|---|
| 0 | inchangé, borné à i ≤ 191 et i ≥ 32 | 0–159 | ligne 95 |
| +1 (haut) | i − 96 ; i < 32 ou retenue → échantillon caché ; remplissage borné à i ≥ 32 (`$1B7C`) | tout descend de **96 lignes** | ligne 191, hors écran |
| −1 (bas) | i + 64 ; i ≥ 191 → cas de bord haut (`$1B6D`) ; borné à 191 (`$1B50`) | tout monte de **64 lignes** | ligne 31 |

Mesure sur les captures : sommet de la montagne ligne 42 → 135 (haut),
épave lignes 125–160 → 65–145 (bas). Les écarts (93–96 et ≈ 60–64) sont
compatibles avec 96 et 64 ; l'asymétrie est dans le code, pas un artefact.

Règles annexes lues dans SURV3D, toutes conditionnées par `$E7` :

- `$1E3C` : les **arbres** (`$1E87,X`) ne sont pas dessinés quand
  `$E7 = 1` ; les captures « haut » ne montrent que le sommet neigeux.
- `$1C52` : `$E7 = 1` saute le placement des **sprites** (`$0D80`,
  `$0D84`) ; pas d'épave en regardant en l'air.
- `$1C82`/`$1C88`, `$1D65`, `$193A` : en regardant en bas, le sprite
  proche est traité à part (`$DC = 8` → ancre `$28` ; borne de dessin
  `$E9` = `$10` au lieu de `$DF`) : l'épave apparaît **entière** (capture
  `o5`). Règle exacte à relever sur les autres sprites (ours au contact,
  cabane) par sonde avant de la porter.
- `$1BC6` : base verticale `$F8` = 96 à niveau, 0 en haut, 192 en bas :
  borne de remplissage du ciel/sol, cohérente avec les décalages.
- Le soleil suit le même décalage (ligne 52 → 149 en haut ; caché en bas).

### 1.3 Persistance

L'inclinaison **persiste** : `LOOK R` tourne la vue inclinée (capture
`p_up_r`), `VIEW` la redessine inclinée, `STATUS` puis retour la
conserve (`$E7` n'est pas touché). **À confirmer** : WALK/SWIM/REST (le
cœur `$5000` remet-il `$E7` à 0 ?) ; sonde : `LOOK U`, `WALK 1`, capture.

## 2. Ce que doit faire le port

Même contrat de jeu que l'original (direction 1 du TODO : fidélité),
rendu DHGR du port (direction 2). À niveau, **rien ne change** :
`test_reference_state.py`, `test_scene_render.py`, `test_dhgr_ref.py`
restent au bit près.

### 2.1 État et commandes

- `tilt` : un octet signé (−1, 0, 1) dans l'état résident (GZP ou un
  octet d'état de TEXT ; le réglage de page zéro est à vérifier : `$E7`
  est dans GZP `$D0-$ED`, déjà attribué).
- Verbes et noms : `LOOK`/`PAN` + `U`, `UP`, `D`, `DOWN` (absolu avec
  LOOK, relatif avec PAN), `F`/`AHEAD`/`FORWARD` = niveau (déjà dans la
  liste LOOK du menu : `AHEAD`). Vérifier dans `src/game.s`/VOCAB si `U`,
  `UP`, `D` existent (`DOWN` existe pour CLIMB) ; VOCAB est à 2 047/2 048
  octets : **chaque mot nouveau dépend de la conquête mémoire** (ou de la
  réutilisation d'un mot existant).
- Refus de l'original (message 64 sous `$0D80` bit 7) : porter la
  condition une fois sondée ; sinon ne pas refuser.
- Aucun coût en temps de jeu, aucun tirage, aucun état de simulation
  touché : `tilt` n'entre pas dans la comparaison d'état.
- Persistance identique à l'original (§ 1.3) ; WALK selon la sonde.

### 2.2 Grille des quatre lignes du bas et flèches

- Liste LOOK de la grille (`src/menu.s`, `list_look`) : ajouter `UP` et
  `DOWN` (+9 octets dans MENUSWAP, 62 libres). `AHEAD` sert de retour à
  niveau.
- Demande utilisateur du 13 octobre 2026 : **flèche haut = STATUS,
  flèche bas = grille des choix** (aujourd'hui STATUS est sur la flèche
  bas et la grille sur TAB, [MENUS.md](MENUS.md) § 4). Changement dans
  `prompt_key`/`idle` de `src/menu.s` (quelques octets, MENUCODE 182
  libres) et dans `tests/test_menu_bar.py` ; documenter dans MENUS.md.
  Les flèches ne servent donc pas à incliner la vue : LOOK UP/DOWN
  passent par la grille ou la commande tapée.

### 2.3 Rendu DHGR incliné

Principe : un **décalage vertical `dv`** (+96 en haut, −64 en bas, 0 à
niveau) appliqué à toute ligne projetée, avec les bornes de la vue
logique 0..159 (rangées physiques 16..159, cache 160..175 pour les lignes
logiques 0..15). Rien ne doit jamais atteindre les rangées 176..191
(MENUSWAP y dort, [MEMORY.md](MEMORY.md) § 11) : toute ligne ≥ 160 est
**cachée**, pas bornée.

| Sous-système | Aujourd'hui | Avec `dv` | Où | Coût estimé |
|---|---|---|---|---|
| Terrain (`src/wild.s` `render_*`) | `row_p0[q]` (dz ≥ 0), `row_n0[q]` (dz < 0), −48/+48 pour q ≥ 256, ligne 0 pour q ≥ 512, `cpx #86` cache les lignes > 159, `cmp top` pour l'occlusion | tables **réécrites** au changement d'angle : `row_p0' = row_p0 + dv` borné à 0 (bas) et marqué caché au-delà de 159, `row_n0` reconstruit comme `project_init` à partir de la table décalée ; la constante `#0` de `render_prow0` devient `max(0, dv)` ; `sbc #48`/`adc #48` gardent leurs bornes (vers 0 : `bcc → 0` ; vers 160 : caché). Le chemin chaud ne gagne aucune instruction : seul le code des bornes change | CODE `$6000` (2 octets libres) | +10 à +16 octets dans `wild.s`, +40 pour la réécriture des tables dans un module (PROJECT, 694 libres) ; **dépend de la conquête mémoire** pour `wild.s` |
| Table `row_p0` | constante en RAM | devient une table de travail (copie décalée) : la version à niveau se régénère par `dv = 0` depuis la copie courante (réversible : +dv puis −dv) ou depuis une base de 256 octets | WILDLO / LOWCACHE | 0 si réversible (un `tilt_old`), sinon +256 |
| Sprites (`src/project.s`) | ancre `95 ± q` | ancre `95 + dv ± q` ; en haut, **pas de sprites** (règle `$1C52`) ; en bas, règle du sprite proche à sonder (§ 1.2) ; découpe existante aux lignes 0 et 159 conservée | PROJECT (694 libres) | +12 |
| Arbres (`src/forest.s`) | `#HORIZON` | `horizon + dv` ; en haut, pas d'arbres (règle `$1E3C`) | FORESTCODE (4 libres) | +6, **dépend de la conquête mémoire** ou déplacer un bout de forest.s |
| Ciel : dégradé par zones (`src/dhgr.s` `sky_zone_end` 32, 48, 72, 84, 160) | fixe | zones décalées de `dv`, bornées 0..160 ; en haut, le zénith occupe 0..128 puis la lueur d'horizon 128..159 ; en bas, seule la lueur reste (0..20) sous les reliefs | WILDGAME (6 libres) → la table vit déjà en GDATA ; sa réécriture dans le module | +5 (base) +20 code |
| Soleil et Lune (`src/sky.s`, SIM) | `#HORIZON`, `#HORIZON+1` | `sky_y + dv`, visible si 16 ≤ ligne ≤ 159 ; en haut, un astre à 60° de hauteur devient visible (ligne 12 + 96 = 108) : **le port montre le soleil haut**, l'original aussi (ligne 149 dans `o1`) | SIM (11 libres) | +8, **dépend de la conquête mémoire** |
| Étoiles (`src/stars.s`, fenêtre SIM) | `adc #95`, bornes 16..95, Lune 16..95 | `95 + dv − h`, borne haute 16 ; en haut, les étoiles jusqu'à 45° + 96 lignes : la projection comprimée au-delà de 45° ([STARS.md](STARS.md) § 14) reste ; `stars_stale = 1` au changement d'angle ; en bas, aucune étoile (toutes ≥ 160 ou sous le relief) | module des étoiles (1 774 libres au-dessus de son BSS) | +10 |
| Nuit (terrain noir sous l'horizon) | lignes 96..159 | lignes `96 + dv`..159 ; en haut, nuit = ciel sombre sur 0..159 moins les crêtes | `src/dhgr.s`/`wild.s` | 0 à +4 |
| Rotations (`LOOK L/R`, PAN) | défilement horizontal par bandes de 8 | inchangé : `dv` est global, les 70 colonnes recalculées le suivent ; vérifier `scene_trim` et l'instantané TOPO (restaure l'image telle quelle) | — | 0 |
| HUD, boussole, texte 80 colonnes | rangées 0..15 et 20..23 | inchangés | — | 0 |

Occlusion : `top` et le remplissage colonne par colonne restent dans le
repère logique décalé ; les échantillons cachés en haut (ligne > 159)
n'écrivent rien, et la colonne se remplit jusqu'au dernier visible comme
aujourd'hui. En bas, les échantillons bornés à la ligne 0 remplissent la
colonne depuis le haut comme le fait déjà `render_prow0`.

Pas de raccourci par défilement vertical : l'original redessine ; le
coût d'un `LOOK U` est celui d'un `LOOK R` complet (≈ 1,9 s mesurés, moins
en haut : presque tout est ciel). Un défilement de 96 lignes avec
re-rendu partiel n'est exact que si aucune colonne n'a été bornée ; à
étudier seulement si la mesure dépasse 2 s.

### 2.4 Oracle et tests

1. `tools/view_ref.py` (et `dhgr_ref.py`, `forest_ref.py`) reçoivent
   `tilt` : décalage `dv`, bornes, arbres et sprites omis en haut, règle
   du sprite proche en bas ; **d'abord validé contre l'original** sur
   la première vue (captures `o0`, `o1`, `o5` : lignes de crête, ligne du
   soleil, position de l'épave ; comparaison HGR possible avec
   `tools/view3d.py` qui reproduit déjà la vue à niveau).
2. `tests/test_scene_render.py`, `test_sprites.py`, `test_dhgr_ref.py` :
   cinq cartes × trois angles, 6502 = oracle au bit près ; une carte avec
   un sommet borné en haut (q ≥ 512) et une falaise en bas.
3. `tests/test_sky.py` : soleil à 60° visible en haut, caché à niveau ;
   Lune de même ; `stars.mk` : banc à trois angles, aucune étoile ≥ 160.
4. `tests/test_adventure.py --original` (ADVENTURE_TESTS.md) : scénario
   `LOOK U`, `LOOK R`, `VIEW`, `LOOK D`, `LOOK F`, `PAN U` ×2, `PAN D`
   ×3 : `tilt` du port = `$E7` de l'original à chaque pas, horloge
   inchangée, écran d'état identique.
5. `tests/test_menu_bar.py` : entrées UP/DOWN de la liste LOOK, flèche
   haut = STATUS, flèche bas = grille.
6. `tests/test_reference_state.py`, `test_resident.py` : inchangés
   (aucune lecture disque, état identique à niveau).
7. Garde-fou : après `LOOK U` et `LOOK D` sur les six régions, rangées
   176..191 des deux banques identiques avant/après (MENUSWAP intact).

### 2.5 Lots

| Lot | Contenu | Pré-requis |
|---|---|---|
| A. Sondes | message 64 et `$0D80`, WALK après LOOK U, règle du sprite proche en bas, deux autres vues (cabane, animal) ; oracle Python validé contre l'original | aucun |
| B. Moteur | `dv` dans terrain, sprites, arbres, zones du ciel, astres, étoiles ; tests 2, 3, 7 | ≈ 30 octets dans `wild.s`, `forest.s` et SIM : **conquête mémoire** (direction 3) |
| C. Commandes | `tilt`, LOOK/PAN U/D/F, refus, liste LOOK de la grille, flèches haut/bas ; tests 4, 5 ; MENUS.md, README, CHANGELOG | VOCAB : place pour `U`/`UP`/`D` |

Hors plan : des angles intermédiaires (16 ou 48 lignes) seraient une
extension ; l'original n'en a pas et la demande se limite à trois angles.

## 3. Réalisation (14 octobre 2026)

Base : `main` `d64afbb` (reconquête mémoire du 14 octobre, MAP plein
écran). Les mesures mémoire viennent de `build/wild.map` et de
`make inspect`, avant et après. Le plan ci-dessus est conservé tel quel ;
cette section dit ce qui a été fait et où il a été corrigé.

### 3.1 Sondes de l'original (lot A)

`tools/re_tilt_probe.py` (rejouable, résultats dans `build/re_tilt/`) et
des sondes ponctuelles (`test_adventure.Driver` rejouant la rencontre
native `sierra_encounter.json` jusqu'à l'ours, puis jusqu'au crotale)
donnent :

| Question du plan | Réponse sondée |
|---|---|
| `$E7` par commande | conforme au § 1.1 : LOOK U/D/F absolus, PAN U/D relatifs et bornés, PAN F sans effet, SCAN = PAN ; horloge inchangée à chaque pas |
| Persistance | gardée par LOOK L/R, LOOK N, LOOK AZ, VIEW, STATUS, REST, USE COMPASS, DRINK ; **remise à 0 par WALK** (sondé deux fois) et par **LOOK B** (SURV3D `$1028` : `stx $E7`, puis +180°) |
| Message court 64 | `NOT NOW!` (table `$0ED8`, entrée `$40`) |
| Refus | `$0D80` = sprite de l'animal au contact (`$81` : l'ours) ; bit 7 levé → LOOK D et PAN D refusés. Le crotale (`$03`) laisse regarder en bas |
| Origine du bit 7 | Journey T0D/SE (`$5F7D`, module chargé en `$5800`) : à l'arrivée d'un animal, bit 7 pour l'espèce 1 sauf en région 3, pour l'espèce 2 en région 3, pour l'espèce 3 en région 1, pour aucune à partir de la région 5. Le même code **règle `$E7`** : −1 (vue vers le bas) pour un animal « au sol », 0 pour un animal debout ; à l'arrivée sur un site (`$0D84`), 0 ou −1 selon le bit 7 du site |
| Cabane | `$0FA9` n'est appelé que hors abri (`$0D5E` = 0) : dans la cabane l'angle ne change pas |
| Vue vers le bas | **96 lignes, pas 64** : relief de la première vue lignes 101, 98 → 6, 3 (−95/−96). Le terrain applique `dz ± n` à la pente (`$1842`), symétrique ; seul le dessin des sprites (`$1B50`) ajoute 64 à l'indice |
| Sprite proche, vers le bas | l'épave monte de 49 lignes (127..158 → 78..137, colonnes 100-112) et apparaît entière ; un sprite sans bit 7 (crotale) n'est dessiné **que** vers le bas (`$1C82`) ; en l'air, aucun sprite (`$1C52`) |
| Soleil en l'air | lignes 50..57 → 146..153 (+96) ; sommet 43 → 138 |

Validation de l'oracle (`view_ref.columns(tilt)`) sur la carte de
comparaison (TOPO original, `test_adventure.original_map`), première vue :
écart moyen original − oracle de la ligne du premier pixel non-ciel
= −1,2 ligne à niveau (140 colonnes), +0,2 en l'air (30 colonnes où les
deux vues ont du relief), +0,3 vers le bas (18 colonnes). Avec 64 lignes
vers le bas, l'écart serait de 32 lignes.

### 3.2 Conception retenue (lots B et C)

**Le décalage est une pente.** 96 lignes = 3 × 512 / 16 : regarder en l'air
revient à projeter la pente `q − 512`, vers le bas `q + 512`. Le moteur
garde ses tables `row_p0`/`row_n0` et sa boucle de rayons ; l'occlusion
(`thr`, `tinc`) ne dépend pas de l'angle. `render_drawchk` porte une
instruction de trois octets : `BIT tilt_row` à niveau (4 cycles par
échantillon visible), `JSR tilt_row` quand la vue est inclinée
(`tilt_apply` la réécrit). `tilt_row` recalcule la ligne depuis `tinc` :
`row_p0[lo] − 48 × hi` bornée à 0, ou `row_n0[|lo|] + 48 × |hi|` cachée
au-delà de 159. Les deux sauts « sous la vue » de `render_nbig` passent
désormais par `render_drawchk` (`render_nhide`). Aucune table réécrite,
aucun octet de plus en page `$1000`.

| Sous-système | Réalisation |
|---|---|
| État | `tilt` en page zéro de jeu (`$EE`, GZP, après `forest_crown_end` déplacé dans `game.s` pour garder son adresse `$ED` : la référence compare sa valeur initiale), 0 / 1 / `$FF`, mis à 0 au démarrage (le chargeur laisse en page zéro les valeurs d'Applesoft) ; `tilt_shown` en WILDLO : `stars_dhgr_frame` appelle `tilt_apply` au premier rendu qui suit un changement |
| Constantes | `dhgr.s tilt_frame` (partagé avec le banc des étoiles) : `tdv` (96 × tilt modulo 256), `tilt2`, `tskylim`, `thoriz` (95 + dv sur 16 bits) et les quatre fins de zones du ciel décalées et bornées à 0..160 (en l'air 128, 144, 160, 160 ; vers le bas 0 : tout le ciel est la lueur) |
| Sprites | en l'air, `draw_dark` = 1 pour la trame : ni sprite ni panneau ; vers le bas, un panneau lointain suit son relief (`anchor − h + tdv` ; une ligne négative est transparente, ce qui corrige au passage un repli possible à niveau) ; les sprites locaux (épave, cabane, animal au contact) gardent leurs lignes : ce sont déjà celles de l'épave de l'original vers le bas (haut en 67 contre 69) |
| Plafond des panneaux | `scene_height_bound` retranche 96 vers le bas ; la commande invalide le cache de scène |
| Arbres | en l'air, `forest_reset` coupe la sonde ; vers le bas, `forest_project_base` part de `thoriz` (−1) sur 16 bits signés |
| Soleil et Lune | `sky_position_raw` (l'ancien calcul) accepte un astre jusqu'à 96 lignes au-dessus de la vue et rend sa ligne signée à niveau (−96..95, `$80` caché) ; `sky_position_core` la range avec le relèvement dans `sky_hy`/`sky_hb` (WILDLO), puis rend à `sky_y`/`sky_bearing` la règle de la référence (255 et l'ancien relèvement au-dessus de la vue : état comparé par `test_reference_state.py`, masque de Lune des étoiles) ; `sky_column` dessine en `sky_hy + dv` sous `tskylim` (96 à niveau, 160 en l'air, jamais vers le bas) |
| Étoiles | liste inchangée, pas de recalcul ; `stars_column` ajoute `tdv` à la ligne (une ligne passée sous 0 devient ≥ 160, donc cachée) et borne la fin de la tache à 160 ; `stars_frame` passe en WILDLO pour libérer la place en SKYRES |
| Nuit | rien de spécifique : terrain noir et ciel bleu foncé suivent les mêmes lignes |
| Rotations | inchangées : le défilement par bandes déplace l'image inclinée, les colonnes neuves sont dessinées au même angle |
| Commandes | `tree.s module_tree_look` : U/UP, D/DOWN, F/AHEAD/FORWARD, LOOK et PAN/SCAN (verbe 36) ; refus `NOT NOW.` par `look_standing` (table par région et espèce de T0D/SE) ; LOOK B et WALK/SWIM (`do_walk`) remettent 0 |
| Grille | `list_look` : `UP`, `DOWN` après `AHEAD` (+8 octets MENUSWAP) ; ligne tapée : flèche haut = STATUS, flèche bas = grille, TAB alias (deux branches échangées, 0 octet) |

### 3.3 Octets

| Zone | Avant | Après | Libre après |
|---|---:|---:|---:|
| GZP (page zéro de jeu) | `$D0-$ED` | `$D0-$EE` (+1, `tilt`) | `$EF` |
| TEXT `$0A00-$0FFF` | 1 463 | 1 475 (+12 : `m_notnow`, `sky_column`) | 61 |
| WILDLO (LOWCODE + LOWTEXT) | 752 + 1 114 | 1 087 + 1 150 (+371) | 1 347 (`$1ABD-$1FFF`) |
| WILDGAME (GCODE) | fin `$576D` | fin `$5778` (+11 : arbres, WALK) | 7 |
| WILDERNESS `$6000` (CODE) | fin `$6EC1` | fin `$6ECE` (+13 : `render_nhide`, panneaux) | 305 |
| MENUSWAP | 1 474 | 1 482 (+8) | 54 |
| SKYRES (carte langage) | 482 | 469 (−13) | 19 |
| Module PROJECT | 1 354 | 1 365 (+11) | 683 |
| Module ADVENTURE | 1 981 | 1 985 (+4) | 63 |
| SIM (`wildsim.bin`, fenêtre `$9600-$B5FF`) | 7 619 | 7 670 (+51 : `sky_position_core`) | 522 |
| VOCAB, SCREENS, TRAVEL, MENUCODE, FORESTCODE | — | inchangés | — |

Volume : 28 → 27 blocs libres (NEOWILD.DAT +406 octets compressés). Aucune
lecture disque pendant la partie. VOCAB n'a pas bougé : U, UP, D, DOWN,
F, AHEAD, FORWARD, PAN et SCAN existaient. La ligne d'aide (HELP) n'a pas
été ajoutée : SCREENS n'a qu'un octet libre.

### 3.4 Temps

Vue complète à niveau, cycles mesurés par `pcprof` (cartes de
`test_scene_render.py`, avant → après) :

| Carte | Sans sprite | Avec sprite |
|---|---|---|
| générée (Sierra) | 4 164 184 → 4 187 962 (+0,57 %) | 5 825 033 → 5 849 911 (+0,43 %) |
| plate | 4 802 246 → 4 845 658 (+0,90 %) | 4 882 852 → 4 906 949 (+0,49 %) |
| falaises | 3 181 553 → 3 197 614 (+0,50 %) | 4 153 900 → 4 164 386 (+0,25 %) |
| bruit | 2 584 905 → 2 591 533 (+0,26 %) | 3 791 238 → 3 798 470 (+0,19 %) |
| héritée plate | 4 802 246 → 4 845 658 (+0,90 %) | 6 605 983 → 6 650 815 (+0,68 %) |

Au plus +0,9 %, sous le seuil de 2 %. Vue inclinée, départ Sierra sans
sprite : 4,19 M cycles à niveau, **3,71 M en l'air** (−11 %), **2,76 M vers
le bas** (−34 %) : le ciel ou le sol proche arrêtent les rayons plus tôt ;
aucun raccourci par défilement vertical n'est utile. Banc des étoiles :
environ +4 cycles par entrée examinée.

### 3.5 Tests

- `tests/test_tilt.py` (ajouté à `make test`) : 21 commandes LOOK/PAN/SCAN
  (angle = `$E7` sondé, horloge inchangée) ; refus par région et espèce ;
  cabane ; WALK ; six cartes (générée, plate, falaises, bruit, héritée,
  sommet et falaise : un sommet borné à la ligne 0 à niveau, une vallée
  sous la vue à niveau) × trois angles = `dhgr_ref.view(tilt)` au bit près,
  rangées cachées comprises ; arbres et épave en panneau lointain sur neuf
  vues avec rotations inclinées ; soleil à 68° (`sky_hy` = −24) caché à
  niveau et vers le bas, ligne 72 en l'air ; six régions : rangées 176-191
  des deux banques identiques avant et après LOOK U/D, PAN U, LOOK R ;
  cycles des trois angles.
- `make -f stars.mk test` : cinq cas inclinés (en l'air, en l'air avec
  crête, vers le bas, Croix du Sud en l'air, rotation en l'air), liste et
  banques au bit près.
- `tests/test_adventure.py --scenario look_tilt` (compris dans `--scenario
  all`, `make test-original`) : LOOK U, LOOK R, VIEW, LOOK D, LOOK F, PAN U
  ×2, PAN D ×3 : angle du port = `$E7` à chaque pas, horloge inchangée,
  0 différence sur l'état comparé. Le cap est retiré de ce scénario :
  LOOK R tourne de 90° dans l'original et de 45° dans le port (écart
  antérieur, mis au jour ici, non traité).
- `tests/test_menu_bar.py` : flèche bas et TAB ouvrent la grille, flèche
  haut affiche STATUS, LOOK UP/DOWN/AHEAD composés = tapés.
- `test_scene_render.py`, `test_dhgr_ref.py`, `test_reference_state.py` :
  inchangés et verts (vue à niveau identique au bit près).

### 3.6 Écarts au plan et à l'original

- **Vers le bas : 96 lignes** (le plan disait 64, valeur du dessin des
  sprites de l'original). Le terrain de l'original est symétrique.
- **Sprites locaux immobiles vers le bas** au lieu de −49 (épave mesurée)
  ou −64 (`$1B50`) : le port dessine déjà l'épave entière à niveau, là où
  l'original la montre vers le bas.
- **Non porté : l'inclinaison automatique** de l'original à l'arrivée d'un
  animal (vers le bas pour un animal « au sol », à niveau pour un animal
  debout) ou d'un site, ni la règle « sprite sans bit 7 visible seulement
  vers le bas » : le port garde ses rencontres à niveau, le crotale reste
  visible sans regarder en bas. Les porter changerait les vues de rencontre
  que vérifient d'autres tests (`test_fauna`, `test_sprites`) ; c'est une
  piste de fidélité pour plus tard.
- Message `NOT NOW.` : un `!` dans un message du port insère la raison de
  l'arrêt d'une marche.
- Étoiles en l'air : la projection comprimée au-delà de 45° reste ; une
  étoile proche d'une Lune visible seulement en l'air n'est pas masquée par
  son disque sombre (le masque de la liste ne vise que la Lune dessinée à
  niveau).
- LOOK AHEAD à niveau redessine la vue (comportement antérieur gardé) ;
  l'original ne fait rien.

Captures (ignorées) : `build/look_level_sierra.png`,
`build/look_up_sierra.png`, `build/look_down_sierra.png` (port) et
`build/look_*_original.png` (original, mêmes commandes).

### 3.7 Nuit sur carte plate (`tests/test_sim.py`)

« Night view: black terrain » attendait les lignes 96 à 159 noires en nuit
noire sur une carte plate ; le ciel bleu foncé descendait jusqu'à la
ligne 103. Cause : la météo de la graine (visibilité 24 demi-cases après
REST 16) limite les rayons à 11 pas (`render_weather_limit`) ; le dernier
échantillon du sol plat est en ligne 104 et le ciel remplit la colonne
jusqu'à lui. L'original remplit aussi le ciel jusqu'au dernier échantillon
visible (première vue Sierra : ciel jusqu'à la ligne 100 sur les colonnes
0 à 2, sous l'horizon) et `view_ref.columns` fait de même ; la portée
réduite par la visibilité est une extension du port (la portée `$E1` de
l'original vaut 128 au redessin). Le rendu suit donc sa règle, le test
était faux : il calcule la limite par `view_ref.columns(steps =
visibilité / 2 − 1)` (nouveau paramètre de l'oracle) et vérifie le noir à
partir de la ligne 104 et le ciel jusqu'à la ligne 103.
