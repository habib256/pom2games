# ROGUE — interface vidéo (cœur ↔ back-end)

*[← ROGUE](../README.md) · [PORT.md](PORT.md)*

Le disque `dist/ROGUE.dsk` porte **deux binaires du même jeu** :

| Fichier       | Machine                                   | Back-end vidéo                 | Propriétaire |
|---------------|-------------------------------------------|--------------------------------|--------------|
| `ROGUE`       | lanceur (toute machine)                   | page texte Apple               | builder TMS  |
| `ROGUE.TMS`   | Apple II+ 48 Ko et plus + carte E-Z Color | `src/video_tms.asm` (TMS9918A) | builder TMS  |
| `ROGUE.DHGR`  | Apple //e 128 Ko ou //c, sans la carte    | `src/video_dhgr.*`, `src/video_x2.*` (DHGR) | builder DHGR |

Les deux binaires assemblent **le même cœur** (`src/core/`) : donjon, champ de
vision, monstres, objets, sac, combat, logique du HUD, sons, clavier. Le cœur ne
touche jamais le matériel vidéo : il parle à un **écran TMS9918 virtuel** à
travers les sept routines ci-dessous. Le back-end TMS les envoie à la vraie
puce ; le back-end DHGR les émule (grille de caractères + liste de sprites) et
dessine la carte à sa façon (ROGUE X2 : une fenêtre de grandes cases centrée
sur le héros, [PORT.md](PORT.md) §3).

## 1. Le modèle : une « VRAM virtuelle » d'écriture seule

Le cœur est le code POM1 d'origine : il écrit un flux d'octets dans la VRAM du
TMS9918 en mode Graphics I. On garde ce modèle tel quel, réduit à deux zones :

| Adresse virtuelle | Taille | Contenu |
|---|---|---|
| `$1800-$1AFF` | 768 o | **table des noms** : 32 colonnes × 24 lignes de caractères 8×8, octet = numéro de caractère (0..255). Adresse = `$1800 + 32·ligne + colonne`. |
| `$1B00-$1B7F` | 128 o | **table des sprites (SAT)** : jusqu'à 32 entrées de 4 octets `Y, X, NOM, COULEUR`. |

Le curseur d'écriture **s'auto-incrémente** après chaque octet, y compris en
passant d'une ligne de noms à la suivante et de `$1AFF` à `$1B00` (le cœur ne
le fait pas, mais rien ne l'interdit). Le cœur **ne relit jamais** la VRAM.

Les motifs (caractères, sprites) et les couleurs sont **fixes** : chargés une
fois par `vid_init`, le cœur ne les modifie jamais. Ce sont des données du
back-end (voir §4).

### Sprites

- 16 × 16 pixels, monochromes, couleur = index de palette TMS9918 (1..15 ;
  0 = transparent).
- `Y` = ligne de pixel **moins un** sur le vrai TMS9918 (le sprite apparaît à
  la ligne `Y+1`). Le cœur pose `Y = rangée·16`, `X = colonne·16` : le back-end
  DHGR peut dessiner à `Y` ou `Y+1`, au choix (un pixel).
- **`Y = $D0` termine la liste** : les entrées suivantes sont ignorées. Le
  cœur réécrit **toute** la liste à chaque tour (`place_all_sprites`) en
  terminant par `$D0` ; `vid_sprites_off` pose `$D0` en entrée 0.
- `NOM` = numéro de motif 8×8 du TMS, toujours multiple de 4 (un motif 16×16
  = 4 motifs) : voir la table des sprites §4.2. Un sprite 32×32 (le boss) =
  4 entrées voisines (`NOM` 56/60/64/68, aux 4 quarts).
- Pas de transparence entre sprites et fond autre que : pixel de sprite à 1 =
  couleur du sprite, pixel à 0 = on voit le fond (caractères). Entre sprites,
  l'entrée de plus petit numéro passe devant.
- La limite matérielle de 4 sprites par ligne du TMS9918 n'est **pas** à
  reproduire (le cœur range déjà le HUD pour ne pas la dépasser).

## 2. Les routines (labels exacts)

