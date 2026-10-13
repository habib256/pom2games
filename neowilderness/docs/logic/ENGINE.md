# Moteur de l'original : organisation

Comment le jeu original se répartit en mémoire et sur ses deux faces, établi
par traces du chargeur dans a2shot (étape `watch:` sur `$03DE`). Les détails
de chaque sous-système sont dans les autres fichiers de ce dossier :
[`state.md`](state.md) (état, STATUS, INVENTORY), [`survival.md`](survival.md)
(temps, physiologie), [`parser.md`](parser.md) (commandes, messages),
[`environment.md`](environment.md) (météo, terrain, faune),
[`sites.md`](sites.md) (entrée/sortie et protection thermique des abris),
[`trees.md`](trees.md) (grimper, suspendre la nourriture et récupérer le sac).

Ces adresses et numéros de modules décrivent l'original. Le découpage mémoire,
les fichiers DOS et l'état du portage sont dans
[IMPLEMENTATION.md](../IMPLEMENTATION.md). Le [TODO](../../TODO.md) suit
les travaux restants.

`tools/re_extract.py` découpe le moteur en blocs et les désassemble dans
`build/re/` (à partir de `build/game.bin`, `make dump-game`).

## Chargeur

`$03DE` (SMALLDOS) lit des secteurs bruts : A = nombre de secteurs, X = piste,
Y = premier secteur, `$BAFD` = page de destination. Les pistes sont des pistes
SMALLDOS : piste physique = 34 − piste, sur les deux faces (vérifié octet pour
octet sur le module STATUS).

## Mémoire pendant une partie

`$03E1` écrit avec les mêmes paramètres que `$03DE`. SURV3D `$103E`
sauvegarde `$4000-$4FFF` en Journey T04/S00 (16 secteurs) avant d'utiliser
cette RAM comme seconde page HGR ; `$1051` la relit. Le drapeau `$01`
indique si l'état est résident. Un dump à l'invite `$B0E2` peut donc contenir
des pixels à la place des objets et de la physiologie. Le pilote différentiel
observe le bloc à `$103E`, avant l'écriture, puis le combine avec la RAM
courante lorsque l'état est paginé. Les dumps bruts sont également conservés.

| Zone | Contenu | Origine |
|---|---|---|
| `$0200-$02FF` | Page de messages courante | Journey, pistes $18-$1B…, 1 secteur |
| `$0300-$03FF` | Points d'entrée SMALLDOS (`$03DE`) | |
| `$0800-$1EFF` | SURV3D : vue 3D, chargeur et répartiteur de modules | Sierra `SURV3D.CODE` |
| `$1F00-$1FFF` | ? | Journey piste $21 secteur $0D |
| `$2000-$3FFF` | HGR page 1 (vue) | |
| `$4000-$4CFF` | Cœur du jeu | Sierra piste $12, 13 secteurs |
| `$4D00-$4FFF` | Cœur, dont le lecteur de messages `$4EA2` | Journey piste $22 secteur $0B |
| `$5000-$57FF` | Cœur | Journey piste $05, 8 secteurs |
| `$5800-$61FF` | Module de commande courant | voir ci-dessous |
| `$6000-$AFFF` | Carte TOPO (voir `../ANALYSE.md`) | Sierra `TOPO` |
| `$B000-$B9FF` | Parseur et vocabulaire (boucle principale `$B003`) | Journey piste $22, 10 secteurs |
| `$BA00-$BFFF` | SMALLDOS | |

## Modules de commande

Le répartiteur de SURV3D (`$0DDE`) range le numéro de module en `$0D59`, le
charge en `$5800` par `$0E7B` s'il n'est pas déjà présent (`$0D5A`), l'appelle
(`JSR $5800`) puis revient à `$B003`. Table en `$0E9F` (piste), `$0EA6`
(secteur), `$0EAD` (nombre), pour les modules 3 à 9 :

| Module | Piste | Secteur | Secteurs | Rôle |
|---|---|---|---|---|
| 3 | $05 | $08 | 4 | ? (pas de texte) |
| 4 | $01 | $0B | 5 | Copie de fichiers (disques de sauvegarde) |
| 5 | $06 | $0A | 7 | STATUS (charge ses libellés : piste $14 secteur 8) |
| 6 | $07 | $08 | 8 | INVENTORY |
| 7 | $13 | $00 | 8 | HELP (conseils) |
| 8 | $15 | $00 | 5 | CLUE (scénario de la cité perdue) |
| 9 | $22 | $01 | 10 | Parseur (rechargé en `$B000`) |
| — | $06 | $02 | 2 | Chargé par `$0E62` |

Autres chargements observés : piste $16 secteur 0 (5 secteurs, depuis
SURV3D `$10AD`) et piste $1D secteur 3 (5 secteurs, depuis `$1C63`),
ce sont des sprites (abri et crotale Sierra). Les positions et le format des
images sont détaillés dans [ANALYSE.md](../ANALYSE.md#graphismes-originaux-récupérés).
Les pages de messages sont chargées depuis `$4EA2`.

Sur la face Journey, les pistes physiques 7 à 14 (pistes SMALLDOS 20 à 27)
portent l'essentiel des textes, en ASCII lisible.
