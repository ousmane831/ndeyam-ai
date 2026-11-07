# Jeu de données de démonstration (DEMO)

Ce jeu sert à présenter NDEYAM AI avec des écrans remplis. **Toutes ses valeurs nutritionnelles sont fictives** :
elles ne viennent d'aucune table publiée, ne sont jamais validées et ne doivent pas servir à nourrir des animaux.

## Commandes (dossier `backend`)

| Action | Commande |
|---|---|
| Charger | `.venv\Scripts\python manage.py load_demo_data` |
| Recharger (supprime d'abord l'ancien jeu DEMO) | `… load_demo_data --reset` |
| Supprimer | `… load_demo_data --remove` |
| Choisir le mot de passe | `--password <mot de passe>` ou variable d'environnement `DEMO_PASSWORD` |

Sans mot de passe fourni, un mot de passe aléatoire est généré et **affiché une seule fois**. Aucun mot de passe
n'est écrit dans le code. La commande refuse de s'exécuter si `DEBUG=False`, sauf avec `--allow-production`.
Elle refuse un second chargement sans `--reset` (pas de doublons).

`--reset` et `--remove` ne suppriment que : les comptes du domaine `demo.ndeyam.example`, les exploitations
`is_demo` dont le nom commence par `[DEMO]`, et le référentiel `is_demo` créé par ces comptes.
Aucune donnée réelle n'est touchée.

## Comptes

| Adresse | Rôle | Accès |
|---|---|---|
| `eleveur@demo.ndeyam.example` | Éleveur (Fatou Diop, DEMO) | [DEMO] Bergerie de Thiès |
| `eleveur2@demo.ndeyam.example` | Éleveur (Ibrahima Ndiaye, DEMO) | [DEMO] Élevage de Kaolack — illustre l'isolation des données |
| `expert@demo.ndeyam.example` | Expert (Aminata Sow, DEMO) | Invité sur Thiès ; référentiel DEMO |

`demo.ndeyam.example` est un domaine réservé (RFC 2606) : aucun e-mail réel ne peut être envoyé.

## Contenu

| Élément | Contenu |
|---|---|
| Exploitations | 2, marquées DEMO |
| Lots | Embouche Tabaski (6 béliers), Brebis reproductrices (5), Agneaux 2026 (3) |
| Animaux | 20 (Ladoum, Touabire, Peul-Peul, Djallonké, Waralé), dont 1 vendu |
| Pesées | 83 sur 90 jours (balance, ruban, une estimation visuelle), générées sans aléatoire |
| Cas d'alerte volontaires | Brebis sans date de naissance ; agneau jamais pesé depuis 40 jours ; formule en attente |
| Référentiel | 1 source DEMO, 7 ingrédients `[DEMO]` (42 valeurs fictives), 2 références « valeurs fictives », 4 contraintes d'incorporation |
| Prix | Un prix fictif par ingrédient et par exploitation |
| Formules | Économique (en attente de vérification), équilibrée, brebis à l'entretien, et un **exemple impossible** (paille seule) avec son diagnostic |
| Rations | 1 ration en cours sur le lot d'embouche ; 30 distributions avec coût estimé ; consommation mesurée 4 jours seulement (jamais supposée) |
| Document | 1 fiche fictive de 2 pages, indexée, en brouillon : visible des experts en prévisualisation, absente des recherches des éleveurs |
| Alertes | Calculées par les règles réelles au chargement |

## Garanties

- Une donnée DEMO ne peut pas être validée : l'API le refuse et PostgreSQL l'interdit (contrainte `CHECK`).
- Une exploitation réelle exclut tout ingrédient, toute composition et toute référence DEMO du moteur.
- Une exploitation DEMO n'utilise que des données DEMO ; ses formules portent l'avertissement
  « Calcul de DÉMONSTRATION réalisé avec des données fictives » et ne peuvent pas être validées.
- Toute saisie faite dans une exploitation DEMO est automatiquement marquée DEMO.
- Tests : `core/tests/test_demo_data.py`.
