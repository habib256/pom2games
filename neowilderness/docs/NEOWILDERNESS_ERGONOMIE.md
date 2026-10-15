# Plan détaillé pour améliorer l’ergonomie de Neowilderness

Date : 11 octobre 2026. Statut : lots 1 à 5 implémentés ; parcours avec un nouveau joueur à réaliser.

Neowilderness doit permettre au joueur de découvrir les actions, corriger une saisie et comprendre les conséquences de ses décisions sans consulter constamment une documentation externe. Les premières priorités sont la sécurité des commandes et la qualité des messages, puis l’apprentissage, la lecture de l’état de survie et l’organisation des écrans.

Ce plan prend pour point de départ l’interface de Wilderness présente dans ce dépôt. Il est conservé ici comme feuille de route dédiée à Neowilderness, dont aucun répertoire distinct n’est présent au moment de la rédaction. Les comportements cibles des lots 1 à 5 sont implémentés ; leur validation avec un nouveau joueur reste à réaliser. Les constats proviennent du code et de la documentation ; leur impact sur les joueurs devra être vérifié par les parcours proposés ci-dessous.

## Périmètre et principes

- Conserver la saisie de commandes et l’atmosphère du jeu d’aventure sur Apple II.
- Rendre disponibles à l’écran les informations nécessaires à la prochaine décision.
- Permettre une annulation explicite avant engagement d’une action.
- Expliquer les refus avec une cause précise et une correction possible.
- Préserver les commandes existantes lorsque leur comportement ne présente pas de risque de sortie involontaire.
- Distinguer les améliorations d’interface des changements de simulation. Tout changement de durée ou d’interruption doit conserver une comptabilité explicite du temps et des ressources.
- Concevoir les écrans pour 40 colonnes et vérifier leur coût sur Apple II+ 48 Ko.

Les exemples de messages sont en anglais pour suivre l’interface actuelle. La traduction générale, les nouvelles règles de survie et le système de sauvegarde constituent des travaux séparés. Le plan doit rester utilisable avant leur réalisation.

## État de départ

| Élément actuel | Difficulté à traiter |
| --- | --- |
| Échap sur une ligne vide retourne à DOS | Une touche courante d’annulation peut faire perdre la partie |
| La saisie numérique ne traite pas Échap comme une annulation | Comportement différent selon l’invite |
| La flèche gauche recommence la saisie numérique | Corriger un chiffre impose de retaper la quantité |
| Les durées sont demandées en heures entières | Les petits déplacements sont difficiles à exprimer |
| HELP affiche trois lignes de commandes | Les manipulations d’équipement et les exemples sont peu découvrables |
| Certains refus sont génériques | Le joueur ne sait pas quelle partie de sa commande corriger |
| FOOD et WATER incluent les réserves accessibles au sol | La quantité disponible ici peut être confondue avec celle emportée |
| L’inventaire contient des indications de placement et une pagination | La consultation peut être mieux organisée et sa sortie explicitée |
| TOPO dispose déjà d’une légende, du cap numérique et du défilement | L’orientation peut être facilitée par un cap cardinal et un recentrage manuel |

## Lot 1 Sécuriser et simplifier les commandes

Priorité immédiate. Ce lot établit les conventions utilisées ensuite dans tous les écrans.

### Comportement des touches

| Contexte | Comportement cible d’Échap |
| --- | --- |
| Commande partiellement saisie | Effacer la saisie et rendre l’invite disponible |
| Invite vide | Rester dans le jeu sans avancer le temps |
| Quantité ou durée demandée | Annuler l’action et revenir à l’invite principale |
| Aide, état, inventaire ou carte | Revenir à la vue |
| Déplacement en cours | Demander un arrêt au prochain point sûr de simulation |

Ajouter une commande `QUIT` qui affiche une confirmation. Échap et une réponse négative reviennent au jeu. Une entrée vide ne confirme jamais la sortie. Tant qu’il n’existe pas de sauvegarde, préciser que la progression sera perdue.

