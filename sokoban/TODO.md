# Sokoban — TODO

Améliorations proposées le 2026-09-15, révisées le 2026-09-30, par ordre
conseillé. Chaque étape se vérifie avec `../dev/tools/a2shot` (captures,
`peek`, `joy`/`btn` pour la manette).

État au moment de la rédaction (`src/sokoban.s`) : annulation d'un seul coup
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
- [x] **Joueur vert sur une cible** (tuile 6) : même silhouette que la tuile 5,
  mais seulement les pixels impairs avec le bit 7 à 0 (vert), à la place du
  trait vert sous les pieds, qui se voit mal. Fait : silhouette redessinée
  sur la grille des pixels impairs, symétrique autour du pixel 6 (la
  silhouette blanche, centrée sur 5,5, ne se réduit pas proprement).

## 2. Base technique

- [x] **Passer Sokoban sur `../dev`**, comme les autres jeux : binaire à
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
- [ ] **Commandes DOS depuis l'assembleur** : une routine qui envoie
  `CHR$(4)` + commande + CR par `COUT` (`$FDED`), les crochets DOS restant en
  place. La sortie va dans la page texte `$400`, invisible en HGR plein écran.
  Elle sert au chargement des paquets de niveaux (étape 4) et à la sauvegarde
  (étape 5). Tout fichier lu par `BLOAD` doit exister sur la disquette dès
  la construction : un `FILE NOT FOUND` sans `ONERR` renvoie à l'invite BASIC.

## 3. Gameplay

- [ ] **Annulation sur plusieurs coups** : 3 bits par coup (direction +
  « a poussé une caisse »), deux coups par octet, soit 510 coups dans 256
  octets de BSS. Tampon **circulaire** : au-delà, les plus anciens coups sont
  oubliés au lieu de bloquer le jeu. U / bouton 0 remonte le tampon.
- [ ] **Rejouer (redo)** : garder le sommet du tampon après une annulation
  tant qu'aucun nouveau coup n'est joué. Nouvelle touche (par ex. Y), et
  bouton 0 + manche vers la droite à la manette.
- [ ] **Compteurs complets** : coups sur 16 bits et compteur de poussées
  affiché dans le HUD. Les deux reculent avec l'annulation.
- [ ] **Compteur de caisses restantes** (`boxes_left`) : initialisé par
  `init_level`, mis à jour par `execute_move` / `execute_undo`. Il remplace
  le parcours de `check_win` et peut s'afficher dans le HUD.
- [ ] **Recommencer (R) sans perte irréversible** : soit demander une
  confirmation, soit garder le tampon d'annulation pour pouvoir revenir en
  arrière après R.
- [ ] **Cases mortes** : à la fin de `init_level`, marquer les coins sans
  cible (une caisse y est bloquée pour toujours). Son grave quand une caisse y
  arrive ; option dans le menu. Détection volontairement partielle : elle ne
  voit pas les blocages le long d'un mur ni entre deux caisses.

## 4. Niveaux : Microban I et II complets

- [ ] **Outil de conversion dans ce dépôt** : `tools/sokoban_rle.py` n'existe
  que dans POM1. Le reprendre ici (`sokoban/tools/`), avec en entrée les
  fichiers texte des collections (format `.sok`/XSB standard). Il produit
  les fichiers `.inc` (ou les paquets binaires) et un rapport des niveaux
  écartés.
- [ ] **Intégrer tout Microban I (155 niveaux) et Microban II (135 niveaux)**
  de David W. Skinner, en conservant leur numérotation d'origine dans le
  rapport de conversion.
- [ ] **Retirer les niveaux trop grands** (pas de défilement). L'outil écarte
  tout niveau qui ne respecte pas, après recadrage sur ses murs :
  - largeur ≤ 20 et hauteur ≤ 12 tuiles ;
  - largeur × hauteur ≤ 255 (`load_level` calcule `w*h` sur 8 bits et
    `LEVEL_BUF` fait 256 octets), sauf à élargir ces deux points ;
  - aucune case non vide sous le HUD (ligne 0, colonnes 0-5 : `M:NNN` ;
    ligne 11, colonnes 16-19 : `L:NN`), en essayant les décalages possibles
    avant d'écarter le niveau, ou en déplaçant le HUD.
  Les niveaux carrés tournés de 90° ne sont pas une solution : garder les
  niveaux tels que publiés.
- [ ] **Chargement par paquets depuis la disquette** : environ 290 niveaux
  ne tiennent pas en RAM à côté du code (`$6000-$95FF`, environ 13,5 Ko).
  Un fichier binaire par paquet (par ex. `MB1A`, `MB1B`, `MB2A`…), chargé
  par `BLOAD` (étape 2) dans une zone fixe, avec en tête sa table de
  pointeurs.
- [ ] **Numérotation au-delà de 255** : `level_idx` passe à un couple
  (collection, numéro) ou à 16 bits ; le HUD affiche `I:NNN` / `II:NNN` (ou
  équivalent) au lieu de `L:NN`. Mettre à jour l'écran titre (`MICROBAN 72
  LEVELS`), le README et les crédits.

## 5. Progression

- [ ] **Choix direct du niveau** : écran de sélection par collection (grille
  paginée, manche ou flèches) ou saisie du numéro, au lieu de N/P un par un.
- [ ] **Sauvegarde sur la disquette** : niveaux résolus et meilleur score
  par niveau (coups, poussées) dans un fichier `SOKOSAVE`, écrit par `BSAVE`
  via la routine `COUT` de l'étape 2. Le fichier est créé vide par le
  `Makefile` (`dos33.py --bin SOKOSAVE=…`) pour que le premier `BLOAD` ne
  puisse pas échouer. Au démarrage, reprendre au premier niveau non résolu ;
  marquer les niveaux terminés dans l'écran de sélection ; afficher le
  record dans le HUD.
- [ ] **Écran de fin** après le dernier niveau de chaque collection, avec les
  totaux, au lieu du retour silencieux au niveau 1.

## 6. Sons

- [ ] **Sons plus parlants** avec la routine `beep` existante : caisse posée
  sur une cible, niveau réussi, annulation, déplacement impossible, caisse
  sur une case morte.
