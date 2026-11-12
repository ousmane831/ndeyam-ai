# Protocole d'essai pilote — rations calculées par Ndeyam AI

*Version de travail du 11/11/2026, à compléter et valider avec le zootechnicien, le vétérinaire et le statisticien
du projet avant le démarrage.*

## 1. Objectif

Vérifier, sur des animaux réels, qu'une ration **calculée par Ndeyam AI puis validée par un nutritionniste ou
zootechnicien** permet d'obtenir un gain de poids **au moins équivalent** à la ration habituelle de l'éleveur, pour un
**coût alimentaire égal ou inférieur**, sans effet négatif sur la santé des animaux.

Questions posées :

1. Le gain moyen quotidien (GMD) du lot « ration Ndeyam » est-il au moins égal à celui du lot « ration habituelle » ?
2. Le coût alimentaire par kilo de poids gagné est-il plus faible ?
3. Les animaux consomment-ils la ration proposée (refus, appétence) ?
4. Observe-t-on des troubles de santé liés à la ration ?
5. L'outil est-il utilisable sur le terrain (pesées, saisies, hors ligne) ?

## 2. Site et animaux

| Élément | Proposition (à ajuster) |
|---|---|
| Site | 1 exploitation ou station partenaire, avec enclos séparés et balance fiable |
| Animaux | Béliers d'embouche (mâles entiers), même race ou races réparties équitablement entre lots |
| Profil à l'entrée | 25 à 35 kg, 8 à 12 mois, en bonne santé |
| Préparation | Identification par boucle, déparasitage et vaccinations selon le vétérinaire |
| Effectif | **15 animaux par lot au minimum** (voir § 4), soit 30 animaux |

## 3. Dispositif

- **Deux lots** :
  - **Lot témoin** : ration habituelle de l'éleveur, décrite précisément (aliments, quantités pesées) ;
  - **Lot essai** : ration calculée par Ndeyam AI (formule rapide ou calcul détaillé), **validée par le
    zootechnicien avant le démarrage**.
- **Répartition** : par tirage au sort à l'intérieur de groupes de poids proches (blocs), pour que les deux lots
  partent avec le même poids moyen.
- **Conditions identiques** : même logement, même eau à volonté, même soins ; seule la ration diffère.
- **Durée** : 14 jours d'adaptation (transition progressive sur 7 jours), puis **60 à 90 jours de mesure**.
- **Saison** : noter la saison (dans l'application : module Saisons). Un second essai en saison sèche chaude est
  recommandé, les besoins et la disponibilité des aliments y changent.

## 4. Nombre d'animaux

Le nombre d'animaux dépend de l'écart de GMD que l'on veut pouvoir détecter et de la variabilité entre animaux. Avec
une variabilité (écart-type) de l'ordre de 35 g/j, à confirmer par le statisticien, un risque d'erreur de 5 % et une
puissance de 80 % :

| Écart de GMD à détecter | Animaux par lot |
|---|---|
| 40 g/j | environ 12 à 15 |
| 30 g/j | environ 22 |
| 25 g/j | environ 31 |

Avec 15 animaux par lot, l'essai pilote détectera un écart important ; un écart plus fin demandera un essai plus grand.

## 5. Avant le démarrage : les données de la ration

1. **Analyses des aliments** au laboratoire (au minimum matière sèche, protéines/MAT, minéraux), saisies dans
   l'application avec leur source.
2. **Référence des besoins** des animaux (source citée) saisie et **validée par le zootechnicien**.
3. **Prix d'achat** réels des aliments saisis par l'éleveur (et prix habituels de la saison).
4. Calcul de la ration, puis **validation par le zootechnicien** dans l'application. Seule une formule validée peut
   devenir une ration distribuée.

## 6. Mesures

| Mesure | Fréquence | Qui | Dans l'application |
|---|---|---|---|
| Poids individuel (à jeun, le matin, même balance) | J0, puis tous les 14 jours, et à la fin (double pesée à J0 et en fin d'essai) | Technicien d'élevage | Séance de pesée (aussi hors ligne) |
| Quantités distribuées par lot | Chaque jour | Éleveur ou technicien | Historique des rations → Distributions |
| Refus (restes) pesés | Chaque jour | Éleveur ou technicien | Quantité consommée = distribuée − refus |
| Prix des aliments achetés | À chaque achat | Éleveur | Prix des ingrédients |
| Santé (troubles, soins, mortalité) | Chaque jour | Vétérinaire, éleveur | Observations « état de santé » |
| Conditions (températures, eau, événements) | Chaque jour | Technicien | Observations |

## 7. Indicateurs et grille de résultats

| Indicateur | Lot témoin | Lot essai | Écart |
|---|---|---|---|
| Poids initial moyen (kg) | | | |
| Poids final moyen (kg) | | | |
| GMD moyen (g/j) | | | |
| Matière sèche consommée (kg/animal/jour) | | | |
| Indice de consommation (kg MS / kg de gain) | | | |
| Coût alimentaire (FCFA/animal/jour) | | | |
| **Coût alimentaire par kg de gain (FCFA)** | | | |
| Refus moyens (% du distribué) | | | |
| Animaux malades / soignés / morts | | | |

L'application fournit directement les pesées, le GMD par animal et par lot, les quantités calculées, distribuées et
consommées, les coûts, et l'export des pesées (CSV) pour l'analyse.

## 8. Analyse

- Comparer les GMD des deux lots en tenant compte du poids initial (analyse de covariance), par le statisticien.
- Comparer le coût par kg de gain et l'indice de consommation.
- Décrire la santé et l'appétence.
- Noter les difficultés d'utilisation de l'outil (saisies, réseau, compréhension).

## 9. Arrêt et bien-être animal

Le vétérinaire peut retirer un animal de l'essai à tout moment. La ration d'essai est suspendue en cas de baisse
marquée et durable de la consommation ou de trouble de santé lié à l'alimentation (seuils à définir avec le
vétérinaire). Tout retrait est noté avec son motif.

## 10. Rôles

| Rôle | Responsabilités | Rôle dans l'application |
|---|---|---|
| Éleveur / propriétaire | Animaux, distribution, achats | Propriétaire de l'exploitation |
| Technicien d'élevage | Pesées, distributions, refus, observations | Technicien d'élevage |
| Nutritionniste / zootechnicien | Références, validation de la ration, interprétation | Nutritionniste / zootechnicien |
| Vétérinaire | Santé, critères d'arrêt | Vétérinaire |
| Statisticien | Effectifs, tirage au sort, analyse | — |
| Équipe Ndeyam AI | Accompagnement, données, rapport | Administrateur |

## 11. Calendrier indicatif

| Semaine | Étape |
|---|---|
| S−4 à S−2 | Partenaires, site, analyses d'aliments, saisie et validation des données |
| S−2 à S0 | Achat des animaux, préparation sanitaire, tirage au sort, adaptation |
| S0 | Début des mesures (pesée J0) |
| S2, S4, S6, S8… | Pesées tous les 14 jours |
| S8 à S12 | Fin de l'essai (double pesée) |
| Fin + 4 semaines | Analyse et rapport, partagé avec les partenaires |

## 12. Limites

Un seul site et une seule saison : les résultats vaudront pour ce profil d'animaux, ces aliments et cette période.
Ils ne prouvent pas à eux seuls la validité de l'outil pour d'autres races, d'autres âges ou la saison chaude, qui
demanderont d'autres essais.

## 13. Postes de dépense à prévoir

Animaux, aliments des deux lots, analyses de laboratoire, soins vétérinaires, balance (et étalonnage), main-d'œuvre
du technicien, déplacements, analyse statistique.
