# Sokoban — Apple II+ / DOS 3.3

Port Apple II du sketch `sketchs/gen2/game_sokoban` de
[POM1](https://github.com/habib256/pom1) (HGR_Sokoban, VERHILLE Arnaud).
Le jeu tourne sur un Apple II+ 48 Ko (et tout modèle ultérieur), en HGR,
et se joue à la manette ou au clavier. Niveaux : **Microban** de David W.
Skinner, tous ceux qui tiennent à l'écran sans défilement (146 sur 155 ;
Microban II s'ajoute dès que `levels/microban2.xsb` existe, voir
[`levels/README.md`](levels/README.md)).

    make            # -> dist/SOKOBAN.dsk  (image DOS 3.3 5"1/4 amorçable)
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
|                                   | C (menu)                         | alerte « coin mort » oui/non |
|                                   | Q (menu)                         | quitter vers DOS           |

Sur l'écran titre et l'écran de succès : n'importe quelle touche ou bouton.
Ctrl-RESET quitte aussi proprement vers DOS (page zéro restaurée).

Le HUD occupe les quatre coins (3 cases chacun) : coups en haut à gauche,
poussées en haut à droite, niveau en bas à gauche (collection et numéro
d'origine : `I:067` est le 67ᵉ niveau de Microban). L'historique garde les
1024 derniers coups ; au-delà, R recharge le niveau au lieu de le rembobiner.
Sons : un clic par pas, un bip aigu quand une caisse arrive sur une cible,
deux notes graves quand une caisse entre dans un coin sans cible (option C),
un choc sourd quand le coup est impossible, une fanfare en fin de niveau.

Améliorations prévues : voir [`TODO.md`](TODO.md).

## Contenu

    src/sokoban.s              le jeu (ca65), BRUN à $6000
    src/bbfont_subset.inc      police du HUD (Beautiful Boot, sous-ensemble + F + - / ? .)
    src/hello.bas              HELLO : 10 PRINT CHR$(4);"BRUN SOKOBAN"
    levels/microban.xsb        Microban, David W. Skinner (source XSB, voir levels/README.md)
    tools/sokoban_levels.py    XSB -> paquets de niveaux + tables ca65 (build/lv)
    dist/SOKOBAN.dsk           l'image produite

Sur la disquette : `SOKOBAN` (le jeu), `MB1A`, `MB1B` (les paquets de
niveaux, 4 Ko au plus, chargés par `BLOAD` en `$1000` quand on passe d'un
paquet à l'autre) et `SOKOSAVE` (la sauvegarde).

`tools/sokoban_levels.py` écarte les niveaux qui ne tiennent pas dans
20 × 12 cases ou dont aucun placement ne laisse les quatre coins du HUD hors
des murs, et écrit la liste dans `build/lv/report.txt`. Pour Microban :
niveaux 66, 99, 101, 109, 112, 113, 143, 154 et 155 (tous trop hauts ou trop
larges). Un niveau est codé en plages d'un octet (type de case sur 3 bits,
longueur sur 5) : 6,5 Ko pour les 146 niveaux, contre 8,8 Ko avec l'ancien
RLE sur l'ASCII.

## Différences avec l'original Apple-1 / GEN2

- Pas de V-blank sur un II+ : les tuiles sont dessinées directement (2-3 par coup).
- Lecture des deux paddles dans une seule boucle de durée fixe (6 ms), boutons
  détectés sur front, répétition du manche toutes les ~200 ms.
- Tuiles en couleur HGR (murs bleus, caisses orange, caisses placées et cibles
  vertes, joueur blanc, vert quand il est sur une cible) ; l'écran texte
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
