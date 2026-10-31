# MB TRACKER

Un tracker natif pour la **Mockingboard**, sur Apple //e enhanced ou //c
128 Ko (ProDOS 8, 80 colonnes). Il écrit et joue directement des fichiers
**AYS v1**, le format compact que les jeux du dépôt embarquent
([AYSONG_FORMAT.md](../dev/lib/apple2/AYSONG_FORMAT.md)) : ce qu'on entend
dans l'éditeur est ce que `aysong.asm` jouera dans le jeu, au registre près.
Il remplace MCS (éditeur façon *Music Construction Set* au haut-parleur).

<table><tr>
<td><img src="screenshots/editor.png" width="380" alt="La démo en lecture : grille, liste d'ordre, instruments"></td>
<td><img src="screenshots/instrument.png" width="380" alt="L'éditeur d'instrument"></td>
</tr></table>

**Lot 1 (2026-10-31)** : grille de motif (3 voix affichées, grille prévue
pour 6), liste d'ordre, éditeur d'instrument, lecture sous interruption à
50 Hz qui suit le curseur, muets par voix, chargement / sauvegarde de
fichiers `.AYS`, aide. Sans carte : « NO MOCKINGBOARD », l'édition et les
fichiers restent possibles.

## Écrans et touches

Le haut de l'écran : le nom du morceau et la carte (`MOCKINGBOARD S4`),
puis le fichier, le motif, les lignes, la vitesse, l'octave, l'instrument
courant, l'état (STOP / PLAY / LOOP, FOLLOW). Au centre la grille ; à droite
la liste d'ordre (`L` = point de bouclage, `*` = entrée jouée) et les 15
instruments. Ligne 22 : les messages ; ligne 23 : les touches principales.
`?` affiche toutes les touches.

Une cellule : `C-4 1 A47` = note, instrument (1-F), effet et paramètre
(hex). `---` vide (la note continue), `===` note coupée.

