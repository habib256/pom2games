# Score et hall of fame (lot 7, étape 6)

Ce document prépare l'étape 6 du lot 7 ([TODO.md](../TODO.md), boîtes « Score
16 bits », « Module `wildhof.bin` », « `NEOWILD.HOF` vide » et « Tests » ;
[SCENARIOS.md](SCENARIOS.md) § 7 et § 8).
Tout ce qui est décrit ici existe et est testé **hors du jeu** : référence
Python, module 6502 de fin de partie, fragment du chargeur, banc IIe
autonome. L'intégration a aussi été construite et jouée sur une copie
temporaire des sources (QUIT près du poste, saisie du nom, écriture, retour
au menu, BEST et écran H relus) : la section 9 donne le correctif exact
([hof_integration.diff](hof_integration.diff)).
**Intégré au jeu le 13 octobre 2026** : le correctif a été appliqué tel
quel, puis `build_disk.py`, le `Makefile` et les tests existants ont été
adaptés (section 9). Volume final : MEMORY.md § 9.1.

| Élément | Fichier | Taille |
|---|---|---:|
| Référence du score, du fichier et des écrans (l'oracle) | `tools/score_ref.py` (réexporté par `tests/score.py`) | — |
| Fichier vide | `tools/genhof.py` → `NEOWILD.HOF` | 512 octets, 1 bloc |
| Module de fin de partie `wildhof.bin` (ID 24) | `src/hof.s` (+ `src/hof_menu.s`) | 3 044 octets → `NEOWILD.END`, 7 blocs |
| Lecture/écriture du fichier et primitives texte, partagées | `src/hof_menu.s` | ≈ 1 136 octets dans le chargeur |
| `module_end` et `module_restart` (module INPUT) | `src/hof_load.inc` | + 64 octets dans INPUT |
| WOZ protégé en écriture pour les tests | `tools/po2woz.py` | — |
| Banc IIe | `src/hof_test.s`, `src/hof_test.cfg`, `src/hof_boot.s`, `hof.mk` | `../dist/NEOHOF_TEST.po` |
| Tests | `tests/test_hof_ref.py` (Python pur), `tests/test_hof.py` (a2shot `--iie`), `tests/test_hof_game.py` (jeu intégré) | `make -f hof.mk test` |

## 1. Décisions en bref

- **Progression = `DONE=` de STATUS** (`goal_pct` → `module_progress`,
  0 à 99, 100 seulement à l'arrivée), et non `module_goal_pct` que nommait
  le plan : cette dernière est l'efficacité native G de l'original, qui vaut
  100 % quand aucune heure n'est écoulée (`s_elap` = 0) ; un QUIT immédiat
  aurait marqué 1 000 points de progression.
- **Santé pondérée par la progression hors arrivée** : `santé × 5` à
  l'arrivée, `santé × 5 × progression / 100` sinon. Avec la formule du plan,
  QUIT à la première invite (100 % de santé) valait 500 points au niveau 4,
  plus que la plupart des morts après un vrai trajet. Le reste de la formule
  est celui du plan.
- **Un score nul n'est jamais classé** (« NOT IN THE TOP 5. »), même si la
  table a des places vides.
- **Ordre et arrondis** : composantes entières, total, `× (10 + niveau)`,
  puis `/ 14` ; chaque division arrondit vers le bas. `base × 20 ≤ 64 400`
  et `santé × 5 × progression ≤ 50 000` tiennent sur 16 bits.
- **Le module tourne à `$9600`** (fenêtre SIM, libre une fois le voyage
  fini), pas à `$5800` : le code qui le charge (INPUT) s'exécute en `$5800`,
  et `goal_pct` y recharge ADVENTURE puis STATUS. Il est lu **depuis le
  disque** (fichier `NEOWILD.END`) : la RAM auxiliaire n'a pas la place
  (681 octets libres avec Burma). L'entrée 24 du répertoire des modules
  reste vide (longueur 0).
- **Toutes les fins passent par le module** : `quit` (mort, arrivée après
  l'écran de fin, QUIT puis Y) saute à `module_end` au lieu de
  `module_restart`.
- **Saisie du nom sur la ligne du classement** : l'entrée est insérée avec
  un nom blanc, le curseur (espace inverse) avance dans la table.
- **Chaque voyage de scénario écrit le fichier** (compteurs de parties),
  même hors du top 5 ou après ESC ; le voyage libre n'y accède jamais.
- **Fichier illisible ou inconnu : jamais réécrit** ; le score reste à
  l'écran dans tous les cas.

## 2. Score

Entrées, lues dans l'état résident à la fin du voyage :

| Entrée | Source | Bornes |
|---|---|---|
| issue | `won` → 1 arrivée, sinon `dead` → 2 mort, sinon 3 abandon | — |
| niveau | `MAP+22` | ramené à 1–10 |
| région | `MAP+32` | hors 1–6 : non classé |
| genre | `MAP+33` (1 = voyage libre) | ≠ 0 : non classé |
| progression | `goal_pct` (STATUS `DONE=`) | ramenée à 0–100 |
| santé | `INT(H / Hmax × 100 + 0,5)` (`f_hmax`, `s_health`, comme STATUS) | ramenée à 0–100 |
| heures | `INT(s_elap)` (`AYINT`) | 32 767 au plus (exposant ≥ `$90` testé avant) |

Formule (`tools/score_ref.py`, `hof_score` dans `src/hof.s`) :

```
P = progression × 10                                  0 – 1 000
A = 1 000 si arrivée                                  0 / 1 000
H = santé × 5                     si arrivée          0 – 500
    ⌊santé × 5 × progression / 100⌋ sinon
S = max(0, 720 − heures)          si arrivée          0 – 720
base  = P + A + H + S                                 ≤ 3 220
score = ⌊base × (10 + niveau) / 14⌋                   ≤ 4 600
```

Exemples (vérifiés par `test_hof_ref.py` et, pour la plupart, par le banc) :

| Voyage | P | A | H | S | base | × | score |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sierra, arrivée, niveau 4, santé 62 %, 312 h | 1 000 | 1 000 | 310 | 408 | 2 718 | 14/14 | **2 718** |
| arrivée, niveau 10, santé 100 %, 0 h (maximum) | 1 000 | 1 000 | 500 | 720 | 3 220 | 20/14 | **4 600** |
| mort, niveau 4, progression 37 %, santé 21 % | 370 | 0 | ⌊105 × 37 / 100⌋ = 38 | 0 | 408 | 14/14 | **408** |
| abandon, niveau 4, 50 %, santé 80 % | 500 | 0 | 200 | 0 | 700 | 14/14 | **700** |
| mort, niveau 1, 5 %, santé 4 % | 50 | 0 | 1 | 0 | 51 | 11/14 | **40** |
| Burma, arrivée, niveau 7, santé 70 %, 400 h | 1 000 | 1 000 | 350 | 320 | 2 670 | 17/14 | **3 242** |
| QUIT à la première invite (100 %, 0 %) | 0 | 0 | 0 | 0 | 0 | 14/14 | **0**, non classé |
| arrivée après 900 h, santé 50 % | 1 000 | 1 000 | 250 | 0 | 2 250 | 14/14 | **2 250** |

## 3. Fichier `NEOWILD.HOF`

Un bloc de 512 octets, fichier « seedling » ProDOS (un seul bloc de
données, pas de bloc d'index), type BIN `$06`, aux `$0000`, créé vide par
`tools/genhof.py` à la construction du volume ; le jeu ne fait jamais de
CREATE. L'écriture remplace les 512 octets en place (OPEN, WRITE 512,
CLOSE) : aucun bloc n'est alloué, même sur un disque plein.

| Offset | Taille | Contenu |
|---:|---:|---|
| 0 | 1 | `'H'` (`$48`) |
| 1 | 1 | version 1 |
| 2 | 2 | voyages de scénario terminés, tous scénarios (u16, saturé à 65 535) |
| 4 | 12 | voyages terminés par scénario 1 à 6 (6 × u16, saturés) |
| 16 | 16 | réservé, 0 (conservé tel quel) |
| 32 + ((s − 1) × 5 + k) × 16 | 16 | entrée de rang k (0–4) du scénario s (1–6) |

Entrée de 16 octets :

| Offset | Taille | Contenu |
|---:|---:|---|
| 0 | 8 | nom, ASCII avec bit 7 (`$C1` = A), complété par des espaces `$A0` |
| 8 | 2 | score (u16) |
| 10 | 2 | heures (u16) |
| 12 | 1 | niveau 1–10 |
| 13 | 1 | issue : 0 entrée vide, 1 arrivée, 2 mort, 3 abandon |
| 14 | 2 | réservé, 0 |

Validité : 512 octets lus, `'H'` et version 1 ; sinon « HALL OF FAME FILE
NOT RECOGNISED. » et aucune écriture. Une entrée est vide si son issue vaut
0 ; les entrées vides sont en fin de table.

Classement : score décroissant, puis heures croissantes ; à égalité de
score et d'heures, le nouveau résultat passe **après** l'ancien. Le rang est
le premier k dont l'entrée est vide, de score inférieur, ou de même score
avec plus d'heures ; aucun (rang 5) si le score est nul ou ne bat aucune
entrée. L'insertion décale les entrées k–3 d'un rang ; la cinquième sort.

## 4. Module de fin de partie (`src/hof.s`, `wildhof.bin`, ID 24)

### Chargement et sortie

1. `quit` (WILDLO) : `WNDTOP` = 0, `overlay_load 13` (INPUT), `jmp
   module_end`.
2. `module_end` (`src/hof_load.inc`, dans INPUT) libère les pages
   `$96-$B5` du bitmap ProDOS — le jeu les protège et READ y refuse le
   tampon (erreur `$56`, mesurée au banc) ; `prodos_restore` remet le bitmap
   sauvegardé ensuite —, lit `/VOLUME/NEOWILD.END` (chemin de `geo_path`,
   suffixe remplacé) à `$9600` et y saute. Échec : `module_restart`
   directement (pas de score, retour au menu).
3. Le module finit par `lda #13 / jsr overlay_load / jmp module_restart` :
   INPUT est recopié depuis la RAM auxiliaire, puis la relance habituelle
   (restauration système, `NEOWILD.SYSTEM` relu à `$2000`).

`module_end` et `module_restart` partagent `hl_load` (chemin, OPEN, READ,
CLOSE) : `src/hof_load.inc` **remplace** l'ancien `module_restart`
d'`input.s` (160 octets) ; INPUT grandit de 64 octets seulement.

### Mémoire

| Zone | Usage |
|---|---|
| `$9600-$A1E3` | code et textes du module (3 044 octets ; SIM window, 8 Ko) |
| `$5800-$59FF` | `NEOWILD.HOF` (HOF_BUF) : la fenêtre des modules, où `goal_pct` laisse STATUS, inutile ensuite |
| `$5A00-$5A40` | chemin `/VOLUME/NEOWILD.HOF` (HOF_PATHBUF) |
| `$5A50-$5A9F` | les 80 octets du scénario avant insertion (ESC les remet) |
| `$BA00-$BDFF` | `io_buffer`, pour chaque OPEN |
| `$D0-$D3` | `gp1`, `gp2` (HOF_ZP) : pointeurs écran et entrée |
| `$0400-$07FF` | page texte 1 (principale), 40 colonnes |
| ROM | flottants Applesoft (`MOVFM`, `FDIV`, `FMULT`, `FADD`, `AYINT`), `BELL1` (`$FBDD`, haut-parleur sans COUT) |

Le module sélectionne la ROM (`$C082`), le texte 40 colonnes page 1
(`TXTSET`, `LOWSCR`, `COL80OFF`, `ALTCHAROFF`, `DHIRES_OFF`) et écrit
directement dans la page texte (aucun crochet COUT). 80STORE peut rester
actif : PAGE2 est éteint.

### Déroulement et écran

1. `hof_gather` (≈ 0,14 s) puis `hof_score`.
2. Bilan, lignes 0 à 12 (`score_ref.breakdown`) ; valeurs sur 5 colonnes
   finissant en colonne 32, le score en inverse :

```
             JOURNEY SCORE                  (bandeau inverse)

SIERRA NEVADA, LEVEL 4                      (+ " (FREE)" en voyage libre)
ARRIVED AFTER 312 HOURS                     (DIED / ABANDONED)

PROGRESS  100% X 10          1000
ARRIVAL   YES                1000
HEALTH     62% X 5            310           (hors arrivée : "X 5 X 37%")
SPEED     720 - 312           408           (hors arrivée : "NO")
                            -----
TOTAL                        2718
LEVEL       4 X 14/14        2718
SCORE                        2718           (valeur en inverse)
```

3. Voyage libre ou région hors 1–6 : ligne 21 « FREE JOURNEY: NOT
   RANKED. », aucun accès disque.
4. Sinon `hm_load` (OPEN, READ 512, CLOSE ; ≈ 0,8 s). Erreur : ligne 21
   « HALL OF FAME UNREADABLE, ERROR $xx. » (ou « … FILE NOT RECOGNISED. »),
   pas d'écriture.
5. Compteurs + 1 ; rang. Ligne 14 « SIERRA NEVADA - TOP 5 », lignes 15–19 :
   `1 ALICE     2718   312H L4  ARRIVED` (« 2 - » pour une entrée vide).
6. Rang 1–5 : ligne 21 « NEW RECORD: RANK n. TYPE YOUR NAME. », ligne 22
   « RETURN: SAVE   ESC: DO NOT RECORD ». Saisie sur la ligne du rang,
   colonnes 2–9 : A–Z (minuscules converties), 0–9, espace (pas en tête),
   `.` et `-` ; flèche gauche ou DELETE efface ; RETURN valide (un caractère
   au moins) ; ESC retire l'entrée (« NOT RECORDED. ») ; toute autre touche
   bipe. Hors classement : « NOT IN THE TOP 5. »
7. `hm_save` (OPEN, WRITE 512, CLOSE ; ≈ 1,9 s), ligne 22 : « HALL OF FAME
   SAVED. », « DISK WRITE-PROTECTED: NOT SAVED. » (`$2B`) ou « DISK ERROR
   $xx: NOT SAVED. ». En cas d'erreur de WRITE, CLOSE est tenté quand même ;
   si CLOSE échoue, un CLOSE de référence 0 ferme tout.
8. Ligne 23 « PRESS A KEY FOR THE MENU. », une touche, sortie.

`hof_key_wait` est la boucle d'attente clavier (point d'arrêt des tests) ;
le tampon clavier est vidé une fois à l'entrée du module (touche de l'écran
de fin), pas à chaque lecture (les touches tapées pendant un bip restent).

Mesures (POM2, IIe, Disk II, intégration temporaire) : `module_end` →
module 1,80 s ; module → écran final 2,87 s dont 0,77 s de lecture
et 1,94 s d'écriture des compteurs ; touche → menu 14,3 s (relance,
tronc, lecture de `NEOWILD.HOF` par le chargeur).

