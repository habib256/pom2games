# Niveaux

| Fichier        | Collection   | Auteur           | Source |
|----------------|--------------|------------------|--------|
| `microban.xsb` | Microban (155 niveaux) | David W. Skinner | <https://raw.githubusercontent.com/Nican/Xye/master/web/microban.xsb> (SHA-256 `4233c2bf…c07e5b`), copie verbatim |

David W. Skinner a publié ses collections pour la libre diffusion, à une
condition : « These sets may be freely distributed provided they remain
properly credited. » Le crédit figure sur l'écran titre, dans le README du
jeu et ici.

Format : XSB standard (`#` mur, `$` caisse, `.` cible, `*` caisse sur cible,
`@` joueur, `+` joueur sur cible, espace ou `-` sol ; `;` commentaire, une
ligne vide entre deux niveaux). `../tools/sokoban_levels.py` les convertit en
paquets pour la disquette et écarte ceux qui ne tiennent pas à l'écran.

**Microban II** (135 niveaux) n'est pas encore là : son site de référence
n'était pas joignable depuis l'environnement de développement. Pour l'ajouter,
déposer le fichier ici sous le nom `microban2.xsb` : le `Makefile` le prend
automatiquement (deuxième collection, « II » dans le HUD).
