# Maze 3D — suivi des améliorations

## Réalisé le 2026-10-03

- [x] Corriger le butin : conserver le type du monstre avant de le marquer
  mort, puis plafonner l'or à 99 pour l'affichage à deux chiffres.
- [x] Carte progressive : les murs et la sortie apparaissent après visite ;
  les monstres aperçus en vue 3D sont signalés sur la carte.
- [x] Trois étages, ennemis plus résistants, dragon obligatoire au dernier
  étage, numéro d'étage visible en 3D et sur la carte.
- [x] Boutique entre les étages : soins, attaque et défense payés en or.
- [x] Sons brefs avec `../dev/lib/apple2/sound.asm` : mur, attaque, coup reçu,
  montée de niveau, escalier, victoire et mort.
- [x] Optimiser le tracé : adresses et masques HGR conservés pendant les lignes
  obliques, effacement des 40 octets par ligne déroulé. Sur une vue testée,
  `render_3d` passe de 188 523 à 169 842 cycles (environ 10 % plus rapide),
  avec le même décor sur deux captures comparées.
- [x] Enrichir chaque labyrinthe : salle 2x2, trois boucles, trois caches et
  une relique obligatoire. Les 100 graines testées restent connexes.
- [x] Différencier les combats : garde, potion, fuite vers la case précédente,
  vol du gobelin, magie sans armure, coup annoncé de l'orc et du dragon.
- [x] Relier exploration et économie : or et potions dans les caches, achat de
  potions à la boutique.
- [x] Afficher la graine, calculer un score à la victoire et enregistrer le
  record avec sa graine dans `MAZESCORE` sur disquette DOS 3.3. La touche `R`
  de l'écran titre rejoue cette graine. Le narrateur occupe `MAZETEXT`, chargé
  depuis la disquette, ce qui libère environ 2 Ko de code.
- [x] Terminer une partie scriptée sur les trois étages sans modifier la
  mémoire du jeu : reliques prises, dragon battu, score 127 écrit sur disquette.

## À poursuivre

- [ ] Accélérer encore le rendu 3D. L'objectif initial de 2 à 3 fois plus
  rapide reste ouvert : la scène complète est toujours effacée et redessinée
  à chaque mouvement. Mesurer les coûts par routine avec `../dev/tools/a2shot`
  avant de choisir une autre stratégie. Comparer les captures avant/après.
- [ ] Permettre la saisie manuelle d'une graine, en plus de la rejouabilité de
  la graine du record.
- [ ] Ajouter la manette avec `../dev/lib/apple2/joy.asm`.
- [ ] Sauvegarder une partie en cours, si l'on souhaite reprendre une campagne
  interrompue. Le record est déjà conservé sur disquette.

Pour valider les changements de jeu, utiliser `../dev/tools/a2shot` : captures,
lecture mémoire et mesure en cycles ou en trames. `tests/check_generation.py`
vérifie les contraintes de génération sur 100 graines. La partie scriptée
doit pouvoir atteindre la boutique, battre le dragon, puis gagner ; les
sorties sans relique, et la dernière avant la mort du dragon, restent fermées.