Conserver les rotations par flèches gauche et droite sur une ligne vide. Documenter cette exception : avec du texte saisi, la flèche gauche sert à effacer. Lors d’une saisie numérique, elle doit effacer seulement le dernier chiffre.

### Quantités et durées

- Accepter les commandes actuelles avec question complémentaire.
- Ajouter progressivement les arguments directs : `WALK 10 MIN`, `REST 1 H`, puis `DRINK WATER 4 OZ`.
- Pour une durée sans unité dans l’invite historique, conserver les heures et afficher clairement cette unité.
- Refuser une unité inconnue, une valeur hors plage ou un dépassement numérique sans modifier l’état du jeu.
- Traiter une entrée vide ou zéro comme une annulation explicitement signalée ; ne pas réutiliser une ancienne valeur.
- Afficher une syntaxe courte dans l’invite, par exemple `DURATION? E.G. 10 MIN OR 1 H`.

Les durées courtes expriment une intention de voyage. Elles ne garantissent pas qu’un pas de terrain puisse être effectué en ce temps. La politique d’acceptation d’un pas et l’affichage de la durée effective doivent suivre les règles de simulation retenues et être documentés.

### Interruption des activités

Commencer par WALK et SWIM. Détecter la demande d’arrêt entre deux pas ; terminer un pas déjà engagé, puis rendre la main. Ne jamais laisser une position, une réserve ou un bilan thermique partiellement mis à jour. Afficher le temps réellement écoulé. Étendre ensuite le mécanisme au repos si sa granularité le permet.

### Validation

- Annuler à chaque type d’invite et vérifier position, horloge, objets et santé inchangés.
- Corriger successivement un, deux et trois chiffres.
- Vérifier les limites numériques et les unités mal saisies.
- Interrompre marche et nage ; comparer l’état obtenu à celui des mêmes pas achevés normalement.
- Vérifier que seule une confirmation explicite de QUIT retourne à DOS.

### Réalisation du lot 1

Le lot 1 est implémenté dans le moteur `wilderness/` qui sert actuellement
de base à Neowilderness. La saisie utilise [input.s](../src/input.s), chargé
comme module `WILDINP` dans la fenêtre de 2 Ko. Le parcours des mots a été
déplacé dans le vocabulaire et le texte d’aide dans le module des écrans pour
respecter les 48 Ko. Les rotations par flèches n’appellent pas ce module.

Échap annule la ligne ou la réponse numérique, et revient depuis les écrans,
y compris la première page d’inventaire. `QUIT` affiche la perte de progression
et exige `Y` ; Entrée, `N` et Échap annulent. Les commandes anciennes conservent
leurs questions ; les arguments directs acceptent `H`, `MIN` et `OZ`.
Les limites retenues sont 255 heures, 15 300 minutes et 255 onces. Une unité
absente conserve les heures ou les onces selon l’action. Les nombres négatifs,
décimaux, trop grands et les unités incompatibles sont refusés avant l’action.
Une réponse vide ou zéro annule, sauf le réglage `NATURE 0` à son invite.

Échap pendant WALK ou SWIM s’applique entre deux pas terminés. Le compte rendu
affiche la durée parcourue ; position, santé et ressources ne sont ni annulées
ni avancées d’un pas supplémentaire. Une marche de 10 minutes sur terrain
exigeant 19 minutes par pas reste sur place, sans dépense. La nage conserve
l’admission originale du dernier demi-pas. REST accepte les minutes ;
l’extension de l’interruption au repos reste une suite facultative.

La transition WALK → SWIM permet le demi-pas d'approche encore sur terre
uniquement si le demi-pas suivant entre dans l'eau. SWIM réalise aussi le
dernier demi-pas vers la rive et s'y arrête ; WALK poursuit sur terre.
Un nouveau SWIM reprend un trajet interrompu par sa durée. Les traversées
dans les quatre directions, en diagonale et depuis une position fractionnaire
sont couvertes par [test_shore.py](../tests/test_shore.py).

