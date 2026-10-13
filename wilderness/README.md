# Wilderness

Réimplémentation de *Wilderness: A Survival Adventure* (Electric Transit,
1985) pour Apple II+ 48 Ko, sous DOS 3.3. Le joueur survit à un crash d'avion
et doit rejoindre le poste de rangers en gérant son équipement, ses réserves
et son état physique.

L'original est l'œuvre de Wesley Huntress, Charles Kohlhase et Peter
Farson. Son moteur de rendu 3D a été développé par Wesley Huntress et
Charles Kohlhase, deux chercheurs du JPL (NASA) ayant travaillé sur les
trajectoires et l'imagerie des missions Mariner et Voyager ; l'algorithme
adapte les techniques de modélisation altimétrique spatiale aux contraintes
extrêmes du MOS 6502 (1,023 MHz, 64 Ko de RAM, aucun coprocesseur
mathématique).

Le jeu comprend la vue 3D, les cartes générées, la marche et la nage,
les objets et la charge, les écrans STATUS/INVENTORY, l'horloge, le cycle jour/nuit,
la température, l'énergie, les déficits de survie, la santé et la thermique
sèche ou immergée. Les sprites originaux de l'épave, de la cabane, de l'ours,
du couguar et du crotale sont composés avec le terrain pendant le rendu de
chaque colonne, avec leurs couleurs et leur transparence. La vue TOPO permet
de repérer les sites ; la cabane accueille le joueur et le protège du froid.

Les rencontres utilisent les critères Sierra et leur probabilité selon la
durée, la difficulté et `NATURE`. Les réactions SCARE/IGNORE/ATTACK utilisent maintenant les seuils Sierra de
bruit, de blessures et de combat, vérifiés sur ROM. Le retrait des animaux,
la cadence des réactions et les protections restent des adaptations du port.
Les 15 conditions médicales ont leurs courbes d'incubation et de guérison,
avec les règles de prévention/traitement de l'original. La perte de sel,
le froid et l'exposition solaire peuvent les déclencher ; l'altitude et
l'oxygène agissent sur la santé. `STATUS`, puis `M`, affiche le détail médical.
Les attaques déclenchent coupures, fractures, choc ou morsure empoisonnée ; boire de l’eau
collectée peut déclencher la giardiase. Les chutes et les autres contaminations
restent à raccorder. Les consommables médicaux décomptent leurs utilisations positives,
affichées dans INVENTORY, avec le comportement natif des stocks épuisés.
La pluie, le feu, les abris fabriqués, les soins complémentaires,
la fabrication et les sauvegardes restent à développer. TOPO est une première
carte textuelle du relief. La suite est ordonnée dans le [TODO](TODO.md), avec
les déplacements et la cadence originale des réactions en prochaine priorité.

Les transitions texte/HGR préparent les menus derrière le paysage et
masquent les rendus complets jusqu’à leur achèvement. La pagination réécrit
uniquement les caractères modifiés, sans anciennes lignes résiduelles.
Le texte d’accueil reste visible pendant tout le chargement initial,
jusqu’à l’apparition du paysage terminé. Les rotations partielles gardent
leur défilement progressif. Le retour de
TOPO reste soumis aux lectures disque et au rendu du port 48 Ko.

## Construire et lancer

Depuis `wilderness/`, avec les outils cc65 et les outils partagés de `dev/` :

```sh
make                 # construit ../dist/WILDERNESS.dsk
make run             # lance la disquette dans POM2
make test            # tests dans l'émulateur a2shot
make fuzz            # comparaisons de rendu plus longues
make SEED=7 LEVEL=8   # autre carte, difficulté 1 à 10
```

La construction utilise `build/JOURNEY.dsk` et l'A2R Journey local pour
extraire les sprites. Lorsqu'ils manquent, les règles de construction peuvent
récupérer les extras de l'original depuis archive.org. `make originals` et
`make extract` préparent l'ensemble des données d'analyse. Les images disque
et leurs extractions restent dans `original/` et `build/`, ignorés par git ;
les cinq sprites sont inclus dans la disquette construite localement.

