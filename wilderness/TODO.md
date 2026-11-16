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

- [ ] Porter la précision aléatoire de la boussole, les pas et coûts de marche ;
  distinguer réserve au sol mémorisée et quantités accessibles dans les rapports.
- [ ] Conserver la géographie et les sites de la carte originale sans perte
  des cellules impaires ; établir un itinéraire crash → rangers rejouable.
- [ ] Comparer cet itinéraire jusqu'à la victoire, avec repas, hydratation,
  nuits, cabane, rencontres et traversée à la nage avec retour sur la rive,
  sans déplacement imposé en mémoire.
- [ ] Ajouter des variantes de mort, blessures/soins et reprise de sauvegarde.

La suite de modèles Python (`make test`) reste nécessaire, mais sa réussite
ne valide pas l'identité des deux jeux.

## 3. Remplacer les rencontres provisoires par la faune originale

- [ ] Établir la position, la durée et les déplacements des animaux ;
  remplacer leur expiration arbitraire à 60 minutes.
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
- [ ] Établir les vitesses et arrêts anticipés de marche de l'original,
  les modificateurs de blessures/équipement en nage et la synchronisation
  du recalcul de charge.
- [ ] Établir la comptabilité exacte des conteneurs, les limites de charge
  et leur effet sur la marche ; remplacer le modèle additif calibré.
- [ ] Compléter les déclencheurs par blessures, contamination et malaria,
  SPLINT, les soins thermiques et les transactions propres à USE
  (placement des objets, stérilisation de la trousse).
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

- [ ] Comparer la génération hydrologique au TMAKE original ; conserver
  la finesse des rives avec un format de carte à résolution complète.
- [ ] Étendre les sprites aux autres sites/objets et aux autres régions.
- [ ] Afficher plusieurs sites dans la même vue et lisser les paliers de taille,
  en mesurant la mémoire et les lectures disque nécessaires.
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
