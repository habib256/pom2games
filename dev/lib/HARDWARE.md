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

## Complément émulé POM2

`a2shot --pal` utilise le faisceau SDK de 312×65=20 280 cycles, contre
262×65=17 030 en NTSC. Ces périodes sont contrôlées par les fronts VBL réels ;
les unités de script suivent le faisceau. Elles diffèrent des unités du profil
natif POM2 (17 045/20 313), et ne doivent pas être mélangées dans les budgets.

`test_cadence.py` suit 1 000 présentations NTSC et 1 000 PAL avec une IRQ
VIA T1 initialement alignée sur le VBL, charge variable, deux dépassements
volontaires, débordement du compteur, invalidation d'arguments et arrêt de
l'horloge. Chaque présentation contrôlée est dans le VBL ; les surcharges
font sauter une échéance, sans rattrapage en rafale. Le test rétablit le vecteur
et l'état IRQ de sa machine temporaire. La bibliothèque ne configure pas la carte.

L'exemple minimal double tampon est également mesuré sur 1 000 images par
standard, avec vraie géométrie HGR, HUD et débordement 16 bits du compteur.
Il conserve deux rafraîchissements par image sans carte IRQ, en répartissant
sa charge sur deux phases VBL. Cela valide cette charge précise sur POM2 IIe.

Les essais automatisés utilisent le cœur POM2 via `a2shot --iie`, ROM IIe
amélioré, CPU 65C02 et RAM auxiliaire 128 Ko. Ils vérifient le nouveau HUD
avec le même oracle de pixels qu'a2run, les deux pages et leurs bords,
la présentation après changement externe de page, les couches de sprites
immobiles/mobiles et les interruptions VIA pendant les effacements DHGR.
Les sondes de pile vérifient un usage connu et un débordement volontaire.

Exécuter `make test-dhgr` et
`python3 dev/bench/run.py --dhgr --check` pour reproduire ce complément.
Les premières mises à jour HUD des exemples sont effectuées avant leur boucle.
Ces résultats émulés ne remplissent aucune case du registre physique ci-dessus.

Le jeu de validation complet prépare les deux pages avant de démarrer une
IRQ VIA de rafraîchissement : quatre sprites mobiles, collisions, HUD natif,
quatre directions clavier et un canal AY servis pendant 1 000 présentations
NTSC puis 1 000 PAL. Résultat : aucune échéance manquée, 2 000 services audio
par standard, flip dans le VBL, wraps 16 bits et deux piles sans débordement.
Les tests de cadence couvrent aussi 10 000/32 760 ticks de suspension pour les
huit périodes acceptées, sans faux timeout ni rafale de frames.

Lors d'un contrôle interactif précédent, POM2 native v0.9.5 a été exécuté en profil IIe
amélioré avec le disque HGR reconstruit : sprites, HUD et décor affichés,
zone des sprites identique entre deux captures en pause, mouvement repris,
et retour au prompt DOS avec ESC. Le compteur de frames continue pendant
la pause. Ce contrôle interactif complète les oracles mémoire du SDK ;
sa cadence native (17 045 cycles/frame) diffère du runner (17 030).
