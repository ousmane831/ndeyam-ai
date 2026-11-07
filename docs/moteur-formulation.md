# Moteur de formulation des aliments

Le moteur calcule une ration à partir des **seules données validées** : référence nutritionnelle, compositions
des ingrédients, contraintes d'incorporation. Il ne fabrique aucune valeur. Son résultat est une
**estimation mathématique** tant qu'un expert ne l'a pas vérifiée.

Le LLM de l'assistant n'effectue aucun calcul : il lit et explique les résultats enregistrés par ce moteur
(outil `get_formula_result`, voir [architecture-ia.md](architecture-ia.md)).

## 1. Architecture

```
POST /api/v1/formulas/calculate/
        │
        ▼
formulations/engine_service.py   (Django : sélection stricte des données)
  ├─ choix de la référence VALIDÉE la plus spécifique (espèce, race, catégorie, stade, objectif, poids, âge)
  ├─ besoins de la référence
  ├─ compositions VALIDÉES, nutriments universels + système de la référence uniquement
  ├─ prix de l'exploitation (ou saisis pour le calcul), disponibilités
  └─ contraintes d'incorporation VALIDÉES
        │  Problem (objet Python pur)
        ▼
formulations/engine/              (Python pur, sans Django)
  ├─ checks.py   refus motivés et exclusions d'ingrédients
  ├─ solver.py   programme linéaire PuLP / CBC + diagnostic d'infaisabilité
  └─ verify.py   recalcul indépendant des apports et des contraintes
        │  FormulationResult
        ▼
FeedFormula (statut ESTIMATED / INFEASIBLE / REFUSED) + ingrédients + instantané complet
```

## 2. Modèle mathématique

Variables : `x_i ≥ 0`, kg de matière sèche de l'ingrédient *i* par animal et par jour.

| Contrainte | Forme |
|---|---|
| Ingestion de MS (référence) | `MSmin ≤ Σ x_i ≤ MSmax` |
| Besoin journalier | `min ≤ Σ x_i · c_ij ≤ max` (c_ij : teneur par kg MS) |
| Teneur de la ration | `min · Σ x_i ≤ Σ x_i · c_ij ≤ max · Σ x_i` |
| Incorporation (expert) | `min% · Σ x ≤ Σ_{i∈S} x_i ≤ max% · Σ x` |
| Disponibilité | `x_i ≤ stock_i / (animaux × jours) × MS_i` |

| Mode | Objectif |
|---|---|
| **Économique** | minimiser `Σ prix_MS_i · x_i` (prix par kg brut converti en prix par kg de MS) |
| **Équilibré** | minimiser `Σ |apport_j − cible_j| / cible_j`, puis le coût (poids 10⁻³). Cible = valeur « cible » de la référence, sinon milieu de [min, max] |

Toutes les conversions brut ↔ MS utilisent la teneur en MS **validée** de chaque ingrédient.

## 3. Règles de sécurité

| Règle du cahier des charges | Mise en œuvre |
|---|---|
| Ne jamais inventer une composition | Valeur absente = inconnue. Un ingrédient sans valeur pour un nutriment contraint est **exclu** (jamais compté à zéro) |
| Ne jamais inventer les besoins | Sans référence validée correspondante : **refus** |
| Refuser si données insuffisantes | Refus si aucun besoin, ingestion de MS non renseignée, aucun ingrédient utilisable |
| Ne jamais masquer une donnée manquante | Ingrédients exclus listés avec leurs raisons ; apports « incomplets » signalés |
| Ne jamais présenter une ration non conforme comme équilibrée | Recalcul indépendant (`verify.py`) : une contrainte non vérifiée fait passer le résultat en INFEASIBLE |
| Signaler les contraintes impossibles | Programme élastique : contraintes à relâcher et écart chiffré (« il manque environ 100 g/jour ») |
| Distinguer estimation et recommandation | Statut ESTIMATED + avertissement ; seule la validation d'un expert donne le statut VALIDATED |
| Validation humaine | Soumission → expert invité sur l'exploitation (ou administrateur) → validée / rejetée avec commentaire |
| Données DEMO | Exploitation réelle : données DEMO exclues. Exploitation DEMO : données DEMO uniquement, formule marquée DEMO, non validable |
| Pas de mélange de systèmes | Seuls les nutriments universels et ceux du système de la référence sont chargés |

