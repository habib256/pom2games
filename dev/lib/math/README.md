# lib/math — arithmétique entière exacte pour la physique (asm)

*[← dev](../../README.md)*

Produits, racine carrée, division et générateur pseudo-aléatoire pour le
6502, pensés pour les moteurs physiques en virgule fixe. Tous les résultats
sont **exacts** et suivent la sémantique « arrondi vers le bas » de Python
(`x * y >> 6`) : un modèle Python sert d'oracle bit à bit, comme dans
DIRTBIKE (`tools/physics.py` ↔ `src/physics.inc`).

Sources des techniques : DIRTBIKE (produits par pointeurs en page zéro) et la
démo PHYSICS reconstruite dans [`physics/`](../../../physics/README.md)
(tables lues à décalage fixe pour les constantes, raccourcis pour ±1,0,
racine par table de départ, LFSR).

## Mise en place

```asm
.include "zp.inc"            ; si random.asm est utilisé (prng_lo/prng_hi)
MUL_TABLES = $0800           ; 2 Ko alignés sur la page, au choix du programme
MUL_ACC    = 1               ; optionnel : accumulateur mul_acc0..2 (+3 o de ZP)
MUL_INIT_BOOT = 1            ; optionnel : mul_init dans le segment "INIT" (code de
                             ; démarrage qu'un tampon recouvre ensuite)
.include "math.inc"          ; EN TÊTE : page zéro et macros

        JSR mul_init          ; une fois au démarrage (~110 000 cycles)
        JSR sqrt_init         ; si isqrt16 est utilisé (après mul_init)
        ...
; à la fin du source, après les appelants (.ifref) :
.include "sqrt.asm"          ; avant mul.asm
.include "div.asm"
.include "random.asm"
.include "mul.asm"
```

`MUL_TABLES` est obligatoire : un `.align 256` dans BSS n'est fiable que si
la config ld65 aligne le segment. Choix habituels : `$0800` (zone HELLO d'un
programme BRUN qui ne revient pas au BASIC, comme DIRTBIKE), 2 Ko libres de
LOWBSS, ou la page HGR inutilisée.

`apple2.mk` ajoute `-I $(MATH)` à `A2_INCS` et suit ces fichiers dans
`A2_ASM_DEPS`.

## Fichiers et routines

| Fichier | Routine | Effet | Coût |
|---|---|---|---|
| `math.inc` | page zéro | `mul_x` (16), `mul_y` (8), `mul_p0..p2` (24), `mul_t`, 4 pointeurs ; 13 o (+3 avec `MUL_ACC`), chacun remplaçable par un alias | — |
| | `MUL_K16 k` | `mul_p = mul_x × k`, k constante 0..255, en ligne | ~60 c |
| | `MUL_KS16 k` | idem avec `mul_x` signé | ~70 c |
| `mul.asm` | `mul_init` | construit les tables de carrés (rien sur le disque) | ~110 000 c |
| | `mul_u8u8` | `mul_p0..1 = mul_x(bas) × mul_y` | ~55 c |
| | `mul_u16u8` | `mul_p = mul_x × mul_y`, non signés | ~110 c |
| | `mul_s16s8` | idem, signés, 24 bits exacts | ~130 c |
| | `mul_dir` | `mul_p = A/X × Y` signés ; Y = 0, +64, −64 (direction ±1,0 à l'échelle 64) prennent un raccourci | 15-50 c / ~150 c |
| | `mul_shr6` | `mul_p1..2 = ⌊mul_p / 64⌋` | 30 c |
| | `mul_acc_set` / `_add` / `_shr6` | somme de produits sur 24 bits puis ⌊/64⌋ | |
| `sqrt.asm` | `sqrt_init`, `isqrt16` | `A = ⌊√mul_x⌋` ; départ `sqrt_seed[mul_x+1]`, puis pas de 1 avec n² = sqr1[2n] | ~40 c + ~25 c/pas |
| `div.asm` | `div16by8` | `mul_x = mul_x / A`, `A = reste` ; 8 pas si le quotient tient sur un octet | ~190 c / ~400 c |
| `random.asm` | `rand8` | LFSR de Galois 16 bits (taps `$B400`) sur `prng_lo/hi` ; graine non nulle | ~20 c |

### Les astuces

* **Quarts de carrés** : a·b = ⌊(a+b)²/4⌋ − ⌊(a−b)²/4⌋. Les octets bas des
  quatre pointeurs valent `mul_y`, les octets de `mul_x` servent d'index
  (`(mul_s1l),Y`), et `EOR #$FF` donne a−b+255 pour la seconde table. Aucun
  code automodifié (contrairement à `mul8x8` de PHYSICS, qui patche 8
  opérandes pour un produit 16×8).
* **Signé** : produit des motifs non signés, puis deux corrections en
  complément à deux (y < 0 : −x·256 ; x < 0 : −y·65536).
* **Constante** (`MUL_K16`) : `sqr1+k,X` et `sqr2+255−k,X` (la seconde table
  est symétrique autour de 255), donc rien à préparer, deux lectures par
  octet. Pratique pour les coefficients fixes (rebond, frottement, amortissement).
* **Directions ×64** (`mul_dir`) : une normale de sol plat vaut (0, −64) ;
  ×0 et ×±64 deviennent un effacement ou deux décalages, avec exactement le
  même résultat. Dans DIRTBIKE, environ −16 % sur la physique de la
  piste 1.
* **Racine** : la table `sqrt_seed[h] = ⌊√(h·256)⌋` (256 o, construite au
  démarrage) ne dépasse jamais ; un ou deux pas suffisent au-delà de 256.
* **Division** : la démo PHYSICS utilisait une table de 512 o de réciproques
  plus une multiplication de correction. Pour un quotient d'un octet, huit pas
  de soustraction coûtent autant, sans table.

## Tests

`dev/tests/test_math.py` (dans `make test-hgr`) assemble chaque routine,
l'exécute dans a2run sur environ 1 900 cas (bords, motifs de signe, hasard
fixe) et compare au calcul Python. Il est construit deux fois : tables en
`$0800`, puis tables et `sqrt_seed` dans la page HGR 2.

Auteur : VERHILLE Arnaud. Licence : [GPL-3.0](../../../LICENSE).
