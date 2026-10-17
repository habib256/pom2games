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

- TMAP et le scénario archipel ont été supprimés sur demande utilisateur.
  Ne pas réintroduire leur entrée au menu, générateur ou paquet de données.

- OBJECTS : les médicaments s’utilisent une fois, avec doses restantes et
  durée native affichées, sans TOUT ni onces pour le soin. LOCAL HUNG ouvre
  LOWER FOOD avec confirmation ; HANG coûte 30 minutes, LOWER est instantané.
  Préserver l’accès aux occurrences distinctes d’un même objet au sol et
  dans le sac suspendu, ainsi que l’annulation sans effet.

- TASTE depuis OBJECTS inspecte la source sélectionnée sans consommer de
  stock, sans délai, sans quantité ni TOUT ; garder la confirmation et
  l’annulation. Ne pas confondre le goût affiché et une garantie de sécurité.

- Ordre des onglets demandé : STATUS, OBJECTS, EQUIPMENT, CRAFT, HELP,
  OPTIONS, MENU. EQUIPMENT se trouve entre OBJECTS et CRAFT ; gauche depuis
  CRAFT y revient, droite depuis EQUIPMENT ouvre CRAFT.

- Réorganisation MouseText du 17 octobre 2026 : STATUS présente HEALTH,
  ENERGY, MEAL, WATER et BODY sur les rangées 3–7. Les explications sont
  dans HELP ; MEDICAL masque les affections inactives et garde les
  protections. Après les soins actifs, le dernier focus permet d’afficher
  ou masquer le catalogue complet sans action de simulation.
- EQUIPMENT : Entrée active les listes ; gauche/droite choisissent WORN,
  HANDS, ACTIVE ou PACK, haut/bas sélectionnent un objet. Sur l’onglet,
  gauche/droite continuent de changer de page. Une action suit l’objet
  dans sa nouvelle catégorie ; une catégorie vide ne doit pas agir sur
  une ancienne sélection. Ne pas réafficher les détails des drapeaux internes.
- CRAFT : synthèse par défaut, prérequis manquants seulement, durée et
  outil utiles ; droite développe les facteurs, gauche restaure la
  synthèse. Sur l’onglet, les flèches changent toujours de page.
- HELP : quatre rubriques sélectionnables, une explication à la fois.
  OBJECTS garde ses trois post-its et ses jauges ; les plages de lignes
  remplacent MORE. OPTIONS et MENU affichent les noms sans lettres de
  raccourci devant chaque ligne ; conserver les raccourcis fonctionnels.

- EQUIPMENT : la liste d’objets occupe deux colonnes équilibrées dans le
  post-it de gauche, jusqu’à quatorze lignes par colonne. Haut/bas parcourent
  la première colonne puis la seconde ; gauche/droite gardent les catégories.
  Conserver la fiche complète et CATCH à droite, ainsi que le défilement.
