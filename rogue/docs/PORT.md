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
`video_tms.asm` ; `ROGUE.DHGR` = cœur + `video_dhgr.*` + `video_x2.*` (ci-dessous).

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

### Le back-end DHGR (`src/video_dhgr.asm`, `src/video_x2.asm`, `src/rogue_dhgr.s`)

`ROGUE.DHGR` = `rogue_dhgr.s` (entrée : `$FBB3 = $06` sinon un message et le
DOS ; mise en place de la mémoire, §6 ; `plat_quit` = la marque de sortie +
redémarrage ; `plat_sound_status` = `RTS`) + cœur + `video_dhgr.asm` (moteur
« texte », gestion des deux pages) + `video_x2.asm` (la vue de jeu), avec
les données générées `video_dhgr_data.inc` (`tools/tiles_dhgr.py`) et
`video_x2_data.inc` (`tools/x2_dhgr.py`), octet pour octet stables. Il
**émule** l'écran TMS9918 virtuel de [VIDEO_API.md](VIDEO_API.md) de deux
façons, choisies à chaque `vid_idle` d'après l'écran virtuel seul :

- **vue de jeu** (aucun nom de texte, ≥ 32, dans les rangées 0 à 19) : à la
  façon de **ROGUE X2** (POM1, `sketchs/gen2/game_rogue_x2` : le Rogue HGR
  « ×2 en couleur »), `video_x2.asm` ; les rangées 20 à 23 (HUD) par le
  moteur texte ;
- **page pleine** (titre, mission, sac, aide, mort, victoire : du texte dans
  les rangées 0 à 19) : l'image TMS divisée par deux en largeur (le moteur
  texte, ci-dessous, celui de la première version DHGR), dessinée sur la
  page montrée, chaque octet écrit une fois à sa valeur finale (comme les
  modales de ROGUE X2, `draw_to_front`). Le titre (« ROGUE » rangée 4
  colonne 13, un blanc de chaque côté) a ses rangées 3 à 6 remplacées par
  une bannière : les glyphes TMS de « ROGUE », un pixel TMS = 2 pixels × 4
  lignes, 84 pixels centrés, encre par rangée de glyphe (`x2_banner`).

La première version (2026-10-31) dessinait aussi la carte en image TMS
divisée par deux (`screenshots/dhgr_old_halved.png`) : 128 × 192 pixels,
des tuiles de 8 × 16, jugées laides face au moniteur de la carte.

#### La vue de jeu (X2)

- **Géométrie** : une fenêtre de **9 × 5 cases de 14 × 32 pixels** couleur
  (126 × 160 : groupes de 7 pixels 1 à 18, lignes 0 à 159 ; les groupes 0
  et 19 restent noirs). 14 pixels = 2 groupes de 4 octets (auxiliaire 2g,
  principal 2g, auxiliaire 2g+1, principal 2g+1) : une case commence
  toujours au début d'un groupe, elle s'écrit octet par octet sans aucun
  décalage. ROGUE X2 avait 8 × 5 cases de 28 × 32 pixels HGR (la même
  taille à l'écran), le héros en (3, 2) ; ici 9 colonnes mettent le héros
  **au centre exact**, case (4, 2), 4 cases de chaque côté.
- **Caméra** : l'entrée 0 de la liste de sprites quand c'est le héros (nom 0,
  sur la grille de 16, au-dessus de la rangée 20) : colonne de la fenêtre =
  colonne du héros − 4, rangée = rangée − 2 (sinon la dernière vue). La
  fenêtre peut déborder de la carte : cases noires. Un pas la décale d'une
  case ; un coup, un repos, le vol d'une dague ne la bougent pas (le héros
  n'a pas changé de case) : seules les cases changées se redessinent.
- **Une case = une clé de 3 octets** : la tuile (le nom en haut à gauche de
  ses 4 noms, / 4 : 0 sol ou inconnu (noir, comme sur la TMS), 1 mur,
  2 escalier, 3 porte, 4 arche / éboulis, 5 fosse, 6 or, 7 potion), le sprite
  de devant, celui de derrière (nom / 4 + 1, + `$40` si sa couleur est 8 :
  le rouge « touché » du cœur, sauf le démon, toujours en couleur 8). Les
  sprites retenus : ceux de la grille de 16 au-dessus de la rangée 20 (les
  icônes du HUD sont dessous), les deux premiers de chaque case (l'entrée la
  plus basse devant, comme sur la puce ; un troisième, rarissime, est
  caché). Le démon = ses 4 quarts, 4 cases.
- **Dessins** (`tools/x2_dhgr.py`) : chaque tuile / sprite 16 × 16 perd 2
  colonnes (les deux vides des sprites, les bords des tuiles, les colonnes
  3 et 11 du mur, pour que ses briques gardent un pas de 7 ; les quarts du
  démon perdent leurs colonnes extérieures, vides) et double ses lignes :
  16 rangées de deux moitiés de 7 pixels, 32 octets. Les tuiles sont
  composées au démarrage en images d'octets de 128 octets (8 octets × 16
  rangées, `x2_timg`) ; un sprite est peint sur sa case au moment du dessin
  par `b = b XOR ((b XOR encre) AND points)`, les points d'une moitié de
  7 pixels donnés par 4 tables de 128 (`x2_m`, construites au démarrage
  depuis les 28 octets `x2_pm`), l'encre par octet par `dg_cpat` : la
  couleur n'est qu'un paramètre, le flash ne coûte rien de plus.
