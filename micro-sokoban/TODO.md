# MICRO-SOKOBAN — TODO

Améliorations proposées le 2026-09-15, révisées le 2026-09-30, par ordre
conseillé. Chaque étape se vérifie avec `../dev/tools/a2shot` ou
`../dev/tools/a2run` (captures, `peek`, `joy`/`btn` pour la manette, `dsk:`
pour relire la disquette après une sauvegarde) ; `tools/test_levels.py` résout
des niveaux et fait jouer les solutions au jeu.

État au moment de la rédaction (`src/micro_sokoban.s`) : annulation d'un seul coup
(`prev_player_row`, `undo_avail`) ; compteur de coups sur 8 bits plafonné à 255,
poussées non comptées ; victoire testée en parcourant les 240 cases à chaque
coup (`check_win`) ; aucune sauvegarde (chaque démarrage reprend au niveau 1) ;
niveaux parcourus seulement avec N/P ; après le 72ᵉ niveau, retour au niveau 1
sans écran de fin ; pas de sortie vers DOS ; un clic par pas et une routine
`beep` ; binaire chargé à `$4000`, sur la page HGR2 ; 72 niveaux Microban I en
RAM, `level_idx` sur 8 bits ; murs et caisses de la même couleur orange.

Contrainte fixe : **pas de défilement HGR**. Un niveau doit tenir entièrement
dans la grille de 20 × 12 tuiles de 14 × 16 pixels.

## 1. Lisibilité (bitmaps seulement)

- [x] **Murs bleus** : bit 7 à 1, pixels pairs allumés (`$D5,$AA` au lieu de
  `$AA,$D5`). Aujourd'hui, murs et caisses sont tous les deux orange et se
  confondent. Les caisses restent orange, les caisses placées vertes.
- [x] **Joueur sur une cible** (tuile 6) : silhouette blanche identique à
  la tuile 5, avec un trait vert sous les pieds. La silhouette toute verte
  a été remplacée à la demande de l'utilisateur le 2026-10-02.

## 2. Base technique

- [x] **Passer MICRO-SOKOBAN sur `../dev`**, comme les autres jeux : binaire à
  `$6000` (config `dev/cc65/apple2_hgr.cfg` ou dérivée) pour libérer HGR2,
  zéro-page en `$50+`, et `apple2.inc`, `kbd.asm`, `hgr.asm`, `exit.asm` à
  la place des équivalents locaux. Garder la lecture de la manette. À faire
  **avant** les étapes 3 à 5 : la carte mémoire change, et l'annulation, les
  paquets de niveaux et la sauvegarde en dépendent.
- [x] **Quitter vers DOS depuis le menu**, via `apple2_zp_save` /
  `apple2_exit` (page zéro restaurée, Ctrl-RESET protégé).
- [x] **Double tampon HGR1/HGR2** pour les changements d'écran (niveau, titre,
  aide, succès), comme Maze3D. Le rendu par tuiles modifiées pendant le jeu
  peut rester sur la page affichée.
- [x] **Commandes DOS depuis l'assembleur** (`dos_cmd`) : RETURN, Ctrl-D,
  commande, RETURN par `COUT` (`$FDED`), après `JSR $03EA` (crochets DOS).
  Notre page zéro est mise de côté et celle de DOS (l'instantané d'`exit.asm`)
  remise en place le temps de la commande. La sortie va dans la page texte
  `$400`, invisible en HGR plein écran. Elle sert au chargement des paquets
  de niveaux (étape 4) et à la sauvegarde (étape 5). Tout fichier lu par `BLOAD` doit exister sur la disquette dès
  la construction : un `FILE NOT FOUND` sans `ONERR` renvoie à l'invite BASIC.

## 3. Gameplay

- [x] **Annulation sur plusieurs coups** — fait autrement que prévu : un
  octet par coup (direction + « a poussé une caisse ») dans un anneau de
  1024 coups en LOWBSS, où 4 Ko sont libres depuis le passage sur `../dev` ;
  compacter à deux coups par octet ne gagnait rien. Au-delà de 1024 coups, les
  plus anciens sont oubliés. U / bouton 0 (tapé) annule.