Le démarrage utilise un chargeur temporaire à `$5800`, qui décompresse les
fichiers résidents depuis le tampon de la future page HGR à `$2000`. La
disquette place les listes de secteurs avant les données et utilise un ordre
de secteurs adapté aux lectures DOS. Sur la carte par défaut, les blocs résidents
et leur remplissage occupent 25 035 octets et deviennent 16 328 octets
répartis dans deux fichiers. L'entrelacement
de neuf secteurs reçoit un décalage d'un secteur physique entre pistes.
Mesuré dans le cœur POM2 à la vitesse Apple II, le lancement du moteur arrive
à 19,39 secondes et la première invite jouable à 45,11 sur la carte courante.
L'initialisation, les modules et le premier rendu sont inclus dans ce dernier
temps. Avant les optimisations mémoire et Disk II, les deux mesures étaient 24,16 et
47,47 secondes avec les mêmes fonctionnalités.

`python3 tools/profile_loading.py` mesure le démarrage et deux lectures de
modules. `python3 tests/test_boot.py` vérifie chaque octet restitué, également
avec une carte peu compressible qui nécessite un fichier supplémentaire.

L'organisation mémoire évite désormais des chargements de vocabulaire et de
LOOK pour les commandes fréquentes. Sur la carte par défaut, `VIEW` passe
de 12,47 à 5,63 secondes, `LOOK R` de 10,43 à 7,26 et `STATUS` au départ de
12,27 à 3,69. Après une action, STATUS passe de 12,36 à 9,28 secondes.
L'arrêt des recherches d'arbres devenues inutiles et l'effacement par lignes
retirent encore environ 0,56 seconde au redessin. Le sommeil de huit heures
prend désormais 22,70 secondes, contre 26,39 après la première optimisation.
`python3 tools/profile_actions.py` mesure les cycles et lectures disque ;
son option `--profile` répartit les cycles entre résident, simulation,
modules, DOS et ROM. Le disque représente encore 68 % du sommeil et
77 % de la marche avant la dernière réduction des transferts ;
`REST`, `SLEEP`, `WALK` et `SWIM` avec une durée directe de 1 à 255 H/MIN
évitent désormais le chargement de la saisie. Le repos d’une heure prend
21,11 secondes et la marche 26,96, avec une lecture de moins chacun ;
les conditions et le détail de la mémoire sont décrits dans
[IMPLEMENTATION.md](docs/IMPLEMENTATION.md#mémoire-et-modules-disque).

La simulation et trois sprites sont maintenant compressés sur disquette et
décompressés directement dans leur fenêtre mémoire. La simulation lit 22
secteurs de données au lieu de 32 ; l'épave, l'ours et la cabane en économisent
deux chacun. Le placement des fichiers suivants reste conservé. Les transferts
diminuent, mais la décompression absorbe presque tout le gain sur REST/SLEEP ;
les temps ci-dessus comprennent ce coût. `test_overlay_codec.py` contrôle
les fichiers DOS, les 20 chargements natifs et leur intégrité mémoire.

## Commandes

Les commandes suivent la forme verbe + nom. Les durées et les quantités peuvent
être demandées ensuite ou saisies directement : `WALK 10 MIN`, `REST 1 H`,
`DRINK WATER 4 OZ`, `EAT CHEESE 8 OZ`. Sans unité, les durées restent en heures
et les quantités en onces. Les autres mots reconnus du vocabulaire original répondent
« NOT IN THIS VERSION YET » lorsqu'aucune action n'est implémentée.

| Commande | Effet |
|---|---|
| WALK, GO, RUN, MOVE, CRAWL | Marcher droit devant pendant *n* heures ; arrêt à deux cases du bord, à l'eau ou à la nuit |
| SWIM | Entrer dans l'eau depuis la berge, nager pendant *n* heures, sortir sur la rive opposée ; arrêt à deux cases du bord ou à la nuit ; WALK pour continuer sur terre |
| REST, SLEEP, CAMP, EXERCISE / WAIT, PAUSE | Se reposer / attendre *n* heures |
| EAT *aliment*, DRINK WATER | Consommer *n* onces accessibles, d'abord dans le sac/la gourde, puis au sol |
| FILL CANTEEN / REFILL CANTEEN | Remplir à 64 OZ depuis une case d’eau ou une berge voisine, en 10 minutes ; gourde transportée et charge disponible requises ; eau non traitée |
| SCARE / IGNORE / ATTACK *animal* | Réagir à l’animal présent : bruit, attente ou combat ; effets incertains selon l’espèce, hache/couteau requis pour ATTACK |
| GET, PACK *objet* | Ranger un objet accessible dans le sac |
| TAKE, CARRY *objet* | Prendre un équipement en main ; aliments/eau dans le sac/la gourde |
| WEAR *vêtement* | Porter un vêtement accessible, une montre ou des lunettes |
| USE *produit médical* | Appliquer les prérequis de prévention/soin et consommer une utilisation positive ; temps propre au produit, objet accessible requis |
| EAT / DRINK FLAGYL, SALT TABLETS, QUININE | Prendre une dose ; les trousses, crèmes, lunettes, l'oxygène et le savon doivent être utilisés avec USE |
| STOP BLEEDING | Compression, 30 minutes ; contribue au traitement des coupures |
| SHIELD EYES / LOWER HEAD | Protéger les yeux / baisser la tête ; prérequis de soin, sans dépense de temps |
| SUCK VENOM | Extraire le venin d'une morsure active, en 15 minutes ; contribue au traitement |
| USE COMPASS | Vérifier la disponibilité de la boussole, sans consommer de temps |
| DROP, REMOVE *objet* | Déposer l'objet à la case courante ; tout le stock pour les aliments/eau |
| CLIMB TREE / CLIMB DOWN | Grimper dans un arbre proche / redescendre ; santé supérieure à 2,5 requise pour monter, déplacements bloqués dans l’arbre |
| HANG FOOD | Suspendre le sac et son contenu à la case courante, en 30 minutes ; nécessite un arbre et un sac accessible |
| GET BACKPACK / LOWER FOOD, LOWER BACKPACK | Récupérer le sac suspendu à sa case ; refus si la charge dépasserait les capacités |
| LOOK L, R, B, F / N, E, S, W | Tourner de 45°, se retourner, regarder devant ou vers un point cardinal |
| ← → sur une ligne vide | Tourner de 22,5° |
| ENTER SHELTER / EXIT SHELTER, LEAVE SHELTER | Entrer dans la cabane à sa case / ressortir ; aucun temps consommé |
| NATURE / NATURE 0 | Fréquence des rencontres : entier de 0 à 100, valeur initiale 1 ; 0 empêche les nouvelles rencontres ; valeur directe ou demandée à l'invite |
| TOPO, T | Carte graphique complète : courbes de niveau tous les 400 pieds, eau, bois, épave, cabane et rangers ; nord en haut ; Entrée/Espace/ESC pour revenir |
| MAP | Carte textuelle centrée sur le joueur : relief, eau, joueur, épave, cabane et rangers ; flèches ou WASD pour défiler, C pour recentrer, cap cardinal magnétique, Entrée/Espace/ESC pour revenir |
| STATUS, INVENTORY, VIEW, HELP | Afficher les écrans ou la vue ; HELP propose trois pages (déplacement, équipement, survie) avec exemples, touches 1/2/3, N/Espace ou B, Échap/Entrée pour revenir |
| M dans STATUS / B dans l'état médical | Consulter les conditions médicales / revenir à STATUS |
| I/S/T/H dans les écrans | Aller directement à INVENTORY, STATUS, TOPO ou HELP, selon les raccourcis affichés en bas de l'écran |
| ESC pendant une saisie | Effacer la commande ou annuler la quantité/durée, sans avancer le temps |
| ESC pendant WALK / SWIM | Arrêter après le pas en cours ; conserver la position atteinte et afficher le temps réellement parcouru |
| QUIT | Demander confirmation avant retour à DOS ; seul Y confirme, Entrée/N/ESC annulent |

La flèche gauche efface le dernier caractère, également pendant la saisie
d'une quantité. Une réponse vide ou zéro annule une action numérique ;
`NATURE` conserve son réglage valide à zéro. Les valeurs négatives, décimales,
les unités inconnues et les dépassements sont refusés avant toute action.
Les limites sont 255 heures, 15 300 minutes ou 255 onces. Échap revient à la
vue depuis STATUS, TOPO ou n'importe quelle page d'INVENTORY.

Les médicaments s'utilisent une dose à la fois, sans nombre ni unité :
`EAT FLAGYL` est valide, tandis que `EAT FLAGYL 0 OZ` est refusé sans
consommer de dose ni appliquer de soin.

Les résultats restent visibles jusqu'à l'action suivante, sans touche de
confirmation entre deux messages. Un déplacement affiche ensemble son temps
effectif et sa cause d'arrêt. Les dangers remplacent les réussites génériques.
Avant une consommation, l'invite indique les onces accessibles ; le résultat
annonce les onces réellement consommées et le stock accessible avant l'action,
même lorsque la demande dépassait ce stock.

Un transfert refusé distingue poids et volume, avec l'excédent et la capacité
disponible. Les volumes précisent WEAR, PACK ou HAND. Par exemple, le ramassage
initial des pommes dépasse le poids de 5 OZ, pour 43 OZ disponibles. Les
messages distinguent aussi le conteneur à récupérer du conteneur à vider et
proposent des commandes disponibles pour corriger une saisie incomplète.

Quand WALK indique l'eau, conserver le cap et lancer SWIM. Si la durée
demandée s'épuise dans l'eau, un nouveau SWIM poursuit depuis la position
atteinte. La vitesse dépend de la santé et du poids transporté : deux commandes
d'une heure ne garantissent pas une traversée complète. À l'arrivée sur terre,
SWIM s'arrête et indique de continuer avec WALK.

WALK et SWIM avancent par demi-cases, avec une durée calculée selon la
charge, la santé, la météo et le terrain. Un pas est admis s’il reste au
moins la moitié entière de son coût ; il consomme ensuite sa durée complète
et peut dépasser la durée demandée. Par exemple, pour un pas de 9 minutes,
3 minutes sont refusées sans avancer le temps, tandis que 4 minutes
permettent de parcourir une demi-case en 9 minutes. Le compte rendu affiche
la durée effective.
Le repos accepte les minutes, mais son interruption pendant l'activité reste
à développer.

## Jouer avec l'état actuel

La boussole est disponible dès le départ : aucune commande d'activation.
Un ruban encadré, centré en haut de la vue sur environ un tiers de sa largeur,
affiche N, NE, E, SE, S, SW, W et NW. Les repères défilent sous un curseur
fixe qui indique la direction regardée ; les graduations intermédiaires
correspondent à 22,5°. `LOOK N`, `LOOK E`, `LOOK S` et `LOOK W` orientent
vers les points cardinaux magnétiques. Le ruban reste visible la nuit
et dans la cabane. Les côtés du bandeau affichent l'heure (ou la période sans
montre), la santé, la faim, la soif et une alerte ou indication thermique. `WALK` avance dans la direction du curseur, sans guidage automatique
vers les rangers.

