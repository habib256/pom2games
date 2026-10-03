# LOGO — Apple II / DOS 3.3 (40 ou 80 colonnes)

Port Apple II de l'APPLE-1 LOGO V2.6 de [POM1](https://github.com/habib256/pom1)
(VERHILLE Arnaud), dans son édition GEN2 HGR (`sketchs/gen2/tool_logo_gen2`,
qui compile l'interpréteur partagé `sketchs/tms9918/tool_logo/TMS_Logo_16k.asm`
avec `CODETANK_BUILD` + `LOGO_GEN2`, renommé ici `LOGO_HGR`). Importé depuis GitHub au commit
`e2a4748` (2026-09-11).

Tortue HGR, procédures avec paramètres et récursion terminale, `REPEAT`,
`IF`/`IFELSE`, variables, `SETPC`, sprites `SETSHAPE`, texte bitmap `LABEL` /
`SAY`, `LIST` / `EDIT`, démos `DEMO` et `DEM2`. Le manuel complet de la V2.6 est
dans [`doc/`](doc/) (français et anglais).

    make            # -> ../dist/LOGO.dsk  (image DOS 3.3 5"1/4 amorçable)
    make run        # démarre l'image dans POM2 (profil Apple //e)

Prérequis : cc65 (`brew install cc65`) et python3. Tout le reste est dans
`../dev`, pistes système DOS 3.3 comprises. `make run` lance POM2 installé
(`/Applications/POM2.app`, ou `make run POM2=chemin/vers/POM2`).

## Machine et colonnes

- **Apple //e ou //c avec carte 80 colonnes** : LOGO démarre lui-même le
  firmware 80 colonnes (pas besoin de `PR#3`) et la console s'affiche en
  80 colonnes.
- **//e sans carte 80 colonnes, ou Apple ][ / ][+** : console en 40 colonnes.

`COLUMNS 40` et `COLUMNS 80` basculent la largeur ; `COLUMNS 80` répond
`? BAD ARG` quand les 80 colonnes n'existent pas. `BYE` rend la main à DOS
dans la largeur en cours.

## Écran : texte, mixte, graphique

Sur l'Apple-1, LOGO avait deux écrans (le terminal et la carte GEN2). Sur
l'Apple II ils se partagent l'écran, comme dans Apple Logo :

| Commande                | Touche | Écran |
|-------------------------|--------|-------|
| `TS` / `TEXTSCREEN`     | Ctrl-T | console texte plein écran |
| `SS` / `SPLITSCREEN`    | Ctrl-S | tortue HGR + 4 lignes de console en bas (mixte) |
| `FS` / `FULLSCREEN`     | Ctrl-L | tortue HGR seule (la frappe continue, invisible) |

Les touches marchent à l'invite et pendant qu'un programme tourne. Au
démarrage l'écran est mixte. Une commande qui dessine (tortue, `LABEL`, `SAY`,
`LIST NAME`) repasse en mixte si l'on était en texte ; `HELP` passe en texte ;
`EDIT` occupe le plein écran le temps de l'édition puis revient au mode
précédent.

## Saisie

- ← ou DEL efface le dernier caractère (le `_` de Wozmon marche aussi).
- ESC ou Ctrl-G interrompt une boucle (`REPEAT FOREVER`, procédure).
- `BYE` revient au prompt DOS ; Ctrl-RESET aussi, proprement.

## Différences avec l'original Apple-1 / GEN2

- Console sur l'écran de l'Apple II via `COUT` (même contrat que `ECHO` de
  Wozmon), en 40 ou 80 colonnes ; commandes et touches TS / SS / FS et
  `COLUMNS` (`src/screen.asm`).
- Clavier Apple II (`../dev/lib/apple2/kbd.asm`), curseur `_` et effacement à
  l'invite.
- `BYE` et Ctrl-RESET : retour à DOS avec la page zéro restaurée
  (`../dev/lib/apple2/exit.asm`).
- Pas de V-blank sur Apple II : l'attente de synchronisation des sprites
  (`hgr_emote_vsync`) est vide.
- Le backend HGR (`src/hgr_logom2.asm`) n'utilise que la page 1 : avec le
  firmware 80 colonnes, `PAGE2` commute de la mémoire au lieu de l'affichage.
- Trois bogues d'origine corrigés :
  - `EDIT` (et tout appelant qui compte sur `pix_x`/`pix_y`) écrivait le texte
    en diagonale : le blitter de glyphes GEN2 ne rendait pas la position
    d'origine (`src/text_bitmap.asm`) ;
  - `LIST NAME` ne rendait jamais la main : `find_proc` repositionne la ligne
    d'après une variable que seul l'appel de procédure remplit, la ligne était
    relue depuis le début et la liste redessinée sans fin (même piège évité de
    justesse par `EDIT`) ;
  - les exemples de `HELP 8` / `HELP 9` utilisent `RT`, que la table des
    commandes ne connaissait pas : `RT` et `LT` sont ajoutés comme alias de
    `TR` et `TL`.

## Contenu

    src/logo.s            l'interpréteur (TMS_Logo_16k.asm de POM1, adapté)
    src/screen.asm        écran Apple II : TS / SS / FS, 40 / 80 colonnes, sortie
    src/a2logo.inc        noms Apple-1 -> Apple II (ECHO = COUT)
    src/hgr_logom2.asm    backend HGR (gen2_logom2.asm de POM1)
    src/text_bitmap.asm   glyphes 8x8 sur le HGR (gen2_text_bitmap.asm)
    src/bubble.asm        bulle de SAY (gen2_bubble.asm)
    src/buffer_editor.asm éditeur EDIT
    src/math.asm          sinus, aléatoire, décimal
    src/sprite_helpers.asm, src/sprites_emotes.asm, src/tms9918.inc
    src/logo.cfg          config ld65 (plan mémoire ci-dessous)
    src/hello.bas         HELLO : 10 PRINT CHR$(4);"BRUN LOGO"
    doc/                  manuels V2.6 (FR / EN) et README d'origine
    ../dist/LOGO.dsk      l'image produite

Bibliothèques : `../dev/lib/apple2` (clavier, impression, sortie DOS),
`../dev/lib/hgr` (tables de lignes et de colonnes, police 8x8),
`../dev/tools/dos33.py`.

## Plan mémoire

    $0050-$0093  zéro-page (sauvegardée au lancement, restaurée par BYE)
    $0400-$07FF  page texte (40 ou 80 colonnes)
    $0800-$0FFF  programme HELLO gardé par DOS
    $1000-$1E55  pile de contrôle, tables des variables et procédures
    $2000-$3FFF  HGR page 1 : l'écran de la tortue
    $4000-$882E  interpréteur (fichier BRUN de 18,5 Ko), puis tampons
    $9600-$BFFF  DOS 3.3
