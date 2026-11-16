# WARGALAGA II — plan de travail

Cible : Apple //e enhanced et //c, 128 Ko, 65C02, ProDOS, HGR double tampon
partout, 30 i/s NTSC (2 rafraîchissements par image ; 25 en PAL, jeu 17 %
plus lent, accepté), avec ou sans Mockingboard, clavier et manette (pas de
souris), disquette 140 Ko.
Raisons et carte mémoire : [README](README.md). Règles reprises de Warblade :
[docs/warblade-reference.md](docs/warblade-reference.md).

Modèle de projet : [CHROMABREAK](../chromabreak/README.md) pour l'amorce
ProDOS, `/RAM`, la cadence //e et //c, la manette lue dans l'attente ; [DIRTBIKE](../dirtbike/README.md) pour le modèle Python oracle
au bit près, le rendu « ne réécrire que ce qui change » et les lots.
Seuil de performance : un gain mesuré de 5 % mérite d'être fait.

Légende : `[lib]` = à ajouter ou modifier dans `dev/lib` (partagé, avec son
test dans `dev/tests` et sa ligne dans le README de la lib) ; `[jeu]` =
propre au jeu, dans `wargalagaii/src` ou `tools`.

Ce qui est fait (lots 0 à 11, chasses aux bugs, demandes du 2026-10-23 au 2026-10-30) : voir [CHANGELOG.md](CHANGELOG.md).

## Contenu

### Lot 3 — reste

- [ ] Conversion décimale hors BCD : pas encore utile (boutique, records).

### Lot 6 — plan d'origine

Plan d'origine :