Le soleil se place selon la latitude, la saison et l'heure solaire du jeu
(midi à 12 h), par rapport au nord géographique. La lune nocturne utilise
une éphéméride de référence de 1985 et une phase stylisée ; elle ne se trouve
pas systématiquement à l'opposé du soleil. Les nuages et le relief masquent
les astres. Regarder horizontalement peut laisser un astre haut hors de la vue.
Le calendrier lunaire répète l'année 1985, l'original ne donnant pas d'année.
Les nuits de pleine lune (disque lunaire entièrement éclairé), le ciel reste
noir mais le relief, les arbres, les sites et les animaux sont visibles.
Les autres nuits conservent un paysage noir. La lune est une extension du port, tandis que
l'original dessine le soleil et propose `LOOK STARS`.

Les objets déposés restent à leur case et sont récupérables au retour.
STATUS distingue les réserves CARRIED de celles HERE, disponibles au sol
sur la case courante ; FOOD/WATER restent les totaux accessibles. INVENTORY
regroupe WORN, IN HAND, IN PACK et GROUND HERE : touches 1 à 4, 12 objets
par page, N/Espace/Entrée pour avancer, B pour revenir, Échap pour la vue.
Le groupe consulté apparaît en vidéo inverse avec son nombre d'objets ;
les capacités libres sont explicitement marquées FREE. La touche 5 affiche
le contenu suspendu à proximité lorsqu'un sac a été accroché à un arbre.
Un aliment réparti entre sac et sol apparaît dans les deux groupes avec
la quantité propre à chaque emplacement. Les capacités restent visibles.
Les qualificatifs distinguent notamment COTTON SOCKS, FIRSTAID KIT,
SNAKEBITE KIT, SEWING KIT et SALT TABLETS. Les transferts ne coûtent pas
encore de temps.

