# Sokoban — Apple II+ / DOS 3.3

Port Apple II du sketch `sketchs/gen2/game_sokoban` de
[POM1](https://github.com/habib256/pom1) (HGR_Sokoban, VERHILLE Arnaud).
Le jeu tourne sur un Apple II+ 48 Ko (et tout modèle ultérieur), en HGR,
et se joue à la manette ou au clavier. Niveaux : **Microban I à IV**
de David W. Skinner, tous ceux qui tiennent à l'écran sans défilement, au
besoin couchés : 150 sur 155, 122 sur 135, 92 sur 101 et 90 sur 102, soit
454 niveaux (voir [`levels/README.md`](levels/README.md)).

    make            # -> ../dist/SOKOBAN.dsk  (image DOS 3.3 5"1/4 amorçable)
    make run        # démarre l'image dans POM2 (profil Apple ][+)

Prérequis : cc65 (`brew install cc65`) et python3. L'image est écrite par
`../dev/tools/dos33.py`, qui prend les pistes système DOS 3.3 (pistes 0-2) dans
`../dev/tools/dos33_system.bin`. `make run` lance POM2 installé
(`/Applications/POM2.app`, ou `make run POM2=chemin/vers/POM2`).

## Commandes

| Manette                           | Clavier                          | Action                     |
|-----------------------------------|----------------------------------|----------------------------|
| manche (répétition auto)          | I J K L, W A S D, flèches        | déplacer / pousser         |
| bouton 0 (tapé)                   | U                                | annuler un coup            |
| bouton 0 maintenu + manche ← / →  | U / Y                            | annuler / rejouer (en continu) |
|                                   | R                                | recommencer (annulable : Y rejoue) |
|                                   | N / P                            | niveau suivant / précédent |
| bouton 1                          | H ou ESC                         | menu (aide)                |
| manche haut/bas + bouton          | I/K + RETURN ou ESPACE           | choisir dans le menu       |
|                                   | G (ou menu)                      | choisir le niveau (grille) |
|                                   | C (menu)                         | alerte « case morte » oui/non |
|                                   | Q (menu)                         | quitter vers DOS           |

L'écran titre montre le nombre de niveaux résolus (toutes collections) et
celui où la partie reprend (`CONTINUE III:056`). Tout en bas, un petit entrepôt
animé montre le joueur poussant une caisse sur sa cible, sans son, à raison
d'un pas toutes les ~0,8 s. Le texte utilise un espacement régulier de 8 pixels.
N'importe quelle touche ou bouton lance la partie ; H l'ouvre sur l'aide,
G sur la grille des niveaux.
Sur l'écran de succès : n'importe quelle touche ou bouton.
Après 10 s sans touche ni bouton sur l'écran titre, une démo sonore joue sept
niveaux de Microban (1, 3, 12, 23, puis 60, 84 et 98, nettement plus difficiles)
avec leurs solutions, puis revient au titre ; une touche ou un bouton
l'interrompt. La démo n'enregistre rien.
Ctrl-RESET quitte aussi proprement vers DOS (page zéro restaurée).

Le HUD occupe les quatre coins (3 cases chacun, 4 en bas à gauche) : coups
en haut à gauche, poussées en haut à droite, niveau en bas à gauche
(collection et numéro d'origine : `I:067` est le 67ᵉ niveau de Microban,
`III:056` le 56ᵉ de Microban III), record en bas à droite une fois le niveau
résolu (`B:0033`).

Les records (coups, puis poussées) sont gardés sur la disquette, dans
`SOKOSAVE`, réécrit après chaque niveau résolu ; au démarrage, le jeu
reprend au premier niveau non résolu. Sur une disquette protégée en écriture,
on joue sans sauvegarde. Le fichier porte une empreinte de chaque collection
(niveaux gardés, ordre, contenu, rotation) : si une nouvelle version du jeu
change les niveaux d'une collection, ses records sont effacés plutôt
qu'attribués à d'autres niveaux ; ceux des autres collections restent. Dans la grille de choix (G), les niveaux résolus
sont soulignés en vert ; après le dernier niveau d'une collection, un écran
fait le bilan. L'historique garde les
1024 derniers coups ; au-delà, R recharge le niveau au lieu de le rembobiner.
Sons : un clic par pas, un bip aigu quand une caisse arrive sur une cible,
deux notes graves quand une caisse arrive sur une case morte (option C,
« DEADLOCK » : une case d'où aucune suite de poussées ne la mènera à une
cible, calculée au chargement du niveau),
un choc sourd quand le coup est impossible, une fanfare en fin de niveau.

Améliorations prévues : voir [`TODO.md`](TODO.md).

## Contenu

    src/sokoban.s              le jeu (ca65), BRUN à $6000
    src/bbfont_subset.inc      police du HUD (Beautiful Boot, sous-ensemble + F + - / ? .)
    src/hello.bas              HELLO : 10 PRINT CHR$(4);"BRUN SOKOBAN"
    levels/microban.xsb        Microban, David W. Skinner (source XSB, voir levels/README.md)
    levels/microban2.xsb       Microban II, idem
    levels/microban3.xsb       Microban III, idem
    levels/microban4.xsb       Microban IV, idem
    tools/sokoban_levels.py    XSB -> paquets de niveaux + tables ca65 (build/lv), démo
    tools/solver.py            solveur (A*, cases mortes, gel) ; même règle des cases mortes que le jeu
    tools/make_solutions.py    une solution vérifiée par niveau -> levels/solutions.txt
    tools/test_levels.py       joue les solutions dans le vrai jeu (a2run) : make test
    levels/solutions.txt       les 454 solutions (démo et tests)
    ../dist/SOKOBAN.dsk        l'image produite

Sur la disquette : `SOKOBAN` (le jeu), `MB1A` … `MB4B` (huit paquets de
niveaux, deux par collection, 4 Ko au plus, chargés par `BLOAD` en `$1000` quand on passe d'un
paquet à l'autre) et `SOKOSAVE` (la sauvegarde).

`tools/sokoban_levels.py` écarte les niveaux qui ne tiennent pas dans
20 × 12 cases ou dont aucun placement ne laisse les quatre coins du HUD hors
des murs, et écrit la liste dans `build/lv/report.txt`. Un niveau trop haut
qui tient couché est tourné d'un quart de tour horaire (le puzzle et sa
solution sont les mêmes, tournés ; le HUD garde le numéro d'origine) :
Microban 66, 109, 112, 143 ; Microban II 55, 86, 87, 91, 93, 100, 102, 104,
110, 119, 121 ; Microban III 22, 40 ; Microban IV 56, 70, 78, 88. Restent
écartés, pour Microban : 99, 101, 113, 154 et 155 ; pour Microban II : 66,
85, 114, 115, 120 (15 × 12 mais murs dans un coin du HUD), 125, 126 et 130 à
135 (de 18 × 17 à 47 × 41) ; pour Microban III : 23, 24, 33, 46, 47, 57, 58,
59, 101 ; pour Microban IV : 30, 39, 40, 42, 50, 58, 59, 60, 75, 85, 101,
102. Le quatrième carré du coin bas-gauche n'écarte aucun niveau de plus.
Un niveau est codé en plages d'un octet (type de case sur 3 bits, longueur
sur 5) : 6,6 Ko pour Microban, 5,8 Ko pour Microban II, 4,0 Ko pour III,
5,0 Ko pour IV.

## Différences avec l'original Apple-1 / GEN2

- Pas de V-blank sur un II+ : les tuiles sont dessinées directement (2-3 par coup).
- Lecture des deux paddles dans une seule boucle de durée fixe (6 ms), boutons
  détectés sur front, répétition du manche toutes les ~200 ms.
- Tuiles en couleur HGR (murs bleus, caisses orange, caisses placées et cibles
  vertes, joueur blanc avec un trait vert sous les pieds sur une cible) ; l'écran texte
  Apple-1 est remplacé par le menu HGR.
- Disposition `../dev` : binaire à `$6000` (config `dev/cc65/apple2_hgr.cfg`),
  au-dessus des deux pages HGR, zéro page en `$50` sauvegardée au démarrage
  et restaurée en quittant (`dev/lib/apple2/exit.asm`).
- Double tampon : les écrans complets (niveau, titre, aide, succès) sont
  dessinés sur la page HGR cachée puis affichés d'un coup ; pendant le jeu,
  les 2-3 tuiles d'un coup sont dessinées sur la page affichée.
- Les niveaux ne sont plus dans le binaire : ils sont lus par paquets sur la
  disquette, par des commandes DOS envoyées comme le ferait un programme
  BASIC (RETURN, Ctrl-D, commande, RETURN par `COUT`), la page zéro de DOS
  remise en place le temps de la commande.
