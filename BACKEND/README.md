# 📊 MFWA MTI Dashboard - Backend API

Backend FastAPI pour le Media Trust Index Dashboard (Ghana).

**Status:** ✅ Production-ready

---

## 🎯 Quick Start

### 1️⃣ Installation

```bash
# Cloner le repo (ou copier les fichiers)
cd backend

# Créer virtual environment
python -m venv venv

# Activer (Windows)
venv\Scripts\activate

# Activer (Mac/Linux)
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### 2️⃣ Configuration

```bash
# Copier le template d'env
cp .env.example .env

# Éditer .env et ajouter:
# - KOBO_TOKEN (depuis https://kf.kobotoolbox.org/settings/account)
# - KOBO_FORM_UID (depuis Kobo Assets)
```

### 3️⃣ Lancer le serveur

```bash
# Development avec auto-reload
python main.py

# Production (Render)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Le serveur démarre sur `http://localhost:8000`

---

## 📚 Architecture

```
backend/
├── main.py              # Application FastAPI + routers
├── database.py          # Configuration SQLite/PostgreSQL
├── models.py            # Modèles SQLAlchemy (Outlet, Response, etc.)
├── schemas.py           # Schémas Pydantic (validation)
├── kobo_service.py      # Service Kobo Toolkit API
│
├── routers/             # Endpoints groupés par domaine
│   ├── __init__.py
│   ├── outlets.py       # CRUD outlets + analytics
│   ├── respondents.py   # CRUD respondents
│   └── dashboard.py     # Stats + Kobo sync
│
├── requirements.txt     # Dépendances Python
├── .env.example         # Template configuration
└── mfwa_mti.db         # SQLite database (auto-créée)
```

---

## 🗄️ Base de Données

### 4 Principales Tables

#### 1. `outlets` (Médias)
```
id              (Primary Key)
outlet_name     (Nom unique du média)
outlet_type     (Radio, TV, Online, Print)
region          (Région)
created_at      (Timestamp)
```

#### 2. `respondents` (Répondants)
```
id              (Primary Key)
outlet_id       (FK → outlets)
respondent_name (Nom du répondant)
respondent_role (Editor, Producer, etc.)
phone           (Contact)
created_at      (Timestamp)
```

#### 3. `responses` (Réponses Kobo)
```
id                      (Primary Key)
outlet_id               (FK → outlets)
respondent_id           (FK → respondents)
kobo_submission_id      (Unique ID from Kobo)
accuracy_score          (0-100)
verification_score      (0-100)
independence_score      (0-100)
fair_balanced_score     (0-100)
public_interest_score   (0-100)
corrections_score       (0-100)
raw_response_data       (JSON from Kobo)
created_at              (Timestamp)
```

#### 4. `mti_indices` (Scores MTI Calculés)
```
id                      (Primary Key)
outlet_id               (FK → outlets, Unique)
mti_score               (Weighted average 0-100)
accuracy_weight         (0.20)
verification_weight     (0.20)
independence_weight     (0.20)
fair_balanced_weight    (0.15)
public_interest_weight  (0.15)
corrections_weight      (0.10)
last_updated            (Timestamp)
```

---

## 🔌 API Endpoints

### Health Check
```
GET /health
→ {"status": "ok", "service": "MFWA MTI API"}
```

### Outlets

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/outlets` | GET | Lister tous les outlets |
| `/api/outlets/{id}` | GET | Détail d'un outlet |
| `/api/outlets` | POST | Créer un outlet |
| `/api/outlets/{id}` | PUT | Modifier un outlet |
| `/api/outlets/{id}` | DELETE | Supprimer un outlet |
| `/api/outlets/{id}/responses` | GET | Réponses d'un outlet |
| `/api/outlets/{id}/mti` | GET | Score MTI d'un outlet |
| `/api/outlets/region/{region}` | GET | Outlets par région |

### Respondents

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/respondents` | GET | Lister tous les respondents |
| `/api/respondents/{id}` | GET | Détail d'un respondent |
| `/api/respondents` | POST | Créer un respondent |
| `/api/respondents/{id}` | PUT | Modifier un respondent |
| `/api/respondents/{id}` | DELETE | Supprimer un respondent |
| `/api/respondents/outlet/{outlet_id}` | GET | Respondents d'un outlet |
| `/api/respondents/{id}/responses` | GET | Réponses d'un respondent |

### Dashboard

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/dashboard` | GET | Stats globales + top outlets |
| `/api/dashboard/dimensions` | GET | Scores moyens par dimension |
| `/api/dashboard/outlets-details` | GET | Details tous les outlets |
| `/api/dashboard/calculate-mti` | POST | Recalculer MTI pour tous |
| `/api/dashboard/sync-kobo` | POST | Syncer depuis Kobo |

---

## 🔄 Kobo Toolkit Integration

### Configuration

1. **Créer un compte Kobo** (https://kobotoolbox.org)
2. **Créer un formulaire** avec les questions MTI
3. **Récupérer le Token** depuis Settings → Account
4. **Copier le Form UID** depuis Assets

### Synchronisation

```bash
# Endpoint pour syncer les submissions
POST /api/dashboard/sync-kobo

