#!/bin/bash
# Watchdog: relance uvicorn (main:app) s'il n'écoute plus sur le port 8000.
# A lancer via cron toutes les 5 min + @reboot. Voir instructions en bas de fichier.

APP_DIR="/home/dxtrmfwa/BACKEND"
VENV="$APP_DIR/venv/bin/activate"
PORT=8000
LOG="$APP_DIR/backend.log"
WATCHDOG_LOG="$APP_DIR/watchdog.log"
LOCK="/tmp/mti_watchdog.lock"

# Evite les exécutions concurrentes si cron se chevauche
exec 200>"$LOCK"
flock -n 200 || exit 0

timestamp() { date "+%Y-%m-%d %H:%M:%S"; }

# Le process répond-il sur le port ?
if curl -s -o /dev/null -m 5 "http://127.0.0.1:$PORT/"; then
    exit 0  # tout va bien, rien à faire
fi

echo "[$(timestamp)] Backend injoignable sur le port $PORT, tentative de redémarrage..." >> "$WATCHDOG_LOG"

# Nettoie un éventuel process zombie sur le port
PID=$(lsof -ti:$PORT)
if [ -n "$PID" ]; then
    kill -9 $PID
    sleep 1
fi

cd "$APP_DIR" || exit 1
source "$VENV"
nohup uvicorn main:app --host 127.0.0.1 --port $PORT >> "$LOG" 2>&1 &

sleep 3

if curl -s -o /dev/null -m 5 "http://127.0.0.1:$PORT/"; then
    echo "[$(timestamp)] Backend redémarré avec succès (PID $!)." >> "$WATCHDOG_LOG"
else
    echo "[$(timestamp)] ECHEC du redémarrage. Vérifier $LOG." >> "$WATCHDOG_LOG"
fi

# --- Installation sur le serveur cPanel ---
# 1. chmod +x /home/dxtrmfwa/BACKEND/watchdog.sh
# 2. crontab -e   puis ajouter ces deux lignes :
#    */5 * * * * /home/dxtrmfwa/BACKEND/watchdog.sh
#    @reboot /home/dxtrmfwa/BACKEND/watchdog.sh
# 3. tail -f /home/dxtrmfwa/BACKEND/watchdog.log   pour suivre l'activité
