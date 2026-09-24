#!/bin/bash
# Réinstalle les dépendances et redémarre le backend après un déploiement.
#
# Appelé automatiquement par le workflow GitHub Actions
# ".github/workflows/deploy-backend.yml" juste après la synchronisation
# des fichiers sur le serveur cPanel. Peut aussi être lancé à la main :
#
#   ssh <user>@<host> -p <port>
#   cd .../BACKEND
#   bash scripts/restart_backend.sh
#
# IMPORTANT : démarre le process avec "python main.py" (pas "uvicorn
# main:app" directement), car le cron de surveillance existant
# (*/5 * * * * pgrep -f "main.py" || ...) cherche un process nommé
# "main.py". Le démarrer autrement ferait croire au cron que le backend
# est arrêté et il en relancerait un second, en conflit sur le port.
#
# Ne touche jamais à .env ni aux bases .db (gérés à la main sur le
# serveur, exclus du déploiement).

set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$APP_DIR/venv"
LOG_DIR="$APP_DIR/logs"
LOG="$LOG_DIR/backend.log"

cd "$APP_DIR"
mkdir -p "$LOG_DIR"

# Lit le PORT depuis .env pour le test de santé (main.py lit .env lui-même
# au démarrage ; ceci ne sert qu'à vérifier que ça répond).
PORT="$(grep -E '^PORT=' .env 2>/dev/null | cut -d= -f2)"
PORT="${PORT:-8000}"

PYBIN="python3"
if [ -x /usr/bin/python3.12 ]; then
    PYBIN="/usr/bin/python3.12"
fi

if [ ! -f "$VENV/bin/activate" ]; then
    echo "[deploy] Aucun venv trouvé, création avec $PYBIN..."
    "$PYBIN" -m venv "$VENV"
fi

echo "[deploy] Installation des dépendances..."
source "$VENV/bin/activate"
pip install -r requirements.txt --quiet
deactivate

echo "[deploy] Arrêt de l'instance en cours..."
pkill -f "main.py" 2>/dev/null || true
sleep 1

echo "[deploy] Démarrage de la nouvelle instance (python main.py)..."
source "$VENV/bin/activate"
nohup python main.py >> "$LOG" 2>&1 &
disown
deactivate

sleep 3

if curl -s -o /dev/null -m 5 "http://127.0.0.1:$PORT/"; then
    echo "[deploy] Backend redémarré avec succès."
else
    echo "[deploy] ECHEC du redémarrage, voir $LOG"
    exit 1
fi