- **Couleurs** : la table de ROGUE X2 (`TILE_HUES`, `SPRITE_HUES`)
  transposée en DHGR pour le héros (bleu clair), les monstres (zombie et
  troll verts, fantôme violet, squelette blanc, DEATH et démon orange) et
  les tuiles (mur gris comme sur la TMS, escalier vert, porte orange,
  fosse violette ; l'arche, utilisée en éboulis, jaune comme sur la TMS au
  lieu du blanc de X2). Les **objets** gardent leur couleur TMS9918
  (`tiles_dhgr.PALETTE_MAP` de `item_color_table`) : celle de leurs icônes
  dans le sac et le HUD, que la vue X2 ne change pas (ROGUE X2 n'avait que
  4 teintes et les choisissait autrement). Coup reçu : orange, blanc pour ce
  qui est déjà orange (X2 inversait la palette HGR, ce qui ne marche pas
  pour le blanc).
- **Écriture** (`x2_w`) : 16 × `LDA image,Y / STA ligne 2r,X / STA ligne
  2r+1,X` (chaque rangée sur deux lignes, 14 cycles), une colonne d'octets
  de la case par appel, les 4 colonnes auxiliaires (IRQ masquées, RAMWRT
  aux) puis les 4 principales : ~2 000 cycles la case. Les 32 adresses de
  lignes sont posées dans `x2_w` une fois par rangée de la fenêtre dessinée
  (`x2_lines`, déroulé), la page de l'image une fois par image différente.
- **Double tampon** : `vid_idle` calcule l'image voulue (`x2_frame` : caméra
  + 45 clés, sautée si rien n'a été écrit depuis), puis dessine sur la
  **page cachée** les cases dont la clé diffère de celle que cette page
  montre (`x2_kt/ka/kb`, une liste par page), puis ses rangées 20 à 23 par
  le moteur texte, et la montre (`$C054` / `$C055`, 80STORE éteint) dans le
  balayage vertical : tout de suite si le faisceau y est déjà (`$C019`
  bit 7 à 0 sur le //e), sinon à son début ; sans signal en ~2 images ; le
  //c, sans ce registre, change de page aussitôt (une image peut se
  déchirer). Si la page montrée a déjà l'image (le second `vid_idle` d'un
  tour, celui de `wait_key`, après le son), c'est la page cachée qui
  **rattrape**, sans changer de page ; une touche l'interrompt entre deux
  cases (le tour passe d'abord, ce qui n'est pas dessiné reste noté). Le
  tour suivant ne dessine donc que ce qu'il change. Une page pleine précédait
  (sac…) : la page cachée retrouve ses marges noires et toutes ses cases.
- **Écrit une fois** : en une mise à jour, chaque octet d'une page l'est au
  plus une fois, à sa valeur finale (le test le vérifie avec `storewatch`
  sur les deux pages, sur un tour entier : la page cachée, montrée, puis
  l'autre qui rattrape).

#### Le moteur texte (rangées du HUD, pages pleines)

Celui de la première version DHGR, devenu **paginé** : son état (ce que la
page montre, `dg_shown` ; la liste de sprites dessinée, `dg_drawn` ; les
rangées touchées depuis, `dg_touch`) existe pour chaque page (blocs
`DGPAGE` en `$0800` et `$0C00`) ; `dg_use_page` déplace de `$400` les
opérandes de ses accès (notés par la macro `DGX` dans le segment `DGFIX`,
17 sites) et règle la page d'écriture (`dg_pgo`). En vue de jeu il ne
traite que les rangées 20 à 23 (`dg_rmin`).

- **Géométrie** : image TMS divisée par deux en largeur, 1 pixel couleur
  DHGR = 2 pixels TMS, 1 ligne = 1 ligne, de x = 6 à 133. Les tuiles de 7
  pixels de large ont été écartées : 32 colonnes de texte ne tiennent pas
  dans 16 × 7 pixels, et les icônes du sac et du HUD sont posées au pixel
  TMS près ; avec 8 pixels par tuile, tout tombe exactement, au prix de
  décalages (un caractère chevauche deux groupes de 7 pixels : 7 phases).
- **`vid_addr` / `vid_put`** : la VRAM virtuelle est une vraie copie aux
  mêmes adresses (`$1800-$1B7F`) ; `vid_put` compare l'octet à celui du
  curseur (opérande auto-modifié) : **27 cycles** s'il est inchangé ; s'il
  change, il l'écrit, marque sa rangée pour les deux pages (un octet de la
  table des sprites marque la table), et un nom de texte dans les rangées
  0 à 19 fait de l'écran une page pleine (`dg_txt`, remis à 0 par
  `vid_clear`). `vid_wait_frame` = `RTS` : le cœur l'appelle avant de tout
  reconstruire, dessiner là montrerait des images à moitié faites.
