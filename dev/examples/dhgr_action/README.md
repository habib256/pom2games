# DHGR ACTION — Apple //e 128 Ko / //c, ProDOS

Une petite démo d'action en double haute résolution sur le **compositeur de
sprites** de `dev/lib/hgrc` (`dhgr_spr_*`, voir
[« Flicker-free sprites »](../../lib/hgrc/README.md#flicker-free-sprites-compositor)),
en **deux pages** (`DHGR_SPR_DOUBLE`) : chaque image se compose sur la page
cachée, puis s'affiche au front du VBL.

- une arène fixe de 20 × 22 tuiles de 7 × 8 pixels couleur (sol en damier :
  tuiles RECTS ; murs : tuiles TILE de quartets), lignes 16 à 191 ;
- cinq ennemis CHUNKY 6 × 6 animés sur deux images, qui rebondissent sur
  les murs (retournés en miroir quand ils vont à gauche) ;
- le vaisseau du joueur (CHUNKY 7 × 7) et son tir (un rectangle 1 × 4) ;
- collisions par boîtes englobantes : un ennemi touché réapparaît en haut
  (+10 points, un bip `a2_tone` de `sound.asm`), un ennemi qui touche le
  vaisseau coûte une vie (son grave, vaisseau clignotant 60 images) ;
- score, vies et mode en texte `dhgr_small` (lignes 0 à 15, hors de la zone
  du compositeur), dessinés sur la page cachée, seulement les caractères
  que cette page n'affiche pas encore.

Touches : flèches ou I J K L (déplacement tant que la touche est tenue),
Espace : tir, S : manette / clavier (manette : direction, bouton 0 : tir),
F : affichage du coût d'une image, Échap : retour à ProDOS.

```sh
make -C dev/examples/dhgr_action          # -> build/DHGRACTION.po (pas dist/)
make -C dev/examples/dhgr_action run      # POM2, //e
make -C dev/examples/dhgr_action test     # //e et //c (a2shot)
make test-dhgr-action                     # le même, depuis la racine
```

## Ce que la démo montre

- **Rien n'est jamais écrit dans la page affichée.** `dhgr_spr_update()`
  écrit sur la page de dessin ce qui a changé depuis que *cette page* a été
  dessinée (ses propres dégâts + ceux que l'autre page a reçus entre-temps),
  chaque octet une fois, avec sa valeur finale ; `dhgr_spr_present()`
  attend le front du VBL, montre cette page et dessine sur l'autre.
- **L'horloge vidéo** (`dev/lib/apple2c/apple2vbl`) : sur le //e, `$C019`
  est lu en boucle (mode 1) ; sur le //c (ou un //e avec une AppleMouse),
  l'interruption VBL de la souris compte chaque balayage (mode 2). Sans
  horloge, `a2_frame_wait` (attente bornée).
- **La touche F** affiche « C » suivi du nombre de cycles d'une image,
  moyenne sur 32 images : (balayages comptés × 17 030) / 32. Le compte
  n'est exact qu'avec l'interruption VBL (//c, //e + AppleMouse) : sur un
  //e sans souris, seul `dhgr_spr_present` lit `$C019`, les balayages passés
  pendant le calcul ne sont pas vus et la démo affiche `-----`.

## Coût mesuré (POM2, `test_dhgr_action.py`)

| Machine | Travail d'une image (de `frame_end` à `dhgr_spr_present`) | Une image tous les |
|---|---:|---:|
| //e, `$C019` | 63 000 à 67 000 cycles | 4 balayages (68 120 cycles, 15 images/s) |
| //c, VBL souris | 66 000 à 70 000 cycles | 4 à 5 balayages (12 à 15 images/s) |

Le //c paie en plus le gestionnaire d'interruption à chaque balayage.
Dans une image : environ 16 000 cycles d'empaquetage + écriture (~100
groupes de 4 octets), 15 000 de peinture des tuiles RECTS, 7 000 de
sprites CHUNKY, 6 000 de parcours des tuiles, 10 000 de gestion des dégâts
(dont la fusion), 8 000 de logique en C. La première image (toute l'arène,
puis de nouveau sur l'autre page) coûte environ 1,6 million de cycles.
Les ennemis vont d'un pixel par image : à deux pixels, les boîtes
grandissent et l'image passe à 5 balayages. Programme : 11,4 Ko (code
8,2 Ko dont le compositeur, données 2,9 Ko, BSS 1,3 Ko), chargé en $6000.

## Partir de là pour un jeu

1. Copier le dossier (à côté de `chromabreak/`, mettre `DEV ?= ../dev`) et
   renommer `ACTION.SYS` / `ACTION.SYSTEM` dans `src/boot.s` et le
   `Makefile`. `src/startup.s` déplace le programme en $6000 (sysreloc de
   `dev/lib/prodos`), `src/boot.s` est le lanceur ProDOS (`sysboot.s`).
2. Garder l'ordre de la boucle : entrées, logique, `dhgr_spr_set` des
   emplacements (0 au fond, le dernier devant), texte de la page cachée,
   `dhgr_spr_update()`, `dhgr_spr_present()`.
3. Au départ : `dhgr_init()`, les deux pages effacées, l'horloge
   (`mouse_init` + `a2_vbl_irq_init`, sinon `a2_vbl_init`), `dhgr_spr_init`
   (tampon de 255 octets), la zone, le fond, `dhgr_spr_invalidate` sur toute
   la zone, puis `dhgr_draw_page(2)` : la page affichée (1) et la page de
   dessin doivent différer.
4. Un fond qui change (une porte, une case ramassée) : changer la carte ou
   le jeu de tuiles, puis `dhgr_spr_invalidate` de la case ; les deux pages
   la reçoivent.
5. Hors de la zone (le texte du haut), dessiner seulement sur la page de
   dessin et se souvenir de ce que chaque page montre (ici `shown1`,
   `shown2`).
6. Le fond est la plus grosse dépense : des tuiles RECTS (un ou deux
   rectangles) coûtent environ deux fois moins que des tuiles TILE ; un fond
   uni (`dhgr_spr_solid`) encore moins.

## Options du compositeur utilisées

`SPR_DEFS := -D DHGR_SPR_DOUBLE=1` pour tous les membres (bibliothèque du
programme `build/platform.lib`, `HGRC_DHGR_SPR_SRCS`) ; `DHGR_SPR_MAX` par
défaut (8 emplacements, 7 utilisés). Les membres liés : appels, mise à
jour, écriture, peintres, `dhgr_spr_area`, tuiles, formes CHUNKY/TILE
(`dhgr_cv_bitmap.s`), `dhgr_spr_present`. Pas de surcouche (pointeur) : ni
`dhgr_spr_overlay.s` ni `dhgr_spr_cursor.s`.

Matériel : //e **révision B** avec carte 80 colonnes **étendue** (64 Ko
auxiliaires) ou //c ; 65C02 (le lanceur refuse un //e d'origine). Le /RAM
de ProDOS est vidé pendant le jeu (`PD_VIDEO_DISCARD_RAM`) et reconstruit
en sortant.

Auteur : VERHILLE Arnaud. Licence : [GPL-3.0](../../../LICENSE).