- [x] **Rejouer (redo)** : le sommet de l'anneau est gardé après une
  annulation tant qu'aucun nouveau coup n'est joué. Y au clavier ; à la
  manette, bouton 0 maintenu + manche à gauche / à droite = annuler / rejouer
  en continu (un bouton 0 tapé sans manche annule, au relâchement).
- [x] **Compteurs complets** : coups sur 16 bits et compteur de poussées
  affiché dans le HUD. Les deux reculent avec l'annulation.
- [x] **Compteur de caisses restantes** (`boxes_left`) : initialisé par
  `init_level`, mis à jour par `execute_move` / `execute_undo`. Il remplace
  le parcours de `check_win` (non affiché : le HUD garde ses quatre coins
  pour coups, poussées, niveau et, plus tard, le record).
- [x] **Recommencer (R) sans perte irréversible** : R rembobine le niveau
  par l'historique, sans dessin ni son, puis Y rejoue tout. Si l'anneau a
  oublié le début (plus de 1024 coups), R recharge le niveau.
- [x] **Cases mortes** : testé au moment de la poussée (pas de table) : une
  caisse posée hors cible avec un mur au-dessus ou en dessous ET à gauche ou
  à droite est bloquée pour toujours. Deux notes graves ; option C dans le
  menu (« CORNERS: ON/OFF »). Détection volontairement partielle : elle ne
  voit pas les blocages le long d'un mur ni entre deux caisses.
- [x] **Cases mortes calculées** (2026-10-02) : `find_dead`, à la fin
  d'`init_level`, tire une caisse fictive depuis chaque cible (parcours en
  largeur, file de 240 octets) ; une case jamais atteinte est morte
  (`dead_tbl`). Couvre les coins et les bords de mur sans cible. L'alerte
  (deux notes graves, option C renommée « DEADLOCK ON/OFF ») consulte la
  table. Même règle que `tools/solver.py` (`Level.live`) : les tables du
  jeu et du Python sont identiques sur les 272 niveaux (a2run, `peek`).
  Restent invisibles les blocages entre caisses (gel 2 × 2…), que seul le
  solveur détecte.

## 4. Niveaux : Microban I et II complets

- [x] **Outil de conversion dans ce dépôt** : `tools/micro_sokoban_levels.py`
  (XSB → paquets + `build/lv/levels.inc` + `build/lv/report.txt`).
- [x] **Intégrer Microban I** (155 niveaux, `levels/microban.xsb`, copie
  verbatim de la source notée dans `levels/README.md`), numéros d'origine
  gardés (HUD `I:067`, rapport).
- [x] **Microban II** (135 niveaux) : `levels/microban2.xsb`, copie verbatim
  depuis GitHub (`OMerkel/Sokoban`), recoupée avec une seconde copie
  indépendante (voir `levels/README.md`). 111 niveaux gardés, 24 écartés (122
  et 13 avec la rotation, plus bas) ; paquets `MB2A` (4 Ko) et `MB2B`,
  `MICROSAVE` passe à 1034 octets (1094 avec la rotation), 409 secteurs libres
  (405 avec la rotation) sur la disquette. `test_levels.py --coll 2` joue la
  collection II.
- [x] **Rotation des niveaux trop hauts** : un niveau qui ne tient pas debout
  mais tient couché (9 × 13 → 13 × 9) est tourné d'un quart de tour horaire
  par `micro_sokoban_levels.py` (`fit`, `rotate`), et listé dans le rapport.
  Microban : 150 gardés (4 couchés : 66, 109, 112, 143) ; Microban II : 122
  (11 couchés : 55, 86, 87, 91, 93, 100, 102, 104, 110, 119, 121). 272
  niveaux en tout. `test_levels.py` prend les niveaux tels que le jeu les
  dessine (`kept_levels`).
- [x] **Retirer les niveaux trop grands** (pas de défilement) : l'outil
  écarte, après recadrage sur les murs, tout niveau de plus de 20 × 12, ou
  sans placement qui laisse les quatre coins du HUD (3 cases chacun, lignes 0
  et 11) hors des murs ; le placement le plus centré gagne. Pas de rotation à
  l'époque. Microban : 146 gardés, 9 écartés (66, 99, 101, 109, 112, 113, 143,
  154, 155, tous trop hauts ou trop larges ; 150 et 5 avec la rotation). La
  limite `w*h ≤ 255` a disparu avec `LEVEL_BUF` : les plages sont décodées
  directement dans la grille.
