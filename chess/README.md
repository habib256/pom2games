# Chess — Apple II+ / DOS 3.3

Port Apple II du sketch `sketchs/gen2/game_chess` de
[POM1](https://github.com/habib256/pom1) (GEN2_Chess, VERHILLE Arnaud) et de
son moteur `dev/lib/games/chess`. Échecs complets (roque, prise en passant,
promotion, échec et mat, pat) contre l'ordinateur (1, 2 ou 3 demi-coups) ou à
deux, en HGR page 1. Pièces de cc65-Chess (Stefan Wessels, portage Apple II
Oliver Schmidt, dessins Frank Gebhart).

    make            # -> ../dist/CHESS.dsk  (image DOS 3.3 5"1/4 amorçable)
    make run        # démarre l'image dans POM2 (profil Apple ][+)

Prérequis : cc65 (`brew install cc65`) et python3. Tout le reste est dans
`../dev`, pistes système DOS 3.3 comprises. `make run` lance POM2 installé
(`/Applications/POM2.app`, ou `make run POM2=chemin/vers/POM2`).

## Commandes

| Clavier                  | Action                                         |
|--------------------------|------------------------------------------------|
| I J K L, flèches         | déplacer le curseur                            |
| ESPACE ou RETURN         | choisir la pièce, puis la case d'arrivée       |
| ESC                      | annuler la sélection                           |
| U                        | annuler le dernier coup                        |
| M                        | changer de mode (HVH, WAI, BAI, AVA)           |
| P                        | niveau de l'IA : L1, L2, L3 = 1, 2, 3 demi-coups |
| N                        | nouvelle partie (retour au menu)               |

Le niveau s'affiche en haut du panneau (`W WAI L2`) ; L2 par défaut, gardé
après N. Temps de réponse mesurés sur 12 positions : L1 < 1 s ; L2 0,1 à
1,5 s ; L3 0,2 à 10 s (4 s après 1.e4).

Au démarrage (et après N), le menu sur l'écran texte propose : 1 deux joueurs,
2 vous avec les blancs, 3 vous avec les noirs, 4 ordinateur contre ordinateur.
Sur un II+, seules les flèches gauche/droite existent (haut/bas sur un //e).

Améliorations prévues : voir [`TODO.md`](TODO.md).

## Contenu

    src/chess.s          le frontal HGR (ca65), BRUN à $6000
    src/chess_engine.asm le moteur (repris de POM1 sans changement de logique)
    src/chess_common.inc constantes partagées
    src/chess_tables.inc tables du moteur
    src/chess.cfg        config ld65 : ZP $50-$FF, BSS $1000, plateau $1400, code $6000
    src/hello.bas        HELLO : 10 PRINT CHR$(4);"BRUN CHESS"
    ../dist/CHESS.dsk    l'image produite
    test/                banc du moteur seul sur le cœur POM2 (cycles exacts) :
                         `make perft | best | undo | play | prof | exact` ; comparer deux
                         versions du moteur en diffant la sortie

Bibliothèques : `../dev/lib/apple2` (clavier, HGR), `../dev/lib/hgr` (pièces,
police, tables de lignes), `../dev/tools/dos33.py` (image disque).

## Différences avec l'original Apple-1 / GEN2

- Pas de second terminal : le menu des modes s'affiche sur l'écran texte
  (le plateau attend sur la page HGR), et les messages « à vous », « réflexion »,
  « échec », mat/pat passent sur le panneau de droite de l'écran HGR (ligne 1 ;
  ligne 23 « N = NEW GAME » en fin de partie).
- Clavier Apple II (`$C000` + `$C010`), flèches en plus de IJKL.
- Un seul binaire de 8,4 Ko à `$6000` ; zéro-page en `$50` pour que COUT du
  Moniteur fonctionne ; état du jeu en `$1000-$14FF` (le HELLO de BASIC reste intact en `$0800`).
