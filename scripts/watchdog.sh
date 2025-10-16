#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# TRADING BOT - Watchdog (Auto-Restart)
# ═══════════════════════════════════════════════════════════════════
# Monitora o bot e reinicia automaticamente se cair
# Use em conjunto com cron ou rode em background
# ═══════════════════════════════════════════════════════════════════

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.bot.pid"
WATCHDOG_LOG="$SCRIPT_DIR/logs/watchdog.log"

# Função de log
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$WATCHDOG_LOG"
}

# Função para verificar se o bot está rodando
is_bot_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            return 0  # Está rodando
        fi
    fi
    return 1  # Não está rodando
}

# Criar diretório de logs
mkdir -p "$SCRIPT_DIR/logs"

log_message "Watchdog iniciado"

# Loop infinito de monitoramento
CHECK_INTERVAL=60  # Verificar a cada 60 segundos
CONSECUTIVE_FAILURES=0
MAX_CONSECUTIVE_FAILURES=3

while true; do
    if ! is_bot_running; then
        CONSECUTIVE_FAILURES=$((CONSECUTIVE_FAILURES + 1))
        log_message "⚠️  Bot não está rodando! (Falha $CONSECUTIVE_FAILURES/$MAX_CONSECUTIVE_FAILURES)"

        if [ $CONSECUTIVE_FAILURES -ge $MAX_CONSECUTIVE_FAILURES ]; then
            log_message "🔄 Tentando reiniciar bot..."

            # Limpar PID file antigo
            rm -f "$PID_FILE"

            # Reiniciar bot
            cd "$SCRIPT_DIR"
            if bash start_background.sh >> "$WATCHDOG_LOG" 2>&1; then
                log_message "✅ Bot reiniciado com sucesso"
                CONSECUTIVE_FAILURES=0
            else
                log_message "❌ Falha ao reiniciar bot"
            fi
        fi
    else
        # Bot está rodando, resetar contador
        if [ $CONSECUTIVE_FAILURES -gt 0 ]; then
            log_message "✅ Bot voltou a funcionar"
        fi
        CONSECUTIVE_FAILURES=0
    fi

    # Aguardar próxima verificação
    sleep $CHECK_INTERVAL
done