[test_input.py](../tests/test_input.py) vérifie les annulations sans changement
de position, heure, température, santé, fréquence des rencontres et stocks ;
les unités, limites, effacements de chiffres, retours des écrans et confirmation
de QUIT ; puis les interruptions réelles de marche et de nage après le premier
pas, en comparant l’état final au dernier état entièrement simulé.
La suite complète `make -C wilderness test` est passée, avec les contrôles
de non-régression du rendu, des rotations et des écritures différentielles TOPO.

## Lot 2 Rendre les messages utiles et persistants

Priorité immédiate, après les conventions du lot 1.

### Refus et corrections

| Situation | Réponse cible |
| --- | --- |
| Verbe inconnu | Signaler le verbe et proposer HELP |
| Objet manquant après un verbe | Demander l’objet avec un exemple de commande valide |
| Objet absent de la case et de l’équipement | Indiquer qu’il est inaccessible ici |
| Commande reconnue mais non implémentée | Indiquer son indisponibilité dans cette version |
| Transfert refusé pour le poids | Afficher le poids excédentaire et la capacité restante |
| Transfert refusé pour le volume | Afficher le volume excédentaire et la capacité restante |
| Poids et volume dépassés | Présenter les deux causes |
| Conteneur absent ou non vide | Distinguer « reprendre le conteneur » de « vider le conteneur » |

Les exemples de correction doivent correspondre à des commandes réellement disponibles. Ne pas suggérer une action de défense ou de fabrication encore absente.

### Retours d’action

- Avant consommation, afficher les quantités accessibles et l’unité OZ.
- Après consommation, annoncer la quantité réellement consommée, notamment si la demande dépasse le stock.
- Après transfert, annoncer l’objet et son nouvel emplacement.
- Après déplacement, présenter ensemble durée effective et cause d’arrêt : eau, rive, nuit, limite de carte, animal ou demande du joueur.
- Donner priorité aux messages de danger et d’arrêt sur une réponse générique de réussite.
- Garder le résultat lisible jusqu’à l’action suivante ; ne pas l’effacer immédiatement lors du retour à la vue.

### Validation

Construire une matrice de refus couvrant chaque cause. Vérifier l’absence de modification d’état après refus. Contrôler la longueur des textes dans la fenêtre réelle : les messages actuels disposent de trois lignes, avec 38 caractères sur la première et 37 sur les suivantes. Vérifier les noms d’objets longs et les valeurs maximales.

### Réalisation du lot 2

Les messages ne consomment plus une touche entre deux retours d'action.
Le résultat demeure affiché pendant la saisie suivante, après Échap ou une
ligne vide. Les déplacements réunissent durée effective et cause d'arrêt,
y compris le terrain impraticable, le manque de temps pour un pas et les
interruptions par animal. Le retour à la vue nocturne conserve ce bilan.
Mort, victoire et faiblesse gardent la priorité ; les bilans de déplacement
conservent aussi leur durée dans ces messages.

