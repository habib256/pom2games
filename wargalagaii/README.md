# WARGALAGA II

**En préparation : aucun code de jeu pour l'instant.** Ce dossier contient le
cahier des charges ([`TODO.md`](TODO.md)), la référence vérifiée du jeu modèle
([`docs/warblade-reference.md`](docs/warblade-reference.md)) et un squelette de
`Makefile`. Le jeu n'est pas encore dans les listes `all` / `test` du
`Makefile` racine.

Shoot'em up fixe dans l'esprit de **Warblade** (Edgar M. Vigdal, PC/Mac 2003),
lui-même réécriture de son *Deluxe Galaga* (Amiga, années 1990) : vaisseau
en bas de l'écran, gauche/droite seulement, aliens qui entrent en vague, se
rangent en formation puis plongent ; pièces et bonus qui tombent, boutique
tous les 4 niveaux, boss tous les 25, 100 niveaux qui bouclent plus durs,
rangs gagnés avec 6 marques de couleur, sous-jeux Meteor Storm et Memory
Station. Ce n'est **pas un portage** : aucun code ni aucune donnée de
Warblade n'est repris ; on reprend les règles, réduites à ce que tient un
Apple II.

Sources cherchées pour « WarGalaga » : rien sous ce nom dans ce dépôt, dans
`~/src` ni dans [POM1](https://github.com/habib256/pom1). POM1 a en revanche
un **TMS Galaga** (`sketchs/tms9918/game_galaga/TMS_Galaga.asm`, 5 127 lignes,
carte TMS9918, sprites matériels) : 3 aliens à la fois, 4 plongées
(droite, zigzag, diagonale, boucle), formation qui oscille, super boss tirant
en rosace (table d'angles), bonus double/triple/bouclier/crâne. Il ne se
porte pas (tout repose sur les 32 sprites matériels du TMS9918), mais ses
plongées et son réglage par vague servent de point de départ aux tables.

## Machine cible

**Apple //e enhanced ou //c, 128 Ko, 65C02, ProDOS 8** (choix de
l'utilisateur, 2026-10-22). Pas de version II+. Même profil que
[CHROMABREAK](../chromabreak/README.md), dont on reprend l'amorce, le
démarrage et la cadence.

- **65C02 exigé** (`STZ`, `BRA`, `PHX/PLX`, `(zp)`, `TRB/TSB`, mode décimal
  fiable pour le score BCD) : //e *enhanced* ou //c. Une //e non améliorée
  (NMOS) reçoit un message au démarrage et rend la main, comme
  `chromabreak/src/boot.s` (test `INC A` = `NOP` sur NMOS). IIgs : non visé
  (polarité VBL différente, `apple2frame` l'exclut) ; s'il démarre, tant
  mieux, sans test.
- **128 Ko** : la mémoire auxiliaire sert de réserve (dessins d'aliens des
  25 paquets, trajectoires, musiques PT3, écrans de boutique), copiée en
  mémoire principale entre deux niveaux. `/RAM` est réclamé au démarrage et
  reformaté à la sortie (`dev/lib/prodos/video.s`,
  `PD_VIDEO_DISCARD_RAM`, comme CHROMABREAK).
- **ProDOS** plutôt que DOS 3.3 : 128 Ko, gestionnaire d'interruptions
  officiel (`ALLOC_INTERRUPT`, nécessaire pour la souris du //c en mode VBL
  et pour la Mockingboard), fichiers de scores simples, volume 140 Ko
  (`.po`, 280 blocs), 800 Ko seulement si le contenu dépasse.

### HGR en jeu, pas DHGR

| | HGR (280×192, 6 couleurs) | DHGR (140×192, 16 couleurs) |
|---|---|---|
| Octets par ligne | 40, une banque | 80, moitié principale / moitié auxiliaire |
| Même surface de sprite | 1× | ~2× les octets, plus 2 bascules de banque (`$C054/$C055` avec 80STORE) par ligne |
| Effacement d'une page (bench) | 51 514 cycles | 207 865 (chemin C, lot 4 en cours) |
| Petit sprite (bench, chemins C) | `hgr_blit7` 4×8 : 1 708 | `dhgr_sprite` 2×2 masqué : 5 158 |
| Lu par les données en mémoire aux | oui (la vidéo n'y est pas) | non : la vidéo occupe aux `$2000-$5FFF` |

Estimation pour un alien de 14×10 points HGR (3 octets par ligne une fois
prédécalé) : ~600 cycles pour le dessiner en `ORA` sur fond noir, ~400 pour
l'effacer (`STA` de zéros), soit ~1 000 par alien qui bouge et par image.
Le même alien en DHGR coûte ~2 000-2 200. Avec le budget d'une image à
30 i/s (ci-dessous), HGR fait bouger ~18 aliens par image, DHGR ~8-9. **Choix : HGR double tampon en jeu.** La
DHGR reste une option pour les écrans fixes (titre, boutique) — voir les
questions ouvertes du `TODO.md`.

Couleurs HGR : les sprites colorés se déplacent par pas de 2 points (la
couleur dépend de la parité de colonne) ; sept prédécalages couvrent un
groupe de 14 points (2 octets), chacun avec le bon bit de palette par octet
(note `x = 14*n` de `dev/lib/hgrc`). Le fond est noir avec des étoiles :
pas de sauvegarde du fond sous les sprites, on efface en écrivant des zéros
et les étoiles sont redessinées à chaque image.

### Cadence

Une image = **2 rafraîchissements** : 30 i/s NTSC, 25 PAL (comme
CHROMABREAK ; le jeu est donc ~17 % plus lent en PAL). Le faisceau mesure
17 030 cycles par rafraîchissement NTSC (20 280 PAL) ; le budget du dépôt
(`dev/bench/budgets.json`) en garde 2 × 17 030 − 6 000 = **28 060** pour le
rendu et la logique, les 6 000 réservés couvrant la musique sous IRQ et la
souris. Répartition visée (NTSC) :

| Poste | Cycles |
|---|---:|
| Logique : formation, plongées, tirs, collisions, bonus | ~5 000 |
| Vaisseau + ~10 tirs + ~6 objets qui tombent | ~3 000 |
| Étoiles (~24, 1 octet chacune, effacer + poser) | ~1 500 |
| HUD : un chiffre au plus par image (`hgr_hud8` : 7 850 pour 5 chiffres) | ~1 000 |
| Aliens : ~18 qui bougent à ~1 000 | ~17 500 |
| **Total** | **~28 000** |

La formation « respire » par petits pas : une rangée bouge par image, les
autres restent en place (règle « ne redessiner que ce qui change »). Plus
de ~18 aliens en mouvement (boss, vagues kamikaze) : on passe en 3
rafraîchissements par image (20 i/s, 45 090 cycles utiles) **sans changer la
vitesse du jeu**, car la logique avance d'un pas fixe par paire de
rafraîchissements, comptés par l'horloge (VBL), pas par image dessinée.

L'horloge vient du VBL : scrutation de `RDVBLBAR` (`$C019`, bit 7 à 0
pendant le VBL) sur //e (`apple2frame`), interruption VBL de la souris
(mode 9) sur //c (`chromabreak/src/timing.s`, `dev/lib/mouse`). Elle ne
dépend ni du son ni de la carte présente.

### Son : avec ou sans Mockingboard

La Mockingboard est **facultative**. `mb_detect`
(`dev/lib/apple2/mockingboard.asm`) cherche une carte au démarrage, slots
7 à 1 sur //e, et la **Mockingboard 4c** sur //c (carte interne d'Ian Kim,
2016, vue en slot 4 : la détection la réveille à `$C403` et peut masquer la
ROM souris du slot 4, donc détecter **avant** la souris).

- Avec carte : musique PT3 et bruitages AY, servis par l'interruption du
  timer T1 de la VIA (50 Hz). Le lecteur PT3 n'existe pas encore dans
  `dev/lib` (base envisagée : lecteur de Vince Weaver 0BSD, ou le port
  GROUiK/French Touch d'A2FileCmd, voir `dev/lib/apple2/README.md`).
- Sans carte : haut-parleur. Bruitages non bloquants, joués **dans
  l'attente du VBL** avant la bascule (le temps libre de l'image, jamais plus) ;
  musique à deux voix (`duet`) seulement hors jeu (titre, boutique, fins),
  où elle peut bloquer.

Le jeu se joue et va à la même vitesse dans les deux cas.

Pas de voix numérisées : `dev/lib/audio` (`sample_player.s`) est bloquant ;
au mieux un très court échantillon hors jeu (un mot au titre).

### Commandes

| Clavier | Manette | Souris | Effet |
|---|---|---|---|
| ← → (ou J / L) | X | X | déplacer le vaisseau |
| Pomme ouverte, ESPACE | bouton 0 | bouton | tirer (tir automatique si acheté) |
| Pomme fermée | bouton 1 | — | missiles, si on en a |
| ↑ ↓ ← → RETURN | | | boutique, Memory Station |
| ESC | | | pause / menu |
| S | | | son coupé / remis |

Sur //e, les touches tenues se lisent : `$C010` bit 7 (une touche est
enfoncée) et les boutons/pommes `$C061/$C062` en continu, donc gauche/droite
se tiennent sans attendre l'auto-répétition. La manette et la souris sont
lues pendant l'attente du VBL (temps de lecture des paddles jusqu'à ~3 ms,
compté comme dans `chromabreak/src/timing.s`). Manette : port jeu du //e,
prise DB-9 du //c. Souris : AppleMouse II sur //e, souris intégrée sur //c.

