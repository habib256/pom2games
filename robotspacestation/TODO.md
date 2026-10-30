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

- [x] Missions 8-14 (2026-10-30) : LE ZIGZAG, LE COLIS, LE GARDIEN, LA RONDE,
      LE SAS, LA CAISSE, LE TANDEM, prouvées par le modèle et jouées en C
      (`make test-long`) ; titre en deux colonnes, touche 0 pour la dixième
      (11-14 : au titre). Le titre est plein (2 × 7) : au-delà, une page de
      plus.
- [ ] Des puces fournies par la station (une bibliothèque de départ).
- [x] Son (2026-10-30) : contact, pince (prise, lâcher), radio, puce gravée,
      mission réussie ; S coupe.

## Interface

- [x] Deux fils partis de bornes voisines partageaient leur segment
      vertical : la colonne libre la plus proche du milieu (2026-10-30).
- [x] Une pièce en main se voit sur le pointeur (un bloc sous la flèche).
- [x] Un indice par mission (touche H), sur le disque après la salle.
- [x] Une page d'aide (AIDE ou H au titre) : bornes, pièces, touches.
- [x] Records : le moins de portes par mission (sauvegarde RSS3, RSS1/2
      migrées), rappelé à l'entrée de la mission, page RECORDS au titre.
- [x] V : vitesse rapide (×1,5 sur //e, ×1,2 sur //c : le tour y coûte déjà
      presque tout le temps).
- [x] `make test-long` : 12 cartes aléatoires (boucles comprises) tour par
      tour == `Sim` du modèle ; 10 drones aléatoires dans des salles aléatoires
      == `Zone` ; la campagne entière, chaque mission jouée en C avec
      la solution du modèle (carte dans `RSS.SAVE`), //e et //c.

## Mémoire (au 2026-10-30)

Principale jusqu'à `$B8AE` (1,3 Ko libres sous `$BE00`), page 2 HI jusqu'à
`$596E` (1,6 Ko), basse jusqu'à `$1F74` (140 octets).