- [ ] `[jeu]` `tools/levels.py` → 25 paquets de 4 niveaux (vagues,
      trajectoires, cadence de tir, dessin d'alien du paquet), 4e niveau
      bonus / kamikaze en alternance, boss aux niveaux 25/50/75/100, boucle
      en miroir et plus rapide après le 100.
- [ ] Réserve en mémoire aux : `WG2.AUX` chargé une fois au démarrage
      (dessins × teintes, trajectoires, musiques) ; copie du paquet
      courant en `$1000-$1FFF` par `AUXMOVE` (`$C311`) pendant la
      « téléportation ». Compression LZ4FH si besoin
      (`dev/lib/apple2/lz4fh.asm`, outil `$(FHPACK)` de `dev/cc65/fhpack.mk`).
- [ ] Boss : sprite composé (32×24 ou plus), points faibles, tirs en
      rosace (table d'angles, comme le super boss du TMS Galaga).
- [ ] Hurry-up : vaisseau qui passe si le niveau traîne.
- **Accepté si** : un pilote automatique (`tools/autopilot.py`, modèle)
  finit les niveaux 1, 25 et 100 ; bench du pire niveau dans le budget.

### Lot 7 — plan d'origine

Plan d'origine :

- [ ] Boutique après chaque paquet si ≥ 50 crédits : ~12 objets
      (vitesse, tir supplémentaire, double/triple, tir automatique, armure,
      vie, temps, marque de rang, 2-3 armes), prix d'après la référence ;
      écran fixe **HGR**, routines lentes permises (texte, chiffres, cadres) ;
      flèches + RETURN, ou manette haut/bas + bouton 0.
      Overlay chargé à `$4000` comme le `ENDING` de CHROMABREAK (hors jeu).
- [ ] Rangs : 6 marques de couleur ; les 6 réunies → rang supérieur à la
      sortie de la boutique ; marque sombre : rang inférieur.

### Lot 8 — plan d'origine

Plan d'origine :

- [ ] Meteor Storm : astéroïdes qui descendent, tir = accélérer (on
      ralentit plus vite qu'on accélère), jauge de vitesse et de distance,
      choc = retour au jeu sans perte de vie, prime selon la vitesse.
      Mêmes sprites et même cadence que le jeu.
- [ ] Memory Station : grille de paires, temps = jauge T, grille plus grande
      à chaque réussite (+25 000), pavillon pirate = fin. Écran fixe HGR,
      curseur au clavier ou à la manette.

## Écarts à valider

### Lot 6

- **Écarts à valider** :
  - **Musique à 25 Hz** (`MUS_HZ` de `tools/sound.py`, le `SPEED` du
    morceau suit) au lieu des 50 Hz usuels du PT3 : moitié moins de CPU.
    Images en retard, joueur normal, 600 images : niveau 97 — sans carte
    96, PT3 50 Hz 206, 25 Hz 140 ; niveau 100 — 56 / 182 / 113 ; niveau 1
    (vagues d'entrée) — 78 / 114 / 104. Un module PT3 du commerce (50 Hz)
    jouerait à mi-tempo : remettre `MUS_HZ = 50` pour en jouer un.
  - Pire niveau **hors budget** : bench « tricheur » (10 tirs triples,
    autofire) 4 à 10 % d'images en retard sans carte, 6 à 22 % avec ; pics
    à 36 000 cycles de rendu (plongeurs en EOR). La vitesse du jeu reste
    exacte (logique par paires de rafraîchissements), seule la fluidité
    baisse. Seuils de `test-long` : 15 % / 28 % (la scène est chaotique :
    46 à 76 images en retard sur ~570 au niveau 97 selon le départ).
  - Boss en sauts de 7 cases (pas de déplacement fluide) ; étoiles 16 au
    lieu de 24, 7 plongeurs au plus, balancement tous les 3 pas.

### Lot 7

- **Écarts à valider** :
  - 10 objets au lieu de ~12 : pas d'armes nouvelles (le jeu en a trois :
    simple, double, triple ; Quad, Plasma, lasers… demanderaient d'autres
    tirs) ; EXTRA TIME, RANK MARKER, LESS SPEED gardés.
  - AUTO FIRE achète le tir automatique pour la durée maximale de la
    jauge T (90 s), pas pour toujours.
  - Le rang n'a pas encore d'effet en jeu : affiché en boutique, à garder
    dans les records (lot 9).

### Lot 8

- **Écarts à valider** :
  - Pas de gemmes à part : la tempête sème des pièces (10 à 200).
  - Le crâne termine la station dès qu'il est retourné (le pavillon de
    Warblade) ; ESC permet aussi de sortir.
  - Le temps de la station se compte **par grille** (pas pour toute la
    station).

### Lot 9

- **Écarts à valider** :
  - Titre en HGR (pas de DHGR, décision 1) et texte du menu en anglais,
    comme le jeu.
  - La démo n'a pas d'entrées scriptées à la main : c'est l'autopilote
    (tir continu, aucune vie perdue sur la minute).
  - ESC en jeu ramène au titre (pas de pause) ; un record peut s'y faire.
  - `HIGHSCORES` est lu une fois, réécrit après un record, ou en quittant
    le titre si la manette a changé (pas à chaque appui sur J).

### Lot 10

- Écarts : le boss avance lentement (une cellule tous les 8 pas : chaque
  déplacement coûte ~5 600 cycles) ; la démo dure 2 550 pas ; la mémoire
  principale est pleine (~10 octets), LOWM à 16 octets près.

### Lot 11

- Écarts à valider : pas de gemmes ni de Gem Drop ; billet de 250 → pièce
  de 200 ; primes en points divisées (score à 6 chiffres) ; EXTRA couvre
  0-94 % (le wiki ne dit rien de 76-94) ; pourcentage affiché en haut, pas
  sous la jauge ; pas de bonus Random ; 3 tailles × 2 images de rochers,
  orange, au lieu de 49 dessins.

### Modes et tirs blancs

- Écarts à valider : une seule table de records pour tous les modes (Warblade
  en a une par mode) ; le mode n'est pas affiché en jeu ; les disques déjà
  joués repartent en EASY seul.

## Performance et lib

### Lot 2 — reste

- **Reste / à surveiller** :
  - Phase d'entrée : jusqu'à ~16 aliens volent ; en NTSC 3 images en
    retard (sur ~1 600) quand une vague arrive pendant que la précédente
    se pose, la vitesse du jeu restant exacte (prévu par le README). PAL :
    aucune.
  - Le pire cas avec 10 tirs (28 000 + logique 3 400) dépasse les 28 060
    qui gardent 6 000 cycles pour la musique sous IRQ (lot 4). Pistes :
    sauter les colonnes d'octets vides selon le décalage, étoiles moins
    chères (~2 300 cycles, ~1 500 prévus), données d'alien à adresse fixe
    (copie du paquet en `$1000`, lot 6) pour un `LDA abs,X`.
  - Promouvoir les routines en `[lib]` `dev/lib/hgr/` une fois stables.

## Mémoire

- Réserves restantes : ZP `$BB-$CF`, `$F0-$FF` ; `TXT6` (~77) et `TXT7`
  (120) ; aux `$0200-$1FDF`, `$BB00-$BFFF`, carte langage aux, fins de zones
  de `WG2.AUX` (voir README, Mémoire).

## À vérifier sur machine

Reste :

- [ ] Validation sur vraies machines (//e enhanced + Mockingboard, //c),
      selon `dev/lib/HARDWARE.md`.

- [ ] //c + Mockingboard 4c : la détection réveille la carte à `$C403` et
      peut masquer la ROM souris du slot 4. L'interruption VBL du firmware
      souris (notre horloge //c) reste-t-elle utilisable ? Sinon : horloge par
      le timer T1 de la VIA (régulière, pas calée sur le VBL : déchirure
      possible à la bascule de page).

### Chasse aux bugs (2026-10-23) — points ouverts

  - **Ouvert, risque faible** : sur //c, `LDA $C070` (manette) acquitte
    aussi le VBL ; une interruption arrivant pendant cet accès peut être
    perdue (une image en retard) ou, en théorie, laisser ProDOS face à une
    IRQ non réclamée. Non observé en 3 200 rafraîchissements ; à vérifier
    sur machine (comme pour CHROMABREAK).
  - **Non testé** : //c avec Mockingboard 4c (deux gestionnaires d'IRQ,
    souris + VIA) : a2shot n'a pas de //c, la sonde n'a pas de carte.

## Écueils connus du dépôt

- Clavier : lire `$C000` puis acquitter par `BIT $C010` ; sur //e la lecture
  de `$C010` rend aussi « touche tenue » en bit 7.
- `ldx #191 … dex / bpl` ne boucle jamais (191 > 127) : `cpx #$FF / bne`.
- Options des libs testées **par valeur** (`RWTS_SEI`, `DOS_SEI`,
  `MUL_INIT_BOOT`…) : `=0` équivaut à absent, mettre `=1` pour activer ;
  quelques-unes restent en `.ifdef` (lire l'en-tête du module).
- Libs assembleur gardées par `.ifref` : les inclure **à la fin** du source,
  après leurs appelants.
- Boucles à cycles comptés (haut-parleur, attente) : `.assert` qu'elles ne
  franchissent pas de page (DIRTBIKE : `tone` à cheval sur une page = notes
  20 % trop longues). Adresses figées des modules rapides (CHROMABREAK :
  `spare.s`) : quelques octets de décalage ont déjà coûté une image.
- Valeurs de départ : le CRT met la BSS à zéro, **pas `LOWBSS`**, que
  l'application initialise elle-même (`dev/lib/ABI.md`) ; une variable qui
  doit partir d'une valeur va en `DATA` (DIRTBIKE).
- Mémoire aux : avec `RAMRD` en aux, le code lui-même est lu en aux ; une
  boucle qui lit des données aux doit exister aux deux adresses
  (CHROMABREAK copie sa boucle de sprite dans les deux banques). Préférer
  `AUXMOVE` entre deux niveaux.
- IRQ : le gestionnaire ne touche ni la ZP cc65 ni sa pile, ni les
  commutateurs graphiques ; le firmware souris du //c envoie 60 IRQ/s
  (horloge VBL) ; la Mockingboard 4c se détecte avant de l'installer.
- `PREAD` ($FB1E) compte en boucle de 11 cycles : une IRQ au milieu
  (tick musique Mockingboard ~1 570 cycles) ajoute ~140 à la lecture. Le
  masquer (`php / sei … plp`) : la boutique dérivait vers le bas
  (2026-10-31, `sh_pread`, test « stick centred with the music »).
- `$C05E/$C05F` règlent la souris sur //c si IOUDIS n'est pas mis
  (CHROMABREAK) : ne pas toucher AN3 en HGR.
- POM2 relit la mémoire en fin d'image (« beam racing ») : une bascule de
  page trop rapprochée montre une page en cours de dessin
  (`dev/tools/a2shot/LETTRE_POM2_AFFICHAGE_MANETTE.md`).

## Décisions (questions closes le 2026-10-22)

1. HGR partout, écrans fixes compris ; DHGR plus tard.
2. PAL : le jeu va 17 % moins vite, comme CHROMABREAK ; pas de vitesses par
   seconde.
3. L'armure protège des tirs ennemis seulement ; une collision tue.
4. Disquette 140 Ko.
5. Sans Mockingboard : bruitages en jeu, musique hors jeu seulement.
6. Peu de dessins (6 petits, 2 gros, 1 boss) × 4 teintes HGR précalculées ;
   d'autres dessins plus tard.
7. Pas de souris comme entrée ; sur //c, son firmware sert seulement
   d'horloge VBL.