Toutes s'appellent par `JSR`. « Préserve » = valeur identique au retour.
Mode décimal toujours effacé ; interruptions masquées (`SEI`) pendant tout le
jeu côté TMS ; le back-end DHGR fait ce qu'il veut tant qu'il rend la main.

| Label | Entrée | Sortie / effet | Préserve | Détruit |
|---|---|---|---|---|
| `vid_init` | — | une seule fois au démarrage du jeu (et à chaque redémarrage après la mort : idempotent) : mode vidéo, motifs, couleurs, motifs de sprites, table des noms à 0, liste de sprites vide, affichage allumé | — | A, X, Y |
| `vid_clear` | — | table des noms entière = caractère 0 (noir) ; ne touche pas aux sprites | — | A, X, Y |
| `vid_sprites_off` | — | SAT[0].Y = `$D0` (plus aucun sprite) | — | A, X, Y |
| `vid_addr` | A = octet bas, X = octet haut de l'adresse virtuelle (bit 6 = `$40` « écriture » **toléré et ignoré** : `$58` et `$18` désignent la même page) | place le curseur | X, Y | A |
| `vid_put` | A = octet | écrit A au curseur, curseur + 1 | **A, X, Y et P (flags)** | rien |
| `vid_wait_frame` | — | attend le début de la prochaine image (≤ ~1/60 s ; jamais de blocage infini) | A, X, Y | P |
| `vid_idle` | — | appelée par le cœur juste avant d'attendre une touche : un back-end qui compose en différé finit son image ici | X, Y | A, P |
| `vid_off` | — | écran du jeu éteint (sortie vers le DOS) | — | A, X, Y |

Règles :

