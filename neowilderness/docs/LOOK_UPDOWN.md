# Neowilderness — plan : LOOK UP / LOOK DOWN (trois angles)

Demande du 13 octobre 2026 : regarder vers le haut et vers le bas, sur
trois angles au plus. L'original les a déjà : `LOOK U`, `LOOK D` et
`LOOK F` (noms 149, 150 et 156 du parseur, [parser.md](logic/parser.md)
§ 5 et verbe 16). Ce plan décrit ce que fait l'original, ce que le port
doit faire en DHGR, où le code peut vivre et comment le tester. Rien n'est
implémenté ; les tailles sont des estimations à confirmer sur
`build/wild.map`.

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
