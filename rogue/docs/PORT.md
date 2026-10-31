# ROGUE — notes de portage POM1 → Apple II + E-Z Color

*[← ROGUE](../README.md) · [VIDEO_API.md](VIDEO_API.md)*

Source : POM1, `sketchs/tms9918/game_rogue/TMS_Rogue.asm` (6 777 lignes),
`tileset_rogue.inc`, `sprites_boss.asm`, et ses morceaux partagés
`dev/lib/games/rogue/{dungeon,shadowcast}.asm`, `dev/lib/m6502/{prng16,multiply}.asm`,
`dev/lib/tms9918/{tms9918m1,tms9918_pad}.asm`. Cible POM1 : Apple-1 + carte
P-LAB TMS9918, cartouche CodeTank à `$4000-$7FFF` (12 051 octets de code),
tampons dans la banque haute `$E000-$E46F`, 98 octets de page zéro.

## 1. Ce que le jeu touchait sur l'Apple-1

| Point de contact | Apple-1 / P-LAB | Apple II (ce portage) |
|---|---|---|
| VDP données / contrôle | `$CC00` / `$CC01`, adresses fixes | `$C0n0` / `$C0n1`, n = 8 + emplacement, trouvé au démarrage (`ez_detect`) |
| Clavier | `KBDCR $D011` (bit 7), `LDA KBD $D010` lit **et** acquitte | `LDA $C000` (bit 7), acquittement explicite `STA/BIT $C010` |
| « Vider le clavier » | `LDA KBD` | `BIT KBDSTRB` (8 endroits) |
| Tampons | `MAPSEG $E000` (carte 80 o + visibilité 20 o), `monsters $E300`, `items $E380`, `inventory $E3A0` en adresses absolues | segment `LOWBSS` à `$1000`, mêmes tailles, **même ordre contigu** (l'effacement unique de `spawn_monsters` en dépend) |
| Page zéro | `$00-$61` (Wozmon écrasé : jamais de retour) | `$50-$BD` ; celle du DOS est copiée au départ et rendue en sortie / Ctrl-RESET (`exit.asm`) |
| Graine du hasard | compteur 16 bits jusqu'à la touche du titre, XOR de la touche | gardé ; en plus la musique du titre tourne (un tick par passage tant qu'elle joue) et l'attente de la page « mission » fait avancer le LFSR (`wait_key_stir`) |
| Démarrage à froid après la mort / la victoire | `JMP $4000` (cartouche) | `JMP start` (le jeu, sans refaire la détection) |
| Sortie | aucune (on éteint) | ESC au titre, ou ESC puis Y en jeu → DOS ; Ctrl-RESET → DOS |
| Terminal Apple-1 (ECHO) | pas utilisé | la page texte Apple affiche l'avis « regardez le moniteur de la carte » |
| Télémétrie `$C440-$C443` | absente de ce jeu | — |

## 2. Accès VDP : une table de patchs, pas d'indexé

Chaque accès VDP de `ROGUE.TMS` est une instruction **absolue** sur `$C080` /
`$C081` émise par une macro (`src/ezvdp.inc`), qui note l'adresse de son
opérande dans le segment `VDPFIX`. Au démarrage, `vdp_patch` réécrit l'octet
bas de chaque opérande en `$80 | port | emplacement·16`.

- Mêmes cycles que sur l'Apple-1 (`STA abs` = 4 cycles, même horloge
  ~1,02 MHz) : le rembourrage silicium de POM1 (≥ 18 cycles entre deux accès,
  22 de `STA` à `STA`) reste exact.
- Pas de `STA $C080,X` : le 6502 NMOS fait une **lecture fantôme** à la même
  adresse avant d'écrire ; lire le port de données avance l'adresse VRAM, lire
  le port de contrôle remet à zéro la bascule des deux octets.
- 30 sites seulement : depuis le découpage cœur / back-end, tous sont dans
  `video_tms.asm` (pilote Mode 1 de POM1 + `vid_*`).
