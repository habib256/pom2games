# Wilderness — historique

Les étapes ci-dessous décrivent les travaux présents dans l'arbre de travail.
Elles ne correspondent pas à des versions publiées. Les tâches à venir sont
suivies dans [TODO.md](TODO.md) et les limites du portage dans
[IMPLEMENTATION.md](docs/IMPLEMENTATION.md).

## Non publié

### Réduction des transferts de modules

- Simulation et sprites épave/ours/cabane compressés, décompression LZ
  résidente en place : 32→22, 8→6, 4→2 et 5→3 secteurs de données lus.
- Allocations conservées, longueurs BLOAD réduites : placement des fichiers
  suivants préservé. Petits modules gardés bruts après mesure du coût natif.
- Tables de projection réduites à une table stockée et un cache reconstruit
  au démarrage ; 24 976 octets résidents, paquet de 16 303 octets en deux fichiers.
- LOOK R à 7,26 s ; repos/sommeil presque inchangés à 21,11/22,70 s,
  marche à 26,96 s. La décompression absorbe presque tout le gain disque.
- 20 chargements natifs vérifiés octet par octet, avec texte, page zéro/FAC
  et bornes mémoire conservés ; états et images de six commandes identiques.
- Durées directes 1–255 H/MIN de REST/SLEEP/WALK/SWIM validées en résident ;
  lecteur complet conservé pour saisie au clavier, autres formes et erreurs.
- Une lecture WILDINP évitée : REST 1 H à 21,12 s, SLEEP 8 H à 22,71 s,
  WALK 1 H à 26,95 s ; états et images identiques.
- Deux tables graphiques redondantes retirées (280 octets) pour loger la
  saisie résidente ; coût du rendu supplémentaire de 0,004 s.
- Dictionnaire de compression partagé entre régions voisines : démarrage
  maintenu dans deux fichiers (16 369 octets) ; résident réduit de huit octets.
- 799 durées natives et les 140 paires de pixels vérifiées ; zéro, erreurs,
  annulation, saisie générale, mémoire DOS et restitution intégrale conservés.

### Audit des coûts et copies natives

- Copies LZ du chargeur par index Y ; mise à jour des pointeurs et compteurs
  une fois par séquence. Moteur prêt à 19,42 s ; première invite à 40,91 s.
- Division de pente nulle immédiate ; suppression du double effacement et
  du second bandeau lors de la restauration nocturne extérieure.
- VIEW à 5,62 s ; DRINK nocturne gagne 0,14 s. Résident : 25 261 octets,
  comprimés en 16 276 octets dans deux fichiers ; quatre octets nets ajoutés.
- Profilage des commandes par zone mémoire : DOS absorbe encore 68 % du
  sommeil et 77 % de la marche. États et pixels comparés sans différence.
- 8 256 divisions et 40 copies testées nativement, ainsi que l'effacement
  nocturne unique ; franchissements de page et chevauchements couverts.

### Chargement Disk II

- Compression LZ optimisée par bloc avec prise en compte des drapeaux,
  fenêtre complète de 4 095 octets et suppression des coupures de sortie
  arbitraires à 4 Ko. Décompresseur et mémoire Apple II identiques.
- Démarrage compacté en 16 272 octets dans deux fichiers au lieu de trois ;
  entrelacement de neuf secteurs avec décalage physique d'un secteur entre pistes.
- Arrivée dans le moteur : 23,48 → 20,83 secondes ; première invite :
  45,89 → 43,26. LOOK R : 8,08 → 7,36 ; sommeil de huit heures : 25,83 → 25,30.
- Mesures Disk II corrigées pour arrêter la saisie avant le premier BLOAD.
  1 023 cas de compression comparés à une recherche exhaustive, limites
  de format et fenêtre, intégrité DOS et restitution native vérifiées.

### Parcours mémoire du rendu

- Recherche des arbres arrêtée pour le reste du rayon après sa limite de
  distance ou la sélection d'une couronne ; réactivation au rayon suivant.
- Effacement par lignes contiguës, avec adresses HGR calculées une fois
  par ligne ; bandeau, cache, trous mémoire et colonnes conservées protégés.
- 32 octets de pointeurs redondants supprimés, sans nouveau calcul d'indice
  dans le remplissage déroulé ; résident total réduit de 14 octets.
- VIEW : 6,20 → 5,64 secondes, LOOK R : 8,28 → 8,08, sommeil de huit heures :
  26,39 → 25,83. États et pixels identiques, lectures DOS inchangées.
- Régressions sur chaque octet d'une page HGR, effacements partiels/complets,
  budget de recherche des arbres et réactivation entre les images.

### Vitesse et durée de vie des données en mémoire

- 170 octets d'une table de rendu hors écran récupérés pour LOOK résident
  et les raccourcis d'écran, avec conservation des pixels. VIEW ne recharge
  plus le vocabulaire et le sprite : 12,47 → 6,20 secondes. LOOK R passe
  de 10,43 à 8,28 ; STATUS au départ de 12,27 à 3,76.
- Temporaires astronomiques réutilisant 68 octets du tampon DOS en dehors
  des chargements ; sorties du ciel toujours résidentes. Cache d'isolation
  de cinq octets, invalidé par les vêtements portés ou le mode d'humidité.
- Mesures reproductibles en cycles et lectures avec profile_actions.py,
  comparaison des états et pixels avant/après, 76 transitions thermiques
  et tests de conservation à travers les chargements.
