# ROBOT SPACE STATION — à faire

*[← README](README.md)* · règles : [docs/SPEC.md](docs/SPEC.md) · fait : [CHANGELOG.md](CHANGELOG.md)

## Matériel réel

- [ ] Essai sur un vrai //e enhanced avec carte AppleMouse, puis sur un //c :
      souris (vitesse du pointeur, clics pendant les grands dessins),
      sauvegarde `RSS.SAVE`, lecture de `RSS.ROOMS`.
- [ ] Sur //c, un clic très bref pendant un grand dessin peut se perdre (la
      souris intégrée compte par interruptions, masquées pendant les accès à
      la mémoire auxiliaire) : mesurer sur la machine.

## Contenu

- [ ] Des puces fournies par la station (une bibliothèque de départ).
      Pas fait le 2026-10-30 : des puces toutes faites donneraient la moitié
      des solutions ; à décider (par exemple une seule, la bascule de choc).

## Interface

- [ ] Essai par un joueur qui découvre le jeu : les briefings et indices
      suffisent-ils ? (surtout missions 7, 15, 16, 20)

## Mémoire (au 2026-10-31 : overlays)

Fait : la page 2 (`$4000-$5FFF`) est une fenêtre d'overlays (PLAY = salle
et drones, FRONT = titre, aide, briefing, lecture de la sauvegarde), rangés
en auxiliaire (`RSS.OVL`) et recopiés en 0,11 s au changement d'écran
(docs/SPEC.md, « Mémoire »). Libres : principale 775 o, PLAY 225 o (avec
DHGRSPRCODE), FRONT ~5,6 Ko, L8 ~260 o ; `sprbuf.s` (inutilisé) supprimé.

Réserves encore inemployées, si un jour il en faut plus :
- [ ] auxiliaire `$0800-$1FFF` (6 Ko) et `$905E-$9FFF` (~4 Ko) : un troisième
      overlay (le labo : gravure, ouverture de puce, effacement) ou des
      données ;
- [ ] carte langage auxiliaire (16 Ko + 4 Ko) : seulement comme réserve de
      données (il faut ALTZP, donc une copie, pas d'exécution) ;
- [ ] la sauvegarde (`persist`, 2,1 Ko en `$1400`) en auxiliaire libérerait
      la mémoire basse pour du code résident, mais la compilation des
      planches lit les puces à chaque fois : à mesurer.
