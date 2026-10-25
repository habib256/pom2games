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

## Lot 0 — préparation (fait, 2026-10-22)

- [x] Dossier, README (machine, mémoire, cadence, son, commandes), TODO.
- [x] Référence Warblade vérifiée, avec sources (`docs/warblade-reference.md`).
- [x] Recherche d'un « WarGalaga » existant : aucun ; POM1 a un TMS Galaga
      (TMS9918, sprites matériels), utile seulement pour les plongées.
- [x] `Makefile` squelette (inclut `apple2.mk`, ne construit rien).

## Lot 1 — V0.1 : démarrage, horloge, vaisseau, tir (fait, 2026-10-23)

Jeu en assembleur 65C02 (`src/game.s`, `src/timing.s`) derrière le crt0
ProDOS de cc65 ; `src/game.cfg` = `apple2_dhgr_prodos_c.cfg` + segment
`SYSBSS` en `$0200-$03CF` (tables `hgr_lo/hi`).

- [x] `src/boot.s` / `boot.cfg` : `WG2.SYSTEM`, refus d'un 6502 NMOS (test
      `INC A`), charge `WG2.SYS` ; `src/startup.s` le reloge à `$6000`.
- [x] Lien `crt0_prodos.s` + `none.lib`, libs `mli.s`, `video.s`, `mouse.s`,
      `apple2frame.s`.
- [x] `/RAM` réclamé (`PD_VIDEO_DISCARD_RAM`) puis reformaté à la sortie ;
      128 Ko vérifiés par MACHID (`$BF98`), sinon message.
- [x] HGR double tampon : `hgr_scanline_ram.asm` (`$0200`), pages par
      opérandes patchés (`hgr_pages.inc/.asm`), bascule `$C054/$C055`.
- [x] Horloge `src/timing.s` (dérivée de `chromabreak/src/timing.s`) : //e =
      fronts de `$C019` comptés par `timing_scan` (appelé entre les phases du
      dessin), //c = interruption VBL du firmware souris (mode 9, ProDOS
      `ALLOC_INTERRUPT`), sinon délais `a2_frame_wait`. Attente bornée, repli.
      Manette (paddle 0) lue dans l'attente, jusqu'à l'échéance.
- [x] Pas fixe : un pas logique par paire de rafraîchissements comptés entre
      deux bascules (`timing_refreshes`), reste reporté, au plus 2 pas par image.
- [x] 24 étoiles sur 3 vitesses, 1 point chacune ; effacées seulement si leur
      octet n'a pas changé, posées seulement sur un octet noir.
- [x] Vaisseau 7 cellules × 10 lignes, 7 prédécalages (`tools/sprites.py`),
      redessiné sur une page seulement s'il a bougé depuis cette page.
