# DIRTBIKE — prochains lots

Les lots terminés sont dans [CHANGELOG.md](CHANGELOG.md).

## Lot 2 — jouabilité
- Régler la conduite à la main dans POM2 : traction, inclinaison, souplesse
  de la suspension, rebond (modèle d'abord, puis `make test`).
- Fantôme : enregistrer les entrées de chaque tick (rejouables au bit près,
  comme la démo) ; course contre le fantôme du record.
- Autres figures (atterrissage sur une roue) ; multiplicateur de combo.
- Drapeau visible dès le bord droit (x > 255 : une ligne verticale 16 bits).
- Encore de la place : ~135 octets en `$6000-$91FF`, une vingtaine par
  bande de la page texte (TXT5, TXT6).

## Lot 3 — contenu
- Moto et pilote plus détaillés (jambes, guidon, fourche) ; animation de la
  chute.
- Décor : drapeaux départ/arrivée, collines lointaines.

## Performances (seuil : 5 %)
Lot 1 bis : défilement au pixel. ~36 000 cycles par image sur les bosses
(28 i/s) et 34 000 sur le plat (30 i/s), contre 48 000 au lot 1 (défilement
par octets). Répartition sur les bosses : sol ~12 700, physique ~9 700,
moto ~8 600.
- Physique : carrés des contraintes en 8×8 au lieu de 16×8 ; `height_at`
  appelé 7 fois par tick.
- Moto : marques d'effacement calculées pendant le tracé.
- Cadence régulière : VBL sur //e ; sur II+, synchronisation par le bus
  flottant : `dev/lib/apple2/vapor.asm` existe depuis le 2026-10-24 (SNAKE,
  marqueur sur la ligne HGR 191, testé sur a2run et POM2 NTSC/PAL/IIe).
- Mémoire : ~135 octets libres en `$6000-$91FF`, ~30 en `$1000-$1FFF`,
  page zéro pleine (1 octet).
