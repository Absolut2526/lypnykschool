#!/bin/bash
# Script to stop Lypnyk School Telegram Admin Bot daemon

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/bot.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        kill "$PID"
        echo "🛑 Бот зупинено (PID: $PID)."
    else
        echo "Бот не запущено."
    fi
    rm -f "$PID_FILE"
else
    echo "Файл PID не знайдено. Бот не запущено."
fi