- [x] Clavier : ← → / J L (la direction tient tant qu'une touche est
      enfoncée, `$C010` bit 7, donc ESPACE ne l'arrête pas), ESPACE et Pomme
      ouverte / bouton 0 tirent (front). **TAB** bascule clavier / manette en
      attendant le menu du lot 9.
- [x] Tir simple, 5 au plus (jauge B de départ), listes d'effacement par page.
- [x] `tools/model.py` (oracle de la logique, commencé dès ce lot) et
      `tests/test_game.py` (`make test`, ~3 s).
- **Acceptation** (`make test`) : volume ; 1 000 images en 2 000
  rafraîchissements, aucune en retard, NTSC et PAL ; 300 pas identiques au
  modèle ; flèches, ESPACE, Pomme ouverte, manette ; ESC et Ctrl-RESET →
  texte, `/RAM` reconstruit, lanceur ProDOS ; II+ (NMOS) → message. Rendu
  mesuré : ~8 400 cycles avec vaisseau mobile, 5 tirs, 24 étoiles (budget
  28 060).
- [x] **//c dans la batterie** (2026-10-24) : la façade POM2 a reçu le //c
      (`Machine::AppleIIc`, livraison 0849ee51) ; `tests/iic_probe.cpp` y
      est porté (`dev/tools/a2shot/probe.hpp`) et ses 13 variantes tournent
      dans `make test` (~18 s), CI comprise. Reste la vraie machine.
- [x] `[lib]` `dev/lib/apple2c/apple2vbl.s` (2026-10-24) : l'horloge
      commune à `src/timing.s` et `chromabreak/src/timing.s` (choix du
      mode, interruption VBL de la souris //c, comptage des fronts //e,
      `A2_VBL_SCAN_SEI=1` ici) ; la bascule de page passe par un crochet,
      la présentation et la manette restent dans chaque jeu. Avec elle :
      `dev/lib/prodos/sysboot.s` (WG2.SYSTEM, octet pour octet) et
      `dev/lib/prodos/file.asm` (HIGHSCORES, dans l'overlay ; WG2.AUX garde
      son chargement résident : plus de place en mémoire principale).
      Coût : +46 octets de mémoire principale (horloge générique), d'où
      RODATA/DATA/BSS décalés de 46 octets ; `make test-iic` : //c
      identique (109 images en retard sur ~1 600 à l'entrée), //e 91 au
      lieu de 89 (manette 97 au lieu de 92), PAL 0. Pur effet
      d'alignement des tables : 46 octets de bourrage de plus (décalage 92)
      redonnent 89/92. Pas de bourrage gardé (≈120 octets libres).

## Lot 2 — V0.2 : sprites, formation, plongées (fait, 2026-10-23)

Code : `src/logic.s` (logique), `src/render.s` (dessin), `src/game.s`
(boucle, entrées, tables). Tables de lignes alignées en `$1000-$12FF`
(segment `ROWS`) : `hgr_hi+R,X` par ligne R du sprite, et `select_page`
ne réécrit que l'octet fort de chaque opérande (`HI_LDA`) ; `hgr_pages`
de la lib n'est plus utilisé (il réécrit les deux octets et ne gère pas
`+R`).

- [x] `tools/sprites.py` : dessins par cellules de 2 points, `X` = point de
      la teinte (violet, vert, bleu, orange), 7 prédécalages, entrée
      `2*décalage+image`. **6 petits aliens en 7×8 cellules** (8 lignes et
      non 10 : 20 % de moins par alien), 2 gros en 10×16, 2 images chacun ;
      `--png F` donne la planche de tous les dessins et teintes. Écrit à
      part de `dev/tools/assets/pack_hgr_sprites.py` (cellules et teintes
      propres au jeu) ; à rapprocher si un second jeu en a besoin.
      **Boss pas encore dessiné** (lot 6). Le jeu ne lie qu'un dessin et
      une teinte (`GAME_SMALL`) : la réserve en mémoire aux est au lot 6.
- [x] Dessin (`src/render.s`) : routines déroulées par macro
      (`SPRITE_ROWS`). Mesures (`make test`) : alien posé **STA 470**
      cycles, **EOR 593**, effacement **322** (objectifs 650 / 400 tenus).
      Changement de méthode en cours de lot : effacer en zéros ce qui vole
      abîmait la formation (redessin sur les deux pages : 47 000 cycles par
      image) ; **ce qui vole (plongeurs, aliens en entrée, tirs) est tracé
      et effacé en EOR**, dans l'ordre exactement inverse du tracé, ce qui
      rend l'écran tel quel sans rien redessiner. Formation posée en STA,
      vaisseau en STA. Tirs : un octet, motif identique sur 6 lignes.
- [x] Formation 5 × 8, respiration d'une cellule ; **une rangée tous les
      2 pas** (une par pas = 16 aliens redessinés par image, chaque
      changement étant tracé sur les deux pages). Une rangée inchangée
      depuis le dernier tracé de la page est sautée en quelques tests.
- [x] `tools/paths.py` : tortue (cap, vitesse, virage) échantillonnée à
      chaque pas, quantifiée en octets Δx (cellules) / Δy (lignes) signés
      4 bits, `$80` = fin ; 1 entrée (boucle) en miroir à droite, 4 plongées
      (demi-tour puis : dérive, zigzag, diagonale, boucle), en miroir sur la
      moitié droite de la formation.
- [x] Vagues : 5 vagues de 4 paires (une rangée chacune, du centre vers
      les bords), puis retour à la place ; plongée toutes les 20 pas si
      moins de 6 aliens volent ; sortie par le bas → retour par le haut.
      Hasard : `dev/lib/math/random.asm`.
- [x] `tools/model.py` : oracle au bit près ; `tests/test_game.py`
      compare **2 000 pas** à chaque pas (état complet + hasard).
- **Acceptation** (`make test`, ~8 s) : banc formation + plongeurs +
  **10 tirs** tirés sans arrêt : **0 image en retard sur 300** ; formation
  posée : 0 retard sur 1 000 images NTSC et PAL ; oracle vert. Profil
  (`tools/profile.py`) : rendu moyen 17 300 / pire 23 200 cycles sans tirs,
  22 000 / 28 000 avec 10 tirs ; logique ~3 000-3 600.
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

## Lot 3 — collisions, tirs ennemis, vies, score, HUD (fait, 2026-10-23)

- [x] Collisions en coordonnées logiques, sans lire l'écran. Tir contre
      aliens posés : `shot_frow` (ligne du tir → la seule rangée qu'il peut
      toucher) puis `col_of` (cellule → colonne), un test ; puis la liste
      des aliens en vol (`fly_list`, construite pendant la boucle des aliens,
      dans l'ordre du modèle). Bombe et alien contre le vaisseau : boîte
      réduite (cellules 1-5, lignes 2-9 du vaisseau). Premier touché
      seulement, ordre fixé par le modèle.
- [x] Bombes ennemies : 6 au plus, une tentative toutes les 12 pas par un
      alien au hasard (posé ou en plongée, visible, au-dessus de la ligne 150),
      4 lignes par pas, bleues, tracées en EOR comme les tirs.
- [x] Aliens touchés : état `ST_BOOM` 8 pas (explosion en 2 images, tracée
      comme un alien en vol), puis morts ; 50 points posés, 100 en vol.
- [x] Vaisseau : 3 vies ; touché → explosion (24 pas visibles), réapparition
      au centre au pas 45, 60 pas d'invulnérabilité (le vaisseau clignote).
      Armure (0 au départ, max 2 au lot 5/7) : absorbe une bombe et donne
      60 pas d'invulnérabilité ; une collision avec un alien tue quand même.
      Plus de vies : `GAME OVER` au milieu du champ ; après 2 s, ESPACE ou
      Pomme ouverte relancent une partie.
- [x] Score BCD 6 chiffres (`SED`), crédits BCD 4 chiffres (0 jusqu'au
      lot 5).
- [x] HUD (lignes 0-7) : score, vies, armure, jauges S et B en barres de
      segments, T, crédits. **Écart au plan** : pas de `hgr_hud8` ni de
      `hgr_text8` ; un caractère = une colonne d'octets de 8 lignes tracée
      par la même macro que les sprites (`glyph_sta`, ~230 cycles), police
      `bbfont` $20-$5F suivie de 4 glyphes du jeu. Le HUD n'est recalculé
      que si son état (8 octets) a changé depuis le dernier tracé de la
      page, et seuls les caractères qui diffèrent sont réécrits.
- [ ] Conversion décimale hors BCD : pas encore utile (boutique, records).
- **Acceptation** (`make test`, ~10 s) : oracle 2 000 pas avec collisions,
  3 vies perdues aux pas 455, 923 et 1602 identiques au modèle puis
  `GAME OVER` ; second oracle avec armure (1 500 pas) ; sans joueur :
  `GAME OVER`, 0 vie dans le HUD des deux pages, ESPACE relance ; banc
  (10 tirs qui traversent grâce au drapeau de test `nohit`, bombes) :
  0 image en retard sur 300.
- **À surveiller** : phase d'entrée, ~37 images en retard sur ~1 600 en
  NTSC (1 en PAL ; chiffre corrigé par la chasse aux bugs, ~45 sur //c), vitesse exacte ; logique ~3 200-4 600 cycles. Gain du
  lot : un alien posé qui change d'octet de départ ne fait plus effacer
  que la colonne qu'il quitte.

## Chasse aux bugs (2026-10-23, après le lot 3)

- [x] **Invariant d'écran** (`tests/test_screen.py`, dans `make test`) : la
      page que le 6502 vient de dessiner est comparée octet par octet à un
      dessin complet de l'état en Python (HUD, formation, GAME OVER,
      vaisseau, vols en EOR, tirs, bombes, étoiles). 5 graines × 210 images
      (jeu, bombes, explosions, fin de partie, relance) : identiques. Une
      mutation (bombes ôtées de la référence) est bien détectée.
- [x] **Écritures sauvages** (`storewatch` a2shot sur une partie avec fin et
      relance) : rien en page zéro hors jeu, `$0200-$0FFF`, `$1300-$1FFF`,
      RODATA, `$8F24-$BEFF`, page ProDOS `$BF00` ; dans le code, seules les
      72 opérandes de `select_page`.
- [x] **Fuzz logique** : 3 graines × 6 000 pas (armure 0, 1, 2) identiques
      au modèle.
- [x] **//c enfin exécutée** (`make test-iic`, optionnel : `tests/iic_probe.cpp`
      sur les sources POM2, comme le `test-mouse` de CHROMABREAK) : ROM
      //c 16 Ko et 32 Ko, NTSC et PAL, avec et sans manette (`$C070`
      acquitte aussi le VBL du //c) : horloge par IRQ, vitesse exacte,
      formation posée sans retard, ESC rend la main et l'IRQ. Pendant
      l'entrée : ~43 images en retard sur //c contre ~21 sur //e (coût des
      interruptions).
