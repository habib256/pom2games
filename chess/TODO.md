# Chess — TODO

Améliorations proposées le 2026-09-15, par ordre conseillé. Chaque étape se
vérifie avec `../dev/tools/a2shot` (captures, `peek`, mesure en trames).

État mesuré au moment de la rédaction :

- **Temps de réflexion** (réponse à 1.e4, a2shot) : ~870 trames (~14,5 s) en
  mode STRONG (2 demi-coups), ~70 trames (~1 s) en mode FAST.
- **Nulles** : `game_status` ne détecte que le mat et le pat. `halfmove_clock`
  est tenu à jour et sauvegardé, mais jamais comparé à 100 : pas de règle des
  50 coups, ni de répétition, ni de matériel insuffisant. Seule la partie
  ordinateur contre ordinateur s'arrête à 200 coups.
- **Promotion** : le moteur accepte dame, tour, fou ou cavalier (`mv_promo`),
  mais `chess.s` passe toujours 0 et `maybe_promote` choisit la dame.
- **Annulation** : un seul coup (un seul jeu de tampons `user_*`).
- **Plateau** : toujours les blancs en bas, même en mode 3 (vous avec les noirs).
- **Liste des coups** : notation par cases (`E2E4`), et seuls les deux
  derniers coups sont réaffichés quand la colonne déborde.
- Pas de son, pas de manette, pas de sauvegarde.

## 1. Moteur

- [ ] **IA STRONG plus rapide** (objectif : moins de 5 s). Pistes : coupure
  alpha-bêta dans la recherche à 2 demi-coups (arrêter d'examiner les réponses
  adverses dès qu'elles rendent le coup pire que le meilleur déjà trouvé),
  essayer d'abord les captures (tri des coups). Vérifier que les coups joués
  sont identiques avant/après sur quelques positions.
- [ ] **Nulles** : règle des 50 coups (`halfmove_clock` ≥ 100), matériel
  insuffisant (roi contre roi, roi + fou ou cavalier contre roi), et si la place
  le permet répétition triple (historique de signatures de position). Message
  « DRAW » existant sur le panneau.

## 2. Interface

- [ ] **Choix de la promotion** : à l'arrivée d'un pion sur la dernière
  rangée, demander D / T / F / C sur le panneau et remplir `mv_promo`.
- [ ] **Plateau retourné** quand on joue les noirs (mode 3) : inverser
  `topsl_tab` / `bcol_tab`, les coordonnées et le déplacement du curseur.
- [ ] **Dernier coup mis en évidence** (cases de départ et d'arrivée),
  surtout utile pour voir ce que l'IA vient de jouer.
- [ ] **Indicateur de réflexion** pendant les ~14 s du mode STRONG (point qui
  avance sur le panneau), pour qu'on ne croie pas à un blocage.

## 3. Partie

- [ ] **Annulation sur plusieurs coups** : pile de coups annulables ; contre
  l'IA, U annule le coup de l'IA et le vôtre ensemble.
- [ ] **Historique complet et notation algébrique** (`Nf3`, `exd5`, `O-O`,
  `+`, `#`), avec défilement de la liste au lieu du réaffichage des deux
  derniers coups.
- [ ] **Sauvegarde sur la disquette** : partie en cours et/ou liste des coups
  dans un fichier texte DOS 3.3 ; reprise au démarrage.

## 4. Confort

- [ ] **Sons** : coup joué, prise, échec, fin de partie (`$C030`).
- [ ] **Manette** : manche = curseur, bouton 0 = choisir, bouton 1 = annuler
  la sélection.