Une surcharge refuse le transfert entier. INVENTORY affiche les capacités
restantes en OZ et IN3. Le sac et la gourde doivent être vidés avant dépôt,
puis repris avant de pouvoir les remplir. Exemple au départ : `GET APPLES`
dépasse la charge ; `DROP AXE` libère assez de place pour les prendre.

Le résumé signale une transition de faim, soif, santé, état thermique,
immersion ou condition médicale, sans répéter une classe inchangée. Une
alerte de danger apparaît en vidéo inverse, tandis qu'une amélioration reste
en texte normal. Les niveaux VERY de faim et de soif et une santé sous 40 %
restent mis en évidence tant que leur valeur est critique.
Sans indication prioritaire, le bandeau propose TOPO/HELP de jour,
REST/HELP la nuit ou LOWER FOOD à la case du sac suspendu.
Une activité longue conserve l'alerte prioritaire jusqu'au résultat ; STATUS
permet de voir toutes les conditions. Sans danger actif, le bandeau rappelle
ENTER/EXIT SHELTER ou ITEMS: INV si des objets sont récupérables ici. Les
rotations conservent ces indications sans lecture disque supplémentaire.

Les vêtements portés modifient le bilan thermique. STATUS affiche la
température corporelle, FEEL (température ressentie), SHIVERING/SWEATING,
les conditions HYPOTHERMIA/HYPERTHERMIA et IMMERSED lorsque le joueur est
dans l'eau. Les frissons augmentent la dépense énergétique ; froid et chaleur
peuvent réduire la santé et interrompre une activité devenue fatale.
REST dans l'eau conserve l'immersion. Un pas sur terre rétablit le sélecteur sec.

