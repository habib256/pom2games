# DIRTBIKE — prochains lots

Lot 1 (fait) : physique Verlet 6502 identique au modèle, piste 1, défilement
par octets, moto en traits et sprites, manette et clavier, chrono, chute,
arrivée.

Lot 1 ter (fait) : menu de 30 parcours prouvés faisables, chargés par RWTS
depuis des fichiers LZ4FH, records de la session.

Lot 1 quater (fait, 2026-10-21) : vitesse x2, suspension raidie (moins de
chutes), points de sauts et saltos, page de titre, démo en attract mode,
hall of fame (temps et points, initiales) sauvé sur la disquette.

Lot 1 quinquies (fait, 2026-10-21) : circuits de 3 tours, reprise après une
chute, compte à rebours, sons d'événements, musique de titre, jingle
d'arrivée (et de record), vitesse x3 du premier réglage (18 px/tick).

## Lot 2 — jouabilité
- AppleMouse (dev/lib/mouse) : X = inclinaison, Y = gaz, comme sur le Mac.
- Régler la conduite à la main dans POM2 : traction, inclinaison, souplesse
  de la suspension, rebond (modèle d'abord, puis `make test`).
- Fantôme : enregistrer les entrées de chaque tick (rejouables au bit près,
  comme la démo) ; course contre le fantôme du record.
- Autres figures (wheeling, atterrissage sur une roue) ; multiplicateur.
- Ligne d'arrivée visible (drapeau).
- RAM principale pleine (7 octets libres) : toute nouveauté doit d'abord en
  libérer (tables en LOWBSS, données dans les fichiers de piste).

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
  flottant (« vapor lock ») à étudier.
- Mémoire : ~3,9 Ko libres en `$6000-$95FF`, ~480 octets en `$1000-$1FFF`,
  page zéro presque pleine (2 octets).
