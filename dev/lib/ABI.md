# Contrats d'intégration 6502 / cc65

Les en-têtes publics décrivent les coordonnées, buffers et retours de chaque
fonction. Les noyaux assembleur décrivent leurs registres et leur scratch.
Ce document fixe les préconditions communes.

## Entrée et mémoire

- D=0 (arithmétique binaire), code et pile matérielle en RAM principale.
- Sur IIe/IIc : page zéro principale, ROM visible, RAMRD/RAMWRT principaux,
  80STORE désactivé à l'entrée des primitives bancaires.
- Le code auto-modifié doit être chargé en mémoire modifiable. La propriété
  `type=ro` d'un segment ld65 n'empêche pas son exécution depuis la RAM.
- Sources, buffers, pile C et pools de sauvegarde résident hors des pages
  vidéo utilisées. Leurs pointeurs et leur contenu restent valides pendant
  les opérations et les restaurations différées des sprites.
- Le CRT sauvegarde la ZP empruntée et initialise la BSS. LOWBSS doit être
  initialisée explicitement par l'application. Dans une configuration
  `load==run`, `copydata` ne conserve pas une copie des valeurs initiales
  pour un nouvel appel BASIC sans rechargement.

## Appels, état et interruptions

Les API utilisent la convention fastcall de cc65 (défaut du compilateur) :
l'argument le plus à droite arrive dans A ou A/X, les autres sur la pile C. Le
résultat d'un octet est dans A, avec X=0. Depuis l'assembleur, utiliser le
contrat du noyau, et non supposer que les autres arguments C sont en registres.

Les primitives de dessin partagent leurs paramètres et leur scratch ; elles
ne sont pas réentrantes et ne doivent pas être appelées depuis une IRQ. Un
gestionnaire IRQ applicatif doit préserver les registres et la ZP qu'il
utilise, sans appeler ces primitives ni changer leurs banques.

| Famille | Effet d'état et obligation de l'appelant |
|---|---|
| HGR C | Tables construites à la demande ; dessin sur la page choisie ; aucune attente VBL implicite |
| Lignes gfx | HGR : noyau ASM ; DHGR : fallback C sélectionné explicitement à la liaison ; aucune allocation dynamique |
| Noyaux ASM HGR C | Préparer toutes les tables avec `hgr_build_tables` avant les accès directs ; le rendu natif de Light3dball suit ce contrat |
| HGR ASM inclus | `.ifref` exige les références avant l'inclusion ; scratch éventuellement aliasé ; bornes du noyau à respecter |
| DHGR | État I conservé ; sortie en RAM principale ; page affichée conservée sauf présentation explicite |
| `dhgr_clear` | Deux banques, trous compris ; IRQ masquées pendant toute l'opération (~189 000 cycles) |
| `dhgr_clear_rows` | Lignes visibles ; banques principales et masque IRQ rétablis entre les lignes ; noyau <1 300 cycles par ligne |
| Sprites sauvegardés | Restaurer avant de modifier le fond ou de redéfinir une forme ; conserver un fond par page |
| Cadence | VBL IIe ou délai ajouté au dessin ; repli borné en cas de signal bloqué ; masque IRQ conservé |
| ProDOS vidéo | Politique explicite pour `/RAM` avant le dessin auxiliaire ; libération à la sortie |

La page affichée et la page de dessin sont distinctes. Attendre un front VBL
avant la présentation synchronise la bascule sur IIe. Sur II/II+, le délai de
repli ne fournit pas cette synchronisation.

## Construction

Lier les objets applicatifs avant les archives. Le nom de chaque membre de
`hgrc.lib` encode son répertoire et son extension pour éviter les collisions.
La signature couvre les flags C/ASM, les outils et les sources ; un changement
invalide les objets même avec GNU make 3.81 et dans la même seconde.

`make test-tools` vérifie les constructions incrémentales et les politiques
ProDOS ; `make test-hgr` vérifie les limites, lignes, tables et pools de sprites ;
`make test-dhgr` vérifie les banques et la durée du noyau par ligne.

## Unités et durée de vie

| Entrées | Unités, bornes et comportement |
|---|---|
| HGR pixels | X 0..279, Y 0..191 ; dimensions en pixels sauf API explicitement en octets |
| `hgr_line` | Deux extrémités inclusives ; refuse toute extrémité hors écran, même pour les axes |
| `gfx_line` | Pixels du backend ; axes triés/rognés par les spans, diagonales hors écran refusées |
| Rectangles `gfx` | Deux coins inclusifs triés et rognés ; toute la largeur du backend est accessible |
| Rectangles HGR bas niveau | `hgr_fill_rect` en colonnes d'octets ; `*_pixrect` en pixels avec largeur 8 bits ; zéro ne dessine rien |
| DHGR mono / couleur | X 0..559 bits / X 0..139 pixels couleur ; Y 0..191 ; couleurs masquées à 0..15 |
| Blocs DHGR | X en octets entrelacés 0..79 ; stride >= largeur ; buffer valide de stride×hauteur octets, même si une partie est rognée |
| Sprite DHGR | X couleur ; sept banques data/mask de stride×hauteur chacune ; masque 1 conserve le fond |
| Sprite HGR sauvegardé | Dimensions stride×hauteur en octets ; capacité par sprite/page fournie à init, 96 pour l'API historique |

