# MICRO-SOKOBAN — Apple II+ / DOS 3.3

Version 1.0 : [disquette et notes de publication](https://github.com/habib256/pom2games/releases/tag/1.0).

Port Apple II du sketch `sketchs/gen2/game_sokoban` de
[POM1](https://github.com/habib256/pom1) (HGR_Sokoban, VERHILLE Arnaud).
Le jeu tourne sur un Apple II+ 48 Ko (et tout modèle ultérieur), en HGR,
et se joue à la manette ou au clavier. Niveaux : **Microban I à IV**
de David W. Skinner, tous ceux qui tiennent à l'écran sans défilement, au
besoin couchés : 150 sur 155, 122 sur 135, 92 sur 101 et 90 sur 102, soit
454 niveaux (voir [`levels/README.md`](levels/README.md)).

    make            # -> ../dist/MICRO-SOKOBAN.dsk  (image DOS 3.3 5"1/4 amorçable)
    make run        # démarre l'image dans POM2 (profil Apple ][+)

Prérequis : cc65 (`brew install cc65`) et python3. L'image est écrite par
`tools/build_disk.py`, à partir de `../dev/tools/dos33.py`, qui prend les pistes système DOS 3.3 (pistes 0-2) dans
`../dev/tools/dos33_system.bin`. `make run` lance POM2 installé
(`/Applications/POM2.app`, ou `make run POM2=chemin/vers/POM2`).

## Commandes

| Manette                           | Clavier                          | Action                     |
|-----------------------------------|----------------------------------|----------------------------|
| manche (répétition auto)          | I J K L, W A S D, flèches        | déplacer / pousser         |
| bouton 0 (tapé)                   | U                                | annuler un coup            |
| bouton 0 maintenu + manche ← / →  | U / Y                            | annuler / rejouer (en continu) |
|                                   | R                                | recommencer (annulable : Y rejoue) |
|                                   | N / P (en partie)                | niveau suivant / précédent |
| bouton 1                          | ESC                              | sauvegarder la position et ouvrir le menu |
| manche haut/bas + bouton          | I/K + RETURN ou ESPACE           | choisir dans le menu       |
|                                   | G (ou menu)                      | choisir le niveau (grille) |
|                                   | V (accueil ou menu)               | choisir, créer ou renommer un profil |
|                                   | H (accueil, partie ou menu)       | HELP                       |
|                                   | F (menu)                         | Hall of Fame               |
|                                   | T (menu)                         | tutoriel de cinq niveaux   |
|                                   | O (menu)                         | options : sons, case morte, triche |
|                                   | Q (menu)                         | quitter vers DOS           |

L'écran titre montre les niveaux résolus et le niveau de reprise du profil actif.
Son nom apparaît en bas à gauche du mur inférieur ; la version **V1.1** apparaît
en bas à droite. Les deux textes blancs ont un fond noir et une marge
qui évitent les franges de couleur. Le couloir animé occupe toute la largeur :
un déplacement toutes les **~1,6 s**. Après au moins 15 s sans entrée, le jeu
attend que la caisse atteigne sa cible : l'animation se termine donc en environ
26 s, puis le **Hall of Fame est présenté pendant 10 s**, suivi de la démo.
Une touche ou un bouton interrompt le classement automatique ou la démo.
Les sept niveaux montrés sont Microban 1, 3, 12, 23, 60, 84 et 98 ; rien n'est
sauvegardé pendant cette présentation, silencieuse par défaut.

**MENU** (ESC ou bouton 1) regroupe PLAY / RESUME, TUTORIAL (5), PROFILES,
RESTART, GO TO LEVEL, OPTIONS, HALL OF FAME, HELP et QUIT TO DOS. Si CHEAT MODE
est activé, une dernière ligne SOLUTION joue la solution du niveau en cours,
sans l'enregistrer : la position d'avant le menu est restaurée.
GO TO LEVEL remplace les choix NEXT/PREV dans le menu. HELP présente le but du
jeu, les déplacements, Undo/Redo et le retour au menu. H ouvre directement HELP depuis l'accueil ou la partie ; quitter HELP ramène au menu.
Depuis l'accueil, on peut
consulter ces pages puis revenir à l'accueil sans commencer une partie.
ESC ou le bouton 1 revient ; RETURN ou le bouton 0 valide une sélection.

À la première partie de chaque profil, le jeu propose **cinq leçons très simples**,
avec des solutions de 2, 2, 5, 5 et 7 coups. Consignes et commandes sont affichées ;
le tutoriel ne participe pas au classement. Son achèvement est sauvegardé par profil.
T dans le menu permet de le rejouer ; G permet d'accéder directement à Microban.
Sur SUCCESS, une touche ou un bouton passe au niveau suivant.
QUIT TO DOS et Ctrl-RESET restaurent la page zéro et rechargent le programme
BASIC `HELLO` : `LIST` affiche le lanceur et `RUN` relance le jeu.

**Lisibilité : tout texte à taille normale est blanc. Seuls les titres agrandis
×2 peuvent être colorés**, conformément à la règle de [`lib/hgr`](../dev/lib/hgr/README.md).
L'espacement du texte compact est de 8 pixels.

Le HUD occupe les quatre coins (3 cases chacun, 4 en bas à gauche) : coups
en haut à gauche (`MOVES`), poussées en haut à droite (`PUSHES`),
niveau en bas à gauche (`LEVEL`)
(collection et numéro d'origine : `I:067` est le 67ᵉ niveau de Microban,
`III:056` le 56ᵉ de Microban III), record en bas à droite une fois le niveau
résolu (`B:0033`).

Le classement privilégie **le nombre de niveaux résolus**, puis **le plus petit
total de coups des meilleurs résultats** à égalité. Les points artificiels ont
disparu. Les totaux sont recalculés depuis les records ; une amélioration fait
baisser le total de coups. Ce départage reste dépendant des niveaux choisis :
ce n'est pas une comparaison à une solution optimale commune.

**PROFILES** permet de choisir parmi dix profils indépendants. Le profil initial
GIS peut être renommé. N crée un profil dans un emplacement libre ; R renomme le
profil sélectionné. Le trait à droite du nom identifie le profil actif. Les
initiales sont préremplies (nom sélectionné lors d'un renommage, dernières
initiales lors d'une création), puis modifiables au clavier ou à la manette.
RETURN/B0 valide, ESC/B1 annule ; deux profils ne peuvent pas porter le même nom.
Changer de profil recharge ses records et sa position sauvegardée, ou son premier
niveau non résolu en l’absence de position. Sélectionner le profil déjà actif
conserve la partie et son historique, sans lecture disque.

Après chaque niveau résolu, les records et le classement sont **enregistrés
automatiquement sous le profil actif**, sans nouvelle saisie d'initiales.
Le **Hall of Fame**, accessible par F dans le menu, affiche une ligne par profil :
initiales, total des coups sur huit chiffres et niveaux résolus, y compris les
profils sans niveau terminé.
Les lignes et en-têtes sont blancs ; seul le grand titre clignote lentement en
changeant de couleur. RETURN, ESC ou un bouton revient au menu.

`MICROHOF` contient le classement, les options, les dix noms et le profil actif
(120 octets, format `HOF3`). Les anciens classements HOF2 sont reconstruits une
fois depuis les records de chaque profil : noms, options et profil actif sont
conservés. HOF1 continue d'importer les records partagés dans le profil zéro.
Les autres profils ne reçoivent aucune progression fictive.

`MICROSAVE` conserve le profil zéro ; `MICROSAV1` à `MICROSAV9` les autres.
Les 1830 octets de records SOK2 restent compatibles ; une position de 134 octets
est ajoutée, soit 1964 octets par fichier. Le bit 7 de l'octet 4 marque le tutoriel
terminé. La position contient le plateau compacté, le joueur, les compteurs,
le niveau, son empreinte et un CRC-8. Une position invalide est ignorée.

**Reprise après extinction :** la position est enregistrée à l'ouverture du menu
ou de HELP, ainsi qu'après environ six secondes sans entrée lorsqu'elle a changé.
Après le redémarrage, PLAY retrouve les caisses, le joueur, les coups et les
poussées. Attendre la fin de « SAVING » avant d'éteindre ; ouvrir le menu permet
de déclencher cette sauvegarde immédiatement. Le tutoriel et la démo ne remplacent
pas la position Microban. **L'historique Undo/Redo reste en mémoire seulement** :
il repart vide après redémarrage ou changement de profil.

L'écran **SUCCESS** affiche un titre orange ×2, les coups et poussées alignés,
le nouveau record (ou le meilleur nombre de coups) et le nombre de niveaux résolus en blanc.

Les caisses hors cible sont remplies en orange ; les caisses sur cible ont
un cadre vert creux et une coche blanche. Leur forme les distingue aussi en
monochrome, où orange et vert ont la même teinte. L’accueil affiche le crédit
« APPLE II PORT BY » puis « VERHILLE ARNAUD » sur deux lignes blanches centrées.

Les records (coups, puis poussées) sont gardés sur la disquette, dans
le fichier du profil actif, mis à jour après chaque niveau résolu. Au démarrage,
le jeu reprend la position sauvegardée ou, à défaut, le premier niveau non résolu. Sur une disquette protégée en écriture,
on joue sans sauvegarde. Le fichier porte une empreinte de chaque collection
(niveaux gardés, ordre, contenu, rotation) : si une nouvelle version du jeu
change les niveaux d'une collection, ses records sont effacés plutôt
qu'attribués à d'autres niveaux ; ceux des autres collections restent. Dans la grille de choix (G), les niveaux résolus
sont soulignés en vert ; après le dernier niveau d'une collection, un écran
fait le bilan. L'historique garde les
1024 derniers coups ; au-delà, R recharge le niveau au lieu de le rembobiner.

**OPTIONS** (O dans le menu) regroupe quatre interrupteurs indépendants : son de
la partie, du menu, de la démo, et CHEAT MODE. Par défaut, la partie et le menu
sont sonores ; la démo et la triche sont éteintes. Haut/bas choisit le
réglage ; RETURN ou le bouton 0 change ON/OFF ; ESC ou le bouton 1 revient. Les
réglages sont sauvegardés sur la disquette. MENU SOUND active aussi une petite
musique calme sur la page de garde, sur le haut-parleur intégré de l'Apple II,
sans Mockingboard : boucle jazz zen, arpèges Dm9 / G13 / Cmaj9, basses graves
et rythme swing à environ 100 BPM. Les durées suivent une pulsation régulière,
avec de courtes respirations entre les trois mesures, en boucle pendant
l'animation.
Elle s'arrête en quittant l'accueil. L'option DEADLOCK active une alerte
sonore quand une caisse est poussée sur une case d'où elle ne peut plus atteindre
de cible. Elle ne bloque pas le déplacement ; C la bascule dans OPTIONS. CHEAT
MODE fait apparaître SOLUTION dans le menu. Les 454 solutions sont dans
`MICROSOL` (lecteur, index, puis coups compactés). Les cinq leçons aussi.

Sons pendant la partie : un clic par pas, un bip aigu quand une caisse arrive sur une cible,
deux notes graves quand une caisse arrive sur une case morte (dans OPTIONS,
« DEADLOCK » : une case d'où aucune suite de poussées ne la mènera à une
cible, calculée au chargement du niveau),
un choc sourd quand le coup est impossible, une fanfare en fin de niveau.

Améliorations prévues : voir [`TODO.md`](TODO.md).

## Contenu

    src/micro_sokoban.s        le jeu (ca65), exécuté à $6000
    src/unpack.s              petit chargeur à $0800, lecture RWTS et décompression
    src/fast_disk.inc         accès disque et cache des listes de secteurs
    src/resume.inc            sauvegarde et reprise de position
    src/beginner.inc           tutoriel et options
    src/score_hof.inc          records, classement et saisie des initiales
    src/profiles.inc           choix des profils et sauvegardes indépendantes
    apple2_micro_sokoban.cfg         mémoire 48 Ko (travail à $0800, MAXFILES 1)
    src/bbfont_subset.inc      police du HUD (Beautiful Boot, sous-ensemble + F + - / ? .)
    src/hello.bas              affiche LOADING MICRO-SOKOBAN, puis lance le chargeur
    tools/pack_program.py     compression LZ vérifiée par décompression indépendante
    tools/build_disk.py       disquette DOS et allocation adaptée aux lecteurs
    levels/tutorial.xsb        cinq niveaux d'initiation (originaux)
    levels/microban.xsb        Microban, David W. Skinner (source XSB, voir levels/README.md)
    levels/microban2.xsb       Microban II, idem
    levels/microban3.xsb       Microban III, idem
    levels/microban4.xsb       Microban IV, idem
    tools/micro_sokoban_levels.py    XSB -> paquets de niveaux + tables ca65 (build/lv), démo
    tools/solver.py            solveur (A*, cases mortes, gel) ; même règle des cases mortes que le jeu
    tools/make_solutions.py    une solution vérifiée par niveau -> levels/solutions.txt
    tools/test_tutorial_options.py  tutoriel, retour accueil et options persistantes
    tools/test_score.py        profils, classement, migration et sauvegarde
    tools/test_resume.py       reprise, profils, CRC et écritures limitées
    tools/test_menu_render.py  textes des options, y compris une adresse finissant par $FF
    tools/test_graphics.py     pages HGR visibles/cachées et retours des menus/solutions
    tools/test_exit.py         démarrage, QUIT/RESET, BASIC restauré et relances RUN (a2run/POM2)
    tools/bench_disk.py        mesure lectures et sauvegardes dans POM2
    tools/test_levels.py       joue les solutions dans le vrai jeu (a2run) : make test
    levels/solutions.txt       les 454 solutions (démo et tests)
    ../dist/MICRO-SOKOBAN.dsk        l'image produite

Sur la disquette : le chargeur `MICRO-SOKOBAN`, le programme comprimé `MICRODATA`, treize paquets de niveaux (`MB1A` à `MB1D`,
`MB2A` à `MB2C`, `MB3A` à `MB3C`, `MB4A` à `MB4C`), les dix fichiers de records,
`MICROHOF` et `MICROSOL` (les 454 solutions). Les paquets font au plus 2 Ko et sont chargés en `$1000` ; les
records et position actifs occupent `$1800` à `$1FAB`, sans réduire l'historique Undo de 1024 coups.

Le BASIC affiche **LOADING MICRO-SOKOBAN**, réserve un seul tampon DOS avec
`MAXFILES 1`, puis lance le petit chargeur. Celui-ci lit `MICRODATA` par secteurs
et décompresse le jeu à `$6000`. Sa carte de lecture est reconstruite avec l'image :
le chargeur et `MICRODATA` forment un ensemble, à ne pas déplacer séparément.

Pendant le jeu, les appels RWTS utilisent les routines disque de DOS 3.3.
Les emplacements des fichiers sont découverts dans le catalogue et mis en cache.
Les secteurs sont lus directement dans la page HGR cachée, puis copiés dans les
tampons du jeu. Une sauvegarde de position ne réécrit que son secteur ; un record
ne réécrit que les secteurs concernés. Le catalogue et la VTOC restent intacts.
Un classement ou des options inchangés ne provoquent aucune écriture.
Les anciens fichiers SOK2 de 1830 octets utilisent déjà les huit secteurs requis
et peuvent recevoir la position ; le lecteur refuse d'étendre un fichier au-delà
de ses secteurs alloués.

L'allocation est propre à ce jeu : ordre DOS optimisé pour le petit chargeur,
entrelacement physique de deux secteurs pour le programme comprimé et de trois
pour les fichiers du jeu. L'outil DOS partagé conserve ses comportements habituels.

Mesures avec `python3 micro-sokoban/tools/bench_disk.py` dans le moteur POM2 Apple II+ :

| Opération | Version précédente reconstruite | Version actuelle |
|---|---:|---:|
| Démarrage jusqu'à l'accueil prêt | 20,18 s | 13,98 s |
| Première lecture d'un profil | 3,60 s | 2,10 s |
| Première lecture d'un paquet | 3,54 s | 2,01 s |
| Records et classement après un niveau terminé | 7,40 s | 0,54 s |
| Sauvegarde d'une position | absente | 0,37 s |

Ce sont les cycles du processeur émulé, rotation et déplacements de tête Disk II
compris, pas le temps de calcul de l'hôte. Ces scénarios mesurés ne constituent
pas une mesure sur une machine physique. Les temps varient selon le fichier et
la position de la tête. Construire `dev/tools/a2shot` avant le benchmark ;
`--disk`, `--labels` et `--legacy` permettent de mesurer une ancienne construction.

`tools/micro_sokoban_levels.py` écarte les niveaux qui ne tiennent pas dans
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
- Disposition `../dev` : binaire à `$6000` (config `apple2_micro_sokoban.cfg`),
  au-dessus des deux pages HGR, zéro page en `$50` sauvegardée au démarrage
  et restaurée en quittant (`dev/lib/apple2/exit.asm`).
- Double tampon : les écrans complets (niveau, titre, aide, succès) sont
  dessinés sur la page HGR cachée puis affichés d'un coup ; pendant le jeu,
  les 2-3 tuiles d'un coup sont dessinées sur la page affichée.
- Les niveaux ne sont plus dans le binaire : ils sont lus par paquets sur la
  disquette, avec les routines RWTS de DOS, les listes de secteurs mises en cache et
  la page zéro du jeu préservée pendant chaque accès.
