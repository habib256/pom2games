# MB TRACKER — plan de travail

Cible : Apple //e enhanced et //c 128 Ko, ProDOS 8, 80 colonnes, Mockingboard
(4c sur //c). Format : AYS v1 ([AYSONG_FORMAT.md](../dev/lib/apple2/AYSONG_FORMAT.md)),
celui que les jeux embarquent ; `dev/tools/audio/aysong.py` est l'oracle des
tests (encodeur et `Player` au registre près).

Les lots terminés sont dans [CHANGELOG.md](CHANGELOG.md).

## Ensuite

- [ ] Souris sur //c **avec** 4c : lire le matériel souris de l'IOU
  (`$C015`/`$C017`, `$C066`/`$C067`, bouton) sans le firmware masqué.
- [ ] Molette absente : défilement de la liste d'ordre par ses bords.
- [ ] AYS : décalage de hauteur par tic dans les instruments, volume de
  canal (récupérerait la plupart des pertes de l'import PT3).
- [ ] Pas d'avance réglable après saisie ; transposition d'une piste entière.
- [ ] Test sur vraies machines : //e enhanced + Mockingboard + AppleMouse,
  //c + 4c (son, interruptions pendant les accès disque, `/RAM` rendu en
  sortie, ALTZP des copies vers la LC auxiliaire).
