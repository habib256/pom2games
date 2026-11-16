# Réponse à POM2 : JP2 testé sur POM2 1.2.1

Bonjour,

Merci pour la 1.2.1 et pour le cavalier JP2. Nous l'avons intégrée le jour
même. Voici ce que nous avons fait et ce que nous avons mesuré.

## SDK

Le SDK embarqué dans pom2games est maintenant `pom2_core` au commit
`11017144` (« Merge release 1.2.1 »), pour les deux hôtes :
- `darwin-arm64` : construit depuis un clone propre, à ce commit ;
- `linux-x86_64` : construit par le workflow `pom2-core-linux.yml`
  (run 43818408015). Son en-tête est identique octet pour octet.

`a2shot` accepte maintenant `--ezcolor-int=irq|nmi|open` et appelle
`setEzColorInterrupt`. La ligne `vregs` affiche la position du cavalier
(`int=irq|nmi|open`), lue dans `EzColorState::interrupt`.

## Nos tests en NMI, sur votre carte

Nous avons suivi votre recette : **un seul gestionnaire pour les deux
vecteurs**, qui lit `$C0n1` à chaque trame. Le programme principal, pendant
ce temps, écrit 2 Ko de VRAM (`$1000-$17FF`) avec, pour chaque octet, une
paire d'adresse puis une donnée. Ce test (`t_pairs`, dans
`dev/tests/test_ezcolor.py`) tourne sur a2run et sur POM2, en ][+ et en //e,
avec les trois positions du cavalier.

| JP2 | interruptions | octets faux | accès perdus |
|---|---|---|---|
| NMI, avec la garde | 16 | 0 | 0 |
| NMI, sans la garde | 16 | **6** | 0 |
| IRQ (SEI autour des paires) | 16 (][+), 17 (//e) | 0 | 0 |
| ouvert | 0 | 0 | 0 |

Sans la garde, la lecture du statut tombe au milieu d'une paire et la coupe.
Le test sait donc voir l'erreur que vous décrivez.

La garde que nous avons validée :
- autour de chaque paire : `PHP / SEI / INC busy` … `DEC busy / PLP`.
  Le SEI protège en IRQ, le sémaphore protège en NMI ;
- si le gestionnaire trouve `busy` à 1, il ne lit pas le statut et met
  `pend` à 1 ;
- après la paire, si `pend` vaut 1, le programme principal lit le statut
  lui-même. C'est indispensable en NMI : tant que personne ne lit le statut,
  /INT reste bas et aucun front ne déclenche la NMI suivante. Notre test
  `t_nmi_quiet` le vérifie : une seule NMI en 5 trames.

**Une précision sur « un gestionnaire commun ».** Les deux chemins
n'arrivent pas dans le même état. En IRQ, la ROM (][+ comme //e) a déjà
sauvé A en `$45` avant de sauter par `$03FE`. En NMI, `$FFFA` mène
directement à `$03FB`, et rien n'est sauvé. Nous plaçons donc en `$03FB`
un `JMP` vers un petit préambule `STA $45`, qui tombe dans le gestionnaire
IRQ. Les deux chemins finissent alors pareil, par `LDA $45 / RTI`. Ce
détail mériterait une ligne dans votre documentation de JP2.

Autres vérifications sur POM2 1.2.1 :
- `t_nmi` : 5 NMI en environ 5 trames sous SEI. Aucune en `open`, aucune en
  `irq` sous SEI ;
- miroirs (décodage de A0 seul) : adresse écrite par `$C0n3/$C0nF/$C0n5`,
  données par `$C0n2/$C0nE/$C0nA/$C0n4`, aucun accès perdu ;
- **IRQ sur ][+** : la carte atteint maintenant `$03FE` (16 IRQ). Notre
  lettre du 31 octobre signalait le contraire (vecteur `$FFFE = $FF59`).
  C'est corrigé chez vous (commit `b0aae5d6`), et nous retirons la remarque ;
- ROGUE (`rogue/tests/test_rogue_pom2.py`) : la partie scriptée de 200
  touches, rejouée en `nmi` puis en `open`, donne la même VRAM qu'en `irq`.
  Il n'y a aucun accès perdu. C'est attendu : ROGUE ne met jamais à 1 le bit 5
  de R1.

## Valeur par défaut

**Oui, passez la valeur par défaut à NMI.** Nous maintenons l'avis de notre
lettre de ce matin (`LETTRE_POM2_EZCOLOR_V121.md`). C'est le câblage publié, et plus rien chez nous ne dépend de
l'IRQ. Si vous la changez, `a2shot` n'a rien à modifier : nos tests
indiquent toujours le câblage explicitement, sauf ceux qui n'activent pas
l'interruption.

Cordialement,
pom2games