- [x] **Chargement par paquets depuis la disquette** : paquets de 4 Ko au
  plus (`MB1A` 101 niveaux, `MB1B` 45), `BLOAD` en `$1000` (LOWBSS) quand le
  jeu passe dans un autre paquet ; « LOADING » s'affiche pendant les ~3 s de
  lecture, et le premier paquet est lu sous l'écran titre. Codage : une plage
  par octet (type sur 3 bits, longueur sur 5), 6,5 Ko pour Microban au lieu
  de 8,8 Ko avec l'ancien RLE ; le binaire passe de 8 à 5 Ko.
- [x] **Numérotation** : un niveau est un couple (collection, rang parmi les
  niveaux gardés) ; le HUD montre la collection et le numéro d'origine,
  l'écran titre le nombre de niveaux (généré).

## 5. Progression

- [x] **Choix direct du niveau** : G (ou « GO TO LEVEL » dans le menu)
  ouvre une grille de 10 × 8 numéros d'origine par page, niveaux résolus
  soulignés en vert, curseur en vidéo inverse ; manche / IJKL pour bouger
  (les pages suivent), N / P pour changer de collection, RETURN / bouton 0
  pour jouer, ESC / bouton 1 pour revenir. L'en-tête compte les niveaux
  résolus.
- [x] **Sauvegarde sur la disquette** : `MICROSAVE` (« SOK1 », dernier niveau
  résolu, puis coups et poussées du record de chaque niveau, 0 = non résolu ;
  590 octets pour 146 niveaux), créé vide par le `Makefile`, lu par `BLOAD`
  sous l'écran titre et réécrit par `BSAVE` après chaque niveau résolu
  (« SAVING » en bas à droite). Un record est battu avec moins de coups, ou
  autant de coups et moins de poussées. Au démarrage, le jeu reprend au
  premier niveau non résolu ; le HUD montre le record en bas à droite
  (`B:0033`) ; l'écran de succès donne coups, poussées et « NEW RECORD » ou le
  record en place. Disquette protégée en écriture : la sauvegarde est sautée
  (capteur du Disk II lu avant le `BSAVE`, slot 6), sinon DOS arrêterait le
  jeu sur WRITE PROTECTED.
- [x] **Écran de fin** après le dernier niveau d'une collection : « BRAVO »,
  niveaux résolus sur le total, sommes des records (coups, poussées), puis
  retour au premier niveau de la collection suivante (ou de la même).

- [x] **Sauvegarde liée aux niveaux** (« SOK2 ») : les records sont rangés
  par rang dans les niveaux gardés ; un changement de la liste (la rotation a
  fait passer Microban de 146 à 150 niveaux) les aurait attribués à d'autres
  niveaux. L'en-tête porte maintenant une empreinte CRC-16 par collection
  (numéros d'origine, ordre, données codées : cases, rotation, placement),
  calculée par `micro_sokoban_levels.py`. Au chargement, une collection dont
  l'empreinte diffère perd ses records, les autres les gardent ; un ancien
  « SOK1 » est effacé. `save_buf` est en fin de mémoire : un fichier plus
  long (version future avec plus de niveaux) déborde dans la RAM libre, pas
  dans le jeu. Vérifié dans a2run avec des sauvegardes fabriquées.

## 6. Sons

- [x] **Sons plus parlants** avec la routine `beep` existante : caisse posée
  sur une cible, niveau réussi, annulation, déplacement impossible, caisse
  sur une case morte.

## 7. Outils et démo (2026-10-02)

- [x] **Solveur de test** (`tools/solver.py`) : A* sur les poussées,
  estimation par affectation optimale caisses → cibles, cases mortes et gel
  (caisses bloquées sur les deux axes). 263 niveaux sur 272 ; les 9 autres
  viennent de YASS (`levels/README.md`). `tools/make_solutions.py` écrit
  `levels/solutions.txt` après rejeu ; `make test` joue les 272 solutions
  dans le jeu (~1 min), au lieu de 41 niveaux auparavant.
- [x] **Mode démo** : après 15 s sans touche ni bouton sur l'écran titre
  (`title_wait`), `run_demo` joue Microban 1, 3, 12 et
  23 avec leurs solutions (4 coups par octet dans `levels.inc`, 46 octets),
  ~0,15 s par coup, sans son, puis retour au titre et nouvelle attente. Une
  touche ou un bouton l'interrompt (le manche seul ne compte pas : débranché,
  il se lit comme tenu). Rien n'est enregistré ni écrit sur la disquette
  (vérifié : image identique après la démo) ; le niveau de reprise est
  restauré.
