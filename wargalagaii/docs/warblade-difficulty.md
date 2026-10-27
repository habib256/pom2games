# Warblade : progression et adaptation à WarGalagaII

Recherche et audit du 27 octobre 2026. Complète la
[référence générale](warblade-reference.md). Les effectifs et délais proposés
ici sont ceux de **WarGalagaII**, pas des données extraites de Warblade.

## Sources et degré de confiance

- **Manuel v1.33**, Simon Quincey, [copie du manuel](https://warblade.fandom.com/wiki/Game_Manual).
  Source primaire hébergée par un wiki. Quatre difficultés : Easy, Normal,
  Hard, Ace ; Easy nécessite un profil Easy. Records séparés par mode.
  Les profils débloquent des avantages disponibles dès le niveau 1.
  Le manuel recommande Normal et présente Easy comme adapté aux enfants et
  aux parties courtes : il ne recommande pas Easy à tout le monde.
- **FAQ v1.2c**, Johnny Walker : [débuter](https://warblade.fandom.com/wiki/Gameplay_Basics)
  et [guide avancé](https://warblade.fandom.com/wiki/Gameplay_Advanced).
  Témoignage de joueur, distinct du manuel. L'auteur recommande Easy pour
  apprendre et conseille des tirs très visibles sur un fond assombri.
  Son guide nomme le niveau 1 « JUST WARMING UP », le 3 « THE FIRST BIG ONE »
  et le 4 « KAMIKAZE ». Il décrit les achats et déblocages comme essentiels
  à la progression. Les niveaux bonus ne tirent jamais ; les perfects
  successifs augmentent leur prime. Après 100 niveaux, reprise plus rapide
  avec trajectoires inversées.
- **Guide communautaire**, [structure des niveaux](https://warblade.fandom.com/wiki/Level_Guide).
  Petits ennemis en 1–2, gros en 3, kamikaze en 4 ; petits en 5–6, gros en
  7 et bonus en 8. Distingue les niveaux à nettoyer entièrement de ceux où
  les ennemis peuvent simplement quitter l'écran.
- **Recoupement secondaire**, [StrategyWiki, Walkthrough](https://strategywiki.org/wiki/Warblade/Walkthrough)
  et [Missions](https://strategywiki.org/wiki/Warblade/Missions).
  Décrit une difficulté qui agit sur résistance, mouvement, cadence et score,
  ainsi que des compositions propres aux missions. Ces descriptions ne
  constituent pas des tables de réglage certifiées du jeu original.

Les ouvertures directes de Fandom renvoient HTTP 402 ; ces passages ont été
consultés dans l'index de recherche. Le site historique warblade.as n'était
pas accessible. Aucun comptage image par image d'une partie neuve n'a été
effectué : **l'effectif exact du premier niveau reste non vérifié**.
Les versions PC, Mac et iOS, les difficultés et les profils débloqués doivent
être distingués dans toute future comparaison vidéo.

## Diagnostic du code avant correction

Le premier niveau lançait 5 vagues de 8, une paire toutes les 6 images
logiques ; une plongée toutes les 20 images, jusqu'à 6 aliens en vol ;
une tentative de tir toutes les 12 images, projectiles à 4 lignes/image.
Les quatre premiers niveaux avaient les mêmes paramètres d'attaque.
Le bonus occupait le niveau 4 et le kamikaze le 8, à l'inverse du guide.

À 30 images/s : 2,5 tentatives de tir/s et une nouvelle plongée toutes les
0,67 s. Avec le vaisseau lent et le tir simple, un débutant rencontrait
déjà presque toute la densité du jeu.

## Correction appliquée

| Niveau | Composition | Effectif lancé | Plongeurs max. | Délai plongée | Délai tir | Vitesse projectile |
|---|---|---:|---:|---:|---:|---:|
| 1 | petits, 2 vagues | 16 | 1 | 60 | 60 | 2 |
| 2 | petits, 3 vagues | 24 | 1 | 52 | 52 | 2 |
| 3 | petits + 4 gros, 4 vagues | 28 | 2 | 44 | 44 | 3 |
| 4 | kamikaze | 40 | sans formation | — | 44 | 3 |
| 5 | petits, 3 vagues | 24 | 2 | 40 | 40 | 3 |
| 6 | petits, 4 vagues | 32 | 3 | 36 | 36 | 3 |
| 7 | petits + 4 gros, 5 vagues | 36 | 3 | 32 | 32 | 3 |
| 8 | bonus, sans tirs | 40 | sans formation | — | — | — |

Délais en images logiques, vitesses en lignes/image. NTSC : 30 images/s ;
PAL : 25. Le délai de tir concerne une tentative : il faut un tireur
éligible et un emplacement de projectile libre.

Dans les niveaux ordinaires avant le 13, une paire arrive toutes les
10 images ; après la dernière paire d'une vague, pause de 90 images.
Les niveaux spéciaux conservent leurs cinq vagues, leurs primes et leur
rythme d'entrée. Les formations ordinaires atteignent progressivement les
40 emplacements ; les gros occupent les colonnes paires de la première
rangée. Les boss gardent leurs 16 escortes.

Les limites finales restent 7 plongeurs et 6 projectiles ennemis. Les
boucles augmentent la difficulté et inversent les trajectoires. Les petites
formations utilisent le signal de fin d'entrée habituel : plongées et
transition ne doivent pas attendre d'ennemis inexistants.

## Deuxième passe : vagues, économie et démo

Quatre entrées originales remplacent l'entrée unique : arc simple, balayage,
boucle et courbe en S. Un script de huit niveaux choisit la première courbe ;
chaque vague prend la suivante, avec des entrées en miroir des deux côtés.
Le premier niveau commence par les deux courbes les plus lisibles. Les
bonus gardent leur trajet de passage sans formation et les kamikazes leur
descente dirigée vers le vaisseau. Ce sont des courbes écrites pour WGII,
pas des trajectoires extraites de Warblade.

Pendant les quatre premiers niveaux, le petit ennemi de la colonne centrale
gauche de chaque vague transporte une pièce d'or de **50 crédits**. Il faut
le détruire et attraper la pièce ; un pool d'objets plein n'écrase pas les
autres bonus. Les autres ennemis gardent leurs drops aléatoires. Une seule
pièce ramassée suffit au seuil de boutique et à l'achat Extra Speed.
C'est un réglage d'accessibilité propre à WGII, inspiré du rôle des achats
dans Warblade, et non une règle attestée du jeu original.

Essai du pilote anticipant les dangers, sur les graines 44348, 1, 5 et 7,
sans achats ni invulnérabilité : avant cette passe, il atteignait la fin
du premier paquet avec respectivement 20, 0, 10 et 0 crédits. Après les
deux changements, il atteint la boutique avec 180, 60, 150 et 150 crédits,
trois vies dans les quatre cas. Le pilote vise surtout les ennemis : ce
petit échantillon vérifie l'accès technique aux achats, pas la réussite
moyenne d'un débutant. L'effet des nouvelles courbes et celui des pièces
ne sont pas isolés dans cette comparaison.

La démo suit maintenant **1 → 3 → 4 → 8 → 25** : petits ennemis, gros,
kamikaze, bonus, boss. Les sauts concernent uniquement la démo ; une vraie
partie garde les niveaux successifs. Elle dure 3 000 pas (100 secondes
NTSC, 120 PAL), puis revient au titre. Les transitions affichent le niveau
réellement présenté. Clavier et bouton peuvent l'arrêter, y compris pendant
le bonus ; aucun record n'est enregistré et la partie suivante reprend au 1.

## Suites recommandées

1. **Affiner les scripts**, au-delà des quatre courbes actuellement utilisées.
   Mesurer les huit premiers niveaux d'une partie PC/Mac, profil neuf et
   difficulté notée, pour pousser la fidélité au-delà de la structure.
2. **Choix Easy / Normal / Hard**, avec records distincts. Faire varier
   cadence, vitesse et attaques simultanées, puis tester chaque courbe.
3. **Économie du premier achat** : faire essayer les pièces prévisibles
   à des débutants et mesurer les crédits réellement ramassés ; l'accès
   reste conditionné au seuil de 50 crédits.
4. **Lisibilité des tirs** : comparer leur contraste aux étoiles et aux
   objets, puis vérifier en mouvement sur affichage HGR réel.
5. **Récompenses de maîtrise** : interception avant formation, séries de
   perfects et progression persistante. Les profils de Warblade rendent une
   partie avancée trompeuse pour calibrer une première partie.

Les tests automatiques vérifient logique, rendu et cadence. Le ressenti
reste à évaluer avec une personne découvrant les huit premiers niveaux,
sans bonus initial ni invulnérabilité.

## Validation du 27 octobre

Compilation des disquettes PO et WOZ réussie. Contrôles exécutés : effectifs
et fins des 100 niveaux, 30 parties aléatoires de 3 000 pas, comparaison
6502/modèle (dont transitions, gros ennemis, boss, gel et soucoupe), rendu,
son, boutique, sous-jeux, démo, records, démarrage et sorties ProDOS.
Les variantes émulées //e et //c, NTSC/PAL, clavier/manette, passent.

Le pilote anticipe les dangers : cela vérifie la jouabilité technique,
sans remplacer un essai de débutant. La séquence aléatoire de référence
perd ses trois vies en 2 000 pas ; elle ne constitue pas un modèle de joueur.
Le banc conserve 40 ennemis, six plongeurs autorisés et dix tirs :
300 images sans retard. Les tests longs des niveaux 25, 97, 100 et de la
boucle 255 passent, avec et sans Mockingboard dans les scènes de charge.

Après la deuxième passe, `make -C wargalagaii test` et
`python3 wargalagaii/tests/test_long.py` passent. Le test de démo échantillonne
les cinq niveaux dans l'émulateur, observe les aliens du bonus, compare les
3 001 pas au modèle, vérifie l'arrêt clavier/bouton pendant le bonus et le
redémarrage d'une partie au niveau 1. Le rendu de la démo et de ses
transitions est comparé à une reconstruction complète sur 120 images.
Les captures du premier niveau, du bonus et du boss ont été inspectées.
