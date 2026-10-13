# Wilderness — suite du développement

Le jeu dispose du moteur de terrain, des commandes de base, de la simulation,
de la gestion des objets et de la charge, de la thermique sèche/immergée et
des cinq sprites originaux de Sierra Nevada. La cabane est utilisable et
TOPO affiche les sites ; les filtres et taux Sierra de la faune sont portés,
mais ses déplacements, sa durée de présence et ses réactions restent provisoires.

L'état actuel et ses limites sont décrits dans le [README](README.md).
Les détails du portage et les tests sont dans
[IMPLEMENTATION.md](docs/IMPLEMENTATION.md) ; les preuves sur l'original
restent dans [ANALYSE.md](docs/ANALYSE.md) et [docs/logic/](docs/logic/ENGINE.md).
L’historique des étapes est dans [CHANGELOG.md](CHANGELOG.md).
Les lots ci-dessous donnent l'ordre de travail proposé.

## Priorité : une aventure complète comparée à l'original

Le pilote `make test-original` exécute l'original sur ROM et le port avec
les mêmes commandes. Il conserve les observations et échoue sur chaque
écart, sans ignorer une commande inachevée. Les cinq scénarios courts et la
marche native jusqu’à x70/y86 concordent ; ils ne couvrent pas encore
une arrivée aux rangers.
Voir [ADVENTURE_TESTS.md](docs/ADVENTURE_TESTS.md).

- [x] Comparer départ, boussole, parka, boissons, repas et repos répétés ;
  corriger temps des actions, crédits, cadence des compteurs, calories et
  pourcentages entiers de santé.
- [x] Observer l'état original paginé sur Journey avant sa réutilisation
  en page graphique, sans modifier le jeu ni ajouter de commande.
- [x] Porter l'onde lente de température et sa phase initiale Sierra ;
  comparer 405 cas à T09/S08 sur ROM. L'air concorde aux six points du départ.
- [x] Porter les températures journalières/horaire, fronts météo, hasard
  et plafonds du pas de santé ; comparer leurs routines sur ROM.
- [x] Faire concorder le vent et le ressenti dans les scénarios courts, dont
  la nuit, et dans la marche native jusqu’à x70/y86.
- [ ] Porter la précision aléatoire de la boussole, les pas et coûts de marche ;
  distinguer réserve au sol mémorisée et quantités accessibles dans les rapports.
- [ ] Conserver la géographie et les sites de la carte originale sans perte
  des cellules impaires ; établir un itinéraire crash → rangers rejouable.
- [ ] Comparer cet itinéraire jusqu'à la victoire, avec repas, hydratation,
  nuits, cabane, rencontres et traversée à la nage avec retour sur la rive,
  sans déplacement imposé en mémoire.
- [ ] Ajouter des variantes de mort, blessures/soins et reprise de sauvegarde.
- [x] Vérifier les nuits de pleine lune : ciel noir, relief, arbres, sites et
  animaux visibles ; conserver la nuit pour les calculs de survie.

La suite de modèles Python (`make test`) reste nécessaire, mais sa réussite
ne valide pas l'identité des deux jeux.

## Avant le prochain lot : place mémoire

- [x] Consulter `build/wild.map` et mesurer la place disponible avant d'ajouter
  du code résident. Les zones `$4000-$57FF`, `$6000-$6FFF` et `$1000-$1FFF`
  sont presque pleines depuis le branchement des sprites.
- [x] Déplacer les nouvelles règles et les écrans dans des modules disque ;
  conserver un état résident limité et explicite pour les sites et les abris.
- [x] Vérifier les changements de module avec sprites actifs : page zéro,
  texte, HGR, objets, horloge et cache doivent être préservés.

## 1. Rendu terrain et sprites — terminé

- [x] Remplacer la vue complète suivie d'une superposition par une composition
  terrain/sprites pendant le rendu de chaque colonne.
- [x] Utiliser la couverture opaque des sprites pour éviter les rayons et les
  remplissages qui ne peuvent plus contribuer à l'image ; tenir compte des
  trous transparents et des pixels noirs opaques.
- [x] Adapter le défilement et les rotations sans traînées ni changement de
  position apparente des sprites.
- [x] Mesurer les cycles et le nombre de pas de rayons avec et sans sprite,
  en distinguant le coût des chargements disque.

**Validation :** `test_scene_render.py` contrôle une image intermédiaire,
les pixels finaux et les pas de rayons sur cinq cartes, dont une sans plafond
déclaré. `test_sprites.py` couvre les cinq sprites aux bords et les rotations.
L'épave reprend sa hauteur d'origine, dix lignes plus bas.

## 2. Sites, cabane et orientation — terminé

Cabane, TOPO et projection des sites voisins intégrés. Le prochain lot
concerne les règles originales de la faune.