- **Mise à jour d'une page** : (1) les noms de chaque rangée touchée sont
  comparés à `dg_shown` (boucle aux opérandes patchés, ~21 cycles par nom ;
  `dg_san` : tous les caractères vides se valent) : chaque nom différent
  marque le ou les deux groupes de 7 pixels dessous (un octet par groupe, 20
  par rangée) ; (2) la liste de sprites est comparée à celle dessinée sur
  la page : chaque entrée changée marque ses deux boîtes (2 groupes × 2 ou 3
  rangées) ; (3) chaque rangée marquée : la liste de ses sprites, puis
  chaque suite de groupes sales est **composée octet par octet** dans un
  tampon de 8 lignes de 80 octets « de flux » (l'octet 2o = auxiliaire o,
  2o + 1 = principal o ; 3 lignes par page, aucun accès indexé ne franchit
  de page) et écrite.
- **Composition par octets** (`tools/tiles_dhgr.py` calcule les tables, et
  `compose()`, le même algorithme en Python, vérifié contre le modèle pixel
  à la génération) : une ligne d'un caractère = 4 pixels × 4 points = 16
  points à partir du point 24 + 16 c, donc 7 phases (c mod 7) : 3 ou 4
  octets, le premier ajouté (`ORA`) au dernier du caractère précédent, les
  autres posés (`STA`). Par ligne : nom → indice (encre 0..3 × 16 + les 4
  pixels, `dg_ri`), puis une table de 64 octets par octet produit
  (`dg_cp<p><i>`) : **41 cycles par caractère et par ligne**, 10 pour un
  caractère noir. Sprites, entrée la plus haute d'abord : deux moitiés de 4
  pixels peintes par `b = b EOR ((b EOR encre) AND points)`. Écriture :
  8 instructions `STA abs,Y` (une par ligne, adresses patchées par bande et
  par page), deux colonnes par passe, ~10 cycles par octet ; octets
  auxiliaires sous `SEI`, puis principaux.

#### Coûts

Mesures //e (`tests/test_dhgr.py`, graine fixée : les mêmes donjons pour
chaque version ; `tools/profile_dhgr.py` pour le détail), d'une touche à la
nouvelle image **affichée** (le premier `vid_idle` du tour, attente du
balayage comprise) :

| | médiane | 90 % | max |
|---|---|---|---|
| un pas (la fenêtre défile), 63 pas | 74 903 | 91 753 | 108 649 |
| une action sans pas (coup), 57 | 5 328 | 43 354 | 53 788 |