- L'Apple II+ 48 Ko reste la cible ; les routines flottantes et les arrondis
  de la simulation sont conservés. Le sommeil reste proche de 26,4 secondes.

### Bandeau de survie et accès direct aux écrans

- Alertes de danger, faim/soif VERY et santé sous 40 % en vidéo inverse ;
  améliorations en texte normal pour distinguer leur importance sans couleur.
- Indications TOPO/HELP de jour, REST/HELP la nuit et LOWER FOOD près du sac
  suspendu, après les dangers et les indications d'abri ou d'arbre.
- Raccourcis affichés pour passer directement entre HELP, INVENTORY,
  STATUS et TOPO. Navigation de STATUS fixée aux deux dernières lignes.
- Vérification des pixels d'alerte et des neuf transitions directes,
  avec conservation du temps, des réserves et de l'image visible.

### Aide et inventaire plus lisibles

- HELP affiche deux pages, déplacements et survie, avec exemples de commandes,
  unités et touches de navigation. Les touches 1/2 sélectionnent une page,
  N/Espace et B changent de page, Échap/Entrée réaffichent le paysage.
- Titres d'aide et groupe d'inventaire en vidéo inverse ; nombre d'objets,
  capacités FREE et commandes de pagination affichés explicitement.
- Consultation vérifiée au clavier, sans avancer le temps ni modifier
  les réserves, la santé ou le paysage.

### Alertes rétablies avant affichage

- Une amélioration remplace désormais l'alerte d'aggravation encore en
  attente pour la même catégorie, au lieu d'afficher un avertissement périmé.
- Régressions pour faim, soif, santé, température et immersion ; les alertes
  encore actives d'autres catégories gardent leur priorité. Le classement
  reste sans effet sur la simulation.

### Résultat des commandes d'attente

- WAIT et PAUSE annoncent « YOU WAITED » en heures ou minutes, au lieu de
  « YOU RESTED » ; leur absence de crédit de repos est conservée.
- Régressions sur les deux unités, les effets identiques de WAIT/PAUSE,
  le crédit distinct de REST et l'annulation d'une durée nulle.
- Réorganisation des textes en mémoire sans lecture disque supplémentaire
  pour le sommeil ; ses cinq lectures et son état final restent vérifiés.

### Limite des forêts dans les écrans d'information

- TOPO et STATUS utilisent la limite d'altitude des arbres de la carte,
  comme la vue 3D et CLIMB TREE, au lieu d'une constante de 11 000 pieds.
- La valeur zéro conserve la limite historique de 11 000 pieds.
  Régressions sous la limite et exactement à celle-ci, pour trois limites,
  en vérifiant les symboles T/t, WOODS/SCRUB et l'accès aux arbres.

### Valeur directe de NATURE

- `NATURE 0` désactive désormais les nouvelles rencontres, comme la valeur
  zéro saisie à l'invite ; la commande directe était refusée par la liste
  des actions numériques et conservait la fréquence précédente.
- Valeurs 0–100, espaces et saisie à l'invite vérifiés. Les nombres hors
  limites, décimales et unités sont refusés sans changer l'état du joueur,
  la fréquence, le paysage ou le hasard.

### Objets au sol dans le bandeau

- « ITEMS: INV » disparaît après récupération du dernier objet ou
  consommation de la dernière réserve au sol, comme dans l'inventaire.
- Le résumé ne prend plus les compteurs de corde et d'autres équipements
  pour des réserves au sol ; les aliments épuisés ne comptent plus non plus.
- Régressions par commandes réelles sur corde, hache, œufs et eau.

### Projection des sites au pied des falaises

- Une cabane très en dessous de la vue ne réapparaît plus à l'écran
  lorsque le calcul de sa hauteur dépasse 16 bits.
- Régression sur neuf hauteurs de falaise et trois orientations, comparées
  pixel par pixel au modèle de projection indépendant.

### Durée des rencontres pendant les actions immobiles

- Les rencontres déjà présentes vieillissent aussi pendant WAIT, les
  repas et le sommeil ; elles expirent à 60 minutes, même sans déplacement.
- Aucun nouveau tirage de faune pendant ces actions. Régression sur une
  attente, un repas et deux repos, avec présence à 59 minutes, disparition
  à 60 minutes et générateur de hasard inchangé.
- NATURE rejoint le module de saisie ; cela libère la place nécessaire
  dans le module de simulation et évite son chargement pour ce réglage.

### Alertes après une boisson

- DRINK actualise immédiatement l'état de soif et de déshydratation utilisé
  par le bandeau, sans attendre une action qui avance le temps.
- Une déshydratation effacée par la boisson ne reste plus affichée ; tests
  de guérison, d'amélioration de la soif et de déshydratation persistante,
  avec stocks débités une seule fois et heure/santé conservées.

### Retour entre groupes de l'inventaire

- Depuis la première page d'un groupe, B revient à la dernière page du
  groupe précédent, au lieu de sauter directement à sa première page.
- Régression sur le passage sac → sol → retour au sac, avec deux pages
  d'objets dans chaque groupe ; heure et stocks conservés.

### Alerte de maladie devenue périmée

- Une maladie disparue avant le rafraîchissement du bandeau affiche
  « ILL IMPROVED », au lieu de provoquer une fausse alerte « EXHAUSTION ».
- Régressions sur les trois guérisons, une déshydratation persistante et
  les remplacements de maladie entre deux affichages.

### Minute de l'horloge