- Les macros posent une étiquette anonyme (`:`) : une étiquette nommée
  couperait la portée des `@locales` de l'appelant.

`a2run --ezcolor` compte les accès trop rapprochés (`vdp_fast_writes`) : 0 au
démarrage, sur 200 touches de jeu, jusqu'à la profondeur 2 et dans la salle du
boss (tests).
Depuis le 2026-10-31, a2shot fait tourner la vraie carte de POM2 (cœur
ba7f04da, `--ezcolor=N`, mode silicon-strict : un accès que le VDP ne peut pas
servir est perdu et compté) : `droppedAccesses` = 0 au titre, sur les 200
touches et jusqu'à la profondeur 2 (`tests/test_rogue_pom2.py`). R1 a toujours
le bit 7 (16 Ko) : `$C2` en jeu, `$80` écran éteint, `$C0` après
`init_vdp_g1` ; en mode strict, sans ce bit, le VDP adresserait en 4 Ko.

## 3. Cœur et back-ends

Le jeu de POM1 est devenu `src/core/rogue_core.inc` : plus aucun accès
matériel vidéo. Il écrit un écran TMS9918 virtuel (table des noms + table des
sprites) par `vid_addr` / `vid_put` ; `WRT_DATA_REG`, `WRT_DATA_VAL`,
`WAIT_VBLANK_SAFE` sont restés des macros, qui appellent le back-end ; les 60
`JSR tms9918_pad18` du jeu ont disparu (le back-end garantit le délai). La mise
en route (`init_vdp_g1`, uploads, `R1 = $C2`) est `vid_init`. Contrat complet :
[VIDEO_API.md](VIDEO_API.md). `ROGUE.TMS` = `boot.inc` + cœur +
`video_tms.asm` ; `ROGUE.DHGR` = cœur + `video_dhgr.*` (autre builder).

**Logique identique octet pour octet** (seuls les appels vidéo, clavier et les
`SFX` ajoutés diffèrent) : génération du donjon (big-room / deux salles +
couloir en L, portes, escaliers, fosses), champ de vision par shadowcasting
(Bergström), IA des cinq monstres et du boss 2×2, objets, sac de 26 places,
bonus à durée, lancer de dague, XP et niveaux, HUD, écrans de mort et de
victoire, aide, carte révélée. `dungeon.asm`, `prng16.asm`, le tileset et les
sprites sont des copies inchangées ; `shadowcast.asm` donne le même champ de
vision que celui de POM1 par d'autres calculs (rangs de pentes en tables, §3.1),
et `multiply.asm` (son `umul4`) n'est plus utile, ni copié.

