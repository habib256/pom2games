# SAVE et RESTORE (lot 9)

Cinq parties sur la disquette du jeu, comme l'original (V1 de
[ORIGINAL_GAP.md](ORIGINAL_GAP.md) § 2.11, lot 9 du § 3). Code :
[`src/save.s`](../src/save.s) ; construction : `tools/build_disk.py`
(`save_files`) ; test : [`tests/test_save.py`](../tests/test_save.py).
Mesures du 14 octobre 2026 sur la tête `d64afbb` + ce lot.

## 1. Décisions en bref

| Question | Choix |
|---|---|
| Commandes | `SAVE` et `RESTORE` (verbes 41 et 42 du vocabulaire, déjà présents) ; le numéro de partie 1–5 est demandé par l'invite numérique d'INPUT (`get_number`), ou tapé à la suite : `SAVE 2`, `RESTORE 2` |
| Où est le code | un module lu sur le disque **à la commande**, `NEOWILD.SAV` (segment `SAVEMOD`, `build/wildsav.bin`, 1 218 octets), exécuté dans la fenêtre SIM à `$9600`, comme `NEOWILD.END` ; seul un relais de 237 octets est résident (WILDLO) |
| Où sont les parties | un fichier ProDOS par partie, `NEOWILD.S1`…`NEOWILD.S5`, de longueur fixe (1 424 octets), créé vide par `tools/build_disk.py` : le jeu ne fait jamais de CREATE et n'alloue aucun bloc (écriture en place, comme `NEOWILD.HOF`) |
| Contenu | l'état mutable de la partie seulement (1 392 octets) : la carte, les modules et la simulation sont rechargés, pas sauvés (l'original sauvait ≈ 24 Ko) |
| Format | en-tête de 32 octets versionné (magie, version, région, niveau, genre, identifiant de construction, longueur, somme de Fletcher-16, heures, nom de région), puis l'état brut |
| Autre région | refusée avec le nom de la région de la partie : `GAME 1: SIERRA NEVADA ONLY.` (l'original : `C$(IC)" ONLY!"` ; le point remplace le `!`, qui est un code de `message`) |
| Écrasement | une partie occupée est décrite (`GAME 1: SIERRA NEVADA, 14 H.`) et `REPLACE IT? Y: YES   N/ESC: NO` est demandé ; une partie vide est écrite sans question |
| Disque | lectures et écritures **seulement** à SAVE, RESTORE et en fin de voyage (`NEOWILD.END`/`.HOF`) ; `tests/test_resident.py` le vérifie |
| Éditions | deux images livrées depuis le 14 octobre 2026 : `dist/NEOWILDERNESS.po` (140 Ko, 224/280 blocs, cinq parties) et `dist/NEOWILDERNESSXL.po` (800 Ko, 305/1 600) ; `tools/build_disk.py --edition` (§ 9) |

## 2. Dialogues

| Situation | Rangées 20–23, colonne de droite |
|---|---|
| `SAVE` | `SAVE THE JOURNEY AS GAME 1-5?` / `ESC CANCELS.`, puis l'invite `>` |
| `RESTORE` | `RESTORE WHICH GAME, 1-5?` / `ESC CANCELS.` |
| ESC, 0 ou ligne vide | `ACTION CANCELLED.` (INPUT) |
| 6 et plus | `GAMES ARE NUMBERED 1 TO 5.` |
| partie occupée (SAVE) | `GAME n: RÉGION, h H.` / `REPLACE IT? Y: YES   N/ESC: NO` ; une autre touche que Y : `GAME n KEPT. NOT SAVED.` |
| écrite | `GAME n SAVED.` |
| reprise | la vue est redessinée, puis `GAME n RESTORED.` |
| partie vide | `GAME n IS EMPTY.` |
| autre région | `GAME n: RÉGION ONLY.` |
| autre construction ou format | `GAME n WAS SAVED BY ANOTHER VERSION.` |
| somme fausse | `GAME n IS DAMAGED.` |
| disque protégé (`$2B`) | `DISK WRITE-PROTECTED: NOT SAVED.` |
| fichier absent (`$46`) | `NEOWILD.Sn IS MISSING.` |
| autre erreur MLI | `DISK ERROR xxH. NOTHING CHANGED.` (le `$` est un code de `message`) |
| module illisible | `NEOWILD.SAV CANNOT BE READ.` |

Aucun refus ne modifie la partie : RESTORE lit tout le fichier dans un
tampon et ne recopie l'état qu'après toutes les vérifications.

## 3. Inventaire de l'état

Méthode : balayage statique de toutes les écritures absolues (`STA`,
`STX`, `STY`, `STZ`, `INC`/`DEC`, `fst` = `MOVMF`) de toutes les images
liées vers la RAM principale résidente, puis comparaisons de mémoire
complète (`$0000-$03FF`, `$0800-$1FFF`, `$4000-$95FF`, `$B600-$BDFF`)
après des parties jouées (marche, nage, repas, objets pris et posés,
repos, nuit) : avant et après SAVE/RESTORE, puis après les mêmes commandes
dans les deux branches.

Sauvé (`sv_ranges`, 1 392 octets) :

| Plage | Octets | Contenu |
|---|---:|---|
| `sun_alt8` … `text80` | 5 | hauteurs du Soleil et de la Lune, phase, humeur du ciel, mode texte |
| `tree_in` … `cachey` | 38 | arbre, position, cap, mort, compteurs du voyage, eau non traitée et son hasard (`water_rng`), victoire, nuit, abri trouvé, période, air, vent, poids, cache au sol |
| `s_hour` … `it_pack_hi` | 855 | horloge (`s_hour`, `s_elap`, `s_date`), énergie, déficits, santé, corps, thermique, mouillé, lever/coucher, `t1`…`t5`, trame de marche, les neuf tables d'objets `it_place`, `it_oz_*`, `it_vol_*`, `it_gnd_*`, `it_pack_*` |
| `resource_seen` … fin de GDATA | 277 | ressources, marche, vêtements, météo (`weather_seed`, horloge, fronts, ciel, tendance), médical (blessures, traitements, actions), altitude, scènes, animal présent (espèce, case, âge ; plus de cap depuis le 15 octobre 2026), fréquence NATURE, `fauna_rng`, caches de scène, HUD (`ui_previous`, `ui_pending`…), forêt et géographie fine |
| `it_x`, `it_y` (WILDLO) | 152 | cases des objets posés au sol |
| en-tête de carte `$7000-$703F` | 64 | abri trouvé (`MAP+16…18`), ressources découvertes (`MAP+26…36`), niveau (`+22`), genre (`+33`), faune et fronts (`+38…40`) |
| `fauna_named` (TEXT) | 1 | espèce nommée par le dernier message |

Non sauvé, et pourquoi :

| Élément | Raison |
|---|---|
| `overlay_current`, `overlay_wanted`, `overlay_reads`, `sim_loaded`, `sim_quiet` | cache des modules : décrit le contenu des fenêtres au moment présent, pas la partie |
| `inbuf`, `nounbuf` | ligne de commande, réécrite par chaque commande |
| `it_kcal`, `verbs`, `verb_lo/hi`, `card_*`, `cdef_*`, `ctol_*`, `m_dead/goal/weak_travel` | tables constantes en GDATA (le test vérifie qu'aucune commande ne les écrit et qu'elles égalent `build/wildgame.bin`) |
| BSS (`cur_pal`, bandes, `ram_unit`, `_prodos_*`) | temporaires du tracé, recalculés à chaque vue ; unité /RAM de la machine |
| page zéro (`GZP`, rendu, `MZP`) | temporaires d'une commande (`verb`, `minutes`, `wdx`…) : la comparaison des continuations le confirme |
| `SCRATCH` `$9500`, fenêtres `$5800` et SIM | temporaires et images rechargées ; `sim_loaded` vaut 0 entre deux commandes (`finish_simulation`) |
| `load_used`, `load_vol`, `load_bad`, `saved_item` (WILDLO) | recalculés (`load_totals`) ou temporaires d'une commande |
| `scene_ceiling`, `row_p0`, `row_n0`, `m_fauna_stop` | caches de projection et texte composé avant affichage |
| carte `$7040-$94FF`, bois, textes et couleurs de région, répertoire | constants pour une région (le paquet chargé) ; la région est vérifiée |
| grille du menu (MENUCODE, MENUSWAP) | interface : RESTORE remet `mn_cur`, `mn_top`, `mn_verb`, `menu_noun` à 0 |
| compteurs `RESBSS` (`mli_calls`…), chemin `geo_path` | instrumentation et machine |

Un futur lot qui ajoute une variable en GDATA l'ajoute au sauvé sans rien
faire s'il la place en fin de GDATA (la dernière plage va jusqu'à
`__BSS_RUN__`) ; ailleurs, `tests/test_save.py` (couverture) échoue tant
qu'elle n'est ni sauvée ni déclarée volatile ou constante. Un lot qui
modifie la grille de la carte (abris construits, objets dans les cases)
devra ajouter sa plage à `sv_ranges` : aujourd'hui, seul l'en-tête change.