## 5. Chargeur : menu et écran H (`src/hof_menu.s`)

Fragment à inclure (aucun `.segment`, aucun `.export`, noms `hm_` / `HM_`) ;
le module l'inclut aussi, sans `HOF_LOADER`.

| Symbole à définir avant `.include` | Chargeur (`boot.s`) | Module (`hof.s`) |
|---|---|---|
| `HOF_ZP` (4 octets de page zéro) | `source` (`source`, `dest` : libres au menu) | `gp1` |
| `HOF_BUF` (512 octets) | `STAGE` (`$2000`, inutilisé du tronc au paquet) | `$5800` |
| `HOF_MLI` (A = commande, X/Y = paramètres) | `ld_mli` | `mli_call` |
| `HOF_IOBUF` | `io_buffer` | `io_buffer` |
| `HOF_PATH` (`/VOLUME/NEOWILD.GEO`) | `geo_path` | `geo_path` |
| `HOF_READ_PARMS` (facultatif) | `read` : `ld_mli` compte alors les 512 octets dans `mli_bytes` | — |
| `HOF_PATHBUF` (facultatif, 65 octets) | — (`.res` dans LOADER) | `$5A00` |
| `HOF_LOADER` | 1 : `hm_best`, `hm_hall` | — : `hm_save` |
| `HOF_NAMES_LO/HI` | `region_names_lo/hi` (`menu.inc`) | — |

