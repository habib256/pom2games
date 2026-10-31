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
victoire, aide, carte révélée. `dungeon.asm`, `shadowcast.asm`, `prng16.asm`,
`multiply.asm`, le tileset et les sprites sont des copies inchangées.

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
  8 pixels par tuile, tout tombe exactement, au prix d'un empaquetage (un
  caractère chevauche deux groupes de 7 pixels).
- **`vid_addr` / `vid_put`** : la VRAM virtuelle est une vraie copie aux
  mêmes adresses (`$1800-$1B7F`) ; `vid_put` écrit l'octet (opérandes
  auto-modifiés), et s'il change, marque la ligne de texte (noms) ou la liste
  de sprites. ~40 cycles pour un octet inchangé (render_map en écrit 640 par
  tour). `vid_wait_frame` = `RTS` : le cœur l'appelle avant de tout
  reconstruire, dessiner là montrerait des images à moitié faites.
- **`vid_idle`** (avant chaque attente de touche, à chaque image d'une dague
  lancée) : (1) les noms de chaque ligne marquée sont comparés à `dg_shown`
  (ce que l'écran montre) : chaque nom différent marque le ou les deux
  groupes de 7 pixels dessous, dans un bitmap de 20 bits par ligne (un
  `vid_clear` suivi de la même carte ne coûte rien : c'est ce que fait chaque
  image du lancer) ; (2) la liste de sprites est comparée à celle dessinée :
  chaque entrée changée marque ses deux boîtes ; (3) chaque suite de groupes
  sales de chaque ligne est refaite ligne d'écran par ligne d'écran dans un
  tampon d'un octet par pixel : caractères (4 chargements par caractère, une
  table par (ligne, pixel) donne directement le quartet DHGR), sprites de la
  bande (le dernier d'abord : l'entrée 0 devant, comme la puce),
  empaquetage en place (7 quartets → 4 octets, 9 tables de 16 o, ~60 cycles
  par groupe), écriture : octets auxiliaires sous `SEI` (RAMWRT aux,
  ~400 cycles par ligne entière), puis principaux. Une suite sans caractère
  allumé ni sprite est écrite noire directement. Chaque octet de la suite est
  écrit une fois, à sa valeur finale : pas de scintillement, une seule page.
- **Coûts** (//e, mesurés par `tests/test_dhgr.py`) : écran entier ~935 000
  cycles (0,9 s), un sprite recoloré (flash) ~27 000 cycles, un tour
  ordinaire 0,15 à 0,5 s de la touche à l'attente suivante, dont 60 à 80 %
  de dessin (le reste : champ de vision, monstres, `render_map`).
- **Pistes** si plus de vitesse était voulue : écriture avec opérandes absolus
  patchés (~10 % de l'écriture), suites voisines fusionnées (moins de mise en
  route), groupes noirs sautés à l'empaquetage.

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
| `$0050-$00BD` | page zéro du jeu (110 o : cœur, `vdp_*`, FOV, `tune_ptr`, `txt_*`, `tms_src`, `ez_ptr/count`) |
| `$0400-$07FF` | page texte Apple : l'avis |
| `$0800-$0FFF` | HELLO (gardé par le DOS) |
| `$1000-$12D3` | `LOWBSS` : carte, visibilité, monstres, objets, sac (468 o) + copie de la page zéro du DOS (256 o) |
| `$2000-$3FFF` | libre (pas de HGR : l'Apple reste en texte) |
| `$4000-$767A` | le fichier : `STARTUP` (entrée = 1er octet), `CODE` 11 899 o, `RODATA` 1 812 o (tileset 2 Ko compris dans CODE, sprites, textes, sons), `VDPFIX` 60 o, `BSS` 19 o |
| `$767B-$95FF` | libre (7,9 Ko) |
| `$9600-$BFFF` | DOS 3.3 |

`$4000` = l'adresse de la cartouche Apple-1. Fichier : 13 922 octets
(56 secteurs). Le DOS reste : ESC y retourne, et la place suffit.

### ROGUE.DHGR (Apple //e 128 Ko ou //c, DOS 3.3 gardé)

| Zone | Contenu |
|---|---|
| `$0050-$00CA` | page zéro (123 o : cœur 99 o + back-end DHGR 24 o) |
| `$0800-$0FFF` | HELLO (gardé par le DOS) |
| `$1000-$12D3` | `LOWBSS` : comme ROGUE.TMS (carte, visibilité, monstres, objets, sac, page zéro du DOS) |
| `$1800-$1E3C` | `DHGRBSS` : l'écran TMS virtuel **à ses propres adresses** (`$1800-$1AFF` noms, `$1B00-$1B7F` sprites, 1 Ko avec la marge), la liste de sprites dessinée (128 o), les bits sales (96 o), la ligne de travail (160 o), les caractères et sprites de la bande |
| `$2000-$3FFF` | page DHGR 1, banque principale (et `$2000-$3FFF` de la banque auxiliaire) |
| `$4000-$8082` | le fichier (15 736 o, 63 secteurs) : `STARTUP`, `CODE` 10 302 o (dont le back-end, 1,4 Ko), `RODATA` 5 313 o (dont 5 Ko au back-end : caractères en tables « un pixel par octet » 4 Ko, sprites 288 o, tables d’empaquetage et de géométrie), `BSS` 779 o (dont `dg_shown`, les noms à l'écran, 768 o) |
| `$8083-$95FF` | libre (5,5 Ko) |
| `$9600-$BFFF` | DOS 3.3 |

La mémoire auxiliaire ne sert qu'à la page DHGR : tout le reste tient en
mémoire principale.

### ROGUE (lanceur)

`$6000-$691C` (1 767 o + BSS), 8 o de page zéro. Écrasé par le chargement de
`ROGUE.TMS` / `ROGUE.DHGR` : le `BRUN` du DOS ne revient jamais.