## Mémoire (prévue)

Configuration de liens : `dev/cc65/apple2_dhgr_prodos_c.cfg` convient telle
quelle (les pages `$2000-$5FFF` principales sont les deux pages HGR ; on
n'écrit pas les pages aux).

| Zone | Usage |
|---|---|
| `$0050-$00FF` | page zéro du jeu et de cc65 (`ZP` du cfg) ; le gestionnaire IRQ n'utilise ni la ZP cc65 ni sa pile |
| `$0200-$03FF` | tables de lignes `hgr_lo/hi` (`hgr_scanline_ram.asm`) ; page 3 : lecteur haut-parleur (boucle à cycles comptés, sans franchir de page) |
| `$0400-$07FF` | page texte 1, jamais affichée en jeu : tables (en évitant les trous `$x78-$x7F`, `$xF8-$xFF`) |
| `$0800-$0FFF` | libre sous ProDOS : tampon de fichier, trajectoires du niveau |
| `$1000-$1FFF` | `LOWBSS` : sprites prédécalés du paquet courant |
| `$2000-$3FFF`, `$4000-$5FFF` | pages HGR 1 et 2 |
| `$6000-$BDFF` | code, données, BSS (~23,5 Ko) |
| `$BE00-$BEFF` | pile C ; `$BF00` page globale ProDOS |
| aux `$0200-$BFFF` | réserve : dessins des 25 paquets, PT3, écrans, niveaux (copie par `AUXMOVE` `$C311` entre deux niveaux) |

## Disquette

`dist/WARGALAGAII.po`, volume `/WARGALAGAII` (11 caractères, nom ProDOS
valide). `WARGALAGA.SYSTEM` ferait 16 caractères, un de trop : l'amorce
s'appelle `WG2.SYSTEM`, le programme `WG2.SYS` (même schéma que
`CHROMA.SYSTEM` / `CHROMA.SYS`), plus `HIGHSCORES`, les données aux
(`WG2.AUX`) et les overlays (boutique, sous-jeux).

    make            # squelette : affiche l'état, ne construit rien

Auteur : VERHILLE Arnaud. Licence : [GPL-3.0](../LICENSE). Warblade est une
œuvre d'Edgar M. Vigdal (EMV Software) ; rien n'en est repris.