- [x] **Corrigé** : chaque nouvelle partie rejouait la même suite au hasard
      (graine fixe) ; la relance sème maintenant avec le compteur d'images.
      La première partie garde `SEED` (tests) ; le titre du lot 9 sèmera
      avec l'instant de la touche.
- Défauts de banc corrigés en route (pas du jeu) : `until:X` deux fois de
  suite n'avance pas ; une relance (effacement des deux pages, ~10
  rafraîchissements) dépassait une limite de 10 images.
- **Seconde passe** :
  - **Corrigé — fronts VBL manqués sur //e** : `timing_scan` doit passer au
    moins une fois par blanc (~4 550 cycles). `aliens_pass` (40 aliens
    quand plusieurs rangées changent) et les effacements de colonne du
    lot 3 tournaient jusqu'à ~6 200 cycles sans scruter : environ un
    rafraîchissement perdu pour 3 000, donc un jeu un peu plus lent et des
    images en retard **non comptées**. Scrutation ajoutée tous les
    8 aliens, après chaque colonne effacée, entre tirs et bombes, dans le
    message. Test permanent `vbl_edges` (chaque front compté ≤ 1,5
    rafraîchissement après le précédent, entrée et banc de 10 tirs).
    Conséquence : l'entrée NTSC montre maintenant ses vrais retards,
    **~37 images sur ~1 600** (21 avant : les fronts manqués en cachaient).
  - La page en cours de dessin n'est jamais affichée : 300 échantillons
    dans le rendu sur //e (a2shot) et sur //c / //e (sonde).
  - Ctrl-RESET avec l'IRQ VBL active sur //c : retour au lanceur ProDOS,
    horloge rendue (`iic32-reset`, `iie-reset` dans `make test-iic`).
  - Endurance : ~10 000 images de jeu au hasard (fin, relance, tous les
    aliens morts), invariant d'écran vérifié toutes les 25 images.
  - Manette en pleine phase d'entrée : répond en moins de 10
    rafraîchissements (la lecture coupée par l'échéance garde la valeur
    d'avant, sans gêne mesurable).
- **Troisième passe** (relecture indépendante de l'assembleur + chemins
  jamais exécutés) :
  - **Corrigé — effacements qui débordaient** : `render_init` et
    `game_init` effaçaient des pages entières (1 024 octets pour 773) et
    remettaient à zéro, derrière leurs variables, l'horloge (après une
    relance, la //e passait en délais ; la //c gardait son IRQ sans
    gestionnaire valide), `ram_unit` (`/RAM` jamais reformaté à la
    sortie) et la page zéro sauvée par le crt0 (restaurée à zéro en
    quittant). `zero_block` efface exactement N octets ; test : horloge,
    `/RAM` et page zéro intactes après une relance. Le test de sortie
    « /RAM reconstruit » passait à tort : il ne regardait que la liste
    des unités.
  - **Corrigé — repli sans horloge à 57 % de vitesse** : deux `WAIT(80)`
    en plus du dessin ; maintenant un `WAIT(60)` (88-101 %).
  - **Corrigé — lecture manette sans borne sur //c** : sans manette et
    sans interruption, `joy_read_irq` tournait pour toujours ; borne à
    255 comptes (17 cycles le compte, seuils recalés : 45 / 124 sur 165).
  - **Corrigé — amorce** : `WG2.SYS` introuvable bouclait pour toujours ;
    message, une touche, QUIT (paramètres dans la page relogée).
  - Testés désormais : 64 Ko (MACHID), volume sans `WG2.SYS`, interruption
    //c qui cesse (avec et sans manette), repli sans horloge.
  - **Ouvert, risque faible** : sur //c, `LDA $C070` (manette) acquitte
    aussi le VBL ; une interruption arrivant pendant cet accès peut être
    perdue (une image en retard) ou, en théorie, laisser ProDOS face à une
    IRQ non réclamée. Non observé en 3 200 rafraîchissements ; à vérifier
    sur machine (comme pour CHROMABREAK).
- **Quatrième passe** (après le lot 5 ; relecture indépendante de
  l'assembleur + tests) :
  - **Corrigé — les bonus ne tombaient presque jamais** : la sorte venait
    de l'octet faible d'un second tirage, qui n'est que le premier décalé
    d'un bit ; après le test « < 40 », seules les pièces et S sortaient
    (modèle et 6502 identiques : l'oracle ne pouvait pas le voir ; l'oracle
    `bonus_effects` pose les objets lui-même). La sorte vient maintenant de
    l'octet fort (uniforme à 3 %). Test : ≥ 15 sortes lâchées en 30 parties
    du modèle (5 avant).
  - **Corrigé — avec la Mockingboard, le haut-parleur jouait aussi** chaque
    bruitage. Test : aucune bascule de `$C030` avec la carte.
  - **Corrigé** : `objects_erase` sans `timing_scan` (6 objets + 6 bombes
    pouvaient dépasser un blanc) ; le son du tir partait sans tir (places
    toutes prises) ; le crâne « fin des bonus » épargnait bouclier et gel ;
    ×2 ramassé sous ×5 faisait redescendre à ×2 (on garde le plus fort).
  - **Garde ajoutée** : un objet lâché sous la ligne 184 serait dessiné
    dans la page zéro (vérifié en le forçant) ; les règles ne peuvent pas le
    produire (un tir ne touche rien sous la ligne 179) ; test permanent
    `model_invariants` (tout ce que la logique donne au dessin reste
    traçable, jauges dans leurs bornes).
  - Ctrl-RESET et ESC en pleine musique (IRQ T1 active sur //e) : retour au
    lanceur ProDOS, qui répond.
  - **Non testé** : //c avec Mockingboard 4c (deux gestionnaires d'IRQ,
    souris + VIA) : a2shot n'a pas de //c, la sonde n'a pas de carte.
- **Reste, hors lot 3** : quand les 40 aliens sont morts, rien ne se
  passe (niveaux suivants : lot 6). Les tampons de fichier ProDOS (lot 6)
  devront éviter `$1000-$12FF` (tables de lignes).

## Lot 4 — son : Mockingboard ou haut-parleur (fait, 2026-10-23)

`src/sound.s`, données `src/sound.inc` (`tools/sound.py`). `logic.s` ne fait
que lever des bits d'événement (`snd_ev` : tir, alien abattu, vaisseau
touché, armure, fin de partie), hors de l'état comparé au modèle.