- Le bandeau et STATUS arrondissent le total des minutes avant d'extraire
  heure/minute : WALK 19 MIN depuis 7 h affiche désormais 7:19, au lieu
  de 7:18 quand le flottant est légèrement inférieur à la minute entière.
- Retenues vers l'heure suivante, midi et minuit gérées ensemble, sans
  modifier le temps simulé. Régression sur une marche réelle et sept
  valeurs proches des limites de minute et d'heure.
- Minuit s'affiche 12:00A dans STATUS ; le format 12 heures affichait
  auparavant 0:00A à cause du drapeau zéro laissé par la comparaison à 12.

### Fin exacte de la durée de voyage

- Après le dernier pas demandé, WALK/SWIM s'arrêtent sans tester un pas
  supplémentaire. Le résultat indique la fin de la durée plutôt qu'un
  obstacle (eau, falaise ou bord de carte) situé au-delà du voyage terminé.
- Les interruptions du pas accompli (animal, nuit, rive, décès, arrivée)
  conservent leur priorité. Régressions sur trois obstacles après exactement
  19 minutes, sur une fin de nage au bord de carte, sur l'eau rencontrée
  avec une minute restante et sur animal/nuit au dernier pas demandé.

### Arguments numériques des médicaments

- `EAT FLAGYL 0 OZ` ne consomme plus une dose malgré la quantité nulle.
  Les médicaments refusent désormais les nombres et unités ajoutés à
  EAT/DRINK, au lieu de les ignorer et d'appliquer une dose unique.
- Le refus conserve stocks, heure et état médical ; il explique de retirer
  le nombre et l'unité. Une prise normale reste disponible après le refus.

### Chasse aux bugs : saisie et lancement des tests

- Les commandes numériques acceptent les espaces en tête comme l'analyse
  ordinaire : `  SLEEP 1 MIN` ne produit plus un refus de valeur invalide.
  Régressions sur repos, marche trop courte et DRINK WATER qualifié.
- `make test` reconstruit a2shot avec son Makefile et ses chemins SDK,
  au lieu d'utiliser la règle C++ implicite qui échouait sur `pom2/core.hpp`.

### Attente réduite pendant SLEEP

- Suppression du détour par le vocabulaire et du rechargement de l'analyse
  numérique pour les commandes de repos avec durée, ainsi que SLEEP seul.
- Sommeil de huit heures sur la scène initiale : 32,1 → 26,8 secondes à
  1,023 MHz, avec cinq lectures de disquette au lieu de sept.
- Santé, météo et durée simulée conservées ; comparaison de l'état et du
  paysage avec REST, et vérification des six verbes de repos et d'attente.

### Corrections sur falaises et entrée dans la cabane

- Rejet du débordement du quotient de pente multiplié par trois : les
  arbres situés très bas sous une falaise ne réapparaissent plus dans le ciel.
- ENTER SHELTER refuse l'entrée depuis un arbre ; il faut CLIMB DOWN avant
  d'entrer dans la cabane. Le refus conserve heure, position et inventaire.
- Message de refus dans l'arbre corrigé : son point d'exclamation était
  interprété comme une substitution du motif d'arrêt de voyage. Même
  correction pour le rapport de victoire sans déplacement.
- Régressions sur cinq falaises ascendantes/descendantes et sur la chaîne
  grimper → entrée refusée → descendre → entrer → sortir.

### Doses et gestes de soin

- Décompte signé des utilisations des produits médicaux, sans débordement
  des stocks nuls ou négatifs ; quantités affichées dans INVENTORY.
- Prises orales de FLAGYL, SALT TABLETS et QUININE par EAT/DRINK ;
  refus de l'oxygène, du savon, des crèmes, lunettes et trousses.
- SHIELD EYES et LOWER HEAD sans durée ; SUCK VENOM exige une morsure
  active et prend 15 minutes. LOWER FOOD/BACKPACK conserve la récupération
  du sac suspendu.
- Commandes déplacées dans WILDMVI, avec retour résident avant le calcul
  des soins et du temps ; les progressions restent dans WILDMED.
- 130 cas supplémentaires sur ROM : 90 compteurs signés, 12 gestes de soin,
  22 prises orales et 6 chaînes USE/inventaire/soins sur la dernière dose
  ou un stock vide. Le prérequis natif reste sélectionné même sans dose
  positive ; ce comportement est conservé.
- L'oxygène dépend du drapeau d'utilisation distinct : la dernière dose
  protège, mais réutiliser une bouteille vide désactive cette protection.
- Restent à porter : SPLINT, soins thermiques, placement/stérilisation
  propre à USE et les déclencheurs de blessures/maladies.

### Conditions médicales et expositions

- État résident des 15 conditions Journey : incubation, santé, guérison
  avec/sans soin et produit des pourcentages entiers.
- Prérequis de prévention et de traitement, protection vestimentaire,
  réinitialisation quotidienne des soins temporaires.
- Compteurs sel/froid, seuils stricts et décroissance protégée ; exposition
  solaire et neige raccordées aux données du port.
- Mal d'altitude, oxygène et plafond de 30 minutes en santé critique ou
  pendant les huit premières heures des conditions 6–11.
- USE médical, STOP BLEEDING et page médicale de STATUS.
- WILDTRV pour la nage, WILDMED pour les soins/expositions, WILDMVI pour
  l'état médical, calcul de charge déplacé dans WILDSIM.
- Comparaisons sur ROM : 160 progressions, 66 combinaisons de soins,
  60 cas d'altitude, 80 cadences, 84 protections vestimentaires et
  59 expositions sel/froid, soit 509 cas.
