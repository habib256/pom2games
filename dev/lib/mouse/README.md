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

## Contexte optionnel pour les programmes assembleur historiques

`mouse_context.asm`, extrait de Pinball, protège toute la zéro-page et les
64 octets des boîtes de communication dans les trous de la page texte.
Le pilote `mouse.s` reste indépendant : inclure ce module seulement dans
les programmes qui réutilisent ces zones. `mouse.mk` fournit la dépendance
`MOUSE_CONTEXT_SRCS` et le chemin `MOUSE_INCS`.

Initialiser `mouse_context_native_mouse` à zéro avant la détection, puis le
mettre à une valeur non nulle pour le firmware natif du //c. Les fonctions
`mouse_context_save_workspace` et `mouse_context_restore_workspace`
entourent l’appel au firmware ; l’appelant masque les IRQ pendant toute la
transaction. Sur une carte en slot, la copie des boîtes est réinstallée ;
sur //c, les coordonnées mises à jour par les IRQ restent en mémoire vive.
`mouse_context_capture_holes` / `mouse_context_install_holes` permettent
aussi de protéger ces boîtes autour d’un autre utilisateur de la page texte.

Le client DOS est optionnel et se configure avant l’include :

```asm
MOUSE_CONTEXT_DOS_ENTRY = $AAFD
MOUSE_CONTEXT_DOS_ROWS = 6
MOUSE_CONTEXT_CLEAR_BASE = $0400
MOUSE_CONTEXT_CLEAR_PAGES = 3
.include "mouse_context.asm"
```

Ces valeurs sont celles de PCS ; un autre client fournit les siennes.
`mouse_context_clear_buffers` efface les pages demandées et conserve les
boîtes natives du //c. `mouse_context_file_manager` échange atomiquement les
copies DOS/souris sur //c autour de l’entrée configurée et conserve les
résultats A/X/Y, les indicateurs d’erreur et le masque IRQ de l’appelant.
L’entrée reçoit X/Y et A contenant le drapeau natif, conformément à l’ABI
historique de PCS. Les appels ne sont pas réentrants.

Sans client DOS, le module réserve 321 octets de BSS, aucune zéro-page ;
le client PCS ajoute 53 octets de BSS. L’appelant garde ces buffers et le
code résidents, initialise leur contenu et laisse les boîtes matérielles
libres de ses propres tables. Les adresses PCS, le choix des paddles, la
conversion des coordonnées et l’ancrage du glissement restent dans Pinball.

`python3 dev/tests/test_mouse_context.py` teste le module sans client DOS.
`make -C pinball test-mouse` valide l’intégration avec les cartes `mouse` et
`mouseaw`, les slots 4/5 et les ROM natives //c de 16/32 Ko.
