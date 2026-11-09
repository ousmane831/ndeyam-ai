# Identité visuelle — « Indigo & Mil »

Référence pour toute nouvelle page ou composant. Les valeurs sont définies une seule fois, dans
`frontend/src/index.css` (jetons Tailwind) et `frontend/src/features/charts/theme.ts` (graphiques).

## Intention

Un outil sérieux et traçable, ancré dans l'élevage sénégalais, jamais « gadget IA ». Chaque motif encode une
information ; aucun n'est décoratif.

| Élément | Origine | Rôle |
|---|---|---|
| **Indigo** | Teinture indigo de Kaolack et Dakar | Structure, navigation, actions principales |
| **Mil** | Céréale qui nourrit hommes et bêtes | Accent, repères, numéros de boucle, dernier point d'une courbe |
| **Acacia** (vert) | Végétation du Sahel | **Réservé** à validé / respecté / croissance |
| **Bande tissée** | Pagnes manjak | Signature, une seule par écran (haut du menu, écran de connexion) |
| **Tampon** | Visa du technicien sur le cahier d'élevage | Statuts de validation et de formule |
| **Boucle** | Boucle auriculaire d'identification | Numéro de chaque animal |
| **Symbole** | Tête de bélier Ladoum aux cornes enroulées | Logo, favicon |

## Couleurs (jetons)

| Jeton | Valeur | Usage |
|---|---|---|
| `brand-900` / `brand-800` | `#141D3A` / `#1D2B53` | Menu latéral, boutons principaux |
| `brand-600` / `brand-700` | `#2E4482` / `#25386D` | Liens, éléments actifs |
| `mil-400` / `mil-300` | `#E0A72E` / `#E9BD52` | Accent, boucle, onglet actif |
| `acacia-600` | `#5D7A3A` | Validé, respecté, courbes de croissance |
| `slate-*` | gris bleutés | Textes, bordures, fonds (remplacent le gris par défaut) |
| `red-*` | — | Refus, erreurs, actions destructrices |

Règles : le vert n'est jamais décoratif ; le jaune mil n'est jamais utilisé pour un avertissement de danger ;
le statut **DEMO** utilise toujours le motif hachuré `demo-hatch`, distinct de tous les autres statuts.

## Typographie

| Rôle | Police | Où |
|---|---|---|
| Titres, chiffres clés | **Bricolage Grotesque** | `font-display` : titres de page, en-têtes de cartes, indicateurs |
| Interface et texte | **Atkinson Hyperlegible Next** | `font-sans` (par défaut) : conçue pour la lisibilité ; zéro barré |
| Identifiants, en-têtes de tableaux | **IBM Plex Mono** | `font-mono` : boucles, tampons, axes de graphiques |

Les chiffres des tableaux sont alignés (`tabular-nums`). Taille minimale : 12 px pour tout texte fonctionnel,
13 px pour les mentions ; contraste ≥ 4,5:1 (texte secondaire `slate-500`, jamais `slate-400`).

## Composants de signature

| Composant | Fichier | Règle |
|---|---|---|
| `Logo`, `Wordmark` | `components/ui/Logo.tsx` | Symbole sur carré mil ; « NDEYAM » + « AI » discret |
| `Stamp` | `components/ui/Feedback.tsx` | Un mot visible ; libellé complet au survol et pour les lecteurs d'écran |
| `FormulaStatus` | `features/formulation/FormulaStatus.tsx` | Statut de formule en tampon (+ tampon DEMO) |
| `AnimalTag` | `components/ui/Feedback.tsx` | Numéro d'animal en forme de boucle |
| `Badge` | `components/ui/Feedback.tsx` | `brand` = état positif (acacia) ; `indigo` = rôle / appartenance |
| `AssistantLauncher` | `features/assistant/AssistantLauncher.tsx` | Bouton flottant bas droite au symbole du bélier ; panneau 400 px (plein écran sur téléphone) ; guide et glossaire si l'assistant n'est pas activé |
| `TodayTasks` | `features/dashboard/TodayTasks.tsx` | Tâches du jour : une ligne, une action directe ; mil = urgent, indigo = à suivre |

**Tampon ou pastille ?** Le *tampon* (`Stamp`) porte un statut de **validation** (formule, référence, composition,
document) : c'est une décision tracée. La *pastille* (`Badge`) porte un **état** courant (présent, actif, respecté,
rôle). La bande tissée apparaît une seule fois par écran (haut du menu ou écran de connexion).

## Graphiques

Segments droits entre les mesures (rien n'est dessiné entre deux pesées) ; dernier point en mil ; graduations
régulières (`niceTicks`) ; nombres au format français ; axes en IBM Plex Mono.

## Formes

Coins discrets (`rounded-md`, 6 px), bordures plutôt qu'ombres, pas de dégradé décoratif. Les cartes ne portent
une bordure que pour séparer un bloc ; les indicateurs restent sobres.
