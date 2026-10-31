# MB TRACKER — plan de travail

Cible : Apple //e enhanced et //c 128 Ko, ProDOS 8, 80 colonnes, Mockingboard
(4c sur //c). Format : AYS v1 ([AYSONG_FORMAT.md](../dev/lib/apple2/AYSONG_FORMAT.md)),
celui que les jeux embarquent ; `dev/tools/audio/aysong.py` est l'oracle des
tests (encodeur et `Player` au registre près).

## Lot 1 — l'éditeur (fait, 2026-10-31)

- [x] Grille de motif : 3 voix affichées (grille prévue pour 6, colonnes 4-6
  en allant à droite pour un fichier à 6 voix), 64 lignes, note /
  instrument / effet + paramètre, piano deux rangées, octave, note coupée,
  effacement, insertion / suppression de ligne, vitesse, lignes.
- [x] Liste d'ordre : entrées, numéro de motif, nouveau motif / copie,
  insertion / suppression, boucle ou arrêt en fin.
- [x] Éditeur d'instrument : tics (volume, ton, bruit, enveloppe, période de
  bruit), boucle, forme et période d'enveloppe, nom, écoute.
- [x] Lecture : `mb_irq` 50 Hz + `ays_tick`, morceau / boucle de motif,
  suivi du curseur, muets, réencodage pendant la lecture ; sans carte :
  message, édition et fichiers seuls.
- [x] Fichiers `.AYS` : catalogue, nom tapé, sauvegarde, `DEMO.AYS` livré ;
  tests sur //e, //c et sans carte.

## Lot M1 — souris (fait, 2026-10-31)

- [x] Pointeur (cellule inversée, le texte se dessine dessous), clics dans
  la grille (champ), les numéros de ligne (pages), la liste d'ordre, les
  instruments (deux clics : l'éditeur), les noms de voix (muet), la barre
  du bas, l'éditeur d'instrument, la liste des fichiers ; glisser = bloc.
- [x] Mockingboard détectée **avant** la souris. Sur //c, la 4c réveillée
  masque le firmware souris (POM2 et la vraie carte) : clavier seul avec
  une 4c ; souris du //c sans carte.
- [x] Mémoire : recouvrements OVL1 (éditeur d'instrument) et OVL2 (fichiers
  + décodeur), gardés dans la LC auxiliaire ; noms de fichiers dans le
  motif de travail ; aide paginée (en-tête d'offsets).
- [x] a2shot `--mouse-slot=N` (carte souris hors du slot 4 de la Mockingboard).

## Lot M2 — blocs (fait)

- [x] `^B` marquer, `^C` `^X` `^V` (entre motifs, presse-papiers en aux),
  `;` `'` `:` `"` transposer, `^Z` annuler / refaire (cellule ou motif).
- [x] Liste d'ordre : `I` insérer un nouveau motif, `C` cloner, `D`
  supprimer un motif (renumérotation).

## Lot M3 — 6 voix (fait)

- [x] Lecteur `AYSONG_VOICES=6`, `MB_IRQ_HUSH_BOTH=1` (et la correction de
  `mb_hush` dans ce mode : un `beq :++` qui visait la mauvaise étiquette) ;
  tic ≤ 5 309 cycles.
- [x] `^N` : 3 ou 6 voix ; grille de 6 colonnes de 8 caractères.

## Lot M4 — import PT3 (fait)

- [x] `dev/tools/audio/pt3play.py` (= `pt3/` sous a2run, registre pour
  registre), `pt3import.py` (rapport de ce qui se perd), `aysong.py
  --import-pt3`, `--to-50hz` ; `WG.AYS` sur la disquette.

## Ensuite

- [ ] Souris sur //c **avec** 4c : lire le matériel souris de l'IOU
  (`$C015`/`$C017`, `$C066`/`$C067`, bouton) sans le firmware masqué.
- [ ] Molette absente : défilement de la liste d'ordre par ses bords.
- [ ] Changer le nombre de voix d'un morceau existant (3 → 6).
- [ ] AYS : décalage de hauteur par tic dans les instruments, volume de
  canal (récupérerait la plupart des pertes de l'import PT3).
- [ ] Pas d'avance réglable après saisie ; transposition d'une piste entière.
- [ ] Test sur vraies machines : //e enhanced + Mockingboard + AppleMouse,
  //c + 4c (son, interruptions pendant les accès disque, `/RAM` rendu en
  sortie, ALTZP des copies vers la LC auxiliaire).
