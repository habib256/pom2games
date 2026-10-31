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

## Lot 2 — souris

- [ ] Clic dans la grille (cellule, champ), la liste d'ordre et les
  instruments ; molette absente : glisser pour défiler.
- [ ] Détecter la Mockingboard **avant** l'initialisation de la souris (le
  réveil de la 4c en `$C403` peut masquer la ROM souris du //c en slot 4).
- [ ] Mémoire : ~1,5 Ko libres ; prévoir un overlay (éditeur d'instrument,
  fichiers) en mémoire auxiliaire comme ROBOT SPACE STATION.

## Lot 3 — import PT3

- [ ] `dev/tools/audio` : PT3 → AYS (motifs, ornements → arpèges, samples →
  instruments), avec la liste de ce qui se perd ; test sur la musique de
  WARGALAGA II.
- [ ] Lire l'AYS produit dans le tracker (limites : 64 motifs, 64 tics).

## Lot 4 — 6 voix

- [ ] Interface à 6 colonnes (80 colonnes : 6 × 10 + numéros = 63), choix 3
  / 6 voix pour un nouveau morceau.
- [ ] Lecteur `AYSONG_VOICES=6` (deux puces), `MB_IRQ_HUSH_BOTH=1`.

## Ensuite

- [ ] Blocs : sélection, copier / coller / effacer, dans une voix ou toutes.
- [ ] Transposition (bloc, motif, piste) ; pas d'avance réglable après saisie.
- [ ] Annuler la dernière modification.
- [ ] Test sur vraies machines : //e enhanced + Mockingboard, //c + 4c
  (son, interruptions pendant les accès disque, `/RAM` rendu en sortie).