- [x] Détection au démarrage (`mb_detect`), **avant** l'horloge //c ;
      `audio_slot` (0 = haut-parleur).
- [x] `[lib]` `mockingboard.asm` : option **`MB_FAST_WRITE = 1`** (opérandes
      absolues patchées par `mb_init`, ~55 cycles l'écriture au lieu de
      ~110) ; défaut 0 identique octet pour octet à l'ancien code ;
      `dev/tests/test_rgb_mockingboard.py` passe sur les deux variantes.
- [x] ~~Écart au plan — pas de PT3~~ : **PT3 fait au lot 6** (voir plus
      bas). Le format maison à deux voix du lot 4 a été retiré ; le morceau
      original en la mineur (`tools/sound.py`) est devenu un module PT3.
- [x] Musique sur **l'IRQ du timer 1 de la VIA à 60 Hz** (gestionnaire
      ProDOS `ALLOC_INTERRUPT`, `mus_irq`, page zéro propre `mptr`, `mb_chip`
      gardé) : les notes partent à l'heure quel que soit le nombre d'images
      par seconde, et au même tempo en PAL. Première version (avancée une
      fois par image) : chaque attaque tombait sur une frontière d'image et
      le rythme boitait avec la cadence — **entendu par l'utilisateur**
      (2026-10-23) ; test `tempo` (60 tics par seconde de processeur en
      entrée, formation posée et PAL). Puce 1 : musique (A mélodie, B basse,
      volume qui décroît) ; puce 2 : bruitages (voix A, son ou bruit), écrits
      par `sound_frame`. Registres écrits seulement s'ils changent.
- [x] Haut-parleur : bruitages seulement (pas de musique en jeu), joués
      **dans les boucles d'attente** de `timing.s` (//e : jusqu'au front VBL ;
      //c : jusqu'à la bascule par l'IRQ), un `STA $C030` toutes les
      `spk_period` tours de 63 cycles (les deux boucles ont la même durée :
      `spk_pad` sur //c). Jamais d'image retardée : sans temps libre, l'effet
      se tait. Bornes des attentes ramenées à 8 192 tours (~0,5 s) : le tour
      plus long avait porté le repli //c à ~4 s.
- [x] Priorités : mort > fin de partie > armure > alien abattu > tir ; un
      effet de même rang repart du début. **S** coupe / remet le son.
- [ ] Musique haut-parleur hors jeu (`duet.asm`) : pas d'écran hors jeu
      avant le lot 9 (titre, boutique).
- [ ] Silence AY avant un accès disque : pas d'accès disque en jeu avant le
      lot 6.
- **Acceptation** (`make test`, `tests/test_audio.py`) : haut-parleur — rien
  sans effet, un tir = des bascules, toutes dans les boucles d'attente,
  rien quand S coupe ; Mockingboard (a2shot `--mockingboard`, registres AY
  décodés des écritures VIA) — slot 4 trouvé, musique sur la puce 1
  (première note, mélodie qui avance), tir sur la puce 2, silence sur S et
  ESC, retour de la musique sur S ; cadence avec la carte : 1 000 images en
  2 000 rafraîchissements, aucune en retard. `make test-iic` : effets sur
  //c et //e, depuis les boucles d'attente seulement.
- **À surveiller** : entrée NTSC ~41-46 images en retard sur ~1 600 avec la
  carte (son ~1 100 cycles par image). Lot 6 : musique PT3, voir plus bas.

## Lot 5 — bonus et jauges (fait, 2026-10-23)

Logique : `tools/model.py` (sortes, poids, effets) → `tools/bonus.py` →
`src/bonus.inc` (constantes `K_*`, `drop_table`) ; 6502 : `drop`,
`pickups`, `take` (table de sauts) dans `src/logic.s`.

- [x] 32 sortes d'objets (≤ 6 à la fois, 2 lignes par pas) : pièces
      10/50/100/200 (crédits BCD, plafond 9999), S, B, T, armes simple
      (malus) / double / triple (tirs obliques ±1 cellule par pas), tir
      automatique (une salve tous les 4 pas, tir **tenu** : Pomme ouverte ou
      ESPACE gardé), armure, vie, crâne (au hasard : arme simple, S−1, B−1
      ou fin des bonus temporisés), lettres E-X-T-R-A (les 5 : une vie),
      ×2 / ×5 (sur le score), bouclier, gel (les aliens s'arrêtent et ne
      tirent plus ; les explosions continuent), 6 marques de rang + marque
      sombre (gardées pour le lot 7), icônes des 2 sous-jeux (gardées pour
      le lot 8).
- [x] Un alien abattu lâche un objet une fois sur ~6 (`DROP_RATE` 40/256),
      sorte tirée dans une table de 64 (poids dans `model.py`).
- [x] Jauges : S = vitesse (1..5 → 2..6 cellules par pas), B = tirs à
      l'écran (5..10), T = durée des bonus (30..90 s, 300 pas par cran) ; au
      maximum (et armure 2, 4 vies), l'icône rapporte 500 points (× le
      multiplicateur).
- [x] Objets dessinés sans prédécalage : ils tombent droit sur une colonne de
      14 points (2 octets) ; icône = une lettre de `bbfont` + une barre de la
      couleur de la catégorie (`tools/sprites.py`, 16 octets), EOR.
- [x] HUD : jauges S et B en 5 segments, T en secondes, crédits, lettres
      EXTRA ramassées (« - » sinon).
- **Acceptation** (`make test`) : nouvel oracle `bonus_effects` — chaque
  sorte tombe sur le vaisseau (posée à la fois dans le 6502 et le modèle),
  jauges poussées au maximum, EXTRA deux fois, crânes, armes, tir automatique,
  ×5, gel : 964 pas identiques au modèle, 32 sortes prises (77 ramassages) ;
  oracle au hasard avec tir tenu ; invariant d'écran avec objets (69
  échantillons sur 480).
- **À surveiller** : entrée NTSC ~44 images en retard sur ~1 600.

## Lot 6 — 100 niveaux, paquets, boss (fait, 2026-10-23)

Réalisé (modèle `tools/model.py` = oracle bit-exact, tables
`tools/bonus.py` → `src/bonus.inc`) :