## 4. Appel de l'API

```json
POST /api/v1/formulas/calculate/
{
  "farm": 1,
  "name": "Embouche lot A",
  "mode": "ECONOMIC",                  // ou "BALANCED"
  "animal": 12,                        // facultatif : préremplit espèce, race, catégorie, stade, poids, âge
  "species": 1,                        // obligatoire sans animal
  "reference": null,                   // facultatif : sinon choix automatique de la référence validée
  "category": 4, "physiological_stage": 3, "objective": 3,
  "animal_weight_kg": "32.5", "animal_age_months": "8",
  "ingredients": [
    {"ingredient": 5},
    {"ingredient": 7, "price_per_kg_as_fed": "180"},
    {"ingredient": 9, "available_kg_as_fed": "300"}
  ],
  "number_of_animals": 20, "duration_days": 30,   // requis si une disponibilité est indiquée
  "save": true                                    // false : calcul sans enregistrement
}
```

Réponse : `formula` (enregistrée) et `result` :

| Champ | Contenu |
|---|---|
| `status` | `ESTIMATED`, `INFEASIBLE` ou `REFUSED` |
| `items` | pour chaque ingrédient : % MS, % brut, kg MS et kg brut par animal et par jour, prix, coût |
| `cost_per_day`, `cost_per_kg_as_fed` | coût total (vide si un prix manque) |
| `nutrients` | apports estimés (par jour et par kg de MS) comparés aux besoins de référence |
| `constraints` | chaque contrainte avec sa valeur, ses bornes et son statut (`ok`, `below`, `above`) |
| `infeasibility` | contraintes bloquantes et écart chiffré |
| `refusal_reasons`, `excluded_ingredients`, `warnings` | raisons et limites, jamais masquées |
| `sources`, `reference` | sources utilisées et référence retenue |
| `disclaimer` | rappel du statut d'estimation |

## 5. Tests

- `formulations/tests/test_engine.py` : moteur seul, jeux de données contrôlés dont la solution est calculée à la main
  (mode économique, conversions MS, contraintes max et de teneur, incorporation, disponibilité, infaisabilité
  diagnostiquée, mode équilibré, refus et exclusions).
- `formulations/tests/test_calculate_api.py` : chaîne complète (référence brouillon ignorée, compositions brouillon
  ignorées, systèmes non mélangés, isolation DEMO, diagnostic enregistré, contraintes expertes, disponibilités,
  préremplissage depuis l'animal, isolation des exploitations, validation par un expert).

## 6. Vérification indépendante (étape 11)

En plus de `verify.py`, les résultats ont été comparés en conditions réelles à un second solveur indépendant
(SciPy `linprog` / HiGHS) : coût optimal identique dans tous les cas testés (dont 8 jeux de prix aléatoires),
écart d'infaisabilité identique au calcul indépendant. Détails : [journal des étapes](journal-etapes.md).

## 7. Limites connues

- Le diagnostic d'infaisabilité propose **un** ensemble minimal de contraintes à relâcher (pondéré par l'écart relatif) ;
  d'autres combinaisons peuvent exister.
- Les besoins sont exprimés par animal et par jour ou en teneur de la ration : les rapports entre nutriments (ex. Ca/P)
  ne sont pas encore pris en charge.
- PuLP est figé en version 3 : le solveur intégré `PULP_CBC_CMD` est annoncé obsolète pour PuLP 4 ; la migration vers
  `COIN_CMD` sera faite lors du passage à PuLP 4.
- Tant qu'aucune référence ni composition n'est validée en base, tout calcul réel est refusé (comportement voulu).
