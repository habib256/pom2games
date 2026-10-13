# Neowilderness — port DHGR et chargements en RAM

Le projet vise Apple IIe enhanced 128 Ko et IIc, à environ 1 MHz, avec une
page DHGR et une image ProDOS `dist/NEOWILDERNESS.po`. La priorité est de
supprimer les lectures disque pendant le jeu courant, puis de porter le rendu.
Les lots 1 et 2 sont faits (HGR sous ProDOS 128 Ko, modules en RAM), le
lot 3 aussi (paysage DHGR) ; l’interface DHGR, TOPO et MAP relèvent du lot 4.

Le point de départ est le contenu de travail de `../wilderness/` au
13 octobre 2026, modifications locales incluses, sur la base Git
`72af9374e01bc88d0b06b4fcea2dad89f3bb52a7`, puis synchronisé avec la tête de
`../wilderness` (commits `d90a563` et `277d455`). Le
[README](README.md) décrit cette copie ; le [backlog HGR](TODO_HGR.md)
conserve les travaux de gameplay hérités.

## Objectifs et limites de la première version

- [x] Charger au démarrage les modules nécessaires aux commandes, à la
  simulation, aux déplacements, aux sites et aux sprites.
- [x] Exécuter les commandes courantes sans lecture disque supplémentaire.
- [ ] Conserver les règles natives, l’ordre des tirages aléatoires, les
  demi-pas et leurs coûts ; comparer les états avec la référence HGR.
- [x] Afficher le paysage en DHGR couleur, 140 × 192 pixels couleur,
  avec une palette de 16 couleurs et du texte lisible (lot 3 ; bandeau et
  panneaux encore dessinés en HGR doublé, refonte au lot 4).
- [ ] Conserver TOPO/T comme carte graphique globale et MAP comme carte
  locale centrée sur le joueur. MAP est une extension absente de l’original.
- [ ] Concentrer les accès disque sur le démarrage, les changements de
  voyage et les sauvegardes lorsqu’elles seront implémentées.

Le premier port garde les calculs assembleur et les flottants Applesoft.
La réécriture du gameplay, une animation à 30 images/s et le double tampon
ne sont pas des prérequis. La résidence complète de la géographie native
fine sur 128 Ko doit être démontrée avant d’être annoncée.

## 0. Copie et référence

- [x] Copier les sources, outils, tests et analyses actuels dans
  `neowilderness/`, avec les corrections des trois tests de déplacement.
- [x] Séparer la disquette DOS provisoire `NEOWILDERNESS.dsk` et les chemins
  des tests/outils pour préserver `WILDERNESS.dsk`.
- [x] Conserver `../dev/` comme bibliothèque commune ; exclure les builds,
  caches et disques originaux de la copie.
- [x] Ignorer `neowilderness/original/` dans Git.
- [x] Conserver les mesures de référence dans
  [BASELINE_HGR.json](docs/BASELINE_HGR.json).
- [ ] Préparer les références locales nécessaires aux sprites et aux
  comparaisons sans les ajouter à Git.
- [x] Construire la copie HGR et enregistrer son fichier de symboles avec
  chaque disque de référence. Les adresses changent lors de la migration.
- [x] Exécuter les tests hérités ; identifier les attentes liées au matériel
  HGR/DOS séparément des assertions de simulation à conserver.

Mesures de la référence, en secondes invitées POM2 à environ 1 MHz :

| Commande | Total | DOS | Lectures de modules |
|---|---:|---:|---:|
| STATUS | 8,900 s | 8,696 s | 3 |
| LOOK R | 7,989 s | 6,031 s | 2 |
| WALK 1 H | 70,705 s | 61,248 s | 20 |

Ces mesures utilisent une session fraîche par commande et NATURE 0.
Elles ne constituent ni un temps maximum, ni une mesure de tous les disques
ou scénarios. `overlay_reads` ne compte pas le BLOAD direct de l’image TOPO :
la nouvelle instrumentation devra couvrir tous les appels disque.

## 1. Prototype mémoire 128 Ko — premier jalon

