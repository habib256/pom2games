# Demande pour POM2 : la carte E-Z Color (TMS9918A) dans la façade `pom2_core`

Bonjour,

Je travaille sur **pom2games** (`~/src/pom2games`), et en particulier sur le
portage de **ROGUE** (la version TMS9918 de POM1, `sketchs/tms9918/game_rogue`)
vers l'Apple II équipé de la carte **E-Z Color** de Steve Ciarcia (BYTE, août
1982) que POM2 vient de recevoir (`src/EzColorCard.cpp`, entrée du CHANGELOG du
2026-10-31, clé de catalogue `ezcolor`). Tous nos tests passent par
**a2shot** (`pom2games/dev/tools/a2shot`), un lanceur sans fenêtre construit
sur votre SDK : `sdk/include/pom2/core.hpp` et `sdk/lib/<hôte>/libpom2_core.a`
(arm64 et linux-x86_64), copiés depuis POM2 au commit `6f7f06a7`.

Or la façade publique ne connaît pas la carte : `core.hpp` expose
`attachMockingboard`, `attachMouse`, `attachRgbCard`, `attachSmartPort`,
`attachDiskII`, mais rien pour l'E-Z Color, et le `pom2_core` que nous
embarquons ne contient pas la classe. En attendant, nous testons ROGUE sur un
modèle TMS9918 minimal ajouté à notre propre `a2run` (lecture/écriture VRAM,
registres, drapeau de trame, fenêtre d'accès), mais seule POM2 fait foi pour
le rendu, la détection par sonde et le respect de la contrainte « silicium
strict » (≥ 18 cycles entre deux accès VDP pendant l'affichage) que vous
avez portée de POM1. Pourriez-vous exposer la carte dans le SDK ?

## Ce dont nous avons besoin

1. **Brancher la carte dans un slot au choix** : `attachEzColor(int slot)`
   sur un II+ comme sur un //e (la carte n'a pas de ROM : elle n'est visible
   qu'à `$C0n0` / `$C0n1`), avec refus si le slot est pris. Notre jeu
   autodétecte la carte en sondant les slots 7, 5, 4, 2, 1, 6 puis 3 : il nous
   faut pouvoir la placer dans n'importe lequel pour tester chaque cas, et
   aussi **l'absence de carte** (le jeu doit alors lancer sa version DHGR ou
   afficher un message d'erreur).
2. **Lire l'état du VDP** depuis l'hôte, pour nos `peek` : les 16 Ko de
   VRAM, les huit registres d'écriture et le registre d'état (sans effacer
   les drapeaux F / 5S / C, c'est une lecture de débogage, pas celle du
   programme).
3. **Récupérer l'image de la carte** : un équivalent de `renderFrame()` pour
   le moniteur de l'E-Z Color (`paintPicture`, 288 × 216 avec la bordure, ou
   les 256 × 192 utiles), afin de produire des captures PNG comparées
   d'une exécution à l'autre, comme nous le faisons pour l'écran Apple.
4. **L'interruption** : confirmer que `/INT` du VDP arrive bien sur l'IRQ
   du slot avec le bit IE du registre 1, et qu'une lecture de `$C0n1` la
   lève. Notre jeu peut s'en servir pour cadencer les mises à jour.
5. **Le compteur d'accès trop rapprochés** : POM1 jette silencieusement les
   écritures espacées de moins que la fenêtre d'accès. Un compteur lisible
   depuis l'hôte (nombre d'accès tombés dans la fenêtre fermée depuis la
   dernière lecture) nous permettrait d'assurer en test que le jeu respecte
   le contrat des 18 cycles, au lieu de constater un écran corrompu.
6. **Déterminisme** : nos tests comparent des octets de VRAM et des cycles
   d'une exécution à l'autre ; le balayage progressif et la fenêtre
   d'accès doivent rester reproductibles à cycle égal. Pouvez-vous nous
   indiquer le modèle de temps retenu (position du faisceau au cycle près,
   taille des fenêtres par mode) pour que nous le notions dans nos tests ?