- [x] Établir les commandes et l'état intérieur/extérieur de la cabane dans
  l'original ; distinguer une cabane trouvée d'un abri construit (`HUT`).
- [x] Permettre d'entrer et de sortir, avec des refus utiles hors du site.
- [x] Appliquer la protection thermique pendant le repos et rétablir le
  milieu extérieur à la sortie ; refuser marche/nage tant qu'on reste dedans.
- [x] Rendre les sites repérables depuis les cases voisines : distance,
  orientation, taille et occlusion des sprites ; conserver leur position
  lors des déplacements et des retours.
- [x] Ajouter un premier écran TOPO utilisable : relief, eau, position,
  épave, cabane et poste de rangers, avec défilement.

**Validation :** trouver la cabane sans modifier la mémoire, entrer, se
reposer au froid, sortir et revenir ; comparer intérieur/extérieur et vérifier
l'effacement des sprites pendant les rotations et les changements de case.
`test_projection.py` compare les images à une référence indépendante :
directions, fractions de case, tailles, clipping, relief devant/derrière,
cache et approche/retour par WALK. La première version affiche un seul site
à la fois, dans un rayon de huit cases ; la projection est une règle du port.

## 3. Remplacer les rencontres provisoires par la faune originale

- [x] Porter les critères Sierra : saison, heure, altitude, terrain,
  difficulté et fréquence réglée par `NATURE`.
- [x] Tirer les rencontres à chaque pas de simulation plutôt qu'au retour
  à la vue ; supprimer le cumul plafonné à 255 minutes des actions longues.
- [x] Tester toutes les espèces même avec un animal présent, porter sa
  conservation/remplacement à 50 % et interrompre la marche sur acceptation.
- [ ] Établir la position, la durée et les déplacements des animaux ;
  remplacer leur expiration arbitraire à 60 minutes.
- [x] Rendre les rencontres jouables : SCARE/IGNORE/ATTACK, outils,
  coupures/morsures, protection par arbre/cabane et bilan des rencontres.
- [x] Sonder les seuils Sierra de bruit, blessures, outils de combat et vol
  sur ROM ; remplacer les réussites automatiques et donner un effet aux provisions.
- [x] Vérifier la distribution de gravité ours/couguar sur ROM et déclencher
  coupures, fractures ou choc avec les conditions et soins existants.
- [x] Sonder les postures et abris natifs sur ROM : risque distinct au sol,
  IGNORE et arbre ; supprimer l’invulnérabilité du joueur dans l’arbre.
- [ ] Compléter les réactions natives : mouvement, délais, autres moyens,
  branche critique du cinquième degré, durée des morsures, chasse/carcasse
  et contexte intérieur/recherche.
- [ ] Relier les conséquences aux conditions de santé et aux soins :
  FIRSTAID KIT, SNAKEBITE KIT et blessures concernées.

**Validation :** scénarios déterministes pour chaque espèce, absence de
rencontre hors des critères, conservation de l'état lors des chargements,
et transitions entre observation, action, blessure et soin.
`re_fauna_probe.py` exécute 162 cas de filtrage et 45 probabilités dans le
code original. `test_fauna.py` les vérifie dans le port et couvre les
exclusions, la pente diagonale, les trois espèces et le réglage NATURE.
`re_fauna_accept_probe.py` contrôle 36 conservations/remplacements et les
drapeaux d'interruption originaux. `test_fauna_steps.py` vérifie les pas d'un
repos sans tirage, les interruptions de marche, les refus de remplacement et l'abri.

## 4. Compléter le milieu thermique : météo, pluie et feu

- [ ] Porter les fronts météo : ciel, pluie, neige, vent, tendance et gel.
  Le vent ressenti est déjà intégré ; l'évolution complète des fronts manque.
- [ ] Relier la pluie au sélecteur d'humidité et aux protections portées ;
  établir les transitions hors pluie sans inventer un séchage progressif.
- [ ] Porter l'allumage, le combustible, la durée et l'extinction du feu.
- [ ] Combiner correctement air, vent, immersion, abri et feu ; compléter
  les déclencheurs et les soins des conditions thermiques 20–21.
- [ ] Adapter la visibilité de la vue à la météo et afficher le soleil
  selon l'heure. Le budget de rayons météo, le masquage par nuages et le
  soleil saisonnier sont présents ; leur fidélité complète à l'original
  reste à comparer. La lune nocturne datée 1985 est une extension documentée.

**Validation :** mêmes scénarios secs, sous pluie, immergés, sous abri et près
du feu ; comparer aux routines originales et conserver les tests froid/chaud,
les calories des frissons et la récupération vers 98,6 °F.

## 5. Compléter les actions et les risques de survie

