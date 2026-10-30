# ROBOT SPACE STATION — à faire

*[← README](README.md)* · règles : [docs/SPEC.md](docs/SPEC.md)

## Matériel réel

- [ ] Essai sur un vrai //e enhanced avec carte AppleMouse, puis sur un //c :
      souris (vitesse du pointeur, clics pendant les grands dessins),
      sauvegarde `RSS.SAVE`, lecture de `RSS.ROOMS`.
- [ ] Sur //c, un clic très bref pendant un grand dessin peut se perdre (la
      souris intégrée compte par interruptions, masquées pendant les accès à
      la mémoire auxiliaire) : mesurer sur la machine.

## Contenu

- [ ] Un deuxième module de missions (les salles sont sur le disque : seule
      la liste des noms et buts reste en mémoire, environ 20 octets par
      mission).
- [ ] Des puces fournies par la station (une bibliothèque de départ).
- [ ] Son : contact, pince, radio, mission réussie.

## Interface

- [ ] Deux fils partis de bornes voisines peuvent partager leur segment
      vertical : choisir le milieu parmi les colonnes libres.
- [ ] Une pièce en main ne suit pas le pointeur (seul le message le dit).

## Mémoire (au 2026-10-30)

Principale jusqu'à `$B8AE` (1,3 Ko libres sous `$BE00`), page 2 HI jusqu'à
`$596E` (1,6 Ko), basse jusqu'à `$1F74` (140 octets).
