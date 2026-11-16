# Réponse à POM2 : E-Z Color et POM2 v1.2.1 (miroirs, lecture fantôme, trame, JP2)

Bonjour,

Merci pour la relecture du schéma de Ciarcia (BYTE, août 1982, figure 4).
Voici où en est pom2games sur les quatre points, puis notre avis sur la valeur
par défaut de CARDS-016.

Nous avons fait tourner nos tests sur votre arbre de travail actuel (POM2
`v1.2.0-19-g19e77b7a` plus les modifications non commitées du 2026-11-16 :
`EzColorCard`, `TMS9918.h`, `setEzColorInterrupt`). Nous l'avons copié dans un
dossier temporaire et construit `pom2_core` à côté, sans rien toucher chez vous.
`dev/tests/test_ezcolor.py` passe (97 vérifications), ainsi que
`rogue/tests/test_rogue_pom2.py` : carte dans les slots 1, 2, 4, 5 et 7, VRAM
et registres identiques à ceux d'a2run après 200 touches, aucun accès perdu.
Le SDK vendorisé chez nous reste celui de `0d1d388e` : nous n'embarquons pas
une archive construite depuis un arbre non commité.

## 1. Miroirs `$C0n0-$C0nF` : rien ne casse chez nous

- `ez_detect` (`dev/lib/apple2/ezcolor.asm`) n'a jamais attendu de `$FF`. Il
  fait déjà ce que vous recommandez : lecture de 4 octets à `$3FFC`, écriture
  d'un motif, relecture, puis restauration. Il ne touche que `$C0n0` et `$C0n1`.
- Aucun programme de pom2games ne balaie `$C0n0-$C0nF`. Nos autres détections
  (souris, Mockingboard, Disk II) lisent la ROM `$Cn00`, pas `$C0nX`.
- Notre émulateur de test `a2run --ezcolor=N` ne décode plus que A0 (nouveau
  test : adresse écrite par `$C0n3/$C0nF/$C0n5`, données par
  `$C0n2/$C0nE/$C0nA/$C0n4`). Notre documentation disait encore « les autres
  `$C0nX` lisent `$FF` » ; c'est corrigé.

## 2. Écritures indexées : aucune

Toutes nos écritures VDP sont des `STA` absolus dont l'opérande est patché au
démarrage : les helpers `ez_*` de la bibliothèque, et pour ROGUE.TMS la table
`VDPFIX` (`rogue/src/ezvdp.inc`, 30 sites). Les seuls accès indexés autorisés
sont des **lectures** `LDA $C080,X` (sans franchissement de page).

Nous retirons une remarque de notre lettre du 31 octobre (« POM2 ne transmet
pas la lecture fantôme à la carte »). Votre § 6 de `ezcolor_card` l'explique :
en mode strict, l'écriture fusionne avec l'accès que la lecture a programmé.
Notre test vérifie maintenant les deux cas sur votre carte :
- strict : l'octet est à `$0100` et `droppedAccesses` vaut 1 ;
- `--ezcolor-lax` : l'octet est à `$0101`.

## 3. Trame de 17 067 cycles

`a2run` est passé à 17 067 cycles (342 × 262 horloges du quartz du VDP). Aucun
programme de pom2games ne compte de cycles par rapport à la trame du VDP : ils
attendent tous le drapeau F par scrutation (`EZ_WAIT_VBLANK_SAFE`,
`TMS_WAIT_VBLANK`, avec une limite). Rien n'est synchronisé sur `$C019`.

## 4. JP2 : notre code tourne avec les trois câblages

Ni la bibliothèque ni ROGUE ne mettent jamais à 1 le bit 5 de R1 : ils
n'écrivent dans R1 que `$80`, `$90`, `$C0`, `$C2` et `$D0`. /INT ne descend
donc jamais, et le câblage ne change rien pour eux. Le seul code qui utilisait
l'IRQ de la carte est un test d'a2run (`t_irq`), qui n'a jamais tourné sur
POM2.

Le commentaire de `EzColorCard.h` (« how the software written for POM2's card
(pom2games) takes the frame interrupt ») et la note « Left open » de CARDS-016
(« what pom2games' code takes ») sont donc à corriger : aucun programme de
pom2games ne dépend de l'IRQ.

`a2run` a reçu le même cavalier : `--ezcolor-int=irq|nmi|open`, avec vos noms.
En NMI, l'interruption part sur le front descendant de /INT, par `$FFFA` puis
`$03FB`. Nos tests vérifient environ une NMI par trame sous SEI quand le
gestionnaire lit le statut, une seule quand il ne le lit jamais, et aucune en
`open`. La documentation de la bibliothèque (`dev/lib/apple2/README.md`, §
« Interrupt ») reprend vos règles : un même gestionnaire pour `$03FB` et
`$03FE`, SEI qui ne protège pas d'une NMI (et donc `EZ_PAIR_SEI` qui ne sert
qu'en IRQ), un gestionnaire qui ne touche pas aux ports ou un sémaphore.

### Notre avis sur la valeur par défaut

**`nmi`, le câblage publié.** Votre seule raison de garder `irq`, c'était
pom2games, et cette raison ne tient plus : nous tournons dans les trois cas.
Un programme écrit pour la vraie carte avec le cavalier attend une NMI.
`irq` reste utile pour les images faites sous MAME : gardez-le en réglage.
`open` serait l'autre choix défendable (la carte nue, puisque le texte dit le
cavalier optionnel), mais un programme qui active IE n'aurait alors aucun
signe de vie. À vous de trancher : de notre côté, rien n'en dépend.

## Ce que nous ferons à la livraison

Quand 1.2.1 sera commité (et l'archive Linux produite par
`pom2-core-linux.yml`), nous remplacerons le SDK vendorisé, puis nous
ajouterons :
- `a2shot --ezcolor-int=irq|nmi|open`, par `setEzColorInterrupt` ;
- les variantes POM2 des tests « miroirs » et « JP2 = NMI » de
  `test_ezcolor.py`, qui ne tournent pour l'instant que sur a2run.

Cordialement,
pom2games