Points d'entrée : `hm_load` (lecture, validation ; en échec, table vide en
mémoire et `hm_status` = code MLI ou `$01` « non reconnu »), `hm_best`,
`hm_hall`, `hm_save`, et les primitives `hm_clear`, `hm_at`, `hm_char`,
`hm_print`, `hm_num`, `hm_hex`, `hm_entry`, `hm_rank_head`, `hm_title`.

- **Lecture** : une fois, juste après le tronc (`jsr hm_load` avant
  `loader_menu`) : le bitmap n'est pas encore protégé et `STAGE` reste
  intact jusqu'au paquet. Fichier absent : tables vides, écran H avec
  « HALL OF FAME UNREADABLE, ERROR $46. ».
- **BEST** : après l'impression de `m_menu`, `hm_best` écrit
  `BEST nnnnn` (colonnes 29–38, score aligné à droite) sur les lignes 2, 5,
  8, 11, 14, 17 des scénarios dont la première entrée est occupée ; les
  autres gardent `BEST -` de `tools/genmenu.py` (inchangé).
- **Écran H** (40 × 24) : bandeau « HALL OF FAME » ; trois rangées de deux
  blocs (scénarios impairs colonne 0, pairs colonne 20 ; en-têtes lignes 2,
  9, 16 en inverse `s NOM`), cinq lignes `k NOMNOMNO nnnnn` ou `k -` ;
  ligne 22 `SCENARIO JOURNEYS: n` (ou l'erreur), ligne 23 « PRESS A KEY FOR
  THE MENU. ». Le chargeur attend la touche (`menu_key`) puis réaffiche le
  menu.

## 6. Tailles

Mesures du 13 octobre 2026 sur l'intégration temporaire (sources de travail
du jour, `build_disk.py --packing auto`) :