## 4. Format de `NEOWILD.Sn`

| Offset | Taille | Contenu |
|---:|---:|---|
| 0 | 2 | `'N','W'` (`$4E $57`) ; absent : partie vide (le fichier livré est nul) |
| 2 | 1 | version 1 |
| 3 | 1 | région 1–6 (`region_number`) |
| 4 | 1 | niveau (`MAP+22`) |
| 5 | 1 | genre de voyage (`MAP+33`) |
| 6 | 2 | identifiant de construction (u16) : deux octets du SHA-256 du tronc et des six paquets, écrits dans `NEOWILD.SAV` (`sv_build`) par `tools/build_disk.py` ; une partie d'une autre construction (autre code, autre carte) est refusée |
| 8 | 2 | longueur de l'état (1 392) |
| 10 | 2 | Fletcher-16 de l'état (deux sommes de 8 bits à retenue circulaire : somme, puis somme des sommes) |
| 12 | 2 | heures écoulées (`s_elap` entier) |
| 14 | 2 | réservé, 0 |
| 16 | 16 | nom de la région (`region_name`, ASCII, complété par des zéros) |
| 32 | 1 392 | les plages de `sv_ranges`, bout à bout |

La longueur du fichier (`sv_size`) est lue dans le module par
`build_disk.py` : elle suit `sv_ranges` sans autre réglage.

