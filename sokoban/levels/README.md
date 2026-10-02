# Niveaux

| Fichier        | Collection   | Auteur           | Source |
|----------------|--------------|------------------|--------|
| `microban.xsb` | Microban (155 niveaux) | David W. Skinner | <https://raw.githubusercontent.com/Nican/Xye/master/web/microban.xsb> (SHA-256 `4233c2bf…c07e5b`), copie verbatim |
| `microban2.xsb` | Microban II (135 niveaux, avril 2002) | David W. Skinner | <https://raw.githubusercontent.com/OMerkel/Sokoban/master/3rdParty/Levels/Microban%20II.txt> (SHA-256 `5a811176…4d60d608`), copie verbatim (fins de ligne CRLF) |

David W. Skinner a publié ses collections pour la libre diffusion, à une
condition : « These sets may be freely distributed provided they remain
properly credited. » Le crédit figure sur l'écran titre, dans le README du
jeu et ici.

Format : XSB standard (`#` mur, `$` caisse, `.` cible, `*` caisse sur cible,
`@` joueur, `+` joueur sur cible, espace ou `-` sol ; `;` commentaire, une
ligne vide entre deux niveaux). `../tools/sokoban_levels.py` les convertit en
paquets pour la disquette et écarte ceux qui ne tiennent pas à l'écran.

Les fichiers sont gardés entiers, numérotation d'origine comprise : c'est
`sokoban_levels.py` qui, à la construction, couche d'un quart de tour horaire
les niveaux trop hauts qui tiennent ainsi, et écarte ceux qui ne tiennent
toujours pas à l'écran (le HUD montre le numéro d'origine, `II:056`).

**Vérification de Microban II.** Le site de référence (sneezingtiger.com) et
les sites Sokoban habituels sont refusés par la politique réseau de
l'environnement de développement ; seul GitHub est joignable. Deux copies
indépendantes y ont été comparées :

- `OMerkel/Sokoban` (ci-dessus) : 135 niveaux, en-tête et titres de Skinner.
  Le `Microban.txt` du même dépôt est identique, niveau par niveau, à notre
  `microban.xsb`.
- `martincameron/warehouse-j2me`, `levels/Microban 2 (c) David W
  Skinner.lev` : 129 niveaux en codage numérique (0 sol, 1 cible, 2 mur,
  4 caisse, 5 caisse sur cible, 6 joueur, 7 joueur sur cible). Ce portage
  pour téléphone a retiré les niveaux trop grands, ici les 130 à 135.

Les 129 niveaux communs sont identiques, dans le même ordre.

**Solutions.** `solutions.txt` donne une solution pour chacun des 272
niveaux gardés, tels que le jeu les dessine (couchés compris) :
`../tools/make_solutions.py` les cherche avec `../tools/solver.py` (263
niveaux) ; les 9 plus durs (Microban 93, 139, 144, 146, 153 ; Microban II
102, 104, 109, 124) ont été résolus par YASS 2.153 de Brian Damgaard (GPL-3,
<https://github.com/joriswit/YASS>, compilé en programme console avec Free
Pascal). Chaque solution est rejouée et vérifiée avant d'être écrite, puis
`make test` les fait toutes jouer au vrai jeu dans a2run (~1 min) : les 272
niveaux sont résolus jusqu'au niveau suivant.