- `vid_put` est l'appel chaud (SAT : ≤ 128 par tour ; la carte : depuis le
  2026-10-31 le cœur garde une ombre de la carte et n'écrit que les cases
  qui changent, sauf après un `vid_clear` : 640 noms) : il doit être rapide
  et **tout** préserver (le cœur boucle sur X/Y autour, et teste parfois des
  flags posés avant l'appel).
- Une écriture ne doit pas être visible « à moitié » trop longtemps : le cœur
  appelle `vid_wait_frame` avant les grosses reconstructions, et `vid_idle`
  avant chaque attente de touche (fin de tour, modales, titre, mort) et, en
  fin de tour, avant de jouer le son du tour (l'image d'abord). Un
  back-end DHGR peut donc marquer les cellules sales dans `vid_put` et ne
  redessiner (fond puis sprites) que dans `vid_idle` / `vid_wait_frame`.
- Pas d'autre appel : le cœur ne connaît ni registres VDP, ni pages DHGR, ni
  mémoire auxiliaire.

### Côté TMS (référence, `src/video_tms.asm`)

`vid_addr` = deux écritures de contrôle, `vid_put` = `STA data` + 3 `NOP` +
`RTS`. Contrat silicium (≥ 18 cycles entre deux accès VDP) tenu **dans** le
back-end : chaque routine finit par ≥ 6 cycles sans accès avant son `RTS`, donc
deux `vid_put` consécutifs sont espacés d'au moins 4 + 6 + 6 + 6 = 22 cycles
(STA→STA) quoi que fasse l'appelant. Le cœur ne contient plus aucun `pad18`.

## 3. Ce que le cœur attend aussi de chaque binaire (plate-forme)

| Label | Fourni par | Rôle |
|---|---|---|
| `start` | cœur | entrée du jeu proprement dit (après la détection) ; `JMP start` = recommencer une partie |
| `plat_quit` | binaire | ESC + Y en jeu, ESC au titre : éteindre (`vid_off`), rendre le DOS (`apple2_exit` ; `ROGUE.DHGR`, qui s'est passé du DOS : marque + redémarrage de la disquette, PORT.md §6) |
| `plat_sound_status` | binaire | A = `snd_on` (0/1) : le binaire l'affiche où il veut (TMS : ligne 22 de la page texte Apple ; DHGR : `RTS`) |

Le cœur inclut lui-même `sound.asm`, `tune.asm` (son de l'Apple II), mais pas
`exit.asm` / `dos.asm` : c'est le binaire (boot) qui les inclut.

### Page zéro

Le cœur réserve sa page zéro dans le segment `ZEROPAGE` (≈ 110 octets, liste
dans le fichier `.map` ; `dev/cc65` : segment à `$50`). Le back-end déclare ses
propres octets dans le même segment (le linker les place) ; il ne doit **pas**
toucher ceux du cœur, sauf `tmp` (scratch libre entre deux appels du cœur) —
et ne doit pas supposer que `tmp` survit à un `vid_*`. Les octets du cœur que
le back-end peut **lire** sans risque : aucun (tout passe par les appels).

### Segments demandés par le cœur

`ZEROPAGE`, `CODE`, `RODATA`, `BSS` (petites variables) et `LOWBSS` (≈ 370 o :
carte, visibilité, monstres, objets, sac). Le cfg de chaque binaire les place.

## 4. Les données graphiques (communes, format TMS)

Sources à convertir par l'outil du back-end DHGR (ne pas les modifier) :

- `src/gfx/tileset_rogue.inc` — `tileset_rogue` : 256 caractères × 8 octets
  (bit 7 = pixel de gauche), `tileset_color_table` : 32 octets, **une couleur
  par groupe de 8 caractères**, quartet haut = encre (pixel 1), quartet bas =
  fond (pixel 0).
- `src/gfx/sprite_pats.inc` — `sprite_pats` : 448 octets = 14 sprites 16×16 de
  32 octets (TL, BL, TR, BR en blocs de 8 lignes, ordre TMS : colonne gauche
  haut, gauche bas, droite haut, droite bas) aux noms 0, 4, 8 … 52.
- `src/gfx/sprites_boss.asm` — `boss_sprite_pats` : 128 octets, noms 56..68.

Palette TMS9918 (index → couleur) : 0 transparent, 1 noir, 2 vert moyen,
3 vert clair, 4 bleu foncé, 5 bleu clair, 6 rouge foncé, 7 cyan, 8 rouge
moyen, 9 rouge clair, 10 jaune foncé, 11 jaune clair, 12 vert foncé,
13 magenta, 14 gris, 15 blanc.

### 4.1 Caractères (noms de la table des noms)

| Caractères | Usage | Couleur (groupe) |
|---|---|---|
| 0..3 | `CHAR_EMPTY` : sol / noir (0 = cellule hors champ de vision) | `$E1` gris / noir |
| 4..7 | `CHAR_WALL` : mur (4 quarts TL, TR, BL, BR d'une tuile 16×16) | `$E1` |
| 8..11 | `CHAR_STAIRS_DOWN` : escalier qui descend | `$A1` jaune foncé / noir |
| 12..15 | `CHAR_DOOR` : porte | `$A1` |
| 16..19 | `CHAR_STAIRS_UP` : arche (inutilisée en jeu) | `$B1` jaune clair / noir |
| 20..23 | `CHAR_TRAP_PIT` : fosse révélée | `$B1` |
| 24..31 | `CHAR_GOLD`, `CHAR_POTION` (réservés) | `$71` cyan / noir |
| 32..127 | police Quale, **ASCII** (`' '`=32, `'0'`=48, `'A'`=65 ; majuscules, chiffres, `[ ] : ? . - !`) | `$F1` blanc / noir |
| 128..255 | vides | `$F1` |

Une tuile logique de la carte (16 × 10 tuiles de 16×16 px) = 4 caractères
`base+0` (haut gauche), `base+1` (haut droit), `base+2` (bas gauche),
`base+3` (bas droit) aux rangées de noms `2r, 2r+1`, colonnes `2c, 2c+1`.
Rangées de noms 0..19 = carte ; 20..23 = HUD (texte + icônes-sprites).

### 4.2 Sprites (`NOM`)

| NOM | Sprite | Couleur posée par le cœur |
|---|---|---|
| 0 | joueur (aventurier) | 5 bleu clair (8 rouge quand il est touché) |
| 4 | UNDEAD (zombie) | 15 |
| 8 | GHOST | 14 |
| 12 | DEATH (faucheuse) | 10 |
| 16 | nourriture (ration) | 11 |
| 20 | SKELETON | 7 |
| 24 | dague (au sol, lancée, icône HUD) | 14 |
| 28 | potion | 13 |
| 32 | parchemin | 7 |
| 36 | épée | 15 |
| 40 | tunique | 6 |
| 44 | amulette | 10 |
| 48 | TROLL | 2 |
| 52 | torche | 9 |
| 56, 60, 64, 68 | boss 32×32 (quarts HG, HD, BG, BD) | 8 |

Tout monstre touché ce tour-ci est posé en couleur 8 (rouge).

## 5. Fichiers

    src/core/rogue_core.inc   le jeu (POM1, accès VDP remplacés par vid_*)
    src/core/tiles.inc        CHAR_* (ids de caractères des tuiles)
    src/core/sfx.inc          sons : file d'événements, clavier (key_xlate)
    src/core/music.inc        généré par tools/music.py
    src/core/dungeon.asm, shadowcast.asm, prng16.asm  (POM1 ; shadowcast :
                              mêmes résultats, pentes en rangs)
    src/gfx/tileset_rogue.inc, sprite_pats.inc, sprites_boss.asm    (données)
    src/video_tms.asm         back-end TMS9918 (vid_*, pilote Mode 1 de POM1)
    src/ezvdp.inc             accès VDP relogeables (table VDPFIX, vdp_patch)
    src/boot.inc              ROGUE.TMS : entry, ez_detect, page texte Apple,
                              plat_quit, plat_sound_status
    src/txtpage.inc           pages de texte Apple sans COUT (lanceur, TMS)
    src/rogue_tms.s, .cfg     binaire ROGUE.TMS ($4000)
    src/launcher.s, .cfg      binaire ROGUE ($6000) : choix TMS / DHGR / erreur
    src/dhgr_stub.s           ROGUE.DHGR bouche-trou (tant que rogue_dhgr.s manque)
    src/video_dhgr.*          back-end DHGR : pages, moteur texte (builder DHGR)
    src/video_x2.*            back-end DHGR : la vue de jeu à la ROGUE X2
    src/rogue_dhgr.s          binaire ROGUE.DHGR       (builder DHGR)

Gabarit d'un binaire (voir `src/rogue_tms.s`, include path `-I src` +
`dev/lib/apple2` : la règle du Makefile) :

```asm
.include "apple2.inc"
; boot : segment STARTUP (premier octet du fichier) : APPLE2_PREAMBLE,
; JSR apple2_zp_save, vérifications, puis JMP start ; plat_quit (vid_off +
; apple2_exit), plat_sound_status (A = snd_on)
.include "core/rogue_core.inc"   ; le cœur (+ sound.asm, tune.asm : SOUND_GATE
                                 ; et TUNE_MUTE = snd_on, déjà faits)
.include "video_dhgr.asm"        ; vid_* (+ ses données)
.segment "LOWBSS"
apple2_zp_buf: .res 256          ; (ou ailleurs)
.include "exit.asm"
```

Le boot du binaire initialise `snd_on` (1 = son) et `sfx_req` (0) avant
`JMP start` : le cœur ne le fait pas (un redémarrage garde le choix S). Le cœur fait `SEI`,
`CLD` et remet la pile (`LDX #$FF / TXS`) au début de `start`.

## 6. Makefile

`rogue/Makefile` construit `ROGUE`, `ROGUE.TMS` et `ROGUE.DHGR` sur le même
disque. Règle à compléter par le builder DHGR :

    $(BUILD)/rogue_dhgr.bin: src/rogue_dhgr.s src/video_dhgr.* src/video_x2.* $(CORE) src/rogue_dhgr.cfg

Tant que `src/rogue_dhgr.s` n'existe pas, le Makefile met à la place un
binaire bouche-trou (`src/dhgr_stub.s`) qui affiche « VERSION DHGR PAS ENCORE
CONSTRUITE » et rend le DOS : le lanceur et ses tests marchent sans attendre.
Adresse de chargement : libre (déclarée dans `DHGR_LOAD` du Makefile :
`$3C00` = le début de `src/rogue_dhgr.cfg`) ; le lanceur fait `BRUN
ROGUE.DHGR` (DOS 3.3, //e 128 Ko : la mémoire auxiliaire est à la disposition
de ROGUE.DHGR, DOS ne s'en sert pas ; ROGUE.DHGR se passe ensuite du DOS).