# Réponse
{
  "status": "success",
  "submissions_synced": 5,
  "last_sync": "2026-05-21T10:30:00"
}
```

### Mapping des Réponses

Les réponses Kobo sont convertis en scores 0-100 :
```
strongly_agree  → 100
agree           → 75
neither         → 50
disagree        → 25
strongly_disagree → 0
```

---

## 📊 MTI Calculation

**Formula:**
```
MTI = (accuracy × 0.20) +
      (verification × 0.20) +
      (independence × 0.20) +
      (fair_balanced × 0.15) +
      (public_interest × 0.15) +
      (corrections × 0.10)
```

La formule est automatiquement appliquée lors de:
1. Chaque sync Kobo
2. Appel à `/api/dashboard/calculate-mti`

---

## 🚀 Deployment sur Render

### Prérequis
- Repo GitHub avec le code backend
- Compte Render (render.com)

### Étapes

1. **Créer une Web Service**
    - Connecter le repo GitHub
    - Runtime: Python 3.13

2. **Configuration**
   ```
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. **Variables d'Environnement**
    - `KOBO_TOKEN` = votre token Kobo
    - `KOBO_FORM_UID` = votre form UID
    - `FRONTEND_URL` = URL de votre frontend (Vercel)
    - `DATABASE_URL` = postgres://... (si PostgreSQL)

4. **Deploy**
    - Cliquer "Create Web Service"
    - Attendre le build (~2-3 min)
    - Récupérer l'URL (ex: https://mfwa-api.onrender.com)

### CORS pour Production

```python
# main.py sera automatiquement mis à jour
allow_origins=[
    "https://votre-frontend.vercel.app",
    "https://mfwa-api.onrender.com",
]
```

---

## 🧪 Testing

### Tester un endpoint

```bash
# Santé du serveur
curl http://localhost:8000/health

# Lister les outlets
curl http://localhost:8000/api/outlets

# Créer un outlet
curl -X POST http://localhost:8000/api/outlets \
  -H "Content-Type: application/json" \
  -d '{"outlet_name":"CitiFM", "outlet_type":"Radio", "region":"Greater Accra"}'

# Syncer Kobo
curl -X POST http://localhost:8000/api/dashboard/sync-kobo
```

### Avec Python

```python
import requests

API = "http://localhost:8000"

# Lister outlets
resp = requests.get(f"{API}/api/outlets")
print(resp.json())

# Syncer Kobo
resp = requests.post(f"{API}/api/dashboard/sync-kobo")
print(resp.json())
```

---

## ⚙️ Configuration Avancée

### Utiliser PostgreSQL (Production)

```bash
# Installer la dépendance
pip install psycopg2-binary

# Dans .env
DATABASE_URL=postgresql://user:password@localhost:5432/mfwa_mti
```

### Logging

```python
# Dans main.py, ajouter:
import logging
logging.basicConfig(level=logging.INFO)
```

---

## 🐛 Troubleshooting

### Problème: "No module named 'routers'"
```
Solution: Assurez-vous que le dossier routers/ existe avec __init__.py
```

### Problème: "Kobo API timeout"
```
Solution: Vérifier KOBO_TOKEN dans .env et la connectivité internet
```

### Problème: "Port 8000 already in use"
```
Solution: Changer le port dans main.py:
uvicorn.run(..., port=8001)
```

### Problème: "CORS error"
```
Solution: Vérifier que FRONTEND_URL est dans allow_origins dans main.py
```

---

## 📝 Endpoints Référence Complète

### Outlets CRUD
```
GET    /api/outlets
POST   /api/outlets
GET    /api/outlets/{id}
PUT    /api/outlets/{id}
DELETE /api/outlets/{id}
GET    /api/outlets/{id}/responses
GET    /api/outlets/{id}/mti
GET    /api/outlets/region/{region}
```

### Respondents CRUD
```
GET    /api/respondents
POST   /api/respondents
GET    /api/respondents/{id}
PUT    /api/respondents/{id}
DELETE /api/respondents/{id}
GET    /api/respondents/outlet/{outlet_id}
GET    /api/respondents/{id}/responses
```

### Dashboard
```
GET    /api/dashboard
GET    /api/dashboard/dimensions
GET    /api/dashboard/outlets-details
POST   /api/dashboard/calculate-mti
POST   /api/dashboard/sync-kobo
```

### Santé
```
GET    /health
GET    /
```

---

## 📞 Support

Pour les questions:
1. Vérifier les logs: `tail -f *.log`
2. Tester l'API: http://localhost:8000/docs (Swagger UI)
3. Vérifier .env: Tous les tokens sont présents?

---

**Version:** 1.0.0  
**Dernière mise à jour:** 21 Mai 2026  
**Status:** ✅ Production Ready