- [x] Niveaux : sortes NORMAL / GROS / BONUS / KAMIKAZE / BOSS, paramètres
      par tables (`lv_*`) + saturation par boucle, téléportation de 60 pas
      avec « LEVEL n », boucle en miroir après le 100 ; `ESCAPE_Y = 224`.
- [x] `WG2.AUX` : 24 petites + 8 grosses tables d'aliens à aux `$2000`,
      chargées par blocs de 8 Ko (bitmap `$BF60-$BF63` libéré le temps du
      READ), `pack_check` copie le paquet courant en `$1000-$1FFF`.
- [x] Gros aliens (rang 0, cases paires, 2 PV, marque de rang) ; boss 16×24
      qui saute de 7 cases tous les 8 pas, cœur cases 4-11, rosace et bombe
      visée.
- [x] Hurry-up : un niveau normal ou gros qui dure plus de 1 800 pas (60 s)
      fait sortir une soucoupe en haut (y 10), 2 cases par pas, qui rebondit,
      hors d'atteinte, et lâche une bombe visée tous les 12 pas ; elle part
      à la fin du niveau. Testée : oracle bit-exact (niveau poussé à
      `level_t` = 1 740), invariant d'écran.
- [x] **PT3** (demandé en cours de lot) : lecteur de Vince Weaver
      (pt3_lib 0.5, 0BSD) en `[lib]` **`dev/lib/apple2/pt3/`** (sources
      inchangées + `pt3_zp.inc` relogeable + `pt3.s` : décodage seul, sans
      IRQ ni écriture carte). Morceau : `tools/pt3.py` écrit
      `build/song.pt3` depuis la mélodie et la basse de `tools/sound.py`
      (table 1, notes une octave plus haut : la Mockingboard à 1 MHz joue
      une octave et ~40 cents plus bas). Lecteur + morceau **en mémoire aux
      à `$6000`** (zone `AUXM` de `game.cfg`, `build/game.bin.mus` collé à
      `WG2.AUX` après les paquets) : la mémoire principale garde sa place
      pour les lots 7-9. L'IRQ du timer 1 y entre par des **trampolines à
      `$1FE0`** (mêmes octets en principal et en aux, RAMRD/RAMWRT) ; ZP du
      lecteur `$D0-$EF` (hors `$FA-$FF` de ProDOS). Puce 1 : registres
      écrits s'ils changent (R13 `$FF` = inchangé) ; puce 2 : bruitages.
      Le lecteur GROUiK d'A2FileCmd (signalé par l'utilisateur) a été
      écarté : 4,8 Ko + 613 octets, et son adaptation place moteur et
      morceau en aux `$2000/$4000` (nos paquets).
- [x] Tick ~1 450-2 400 cycles (moyenne 1 570) : l'IRQ fait un
      `timing_scan` à l'entrée et à la sortie, rendu **atomique** (`sei`)
      pour ne compter aucun front deux fois.
- [x] `make test-long` : pilote automatique (niveaux 1, 25, 100 finis avec
      3 vies) et pires niveaux (97, boss 25, boss 100) avec et sans carte.
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

## Chasse aux bugs 5 (2026-10-23, après le lot 6 et le PT3)

Relecture indépendante (sous-agent) + vérifications ; chaque bug a son test,
vérifié en échec avant le correctif.

- [x] **Haut-parleur ~13 % trop grave sur //e** (introduit par le PT3) :
      `timing_scan` atomique (`php/sei/plp`, +9 cycles) portait le tour de
      la boucle d'attente à 72 cycles, `SPK_TURN` restait à 63 et le //c
      (`spk_pad`) n'était plus pareil. `SPK_TURN = 72`, `spk_pad` +9 ; test
      de hauteur dans `test_audio.py` (demi-périodes = n × `SPK_TURN`).
