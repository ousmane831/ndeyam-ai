# Guide d'importation des données

Les imports CSV permettent de charger des données existantes sans saisie manuelle.
Les modèles vides (en-têtes uniquement) se trouvent dans [`backend/templates/csv/`](../backend/templates/csv/).

## Règles communes

- Séparateur `;` ou `,` (détecté automatiquement) ; encodage UTF-8 (recommandé) ou Windows-1252.
- Nombres : virgule ou point décimal (`28,5` ou `28.5`).
- Taille maximale : 5 Mo, 20 000 lignes.
- Chaque import est tracé dans l'historique des importations (`/api/v1/import-batches/`) avec le nombre de lignes
  créées, mises à jour et en erreur, et le **numéro de chaque ligne en erreur** avec la raison.
- Les lignes valides sont importées même si d'autres sont en erreur ; corrigez puis réimportez les lignes rejetées.

## 1. Animaux (éleveurs)

`POST /api/v1/animals/import/` — formulaire `multipart` : `farm` (identifiant de l'exploitation), `file`.
Réservé au propriétaire ou au gestionnaire de l'exploitation.

| Colonne | Obligatoire | Format / valeurs |
|---|---|---|
| `numero` | oui | Numéro ou boucle, unique dans l'exploitation |
| `sexe` | oui | `M`, `F`, `mâle`, `femelle` |
| `espece` | non | Code d'espèce active (défaut `OVIN`) |
| `nom` | non | Texte |
| `race` | non | Nom exact d'une race de l'espèce (ex. `Touabire`) |
| `date_naissance` | non | `AAAA-MM-JJ` ou `JJ/MM/AAAA` |
| `age_estime_mois` | non | Nombre ; exclusif de `date_naissance` (la date est alors marquée « estimée ») |
| `poids_initial_kg` | non | Nombre > 0 |
| `categorie`, `stade` | non | Code ou nom (ex. `BREBIS`, `Lactation`) |
| `lot` | non | Nom du lot ; créé automatiquement s'il n'existe pas |
| `observations` | non | Texte |

Chaque ligne subit exactement les mêmes contrôles que la saisie manuelle. Un numéro déjà présent n'est jamais écrasé.

## 2. Compositions nutritionnelles (experts et administrateurs)

`POST /api/v1/compositions/import/` — formulaire `multipart` : `file`, `source` (identifiant de la source documentaire,
**obligatoire**), `is_demo` (`true` pour un jeu de démonstration).

| Colonne | Obligatoire | Format / valeurs |
|---|---|---|
| `ingredient` | oui | Nom de l'ingrédient du catalogue commun (créé s'il n'existe pas) |
| `categorie` | si nouvel ingrédient | Code : `CEREALES`, `SOUS_PRODUITS_CEREALIERS`, `TOURTEAUX`, `FOURRAGES`, `RESIDUS_CULTURE`, `SOURCES_MINERALES`, `COMPLEMENTS`, `AUTRES` |
| `nutriment` | oui | Code : `MS`, `MAT`, `MG`, `MM`, `CB`, `NDF`, `ADF`, `CA`, `P`, ou un code propre au système (`UFL`, `UFV`, `PDI`, `EM`, `PM`) |
| `systeme` | si nutriment de système | `INRA`, `NRC` ; vide pour un nutriment universel |
| `valeur` | oui | Nombre ≥ 0, dans l'unité du nutriment (voir ci-dessous). **Cellule vide = valeur inconnue, ligne ignorée** |
| `date_reference` | non | `AAAA-MM-JJ` |
| `methode`, `origine` | non | Méthode d'analyse, origine de l'échantillon |

### Unités attendues

| Nutriment | Unité |
|---|---|
| `MS` (matière sèche) | g/kg de produit **brut** (entre 0 et 1000) |
| Tous les autres | par kg de **matière sèche** : g/kg MS, UFL/kg MS, Mcal/kg MS… |

Consultez `GET /api/v1/nutrients/` pour la liste exacte des codes et unités.

### Garanties

- **Tout est importé en BROUILLON.** Un import ne valide jamais une donnée : un expert doit la valider ensuite.
- Une valeur déjà **validée** n'est jamais modifiée par un import (la ligne est signalée en erreur).
- Une source DEMO ne peut alimenter que des données DEMO ; un ingrédient DEMO et un ingrédient réel ne se mélangent pas.
- Aucune valeur n'est complétée ni remplacée par zéro : une cellule vide reste « inconnue ».

## 3. Exports CSV

| Données | Route |
|---|---|
| Animaux (mêmes filtres que la liste) | `GET /api/v1/animals/export/` |
| Compositions des ingrédients visibles | `GET /api/v1/ingredients/export/` |
| Historique alimentaire | `GET /api/v1/feeding-records/export/` |

Les exports utilisent le séparateur `;` et l'encodage UTF-8 avec BOM : ils s'ouvrent directement dans Excel.

## 4. Après l'import : validation

1. Vérifier les valeurs importées (`GET /api/v1/compositions/?status=DRAFT&source=<id>`).
2. Les soumettre (`POST /api/v1/compositions/{id}/submit/`) ou les valider directement en tant qu'expert
   (`POST /api/v1/compositions/{id}/validate/`).
3. Seules les valeurs **validées et non DEMO** sont utilisées par l'analyse des rations et, à l'étape 6, par le moteur
   de formulation.
