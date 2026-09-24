# Déploiement automatique du backend sur cPanel (GitHub Actions)

Ce document explique comment mettre en place le déploiement automatique
du dossier `BACKEND/` vers le serveur cPanel à chaque push sur `main`.

Le workflow correspondant est `.github/workflows/deploy-backend.yml`.
Il ne touche jamais au frontend (`mti-dashboard/`).

## Comment ça marche

1. À chaque push sur `main` qui modifie `BACKEND/**`, GitHub Actions :
   - synchronise le contenu de `BACKEND/` vers le serveur via `rsync` sur SSH
     (en excluant `venv/`, `.env`, `*.db`, `__pycache__/`, `*.log` — ces
     fichiers restent gérés uniquement sur le serveur) ;
   - se connecte en SSH et exécute `BACKEND/scripts/restart_backend.sh`,
     qui réinstalle les dépendances dans le `venv` existant puis relance
     `uvicorn` sur le port 8000 (même logique que `watchdog.sh`, qui continue
     de tourner en cron toutes les 5 min comme filet de sécurité).
2. Le fichier `.env` du serveur (KOBO_TOKEN, DATABASE_URL, FRONTEND_URL...)
   n'est **jamais** écrasé ni géré par le workflow : il reste à modifier
   manuellement sur le serveur (`nano /home/<user>/BACKEND/.env`).

## 1. Générer une clé SSH dédiée au déploiement

Sur votre machine (pas besoin de réutiliser une clé existante) :

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f deploy_key -N ""
```

Cela crée deux fichiers : `deploy_key` (clé privée) et `deploy_key.pub`
(clé publique).

## 2. Autoriser la clé publique sur cPanel

Dans cPanel : **Sécurité (Security) → Accès SSH (SSH Access) → Gérer les
clés SSH (Manage SSH Keys)**

- **Import Key** → coller le contenu de `deploy_key.pub`.
- Une fois importée, cliquer sur **Authorize** en face de la clé pour
  l'ajouter à `~/.ssh/authorized_keys`.

Notez également, sur la même page ou dans **Détails du compte / Statistiques
générales**, le **port SSH** du serveur (souvent différent de 22 sur cPanel,
par exemple 21098 ou 2222).

## 3. Ajouter les secrets sur GitHub

Dans le dépôt `ininahazwe/media-trust` : **Settings → Secrets and variables
→ Actions → New repository secret**, ajouter :

| Secret | Valeur |
|---|---|
| `CPANEL_SSH_HOST` | nom d'hôte ou IP du serveur cPanel |
| `CPANEL_SSH_PORT` | port SSH (voir étape 2) |
| `CPANEL_SSH_USER` | utilisateur cPanel, ex. `dxtrmfwa` |
| `CPANEL_SSH_PRIVATE_KEY` | contenu complet de `deploy_key` (la clé **privée**, en entier, `-----BEGIN...` à `-----END...`) |
| `CPANEL_REMOTE_PATH` | chemin absolu du backend sur le serveur, ex. `/home/dxtrmfwa/BACKEND` |

Une fois les secrets ajoutés, supprimez `deploy_key` et `deploy_key.pub` de
votre machine locale (ou conservez-les en lieu sûr, hors du dépôt).

## 4. Vérifier que le serveur est prêt

Le workflow suppose que sur le serveur, dans `CPANEL_REMOTE_PATH` :

- un environnement virtuel existe déjà dans `venv/` (sinon le script le
  crée automatiquement au premier déploiement) ;
- `.env` est déjà présent et configuré (`KOBO_TOKEN`, `KOBO_BASE_URL`,
  `DATABASE_URL`, `FRONTEND_URL`) ;
- le cron du `watchdog.sh` existant peut rester en place tel quel, il sert
  de filet de sécurité entre deux déploiements.

## 5. Tester

- Poussez un commit modifiant un fichier dans `BACKEND/` sur `main`, ou
  déclenchez manuellement le workflow depuis l'onglet **Actions** →
  **Deploy Backend to cPanel** → **Run workflow**.
- Suivez l'exécution dans l'onglet Actions. Le job affiche les logs de
  `rsync` puis ceux de `restart_backend.sh`.
- Vérifiez ensuite `curl http://127.0.0.1:8000/health` sur le serveur (ou
  l'URL publique de l'API) et consultez `BACKEND/backend.log` en cas de
  souci.

## Sécurité

- La clé privée SSH ne doit **jamais** être committée dans le dépôt.
- `.env` reste exclu du déploiement : les secrets Kobo ne transitent jamais
  par GitHub.
- Le workflow ne s'exécute que sur `main` et seulement quand `BACKEND/**`
  change, pour ne pas interférer avec le déploiement du frontend
  (`mti-dashboard/`, généralement sur Vercel).