- [x] Inventorier chaque segment : code, constantes, état persistant,
  temporaires, dépendances et adresses absolues.
- [x] Définir un plan mémoire principal/auxiliaire incluant ProDOS, page
  zéro, pile, ROM flottante, tables vidéo et buffers de transfert.
- [x] Réserver une seule page DHGR : 8 Kio principaux + 8 Kio auxiliaires.
- [x] Déplacer la simulation hors de `$2000–$3FFF`, désormais vidéo.
- [x] Précharger les modules en RAM auxiliaire. Garder les fenêtres
  d’exécution principales nécessaires aux appels et retours existants.
- [x] Remplacer `overlay_load` par un transfert RAM ou une décompression
  RAM ; conserver un cache du module déjà présent et mesurer son coût.
- [x] Préserver les modules appelants, la pile, les flottants, les états
  vidéo, `RAMRD/RAMWRT`, `80STORE` et les interruptions autour des transferts.
- [x] Adapter les accès ROM/DOS existants aux nouvelles conventions bancaires.
- [x] Compter séparément lectures disque, octets copiés et cycles de calcul.

Budget initial mesuré sur les fichiers HGR, avant relocalisation :

| Contenu | Octets | Kio approximatifs |
|---|---:|---:|
| Images résidentes hors carte | 15 266 | 14,9 |
| Images des modules distincts | 32 585 | 31,8 |
| Carte courante avec bois | 9 766 | 9,5 |
| Cinq sprites | 4 838 | 4,7 |
| Une page DHGR | 16 384 | 16,0 |
| Sous-total | 78 839 | 77,0 |

Ce budget n’inclut pas le système, tous les états non initialisés, les
copies dans les fenêtres d’exécution, les nouveaux assets DHGR ni la marge.
Les images contiennent aussi des temporaires : le plan mémoire doit éviter
de compter deux fois les zones réellement partageables. Les 128 Ko ne sont
pas un espace linéaire ; vérifier les réservations et les conflits d’adresses.

État (lots 1–2) : plan et inventaire dans [MEMORY.md](docs/MEMORY.md) ;
`test_resident.py` (zéro appel MLI après préchargement, y compris santé et
changement de jour), `test_reference_state.py` (état identique à la référence
HGR après chaque étape) et `test_transfers.py` couvrent cette validation.

**Validation :** sur une copie expérimentale, STATUS, INVENTORY, HELP,
rotations, WALK/SWIM et soins n’effectuent plus de lectures de modules après
le préchargement. Leurs états de simulation restent identiques à HGR.
Mesurer au moins une séquence avec mise à jour de santé et changement de jour.

## 2. Démarrage et fichiers ProDOS

- [x] Créer `NEOWILDERNESS.SYSTEM` et le chargeur du jeu avec les outils
  de `../dev/tools/prodos/` et les services de `../dev/lib/prodos/`.
- [x] Regrouper les données initiales en fichiers séquentiels ; comparer
  chargement brut et compression pour le temps de démarrage réel.
- [x] Prendre possession de la mémoire auxiliaire selon le contrat ProDOS
  de la bibliothèque, avec une politique explicite pour un `/RAM` existant.
- [x] Restaurer le mode texte, les banques et les ressources système à QUIT
  et RESET ; afficher un message sur une machine incompatible.
- [ ] Ajouter construction, lancement et inspection de `NEOWILDERNESS.po`.
- [x] Valider amorçage et préchargement sur une image 5,25 pouces ; prévoir
  une image plus grande si les données du voyage ne tiennent pas.

