# ARKABREAKOUT — plan et suivi

Objectif : casse-briques nerveux inspiré des mécaniques d'Arkanoid, adapté à
l'Apple II+ 48 Ko, HGR 280 × 192 et 6502 à 1 MHz. Disquette DOS 3.3 autonome.

## 1. Première version complète

- [x] 12 tableaux originaux, trois vies, score et difficulté progressive.
- [x] Briques normales, résistantes et indestructibles.
- [x] Rebond dirigé selon le point d'impact sur la raquette.
- [x] Vitesse progressive avec plafond, accélération toutes les 12 briques détruites.
- [x] Une vie bonus tous les 1 000 points, réserve plafonnée à cinq vies.
- [x] Record de session conservé lors des reprises.
- [x] Capsules : raquette élargie, ralentissement et raquette collante.
- [x] Titre, pause, défaite, reprise et victoire.
- [x] Terminer les 12 tableaux avec un pilote déterministe, sans modifier la progression.
- [ ] Équilibrer durée, difficulté et capsules par des campagnes jouées manuellement.

## 2. Affichage HGR lisible

- [x] HGR plein écran, bandeau supérieur : score, vies et niveau.
- [x] Grille de 12 colonnes × 8 rangées ; pas horizontal de 21 pixels.
- [x] Briques colorées, balle et raquette blanches ; petit texte blanc.
- [x] Deux pages HGR, restauration des objets et mises à jour différées des briques.
- [x] Capsules W/S/C blanches, précalculées pour les sept alignements.
- [x] Titre ×2, bord lumineux des briques, encoches de résistance et métal hachuré.
- [x] Bandeau explicite READY/PAUSE et indications adaptées au paddle.
- [ ] Contrôler les couleurs et franges sur un écran composite réel.

## 3. Moteur 6502

- [x] Assembleur ca65, réutilisation des bibliothèques communes.
- [x] Positions avec fraction horizontale, sans flottants.
- [x] Inclinaison du rebond selon la zone de contact avec la raquette.
- [x] Petits pas, collisions sur la grille et résolution séparée des axes.
- [x] Sons courts et coût borné pendant le jeu.
- [x] Cadence initiale mesurée : environ 32 mises à jour/s au clavier au repos.
- [x] Comparer les modes en jeu : environ 29 mises à jour/s au clavier et au paddle.
- [x] Compenser le coût des temporisateurs du paddle par une attente plus courte.
- [ ] Mesurer précisément les pires trames et optimiser leurs mises à jour du bandeau.
- [x] Huit zones symétriques, adaptées aux deux largeurs, jusqu'à environ 68°.
- [x] Fractions sur les deux axes pour une vitesse comparable entre les trajectoires.

## 4. Commandes

- [x] Paddle proportionnel ; bouton pour lancer.
- [x] A/D et flèches ; mouvement continu et S pour arrêter sur II+.
- [x] Espace pour lancer, P pour pause, Échap pour quitter.
- [x] Sensibilité clavier réglable pendant le jeu avec + et -.
- [x] Calibration facultative des deux extrémités du paddle au titre.
- [ ] Ajouter un réglage de sensibilité du paddle indépendant de la calibration.
- [ ] Tester le confort sur un paddle et un clavier Apple II+ physiques.

## 5. Étapes jouables

- [x] Prototype : balle, raquette, tableau, rebonds et perte de vie.
- [x] Moteur : collisions, dessin, cadence et commandes paddle.
- [x] Jeu complet : tableaux, score, capsules, sons et progression.
- [x] Première finition : écrans, instructions et disquette amorçable.
- [ ] Finition après retours de jeu : équilibrage et présentation.

## 6. Intégration et validation

- [x] Dossier arkabreakout/ : sources, niveaux, Makefile, README et TODO.
- [x] dist/ARKABREAKOUT.dsk intégrée à la construction générale.
- [x] Compatibilité mémoire II+ 48 Ko : deux pages HGR, DOS conservé.
- [x] Tests du binaire sur le 6502 NMOS de a2run.
- [x] Vérifier murs, plafond, vitesse maximale, briques résistantes et métal.
- [x] Vérifier capsules, tableaux, défaite/reprise, victoire, pause et sortie DOS.
- [x] Vérifier les deux pages figées, le paddle et sa calibration.
- [x] Vérifier l'effacement des trois capsules sur leurs sept alignements HGR.
- [x] Examiner les captures du titre et du terrain avec le cœur de POM2.
- [x] Passer la suite complète make test du dépôt sur les disquettes reconstruites.
- [x] Premier retour utilisateur : le jeu fonctionne.
- [ ] Essais interactifs prolongés dans POM2 et sur un Apple II+ réel.
- [x] Tester les contacts diagonaux avec les briques et les deux murs simultanément.
- [x] Tester le centrage de la raquette lors des changements de largeur.
- [x] Tester la campagne complète jusqu'à la victoire avec le véritable binaire 6502.

## Extensions après stabilisation

- [ ] Multiballe, après mesure du budget CPU et mémoire.
- [ ] Lasers et briques associées.
- [ ] Record sauvegardé sur disque, avec gestion des disquettes protégées.
- [ ] Éditeur ou outil de validation des niveaux.
