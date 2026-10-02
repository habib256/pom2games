# Maze 3D — TODO

Améliorations proposées le 2026-09-15, par ordre conseillé. Chaque étape se
vérifie avec `../dev/tools/a2shot` (captures, `peek`, mesure en trames), comme
le double tampon HGR1/HGR2.

État mesuré au moment de la rédaction : une image 3D apparaît ~17 trames
(~0,3 s) après une touche, la carte ~14 trames ; aucun son ; le type « dragon »
est déclaré mais jamais créé ; l'or n'a aucun usage ; la carte montre tout le
labyrinthe.

Son, manette et sauvegarde : partir des modules communs sortis de MICRO-SOKOBAN,
`../dev/lib/apple2/sound.asm` (`tone`), `joy.asm` (`read_stick`,
`stick_dir`) et `dos.asm` (`dos_cmd_*`, `disk_protected`), plutôt que
d'écrire une nouvelle version.

## 1. Vitesse + son

- [ ] **Dessin 3D plus rapide** (objectif : 2 à 3 fois).
  Les murs passent par `line_xy`, qui trace point par point via `plot_set` /
  `calc_pix_addr` (adresse de ligne recalculée à chaque point). Pistes :
  segments horizontaux et verticaux en octets entiers, diagonales avec
  pointeur de ligne incrémental. Aucun changement visible attendu :
  comparer les captures avant/après, mesurer le délai en trames.
- [ ] **Son sur le haut-parleur (`$C030`)** : « bonk » contre un mur, coup
  porté / reçu, fanfare de montée de niveau et de sortie, glas à la mort.
  Une petite routine de bip (durée, période) dans `dev/lib/apple2` servirait
  aussi aux autres jeux.

## 2. Durée de vie

- [ ] **Carte qui se découvre** : n'afficher que les cases visitées (marque
  dans le bit libre de chaque case de `grid`) et les monstres déjà aperçus.
  Aujourd'hui M révèle monstres et sortie.
- [ ] **Plusieurs étages** : la sortie `E` mène à l'étage suivant, monstres
  plus forts à chaque étage, HUD avec le numéro d'étage.
- [ ] **Le dragon en boss du dernier étage** : `mob_type` 3 est prévu
  (commentaire de `mob_type`) mais `place_mobs` n'attribue que 0, 1, 2. Il
  faut un sprite, des PV/dégâts, un nom et une couleur.

## 3. Au choix

- [ ] **Donner un usage à l'or** (`p_gold`, affiché mais inutile) :
  fontaine qui soigne contre de l'or, ou marchand entre deux étages
  (ATK, DEF, PV).
- [ ] **Labyrinthes variés** : la graine ne dépend que de la touche pressée
  sur l'écran titre. Mélanger aussi la durée d'attente, en gardant un moyen
  d'obtenir une graine fixe pour que les tests a2shot restent
  reproductibles.
- [ ] **Manette** (comme Sokoban) : manche = avancer / reculer / tourner,
  bouton 0 = attaquer, bouton 1 = carte.
- [ ] **Sauvegarde sur disquette et meilleur score** : partie en cours ou
  tableau des scores dans un petit fichier DOS 3.3 sur le disque du jeu.
