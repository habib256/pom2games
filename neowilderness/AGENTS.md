# Demandes utilisateur à conserver

Ces décisions ont été demandées et confirmées le 16 octobre 2026. Les
appliquer aux prochaines modifications de NeoWilderness et NeoWildernessXL,
et préserver les comportements déjà réalisés, sauf nouvelle instruction
de l'utilisateur. Les détails sont dans `docs/MENUS.md` et `CHANGELOG.md`.

- TOPO : placer l'échelle de distance et son chiffre **4 en bas à gauche**
  de la carte.
- Vue : ne pas remettre de barre verticale supplémentaire à droite de
  **DRINK** dans la grille d'actions en bas à droite.
- Pages du haut : mémoriser la dernière page ouverte. Depuis OBJECTS,
  revenir à la vue puis appuyer sur haut doit retrouver OBJECTS, même après
  une commande de simulation. Ne pas imposer STATUS à chaque retour.
  La commande tapée STATUS ouvre explicitement STATUS.
- OBJECTS : distinguer le focus sur l'onglet du focus dans les listes,
  comme confirmé par l'utilisateur. À l'ouverture, l'onglet a le focus :
  bas revient à la vue, Entrée active les listes ; ensuite haut/bas
  parcourent les objets et gauche/droite changent de côté. Haut au-dessus
  du premier objet rend le focus aux onglets. Préserver les transferts.
- Retirer le rappel **S/O/R/H** en haut d'OBJECTS et des autres pages.
  Cette demande concerne le rappel affiché ; conserver les raccourcis.
- OBJECTS sur XL : **HANDS et PACK ont chacun leur post-it**. Exploiter
  la hauteur en plaçant **CARRYING et LOAD plus bas** ; les listes ont
  douze entrées visibles, les blocs CARRYING/LOAD occupent les rangées
  16–20. Préserver des cadres propres pendant le défilement, sans doublon
  du titre PACK. L'édition 140 Ko conserve les mêmes positions en texte.

- OBJECTS : conserver le côté choisi, les deux sélections et leur défilement
  au retour depuis la vue ou une autre page, y compris après une simulation.
  Mémoriser l'identité des objets, afin qu'un changement de liste ne déplace
  pas la sélection sur un autre objet. Si l'objet disparaît, choisir un
  objet voisin valide ; l'arrivée reste sur l'onglet, Entrée active la liste.
- LOAD : garder les jauges de volume PACK et HANDS, six cellules remplies
  selon le volume occupé, avec le volume libre exact en IN3. Conserver aussi
  le poids total, le ralentissement de marche et la place libre des vêtements.

Depuis la demande du 16 octobre 2026 d’arrêter la version 140 Ko,
poursuivre le développement et les validations sur NeoWildernessXL uniquement.
L’image 140 Ko est historique ; ne plus la reconstruire par défaut.
Vérifier XL lors d’un changement de navigation ou de disposition. Garder la documentation et les tests cohérents avec
ces décisions ; ne pas rétablir les anciennes attentes par défaut.

- EQUIPMENT : conserver une page dédiée séparant porté sur soi, en mains
  et effectivement en usage. La possession ne vaut pas activation. Les
  actions utilisent les prérequis natifs et reviennent sur le même objet ;
  afficher charge, volume des mains et préparation de CATCH.