## 5. Fichiers et volume

| Fichier | Octets | Blocs ProDOS |
|---|---:|---:|
| `NEOWILD.SAV` | 1 218 | 4 (3 + index) |
| `NEOWILD.S1`…`S5` | 1 424 chacun | 4 chacun (3 + index), 20 en tout |
| **Total du lot** | | **24** |

État au 16 octobre 2026 : la partie était passée à 1 725 octets (4 blocs
de données, 5 avec l'index) avec les lots 2, 3, 4 et 13, et le volume de
140 Ko était plein (280/280). Depuis, `sv_ranges` ne sauve plus les poids
et volumes constants des objets (W5 `it_oz_*`, W6 `it_vol_*`) : seulement
ceux que le jeu écrit (provisions et eau 22-37, FUEL 40 et GOLD 75 de la
préparation ; la gourde, 64, est recalculée par `load_totals`) ; l'état
fait 1 477 octets, la partie 32 + 1 477 = 1 509 octets, **4 blocs** (3 +
index ; assertion dans `src/save.s`), cinq blocs rendus au volume.
`tests/test_save.py` vérifie que les octets laissés de côté restent ceux de
l'image (`ITEM_TABLES`).

Volume 140 Ko : 252 → **276 blocs occupés sur 280, 4 libres**. Un volume
trop petit pour les cinq parties (disque de comparaison à carte native,
dont l'atlas ajoute 13 blocs au paquet Sierra : `tests/common.disk_with`)
garde autant de parties qu'il en tient (deux aujourd'hui) ; les autres
répondent `NEOWILD.Sn IS MISSING.`. Les fichiers `S1`…`S5` et `SAV` se
placent avant `NEOWILD.SYSTEM` dans le catalogue : le lanceur Bitsy Bye en
liste quinze avant lui (`tests/test_prodos.py`).

## 6. Code, mémoire, appels MLI

```
SAVE/RESTORE ─ dispatch (VOCAB) ─ jmp do_save (WILDLO, résident)
   do_save : bitmap $96-$AF libéré (4 octets gardés), chemin /VOL/NEOWILD.SAV
             en $AF00, OPEN (tampon $AB00), READ → $9600, CLOSE, jsr $9600
   module  : get_number (INPUT en $5800), /VOL/NEOWILD.Sn, OPEN …
             SAVE    READ 32 (occupée ?), question, image en $9C00,
                     SET_MARK 0, WRITE 1 424, CLOSE
             RESTORE READ 1 424 en $9C00, CLOSE, vérifications, recopie
   do_save : bitmap remis, sim_loaded = 0 ; après une reprise :
             stars_stale = 1, scene_cache_valid = 0, show_view,
             « GAME n RESTORED. »
```

| Zone | Usage pendant la commande |
|---|---|
| `$9600-$9AC1` | module `NEOWILD.SAV` (la fenêtre SIM est libre entre deux commandes) |
| `$9C00-$A18F` | image de la partie (en-tête + état) |
| `$AB00-$AEFF` | tampon d'E/S ProDOS des deux fichiers (`$BA00` est MENUCODE, vivant) |
| `$AF00-$AF27` | chemin ; `$AF40-…` messages composés |
| `$5800` | INPUT (invite numérique), comme toute commande |
| page zéro | `gp1`, `gp2`, `g0`–`g2` du jeu ; ProDOS n'utilise que sa zone `$3A-$4F` |

Le module rend la main au relais résident **avant** le redessin :
`show_view` peut charger le module des étoiles dans la même fenêtre SIM.

Coût résident : **WILDLO +237 octets** (relais 148, données et messages
89 ; 1 718 → 1 481 libres), **WILDGAME +6** (deux entrées des tables de
verbes). Stock auxiliaire : INPUT +13 octets (`SAVE`, `RESTORE` acceptent
un nombre en ligne), soit 13 de moins dans chaque région. Rien dans les
fenêtres pleines (VOCAB, TRAVEL, STATUS, SCREENS).

Appels MLI : SAVE **8** (OPEN, READ, CLOSE du module ; OPEN, READ de
l'en-tête, SET_MARK, WRITE, CLOSE) ; SAVE refusé par N : 6 ; RESTORE
**6** ; toute autre commande : 0 (`tests/test_resident.py`, compteurs de
`mli_call` et point d'arrêt sur `$BF00`).

## 7. Ce que RESTORE reconstruit

- l'état des plages, octet pour octet ;
- la vue : `show_view` (humeur et palette de l'heure restaurée, ciel,
  Lune, étoiles recalculées par `stars_stale = 1`, sprites de la scène
  par `scene_cache_valid = 0`, HUD, abri) ; la région étant la même, les
  sprites d'animaux et les couleurs chargés sont ceux de la partie ;
- le menu : première case, liste refermée ;
- la fenêtre SIM : `sim_loaded = 0`, la prochaine simulation recopie son
  image vierge ; l'instantané de TOPO est refait à chaque ouverture
  (`tp_save`).

## 8. Gardes ProDOS

- Le jeu protège `$60-$B9` dans le bitmap : OPEN et READ refusent un
  tampon protégé (`$56`). Le relais libère `$96-$AF` (octets 18 à 21 du
  bitmap, gardés), les remet ensuite, même en cas d'erreur ; le test
  compare le bitmap et le vecteur RESET avant et après chaque commande.
- Aucune allocation de bloc : écriture dans un fichier de longueur fixe
  (SET_MARK 0, WRITE de la longueur exacte). Le test relit l'image après
  éjection : mêmes blocs, même longueur, même nombre de blocs libres.
- Échec d'écriture : CLOSE est tenté ; s'il échoue, CLOSE de référence 0.
- Sortie : `tests/test_prodos.exit_state` est rejoué avec SAVE 1 et
  RESTORE 1 avant QUIT : page zéro, bitmap et vecteur RESET égaux à ceux
  de l'entrée du chargeur au QUIT final.

## 9. Mesures

POM2 (IIe enhanced, Disk II, ProDOS 2.4.3), a2shot, secondes invitées :

| Commande | Durée | Détail |
|---|---:|---|
| `SAVE 1` (partie vide) | 4,4–4,9 s | module 1,1 s ; ouverture et en-tête 1,4 s ; écriture et fermeture 1,7–1,9 s |
| `SAVE 1` (occupée, Y) | ≈ 4,4 s + la réponse | |
| `RESTORE 1` | 6,2 s de nuit, 9,1 s de jour | module 1,2 s ; lecture 1,9 s ; redessin de la vue 3 à 6 s (comme VIEW) |

## 10. Édition XL de 800 Ko

Depuis le 14 octobre 2026, `make` construit les deux éditions :
`dist/NEOWILDERNESS.po` (140 Ko, la Sierra seule, cinq parties, 224/280
blocs) et `dist/NEOWILDERNESSXL.po` (800 Ko, 1 600 blocs, les six
scénarios, `NEOWILD.BLK` pour CAMP/MEDVIEW/TREE/ORIENT lus à la demande ;
`tools/build_disk.py --edition xl`). a2shot démarre l'image de 819 200
octets sur la carte SmartPort 3,5" du slot 5 que POM2 expose dans
`pom2_core` depuis le 14 octobre (commit POM2 `b93b5f6`) : la suite de
tests tourne sur l'édition XL (`tests/common.py DISK`), l'édition 140 Ko
étant couverte par `tests/test_editions.py` et `test_save.py` (WOZ et
copie 140 Ko). L'historique de la première vérification manuelle sous POM2
(`SAVE 1` / `RESTORE 1` sur une image 800 Ko, volume `NEOWILD800`) est
dans CHANGELOG.md (lot 9).

## 11. Tests

- `tests/test_save.py` (≈ 15 s) : partie de nuit (marche, repas, eau,
  objet pris et posé, repos), SAVE 1, suite de référence, SAVE 1 refusé
  par N, RESTORE 1 (état et vue égaux, suite identique octet pour octet),
  refus sans effet (vide, 9, ESC), SAVE 2 en ligne, Burma (refus de
  région), redémarrage puis RESTORE, fichiers relus après éjection,
  défauts sur quatre volumes modifiés et un WOZ protégé, jour (paysage
  égal), couverture de GDATA, tables constantes, `exit_state` de
  `test_prodos.py` avec SAVE/RESTORE avant QUIT.
- `tests/test_resident.py` : SAVE 8 appels, RESTORE 6, les autres 0.
- `tests/test_prodos.py` (15 flèches dans Bitsy Bye),
  `tests/test_pack_boot.py` (catalogue), `tests/test_reference_state.py`
  (`verbs`, table constante qui grandit, comparée comme `verb_lo/hi`).

## 12. Limites, non fait

- **HELP** : le module SCREENS est plein (1 octet libre) ; l'aide ne cite
  pas SAVE et RESTORE. Le README les documente.
- Pas de catalogue des cinq parties ni de nom de partie (l'original
  demandait un nom de 32 caractères) : lire cinq en-têtes coûterait 15
  appels MLI et ≈ 5 s ; la question d'écrasement décrit la partie visée.
- Pas de disquette de sauvegarde séparée ni d'échange de disquettes : les
  parties sont sur la disquette du jeu (protégée : message, rien d'écrit).
- Le module (1 218 octets) dépasse 1 024 de 194 octets : un bloc de plus
  sur le volume (4 au lieu de 3).
- Une construction nouvelle refuse les parties de l'ancienne (identifiant
  de construction) : volontaire, l'état est une image mémoire.
