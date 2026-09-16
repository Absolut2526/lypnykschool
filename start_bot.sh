#!/bin/bash
# Script to launch Lypnyk School Telegram Admin Bot daemon in background

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/bot.pid"
LOG_FILE="$SCRIPT_DIR/bot.log"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "⚠️ Бот вже запущено (PID: $PID). Логи: $LOG_FILE"
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

echo "🚀 Запуск Telegram-бота @LypnykSchoolBot..."
nohup python3 "$SCRIPT_DIR/bot_admin.py" > "$LOG_FILE" 2>&1 &
BOT_PID=$!
echo $BOT_PID > "$PID_FILE"
echo "✅ Бот успішно запущено у фоновому режимі (PID: $BOT_PID)!"
echo "📄 Лог-файл: $LOG_FILE"