État (lots 1–2) : le chargeur s'appelle `NEOWILD.SYSTEM` (15 caractères au
plus sous ProDOS). Démarrage, refus d'un ][+, QUIT, Ctrl-RESET, relance et
politique /RAM sont testés sur IIe enhanced (`test_prodos.py`) ; le IIc n'est
pas encore testé (a2shot n'émule que le //e), et `make run` n'a pas été lancé
dans l'application POM2. Mesures dans [BASELINE_128K.json](docs/BASELINE_128K.json).

**Validation :** démarrage reproductible sur IIe enhanced et IIc dans POM2,
retour ProDOS correct, absence de chargements cachés pendant les commandes.
Mesurer le premier écran jouable, la quantité lue et le temps de décompression.

## 3. Paysage DHGR

- [x] Relier des primitives DHGR testées : passes du jeu dans `src/dhgr.s`,
  dérivées du banc `src/dhgr_cols.s` (tables TN #3, adresses de lignes,
  lignes déroulées). `../dev/lib/hgrc/` n’est pas lié : il suppose
  `80STORE` inactif et ses écritures par `RAMWRT` sont incompatibles avec
  le code automodifié du moteur ([DHGR.md](docs/DHGR.md) § 6).
- [x] Définir la palette du ciel, de la terre, des reliefs, de l’eau,
  de la neige et des forêts ; établir des captures de référence
  (dix humeurs, `tools/dhgr_palette.py`, `build/dhgr/ref_*.png` et
  captures du jeu `build/dhgr/game_*.png`).
- [x] Garder les 140 rayons et la projection existante, puis remplacer
  le dessin HGR par des colonnes DHGR. Écritures par colonne en
  lecture-modification-écriture, une passe par banque ; le regroupement en
  octets (tampons + `dc_flush`) a été mesuré et écarté : ≈ 500 000 cycles
  et 7 Ko de plus par vue ([DHGR.md](docs/DHGR.md) § 10).
- [x] Adapter effacement, bandes remplies, cache du bandeau, défilement
  et rotations partielles aux banques principale et auxiliaire.
- [x] Porter soleil, lune, nuages et occlusion ; conserver les règles
  nocturnes, dont les paysages visibles à la pleine lune (règle HGR
  conservée, lumière de la pleine Lune graduée par sa hauteur et les nuages).
- [x] Sprites : flux originaux conservés et décodés colonne par colonne,
  4 couleurs par asset et ombrage de l’humeur (20 octets au lieu de
  11,7 Ko de sprites convertis) ; transparence, projection, clipping et
  masquage par le relief inchangés.
- [x] Mesurer les copies et le rendu à 1 MHz ; optimiser les boucles
  critiques en assembleur avant de multiplier la précision des calculs
  ([BASELINE_DHGR.json](docs/BASELINE_DHGR.json) : +2 à +5,4 % contre
  HGR 128 Ko).
- [x] Évaluer le double tampon seulement après mesure de la marge mémoire
  et des défauts de présentation : une seconde page coûte 16 Kio. Mesuré :
  128 octets libres en RAM principale, `$4000-$5FFF` occupé par le jeu ;
  vues complètes déjà préparées derrière le rideau texte. Non retenu
  ([MEMORY.md](docs/MEMORY.md) § 7).

État (lot 3) : `test_dhgr_ref.py` (géométrie DHGR = HGR avec les codes HGR),
`test_view`, `test_fuzz`, `test_play`, `test_sprites`, `test_scene_render`,
`test_pan`, `test_projection`, `test_forest`, `test_sky`, `test_moonlight`
comparent les deux banques à `tools/dhgr_ref.py` pixel pour pixel ;
`test_dhgr_mood.py` et `test_dhgr_video.py` couvrent humeurs, palette,
modes vidéo et lignes texte ; `test_reference_state.py` et
`test_resident.py` restent verts. Le IIc n’est pas testé (a2shot n’émule
que le //e) ; les franges composites du texte 80 colonnes restent à voir
sur machine.

**Validation :** comparer géométrie et visibilité à la référence HGR,
et les octets vidéo DHGR à une référence propre au nouveau format. Couvrir
les bords, les phases de sprites, les deux banques, les rotations et la nuit.
La palette différente ne doit pas masquer une régression de projection.

## 4. Interface, TOPO et MAP

- [ ] Porter boussole, résumé de survie, messages et saisie ; commencer
  avec quatre lignes texte, puis évaluer l’affichage 80 colonnes. (Lot 3 :
  boussole et panneaux en HGR doublé, messages en cellules 80 colonnes
  impaires par des primitives 40 colonnes propres ; 128 octets libres en
  RAM principale : prévoir un module.)
- [ ] Adapter STATUS, INVENTORY et HELP en conservant pagination,
  raccourcis, annulation et mise en évidence des dangers.
- [x] Générer TOPO depuis les données en RAM, ou depuis un asset déjà
  préchargé dont le coût mémoire est validé ; supprimer son BLOAD direct.
  (Module 0 `src/topo.s`, 1 531 octets au lieu de la feuille HGR de 8 Ko ;
  1,0 s d'ouverture ; `docs/MEMORY.md` §8.)
- [x] Porter les courbes, l’eau, les bois et les repères graphiques TOPO.
  (DHGR : teintes de 800 pieds, courbes de 400 pieds, eau, damier des bois,
  C/R/H/P, légende ; modèle exact `tools/topo_ref.py`, `docs/DHGR.md` §11.)
- [ ] Garder MAP centrée sur le joueur, son défilement, C pour recentrer
  et ses écritures différentielles pendant les déplacements.
- [ ] Rétablir la vue au retour des écrans sans lecture disque ni avance
  du temps ; vérifier objets, santé, hasard et position inchangés.
- [ ] Mettre à jour le nom affiché, l’accueil et la documentation du port.

**Validation :** toutes les transitions d’écrans sont testées au clavier,
avec relevé des lectures disque et vérification de l’état avant/après.
Définir les budgets de latence à partir du prototype, puis tester les
premières ouvertures et les ouvertures répétées séparément.

## 5. Géographie fine native

- [ ] Conserver les 224 × 168 positions, les rivières/lacs et les cellules
  impaires utilisées par la simulation native.
- [ ] Mesurer la compression par blocs sur plusieurs cartes et niveaux,
  y compris des données peu compressibles.
- [ ] Précharger l’atlas compressé et conserver plusieurs blocs décodés
  en cache RAM pour les requêtes de position et de voisinage.
- [ ] Vérifier le coût des changements de bloc et l’absence de lectures
  disque pendant une traversée de carte ou une collecte près d’une rive.
- [ ] Si le budget 128 Ko ne tient pas, documenter les options mesurées
  avant de choisir une extension RAM ou des chargements exceptionnels.

Référence locale : la géographie fine occupe 42 336 octets bruts ; sur
`wilderness/build/parity-stage15/map.bin`, elle occupe 11 305 octets
compressés indépendamment en 24 blocs avec le compresseur existant.
Cette observation sur une carte n’est pas une borne maximale.

**Validation :** concordance des interactions natives sur les cellules
paires/impaires, rives, bois et sites ; comptage des décompressions et des
lectures disque sur un itinéraire complet.

## 6. Validation finale et livraison

- [ ] Adapter les tests matériels HGR/DOS au DHGR/ProDOS, en conservant
  les assertions de comportement et les comparaisons aux routines originales.
- [ ] Rejouer les scénarios de survie et un trajet crash → rangers avec
  repas, eau, repos, cabane, rencontres, soins et traversée à la nage.
- [ ] Vérifier les garde-fous mémoire, page zéro, pile, changement de banque,
  interruptions et restaurations au retour système.
- [ ] Comparer les performances avec `docs/BASELINE_HGR.json` à fréquence
  identique ; distinguer disque, transferts RAM, décompression et calcul.
- [ ] Vérifier **zéro lecture disque pendant le jeu courant** après le
  chargement du voyage, avec instrumentation des appels MLI et des anciens
  chemins DOS, pas uniquement du compteur `overlay_reads`.
- [ ] Tester IIe enhanced et IIc ; compléter par une machine réelle si
  disponible. Le matériel DHGR d’un IIe dépend aussi de sa carte vidéo.
- [ ] Produire `dist/NEOWILDERNESS.po`, README, changelog et relevé mémoire
  final ; préciser les données locales nécessaires et les limites restantes.

**Terminé lorsque :** le port DHGR est jouable, les commandes et déplacements
courants ne déclenchent plus de lecture disque, les tests adaptés passent,
les états de simulation concordent avec HGR et les performances mesurées
sont publiées. La simple création d’un écran DHGR ne clôt pas le projet.
