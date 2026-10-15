# Demande pour POM2 : disquette 3,5" de 800 Ko dans la façade `pom2_core`

Bonjour,

Je travaille sur **pom2games** (`~/src/pom2games`), en particulier sur
**Neowilderness**, un portage Apple IIe enhanced 128 Ko / ProDOS 8. Tous nos
tests passent par **a2shot** (`pom2games/dev/tools/a2shot`). C'est un
lanceur sans fenêtre, construit sur votre SDK : `sdk/include/pom2/core.hpp`
et `sdk/lib/libpom2_core.a` (arm64), copiés depuis POM2.

Le jeu va être livré sur une **disquette 3,5" de 800 Ko** (image ProDOS de
819 200 octets, 1 600 blocs). La version 140 Ko est pleine et le prochain lot
(chasse, pêche, cueillette) ne tient que sur 800 Ko. Or la façade publique
n'expose que le Disk II 5,25" :

> `Disk II: Refused /tmp/a2shot-….po: file size 819200 bytes doesn't match
> any supported format`

L'émulateur complet sait déjà le faire (`SmartPortCard`, `SmartPort35Unit`),
c'est seulement `pom2_core` qui ne l'expose pas. Pourriez-vous l'ajouter ?

## Ce dont nous avons besoin

1. **Installer le contrôleur** : une carte SmartPort avec des unités 3,5",
   dans un slot vide (5 par convention), sans dump Liron (votre ROM
   synthétique suffit), sur IIe enhanced (`CpuModel::CMOS65C02`,
   `iieMemory = true`).
2. **Monter une image** de 819 200 octets en ordre ProDOS (`.po`, et `.2mg`
   si c'est simple) sur l'unité 0 ou 1.
3. **Persistance des écritures dans le fichier image.** Le jeu écrit sur sa
   disquette (SAVE/RESTORE, Hall of Fame) et nos tests relisent le fichier
   **pendant** que l'émulateur tourne. Aujourd'hui, avec le Disk II, ils
   déclenchent l'écriture par un échange de disquette (`insertDisk`). Il nous
   faut l'équivalent : soit un vidage explicite, soit des écritures qui
   vont directement au fichier.
4. **Démarrer à froid sur la carte** ($Cn00), comme `bootDisk()` le fait pour
   le slot 6. Si possible sans Disk II branché, et sinon en le gardant
   branché sans qu'il ait la priorité.
5. **Déterminisme.** Nos tests comparent des comptes de cycles et des états
   mémoire d'une exécution à l'autre : le temps d'une lecture de bloc doit
   être reproductible. Pouvez-vous nous indiquer le modèle de temps de la
   carte (cycles par bloc lu ou écrit) pour que nous le notions ?

## Proposition d'API (à adapter à vos conventions)

```cpp
/// Install POM2's 3.5" SmartPort controller (synthetic ROM, a ProDOS
/// block device; no Liron dump) in an empty slot, 5 by convention.
bool attachSmartPort(int slot = 5);
/// Mount an 800 KB ProDOS-order image (.po/.2mg) on SmartPort unit 0 or 1.
/// Writes reach the image file (flushSmartPortDisk, or a new insert).
bool insertSmartPortDisk(int unit, std::string_view path);
/// Write the unit's changed blocks back to its image file now.
bool flushSmartPortDisk(int unit);
/// Cold boot at the boot ROM of the card in `slot` ($Cn00).
bool bootSlot(int slot);
```

Pour gagner du temps, j'ai fait un prototype dans `src/Pom2Core.cpp`, puis
je l'ai **annulé** : je ne touche pas à votre dépôt. Je vous le décris pour
référence :

- `std::make_unique<SmartPortCard>(slot)`, puis `setUnitCount(2)` ;
- `setUnit(i, std::make_unique<SmartPort35Unit>())`, avec
  `setWriteBackEnabled(true)` **avant** `loadImage`, puisque `loadImage`
  recopie l'option sur l'image de remplacement ;
- `flushSmartPortDisk` = `saveDirty()` de l'unité ;
- `bootSlot` = `coldBoot()` puis `cpu.setProgramCounter(0xC000 | slot << 8)`.

Points que je n'ai pas pu vérifier :
- le démarrage ProDOS 2.4.3 sur la ROM synthétique d'un IIe enhanced (nos
  disquettes utilisent le bloc de démarrage ProDOS standard) ;
- le comportement de `$Cn07 = $01` sur ce modèle ;
- la gestion de `setUnitCount` quand une seule unité est montée.

## Ce qui nous serait livré

- `include/pom2/core.hpp` et `libpom2_core.a` (arm64, sans symboles de
  débogage, comme aujourd'hui), que nous copions dans
  `pom2games/dev/tools/a2shot/sdk/` ;
- idéalement un test de contrat dans `pom2_core_api` : démarrer une image
  ProDOS 800 Ko depuis le slot 5, écrire un fichier, vider, relire le fichier
  image depuis l'hôte.

De notre côté, a2shot choisira le contrôleur selon la taille de l'image :
`--disk` d'un fichier de 819 200 octets → SmartPort slot 5, et `insert:`
videra l'image courante avant l'échange. Les 80 scripts de tests de
Neowilderness rejoueront tout sur l'image 800 Ko.

Merci beaucoup !

— pour pom2games / Neowilderness
