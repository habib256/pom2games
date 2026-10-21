# tools/re6502 — rétro-ingénierie de programmes 6502

*[← dev](../../README.md)*

Les outils génériques sortis de la reconstruction de la démo PHYSICS
([`physics/`](../../../physics/README.md)), qui les utilise encore pour
regénérer ses sources et les recouper avec da65.

| Module | Rôle |
|---|---|
| `opcodes.py` | `OPS` (6502 NMOS documenté), `C02OPS` (ajouts 65C02), `LEN` ; `decode()`, `branch_target()`, `operand_text()`, `text()` |
| `trace.py` | `trace(img, entrées, régions, stops)` : parcours récursif (branches, JSR, JMP) → octets de code, cibles, problèmes (opcode inconnu, 65C02, saut indirect ou hors image) ; `runs()` |
| `da65.py` | `info(code, lo, hi, labels, zp)` : fichier info da65 tiré de la trace, pour un désassemblage indépendant |
| `disk.py` | `PHYS2LOG`, `phys_sector()` : secteurs physiques d'une image .dsk en ordre DOS (chargeurs maison) |
| `cli.py` | `trace`, `listing`, `refs abs|zp` sur une image mémoire de 64 Ko |

```
python3 dev/tools/re6502/cli.py trace physics/work/image.bin --region 800-1D00 --region 9400-9B00
python3 dev/tools/re6502/cli.py listing physics/work/image.bin 0800 0900 --region 800-1D00
python3 dev/tools/re6502/cli.py refs physics/work/image.bin zp --region 800-1D00
```

Dans un script, importer le paquet depuis `dev/tools` :
`sys.path.insert(0, '<racine>/dev/tools')` puis `from re6502.trace import trace`.
Les scripts de `physics/tools` le trouvent par un chemin relatif à leur
propre emplacement, et restent compatibles avec `python3 -I`.

Vérifié lors de l'extraction : sources régénérées, image extraite et fichiers
info da65 identiques à l'octet près à ceux des anciens scripts ; le disque
reconstruit reste identique à l'original et `make da65check` passe.

Auteur : VERHILLE Arnaud. Licence : [GPL-3.0](../../../LICENSE).
