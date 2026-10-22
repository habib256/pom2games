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

Lot 2a (fait, 2026-10-21) : ~420 octets libérés (page texte 1 en BSS, hall
of fame en LOWBSS), drapeau sur la ligne d'arrivée et de tour, points de
wheeling.

Lot 2b (fait, 2026-10-22) : souris retirée ; manette : X = inclinaison
analogique, bouton 0 = gaz, bouton 1 = frein, menus au manche (un cran par
poussée) ; frein revu (il coupe les gaz, ~1 g au lieu de ~0,6 g, une roue
arrêtée par le frein tient : la moto ne recule plus) ; 30 parcours résolus
de nouveau. Puis le frein en l'air : il n'arrête plus que la rotation des
roues (un petit couple fini, ~12°), plus de rotation sans fin.
Inclinaison sur 8 niveaux (fins au milieu, jusqu'à 6 px en arrière) pour
les wheelings. Puis 6 px en avant aussi : en avant du milieu le pilote se
déplace sans vitesse (plus de coup qui jetait la moto en l'air ou écrasait
le pilote quand le manche passait d'un bout à l'autre).

## Lot 2 — jouabilité
- Régler la conduite à la main dans POM2 : traction, inclinaison, souplesse
  de la suspension, rebond (modèle d'abord, puis `make test`).
- Fantôme : enregistrer les entrées de chaque tick (rejouables au bit près,
  comme la démo) ; course contre le fantôme du record.
- Autres figures (atterrissage sur une roue) ; multiplicateur de combo.
- Drapeau visible dès le bord droit (x > 255 : une ligne verticale 16 bits).
- Encore de la place : 3,5 bandes de la page texte ($0680-$07F7), ~220
  octets en RAM principale.

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
