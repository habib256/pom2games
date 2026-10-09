# Validation sur machines physiques

Les tests automatisés exécutent les binaires dans a2run / POM2. Aucun essai
physique n'a été exécuté dans cette session : les lignes ci-dessous restent
à renseigner après observation. Les modèles revendiqués par chaque famille
sont décrits dans ses en-têtes ; un test HGR ne valide pas le DHGR.

## Préparer un lot identifiable

```sh
make -C dev/examples/minimal clean all
python3 -c 'from pathlib import Path; import hashlib; [(print(hashlib.sha256(p.read_bytes()).hexdigest(), p)) for p in sorted(Path("dev/examples/minimal/build").glob("*.dsk")) + sorted(Path("dev/examples/minimal/build").glob("*.po"))]'
cl65 --version
```

Conserver les sommes des images, la révision Git avec ses changements locaux,
`build/memory.json`, la version de cc65 et la date. Transférer ces images par
le moyen habituel de la machine, puis amorcer le système de la disquette.
Décrire ROM, RAM auxiliaire, affichage, accélérateur et configuration PAL/NTSC
lorsqu'ils sont connus ; ne pas déduire ces caractéristiques d'un simple succès.

## Observations à effectuer

1. HGR simple : titre et diagonale restent fixes, compteur avance, carré se
   déplace sur une bande noire. Observer les écritures visibles ; ESC rend
   un affichage texte utilisable et permet de relancer le programme.
2. HGR double : même contenu, alternance régulière des deux pages. Observer
   les déchirures et la cadence ; ne pas confondre repli temporisé et VBL.
   ESC puis relance doivent fonctionner ; vérifier aussi Ctrl-RESET.
3. DHGR ProDOS avec `/RAM` installé : le programme doit rester en texte et
   refuser l'animation, même si `/RAM` est vide. Vérifier que les fichiers
   présents restent accessibles après retour au lanceur.
4. DHGR dans une configuration sans `/RAM` installé : fond noir, texte blanc,
   carré orange en mouvement ; aucune modification persistante du mode texte
   après ESC ou Ctrl-RESET. Relancer depuis ProDOS et vérifier le même résultat.
5. Pour une application utilisant une IRQ de périphérique : exécuter sa charge
   habituelle pendant les effacements découpés et relever les interruptions
   manquées ou retardées. Le test VIA automatisé valide le cas émulé ; le simple
   exemple sans carte ne démontre pas le fonctionnement d'une IRQ physique.

## Registre des résultats

| Machine/configuration | HGR simple | HGR double | DHGR refus /RAM | DHGR sans /RAM | ESC / RESET / relance |
|---|---|---|---|---|---|
| II / II+ | À tester | À tester | Non ciblé | Non ciblé | À tester |
| IIe, configuration RAM/vidéo à consigner | À tester | À tester | À tester | À tester | À tester |
| IIc, version ROM à consigner | À tester | À tester | À tester | À tester | À tester |

Pour chaque essai, noter image/SHA256, compilateur, configuration, résultat,
anomalies et moyen d'observation. Un résultat s'applique à cette combinaison ;
il ne couvre pas automatiquement les clones, autres ROM ou accélérateurs.

Les exemples HGR utilisent un historique HUD indépendant par page. Lors des
essais physiques, vérifier en particulier le passage 9 → 10, les retours à une
valeur courte après relance, et l'absence de chiffres anciens sur une seule
des pages. Les nouveaux benchmarks incluent les identités CPU/runner/ROM,
mais ces identités d'émulation ne remplacent pas les observations du tableau.