- Restent à porter : soins complémentaires, déclencheurs par
  attaques/chutes/contamination et sélecteurs solaires/neige exacts.
- TOPO : légende raccourcie pour préserver la progression en marche.
- Bandeau invalidé quand WILDSIM emprunte HGR ; retour de STATUS restaure
  les pixels affichés et le cache du terrain. Les tests distinguent ce dessin
  des octets graphiques inutilisés servant aux calculs temporaires.
- Pilote d'aventures : acquittement du temps de marche natif pris en charge,
  quatre scénarios terminés avec écarts toujours signalés ; 112 évolutions
  bornées du vent comparées au moteur original.

### Correction du rendu des arbres

- Dessous du premier profil ramené à la hauteur du feuillage central :
  suppression des pointes noires latérales qui descendaient vers le sol.
- Couronnes séparées, centrées dans leurs cases : le profil natif de
  32 colonnes ne couvre plus deux cases entières.
- Motif de feuillage vert/noir rétabli, avec pixels opaques et occlusion
  des astres ; les profils ne sont plus remplis entièrement en noir.
- Troncs noirs sous le centre du feuillage, ancrés au terrain ; couronnes
  relevées de 18 pixels divisés par la distance pour les arbres proches.
- Contour supérieur noir continu et liseré inférieur du feuillage pour
  détacher les couronnes du ciel violet et du terrain vert.
- Limite du feuillage conservée quand la base projetée dépasse l'écran,
  sans débordement vers un remplissage noir sur les pentes descendantes.
- Stockage de cette limite hors de l'octet d'arrondi Applesoft, pour
  conserver les calculs exacts de durée après l'affichage des arbres.
- Contrôle visuel en émulateur et régression contre les bandes noires
  continues, en plus des comparaisons de pixels et des rotations.

### Grimper et suspendre la nourriture

- `CLIMB TREE` / `CLIMB DOWN` : arbre proche, santé > 2,5 pour monter,
  marche et nage refusées dans l’arbre ; aucun temps ajouté.
- `HANG FOOD` suspend le sac et son contenu pendant 30 minutes, avec
  le coût natif de 1,65 + 0,02 × poids corporel kcal/min.
- `GET BACKPACK`, `LOWER FOOD` et `LOWER BACKPACK` récupèrent le sac à sa
  case ; charge vérifiée et restauration atomique en cas de refus.
- INVENTORY affiche `HUNG HERE` ; STATUS signale l’arbre et le sac suspendu.
- Sonde de 24 cas CLIMB et 16 cas HANG dans le code original sur ROM ;
  tests du port sur les stocks partagés, les conteneurs, les écrans et les refus.

### Arbres et forêts

- Zones boisées issues des contours TMAKE et profils d’arbres Sierra portés.
- Projection attachée au monde, clipping par le relief, priorité aux sprites proches.
- TOPO, STATUS et filtres de faune reconnaissent bois et maquis d’altitude.
- Extension MAP de 294 octets, import des forêts TOPO, compatibilité des cartes anciennes.
- Tests du dessin, des rotations et du chargement.


### Neowilderness lots 4 et 5 Survie, inventaire et orientation

- Compas encadré sur toute sa hauteur, conservé pendant les rotations.
- Résumé monochrome autour de la boussole : heure/période, santé, faim, soif,
  alerte de transition ou état thermique ; abri et objets récupérables ici.
- Alertes aux seuils existants, sans répétition à classe inchangée ni changement
  des règles ; les activités longues conservent une alerte prioritaire.
- STATUS réorganisé, avec conditions avant besoins/environnement et réserves
  CARRIED/HERE distinctes ; cas maximal lisible sans couper un nom de condition.
- INVENTORY regroupé par emplacement, douze objets/page, réserves réparties
  affichées séparément, capacités permanentes et navigation explicite.
- TOPO : C pour recentrer, huit caps magnétiques et site sous le joueur nommé.
- WILDHUD/WILDSTA dans la fenêtre de 2 Ko ; bandeau conservé pendant rendu
  et rotations, faune traitée avant sa composition au démarrage.
- `test_interface.py` vérifie affichage, transitions, groupes/pages/quantités,
  STATUS maximal, orientation/recentrage et consultations sans dépense.
- Validation : suite complète `make -C wilderness test` réussie après le cadre ;
  disquette reconstruite, contrôles de rendu et mémoire inclus.


### Soleil et lune comme repères géographiques

- Soleil calculé selon latitude, saison et heure solaire, indépendant de
  la déclinaison magnétique ; projection dans les axes du terrain.
- Lune nocturne à partir d'une éphéméride de référence 1985, avec phase
  stylisée et correction moyenne de parallaxe ; extension identifiée du port.
- Masquage par nuages, relief et sprites ; conservation du panorama partiel
  de jour et de la vue sombre la nuit, qui ne révèle pas le terrain.
- Initialisation déplacée dans WILDSIM pour respecter la mémoire résidente.
- `test_sky.py` vérifie positions, hémisphères/saisons, masquage et rotations.


### Neowilderness lot 2 Refus et résultats lisibles

- Suppression des confirmations cachées entre messages : la commande suivante
  conserve sa première touche. Le résultat reste lisible au retour à la vue,
  pendant la saisie, après Échap et après une ligne vide.
