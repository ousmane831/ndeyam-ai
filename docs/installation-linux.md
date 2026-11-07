# Installation sous Linux (Ubuntu / Debian)

## 1. Prérequis

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv postgresql git
# Node.js 24 (via nvm recommandé)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
nvm install 24
```

Démarrer PostgreSQL : `sudo systemctl enable --now postgresql`.

## 2. Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

### Base de données

Le script `scripts/init_db.py` se connecte en TCP avec un mot de passe. Sur une installation
Ubuntu par défaut, le compte `postgres` n'a pas de mot de passe ; deux options :

**Option A — script (après avoir défini un mot de passe pour `postgres`) :**

```bash
sudo -u postgres psql -c "\password postgres"
python scripts/init_db.py
```

**Option B — manuelle :**

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE ndeyamai WITH LOGIN CREATEDB PASSWORD 'mot-de-passe-solide';
CREATE DATABASE ndeyamai OWNER ndeyamai ENCODING 'UTF8' TEMPLATE template0;
SQL
cp .env.example .env
# renseigner DB_PASSWORD et DJANGO_SECRET_KEY, par exemple :
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### Migrations et lancement

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Vérification : http://localhost:8000/api/v1/health/ doit renvoyer `"status": "ok"`.

Données de démonstration (facultatif) : `python manage.py load_demo_data` — voir [donnees-demo.md](donnees-demo.md).

## 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Ouvrez http://localhost:5173. Le fichier `frontend/.env` est facultatif (voir `.env.example`).

## 4. Évaluation quotidienne des alertes (facultatif)

Les alertes sont recalculées après chaque pesée, chaque décision de validation et à la demande ; la commande
quotidienne couvre les rappels liés au temps qui passe.

```bash
# crontab -e : tous les jours à 6 h
0 6 * * * cd "/chemin/vers/Ndeyam AI/backend" && .venv/bin/python manage.py evaluate_alerts
```

## 5. Tests

```bash
cd backend
python -m pytest
cd ../frontend
npm test && npm run typecheck && npm run lint
```

## Dépannage

Voir le tableau de dépannage du [guide Windows](installation-windows.md#dépannage) : les causes sont identiques
(chemins mis à part).
