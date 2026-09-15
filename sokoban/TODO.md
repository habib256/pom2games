# Sokoban — TODO

Améliorations proposées le 2026-09-15, par ordre conseillé. Chaque étape se
vérifie avec `../dev/tools/a2shot` (captures, `peek`, `joy`/`btn` pour la
manette).

État au moment de la rédaction (`src/sokoban.s`) : annulation d'un seul coup
(`prev_player_row`, `undo_avail`) ; compteur de coups sur 8 bits plafonné à 255,
poussées non comptées ; aucune sauvegarde (chaque démarrage reprend au
niveau 1) ; niveaux parcourus seulement avec N/P ; après le 72ᵉ niveau, retour
au niveau 1 sans écran de fin ; pas de sortie vers DOS ; un clic par pas et une
routine `beep` ; binaire chargé à `$4000`, sur la page HGR2.

## 1. Gameplay

- [ ] **Annulation sur plusieurs coups** : une pile d'un octet par coup
  (direction + drapeau « a poussé une caisse »), jusqu'à 255 coups pour
  256 octets de BSS. U / bouton 0 remonte la pile ; recommencer (R) la vide.
- [ ] **Compteurs complets** : coups sur 16 bits, et compteur de poussées
  affiché dans le HUD. Les deux doivent reculer avec l'annulation.

## 2. Base technique

- [ ] **Passer Sokoban sur `../dev`**, comme les autres jeux : binaire à
  `$6000` (config `dev/cc65/apple2_hgr.cfg` ou dérivée) pour libérer HGR2,
  zéro-page en `$50+`, et `apple2.inc`, `kbd.asm`, `hgr.asm`, `exit.asm` à
  la place des équivalents locaux. Garder la lecture de la manette.
- [ ] **Quitter vers DOS depuis le menu**, via `apple2_zp_save` /
  `apple2_exit` (page zéro restaurée, Ctrl-RESET protégé).
- [ ] **Double tampon HGR1/HGR2** pour les changements d'écran (niveau, titre,
  aide, succès), comme Maze3D. Le rendu par tuiles modifiées pendant le jeu
  peut rester sur la page affichée.

## 3. Progression

- [ ] **Choix direct du niveau** : écran de sélection (grille des 72 niveaux,
  manche ou flèches) ou saisie du numéro, au lieu de N/P un par un.
- [ ] **Sauvegarde sur la disquette** : niveaux résolus et meilleur score par
  niveau (coups, poussées) dans un petit fichier DOS 3.3. Au démarrage,
  reprendre au premier niveau non résolu ; marquer les niveaux terminés dans
  l'écran de sélection. Attention aux accès disque depuis un programme en
  HGR (RWTS et page zéro de DOS).
- [ ] **Écran de fin** après le 72ᵉ niveau, avec les totaux, au lieu du
  retour silencieux au niveau 1.

## 4. Sons

- [ ] **Sons plus parlants** avec la routine `beep` existante : caisse posée
  sur une cible, niveau réussi, annulation, déplacement impossible.