Les chaînes sont terminées par NUL ; les sources sont empruntées, sans copie
de leur contenu par la bibliothèque. Une source de sprite HGR doit rester
valide et immuable tant qu'un fond associé doit être restauré, y compris sur
l'autre page. Une réinitialisation valide oublie les fonds : nettoyer les deux
pages avant de réinitialiser. Les buffers ne peuvent chevaucher les pages
vidéo actives ni le scratch du moteur. Aucun garde mémoire n'est alloué sur cible.

Les appels C de dessin peuvent détruire le scratch cc65 partagé et leurs
paramètres privés ; un appel ASM direct doit suivre l'en-tête du noyau pour
A/X/Y et les octets ZP concernés. Un gestionnaire IRQ doit préserver tout ce
qu'il utilise ; le test VIA vérifie le service réel pendant `dhgr_clear_rows`,
avec contrôle des banques à l'entrée de l'IRQ et comparaison des deux pages.

`make test-minimal` vérifie les intégrations DOS HGR ; `make test-dhgr` ajoute
les intégrations IIe/ProDOS. Les essais physiques sont suivis séparément dans
[HARDWARE.md](HARDWARE.md), sans transformer un succès émulé en certification.


## Champs HUD différentiels

Les champs `hgr_hud_field_t` appartiennent à l'appelant et possèdent une boîte
noire sur chaque page. Leur structure ne doit pas être modifiée pendant le rendu.
Après une écriture extérieure dans la boîte, invalider l'historique de cette page.
Une valeur trop large est refusée avec 255, sans modifier le champ. L'API historique
`hgr_putu_field` reste sans historique et permet son ancien débordement à droite.
Le double tampon garde les deux valeurs et contenus de chiffres séparément.

Les tables HGR conservent leur format et leur adresse ; la bascule est déroulée
sur huit groupes de lignes, sans changement de scratch. La stratégie à base fixe
est testée comme prototype, sans changer le contrat des noyaux ASM actuels.

Le nombre maximum de sprites peut être fixé par `HGR_SPR_MAX` (1..8).
Compiler l'application et sa bibliothèque avec la même valeur ; la valeur
par défaut conserve huit slots et le moteur reste non réentrant.

## Rendu incrémental et adressage explicite

Le HUD compact `hgr_hud8_field_t` possède 19 octets d'état cc65 et cinq cellules
au maximum, chacune 8×8 avec un pitch de 8. Il partage les contrats de retour,
de cache par page et d'invalidation du HUD 16×16 ; chaque famille est dans des
membres d'archive distincts. Les noyaux partagent le scratch texte, sans nouvelle ZP.

`APPLE2C_CADENCE_SRCS` ajoute un ordonnanceur optionnel à échéances, alimenté
par `a2_cadence_tick` depuis l'IRQ détenue par l'application. Il n'installe
aucun vecteur ni périphérique. Le tick préserve A/X/Y, modifie NZ ; l'IRQ doit
restaurer les flags. `init`/`wait` exigent D=0 et préservent I. La source doit
avancer pendant l'attente et être synchronisée au VBL pour éviter les déchirures.
Les échéances en retard sont sautées, le retour vaut leur nombre ; $FFFF
signale un timeout et désactive l'ordonnanceur jusqu'au prochain `init`.
Les lectures 16 bits du compteur IRQ doivent être atomiques. Ne pas laisser
passer 32767 ticks sans appeler `wait`. Les fonctions de dessin restent hors IRQ.

`HGR_SPR_DAMAGE=1` est une option de compilation du moteur : elle ajoute
4×HGR_SPR_MAX+11 octets BSS pour une fermeture conservatrice des intersections
des rectangles en octets, anciens/nouveaux. L'ordre restauration inverse puis
dessin direct est conservé. Le défaut utilise toujours le préfixe/suffixe simple.

Le moteur de sprites garde un préfixe de couches inchangées par page ; il
restaure et redessine tout le suffixe dès la première couche modifiée.
Le contenu des formes doit rester immuable, même pour un sprite immobile.
`hgr_spr_invalidate` force un redessin, sans autoriser les écritures sous les
sprites. La présentation reprend explicitement la page possédée par le moteur.

`hgr_row_on_page` est indépendant de l'état global. Ses tables immuables
coûtent 384 octets chargés, aucune BSS ; les sprites masqués et le HUD 8×8
utilisent ces offsets avec la base sélectionnée. Les autres noyaux historiques
conservent leurs tables mutables. Le noyau HUD utilise les paramètres texte
partagés et reste non réentrant. Préparer le HUD sur chaque page avant animation.

Le moteur de sprites calcule stride×hauteur lors de la définition, puis utilise
des contrôleurs assembleur ; ses symboles `spr_*` servent uniquement à la liaison
interne C/ASM. Le contenu des formes reste immuable. Les contrôleurs HUD acceptent
les pas +1/+2 via les chiffres en cache ; les autres valeurs utilisent la conversion
16 bits. Un overflow conserve les pixels et les historiques.

`hgr_tile_restore` est optionnel, fastcall, non réentrant et hors IRQ. Il écrit
directement la page demandée sans modifier les pages globales ni les banques.
La carte 40×24 et les glyphes 7×8 résident hors des deux pages vidéo. La région
est rognée avant une validation complète des IDs, puis reconstruite en ASM.
L'application possède les régions sales, l'ordre des couches et les historiques
de ses pages ; ce chemin ne modifie pas le moteur save-under existant.

La pile matérielle est observée séparément de la pile cc65. La profondeur
matérielle compte aussi les octets déjà occupés à l'entrée de la charge.
Le détecteur signale les passages de S sous $00 à travers les instructions
observées ; ce profil ne constitue pas une preuve statique de toutes les IRQ,
de changements explicites de S ou de chemins non exécutés.