## Proposition d'API (à adapter à vos conventions)

```cpp
/// Install an E-Z Color Graphics Interface (TMS9918A, 16 KiB VRAM) in an
/// empty slot. No slot ROM: the card lives at $C0n0 (data) and $C0n1
/// (register/status); its /INT drives the slot IRQ. Returns false if the
/// slot is taken or the machine has no slots (a //c).
bool attachEzColor(int slot = 4);
bool ezColorAttached() const;

/// Debug reads that leave the chip's state alone.
struct EzColorState {
    std::array<std::uint8_t, 8> registers;
    std::uint8_t status;          // F, 5S, C and the 5th-sprite number
    std::uint16_t address;        // the auto-incremented VRAM pointer
    bool irqAsserted;
    std::uint32_t fastAccesses;   // accesses inside a closed window since the last call
};
EzColorState ezColorState() const;
void ezColorVram(std::uint8_t* out, std::size_t len, std::uint16_t from = 0) const;

/// The card's own monitor: same lifetime rules as renderFrame().
FramebufferView renderEzColorFrame();
```

Une option de ligne de commande dans l'application (`--ezcolor=N`, à côté de
`ezcolor_card` dans `CliDispatcher.cpp`) nous servirait aussi pour `make run`.

## Ce que nous ferons ensuite

Dès que le SDK l'expose, a2shot gagne `--ezcolor=N`, un pas `vpeek` et une
capture du moniteur de la carte ; les tests de ROGUE (détection dans chaque
slot, absence de carte, rendu du premier donjon, contrat des 18 cycles sur
une partie scriptée) basculeront de notre modèle `a2run` vers POM2, qui
restera la référence.

Merci d'avance,

pom2games

## Complément (bibliothèque et modèle a2run, 2026-10-31)

- **Lecture fantôme des écritures indexées.** Sur le 6502 NMOS, `STA abs,X`
  (et `STA (zp),Y`) lit l'adresse cible un cycle avant d'écrire. Sur
  `$C0n0`, cette lecture est une lecture VRAM (l'adresse avance, l'octet
  tombe un cran plus loin) ; sur `$C0n1`, c'est une lecture d'état (bascule
  des deux octets remise à zéro, F effacé). Notre bibliothèque
  (`dev/lib/apple2/ezcolor.asm`) n'écrit donc qu'en absolu (opérandes
  patchés par `ez_detect`), et notre `a2run` modélise cette lecture fantôme.
  Pouvez-vous confirmer que le `M6502` de POM2 fait cette lecture fantôme
  vers `deviceSelectRead` de la carte, pour qu'une écriture indexée fautive
  se voie aussi chez vous ?
