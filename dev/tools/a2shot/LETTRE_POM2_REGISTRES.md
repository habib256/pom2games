# Demande pour POM2 : écrire les registres du 6502 dans la façade `pom2_core`

Bonjour,

Je travaille sur **pom2games** (`~/src/pom2games`). Nos tests de
bibliothèque passent par deux lanceurs sans fenêtre : **a2run** (notre
émulateur ][+ portable) et **a2shot** (`pom2games/dev/tools/a2shot`), construit
sur votre SDK (`sdk/include/pom2/core.hpp`, `sdk/lib/<hôte>/libpom2_core.a`).
a2shot sert à tout ce qui demande un //e : DHGR, mémoire auxiliaire, 65C02,
Mockingboard.

## Le besoin

Pour tester une routine, nous fabriquons une disquette DOS 3.3 qui fait
`BRUN` du programme de test, puis nous attendons ~1 100 images de boot avant
le premier test. a2run sait maintenant s'en passer : `load:FICHIER@ADR` copie
le binaire en RAM, puis `go:ADR` (saut) ou `call:ADR:N` (JSR depuis le PC
courant, jusqu'au retour) le lancent directement.

a2shot a reçu `load:` (par `Core::write`), mais il ne peut pas lancer le
code : la façade donne `cpuState()` en lecture seulement. Il n'existe aucun
moyen de placer le PC, ni A, X, Y, S et P.

Nous n'avons pas voulu passer par le vecteur de RESET ($03F2-$03F4 plus
`softReset()`). Sur //e, le RESET remet à zéro 80STORE, RAMRD/RAMWRT, ALTZP,
la carte langage et le mode vidéo, c'est-à-dire ce que les tests DHGR et
mémoire auxiliaire préparent justement.

## Ce que nous proposons

```cpp
/// Overwrite the registers at the current instruction boundary. cycles and
/// halted are ignored; the next step()/run() executes at programCounter.
void setCpuState(const CpuState& state);
```

Ou, plus petit, `setProgramCounter(std::uint16_t)` plus
`setRegisters(a, x, y, s, p)`. Le JSR de `call:` se fait alors côté a2shot :
il empile l'adresse de retour avec `write()` sur la page 1, place S et le PC,
puis exécute `step()` jusqu'au retour.

Contraintes :

- être appelable entre deux `run()` / `step()`, à une frontière
  d'instruction ;
- ne toucher ni au cycle courant, ni aux soft switches, ni à l'état d'une IRQ
  en attente ;
- même comportement en NMOS 6502 (][+) et en 65C02 (//e enhanced).

## Livraison

Comme pour le SmartPort : `core.hpp` et `libpom2_core.a` sans symboles de
débogage (darwin-arm64 et linux-x86_64), à copier dans
`dev/tools/a2shot/sdk`. Nous ajouterons alors `regs:`, `go:` et `call:` à
a2shot, avec la même syntaxe qu'a2run.

Rien n'a été modifié dans `~/src/pom2`.

---

Merci ! Nous pouvons retester avec `dev/tests` (les tests DHGR et mémoire
auxiliaire seront les premiers à en profiter).