- Déplacement : durée effective et arrêt par eau, rive, nuit, limite, animal,
  Échap, manque de temps ou terrain/rythme réunis. Mort, victoire et faiblesse
  gardent la priorité ; les résultats de voyage conservent leur durée.
- Verbe inconnu signalé avec HELP ; objet manquant accompagné d'exemples
  disponibles ; objet inaccessible distingué d'une commande non implémentée.
- Consommation : stock accessible avant la réponse, puis quantité réellement
  consommée et stock initial. Les transferts nomment l'objet comme dans
  INVENTORY et son nouvel emplacement, y compris les objets qualifiés.
- Refus de charge : poids, volume ou les deux, excédent et capacité après
  annulation en OZ/IN3 ; distinction des volumes portés, du sac et de la main.
  Dépassement arithmétique distingué d'une capacité simplement insuffisante.
  Sac/gourde absents, conteneurs non vides et sac rangé dans lui-même séparés.
- WILDITM regroupe les transferts dans 2 Ko pour libérer la mémoire résidente.
  Le moteur garde les textes dans trois lignes, sans défilement provoqué par
  un nom long. `test_feedback.py` couvre la matrice de refus, les valeurs
  maximales, la persistance, le stock et les arrêts pour animal/nuit.
- Validation : `make -C wilderness test` complet réussi, avec préservation
  des optimisations de rotation, des écritures TOPO et des traversées de rives.

### Traversée des rives WALK / SWIM

- WALK indiquait l'eau une case avant celle-ci, puis SWIM refusait son premier
  demi-pas encore sur terre. Deux SWIM successifs restaient donc sur place.
  Ce demi-pas est désormais autorisé si le suivant entre dans l'eau, avec
  vérification du trajet sans déplacement ni dépense pendant la vérification.
- SWIM réalise le dernier demi-pas vers la terre et s'arrête sur la rive,
  avec le bilan du temps réellement passé et la fin de l'immersion. WALK
  permet ensuite de poursuivre. SWIM sans eau devant reste sans effet.
- `test_shore.py` couvre les quatre directions, une position fractionnaire,
  un trajet diagonal et deux SWIM successifs jusqu'à la rive opposée.
- Validation : suite complète `make -C wilderness test` réussie, y compris
  trajectoires et durées de nage, bilan thermique, Échap, TOPO et rotations.

### Neowilderness lot 1 Commandes et annulation

- Échap efface la commande ou annule une saisie numérique, sans quitter le
  jeu ; QUIT exige Y après avertissement de perte de progression.
- La flèche gauche supprime un seul caractère dans les quantités et durées.
  Une saisie vide ou zéro annule l'action ; NATURE conserve son réglage zéro.
- Arguments directs et unités : WALK 10 MIN, REST 1 H, DRINK WATER 4 OZ et
  EAT CHEESE 8 OZ. Les anciennes questions restent utilisables ; absence
  d'unité = heures ou onces. Les unités, plages et dépassements sont vérifiés.
- Échap interrompt WALK et SWIM après un pas terminé, avec position, santé,
  réserves et temps effectif conservés. Le repos accepte les minutes ; son
  interruption pendant l'activité reste une suite facultative.
- Échap quitte immédiatement chaque page d'inventaire, sans attendre une
  seconde touche. STATUS et TOPO conservent leur retour à la vue.
- Module WILDINP à $5800 ; déplacement du parcours des mots dans WILDVOC et
  du texte HELP dans WILDSCR pour rester dans les 48 Ko, sans lecture ajoutée
  au chemin des rotations par flèches.
- `test_input.py` couvre les annulations, refus atomiques, unités, correction
  de chiffres, sorties des écrans, confirmation de QUIT et arrêts marche/nage.
- Validation : `make -C wilderness test` complet réussi.

### TOPO écrit seulement les caractères modifiés

- Suppression de HOME et de la réécriture systématique de la carte à chaque
  pas ou défilement. Comparaison directe avec la RAM texte avant chaque écriture,
  pour le relief, les repères, les coordonnées, les légendes et les espaces.
- Retrait des anciens caractères en fin de ligne sans réécrire les espaces
  déjà présents ; conservation des messages et du curseur pendant la marche.
- Tests des écritures réellement exécutées : une écriture par caractère modifié
  sur douze pas de WALK et les défilements ; zéro écriture si la carte ne change pas.

### Présentation pendant le chargement

- Après le titre Apple II+, l'écran présente le crash, l'objectif de rejoindre
  les rangers, les besoins de survie et les commandes principales.
- Les durées en heures, les quantités en onces et les rotations sur une ligne
  vide sont expliquées. Le chargement continue sans attente de touche.
- Présentation intégralement en anglais, limitée à vingt lignes de moins de quarante
  caractères pour rester visible pendant les lectures DOS.
- Vérification du texte au début et à la fin du chargeur, de l'arrivée à
  l'invite jouable et de la restitution des données résidentes par `test_boot.py`.

### Défilement près des sites et accélération du rendu

- Les rotations de 22,5° et 45° réutilisent désormais la géométrie d'un site
  distant unique, même hors champ. Les flèches ne chargent aucun module ;
  seules les colonnes découvertes sont rendues. Les scènes à plusieurs sites
  potentiellement voisins conservent la sélection par reprojection.
- Invalidation du cache de cap après défilement pour éviter de réutiliser une
  ancienne projection avec une origine de sprite déjà décalée.
- Parcours direct des lignes physiques pour l'effacement et le défilement ;
  suppression des appels d'activation de sprite inutiles dans les rayons.