| Élément | Avant | Après | Écart |
|---|---:|---:|---:|
| `NEOWILD.SYSTEM` | 3 911 octets, 9 blocs | 4 930 octets, 11 blocs | +1 019 (fragment ≈ 1 136, `m_hall` −117) |
| segment LOADER | `$9600-$A524` | `$9600-$A91F` (LOADBSS jusqu'à `$A967`) | marge 2 968 octets sous `TABLE` (`$B500`) |
| module INPUT | 1 602 octets (446 libres) | 1 666 (382 libres) | +64 |
| RAM auxiliaire libre (INPUT y est préchargé) | Burma 745, Bolivia 769, BC 956 | 681, 705, 892 | −64 dans chaque région |
| `NEOWILD.DAT` | 55 923 → 46 441, 92 blocs | 55 987 → 47 863, 95 blocs | brut +64 ; « auto » passe un enregistrement en brut (+119 seulement en `--packing lz`) |
| `NEOWILD.END` | — | 3 044 octets, 7 blocs (6 + index) | 6 blocs de données tant que ≤ 3 072 octets |
| `NEOWILD.HOF` | — | 512 octets, 1 bloc | |
| Volume | 244/280 blocs, 36 libres | 257/280, **23 libres** | +13 |
| RAM principale résidente | — | 0 | rien de résident |

Mesure finale après l'intégration (avec les étoiles de l'étape 5) :
`NEOWILD.SYSTEM` 4 943 octets, 11 blocs ; INPUT 1 666 octets ; volume
269/280 en paquetage `auto` (11 libres), **246/280 en `lz`** (34 libres),
devenu le défaut (MEMORY.md § 9.5). Le chiffre de 257/280 ci-dessus était
celui de l'intégration temporaire sans le module des étoiles.