- [x] **Manche faussé par la musique** (//e et //c avec carte) : un tick PT3
      au milieu du comptage du paddle arrêtait X mais pas le timer, lecture
      trop basse (à droite lu « gauche » ~1 image sur 15). La lecture est
      abandonnée si `mus_ticks` a bougé (pas de `sei` : sur //c il
      bloquerait la bascule). Test `joystick` avec la carte (droite,
      centre : valeurs constantes).
- [x] **Changement de paquet** : un seul `AUXMOVE` de 1 232 octets sous
      `sei`, ~50 000 cycles sans IRQ ni `timing_scan` : un tick de musique
      et des fronts VBL perdus à chaque paquet. `aux_fetch` copie 64 octets
      à la fois (`sei` par bloc, scan entre deux). Scène « level changes,
      Mockingboard » de `vbl_edges` (échoue avec des blocs de 255).
- [x] **Manche mort sans horloge vidéo** (délais : //c dont l'IRQ s'arrête,
      pas de firmware souris) : lu avant le WAIT (`joy_read_delay`, 17
      cycles par compte comme les autres boucles). Test `joystick_delay`.
- Vérifié sans défaut : IRQ et état mémoire (RAMRD/RAMWRT/ALTZP/80STORE),
  trampolines, ZP (crt0 sauve les 256 octets), taille de `WG2.AUX`, module
  PT3 (en-tête, motifs, samples, boucle), états partagés du son, soucoupe
  (ordre EOR/STA, y compris au-dessus des gros aliens), boss.

## Chasse aux bugs 6 (2026-10-23)

Seconde relecture indépendante (bornes, branches rares, modèle = 6502) ;
oracle long en boucles 1, 5, 250 et 255 (boss du 100) : identique.

- [x] **Les cadeaux du boss perdus** (règle du modèle aussi) : vie et pièce
      de 200 tombent de la ligne 32, la fin du niveau venait 40 pas après
      le boss et les effaçait à mi-chemin. Des objets qui tombent
      retiennent maintenant la fin. Test du modèle (vaisseau dessous : la
      vie prise), échoue sur l'ancien modèle.
- [x] **Gel (FREEZE) sur un niveau à gros aliens** : la boucle gelée ne
      listait pas les gros aliens posés, les tirs les traversaient (le
      modèle les touchait). Oracle « frozen big aliens » (gel au pas 140
      du niveau 3), échoue sans le correctif.
- [x] Gros alien qui se pose : absent de la liste des cibles ce pas-là
      (`home`), le modèle le comptait. Corrigé (`fly_add`).
- [x] « LEVEL n » juste jusqu'au bout : n sur 16 bits, 5 chiffres
      (message de 11 caractères, GAME OVER centré dedans) ; avant, les
      centaines valaient boucle mod 10 (faux après le niveau 1 000). Test
      `messages` (2 … 25 601).
- [x] La boucle sature à 255 (255 + 1 donnait 0 : le jeu redevenait
      facile) ; oracle « loop 255 » dans `make test-long`.
- [x] Le score s'arrête à 999 999 (il repassait à 0) ; test `score_cap`.
- [x] Plus de niveaux qui avancent derrière GAME OVER (bonus / kamikaze se
      vidaient seuls et chargeaient le paquet suivant).

## Lot 7 — boutique et rangs (fait, 2026-10-23)

Réalisé :

- [x] Règles dans le modèle (`ITEMS`, `buy`, `shop_exit`) et dans
      `logic.s` (`shop_room`, `shop_can`, `shop_buy`, `shop_exit`), tables
      par `tools/bonus.py` (prix BCD, noms). La boutique s'ouvre à la fin de
      la téléportation qui suit le 4e niveau de chaque paquet (4, 8 … 100)
      si l'on a ≥ 50 crédits ; la logique attend (`shop`), le niveau
      suivant vient à la sortie. Crochet de test `noshop` (fermée aussitôt,
      rien d'acheté) pour les scènes qui traversent une fin de paquet.
- [x] Écran (`src/shop.s`) : overlay lié pour `$4000` (zone `SHOPM`,
      `build/game.bin.shop`, 1,4 Ko avec le duet), rangé en fin de
      `WG2.AUX` (aux `$7000`) et copié sur la page 2 quand la boutique
      s'ouvre (page 1 affichée) : **pas d'accès disque en jeu**. Crédits,
      rang, 10 objets avec prix et « MAX » à la limite, jauges, marques
      (icônes du jeu), curseur ; ← ↑ / → ↓ déplacent, RETURN ou ESPACE
      achète (carillon ; refus : petit son), ESC ou LEAVE sort ; manette
      (mode TAB) : paddle 1 haut / bas, bouton 0.
- [x] Musique : Mockingboard, le PT3 continue ; **haut-parleur : le duet**
      (`dev/lib/apple2/duet.asm`, aligné sur une page dans l'overlay) joue
      la mélodie et la basse du jeu par tranches de 4 (~33 ms), une touche
      coupe la tranche (le point du lot 4 « musique haut-parleur hors jeu »
      est fait pour la boutique ; le titre au lot 9).
- [x] Rangs : 6 marques → rang + 1 à la sortie (marques remises à 0) ;
      marque sombre → rang − 1 ; RANK MARKER donne la première marque qui
      manque. Rang 0-99.
- [x] Tests (`tests/test_shop.py`, `make test`) : achats au clavier avec
      la carte (dont un refus), marque achetée → rang + 1 par LEAVE, marque
      sombre → rang − 1 par ESC, achats à la manette, musique haut-parleur
      (voix qui basculent, un événement toutes les 0,233 s, curseur qui
      répond), pas de boutique sous 50 crédits ; chaque état final ==
      modèle.
- **Écarts à valider** :
  - 10 objets au lieu de ~12 : pas d'armes nouvelles (le jeu en a trois :
    simple, double, triple ; Quad, Plasma, lasers… demanderaient d'autres
    tirs) ; EXTRA TIME, RANK MARKER, LESS SPEED gardés.
  - AUTO FIRE achète le tir automatique pour la durée maximale de la
    jauge T (90 s), pas pour toujours.
  - Le rang n'a pas encore d'effet en jeu : affiché en boutique, à garder
    dans les records (lot 9).

Plan d'origine :

- [ ] Boutique après chaque paquet si ≥ 50 crédits : ~12 objets
      (vitesse, tir supplémentaire, double/triple, tir automatique, armure,
      vie, temps, marque de rang, 2-3 armes), prix d'après la référence ;
      écran fixe **HGR**, routines lentes permises (texte, chiffres, cadres) ;
      flèches + RETURN, ou manette haut/bas + bouton 0.
      Overlay chargé à `$4000` comme le `ENDING` de CHROMABREAK (hors jeu).
- [ ] Rangs : 6 marques de couleur ; les 6 réunies → rang supérieur à la
      sortie de la boutique ; marque sombre : rang inférieur.

## Lot 8 — sous-jeux (fait, 2026-10-23)

Réalisé :

- [x] Entrée : l'icône attrapée (`subgame`) lance le sous-jeu **à la fin de
      la téléportation** qui suit le niveau ; ensuite la boutique (si c'est
      un 4e niveau et ≥ 50 crédits), puis le niveau suivant (`teleported`
      dans `logic.s` et le modèle).
- [x] **Meteor Storm** (`src/storm.s`, règles dans `storm_step` du modèle,
      oracle au pas près) : dans le moteur du jeu, mêmes sprites, même
      cadence. Les rochers sont des aliens (emplacements 0-11, état
      `ST_ROCK`), dessinés comme des aliens qui volent, avec un dessin de
      rocher (2 images, `WG2.AUX` après les gros aliens, copié dans
      `cur_alien` par `pack_check`). Tir tenu = plus vite (+1 par pas, 0-63),
      relâché = plus lent (−2 : on ralentit plus vite qu'on accélère) ; le
      champ descend de 2 + vitesse / 8 lignes par pas (rochers, pièces, et
      les étoiles en plus de leur propre vitesse). Un rocher ou une pièce
      toutes les 28 lignes ; 4 096 lignes à parcourir ; « METEOR STORM »
      pendant les 60 premiers pas. HUD propre : SPEED et DIST en 8 segments,
      crédits. Choc : le vaisseau explose, **aucune vie perdue**, fin quand
      l'explosion finit. Traversée : une prime selon le temps mis (par
      tranches de 128 pas, ~4 s : 32 000 → 2 000 points), multiplicateur
      compris. Puis téléportation (LEVEL n).
      Code **résident en `$0800-$0FFF`** (zone `LOWM`, protégée par le
      crt0) : copié de `WG2.AUX` (aux `$8000`) au démarrage, 601 octets.
      Aucune image en retard à pleine vitesse (avec et sans carte).
- [x] **Memory Station** (`src/memory.s`, dans l'overlay de la boutique) :
      grilles 3×3, 5×3, 5×5 puis 7×5 ; des paires de bonus (pièces, S, B, T,
      vie, armure, armes 2-3, lettres EXTRA, ×2) et **un crâne** (le
      pavillon pirate) qui termine la station. Une paire : son bonus (`take`,
      comme une icône attrapée) ; la grille finie : **+25 000** et la grille
      suivante ; deux cartes différentes restent visibles ~1 s. Temps : jauge
      T (10 s par niveau de T) par grille, horloge de l'écran (la logique du
      jeu attend). Cartes = icônes du jeu (`?` face cachée). Flèches ou
      I J K L, RETURN ou ESPACE, ESC sort ; manette : paddles 0/1, bouton 0.
      Musique : PT3 ou duet, comme la boutique. Règles (`mem_deal`,
      `mem_turn`) contre le modèle.
- [x] Tests (`tests/test_subgames.py`, `make test`) : modèle (20 tempêtes,
      donnes de toutes tailles) ; **oracle Meteor Storm** au pas près depuis
      le niveau 4 (traversée à pleine vitesse ; choc sans perte de vie) ;
      Memory Station au clavier (une erreur, 4 paires, grille finie +25 000,
      crâne sur la grille 5×3), à la manette (une paire, ESC, puis la
      boutique), temps écoulé. `test_screen` : écran de la tempête == redessin
      complet (HUD, rochers, message). Message central passé à 12 caractères.
- **Écarts à valider** :
  - Pas de gemmes à part : la tempête sème des pièces (10 à 200).
  - Le crâne termine la station dès qu'il est retourné (le pavillon de
    Warblade) ; ESC permet aussi de sortir.
  - Le temps de la station se compte **par grille** (pas pour toute la
    station).

Plan d'origine :

- [ ] Meteor Storm : astéroïdes qui descendent, tir = accélérer (on
      ralentit plus vite qu'on accélère), jauge de vitesse et de distance,
      choc = retour au jeu sans perte de vie, prime selon la vitesse.
      Mêmes sprites et même cadence que le jeu.
- [ ] Memory Station : grille de paires, temps = jauge T, grille plus grande
      à chaque réussite (+25 000), pavillon pirate = fin. Écran fixe HGR,
      curseur au clavier ou à la manette.

## Lot 9 — titre, démo, records, intégration (fait, 2026-10-23)

Réalisé :

- [x] **Écran titre** (`src/front.s`, dans l'overlay de la boutique : segment
      `FRONT` après `DUET`, overlay porté à 8 Ko, aux `$7000-$8FFF` ; la
      boutique ne copie que sa part). Image `tools/title.py` (WARGALAGA en
      lettres de la police ×2 cellules × 3 lignes, II, les petits aliens,
      étoiles) → `fhpack -c -9 -h` → **792 octets**, décodée en page 1 par
      `lz4fh.asm` assemblé dans l'overlay (`[lib]` : option `LZ4FH_HERE=1`,
      défaut identique). Sous l'image, un panneau (lignes 11-23) : menu
      (jouer, J clavier / manette, S son, H aide, ESC quitter, meilleur
      score), records, aide. Musique : PT3 ou `duet` (`sh_tick` de la
      boutique).
- [x] **Mode démo** (`src/demo.s`, résident en `$0A59` après Meteor Storm) :
      une vraie partie (niveau 1, `SEED`), `logic_step` prend chaque pas
      dans `src/demo.inc` (`tools/demo.py` : les déplacements de
      l'autopilote sur le modèle, tir pressé et tenu, plages d'un octet,
      ~320 octets pour 1 800 pas : niveaux 1 à 3, début du 4) ; boutique et
      station fermées (`noshop`) ; « DEMO » au centre (message 4) ; une
      touche, un bouton, la fin du script ou GAME OVER : le titre. Cycle au
      repos : menu ~10 s, records ~8 s, démo.
- [x] **Records** `HIGHSCORES` (`tools/records.py` : format, règles, fichier
      neuf ; 8 entrées : initiales, score BCD, niveau atteint ; la manette) :
      lu une fois (défauts s'il manque ou est invalide), écrit après un
      record ou un changement de manette (créé s'il manque) ; disquette
      protégée : « SCORES NOT SAVED », la table reste en mémoire. Initiales
      au clavier (lettres, chiffres, `.`, ← / DELETE, RETURN) ou à la
      manette (Y choisit, bouton valide) ; 30 s sans rien : ce qui est tapé.
- [x] **Choix du périphérique** au titre (J ou TAB), retenu dans
      `HIGHSCORES` ; TAB reste en jeu.
- [x] Flux : démarrage → titre ; ESC en jeu → titre (record possible),
      ESC au titre → ProDOS ; GAME OVER → titre après le tir (passé
      `OVER_WAIT`) ou `OVER_END` = 240 images.
- [x] Construction : `HIGHSCORES` sur le volume, `fhpack` (`dev/cc65/fhpack.mk`),
      `make test` y compris `tools/demo.py --check`. Racine : `wargalagaii`
      dans `IIE_PRODOS_GAMES` (`all`, `profile-iie-prodos` qui parcourt la
      liste) et dans `TESTED` (`test-wargalagaii`), ligne et section du
      README racine, captures `screenshots/`.
- [x] Tests : `tests/test_front.py` (règles des records ; titre = image +
      menu, J, H ; cycle au repos ; **démo entière == modèle** au pas près,
      1 801 pas ; démo arrêtée par une touche, par le bouton, sans record ;
      record au clavier, fichier écrit puis relu ; record à la manette sur
      disquette protégée, erreur `$2B` via `POM2_MEDIA_WRITE_DEFAULT`) ;
      `test_screen` : écran de la démo == redessin complet. Les autres tests
      démarrent par `tests/boot.py` (`front_skip` posé en `_main` : la partie
      tout de suite, `SEED`) ; ceux qui laissent la partie finir tiennent
      `over_wait` à 0 ou donnent 9 vies.
- [x] Banc (`tools/profile.py`, //e NTSC) : formation + plongeurs + 10 tirs :
      rendu moyen 21 145 (pire 27 672) + logique 3 759 (pire 4 493) ; boss
      (niveau 25) : rendu 18 417 (pire 26 348) + logique 4 522 (pire 5 617),
      contre 28 060 ; aucune image en retard sur ces scènes, ni en Meteor
      Storm (lot 8). Rien n'est passé en lib : pas d'entrée `bench-check`.
      Entrée des vagues (déjà au-delà du budget) : 88 images en retard sur
      1 600, contre 78 avant le lot ; le seul placement du code (octets de
      remplissage devant `_main`) fait varier ce nombre de 80 à 90 : bruit
      d'alignement, pas le coût des nouveaux tests.
- [x] Relecture indépendante (sous-agent, code seul) : rien qui plante,
      bloque, écrase ou désynchronise la démo ; six défauts corrigés :
      DELETE effacé en majuscule (`$7F` → `$5F`, n'effaçait rien), bouton
      encore tenu après la dernière initiale à la manette = « jouer »
      (`fr_btn` relu après la saisie), délai des initiales compté depuis la
      dernière saisie, ESPACE tenu à GAME OVER sautait le titre (touches
      verrouillées jusqu'à leur relâche), le message « NOT SAVED » abrégé
      par une touche (haut-parleur), un `HIGHSCORES` court gardait des
      octets périmés (défauts si moins de 64 octets lus).
- **Écarts à valider** :
  - Titre en HGR (pas de DHGR, décision 1) et texte du menu en anglais,
    comme le jeu.
  - La démo n'a pas d'entrées scriptées à la main : c'est l'autopilote
    (tir continu, aucune vie perdue sur la minute).
  - ESC en jeu ramène au titre (pas de pause) ; un record peut s'y faire.
  - `HIGHSCORES` est lu une fois, réécrit après un record, ou en quittant
    le titre si la manette a changé (pas à chaque appui sur J).

Reste :

- [ ] Validation sur vraies machines (//e enhanced + Mockingboard, //c),
      selon `dev/lib/HARDWARE.md`.

## Lisibilité des bonus (2026-10-23)

Demande : « l'affichage des bonus doit être fortement amélioré en pensant à
la lisibilité ». Avant : une lettre de la police (traits d'un point, franges
de couleur) et un carré de couleur, 2 × 8 ; deux T, deux A, des chiffres
pour les armes comme pour les marques.

- [x] Icônes redessinées dans `tools/sprites.py` (`ICON_SHAPES`), **7 cellules
      × 13 lignes** (`ICON_H` = `OBJ_H`, 8 avant), tracées en cellules de 2
      points : traits blancs sans franges. Une forme par famille, la couleur
      dit laquelle : pièces = disque à `$` découpé (vert 10, orange 50, bleu
      100, violet 200) ; jauges = pilule bleue S B T ; armes = pilule violette
      (1, 2, 3 tirs ; tir auto : tirets) ; multiplicateurs = pilule orange
      2, 5 ; EXTRA = pilule blanche ; bouclier = bulle verte autour du
      vaisseau ; armure = écu bleu ; vie = cœur orange ; crâne ; gel = flocon ;
      marques = médaille (ruban, disque de la couleur, numéro découpé),
      marque sombre = médaille vide ; sous-jeux = le rocher, la carte verte `?`.
- [x] `icon_src` par table (`icon_lo/hi`) ; la boîte de ramassage suit
      `OBJ_H` (modèle et 6502) ; script de la démo régénéré ; aide du titre.
- [x] Bug trouvé en passant (lot 7) : les marques de la boutique étaient
      posées toutes les 3 colonnes, une sur deux sur une colonne impaire, où
      les couleurs s'échangent (orange affiché bleu) : pas de 4 (test
      `marks_screen` de `tests/test_shop.py`).
- Coût : 5 lignes de plus par objet, à l'effacement et au tracé ; environ
  520 cycles par objet visible et par image, compte fait sur le code (pas
  mesuré), soit ~3 100 au pire avec 6 objets à l'écran. Aucune image en
  retard au banc, cadence inchangée (90 images en retard à l'entrée des
  vagues, dans le bruit 80-90 mesuré au lot 9).
- Aperçu : `screenshots/bonus.png` (les 32, dans l'ordre de `model.KINDS`).

## Effets des bonus et malus perçus (2026-10-23)

Demande : « implémente les actions de tous les bonus et malus ». Les 32
effets existaient déjà depuis le lot 5 (modèle et 6502, oracle
`bonus_effects`) mais un ramassage était muet et invisible : rien ne disait
ce qu'on avait pris, ni quel malus le crâne avait tiré.

- [x] **Nom au ramassage** : le message du milieu du terrain (ligne 96)
      affiche ce que le ramassage a fait pendant `PICK_T` = 45 pas (1,5 s) :
      « +50 CREDITS », « TRIPLE SHOT », « SCORE X5 », « RANK MARK 3 »… ; une
      jauge, l'armure ou les vies déjà au maximum : « BONUS POINTS » ; le
      crâne dit son malus (« SINGLE SHOT », « LESS SPEED », « LESS BULLET »,
      « BONUS LOST ») ; la cinquième lettre : « EXTRA LIFE ». Priorité :
      GAME OVER, LEVEL n, METEOR STORM, puis le ramassage, puis DEMO.
- [x] État de logique `pick_msg` / `pick_t` (modèle = oracle, `take` pose
      `pick_msg`, `pickups` arme `pick_t`) ; 36 textes de `model.PICK_TEXT`
      générés par `tools/bonus.py` dans le segment `PICK` de LOWM ($0BCE,
      504 octets : la mémoire principale n'en a plus que ~380).
- [x] **Deux bruitages** : `bonus` (arpège montant do-mi-sol-do) et `malus`
      (chromatique descendante) pour arme simple, marque sombre et crâne ;
      priorité entre l'armure et l'explosion.
- **Acceptation** : `bonus_effects` étendu (988 pas == modèle, les 36 textes
      vus) ; `pickup_feedback` (SHIELD + son bonus, DARK MARK + son malus, le
      message s'efface) ; l'invariant d'écran connaît le message.
- Coût : un changement de message réécrit 12 caractères sur chaque page (au
  ramassage et 1,5 s plus tard), pas chaque image.

## Chasse aux bugs 7 — chargement auxiliaire et build (2026-10-25)

- [x] `aux_load` vérifie désormais la taille cumulée **avant** chaque
      `AUXMOVE`. Un `WG2.AUX` trop long était rejeté seulement après avoir
      écrit au-delà de sa zone auxiliaire. Reproduction : 64 octets ajoutés
      écrasaient la sentinelle placée juste après le fichier attendu.
      `tests/test_game.py` couvre le fichier vide, tronqué, trop long d'un
      octet ou d'un bloc de 8 Ko : sentinelles et bitmap conservés, message
      d'erreur et retour au lanceur ProDOS.
- [x] La génération de `song.pt3` accepte un `BUILD` absolu : le changement
      de dossier vers `tools/` préfixait auparavant sa destination par
      `../`, ce qui cassait les compilations isolées dans `/tmp`.
- Validation : build isolé, `make test` et `tests/test_long.py` (boucle 255,
      niveaux les plus chargés avec et sans Mockingboard). Les images de
      `dist/` restent intactes.

## À vérifier sur machine

- [ ] //c + Mockingboard 4c : la détection réveille la carte à `$C403` et
      peut masquer la ROM souris du slot 4. L'interruption VBL du firmware
      souris (notre horloge //c) reste-t-elle utilisable ? Sinon : horloge par
      le timer T1 de la VIA (régulière, pas calée sur le VBL : déchirure
      possible à la bascule de page).

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