- Mesures : 77,0 % de cycles en moins sur 48 rotations près de la cabane,
  comparées au rendu complet forcé ; 4,7 à 11,5 % de gain sur le rendu complet
  des cinq cartes de contrôle, avec images identiques à la référence.
- Tests de rotation étendus aux sites distants, au masquage par une crête,
  aux sites concurrents, aux tours complets et aux compteurs de lectures disque.
- Validation : `make test` complet réussi, plus rotations de l'épave distante
  et sélection de deux sites à des azimuts différents ; disquette reconstruite.

### Ciel, orientation et carte pendant la marche

- Le ciel et le relief occupent à nouveau les côtés du ruban. Le paysage
  sous le ruban est conservé dans des lignes HGR invisibles pour éviter les
  traces lors des rotations, sans allocation de mémoire supplémentaire.
- TOPO affiche maintenant les Y décroissants : le nord est réellement en
  haut, comme les déplacements et la boussole. Les touches de défilement
  suivent cette orientation.
- À chaque pas de WALK, TOPO se recentre et se rafraîchit dans les vingt
  premières lignes. Les messages, leur curseur et la simulation sont préservés ;
  aucun rechargement ni attente de touche entre les pas.
- Vérifications : déplacements réels N/E/S/W et douze rafraîchissements
  consécutifs pendant WALK, avec contrôle des zones préservées.

### TOPO : actualisation avant affichage

- La carte est reconstruite avant de passer en mode texte à l'ouverture,
  pour éviter l'apparition fugace du précédent écran TOPO ou STATUS.
- Vérification de la réouverture après défilement, marche et rotation :
  recentrage, position/cap, relief et repères relus depuis l'état courant ;
  la vue 3D et son ruban de boussole restent intacts au retour.

### Boussole permanente en haut de la vue

- Suppression de l'activation `USE COMPASS` : les points cardinaux sont
  disponibles dès le départ, sans désactivation lors des transferts d'objets.
- Ruban de 98 pixels centré en haut, avec N/NE/E/SE/S/SW/W/NW, graduations
  tous les 22,5° et curseur fixe. Défilement continu à un pixel pour deux
  unités d'azimut, avec prise en compte de la déclinaison magnétique.
- En-tête réservé sur 16 lignes ; il reste visible la nuit et à la cabane,
  et n'est pas entraîné par le défilement du terrain. Pas de chargement disque
  ni de calcul flottant pour mettre à jour le ruban lors des rotations.
- Vérification des 560 azimuts, du raccord nord, du centrage magnétique,
  des commandes de rotation et des retours depuis STATUS.

### Rotations de la vue

- Défilement du terrain et des sprites locaux pour les rotations de 22,5°
  et 45° ; seules les colonnes entrantes sont recalculées. Géométrie et
  masquage des sites distants conservent le rendu complet.
- Restauration de l'image du sprite après le chargement du vocabulaire de
  LOOK ; les flèches évitent ce chargement lorsque l'image est déjà en mémoire.
- Boucle de défilement raccourcie et suppression d'une table sinusoïdale
  de 141 octets, avec conservation exacte des arrondis des directions.
- Test des cinq sprites, sorties/retours dans le champ et tours complets
  dans les deux sens. Sur 52 rotations autour de l'épave : 435 480 947 →
  98 301 942 cycles, soit 77,4 % économisés, pixels et texte identiques.

### Température : variation lente originale

- Ajout de `INT(5 × SIN(0,0187 × heures écoulées + phase))`, avec la phase
  sauvegardée du premier voyage Sierra et les arrondis de la ROM Applesoft.
- 405 cas comparés à la routine T09/S08 originale : phases, durées,
  températures signées et passage de la limite d'un octet.
- L'air concorde désormais aux six points du scénario de départ ; les
  écarts passent de 13 à 6, encore sur le vent et le ressenti. Le cycle
  quotidien, la visibilité et les fronts météo restent à porter.

### Marche : attente et accès disque

- Regroupement de la faune avec les calculs d'environnement : deux lectures
  de modules par pas ordinaire au lieu de trois quand la faune est active.
- Affichage des minutes parcourues après chaque pas, sans touche à presser.
- Test d'une marche de quatre heures : progression, nombre de lectures,
  retour à la commande et absence de lectures supplémentaires à l'arrêt.

### Terrain : rivières et lacs

- Les plateaux s'écoulent désormais vers un exutoire au lieu de déclencher
  des lacs artificiels. Les véritables cuvettes sont remplies jusqu'au
  niveau de débordement, avec une surface plane et une sortie continue.
- Suppression du remplissage tronqué à 300 unités et des carrés d'eau
  effacés après génération autour du crash et des rangers. Une source
  couvrant ces lieux est rejetée avant modification du terrain.
- Conversion 224 × 168 vers 112 × 84 : chaque bloc garde ses points d'eau,
  y compris aux coordonnées impaires, à la hauteur de l'eau. La cabane
  évite aussi ces cases converties. Les autres marqueurs TOPO ne sont
  plus interprétés comme des rivières.
- Tests des plateaux, petites/grandes cuvettes, rivières fines et de
  18 couples graine/difficulté : continuité, descente et reproductibilité.
  L'écoulement reste une reconstruction, à comparer au générateur original.

### Nage : tracé des caps obliques

- Remplacement des vecteurs continus par l'axe majeur entier et l'accumulateur
  sinusoïdal de l'original ; la durée distingue désormais chaque pas réellement
  droit ou diagonal. État du tracé conservé pendant les changements de module.
