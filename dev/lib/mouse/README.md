# AppleMouse II

Pilote cc65/6502 du firmware AppleMouse en slots 1 à 7. `mouse_init()` détecte
la carte, initialise le mode 1 par scrutation, borne X à 0–139 et Y à 0–191,
et positionne la souris au centre. Il renvoie le slot, ou zéro en son absence.

`mouse_poll()` fournit `mouse_x`, `mouse_y` et `mouse_buttons` (bit 7 : bouton
principal pressé). Le jeu calcule le front montant pour distinguer un clic
d'un bouton maintenu. `mouse_close()` désactive la carte à la sortie.

Sur //e, le pilote ne demande pas d'interruptions souris et conserve le masque
IRQ. Sur //c, il active les interruptions natives nécessaires au comptage des
déplacements, tout en lisant la position par scrutation. Dans les deux cas, il
copie les résultats de READMOUSE avant de rétablir ce masque. L'appelant doit
utiliser la RAM et la page zéro principales, 80STORE désactivé, ROM visible.
Les coordonnées correspondent aux pixels de couleur DHGR ; la raquette suit
X et aucun curseur logiciel supplémentaire n'est dessiné.

Validé avec les deux cartes POM2 `mouse` (MC68705) et `mouseaw` (AppleWin),
toutes deux exécutant la ROM de slot Apple. Également validé avec la souris
**intégrée native du //c**, sans substitution de ROM, versions 16 et 32 Ko.
Le //c+ n'est pas encore validé.

Référence : [Apple II Mouse Technical Notes, notes 1 et 5](https://mirrors.apple2.org.za/Apple%20II%20Documentation%20Project/Interface%20Cards/Digitizers/Apple%20Mouse%20Interface%20Card/Documentation/Apple%20II%20Mouse%20Technical%20Notes.pdf).

Le client ChromaBreak utilise aussi `_mouse_timing_mode` et `_mouse_serve_irq`
pour le mode 9 (VBL) du //c, avec un gestionnaire alloué par ProDOS.
La fermeture désactive ce mode avant de libérer le gestionnaire.