Un tour entier (de la touche à l'attente de la suivante : l'image, le son
puis l'autre page qui rattrape) : médiane 108 834. Dans un tour moyen :
écriture des cases 28 500 (les deux pages), comparaison des clés 8 600,
préparation des cases 5 400, sprites peints 5 300, attente du balayage
3 900, image voulue 2 300, moteur texte (HUD) ~20 000, `vid_put` 3 900,
cœur 14 200, son 21 600. Une page entière redessinée (45 cases + HUD) :
~180 000 cycles ; une page pleine (sac, aide) : ~0,3 s comme avant. Une
case : ~2 000 cycles d'écriture (8 colonnes × 32 lignes), ~3 500 de plus
avec un sprite (case copiée puis peinte).

### 3.1 Budget d'un tour (2026-10-31)

(Mesures de la version DHGR d'avant ROGUE X2, la carte en image TMS
divisée par deux ; les lots du cœur restent.)

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
  finissait alors à `$9017` (1,5 Ko libres sous `$9600`), ROGUE.TMS fait 14 367 octets.

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
   `BRUN ROGUE.DHGR` (chargé en `$3C00`, par-dessus le lanceur ; il se passe
   ensuite du DOS, §6).
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

### ROGUE.DHGR (Apple //e 128 Ko ou //c, sans DOS pendant le jeu)

Les deux pages DHGR (`$2000-$5FFF`, principale et auxiliaire) ne laissent
pas la place au jeu sous le DOS. DOS 3.3 charge le fichier en `$3C00` (le
`BRUN` du lanceur, ou celui de `HELLO`), puis `STARTUP` :

1. lit l'emplacement du lecteur de démarrage (`$B7E9`, pour la sortie) et
   pointe le vecteur RESET sur `rg_reset` ;
2. recopie la ROM du moniteur (`$F800-$FFFF`) dans la RAM de la carte
   langage (lecture ROM, écriture RAM), puis passe en lecture / écriture RAM
   banque 2 (`$C083` deux fois) : `tune.asm` appelle `WAIT` (`$FCA8`) ;
3. recopie `LCCODE` + `LCDATA` (le back-end : moteur texte, vue X2, leurs
   tables) de `$3CDC` à `$D000` ;
4. `JMP start` : le DOS (`$9600-$BFFF`) n'est plus qu'une zone de BSS.

| Zone | Contenu |
|---|---|
| `$0050-$00F6` | page zéro (167 o : le cœur, le moteur texte 43 o, la vue X2 24 o, `rg_ptr` 2 o) |
| `$0800-$0FFF` | `DGPAGE` : l'état du moteur texte pour la page 1 (`$0800` : `dg_shown` 768 o, `dg_drawn` 128 o, `dg_touch` 24 o) et la page 2 (`$0C00`) ; `QUIT_MARK` en `$0FFE` |
| `$1000-$12F7` | `LOWBSS` : carte, visibilité, monstres, objets, sac, ombres de render_map et du HUD |
| `$1400-$167F` | `X2LOW` : les masques des moitiés de 7 pixels (`x2_m`, 512 o), le tampon de composition d'une case (`x2_cbuf`, 128 o) |
| `$1800-$1F0E` | `DHGRBSS` : l'écran TMS virtuel **à ses propres adresses** (`$1800` noms, `$1B00` sprites), le tampon de lignes du moteur texte (`$1C00-$1EFF`), drapeaux par page |
| `$2000-$3FFF` | page DHGR 1 (principale ; et l'auxiliaire) |
| `$4000-$5FFF` | page DHGR 2 (idem) ; au chargement : `STARTUP` (`$3C00-$3CDB`) puis `LCCODE` + `LCDATA` (8,3 Ko), complétés jusqu'à `$6000` |
| `$6000-$9469` | le fichier : `CODE` (le cœur, `plat_quit`, `rg_reset`) 9 120 o, `RODATA` 4 264 o (le cœur, `video_dhgr_data.inc`), `DGFIX` 34 o ; `$946A-$95FF` libres (406 o) |
| `$9600-$99FF` | (le DOS) `X2IMG` : les 8 images de tuiles (1 Ko) |
| `$9A00-$9E05` | `BSS` : clés des cases des deux pages, image voulue, groupes sales du moteur texte ; `$9E06-$BFFF` libres (8,7 Ko) |
| `$D000-$F13D` | carte langage, RAM banque 2 et commune : le back-end (`LCCODE` 6,4 Ko, `LCDATA` 2,1 Ko) ; `$F13E-$F7FF` libres (1,7 Ko) |
| `$F800-$FFFF` | carte langage : la copie de la ROM du moniteur |

Fichier : 22 634 octets (89 secteurs, 486 octets de remplissage avant
`$6000`). Mémoire auxiliaire : seulement ses moitiés des deux pages DHGR.

**Sortie** (ESC au titre, ESC puis Y, Ctrl-RESET : `plat_quit` /
`rg_reset`) : « QU » en `$0FFE`, lecture ROM, écran texte 40 colonnes,
`JMP $Cs00` (le lecteur de démarrage) : la disquette redémarre, `HELLO` voit
la marque (`PEEK (4094)`, `(4095)`), l'efface, écrit « ROGUE: BYE! » et
s'arrête : le prompt BASIC avec DOS 3.3 (la façon de DIRTBIKE, qui pose sa
marque en `$8000` ; ici `$0FFE`, au-dessus de `HELLO` et de ses variables,
loin de ce que le démarrage du DOS écrit). Sur un //e, RESET remet la carte
langage en lecture ROM : le vecteur `$03F2` mène à `rg_reset` en RAM
principale.

### ROGUE (lanceur)

`$6000-$691C` (1 767 o + BSS), 8 o de page zéro. Écrasé par le chargement de
`ROGUE.TMS` / `ROGUE.DHGR` : le `BRUN` du DOS ne revient jamais.