- 2 880 positions sur 360 caps comparées aux routines originales sur ROM.

### Nage : effort et charge

- Remplacement des 19 minutes par case par la durée de nage normale de
  l'original, dépendant de la santé, de la charge et du caractère diagonal
  du pas. SWIM avance maintenant d'une demi-case ; un dernier pas peut
  dépasser le temps demandé s'il reste au moins la moitié de sa durée.
- 143 durées identiques aux routines originales exécutées sur ROM ; tests
  de la commande réelle, du dépassement de durée et du retour sur la rive.
  Nouveau module `WILDTRV` pour préserver la place mémoire résidente.

- SWIM utilise désormais le coût original lié au poids total : environ
  14,43 kcal/min avec l'équipement initial. L'eau de la gourde n'est plus
  comptée deux fois dans ce calcul ; les frissons s'ajoutent à cet effort.
- 81 cas de poids, charge et durée vérifient la dépense calorique ; les
  métabolismes sont également comparés octet par octet au helper original
  exécuté sur la ROM, et les calories à sa routine énergétique. Premier
  intervalle de santé de nage rétabli à 15 minutes. Test de la commande réelle,
  immersion, repos dans l'eau et sortie sur la rive. Les modificateurs de
  blessures/équipement restent à reproduire.

### Comparaison de commandes avec le jeu original

- Nouveau pilote différentiel sur les deux exécutables Apple II : départ,
  équipement, boissons, repas, repos répétés, nuit et première marche.
  Questions inspectées avant réponse ; erreurs et différences font échouer
  le test. Dumps, images, journaux, symboles et rapports restent dans `build/`.
- Observation de l'état original avant sa pagination sur Journey T04,
  pour éviter de confondre la seconde page HGR avec la physiologie.
- Boire à la gourde ne consomme plus de temps ; manger prend 16 minutes,
  avec crédits alimentaires et hydriques originaux. Les frissons de la
  sauvegarde initiale contribuent aux premières calories dépensées.
- Repos adaptatif après le premier pas de 30 minutes ; compteurs et
  déficits actualisés à la cadence de santé, pourcentages entiers et Hmax
  initial conservé à sa précision originale.
- Correction de la règle de rencontres précédente : repos et repas ne
  tirent aucune faune. Les tirages et interruptions restent actifs en marche.
- Directions cardinales corrigées par la déclinaison magnétique de la carte.
  La précision aléatoire de la boussole reste à porter.
- `make test-original` reste en échec sur les écarts météo/nuit/marche.
  Aucune aventure complète jusqu'aux rangers n'est encore validée.

### Rencontres pendant les actions

Cette étape précédait les corrections différentielles ci-dessus ; les
tirages pendant REST et sa cadence fixe ont depuis été remplacés.

- Tirage à chaque pas de simulation : repos de 30 minutes, marche/nage
  selon la durée du pas ; suppression du cumul limité à 255 minutes.
- Toutes les espèces sont testées dans l'ordre Sierra, même si un animal
  est présent ; conservation ou remplacement à 50 %, vérifiés dans l'original.
- Une rencontre acceptée interrompt marche/repos après le pas écoulé,
  avec temps exact et message d'interruption du repos.
- Aucun tirage extérieur sous abri ; VIEW/STATUS ne dépensent ni temps
  ni hasard. Les interruptions laissent le sprite disponible pour l'action suivante.
- Sondes des drapeaux originaux et scénarios déterministes de repos long,
  marche interrompue, remplacements et protection de la cabane.
  Durée de présence de 60 minutes et déplacements des animaux restent provisoires.

### Faune Sierra et limites de déplacement

- Filtres des trois espèces : saison, heure, terrain, altitude, pente
  maximale du voisinage 3 × 3 et indice climatique régional.
- Probabilité `minutes × NATURE × √difficulté × taux × 10⁻⁵`, avec les
  taux originaux 80/40/100 et un générateur indépendant de la météo.
- Commande NATURE : multiplicateur entier 0–100, valeur initiale 1, refus
  des valeurs supérieures ; les animaux nocturnes restent invisibles la nuit.
- Difficulté et indice Sierra dans l'en-tête de carte ; anciennes cartes
  compatibles avec les valeurs par défaut 4 et 31.
- Marche et nage arrêtées avant la bande extérieure de deux cases, avec
  message explicite et aucun temps facturé pour le pas refusé.
- Sondes du code original, scénarios par espèce et tests des quatre côtés.
  Cadence des tirages, durée de présence, déplacements et réactions restent
  provisoires ; NATURE n'accepte pas encore les valeurs fractionnaires.

### Sites visibles à distance

- Épave et cabane projetées à moins de huit cases : azimut depuis leurs
  coordonnées fixes, tailles par paliers et ancrage sur leur altitude.
- Insertion du sprite au pas de rayon correspondant à sa distance ; le relief
  situé devant le masque, celui situé derrière conserve le sprite visible.
- Composition toujours par colonne, sans chargement disque dans les rayons,
  avec les couleurs, la transparence et les pixels noirs des flux originaux.
- Module WILDPRJ pour préparer la géométrie et les bornes du terrain ; cache
  réutilisé quand position, cap et rencontre restent identiques.
- Rotations complètes près des sites, y compris lorsqu'ils sont hors champ,
  pour éviter les apparitions manquées et les traces du défilement partiel.
- Comparaisons exactes et parcours d'approche/retour à pied. Limite actuelle :
  un seul site par vue, sélectionné par distance dans le champ ; les animaux
  restent locaux et la projection est une règle propre au port.

