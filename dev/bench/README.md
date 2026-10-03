# Mesures cc65

```sh
make bench             # HGR, a2run portable
make bench-dhgr         # HGR + DHGR, a2shot IIe requis
make bench-check       # Budgets HGR, exécutés aussi dans make test / CI
python3 dev/bench/run.py --dhgr --check
python3 dev/bench/run.py --dhgr --out /tmp/apple2-metrics.json
```

Le script construit une archive, puis un petit programme par opération avec
`-Oirs`. Il démarre DOS et s’arrête sur deux marqueurs d’instruction : les cycles
mesurés comprennent les arguments et l’appel C, excluent l’initialisation et
les 12 cycles des deux appels de marqueur. HGR initialise ses tables avant
la mesure. HGR utilise un NMOS 6502 dans a2run ; DHGR un 65C02 dans a2shot.
Les adresses viennent du fichier de labels ld65, sans estimation de timing.

Les tailles sont celles du programme de mesure complet, CRT et bibliothèque
cc65 compris : CODE + STARTUP, RODATA, RAM (BSS/LOWBSS/DATA/ZPSAVE), ZEROPAGE
et fichier binaire. La pile C réservée et les pages vidéo ne sont pas comptées
comme BSS ; la RAM affichée ne représente donc pas toute la mémoire occupée.
La ligne compiler et les options sont enregistrées dans le JSON.

`baseline.json` conserve les mesures de référence. Une hausse des cycles de
plus de 5 % (minimum 16), des tailles de plus de 3 % (minimum 16 octets), ou
une hausse de ZP fait échouer `--check`. Un compilateur différent peut changer
ces résultats ; le rapport en conserve la version pour faciliter le diagnostic.
Le gate DHGR reste local car le SDK a2shot fourni est macOS arm64.

Après examen d’une modification intentionnelle :

```sh
python3 dev/bench/run.py --dhgr --update
```

Cette commande remplace les références des cas mesurés. Une exécution normale
ou `--check` ne modifie jamais la référence.

Cas actuels : clear, segment pleine largeur, rectangle, texte, sprite HGR ;
clear, segment, rectangle, transfert de bloc, sprite masqué et texte DHGR.
Les résultats sont reproductibles pour un même compilateur et cœur CPU.