L'épave reste au lieu du crash. Une cabane est placée sur terre au tiers du
trajet vers les rangers. L'épave et la cabane sont visibles à moins de huit
cases, avec une taille réduite selon la distance et un masquage par le relief
situé devant elles. Un seul site est affiché par vue : le plus proche dans
le champ, avec priorité au site ou à l'animal de la case courante.
Les animaux restent affichés à leur case. Tourner ou se déplacer efface
l'ancienne image et recalcule la position des sites.
Les rotations de 22,5° et 45° réutilisent le terrain, les sprites locaux et
la géométrie d'un site distant unique, même lorsqu'il est hors champ :
seules les colonnes nouvellement visibles sont calculées, en partant du bord
de la vue conservée. Les rotations par flèches ne relisent alors aucun module
disque. Si plusieurs sites peuvent être proches, la vue est reprojetée pour
respecter la sélection du plus proche dans le champ. Le masquage par le relief
est conservé dans les deux cas. Les sites sont masqués les nuits sans pleine lune. Sur MAP, `H` repère la cabane, `C` l'épave, `R` les
rangers et `P` le joueur. L'eau est marquée `=` ; le nord est en haut.
À chaque ouverture, MAP se recentre sur la position actuelle et reconstruit
le relief et les repères avant d'afficher la carte. C recentre aussi après
défilement. HEAD affiche un cap en unités 0–559, son point cardinal et MAG,
cohérents avec la boussole. La cabane et l’épave dans la vue 3D suivent
les mêmes directions nord/sud/est/ouest que leurs repères sur MAP. Une ligne indique le site sous P : épave, cabane
avec ENTER/EXIT SHELTER, ou rangers.
TOPO affiche une feuille graphique couvrant tout le terrain, calculée lors de
la construction du disque à partir de sa carte. Les courbes vertes sont
interpolées tous les 400 pieds ; l’eau est magenta et les repères C/H/R sont
blancs. Cette feuille reste fixe, comme une carte papier. MAP affiche la
position actuelle du joueur et permet de défiler et de se recentrer.
Le tracé TOPO reprend la présentation de l’original à partir de la grille
du port ; il ne réutilise pas ses images ni son format de courbes natif.

Pendant la marche, MAP se met à jour après chaque pas. Chaque
caractère est comparé à celui déjà affiché : seules les différences sont
écrites, sans effacement préalable, également pendant le défilement manuel.
Les mises à jour de marche restent dans les vingt rangs supérieurs ; les
messages de progression restent en bas. La vue 3D revient à la fin du trajet.

À la cabane, `ENTER SHELTER` met à l'abri : la thermique utilise la température
ambiante +15 °F au lieu du ressenti du vent. REST reste à l'intérieur et
STATUS indique INSIDE SHELTER. `EXIT SHELTER` permet de repartir. La vue
intérieure affiche une description sur fond noir ; `HUT` reste réservé aux
abris fabriqués, encore à porter.

La marche et la nage s'arrêtent avant d'entrer dans une bande de deux cases
autour de la carte. Le pas refusé ne consomme pas de temps.