### Cabane et TOPO

- `ENTER SHELTER`, `EXIT SHELTER` et `LEAVE SHELTER` à la cabane ; état
  intérieur conservé pendant REST, rotations et écrans STATUS/TOPO.
- Protection thermique de l'abri trouvé : air ambiant +15 °F, sans vent,
  comparée à la branche originale ; HUT reste une fabrication distincte.
- Refus de marche/nage à l'intérieur, absence de rencontres pendant le
  repos sous abri et restitution de la vue extérieure à la sortie.
- Première carte TOPO textuelle de 32 × 14 cases : relief, eau et repères
  joueur/épave/cabane/rangers, avec défilement borné par flèches ou WASD.
- Nouveau module disque WILDSIT ; résolution des qualificatifs déplacée
  dans WILDVOC pour préserver la petite marge de mémoire résidente.
- Parcours testé sans changement de position en mémoire : repérage, marche,
  entrée, repos au froid, sortie et retour ; tests supplémentaires de nuit
  et sondes locales des commandes et températures originales.

### Rendu par colonne

- Composition du sprite et du terrain dans chaque colonne, sans passe de
  superposition après la vue complète ; chargement disque avant le rendu.
- Remplissage limité aux zones transparentes et arrêt des rayons lorsque
  le relief maximal ne peut plus contribuer aux lignes encore visibles.
- Réutilisation du tampon de texte BLOAD pour les 160 couleurs de la colonne,
  avec conservation des pixels noirs opaques et des rotations.
- Épave descendue de dix lignes pour retrouver ses coordonnées verticales
  d'origine, sans empiéter sur le texte.
- Test de l'image intermédiaire, comparaisons exactes sur cinq cartes et
  profilage des pas de rayons et cycles hors chargement DOS.

### Documentation

- Réorganisation du TODO en lots ordonnés, avec la correction du rendu
  terrain/sprites en première priorité.
- README recentré sur l'état jouable, les commandes et la construction.
- Référence du portage regroupée dans `docs/IMPLEMENTATION.md` : règles
  provisoires, mémoire, format de carte, tests et outils.
- Nettoyage des mentions périmées dans les analyses et ajout de cet historique.

### Graphismes originaux

- Extraction des flux Journey de l'épave, de la cabane et des animaux,
  avec PNG transparents et manifeste des positions/empreintes.
- Branchement des sprites épave, cabane, ours, couguar et crotale Sierra
  dans la fenêtre de chargement disque de 2 Ko.
- Épave ancrée au départ, cabane placée sur terre et premières rencontres
  graphiques avec un générateur aléatoire indépendant.
- Préservation des couleurs, des pixels noirs et de la transparence ;
  clipping, suivi du cap, masquage nocturne et effacement au départ de la case.
- Tests des cinq images au pixel près et d'une rencontre après REST.
- La cabane est visuelle et les comportements des animaux restent à porter.

### Immersion

- SWIM traverse les cases d'eau et s'arrête avant la rive ; WALK rejoint la terre.
- Pertes des vêtements mouillés, température d'eau liée à l'altitude et
  bilan thermique immergé ; sueur supprimée dans l'eau.
- REST conserve l'immersion ; STATUS affiche IMMERSED. Un pas sur terre
  remet le sélecteur à sec. La cadence de nage reste reconstruite.

### Vent et énergie

- Température ressentie signée affichée dans STATUS et utilisée par la thermique.
- Dépense entière en kcal par pas ; supplément des frissons selon le poids,
  avec effet sur le déficit alimentaire et conservation du métabolisme de base.
- Comparaisons des formules de vent et d'énergie aux routines originales sur ROM.

### Thermique sèche

- Température corporelle selon air, activité et vêtements ; récupération
  bornée à 98,6 °F et seuil de dérive vérifié sur la ROM.
- Reconstruction déterministe des couches vestimentaires et facteurs de santé
  froid/chaud ; arrêt de l'activité lorsque la santé devient fatale.
- STATUS affiche température corporelle, frissons/sueur et hypo/hyperthermie.

### Modules disque

- Découpage du vocabulaire, des écrans et de l'environnement dans une fenêtre
  BLOAD partagée, avec cache du module courant.
- Préservation de la page zéro, du texte visible, de HGR et de l'état du jeu.
- Air horaire et thermique regroupés pour limiter les lectures pendant REST.

### Objets et charge

- WEAR, GET/PACK, CARRY/TAKE et DROP/REMOVE : corps, sac, main et sol.
- Positions au sol, reprise au retour, quantités accessibles et qualificatifs
  des noms partagés ; désactivation de la boussole lorsqu'elle est déposée.
- Poids et volumes par catégorie, refus atomiques de surcharge/débordement,
  vidage des conteneurs avant dépôt et capacités restantes dans INVENTORY.
- Limites du modèle calibrées sur les capacités de départ de l'original ;
  comptabilité exacte des conteneurs encore à établir.

### Socle jouable

- Vue de terrain 3D, cartes générées, rotations et défilement partiel,
  comparés au bit près à une référence Python.
- Parseur de 280 mots, marche, repos, repas, boisson, boussole,
  STATUS et INVENTORY.
- Horloge, date, soleil, air, énergie, déficits de survie, santé, mort
  et arrivée au poste de rangers.
- Tests des commandes aléatoires, refus de marche nocturne et calcul du temps
  sur les fortes pentes.