- [x] **Microban III et IV** : `levels/microban3.xsb` (101 niveaux) et
  `microban4.xsb` (102), copies verbatim depuis `OMerkel/Sokoban`, recoupées
  avec `rkirov/sokoban-ai` (ses quatre Microban sont identiques aux nôtres).
  92 et 90 niveaux gardés (2 et 4 couchés) : 454 en tout, huit paquets,
  `MICROSAVE` 1830 octets, 357 secteurs libres. Le coin bas-gauche du HUD
  passe à 4 cases pour « III:056 » (7 glyphes) ; cela n'écarte aucun niveau,
  ne déplace aucun niveau de I et II (empreintes inchangées : les records
  restent). Solutions : 421 par `solver.py`, 33 par YASS ; `make test` joue
  les 454 (~1 min 30).
- [x] **Écran titre** : « MICRO-SOKOBAN » en orange (pixels impairs, bit 7 : la
  couleur des caisses), bandeau de murs, couloir animé sur toute la largeur (le joueur
  pousse une caisse sur sa cible, sans son, tout en bas de l'écran,
  ~0,8 s par étape pendant `title_wait`), texte blanc à pas de 8 pixels,
  « KEY OR BUTTON » qui clignote,
  niveaux résolus sur 454 et niveau de reprise (`CONTINUE III:056`), lus
  dans `MICROSAVE`. « APPLE II » et « JOYSTICK OR IJKL » laissent la place
  (les commandes sont dans l'aide). Corrigés au passage : H sur le titre
  ouvre bien l'aide (il lançait seulement la partie) et « LOADING » ne
  reste plus affiché une fois le premier paquet lu.
- [x] **Démo étendue** : après les quatre niveaux d'introduction, Microban
  60, 84 et 98 (221, 287 et 371 coups, 46, 72 et 112 poussées). Sept niveaux
  en tout, toujours dans le premier paquet ; accueil silencieux, menu et démo silencieux par défaut (OPTIONS).
- [x] **Organisation des textes** : accueil avec progression, crédits et
  raccourcis regroupés ; HELP avec actions et commandes en deux colonnes,
  indication de sélection, puis options et raccourcis alignés. Même texte
  blanc à pas de 8 pixels, curseur et bascule DEADLOCK conservés.

- [x] **Score et Hall of Fame** : SCORE sur six chiffres en haut à droite,
  somme des meilleurs résultats par niveau (100 + bonus de 1000 moins les coups,
  plancher du bonus à zéro). Dix instantanés sous trois initiales, un meilleur
  score par nom, avec le nombre de niveaux résolus ; F dans HELP pour consulter.
  Saisie après un nouveau score admis au classement, dernières initiales préremplies
  et modifiables. Classement séparé dans MICROHOF, compatible avec MICROSAVE.
  Couleurs HGR alternées et titre clignotant lentement ; tests de progression,
  bonus, classement, total maximal, rechargement et protection en écriture.
- [x] **Présentation** : titre MICRO-SOKOBAN centré, murs bleus sur les deux
  côtés de l'accueil et de HELP, bloc MENU compact avec repère vert. Compteurs
  MOVES et LEVELS en toutes lettres ; LOADING décalé de deux octets vers la gauche.

- [x] **Initiation et options** : cinq niveaux originaux de 2, 2, 5, 5 et
  7 coups, avec consignes. Tutoriel proposé à la première partie et rejouable
  par T ; achèvement sauvegardé, aucun point attribué. OPTIONS (O) regroupe
  le son de la partie, du menu, de la démo et DEADLOCK. Son du menu et de la
  démo désactivés par défaut, réglages enregistrés. HELP depuis l'accueil
  revient à l'accueil par ESC ou le bouton 1 sans commencer une partie.
- [x] **Renommage complet** : dossier micro-sokoban, source micro_sokoban.s,
  convertisseur micro_sokoban_levels.py, programme DOS MICRO-SOKOBAN et
  disquette MICRO-SOKOBAN.dsk ; MICROSAVE et MICROHOF, documentation et CI.
- [x] **Écran SUCCESS** : titre orange, murs bleus, statistiques compactes alignées,
  nouveau record vert et score total. Le tutoriel n'affiche pas de record de partie.
- [x] **Tutoriel identifiable** : rappel vert sur l'accueil, entrée verte
  TUTORIAL (5) dans HELP ; cinq leçons sans score, distinctes des collections Microban.


## 8. Profils, menu unique et lisibilité (2026-10-02)

- [x] Dix profils indépendants, choix/création/renommage, nom actif dans le mur
  inférieur avec un cadre noir élargi. Initiales modifiables et uniques ; scores
  enregistrés automatiquement. MICROHOF devient HOF2 (120 octets), avec une ligne
  par profil ; dix fichiers SOK2 préalloués, tutoriel enregistré par profil.
- [x] Menu unique avec profils, options, niveaux, classement et HELP ; NEXT/PREV
  retirés du menu. HELP réorganisé en déplacements, Undo/Redo et menu.
- [x] ESC ouvre le menu ; H ouvre directement HELP depuis l'accueil ou la partie.
  Quitter HELP ramène au menu sans démarrer ni recommencer la partie.
- [x] Animation ralentie à ~1,6 s par étape. L'accueil attend que la caisse soit
  sur la cible, puis affiche le Hall of Fame dix secondes avant la démo.
- [x] Règle impérative inscrite dans lib/hgr et lib/hgrc : petit texte blanc,
  couleur réservée aux titres ×2. Remplace les anciennes couleurs de petit texte.
- [x] Paquets de 2 Ko et records actifs en mémoire basse ; historique de 1024 coups
  conservé. Allocation DOS optimisée et mesurée : environ 29 % de gain au démarrage,
  20 % au chargement d'un profil et 22 % pour un paquet dans POM2.
- [x] Tests des 454 niveaux, cinq leçons, profils isolés, renommage, doublons,
  sauvegardes/rechargement, menu, options et présentation automatique du classement.


## 9. Classement, reprise et accès disque (2026-10-02)

- [x] Supprimer les points artificiels : niveaux résolus décroissants, puis total
  exact des meilleurs coups croissant. HOF3 conserve les dix profils et migre HOF2
  depuis leurs records ; totaux 32 bits, poussées rétablies dans le HUD.
- [x] Position par profil : plateau, joueur, compteurs, empreinte et CRC-8. Écriture
  au menu/HELP ou après six secondes sans entrée ; Undo/Redo restent en RAM.
- [x] BASIC : afficher « LOADING MICRO-SOKOBAN » et réserver un tampon DOS.
- [x] Chargeur léger, programme LZ et lecture par secteurs ; cache des listes T/S
  pendant le jeu et écritures limitées aux secteurs modifiés. Classement/options
  inchangés et sélection du profil actif ne provoquent plus d'accès inutiles.
- [x] Mesures POM2 : démarrage 20,18 → 13,98 s ; profil 3,60 → 2,10 s ; paquet
  3,54 → 2,01 s ; records et classement 7,40 → 0,54 s ; position seule 0,37 s.
- [x] Tests de redémarrage, isolation des positions, CRC, protection en écriture,
  migration de tous les profils, totaux au-delà de 24 bits et secteur unique.

- [x] Textes des options : marqueur de fin des tables sur deux octets, pour ne
  plus confondre une adresse de texte finissant par $FF avec la fin du menu.
  Comparaison des écrans depuis l’accueil et la partie, avec adresse $05FF forcée.


## 10. Affichage, crédit et musique d’accueil (2026-10-04)

- [ ] **Mode monochrome** : il ne s’affiche pas correctement. À investiguer
  (rendu des tuiles et des titres pensés pour la couleur HGR : pixels pairs
  ou impairs, bit 7).
- [ ] **Crédit de l’écran titre** : remplacer « PORT VERHILLE ARNAUD »
  (`title_author`) par « Apple II port by VERHILLE Arnaud ».
- [ ] **Musique d’accueil** : une petite musique calme et planante pendant
  la page de titre. L’animation du couloir et la démo restent silencieuses
  aujourd’hui.