- [ ] Terrain : forêts, rives, pente (`SLOPE`), chutes et déplacements dangereux.
- [x] Arrêter marche et nage à deux cases des limites de la carte ; conserver
  la position et ne facturer que les pas acceptés (`test_boundary.py`).
- [x] Porter l'effort de nage selon le poids total et vérifier 81 métabolismes
  sur la ROM originale ; conserver les tests immersion et sortie sur la rive.
- [x] Porter la durée de nage normale selon santé/charge, vérifier 143 pas
  sur ROM, avancer par demi-cases et admettre le dernier pas à mi-durée.
- [x] Porter le tracé entier des caps obliques ; comparer 2 880 positions
  pour les 360 caps aux routines originales sur ROM.
- [ ] Établir les vitesses et arrêts anticipés de marche de l'original,
  les modificateurs de blessures/équipement en nage et la synchronisation
  du recalcul de charge.
- [ ] Établir la comptabilité exacte des conteneurs, les limites de charge
  et leur effet sur la marche ; remplacer le modèle additif calibré.
- [x] Porter les courbes et prérequis des blessures/maladies 1–15 ;
  comparer progression, prévention, traitement et altitude à l'original.
- [x] Raccorder les compteurs sel/froid, USE médical, STOP BLEEDING
  et l'état médical paginé.
- [x] Décompter les doses positives, afficher les utilisations restantes,
  porter les prises orales, SHIELD EYES, LOWER HEAD et SUCK VENOM ;
  vérifier les refus et le comportement natif des stocks épuisés sur ROM.
- [ ] Compléter les déclencheurs par blessures, contamination et malaria,
  SPLINT, les soins thermiques et les transactions propres à USE
  (placement des objets, stérilisation de la trousse).
- [x] Collecter de l’eau à la berge avec gourde, capacité et charge ;
  déclencher la giardiase depuis une réserve non traitée consommée.
- [ ] Comparer collecte/contamination à l’original et porter le traitement
  de l’eau ; ajouter chasse, pêche et cueillette.
- [ ] Porter la fabrication par familles d'objets : abris, outils et armes
  (HUT, IGLOO, TRENCH, BOW, SPEAR…), avec consommations et temps d'action.
- [ ] Compléter HELP, les messages et les saisies propres aux nouvelles actions.

**Validation :** chaque action respecte le temps, la charge, l'accessibilité
et les quantités ; les refus conservent l'état et les effets de santé sont
vérifiés avec et sans soin.

## 6. Permettre des parties longues et plusieurs régions

- [ ] SAVE / RESTORE : définir un format versionné comprenant carte, objets
  au sol, simulation, météo, sites, faune et générateurs aléatoires.
- [ ] Vérifier une reprise identique après sauvegarde et les erreurs de lecture.
- [ ] Intégrer les six régions : paramètres climatiques, faune, sprites et cartes.
- [ ] Compléter les effets des dix niveaux de difficulté.
- [ ] Évaluer le second scénario et CLUE après stabilisation du parcours
  crash → poste de rangers.

## Améliorations du rendu et de la carte

Ces travaux peuvent accompagner les lots précédents après mesure du bénéfice.

- [x] Remplacer les faux lacs de plateaux par un écoulement vers les exutoires ;
  remplir les cuvettes à niveau constant et conserver les rivières fines
  dans les blocs 2 × 2, sans effacer de tronçons autour des sites.
- [ ] Comparer la génération hydrologique au TMAKE original ; conserver
  la finesse des rives avec un format de carte à résolution complète.
- [ ] Étendre les sprites aux autres sites/objets et aux autres régions.
- [ ] Afficher plusieurs sites dans la même vue et lisser les paliers de taille,
  en mesurant la mémoire et les lectures disque nécessaires.
- [x] Ajouter les forêts à la carte et à la vue avec un format de données adapté.
- [x] Porter les interactions avec les arbres : grimper et suspendre la nourriture,
  récupérer le sac à sa case et vérifier les capacités sans perdre de stock.
- [ ] Profiler les vues et déplacements représentatifs avec `tools/profile.py`,
  en distinguant rendu et lectures disque ; conserver le rendu au bit près.
- [ ] Réévaluer la division déroulée appelée en sous-routine si une marge mémoire
  devient disponible. Les mesures et pistes antérieures sont conservées dans
  [IMPLEMENTATION.md](docs/IMPLEMENTATION.md#performance).

## Vérifications à conserver

`make test` couvre les sprites, le terrain, les commandes aléatoires,
la simulation, les objets, la charge, les modules disque et la thermique.
Étendre les tests du sous-système modifié, puis exécuter la suite complète
avant de considérer un lot terminé. Les règles reconstruites doivent rester
identifiées comme telles jusqu'à leur comparaison avec l'original.