- **Sonde de détection.** Par slot candidat : lecture d'état, adresse de
  lecture `$3FFC`, 4 lectures sauvées, adresse d'écriture `$3FFC`, motif
  `$A5 $5A $3C $C3`, relecture et comparaison, puis réécriture des 4 octets
  sauvés ; ≥ 18 cycles entre deux accès ; dernier accès toujours sur
  `$C0n0` (phase 0 d'un Disk II laissée éteinte). Un test POM2 utile :
  E-Z Color dans un slot, Disk II (boot) en 6, souris en 4, carte absente.
- **Chiffres du modèle a2run** (à comparer aux vôtres, point 6) : trame de
  17 030 cycles depuis la mise sous tension, F levé à l'entrée de la ligne
  192 (65 cycles par ligne), accès compté « trop rapide » s'il suit le
  précédent de moins de 16 cycles avec l'affichage actif (R1 bit 6) et le
  faisceau sur les lignes 0-191 ; accès comptés : port de données et
  prélecture d'une adresse de lecture. 5S et C restent à 0 chez nous.
- **ROM II+.** Notre `apple2p.rom` (celle d'a2shot/roms) contient `$FF59`
  en `$FFFE` (le RESET de l'ancien Monitor) alors que le point d'entrée IRQ
  de l'Autostart, `$FA40`, est bien présent ; a2run y route l'IRQ. Si la
  ROM II+ de POM2 vient du même fichier, l'IRQ de la carte sur un II+
  pourrait partir en `$FF59` : à vérifier de votre côté.

## Réponse reçue le 2026-10-31 (ba7f04da)

POM2 a répondu par le commit ba7f04da (main) : la façade expose la carte —
`attachEzColor(slot, siliconStrict = true)`, `ezColorAttached`,
`ezColorState` (R0-R7, état, adresse, /INT, compteur `droppedAccesses`, lus
sans effet de bord), `ezColorVram`, `resetEzColorDropCount`,
`renderEzColorFrame` (288 × 216, image en 16,12 dans la bordure R7). Le mode
silicon-strict est désormais actif par défaut (aussi dans l'application) :
fenêtre d'accès des tables openMSX selon le mode et le faisceau (Graphics I/II
: 8 cycles jamais perdus, 7 perdus), R1 bit 7 = adressage 16 Ko, trame NTSC
propre de 17 062 cycles.

Intégré chez nous le même jour :

- SDK vendorisé à ba7f04da (`sdk.mk`) : darwin-arm64 construit ici,
  linux-x86_64 par `.github/workflows/pom2-core-linux.yml` (run 41225532582),
  en-tête identique ; `POM2_SDK_HAS_EZCOLOR` garde la compilation d'a2shot.
- a2shot : `--ezcolor[=N]`, `--ezcolor-lax`, pas `vpeek`, `vregs`,
  `vdrop:reset`, `vshot:FICHIER.png[:pic]`, `text`, `cpu`, et
  `vdp_dropped=N` en fin de run (formats d'a2run : `a2test.Result` lit les
  deux).
- a2run : la trame du VDP passe à 17 062 cycles (262 lignes), comme la vôtre.
- R1 bit 7 : déjà à 1 partout (`$C0`/`$C2`/`$80`/`$D0`/`$90` dans
  dev/lib/tms9918 et ROGUE) ; seule la sonde `ez_detect` tourne avant le
  premier R1 (R1 = 0, donc 4 Ko en mode strict) : écriture et relecture
  passent par la même correspondance, la détection reste juste.
- Mesures (`droppedAccesses`) : ROGUE 0 au titre, 0 sur la partie scriptée de
  200 touches, 0 jusqu'à la profondeur 2, cartes en 1, 2, 4, 5, 7 ; le VRAM et
  les registres de ROGUE sont ceux d'a2run octet pour octet (titre, premier
  donjon, 200 touches) ; bibliothèque : 0 pour tous les chemins, 0 aussi pour
  une boucle `STA` non paddée de 9 cycles, 95 perdus sur une rafale de
  512 écritures à 4 cycles (`dev/tests/test_ezcolor.py`, variantes POM2).
- Le VRAM de POM2 démarre en motif FF/00 (le nôtre à zéro) : nos tests ne
  comparent que les octets écrits.

Toujours ouvert : la ROM ][+ (`roms/apple2p.rom`, identique chez vous) a
`$FF59` en `$FFFE` ; l'IRQ de trame de la carte (R1 bit 5) sur un ][+ part
donc en `$FF59` et n'atteint pas `$03FE` (vérifié sur a2shot : le
`t_irq` de test_ezcolor ne revient pas). Lecture fantôme NMOS : sur a2shot,
`STA $C080,X` (X = `$40`, sans franchissement de page) après une adresse
d'écriture `$0100` dépose l'octet en `$0100` : la lecture fantôme n'atteint
pas la carte (le 6502 NMOS lit `$C0C0` avant d'écrire, l'octet tomberait en
`$0101`, comme dans a2run). Sans conséquence pour nous (la bibliothèque
n'écrit qu'en absolu), mais à signaler.