Le premier verbe inconnu est signalé (jusqu'à 12 caractères), avec HELP.
Un objet manquant reçoit des exemples valides ; un objet inaccessible reçoit
une indication distincte. Les consommations affichent le stock accessible,
comptent uniquement le sol de la case courante et annoncent la quantité réelle.
Les transferts utilisent le nom d'inventaire de l'objet et sa destination.

Les refus de charge annoncent poids, volume ou les deux, avec excédent et
capacité disponible après annulation. Les unités sont OZ pour le poids et
IN3 pour WEAR, PACK et HAND. Les dépassements arithmétiques sont signalés
séparément. Sac/gourde absents, conteneur non vide et tentative de ranger
le sac dans lui-même reçoivent chacun une correction disponible.

Les transferts sont déplacés dans WILDITM, un module de 2 Ko à `$5800`, pour
respecter les 48 Ko. Le texte est limité à trois lignes et réserve la dernière
colonne (37 caractères après l'indicateur ou l'indentation) pour éviter tout
défilement. [test_feedback.py](../tests/test_feedback.py) couvre les refus
atomiques, les chiffres exacts, les valeurs 65535, les noms longs, le stock,
la persistance et les interruptions par animal ou nuit.
La suite complète `make -C wilderness test` est passée, y compris TOPO,
rotations optimisées, transferts, simulation, thermique et traversées de rives.

### Cause d’arrêt nommée (Neowilderness, lot 7)

Une marche, une nage, un repos ou une attente interrompus par une rencontre
ou une découverte ne disent plus « A DISCOVERY INTERRUPTS YOUR ACTION. » :
le message nomme ce qui est arrivé, avec la durée effective comme avant.

| Cause | Message |
| --- | --- |
| Animal accepté sur la case du joueur pendant ce pas | `BEAR IN YOUR AREA!` (espèce de la région : `TIGER`, `ANACONDA`…) |
| Ressource trouvée par ce pas (bits de `MAP+36`) | `YOU FIND GAME ANIMALS.`, `FISH.`, `INSECTS.`, `FRUIT.`, `CACTI.`, `MUSHROOMS.`, `PLANTS.`, `NUTS.` |
| Abri naturel (aucun animal, aucune ressource) | `YOU FIND SHELTER.` |

Le texte est composé par `module_fauna_cause` (module PROJECT, appelé par le
talon résident `fauna_cause`) dans `m_fauna_stop`, sans tirage ni écriture
d’état de jeu ; l’ordre des tirages et la simulation sont inchangés.
L’original disait « A <ANIMAL> HAS ENTERED YOUR AREA! » (événement 32) : le
port garde une forme courte qui tient avec la durée sur les lignes de
message. [test_feedback.py](../tests/test_feedback.py) vérifie l’ours,
l’abri et le poisson, et l’absence de « DISCOVERY ».

## Lot 3 Faciliter les premières minutes

Priorité haute, après stabilisation des commandes et messages.

### Accueil et aide

Présenter au départ l’objectif de rejoindre les rangers et trois actions utiles : `INVENTORY`, `STATUS` et `TOPO`. L’accueil doit être court et pouvoir être fermé immédiatement. HELP permet de retrouver les mêmes indications.

Répartir l’aide en pages courtes :

1. Orientation et déplacement : boussole, rotations, LOOK, WALK, SWIM, TOPO et interruption.
2. Équipement : GET, TAKE, WEAR et DROP, avec la distinction sac, main, vêtements et sol.
3. Survie : EAT, DRINK, REST, STATUS et accès à la cabane.

Chaque page comprend des exemples complets et un pied de page indiquant comment avancer et revenir à la vue. Expliquer les conséquences peu évidentes, notamment le dépôt de tout le stock lorsque DROP s’applique aux provisions.

Ajouter au besoin une courte indication contextuelle au premier événement pertinent : rencontre de l’eau, présence sur la case de la cabane ou premier refus de charge. Limiter ces indications pour qu’elles ne masquent pas le résultat de l’action.

### Validation

Faire jouer une personne sans README : elle doit pouvoir consulter ses réserves, choisir un vêtement, ouvrir TOPO et commencer un déplacement. Relever les hésitations et les commandes erronées. Un objectif de première observation est d’accomplir ces étapes en cinq minutes ; ajuster ce seuil après les premiers essais sur la machine cible.

### Réalisation du lot 3

Le message de départ rappelle l’objectif des rangers et propose INVENTORY,
STATUS, TOPO et HELP. Il reste visible à la première invite, sans touche
supplémentaire ni temps simulé. HELP reprend ces indications dans sa première
page. Les trois pages séparent déplacement, équipement et survie, avec des
exemples complets et les emplacements PACK, HAND, WORN et GROUND HERE.
DROP CHEESE avertit du dépôt de tout le stock ; les objets déposés restent
sur leur case. Les touches 1/2/3 sélectionnent une page ; N/Espace et B
parcourent les pages dans les deux sens avec retour circulaire. Échap ou
Entrée revient à la vue. Les liens I/S/T restent disponibles.

Les indications contextuelles déjà présentes couvrent eau, cabane et charge.
Les textes restent dans le module WILDSCR de 2 Ko. `test_interface.py`
contrôle l’accueil, les trois pages, leurs exemples, la navigation et la
conservation de la simulation, des stocks et de la vue. Le parcours humain
sans README décrit ci-dessus reste à effectuer.

Validation du 12 octobre : construction et `test_interface.py` réussis.
Les 52 commandes de test ont été exécutées : 33 réussissent et 19 échouent.
Les 19 échecs sont également reproduits avec les sources précédentes (`HEAD`)
reconstruites séparément ; ils concernent les déplacements, la simulation
et les compteurs de chargement, et restent à corriger.

## Lot 4 Rendre la survie lisible pendant le jeu

Priorité haute. La mise en page doit être essayée en 40 colonnes avant d’ajouter du code résident.

### Résumé et alertes

Prévoir un résumé compact de l’heure, de la santé, de la faim, de la soif et de l’état thermique. Préserver l’espace nécessaire à la commande et aux messages ; si toutes les valeurs ne tiennent pas, privilégier les problèmes actifs et laisser les détails dans STATUS.

Déclencher une alerte lors d’une transition significative : apparition d’une condition, aggravation ou récupération. Ne pas répéter la même alerte à chaque pas. Employer des libellés compréhensibles en monochrome, sans dépendre d’une couleur.

Les seuils doivent dériver de la simulation existante. Une amélioration d’affichage ne doit pas introduire de nouveaux dégâts, de nouvelles conditions ou une estimation trompeuse du temps restant avant la mort.

### Organisation de STATUS

Afficher dans cet ordre :

1. Conditions actives et état global de santé.
2. Faim, soif, énergie et état thermique.
3. Réserves transportées et réserves accessibles au sol ici, séparément.
4. Heure et informations environnementales détaillées.

Conserver des unités explicites pour température, masse et volume. Vérifier la pagination dans le cas où plusieurs conditions, l’immersion et l’abri sont simultanément affichés.

### Validation

Parcourir des scénarios de faim, soif, épuisement, froid, chaleur et immersion. Vérifier qu’une transition produit une alerte lisible et que la consultation des écrans n’avance pas le temps. Comparer les stocks affichés avant et après avoir quitté une case contenant des provisions.

## Lot 5 Clarifier l’inventaire et l’orientation

Priorité suivante, en deux sous-lots indépendants.

### Inventaire

- Regrouper les objets par emplacement : portés, en main, dans le sac, au sol ici.
- Pour un aliment réparti entre sac et sol, afficher les deux quantités sans les confondre.
- Garder les capacités restantes visibles sur chaque page.
- Afficher un indicateur de page et les touches de navigation réellement prises en charge.
- Permettre un retour immédiat à la vue depuis n’importe quelle page.
- Rappeler les commandes de manipulation dans un emplacement stable.

Valider un inventaire vide, un inventaire rempli, plusieurs pages, des noms longs, des réserves réparties et des conteneurs déposés puis repris. Vérifier que chaque quantité n’est comptée qu’une fois.

### Carte et sites

- Ajouter une touche explicite pour recentrer TOPO sur le joueur après défilement.
- Associer au cap numérique un libellé cardinal ou intercardinal cohérent avec la boussole.
- Garder visibles la légende, le nord et la commande de retour.
- Rendre lisible la superposition joueur/site : la présence du joueur ne doit pas faire oublier qu’il se trouve sur la cabane, l’épave ou les rangers.
- À l’arrivée sur la case de la cabane, indiquer `ENTER SHELTER` ; à l’intérieur, rappeler `EXIT SHELTER` lorsque le joueur tente de partir.
- Signaler la présence d’objets récupérables sur la case sans multiplier les messages à chaque rotation.

Valider le défilement vers les limites, le recentrage, les huit directions principales, l’approche de la cabane et le retour sur des objets déposés. Les indications doivent rester cohérentes entre TOPO, la vue et les commandes.

## Réalisation des lots 4 et 5

Le résumé occupe les côtés du ruban de boussole sur seize lignes HGR ;
les quatre lignes de commande/résultat restent disponibles. À gauche la
santé, à droite l'heure (ou la période sans montre) suivie du jour du séjour
sont permanentes ; le bas du panneau droit montre le besoin le plus pressant,
faim ou soif (la faim à égalité), l'autre restant dans STATUS. Le champ sous
la santé privilégie une transition, le danger thermique, immersion/vêtements
mouillés, frissons ou sueur, puis l'abri ou les objets récupérables ici. Les
seuils sont repris de STATUS. Une classe inchangée ne répète pas l'alerte à chaque pas ; une
action longue conserve une seule alerte prioritaire jusqu'au compte rendu.
STATUS distingue CARRIED et HERE, avec les unités OZ, et place les conditions
avant besoins et environnement. Le cas simultané de toutes les conditions,
abri, immersion et frissons tient dans les 24 lignes sans pagination.

INVENTORY regroupe WORN, IN HAND, IN PACK et GROUND HERE, sélectionnables
par 1–4. Chaque groupe contient douze objets par page ; N/Espace/Entrée
avancent, B recule et Échap revient immédiatement. Les quatre capacités
restantes, les unités et les commandes de manipulation restent visibles.
Les réserves réparties ont une quantité distincte dans sac et sol.
TOPO ajoute C pour recentrer et un libellé cardinal magnétique cohérent avec
le ruban ; une ligne nomme le site masqué par P et rappelle ENTER/EXIT SHELTER.
Le bandeau signale les objets récupérables sans message répété à chaque rotation.

`test_interface.py` contrôle les glyphes du résumé, alertes et récupérations,
absence de répétition et de mutation de simulation, groupes vides et deux
pages, quantités réparties, capacités, sortie, STATUS maximal, les huit caps
avec déclinaisons ±17°, recentrage et superposition joueur/site. Les scénarios
existants couvrent conteneurs déposés/repris, voyages vers la cabane, repos,
sortie, masquage et écritures différentielles TOPO. Les coûts mémoire et
lectures DOS sont consignés dans [IMPLEMENTATION.md](IMPLEMENTATION.md).
La suite complète `make -C wilderness test` est passée après le cadre du
compas, avec rendu, rotations, simulation et météo. Les flèches n'ajoutent
pas de lecture du résumé. L'accueil/aide du lot 3 et
l'observation du parcours par un nouveau joueur restent à réaliser.

### Interface DHGR (lot 4 de Neowilderness)

Le résumé de survie garde ses quatre champs et ses règles d'alerte ; il est
dessiné en DHGR couleur (police de 7 rangées) : un avertissement, autrefois
en inverse, est écrit en blanc sur une bande rouge ; une reprise en aqua ;
une indication en bleu clair. Les libellés restent lisibles sans couleur
(mêmes mots). Les quatre lignes de commande et de résultat sont en texte
80 colonnes : une ligne accepte désormais 79 caractères (les messages
existants gardent leur mise en page de 38 colonnes, les messages plus longs
de ce plan peuvent s'y étendre). Les écrans d'aide, d'état et d'inventaire
restent en 40 colonnes ; MAP est en 80 colonnes. Comme avant, le retour
d'un écran rend des lignes de commande vides ; il ne redessine plus la vue.

## Contraintes de réalisation

### Mémoire et chargements

Mesurer les segments dans `build/wild.map` avant chaque ajout résident. Le moteur utilise déjà des modules disque pour certains écrans et règles ; privilégier cette organisation pour les pages d’aide et les textes volumineux. Garder résident uniquement l’état nécessaire aux commandes, interruptions et alertes.

Mesurer les cycles et lectures disque sur la configuration Apple II cible, en distinguant premier accès et accès répété. Toute nouvelle lecture pendant une saisie ou chaque pas de marche doit être justifiée et comparée au comportement de départ.

### Compatibilité et règles

Les commandes historiques doivent rester reconnues. Les extensions de syntaxe ne doivent pas changer silencieusement la signification d’une commande existante. Les nouvelles entrées de courte durée et les interruptions demandent des tests de simulation, en particulier sur les demi-cases de nage, les rencontres et les arrêts naturels.

Documenter les écarts voulus de Neowilderness dans cette feuille de route et dans sa future documentation d’utilisation. Les objectifs de fidélité du port Wilderness restent décrits dans son TODO et ses documents de comparaison à l’original.

## Ordre de livraison

| Étape | Contenu | Condition de fin |
| --- | --- | --- |
| A | Annulation, correction numérique et QUIT | Aucun retour involontaire à DOS ; annulations sans effet sur la simulation |
| B | Durées courtes et interruption du déplacement | Temps effectif et état après arrêt cohérents |
| C | Refus précis et retours d’action | Chaque refus indique une correction ; les causes d’arrêt restent lisibles |
| D | Accueil et aide paginée | Premier parcours réalisable sans documentation externe |
| E | Résumé, alertes et STATUS | Besoins et réserves transportées identifiables sans ambiguïté |
| F | Inventaire, recentrage et indications de site | Préparation, orientation et récupération d’objets compréhensibles |

Pour chaque étape : préciser le comportement, réaliser une maquette textuelle si nécessaire, implémenter, exécuter les tests du sous-système puis les vérifications requises par le projet, et rejouer le parcours manuel concerné. Aucun lot n’est terminé sur la seule présence des nouveaux textes.

## Parcours de validation global

Utiliser une carte et un état initial reproductibles. Garder séparés les tests techniques déterministes et l’observation d’un nouveau joueur.

1. Démarrer et comprendre l’objectif depuis l’accueil.
2. Consulter l’aide, l’état et les objets disponibles.
3. Provoquer un refus de charge, comprendre sa cause et corriger l’équipement.
4. Saisir une quantité incorrecte, la corriger puis annuler sans effet.
5. Consommer une quantité connue et vérifier les réserves restantes.
6. Choisir un cap, demander un déplacement court et interrompre une marche plus longue.
7. Atteindre l’eau et comprendre la raison de l’arrêt ; vérifier la nage sur un scénario adapté.
8. Ouvrir TOPO, défiler, se recentrer et revenir à la vue.
9. Atteindre la cabane, entrer, consulter son état, se reposer et ressortir.
10. Déposer puis retrouver un objet, en vérifiant sa présence au sol et son accessibilité.
11. Observer une dégradation de survie et identifier l’information qui appelle une action.
12. Annuler QUIT, puis confirmer une sortie lors d’un essai dédié.

Relever le nombre de commandes rejetées, les recours au README, les hésitations, les sorties involontaires et les délais perceptibles. Comparer avant et après sur la même configuration. Le succès recherché est un parcours plus compréhensible, avec des résultats de simulation cohérents et sans régression de réactivité inexpliquée.

## Suivi des travaux

- [x] Lot 1 : annulation, sortie explicite, saisie et interruption marche/nage.
- [x] Lot 2 : refus précis, quantités et comptes rendus d’action.
- [ ] Lot 3 : accueil, aide et indications contextuelles.
- [x] Lot 4 : résumé de survie, alertes et organisation de STATUS.
- [x] Lot 5 : inventaire et orientation.
- [ ] Parcours global validé et coûts mémoire/disque consignés.

## Références dans le dépôt

- [Commandes et comportement actuel](../README.md).
- [Priorités et contraintes du port Wilderness](../TODO.md).
- [Saisie, simulation et écrans](../src/game.s).
- [Messages actuels](../src/messages.inc).
- [Carte et cabane](../src/sites.s).
- [Architecture et limites du port](IMPLEMENTATION.md).
- [Comparaisons d’aventures avec l’original](ADVENTURE_TESTS.md).
