# Demandes pour POM2 : ce qui manque à la façade `pom2_core` pour les tests de pom2games

Bonjour,

Je travaille sur **pom2games** (`~/src/pom2games`). Tous nos tests passent
par **a2shot** (`pom2games/dev/tools/a2shot`), un lanceur sans fenêtre et
déterministe, construit sur votre SDK : `sdk/include/pom2/core.hpp` et
`sdk/lib/<hôte>/libpom2_core.a` (darwin-arm64 et linux-x86_64), copiés depuis
POM2. Merci encore pour le SmartPort 3,5" (b93b5f6), qui sert tous les jours.

Trois manques nous obligent aujourd'hui soit à compiler des tests contre vos
sources internes (`--pom2-src ../../pom2`, hors de notre CI), soit à tester
à la main dans l'application. Tout ce dont nous avons besoin existe déjà dans
le cœur ; il s'agit de l'exposer dans `core.hpp`. Les demandes sont classées
par priorité.

---

## 1. Écrire les registres du 6502 (prioritaire, petit)

**Le besoin.** Pour tester une routine, nous fabriquions une disquette DOS
3.3 qui faisait `BRUN` du programme de test, puis nous attendions ~1 100
images de boot. Notre émulateur portable a2run s'en passe maintenant :
`load:FICHIER@ADR` copie le binaire en RAM, puis `go:ADR` (saut) ou
`call:ADR:N` (JSR depuis le PC courant, jusqu'au retour) le lancent. Sur
14 tests de bibliothèque, ce mode et un vidage mémoire plus rapide ont fait
passer le temps de ~140 s à ~35 s.

a2shot, qui sert à tout ce qui demande un //e (DHGR, mémoire auxiliaire,
65C02, Mockingboard), a reçu `load:` par `Core::write`. Il ne peut pas lancer
le code, car `cpuState()` est en lecture seule. Nous n'avons pas voulu passer
par le vecteur de RESET ($03F2-$03F4 plus `softReset()`) : sur //e, le RESET
remet à zéro 80STORE, RAMRD/RAMWRT, ALTZP, la carte langage et le mode vidéo,
c'est-à-dire ce que les tests préparent justement.

**Proposition.**

```cpp
/// Overwrite the registers at the current instruction boundary. cycles and
/// halted are ignored; the next step()/run() executes at programCounter.
void setCpuState(const CpuState& state);
```

Le cœur l'a déjà en interne (`M6502::setProgramCounter`, `setAccumulator`,
dans `src/M6502.h`, utilisés par vos tests du débogueur). Le JSR de `call:`
se fait côté a2shot : il empile l'adresse de retour avec `write()` sur la
page 1, place S et le PC, puis exécute `step()` jusqu'au retour.

Contraintes : appelable entre deux `run()`/`step()` ; ne toucher ni au cycle
courant, ni aux soft switches, ni à une IRQ en attente ; même comportement en
NMOS 6502 (][+) et en 65C02 (//e).

---

## 2. Carte souris AppleMouse

**Le besoin.** PINBALL, ARKABREAKOUT et CHROMABREAK se pilotent à la souris
(II+ et //e : carte AppleMouse dans un slot). Leurs tests souris (`make
test-mouse`) compilent `pinball/tests/mouse_probe.cpp` ou `playtest.cpp`
contre `M6502.h`, `Memory.h`, `MouseCard.h`, `MouseCardAppleWin.h` et
`IIcMouse.h`, en liant `build/libpom2_core_test.a`. Ils dépendent donc de
votre arborescence et de son build, et ne tournent pas en CI.

**Proposition.**

```cpp
enum class MouseModel : std::uint8_t { AppleMouse, AppleMouseAppleWin };
/// Install a mouse card (real firmware ROM from roms/) in an empty slot.
bool attachMouse(int slot = 4, MouseModel model = MouseModel::AppleMouse);
/// Host mouse state: absolute position in the card's clamp window, button.
void setMouse(int x, int y, bool button);
```

Il faut aussi que les interruptions de la carte (mouvement, bouton, VBL)
arrivent au 6502 comme dans l'application : nos jeux s'y calent.

---

## 3. Le modèle //c

**Le besoin.** WARGALAGA II et CHROMABREAK visent le //e enhanced **et le
//c**. Sur //c, leur horloge est l'interruption VBL du firmware souris
intégré. Aujourd'hui, nous ne le vérifions qu'avec `make run-iic` (`POM2
--preset iic --slot 4=iicmouse`) ou `make test-iic`, qui compile lui aussi
contre vos sources. Le TODO de WARGALAGA II garde « //c non testé » ouvert
pour cette raison.

**Proposition.** Un choix de machine dans `CoreConfig` :

```cpp
enum class Machine : std::uint8_t { AppleIIPlus, AppleIIe, AppleIIeEnhanced, AppleIIc };
struct CoreConfig { Machine machine = Machine::AppleIIPlus; VideoTiming timing; /* ... */ };
```

Pour `AppleIIc` : ROM //c (16 Ko et 32 Ko si possible, nos tests passent
déjà par vos variantes `iic16` et `iic32`), souris intégrée et son VBL,
lecteur 5,25" intégré et SmartPort externe. `setMouse()` (point 2) piloterait
la souris intégrée.

**Question liée** (à vérifier de votre côté, même sans façade) : sur //c avec
une Mockingboard 4c, la détection réveille la carte à `$C403` et peut masquer
la ROM souris du slot 4. L'interruption VBL du firmware souris reste-t-elle
utilisable ? `attachMockingboard()` sur //c nous permettrait de le tester.

---

## Livraison

Comme pour le SmartPort : `core.hpp` et `libpom2_core.a` sans symboles de
débogage (darwin-arm64 et linux-x86_64), à copier dans
`dev/tools/a2shot/sdk`, et les ROM éventuellement nécessaires (souris, //c)
dans `dev/tools/a2shot/roms`. Les trois points sont indépendants : livrez-les
dans l'ordre qui vous arrange, le point 1 nous débloque le plus vite.

De notre côté, à chaque livraison : `regs:`, `go:`, `call:` dans a2shot,
puis le passage des tests souris et //c dans la batterie normale (et donc
dans notre CI Linux).

Rien n'a été modifié dans `~/src/pom2`.

---

Merci ! Nous pouvons fournir les disquettes, les scripts de test
(`dev/tools/a2test.py`) et retester chaque livraison avec toute la batterie
de pom2games.
