# ROBOT SPACE STATION — historique

*[← TODO](TODO.md)* · les cases cochées, sorties de TODO.md le 2026-11-16.

## Contenu

- [x] Missions 8-14 (2026-10-30) : LE ZIGZAG, LE COLIS, LE GARDIEN, LA RONDE,
      LE SAS, LA CAISSE, LE TANDEM, prouvées par le modèle et jouées en C
      (`make test-long`) ; titre en deux colonnes, touche 0 pour la dixième
      (11-14 : au titre). Missions 15 LE COMPTEUR (fronts du capteur O),
      16 LA SPIRALE (quatre caps), 17 LE CONVOI (pince dans les virages), 18 DEUX
      CLES (réutiliser la puce de LA CAISSE), 19 LA PASSE (pince, radio, fente), 20 LES
      ETAGES (bascule T : une OX rebouclée)
      sur une seconde page du titre (PAGE ; RECORDS suit la page).
      `best` a 28 places (deux pages de titre).
- [x] Son (2026-10-30) : contact, pince (prise, lâcher), radio, puce gravée,
      mission réussie ; S coupe.

## Interface

- [x] Refonte de l'ergonomie (2026-10-30, soir) : tout en anglais, un
      briefing par mission (but, nouveauté, deux indices), la ligne du bas
      décrit ce que montre le pointeur ou dit quoi faire ensuite, moteurs
      nommés par la direction du drone, textes en mémoire auxiliaire
      (`tools/gen_text.py`, `RSS.TEXT1/2`). Puis : la borne + (alimentation,
      toujours 1), la boîte à outils étiquetée, un cours d'électronique en
      six pages (tables de vérité), GATES sur le briefing.
      Puis : sortie derrière le drone (sa planche jouée 4 tours d'avance),
      on n'entre qu'en cliquant le drone, sprites de profil (drone et
      technicien), redessin des seules bandes découvertes (vitesse
      d'avant à 5-8 % près).
- [x] Deux fils partis de bornes voisines partageaient leur segment
      vertical : la colonne libre la plus proche du milieu (2026-10-30).
- [x] Une pièce en main se voit sur le pointeur (un bloc sous la flèche).
- [x] Un indice par mission (touche H), sur le disque après la salle.
- [x] Une page d'aide (AIDE ou H au titre) : bornes, pièces, touches ; puis
      la légende des salles (grille, tunnel, portes et plaques, chargeur...).
- [x] Records : le moins de portes par mission (sauvegarde RSS3, RSS1/2
      migrées), rappelé à l'entrée de la mission, page RECORDS au titre.
- [x] V : vitesse rapide (×1,5 sur //e, ×1,2 sur //c : le tour y coûte déjà
      presque tout le temps).
- [x] `make test-long` : 12 cartes aléatoires (boucles comprises) tour par
      tour == `Sim` du modèle ; 10 drones aléatoires dans des salles aléatoires
      == `Zone` ; la campagne entière, chaque mission jouée en C avec
      la solution du modèle (carte dans `RSS.SAVE`), //e et //c.