**Changé** : titre (« APPLE II E-Z COLOR ROGUELIKE », « MOVE IJKL OR
ARROWS », ligne « [S] SOUND [ESC] QUIT ») ; flèches → IJKL (←/→ sur tout
Apple II, ↑/↓ sur //e), minuscules repliées ; `S` = son, `ESC` = quitter
(question sur la ligne 23) ; sons ; graine.

### Le back-end DHGR (`src/video_dhgr.asm`, `src/rogue_dhgr.s`)

`ROGUE.DHGR` = `rogue_dhgr.s` (entrée : `$FBB3 = $06` sinon un message et le
DOS ; `plat_quit` = `vid_off` + `apple2_exit` ; `plat_sound_status` = `RTS` ;
`APPLE2_EXIT_HOOK` vide la page texte) + cœur + `video_dhgr.asm` + les données
générées `video_dhgr_data.inc` (`tools/tiles_dhgr.py`, octet pour octet
stable). Il **émule** l'écran TMS9918 virtuel de [VIDEO_API.md](VIDEO_API.md) :

- **Géométrie** : image TMS divisée par deux en largeur, 1 pixel couleur DHGR
  = 2 pixels TMS, 1 ligne = 1 ligne, de x = 6 à 133. Les tuiles de 7 pixels
  de large (alignées sur les groupes DHGR) ont été écartées : 32 colonnes de
  texte ne tiennent pas dans 16 × 7 pixels, les icônes du sac et du HUD sont
  posées au pixel TMS près, et 16 → 7 colonnes déforme tuiles et police. Avec
  8 pixels par tuile, tout tombe exactement, au prix de décalages (un
  caractère chevauche deux groupes de 7 pixels : 7 phases, voir plus bas).
- **`vid_addr` / `vid_put`** : la VRAM virtuelle est une vraie copie aux
  mêmes adresses (`$1800-$1B7F`) ; `vid_put` compare l'octet à celui du
  curseur (opérande auto-modifié) : **27 cycles** s'il est inchangé
  (`PHP` / `CMP` / `INC` / `PLP`) ; s'il change, il l'écrit ; un nom est
  aussitôt comparé à `dg_shown` (ce que l'écran montre, vu par `dg_san` :
  tous les caractères vides se valent) : différent, il marque son ou ses
  deux groupes de 7 pixels et sa ligne (~130 cycles), pareil, rien
  (~95) ; un octet de la table des sprites marque la table. `vid_wait_frame` = `RTS` :
  le cœur l'appelle avant de tout reconstruire, dessiner là montrerait des
  images à moitié faites.
- **`vid_idle`** (avant chaque attente de touche, à chaque image d'une dague
  lancée) : (1) les noms de chaque ligne qu'un `vid_clear` a marquée sont
  comparés à `dg_shown` (boucle aux opérandes patchés, ~21 cycles par nom) :
  chaque nom différent marque le ou les deux groupes de 7 pixels dessous
  (un octet par groupe, 20 par ligne) ; un `vid_clear` suivi de la même
  carte ne marque rien, une tuile de sol (caractères vides) qui s'éteint
  non plus ; (2) la liste de sprites est comparée à celle
  dessinée : chaque entrée changée marque ses deux boîtes (2 groupes × 2
  ou 3 lignes) ; (3) chaque ligne de texte marquée : la liste de ses
  sprites, puis chaque suite de groupes sales est **composée octet par
  octet** dans un tampon de 8 lignes de 80 octets « de flux » (l'octet 2o
  = auxiliaire o, 2o + 1 = principal o ; 3 lignes par page, aucun accès
  indexé ne franchit de page) et écrite.
- **Composition par octets** (`tools/tiles_dhgr.py` calcule les tables, et
  `compose()`, le même algorithme en Python, vérifié contre le modèle pixel
  à la génération) : une ligne d'un caractère = 4 pixels × 4 points = 16
  points à partir du point 24 + 16 c, donc 7 phases (c mod 7) : 3 ou 4
  octets, le premier ajouté (`ORA`) au dernier du caractère précédent, les
  autres posés (`STA`). Par ligne : nom → indice (encre 0..3 × 16 + les 4
  pixels, `dg_ri`), puis une table de 64 octets par octet produit
  (`dg_cp<p><i>`) : **41 cycles par caractère et par ligne**, 10 pour un
  caractère noir. Code déroulé sur les 8 lignes, une routine par phase,
  les caractères enchaînés de gauche à droite. Sprites, entrée la plus
  haute d'abord : deux moitiés de 4 pixels, chacune 3 ou 4 octets à partir
  du bit r de l'octet k (`dg_sm<r><i>`, 16 octets), peintes par
  `b = b EOR ((b EOR encre) AND points)` (`dg_cpat` : l'encre selon k mod 4),
  ~25 cycles par octet. Plus d'empaquetage : les octets sont déjà ceux de
  l'écran. Écriture : 8 instructions `STA abs,Y` (une par ligne, adresses
  patchées par bande), deux colonnes par passe, ~10 cycles par octet ;
  octets auxiliaires sous `SEI` (RAMWRT aux), puis principaux. Chaque octet
  de la suite est écrit une fois, à sa valeur finale (vérifié par le test
  avec `storewatch`) : pas de scintillement, une seule page.
- **Coûts** (//e, `tests/test_dhgr.py`, partie à graine fixe : mêmes
  donjons pour chaque version ; détail par routine : `tools/profile_dhgr.py`) :

  | | avant (pixel par pixel) | octets | + lots du 2026-10-31 (§3.1) |
  |---|---|---|---|
  | écran entier | 893 580 cycles (0,87 s) | 336 818 (0,33 s) | 337 327 |
  | un sprite recoloré (flash) | 32 733 | 14 825 | 14 778 |
  | tour, médiane | 144 104 | 108 688 (0,11 s) | 40 829 (0,04 s) |
  | tour, 90 % | 358 096 | 227 326 | 138 644 |
  | tour, moyenne | 181 107 | 112 639 | 74 648 |
  | tour le plus lent | 816 869 | 424 776 | 405 686 |

### 3.1 Budget d'un tour (2026-10-31)

Cinq lots, sans rien changer au jeu (donjons, hasard, champ de vision,
combats, objets) : seulement l'ordre, les caches et les attentes du
rendu. Vérifié par `tests/test_dhgr.py` (`tests/dhgr_screens.txt` : le
sha1 de l'écran virtuel, noms + sprites, aux 89 points de contrôle dont un
après chaque heurt / repos et chaque fermeture du sac ou de l'aide, relevé
sur la version d'avant) et, hors dépôt, par l'écran virtuel + l'état du jeu
(carte, visibilité, monstres, objets, sac, PV, hasard) après chaque tour,
identiques à la version d'avant : //e graines `0x1983` et `0x5A3C`
(137 tours chacune), TMS (a2run) 260 touches × 2 graines, et les 56 images
de vol de 40 lancers de dague.

1. **L'image avant le son** : `main_loop` appelle `vid_idle` avant
   `sfx_flush` (le DHGR dessine là ; sur la carte l'image est déjà
   complète, le son ne fait toujours qu'allonger les écarts entre accès).
   Le tour dure autant, mais le coup se voit tout de suite, le son suit
   (avant : jusqu'à 215 000 cycles de son avant l'image).
2. **render_map incrémental** : `map_shadow` (160 octets, un par case : la
   base de ses 4 noms, `RM_DARK` = 4 zéros, `RM_STALE` = inconnu) ; seules
   les cases dont le code change sont écrites (`rm_write` : 2 `vid_addr`,
   4 `vid_put`). Une rangée dont les octets de visibilité et de carte sont
   ceux de son dernier dessin (`rm_vis`, `rm_map`) est sautée. Tout
   effacement passe par `clear_screen` (= `rm_invalidate` + `vid_clear`) :
   titre, mission, sac, aide, mort, victoire, nouvel étage, parchemin ; la
   carte suivante est alors réécrite en entier. `redraw_game` sans modale
   depuis (dague, objet utilisé) n'efface plus que les noms du HUD que
   `update_hud` ne réécrit pas (ligne 22 col. 0-23, ligne 23 col. 0-1).
   `vid_put` : 468 → 73 appels par tour.
3. **Lancer de dague** : seule la première image repeint le jeu (elle
   efface DIRECTION?) ; les suivantes ne refont que la table des sprites
   (rien d'autre ne bouge en vol), la dernière les sprites + le HUD (l'XP
   d'un monstre tué). Mêmes noms à chaque image (vérifié image par image).
   Les attentes du cœur (`delay_throw_frame`, ~82 000 cycles par image)
   sont gardées : le vol dure presque autant, il était surtout fait
   d'attente ; une image coûte maintenant ~15 000 cycles de dessin.
4. **Champ de vision** (résultats identiques) : les pentes de
   `shadowcast.asm` ne sont plus des fractions multipliées (`umul4`, ~70
   cycles le produit) mais des **rangs** : toute pente est un n / d avec
   n ≤ 15, 1 ≤ d ≤ 15 (fov_r ≤ 7), son rang = combien des 240 fractions
   sont plus petites ; comparer deux pentes = comparer deux octets, pentes
   gauche / droite de chaque case en tables (`sc_lrank`, `sc_rrank`,
   calculées par l'assembleur). La bizarrerie de POM1 est gardée : après un
   appel récursif, le parent prend la pente droite de la dernière case
   balayée par l'enfant (`cast_li`). Transformation d'octant en tables
   (source col / profondeur et signe), `mark_visible_at_cur` et
   `is_opaque_at_cur` par tables. `multiply.asm` n'est plus inclus.
   Le cœur d'un tour moyen : 35 600 → 13 400 cycles.
5. **HUD** : `update_hud` = 4 appels (une ligne chacun) ; `finish_turn`
   (`hud_paint`) ne repeint que les lignes dont les valeurs ont changé
   (`hud_last`) tant que `hud_ok` dit que les lignes 20-23 montrent sa
   dernière peinture (`clear_screen`, `draw_text`, `clear_msg_rows`,
   `clear_msg_row23`, `update_hud` le remettent à 0).

Et dans le back-end : `dg_shown` en `dg_san` (une tuile de sol qui
s'allume ou s'éteint ne redessine rien), `vid_put` qui marque lui-même
les groupes (plus de balayage des lignes touchées, ~670 cycles par ligne).

Mesures (`tools/profile_dhgr.py`, cycles de la touche lue à l'attente de
la suivante ; « sans le son » = l'image est là, le son suit) :

| //e, graine 0x1983 | médiane | 90 % | moyenne | max |
|---|---|---|---|---|
| avant | 108 688 | 227 326 | 112 639 | 424 776 |
| 1. image avant le son | 109 423 | 228 024 | 113 293 | 424 978 |
| 2. render_map incrémental | 83 720 | 211 585 | 101 395 | 427 997 |
| 3. dague | 83 769 | 212 094 | 101 559 | 428 481 |
| 4a. pentes en tables (`umul4` → `sc_mul`) | 57 520 | 177 262 | 87 932 | 426 458 |
| 5. HUD | 49 479 | 169 261 | 83 129 | 426 507 |
| back-end : vides égaux, marquage direct | 47 149 | 146 403 | 78 094 | 433 056 |
| 4b. rangs, tables de case, cache de rangée | **40 829** | **138 644** | **74 648** | **405 686** |
| sans le son : avant → après | 106 453 → 38 149 | 179 099 → 103 094 | 91 067 → 53 076 | 317 545 → 317 675 |

| //e, graine 0x5A3C (torche souvent allumée) | médiane | 90 % | moyenne | max |
|---|---|---|---|---|
| avant | 152 154 | 237 678 | 143 071 | 999 281 |
| après | **61 896** | **147 321** | **83 624** | **602 913** |
| sans le son : avant → après | 149 677 → 56 570 | 201 358 → 97 882 | 128 117 → 68 668 | 966 290 → 559 401 |

Autres graines (après, avec / sans le son) : médianes 54 600 / 50 300,
57 000 / 54 000, 58 600 / 55 400, 56 800 / 54 000 ; 90 % sans le son
94 000 à 105 000. Le 90 % avec le son est fait des tours qui en jouent un
(heurt 61 000, coup 72 000, objet 107 000, escalier 215 000 cycles) et des
écrans entiers (sac, aide : ~240 000 à l'ouverture, ~300 000 à la
fermeture) : ni l'un ni l'autre n'a changé.

Un tour moyen (graine 0x1983) : son 21 600, cœur 13 400 (était 35 600),
`vid_put` 5 100 (14 700), dessin ~33 000 (~40 000 : écriture 9 500,
caractères 8 300, sprites 6 200, le reste comparaisons et suites). Le
déplacement médian : cœur ~18 700 (champ de vision ~12 000), dessin
~20 000. TMS (a2run, 260 touches, son et deux attentes de trame compris) :
médiane 63 060 → 40 510 (graine 0x1983) et 102 366 → 51 176 (0x5A3C),
90 % 102 393 → 98 952 et 119 435 → 89 456, moyenne 66 242 → 49 665 et
83 029 → 48 863.

- **Ce qui reste** : les sons (durées inchangées), les écrans entiers
  (~0,33 s : tout l'écran recomposé), les attentes du lancer, et sur la
  carte les deux `vid_wait_frame` d'un déplacement (render_map,
  place_all_sprites : jusqu'à une trame chacune). Mémoire : ROGUE.DHGR
  finit à `$9017` (1,5 Ko libres sous `$9600`), ROGUE.TMS fait 14 367 octets.

## 4. Démarrage, détection, messages

1. `HELLO` → `BRUN ROGUE` : le **lanceur** (`src/launcher.s`, `$6000`).
2. II / II+ / //e : `ez_detect` (`dev/lib/apple2/ezcolor.asm`) sonde les
   emplacements 7, 5, 4, 2, 1, 6 en sautant celui du lecteur de démarrage
   (`$B7E9`, IOB du DOS 3.3) ; l'emplacement 3 est évité (cartes 80 colonnes
   et souris y ont des registres en `$C0B0`). //c (`$FBC0 = 0`) : pas de sonde.
3. Carte trouvée → « E-Z COLOR CARD IN SLOT N », `BRUN ROGUE.TMS`, qui refait
   la détection (au cas où on le lance directement), patche ses accès, écrit
   la page texte Apple (gardée pendant toute la partie, ligne « SOUND: ON/OFF »
   mise à jour par S) puis lance le jeu.
4. Pas de carte, //e 128 Ko ou //c (`$FBB3 = $06`, mémoire auxiliaire vérifiée
   en l'écrivant : 80STORE + HIRES + PAGE2, `$2000` et `$0400` auxiliaires
   doivent garder deux valeurs différentes) → « NO E-Z COLOR CARD: DHGR »,
   `BRUN ROGUE.DHGR`.
5. Ni l'un ni l'autre → page « ROGUE CANNOT RUN ON THIS APPLE » : ce qu'il
   faut (la carte dans un emplacement libre sauf 3 avec son moniteur, ou un
   //e 128 Ko / //c), l'emplacement du lecteur non testé, comment faire dans
   POM2 ; une touche rend le DOS (prompt sous le texte).

Avant d'enchaîner, le lanceur remet le vecteur RESET du DOS (sinon le
programme suivant garderait celui du lanceur, écrasé par le chargement).

## 5. Sons (haut-parleur, `tone` de `sound.asm`)

Un tour empile au plus un son (`SFX id`, l'id le plus haut gagne) ; `main_loop`
le joue après l'image, avant d'attendre la touche suivante. Un son allonge
l'écart entre deux accès VDP, jamais ne le raccourcit. Données générées par
`tools/music.py` → `src/core/music.inc`.

| id | Événement | Son |
|---|---|---|
| 1 | heurter un mur | bourdon grave A4 |
| 2 | porte de bord (salle voisine) | C5-G5 |
| 3 | ramasser un objet | E6-B6 |
| 4 | frapper un monstre | A5-F5 |
| 5 | lancer une dague (tout de suite) | glissando C7 → A5 |
| 6 | tuer un monstre | E5-C5-A4 |
| 7 | épée / tunique / amulette / torche | C6-E6-G6 |
| 8 | ration / potion | G5-C6-E6-G6 |
| 9 | parchemin (pendant la carte) | scintillement C7-G6-E7-C7-G7 |
| 10 | un monstre vous mord | B4-A4 |
| 11 | fosse | chute C6 → A4 |
| 12 | escalier | descente G5-E5-C5-B4-A4 |
| 13 | niveau gagné (PV max, ATK, DEF) | arpège C5-E5-G5-C6 |
| 14 | salle du démon | trille A4 / A#4 |
| — | titre / mort / victoire | airs `tune.asm` (le titre joue une fois pendant l'attente) |

`S` coupe tout (sons et airs, le tempo des airs est gardé). Pas de clic de pas
(option non faite, voir TODO).

## 6. Mémoire

### ROGUE.TMS (Apple II+ 48 Ko, DOS 3.3 gardé)

| Zone | Contenu |
|---|---|
| `$0050-$00BB` | page zéro du jeu (108 o : cœur, `vdp_*`, FOV, `tune_ptr`, `txt_*`, `tms_src`, `ez_ptr/count`) |
| `$0400-$07FF` | page texte Apple : l'avis |
| `$0800-$0FFF` | HELLO (gardé par le DOS) |
| `$1000-$13F7` | `LOWBSS` : carte, visibilité, monstres, objets, sac (468 o), ombre de la carte de render_map (`map_shadow`, `rm_*` : 280 o) et du HUD (12 o) + copie de la page zéro du DOS (256 o) |
| `$2000-$3FFF` | libre (pas de HGR : l'Apple reste en texte) |
| `$4000-$7831` | le fichier : `STARTUP` (entrée = 1er octet), `CODE` 12 210 o, `RODATA` 1 940 o (tileset 2 Ko compris dans CODE, sprites, textes, sons, rangs de pentes 128 o), `VDPFIX` 60 o, `BSS` 19 o |
| `$7832-$95FF` | libre (7,6 Ko) |
| `$9600-$BFFF` | DOS 3.3 |

`$4000` = l'adresse de la cartouche Apple-1. Fichier : 14 367 octets
(57 secteurs). Le DOS reste : ESC y retourne, et la place suffit.

### ROGUE.DHGR (Apple //e 128 Ko ou //c, DOS 3.3 gardé)

| Zone | Contenu |
|---|---|
| `$0050-$00DA` | page zéro (139 o : cœur 95 o + back-end DHGR 44 o) |
| `$0800-$0FFF` | HELLO (gardé par le DOS) |
| `$1000-$13F7` | `LOWBSS` : comme ROGUE.TMS (carte, visibilité, monstres, objets, sac, ombres de render_map et du HUD, page zéro du DOS) |
| `$1800-$1F84` | `DHGRBSS` : l'écran TMS virtuel **à ses propres adresses** (`$1800-$1AFF` noms, `$1B00-$1B7F` sprites, 1 Ko avec la marge), le tampon de composition (`$1C00-$1EFF` : 8 lignes de 80 octets, 3 par page), la liste de sprites dessinée (128 o) |
| `$2000-$3FFF` | page DHGR 1, banque principale (et `$2000-$3FFF` de la banque auxiliaire) |
| `$4000-$8A7C` | le fichier (19 069 o) : `STARTUP`, `CODE` 13 608 o (dont le back-end, ~4,3 Ko : une routine déroulée par phase de caractère et de sprite), `RODATA` 5 340 o (dont ~4,9 Ko au back-end : indices des lignes de caractères 1 Ko, tables de morceaux 1,7 Ko, sprites 576 o, encres, géométrie), `BSS` 1 435 o (`dg_shown`, les noms à l'écran, 768 o ; les groupes sales, 480 o ; noms de la bande, lignes marquées) |
| `$9018-$95FF` | libre (1,5 Ko) ; `BSS` en `$8A7D-$9017` |
| `$9600-$BFFF` | DOS 3.3 |

La mémoire auxiliaire ne sert qu'à la page DHGR : tout le reste tient en
mémoire principale.

### ROGUE (lanceur)

`$6000-$691C` (1 767 o + BSS), 8 o de page zéro. Écrasé par le chargement de
`ROGUE.TMS` / `ROGUE.DHGR` : le `BRUN` du DOS ne revient jamais.
