# Demandes pour POM2 : la façade `pom2_core` pour la sonde de CHROMABREAK

Bonjour,

Merci pour la livraison 0849ee51 (`setCpuState`, `attachMouse`/`moveMouse`/
`setMouse`, `Machine::AppleIIc`, Mockingboard 4c). Elle est intégrée :
a2shot a maintenant `regs:`/`go:`/`call:`, `--iic`/`--iic16`, `--mouse`
et `mouse:`. Les tests souris de PINBALL et d'ARKABREAKOUT ainsi que le
test //c de WARGALAGA II sont portés sur la façade, avec un petit en-tête
commun `dev/tools/a2shot/probe.hpp`. Ils tournent dans `make test` et dans
notre CI Linux (≈60 s à eux trois), avec les mêmes mesures que sur vos
sources.

Il reste une sonde compilée contre vos sources internes (`--pom2-src`) :
`chromabreak/tests/playtest.cpp` (1 400 lignes, `make test-mouse` et
`make test-records`). Voici ce qui lui manque, par priorité. Comme la
dernière fois, tout existe déjà dans le cœur.

---

## 1. Observer les accès au bus (prioritaire)

**Le besoin.** La sonde utilise `MemoryWatchSink` avec `setReadWatch` et
`setWriteWatch` pour trois vérifications :

- compter les clics du haut-parleur (lectures de `$C030`) et les dater au
  cycle près : thème du titre, hauteur et tempo des notes, silence en pause ;
- compter les bascules de page (`$C054`/`$C055`) et vérifier qu'elles
  tombent dans le VBL (`cycle % période >= 65 × 192`) ;
- vérifier qu'aucune écriture dans `$2000-$5FFF` ne touche la page affichée
  pendant un changement de niveau.

Sans observateur, nous décodons chaque instruction avant de l'exécuter
(`probe::storeTarget`, suffisant pour WARGALAGA II), mais ce décodage ne
voit ni les lectures, ni le cycle exact de l'accès, ni les accès des
interruptions.

**Proposition.**

```cpp
/// Called for each CPU bus access to a watched address, at its cycle.
using BusWatch = std::function<void(std::uint16_t address, std::uint8_t value,
                                    bool write, std::uint64_t cycle)>;
void setBusWatch(BusWatch watch);               // empty: off
void watchAddresses(std::uint16_t first, std::uint16_t last, bool reads, bool writes);
void clearWatchedAddresses();
```

Un simple `speakerToggleCount()` suffirait déjà pour une partie des tests
(la sonde appelle aussi `Memory::getSpeakerToggleCount()`).

## 2. L'état vidéo

**Le besoin.** `Memory::getDisplayState()` : TEXT, HIRES, MIXED, PAGE2
(et 80COL/DHGR). Sur //e et //c nous relisons `$C01A-$C01F` ; sur un ][+
ces registres n'existent pas, et PINBALL et ARKABREAKOUT vérifiaient le
mode HGR plein écran sur ][+ aussi (le firmware souris passe en TEXT et
LORES à l'initialisation).

**Proposition.** `DisplayState displayState() const;` (une structure de
booléens, sans effet de bord).

## 3. La carte RGB Le Chat Mauve

**Le besoin.** CHROMABREAK choisit le DHGR mixte sur une carte RGB, sans
la détecter. La sonde branche `LeChatMauveCard` en slot 7 (variante
`Feline` sur //e, `IIcAdapter` sur //c) et vérifie `dhgrMode()` : mixte
pendant le jeu, 140 couleurs à la sortie.

**Proposition.**

```cpp
enum class RgbCardModel : std::uint8_t { LeChatMauveFeline, LeChatMauveIIcAdapter };
enum class RgbDhgrMode : std::uint8_t { Color140, Mono560, Mixed };
bool attachRgbCard(int slot = 7, RgbCardModel model = RgbCardModel::LeChatMauveFeline);
RgbDhgrMode rgbDhgrMode() const;
```

## 4. Le Disk II dans un autre slot, et la protection en écriture

- `attachDiskII` ne connaît que le slot 6. PINBALL avait une variante qui
  démarre d'un Disk II en slot 5 et y vérifie SAVE/LOAD (le menu fichier
  propose le slot de démarrage). Proposition : un paramètre `int slot = 6`
  à `attachDiskII` et `bootDisk`.
- La sonde rend le disque protégé en écriture
  (`driveImage(0).setWriteBackEnabled(false)`) pour vérifier qu'une
  sauvegarde refusée n'altère rien. Proposition :
  `bool setDiskWriteProtected(int drive, bool protectedOn);`.

## 5. Petites choses

- La ROM du //e non enhanced (`apple2e_unenh.rom`) et un
  `Machine::AppleIIe` qui l'accepte : la variante `iie-nmos` vérifie le
  message « 65C02 requis ». Si la ROM est redistribuable comme les autres,
  merci de l'ajouter à la livraison (`dev/tools/a2shot/roms`).

---

## Livraison

Comme d'habitude : `core.hpp`, `libpom2_core.a` sans symboles de débogage
(darwin-arm64 et linux-x86_64), et les ROM nécessaires dans
`dev/tools/a2shot/roms`. Les points sont indépendants ; le 1 et le 2
débloquent le plus.

De notre côté, à la livraison : `chromabreak/tests/playtest.cpp` porté sur
`probe.hpp`, `test-mouse` et `test-records` versés dans `make test`, et la
variante slot 5 de PINBALL rétablie.

Rien n'a été modifié dans `~/src/pom2`.

Merci !
