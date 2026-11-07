# NDEYAM AI

Plateforme AgriTech de gestion d'élevage et de formulation alimentaire destinée aux éleveurs
et aux professionnels de l'élevage au Sénégal et en Afrique de l'Ouest.
Première espèce prise en charge : **ovins**. L'architecture prévoit les caprins et bovins.

> **Statut : prototype fonctionnel complet (v0.1.0)** — les 11 modules du cahier des charges sont livrés et
> vérifiés de bout en bout. Aucune fonctionnalité n'est présentée comme scientifiquement validée : les résultats du
> moteur sont des estimations mathématiques tant qu'un expert ne les a pas validés, et **aucune donnée
> nutritionnelle de référence n'est fournie** (collecte en cours). Ce qui reste partiel ou à faire est signalé dans
> [Couverture, limites et évolutions](docs/limites-et-evolutions.md).

## Avancement

| Étape | Contenu | État |
|---|---|---|
| 1 | Initialisation (backend, frontend, base, outillage, documentation) | ✅ Terminée |
| 2 | Modèles de données et migrations | ✅ Terminée |
| 3 | Authentification et rôles | ✅ Terminée |
| 4 | API métier | ✅ Terminée |
| 5 | Croissance et alertes | ✅ Terminée |
| 6 | Moteur nutritionnel (PuLP) | ✅ Terminée |
| 7 | Frontend : animaux, croissance, tableau de bord, alertes | ✅ Terminée |
| 8 | Frontend : ingrédients, références, formulation, rations, traçabilité | ✅ Terminée |
| 9 | Base documentaire RAG | ✅ Terminée |
| 10 | Assistant IA | ✅ Terminée |
| 11 | Intégration, vérification de bout en bout, jeu DEMO | ✅ Terminée |
| 12 | Documentation finale | ✅ Terminée |

## Pile technique

| Couche | Technologies |
|---|---|
| Backend | Python 3.12, Django 5.2 LTS, Django REST Framework 3.16, SimpleJWT, drf-spectacular |
| Base de données | PostgreSQL 18 (pgvector non requis) |
| Calcul | PuLP 3 (solveur CBC intégré), NumPy, SciPy |
| IA | Interface `LLMProvider` : Claude (Anthropic), API compatibles OpenAI, Ollama |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, React Router, TanStack Query, Recharts — identité « Indigo & Mil » |
| Tests | pytest + pytest-django ; Vitest + Testing Library |

## Démarrage rapide

Guides détaillés : [Windows](docs/installation-windows.md) · [Linux](docs/installation-linux.md)

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate            # Linux : source .venv/bin/activate
pip install -r requirements-dev.txt
python scripts/init_db.py         # crée le rôle et la base « ndeyamai », génère .env
python manage.py migrate
python manage.py createsuperuser  # compte administrateur
python manage.py load_demo_data   # facultatif : jeu de démonstration fictif (DEMO)
python manage.py runserver        # http://localhost:8000

# Frontend (second terminal)
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

| URL | Description |
|---|---|
| http://localhost:5173 | Application |
| http://localhost:8000/api/docs/ | Documentation interactive Swagger |
| http://localhost:8000/api/redoc/ | Documentation ReDoc |
| http://localhost:8000/admin/ | Administration Django |

## Tests

```bash
cd backend
python -m pytest                      # 455 tests ; nécessite PostgreSQL (base de test temporaire)
cd ../frontend
npm test && npm run typecheck && npm run lint && npm run build   # 75 tests
```

## Structure

```
backend/   API Django : config, core, accounts, governance, farms, animals, nutrition,
           formulations, feeding, growth, alerts, knowledge_base, assistant
frontend/  Application React
docs/      Guides, documentation API, architecture, décisions techniques, journal des étapes
```

## Documentation

- **[Couverture du cahier des charges, limites et évolutions](docs/limites-et-evolutions.md)**
- [Installation Windows](docs/installation-windows.md)
- [Installation Linux](docs/installation-linux.md)
- [Guide utilisateur](docs/guide-utilisateur.md)
- [Guide administrateur et expert](docs/guide-administrateur.md)
- [Documentation de l'API](docs/api.md)
- [Guide d'importation des données](docs/import-donnees.md)
- [Moteur de formulation](docs/moteur-formulation.md)
- [Architecture IA](docs/architecture-ia.md)
- [Schéma de la base de données](docs/schema-base-donnees.md)
- [Identité visuelle](docs/identite-visuelle.md)
- [Décisions techniques](docs/decisions-techniques.md)
- [Journal des étapes](docs/journal-etapes.md)
- [Jeu de données de démonstration](docs/donnees-demo.md) — `python manage.py load_demo_data`
- Fichiers de configuration : [`backend/.env.example`](backend/.env.example), [`frontend/.env.example`](frontend/.env.example)
- Schéma OpenAPI : [`docs/openapi.yaml`](docs/openapi.yaml) (et Swagger sur `/api/docs/`)

## Règles du projet

- Aucune donnée nutritionnelle inventée ; toute valeur de référence porte une source et un statut de validation.
- Les données de démonstration sont marquées **DEMO** et ne sont jamais utilisées pour une formulation réelle.
- Aucune clé API dans le code source : tout passe par `backend/.env`.
- Le LLM n'effectue aucun calcul nutritionnel : il explique les résultats du moteur Python.
