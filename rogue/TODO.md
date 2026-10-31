# ROGUE — prochains lots

Lot 1 (fait, 2026-10-31) : portage du TMS_Rogue de POM1 sur Apple II + carte
E-Z Color, détection dans tout emplacement (sauf 3 et le lecteur), message
clair sans carte, sons et airs au haut-parleur, cœur séparé de l'affichage
(docs/VIDEO_API.md), lanceur TMS / DHGR / erreur, tests a2run --ezcolor.

- **Version DHGR** (`ROGUE.DHGR`, //e 128 Ko ou //c sans la carte) : autre
  builder, sur `docs/VIDEO_API.md` ; aujourd'hui un bouche-trou
  (`src/dhgr_stub.s`). Une fois là : un test //e qui joue quelques tours.
- **Rogue X2** : la suite de POM1 (plus grande carte, défilement), si elle
  est faite côté POM1.
- **Mockingboard** : sons et musique sur le AY (`mb_irq.asm`, `aysong.asm`)
  quand une carte est présente, le haut-parleur sinon.
- **Partie sauvée** : écrire l'état (page zéro du jeu + LOWBSS, ~600 o) dans
  un fichier par RWTS (`rwts_sectors`, `dos33patch.py --sectors`).
- **Vrai matériel** : essayer une E-Z Color (ou une réplique) sur II+ et //e,
  emplacement 3 compris ; vérifier l'avis sur l'écran Apple.
- Clic de pas optionnel (désactivé par défaut) ; touches ZQSD / HJKL en
  option (aujourd'hui IJKL et flèches, H = aide comme dans POM1).
- `a2shot` n'a pas la carte : un test POM2 de bout en bout quand le SDK
  l'aura.
