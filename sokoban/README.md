# Sokoban — Apple II+ / DOS 3.3

Port Apple II du sketch `sketchs/gen2/game_sokoban` de
[POM1](https://github.com/habib256/pom1) (HGR_Sokoban, VERHILLE Arnaud).
Le jeu tourne sur un Apple II+ 48 Ko (et tout modèle ultérieur), en HGR page 1,
et se joue à la manette ou au clavier. 72 niveaux Microban I (David W. Skinner).

    make            # -> dist/SOKOBAN.dsk  (image DOS 3.3 5"1/4 amorçable)
    make run        # démarre l'image dans POM2 (profil Apple ][+)

Prérequis : cc65 (`brew install cc65`) et python3. L'image est écrite par
`../dev/tools/dos33.py`, qui prend les pistes système DOS 3.3 (pistes 0-2) dans
`../dev/tools/dos33_system.bin`. `make run` lance POM2 installé
(`/Applications/POM2.app`, ou `make run POM2=chemin/vers/POM2`).

## Commandes

| Manette                      | Clavier                          | Action                     |
|------------------------------|----------------------------------|----------------------------|
| manche (répétition auto)     | I J K L, W A S D, flèches        | déplacer / pousser         |
| bouton 0                     | U                                | annuler le dernier coup    |
| bouton 1                     | H ou ESC                         | menu (aide)                |
| manche haut/bas + bouton     | I/K + RETURN ou ESPACE           | choisir dans le menu       |
|                              | R / N / P                        | recommencer / niveau suivant / précédent |

Sur l'écran titre et l'écran de succès : n'importe quelle touche ou bouton.

Améliorations prévues : voir [`TODO.md`](TODO.md).

## Contenu

    src/sokoban.s              le jeu (ca65), BRUN à $4000
    src/sokoban_levels.inc     niveaux 1-45  (RLE, repris de POM1)
    src/sokoban_levels_ext.inc niveaux 46-72 (RLE, repris de POM1)
    src/bbfont_subset.inc      police du HUD (Beautiful Boot, sous-ensemble)
    src/apple2_dos33.cfg       config ld65 : ZP $80-$9F, code+données à $4000
    src/hello.bas              HELLO : 10 PRINT CHR$(4);"BRUN SOKOBAN"
    dist/SOKOBAN.dsk           l'image produite

## Différences avec l'original Apple-1 / GEN2

- Pas de V-blank sur un II+ : les tuiles sont dessinées directement (2-3 par coup).
- Lecture des deux paddles dans une seule boucle de durée fixe (6 ms), boutons
  détectés sur front, répétition du manche toutes les ~200 ms.
- Tuiles en couleur HGR (murs orange, caisses orange, caisses placées et cibles
  vertes, joueur blanc) ; l'écran texte Apple-1 est remplacé par le menu HGR.
- Les 72 niveaux tiennent en RAM (7 Ko de binaire), zéro page limitée à
  $80-$9F comme la cible apple2 de cc65.
