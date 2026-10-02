# Maze 3D — Apple II+ / DOS 3.3

Port Apple II du sketch `sketchs/gen2/game_maze3d` de
[POM1](https://github.com/habib256/pom1) (HGR_Maze3D, VERHILLE Arnaud) :
un dungeon crawler façon Wizardry en fil de fer. Labyrinthe 11x7 généré par
DFS, vue 3D avec ombrage, carte vue de dessus, niveaux d'expérience et combats
au tour par tour contre gobelins, orcs et mages noirs. Sprites SCROLL-O-SPRITES
de Quale (CC-BY-3.0).

    make            # -> ../dist/MAZE3D.dsk  (image DOS 3.3 5"1/4 amorçable)
    make run        # démarre l'image dans POM2 (profil Apple ][+)

Prérequis : cc65 (`brew install cc65`) et python3. Tout le reste est dans
`../dev`, pistes système DOS 3.3 comprises. `make run` lance POM2 installé
(`/Applications/POM2.app`, ou `make run POM2=chemin/vers/POM2`).

## Commandes

| Clavier           | Action                    |
|-------------------|---------------------------|
| I ou flèche haut  | avancer                   |
| K ou flèche bas   | reculer                   |
| J ou flèche gauche| tourner à gauche          |
| L ou flèche droite| tourner à droite          |
| M                 | carte / vue 3D            |
| H                 | aide                      |
| A / F             | attaquer / fuir (combat)  |
| ESC               | quitter vers DOS          |

Trouvez la sortie `E` en bas à droite. Sur un II+ il n'y a que les flèches
gauche/droite ; haut/bas existent sur un //e. La touche pressée sur l'écran
titre choisit le labyrinthe.

Améliorations prévues : voir [`TODO.md`](TODO.md).

## Contenu

    src/maze3d.s               le jeu (ca65), BRUN à $6000
    src/sprites_trollkind.asm  gobelin, orc (SCROLL-O-SPRITES, repris de POM1)
    src/sprites_characters.asm mage noir (idem)
    src/maze3d.cfg             config ld65 : ZP $50-$FF, labyrinthe $1000, code $6000
    src/hello.bas              HELLO : 10 PRINT CHR$(4);"BRUN MAZE3D"
    ../dist/MAZE3D.dsk         l'image produite

Bibliothèques : `../dev/lib/apple2` (HGR, sortie DOS), `../dev/lib/hgr` (texte
8x8, sprites 16x16, tables de lignes), `../dev/tools/dos33.py`.

## Différences avec l'original Apple-1 / GEN2

- Clavier Apple II (`$C000` + `$C010`), minuscules repliées, flèches en plus
  de IJKL.
- Commutateurs `$C050-$C057`.
- **Double tampon HGR1/HGR2** : chaque écran complet (vue 3D, carte, combat,
  titre, aide, fin de partie) est dessiné sur la page cachée puis affiché d'un
  seul coup en basculant de page. L'original affichait une page noire pendant
  le redessin ; ici l'image précédente reste à l'écran jusqu'à ce que la
  suivante soit prête. Le HUD, qui n'est pas redessiné à chaque pas, est
  reconstruit sur les deux pages quand il change.
- ESC revient au prompt DOS : la page zéro est sauvegardée au lancement et
  restaurée en sortie, BASIC et DOS retrouvent leurs pointeurs.
- Binaire de 11,6 Ko à `$6000`, zéro-page en `$50`.
- Correction d'un bogue hérité : en revenant de l'écran d'aide (H), la zone
  du HUD gardait « PRESS ANY KEY... » au lieu des statistiques.