| Touches (grille) | |
|---|---|
| flèches, `[` `]` | se déplacer (note, instrument, effet, paramètre ×2), 16 lignes |
| `Z S X D C V G B H N J M ,` | piano, octave courante (`,` = do suivant) |
| `Q 2 W 3 E R 5 T 6 Y 7 U I` | piano, octave + 1 |
| `1` | note coupée ; `Delete` ou `.` : efface le champ |
| `-` `=` | octave ; `<` `>` : instrument des notes saisies (écrit avec chaque note) |
| `0`-`F` | instrument, paramètre ; `O A U D F S N E` : effet (arrêt, arpège, glissés, fondu, crescendo, bruit, période d'enveloppe) |
| `^O` `^Y` | insérer / supprimer une ligne (toutes les voix) |
| `_` `+`, `{` `}` | vitesse (tics par ligne), lignes des motifs (1-64) |
| `^P`, `^R`, espace / `Esc` | jouer depuis l'entrée d'ordre courante, boucler le motif, arrêter |
| `^F` | suivre la lecture ; `! @ #` (`$ % ^`) : muet voix 1-3 (4-6) |
| `Tab` | liste d'ordre : `↑ ↓` entrée, `- =` / `← →` numéro de motif (au-delà du dernier : nouveau motif), `N` / `C` motif vide / copie, `^O` `^Y` insérer / supprimer, `L` boucle (à nouveau : arrêt en fin) |
| `^E` | éditeur d'instrument |
| `^T` `^A` | nom du morceau, auteur |
| `^L` `^S` `^N` `^Q` | charger, sauver, nouveau, quitter vers ProDOS |

L'éditeur d'instrument (`^E`) : une ligne par tic (volume 0-F, ton, bruit,
enveloppe matérielle, période de bruit), le point de boucle (`L` ; sur le
dernier tic : tenue), la forme et la période d'enveloppe (ligne du haut),
`^O` / `^Y` dupliquer / supprimer un tic, `<` `>` instrument précédent /
suivant (au-delà : un nouveau), `Retour` fait entendre le do de l'octave,
`^T` le nom. Chaque note saisie dans la grille est aussi jouée seule.

Pendant la lecture, une modification réencode le morceau et la lecture
reprend à la ligne où elle en était (les voix se taisent jusqu'à leur
note suivante).

## Fichiers

`^S` demande un nom (`.AYS` ajouté s'il manque) et écrit un fichier BIN sur
le volume de démarrage ; `^L` liste les `.AYS` du volume (`/` : taper un
nom). La disquette porte `DEMO.AYS`, la démo de
[`dev/tools/audio/aysong.py`](../dev/tools/audio/aysong.py) (`--demo`),
générée au build. Les fichiers se relisent avec `aysong.py` (`decode`,
`--json`, `--frames`) et s'embarquent dans un jeu avec `--asm` ou tels
quels (`ays_init` A/Y = adresse).

L'encodeur (src/song.c) produit les mêmes octets que `aysong.encode()` :
en-tête, ordre, pistes (les pistes identiques partagées), blocs, table des
motifs, instruments, textes (nom, auteur, noms d'instruments). Un fichier
chargé puis réencodé redonne les mêmes octets s'il vient d'`aysong.py` ou
du tracker.

Limites de ce lot : 64 motifs de 3 voix (32 de 6), 64 lignes, 15
instruments de 64 tics au plus, un morceau encodé de 12 Ko au plus.
Un fichier à 6 voix se charge, s'affiche (les colonnes 4-6 en allant à
droite) et se sauve ; le lecteur est compilé à 3 voix (`AYSONG_VOICES=3`),
il ne joue que la première puce.

## //c

Le //c est servi par la **Mockingboard 4c** : `mb_detect` la réveille en
`$C403` avant tout (il n'y a pas de souris dans ce lot ; un lot souris
devra garder la détection de la carte avant l'initialisation de la
souris, qui partage le slot 4).

## Construction, lancement, tests

    make -C mbtracker            # ../dist/MBTRACKER.po (+ dist/woz/MBTRACKER.woz)
    make -C mbtracker run        # POM2, //e enhanced, Mockingboard en slot 4
    make -C mbtracker run-iic    # POM2, //c
    make -C mbtracker test       # ~3 s

Le volume : `MBT.SYSTEM` (l'amorce `dev/lib/prodos/sysboot.s`), `MBT.SYS`
(le programme, lié pour `$2000`, sans relocation), `DEMO.AYS`, `MBT.HELP`
(les pages d'aide, `tools/help.py`, gardées en mémoire auxiliaire).

`tests/test_mbt.py` (a2shot avec Mockingboard) : //e — démarrage (barre de
titre, carte en slot 4, grille lue sur les deux pages texte), saisie au
piano de notes, coupure, effet, paramètre, instrument édité, vitesse : les
octets de la grille et l'AYS encodé = `aysong.encode()` du même morceau
construit en Python ; `^P` : les écritures AY décodées des accès au VIA =
le `Player` Python tic par tic ; `^S` : `TEST.AYS` relu dans l'image disque
et décodé par `aysong.py` ; `^L` : `DEMO.AYS` listé et chargé (octets
identiques au fichier livré), réencodé identique et joué comme le modèle.
//c avec 4c : la même saisie et la même lecture. //e sans carte : le
message, une note saisie, `^P` refusé, la liste d'ordre, `^Q`.

## Carte mémoire

| Zone | Contenu |
|---|---|
| main `$0800-$0EE2` | sauvegarde de la page zéro (crt0), tables de l'encodeur, morceau d'écoute |
| main `$1000-$1F41` | tampon OPEN, bloc de catalogue, préfixe, motif courant (`grid`) + motif de travail (pages libres du bitmap ProDOS : les lectures MLI y sont permises) |
| main `$2000-$8835` | saut d'entrée, RODATA (≥ 512 o : le FORMAT de `/RAM` écrase `$2000-$21FF` à la sortie), crt0, code (21 Ko), données |
| main `$8E00-$BDFF` | le morceau AYS (12 Ko), lu par le lecteur |
| main `$BE00-$BEFF` | pile C |
| aux `$0400-$07FF` | colonnes paires du texte 80 colonnes |
| aux `$0800-$97FF` | les motifs, 3 octets par cellule (`/RAM` déconnecté) |
| aux `$9800-$9FFF` | les pages d'aide |

Code : `main.c` 11,2 Ko (écrans), `song.c` 4,9 Ko (modèle, encodeur,
décodeur), `files.c` 0,7 Ko, `mbt_asm.s` 2,3 Ko (Mockingboard, `mb_irq`,
`aysong`, texte, clavier, copies aux). Il reste ~1,5 Ko libres sous le
morceau.

Suite : [TODO.md](TODO.md).