## 7. Tests

- `tests/test_hof_ref.py` (Python pur) : exemples de la § 2, bornes 16 bits
  sur toutes les entrées, bornages, ordre des divisions ; fichier vide et
  `genhof.py` ; aller-retour d'une entrée ; règles de rang (vide, plus
  haut, égalité avec moins d'heures, égalité complète après, score nul) ;
  insertion et cinquième entrée sortie ; compteurs saturés ; 400 voyages
  aléatoires (tables triées, top 5 exact) ; écrans ; `po2woz` (piste
  redécodée en 6-and-2 = secteurs du `.po`, drapeau de protection).
- `tests/test_hof.py` (banc, a2shot `--iie`) : une session joue 19 cas sur
  le même volume — menu vide, arrivée avec nom corrigé (espace de tête,
  flèche gauche, caractère refusé), mort, premier rang, égalités, cinquième
  sortie, hors top 5, ESC, voyage libre, Burma avec DELETE, erreur de READ
  `$27`, erreur de WRITE `$27`, `$2B` injecté, `NEOWILD.END` absent,
  bornages niveau/heures/progression, score nul, menu rempli. À chaque cas :
  écran de saisie et écran final octet pour octet contre `score_ref`,
  composantes du module, table en mémoire, journal des appels MLI, appel
  `overlay_load 13`. Puis éjection (POM2 réécrit la copie privée), image
  retrouvée et `NEOWILD.HOF` relu avec `dev/tools/prodos/read_volume.py` :
  égal à la référence, toujours un bloc « seedling », aucun bloc alloué.
  Trois autres volumes : **WOZ protégé en écriture** (`tools/po2woz.py` ;
  POM2 honore le drapeau INFO, ProDOS rend un vrai `$2B` ; score affiché,
  disque inchangé), en-tête invalide, fichier absent (`$46`).