Les filtres Sierra prennent en compte la saison, l'heure, le terrain,
l'altitude, la pente et l'indice régional. L'ours et le couguar peuvent
apparaître la nuit ; leurs sprites sont visibles à la pleine lune.
La probabilité utilise la durée écoulée, la racine de la difficulté et le
réglage `NATURE`. La carte native utilise le hasard partagé avec la météo et la boussole.
La durée de présence et les réactions automatiques restent à comparer ;
la règle provisoire réévalue les rencontres après 60 minutes sans décision
et les efface au départ de la case. Les zones
boisées participent aux filtres de terrain. Les tirages ont lieu à chaque pas de marche
ou de nage. Les ressources et rencontres des repas et attentes suivent les filtres natifs.
Une rencontre acceptée interrompt le déplacement après
ce pas. Toutes les espèces
sont testées dans l'ordre Sierra ; un animal présent peut être remplacé avec
une chance sur deux. Le repos à la cabane ne tire aucune rencontre extérieure.

Les règles encore reconstruites — déplacements, charge, rencontres et
certaines conditions physiologiques — sont détaillées dans
[IMPLEMENTATION.md](docs/IMPLEMENTATION.md#règles-provisoires-et-écarts).
La nage normale utilise maintenant des demi-cases et une durée calculée
selon santé/charge, vérifiée sur 143 cas contre les routines originales.
Les caps obliques sont vérifiés sur 2 880 positions contre l'original ;
blessures et changements d'équipement demandent encore une comparaison
en aventure complète.

## Progression, ravitaillement et arrivée

STATUS affiche `DONE` : 0 % au crash, progression selon la distance directe
restante, 100 % après une arrivée effective. `TO … CELLS` indique cette
distance arrondie au-dessus, fractions de case comprises. Un détour peut
faire redescendre la progression. Le score d’efficacité hérité de l’original
est conservé dans le bilan final sous `NATIVE JOURNEY SCORE` : ce score
n’est pas une mesure du chemin parcouru.

`FILL CANTEEN` et `REFILL CANTEEN` remplissent la gourde transportée à 64 OZ
(2 quarts), sans quantité. L’eau doit être sur la case ou dans l’une des huit
cases voisines. L’opération dure 10 minutes et est entièrement refusée si
le poids ou un volume dépasse la capacité. Les piles d’eau laissées ailleurs
restent à leur position. `GET WATER` récupère d’abord une réserve au sol
accessible ; en son absence, il permet aussi de collecter à la berge.
Remplir ne désaltère pas : il faut ensuite `DRINK WATER`.

L’eau collectée est non traitée. Chaque consommation de cette réserve a une
chance sur huit de déclencher la giardiase, avec un hasard indépendant des
rencontres ; ses courbes et soins existants prennent ensuite le relais.
Le statut suit l’eau déposée ou récupérée et disparaît lorsque la réserve
correspondante est vide. Cette contamination
est une règle du port, pas encore comparée à l’original. Les seuils natifs
de déshydratation, faim et fatigue sont conservés ; le bandeau signale une
réserve transportée de 16 OZ ou moins avec `WATER LOW:INV`.

Une rencontre propose `SCARE/IGNORE` pour ours/couguar, `IGNORE/MOVE` pour
le crotale. Une réponse ratée laisse l’animal présent ; il est aussi possible
de quitter sa case pour s’éloigner.

- `SCARE` fait du bruit en 5 minutes, sans exiger d’outil : environ une chance
  sur deux de chasser ours/couguar. Le bruit ne chasse pas le crotale. Un échec
  peut provoquer coupures, fractures, choc ou morsure ; insister contre le crotale est risqué.
- `ATTACK` demande une hache ou un couteau accessible et prend 10 minutes.
  Hache et couteau partagent les mêmes chances, qui dépendent de l’espèce.
  Blessure et réussite sont
  deux tirages distincts : repousser l’animal n’évite pas nécessairement une blessure.
- `IGNORE` prend 5 minutes : l’animal peut partir, rester, blesser le joueur,
  ou, pour l’ours/couguar, voler la nourriture accessible avant de partir.
  Le couguar reste plus souvent que l’ours ; le crotale ne vole pas de nourriture.
- `HANG FOOD` protège les stocks suspendus. Le vol ne touche ni l’eau,
  ni l’équipement, ni les réserves au sol sur une autre case. Les animaux peuvent
  encore blesser le joueur dans un arbre ; la nourriture non suspendue reste
  exposée. La cabane protège le joueur et ses provisions. SCARE/ATTACK exigent
  de redescendre ou de sortir de la cabane.

Attente/repos/repas au sol utilisent un risque de blessure de 2 % pour
l’ours/couguar et 4 % pour le crotale ; IGNORE et la posture dans l’arbre
utilisent 4 % et 6 %. Ces seuils sont vérifiés dans l’original.

Sans décision, une réaction est évaluée après 60 minutes et interrompt l’action
avec un message. Les blessures utilisent les conditions et soins existants :
`STATUS M`, `STOP BLEEDING`, trousses de premiers secours ou de morsure.
La gravité ours/couguar suit la distribution originale ; les deux issues les
plus graves sont regroupées en choc. SPLINT reste à implémenter pour soigner
les fractures. Les seuils de bruit/blessure/combat et le risque de vol extérieur viennent
du moteur original, vérifiés par `tools/re_animal_reactions_probe.py`.
Le hasard discret, le départ après IGNORE (ours 50 %, couguar 25 %, crotale
75 %, après les risques), la cadence de 60 minutes, les protections et la
réussite ATTACK interprétée comme défense restent des adaptations du port.
La chasse et la récupération d’une carcasse ne sont pas implémentées.
Les filtres, taux, réglage NATURE et remplacements Sierra sont conservés.

L’arrivée ouvre un écran dédié : accueil des rangers, durée totale en
minutes, pas effectués, distance cumulée en cases, nombre de rencontres, santé et provisions finales,
puis score natif. Il reste affiché jusqu’à une touche explicite. La mort a
également son bilan. La distance compte une demi-case par pas de marche ou de
nage, affichée avec `.5` si nécessaire.

Le ciel violet, la terre verte, l’eau violette et la neige blanche sont les
couleurs explicitement définies dans `src/wild.s`.
Ce ne sont pas des zones mémoire corrompues ni un défaut POM2. La palette et
les couleurs des sprites originaux sont conservées ; l’Apple II HGR utilise
seulement des paires de pixels pour ce terrain.

## Documentation de développement

`make test-original` exécute les mêmes commandes dans le jeu original et
le port, sur des copies privées des disques locaux. Les cinq scénarios courts et
la marche native jusqu’à x70/y86 concordent, y compris vent, ressenti, charge
et hasard partagé. Aucune
aventure complète crash → rangers n'est encore validée. Les scénarios,
preuves et limites sont décrits dans [ADVENTURE_TESTS.md](docs/ADVENTURE_TESTS.md).

| Document | Usage |
|---|---|
| [CHANGELOG.md](CHANGELOG.md) | Historique des étapes présentes, sans version publiée |
| [TODO.md](TODO.md) | Ordre des prochains lots et critères de validation |
| [IMPLEMENTATION.md](docs/IMPLEMENTATION.md) | État du portage, règles provisoires, mémoire, carte, tests et outils |
| [ANALYSE.md](docs/ANALYSE.md) | Disques originaux, SMALLDOS, carte TOPO, rendu et format des sprites |
| [ENGINE.md](docs/logic/ENGINE.md) | Organisation du moteur original et accès aux analyses par sous-système |

La vue de terrain est comparée au bit près à une référence Python. Les
formules de survie établies sont calculées avec les flottants Applesoft de
la ROM ; les notes d'analyse précisent les preuves et les points incertains.

Les forêts reprennent les contours irréguliers de TMAKE et les deux profils
d’arbres Sierra de SURV3D. Leurs silhouettes suivent le terrain pendant les
rotations ; l’eau et les altitudes à partir de 11 000 pieds ne portent pas
d’arbres. MAP indique `T` pour les bois et `t` pour le maquis d’altitude ;
STATUS indique `WOODS` ou `SCRUB`. La couverture occupe 294 octets résidents,
sans lecture disque lors des rotations. Les anciennes cartes restent lisibles.
`CLIMB TREE` et `HANG FOOD` sont disponibles. INVENTORY propose une cinquième
catégorie `HUNG HERE` pour le sac suspendu et son contenu ; STATUS signale
la présence dans un arbre et le sac suspendu. Le contenu suspendu reste à sa
case, devient inaccessible et ne compte plus dans la charge portée. La gourde
reste disponible si elle est portée à la main. Les vols de nourriture par les
animaux restent à porter. Les preuves et les adaptations sont décrites dans
[trees.md](docs/logic/trees.md).
