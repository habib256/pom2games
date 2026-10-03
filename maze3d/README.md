# Maze 3D — Apple II+ / DOS 3.3

Port Apple II du sketch `sketchs/gen2/game_maze3d` de
[POM1](https://github.com/habib256/pom1) (HGR_Maze3D, VERHILLE Arnaud) :
un dungeon crawler façon Wizardry en fil de fer. Trois labyrinthes 11x7 générés
par DFS enrichi de boucles et d'une salle 2x2, vue 3D avec ombrage, carte qui
se découvre, niveaux d'expérience et combats au tour par tour contre gobelins,
orcs, mages noirs et un dragon final. Chaque étage demande de trouver une
relique avant d'atteindre la sortie ; trois caches rapportent or et parfois
une potion.
Les trois premiers monstres utilisent des sprites SCROLL-O-SPRITES de Quale
(CC-BY-3.0) ; le dragon est un sprite original.

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
| P                 | boire une potion (+10 PV) |
| A / G / F         | attaquer / garder / fuir (combat) |
| R (écran titre)   | rejouer la graine du record |
| ESC               | quitter vers DOS          |

Chaque sortie mène à une boutique entre deux étages : H soigne 10 PV pour
8 pièces d'or (maximum 30 PV), A ajoute 1 ATK pour 12 pièces et D ajoute
1 DEF pour 12 pièces, P achète une potion pour 6 pièces. C descend à l'étage
suivant. La sortie exige la relique de l'étage ; la dernière exige aussi la
mort du dragon. La garde réduit le prochain coup et renforce la prochaine
attaque. Les orcs et le dragon annoncent leur coup puissant ; la magie ignore
l'armure. Une fuite réussie ramène sur la case précédente.

La carte indique les cases visitées, la salle `R`, les caches `$`, la relique
`*`, les monstres aperçus et la graine hexadécimale. Elle révèle la sortie une fois sa case
explorée. À la victoire, le score récompense les caches et le niveau, puis
retire un point par quatre déplacements. Le meilleur score et sa graine sont
enregistrés dans `MAZESCORE` sur la disquette ; une disquette protégée permet
de jouer mais ne conserve pas le nouveau record.

Trouvez la sortie `E` en bas à droite. Sur un II+ il n'y a que les flèches
gauche/droite ; haut/bas existent sur un //e. La touche pressée sur l'écran
titre contribue à la graine d'une nouvelle partie. `R` rejoue celle du record.

Améliorations prévues : voir [`TODO.md`](TODO.md).

## Contenu

    src/maze3d.s               le jeu (ca65), BRUN à $6000
    src/narrator.asm            textes du narrateur, BLOAD à $1100
    src/sprites_trollkind.asm  gobelin, orc (SCROLL-O-SPRITES, repris de POM1)
    src/sprites_characters.asm mage noir (idem)
    src/maze3d.cfg             config ld65 : ZP $50-$FF, données $1100, code $6000
    src/hello.bas              charge MAZETEXT et MAZESCORE, puis BRUN MAZE3D
    tests/check_generation.py  vérification de 100 labyrinthes dans l'émulateur
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
- Binaire de 11,6 Ko à `$6000`, zéro-page en `$50`. Les textes longs sont dans
  `MAZETEXT` sur la disquette, chargé à `$1100`. `MAZESCORE` occupe huit octets
  à `$1F00` et contient la version, le record, sa graine et une somme de
  contrôle.
- Correction d'un bogue hérité : en revenant de l'écran d'aide (H), la zone
  du HUD gardait « PRESS ANY KEY... » au lieu des statistiques.
