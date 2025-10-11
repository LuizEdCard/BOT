#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# TRADING BOT - Status
# ═══════════════════════════════════════════════════════════════════

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.bot.pid"
LOG_FILE="$SCRIPT_DIR/logs/bot_background.log"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}         TRADING BOT - STATUS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Verificar se está rodando
if [ ! -f "$PID_FILE" ]; then
    echo -e "   Status: ${RED}⭕ NÃO RODANDO${NC}"
    echo ""
    echo -e "   Use: ${GREEN}./start_background.sh${NC} para iniciar"
    echo ""
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! ps -p $PID > /dev/null 2>&1; then
    echo -e "   Status: ${RED}⭕ NÃO RODANDO${NC}"
    echo -e "   ${YELLOW}(PID file existe mas processo não encontrado)${NC}"
    echo ""
    rm -f "$PID_FILE"
    exit 0
fi

# Bot está rodando
echo -e "   Status: ${GREEN}✅ RODANDO${NC}"
echo -e "   PID: ${GREEN}$PID${NC}"
echo ""

# Informações do processo
UPTIME=$(ps -p $PID -o etime= | xargs)
MEM=$(ps -p $PID -o rss= | xargs)
MEM_MB=$((MEM / 1024))
CPU=$(ps -p $PID -o %cpu= | xargs)

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "📊 INFORMAÇÕES DO PROCESSO:"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "   Tempo Ativo: ${GREEN}$UPTIME${NC}"
echo -e "   Memória: ${GREEN}${MEM_MB} MB${NC}"
echo -e "   CPU: ${GREEN}${CPU}%${NC}"
echo ""

# Ambiente
if [ -f "$SCRIPT_DIR/config/.env" ]; then
    AMBIENTE=$(grep "^AMBIENTE=" "$SCRIPT_DIR/config/.env" | cut -d'=' -f2)
    if [ "$AMBIENTE" == "PRODUCAO" ]; then
        echo -e "   Ambiente: ${RED}🔴 PRODUÇÃO (TRADES REAIS)${NC}"
    else
        echo -e "   Ambiente: ${YELLOW}🟡 $AMBIENTE${NC}"
    fi
fi

# Wakelock status (Termux)
if command -v termux-wake-lock &> /dev/null; then
    echo -e "   Wakelock: ${GREEN}✅ Disponível${NC}"
fi

echo ""

# Últimas linhas do log
if [ -f "$LOG_FILE" ]; then
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "📝 ÚLTIMAS 10 LINHAS DO LOG:"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    tail -n 10 "$LOG_FILE"
    echo ""
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "📱 COMANDOS:"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "   Ver logs:      ${GREEN}tail -f $LOG_FILE${NC}"
echo -e "   Parar bot:     ${GREEN}./stop_bot.sh${NC}"
echo -e "   Reiniciar:     ${GREEN}./restart_bot.sh${NC}"
echo ""
