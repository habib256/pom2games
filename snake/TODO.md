# Snake — TODO

Améliorations proposées le 2026-09-15, par ordre conseillé. Chaque étape se
vérifie avec `../dev/tools/a2shot` (captures, `peek`, mesure en trames).

État mesuré au moment de la rédaction (`src/snake.c`) :

- **Clavier** : `read_input` lit le clavier une seule fois par tick (~0,33 s
  au départ). Le verrou `$C000` ne garde qu'une touche : deux virages rapides
  dans le même tick, seul le dernier compte.
- **Aléatoire** : `rng_state` part toujours de `0xACE1` et n'est jamais
  mélangé ; la première partie après le démarrage est donc toujours la même
  (mêmes pommes, même bonus).
- **Vitesse** : boucle d'attente active (`throttle`) calibrée pour 1 MHz ;
  ~0,33 s par case au départ, −200 itérations par pomme jusqu'à 400. Le jeu va
  plus vite sur une carte accélératrice.
- **Longueur** : `MAXLEN` = 96 ; au-delà le serpent cesse de grandir sans rien
  signaler.
- Pas de pause, pas de retour à DOS, pas de son, pas de manette, pas de
  meilleur score ; seuls les murs du haut et du bas existent.
- Le runtime C HGR n'est plus une copie propre à Snake : le jeu utilise
  `../dev/lib/hgrc`, `../dev/lib/gfx` et `../dev/lib/apple2c`, comme les démos.

Son, manette et sauvegarde : partir des modules communs sortis de Sokoban,
`../dev/lib/apple2/sound.asm` (`tone`), `joy.asm` (`read_stick`,
`stick_dir`) et `dos.asm` (`dos_cmd_*`, `disk_protected`) ; en C :
`apple2game.h` et `apple2dos.h` dans `../dev/lib/apple2c`, plutôt que
d'écrire une nouvelle version.

## 1. Jouabilité

- [ ] **File de directions** : lire le clavier aussi pendant `throttle` et
  garder jusqu'à 2 virages en attente (appliqués un par tick, en refusant le
  demi-tour), pour que les virages rapides ne soient plus perdus.
- [ ] **Graine aléatoire** : mélanger à `rng_state` le nombre de tours de la
  boucle d'attente du titre et la touche pressée. Garder un moyen d'obtenir une
  graine fixe pour les tests a2shot.
- [ ] **Longueur maximale** : augmenter `MAXLEN` (le terrain jouable fait
  33 × 20 cases) ou déclarer la victoire quand il est atteint.

## 2. Confort

- [ ] **Pause** (P ou ESC) et **retour à DOS** depuis la pause (`a2_dos()`,
  qui restaure la page zéro via `crt0_apple2.s`).
- [ ] **Sons** : pomme, bonus, accélération, mort (`$C030`).
- [ ] **Manette** : manche = direction.
- [ ] **Choix de la vitesse de départ** sur l'écran titre.

## 3. Durée de vie

- [ ] **Meilleur score** affiché dans le HUD et sauvegardé sur la disquette
  (petit fichier DOS 3.3).
- [ ] **Niveaux avec obstacles** : murs intérieurs différents tous les N
  pommes, collisions via une grille de cases occupées.

## 4. Technique

- [x] **Déplacer le runtime C HGR dans `../dev/lib`** : fait, `../dev/lib/hgrc`
  (partagé avec les démos C de `../demos`).
