# Installation sous Windows

Testé sous Windows 11 avec Python 3.12.10, Node.js 24, PostgreSQL 18.6. Docker n'est pas nécessaire.

## 1. Prérequis

| Logiciel | Version minimale | Vérification |
|---|---|---|
| Python | 3.12 | `python --version` |
| Node.js | 20.19 (24 recommandé) | `node -v` |
| PostgreSQL | 15 (18 recommandé) | `psql --version` |
| Git | — | `git --version` |

> **Python du Microsoft Store :** il fonctionne, mais peut poser des problèmes de chemins.
> En cas de difficulté, installez Python depuis https://www.python.org/downloads/ en cochant
> « Add python.exe to PATH ».

Le service PostgreSQL doit être démarré (`services.msc` → `postgresql-x64-18`).

## 2. Backend

Dans PowerShell, depuis le dossier du projet :

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

Si PowerShell refuse d'activer l'environnement :
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### Base de données

```powershell
python scripts\init_db.py
```

Le script demande le mot de passe du compte administrateur PostgreSQL (`postgres`), **sans l'enregistrer**, puis :

- crée le rôle `ndeyamai` (avec le droit CREATEDB, nécessaire aux tests) et la base `ndeyamai` ;
- génère `backend\.env` avec un mot de passe aléatoire pour `ndeyamai` et une clé secrète Django.

Il ne modifie ni la configuration du serveur PostgreSQL ni les autres bases. Il peut être relancé sans risque.

**Alternative manuelle (pgAdmin ou psql) :**

```sql
CREATE ROLE ndeyamai WITH LOGIN CREATEDB PASSWORD 'mot-de-passe-solide';
CREATE DATABASE ndeyamai OWNER ndeyamai ENCODING 'UTF8' TEMPLATE template0;
```

puis copiez `.env.example` en `.env` et renseignez `DB_PASSWORD` et `DJANGO_SECRET_KEY`.

### Migrations et lancement

```powershell
python manage.py migrate
python manage.py createsuperuser     # compte administrateur de la plateforme
python manage.py runserver
```

Vérification : http://localhost:8000/api/v1/health/ doit renvoyer `"status": "ok"`.

Données de démonstration (facultatif) : `python manage.py load_demo_data` — voir [donnees-demo.md](donnees-demo.md).

## 3. Frontend

Dans un second terminal :

```powershell
cd frontend
npm install
npm run dev
```

Ouvrez http://localhost:5173. Le fichier `frontend\.env` est facultatif (voir `.env.example`).

## 4. Évaluation quotidienne des alertes (facultatif)

Les alertes sont recalculées après chaque pesée, chaque décision de validation et à la demande. Pour les rappels
liés au temps qui passe
(pesées, suivi alimentaire), planifiez la commande une fois par jour avec le Planificateur de tâches
(adaptez le chemin du projet) :

```powershell
$projet = "C:\Users\<vous>\Desktop\Ndeyam AI\backend"
schtasks /Create /SC DAILY /ST 06:00 /TN "NDEYAM AI - alertes" `
  /TR "`"$projet\.venv\Scripts\python.exe`" `"$projet\manage.py`" evaluate_alerts"
```

Exécution manuelle : `python manage.py evaluate_alerts`.

## 5. Tests

```powershell
cd backend
python -m pytest
cd ..\frontend
npm test; npm run typecheck; npm run lint
```

## Dépannage

| Symptôme | Cause probable |
|---|---|
| `fe_sendauth: no password supplied` | `DB_PASSWORD` vide dans `backend\.env` : relancez `scripts\init_db.py` |
| `permission denied to create database` (tests) | le rôle `ndeyamai` n'a pas CREATEDB : relancez `scripts\init_db.py` |
| Page d'état : « Impossible de joindre le serveur » | le backend Django n'est pas démarré sur le port 8000 |
| `ImproperlyConfigured: Set the DJANGO_SECRET_KEY` | fichier `backend\.env` absent |
| Page « Assistant non configuré » | normal sans `LLM_PROVIDER` : voir le [guide administrateur](guide-administrateur.md#7-assistant-ia) |
| « Calcul refusé » pour toute formule réelle | aucune référence ni composition validée : voir le [guide administrateur](guide-administrateur.md#3-constituer-le-référentiel-experts) |
| `load_demo_data` : « déjà chargé » | utilisez `--reset` pour recharger le jeu DEMO |