- `tests/test_hof_game.py` : sur `dist/NEOWILDERNESS.po` une fois intégré
  (SKIP avant) — écran H vide, Sierra niveau 4 déplacé à trois cases du
  poste, QUIT/Y, écran = référence pour les valeurs relevées, nom, retour au
  menu, BEST et écran H relus, voyage libre sans accès au fichier. Passé
  sur l'intégration temporaire (score 1 425).

`make -f hof.mk test` lance les deux premiers ; `make -f hof.mk` construit
le disque de démonstration (trois fins de voyage, puis BEST et écran H ;
toute touche continue) ; `make -f hof.mk sizes` donne les tailles.

## 8. Limites

- Le module occupe 3 044 octets : 28 octets de plus feraient passer
  `NEOWILD.END` à 7 blocs de données (8 avec l'index).
- `wild.lbl` contient deux fois chaque `hm_*` (copie du chargeur et copie du
  module, toutes deux autour de `$9600`) : les tests doivent viser les
  `hof_*` (module) et `menu_key`/`loader_menu` (chargeur).
- Chaque fin de voyage de scénario écrit le disque (≈ 1,9 s) ; une
  disquette protégée affiche donc un message à chaque partie.
- Le niveau et le genre sont ceux de l'en-tête de carte : un `MAP+22` hors
  1–10 est borné, il n'est pas refusé.

## 9. Intégration (agent moteur)

Le correctif complet, appliqué et construit sur une copie des sources du
13 octobre : [hof_integration.diff](hof_integration.diff)
(`git apply docs/hof_integration.diff` depuis `neowilderness/`, ou à la main
si les fichiers ont bougé).

1. **`src/wild.s`** : dans `quit`, `jmp module_restart` → `jmp module_end` ;
   après `.include "geography.s"` (donc après `game.s` : `gp1` doit être
   connu comme page zéro), `.include "hof.s"`.
2. **`src/input.s`** : remplacer le bloc `module_restart` (commentaire,
   code, `restart_system`, `restart_open/read/close`, `restart_path`,
   `.export module_restart`) par `.include "hof_load.inc"`, toujours dans le
   segment INPUT. `restart_path` disparaît (`hl_path`).
3. **`src/wild.cfg`** : `HOF: start = $9600, size = $2000, type = rw, file
   = "build/wildhof.bin";` dans MEMORY et `HOF: load = HOF, type = rw;` dans
   SEGMENTS.
4. **`src/boot.s`** : `jsr hm_load` juste avant `loader_menu:` ; `jsr
   hm_best` après l'impression de `m_menu` dans `menu` ; `@hall: jsr
   hm_hall / jsr menu_key / jmp menu` ; supprimer `m_hall` ; avant
   `move_src`, les définitions de la § 5 puis `.include "hof_menu.s"`.
   Mettre à jour l'en-tête (« H hall of fame »).
5. **`tools/build_disk.py`**, dans le dossier de construction du volume :
   ```python
   (stage / 'NEOWILD.END#069600').write_bytes((build / 'wildhof.bin').read_bytes())
   (stage / 'NEOWILD.HOF#060000').write_bytes((build / 'NEOWILD.HOF').read_bytes())
   ```
   (ou `score_ref.empty_file()` directement) ; ajouter leurs blocs à
   `layout.json`. L'entrée 24 du répertoire reste de longueur 0.
6. **`Makefile`** :
   ```make
   $(BUILD)/NEOWILD.HOF: tools/genhof.py tools/score_ref.py
   	$(PYTHON) -I tools/genhof.py $@
   ```
   `$(BUILD)/NEOWILD.HOF` dans les dépendances de `$(DISK)` ;
   `src/hof.s src/hof_menu.s src/hof_load.inc` dans celles de `wild.o`,
   `src/hof_menu.s` dans celles de `boot.o` ; dans `test` :
   `$(MAKE) -f hof.mk test` et `$(PYTHON) tests/test_hof_game.py`.
7. **Tests existants** :
   - toute fin de partie passe maintenant par l'écran du module : après
     `QUIT`/`Y` à la première invite (score nul, jamais classé), une seule
     touche à `hof_key_wait` ramène au menu ; une fin classée attend un nom
     (ou ESC) puis une touche. `test_boot.py`, `test_prodos.py` et les tests
     de retour au menu doivent attendre `hof_key_wait` avant `menu_key` ;
   - appels MLI après `start` : 3 (`NEOWILD.END`) + 3 (lecture) + 3
     (écriture) en fin de voyage de scénario, 3 en voyage libre ; aucun
     pendant la partie (`test_resident.py`, `test_menu.py` inchangés tant
     qu'ils s'arrêtent avant la fin) ;
   - `test_pack_boot.py` et `docs/MEMORY.md` § 9 : volume 257/280 (23
     libres), `NEOWILD.SYSTEM` 11 blocs, RAM auxiliaire −64 octets ;
   - `test_menu.py` : sur le volume construit, `NEOWILD.HOF` est vide et
     les `BEST -` restent.
8. **Documents** : `SCENARIOS.md` § 7–8 (progression `DONE=`, santé
   pondérée, score nul, module à `$9600` lu depuis `NEOWILD.END`), boîtes
   de l'étape 6 du `TODO.md`, `MEMORY.md` § 9.
