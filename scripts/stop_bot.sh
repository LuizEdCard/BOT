#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# TRADING BOT - Parar Bot
# ═══════════════════════════════════════════════════════════════════

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.bot.pid"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}           PARAR TRADING BOT${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}⚠️  Bot não está rodando (PID file não encontrado)${NC}"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! ps -p $PID > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Bot não está rodando (PID $PID não encontrado)${NC}"
    rm -f "$PID_FILE"
    exit 0
fi

echo -e "${YELLOW}🛑 Parando bot (PID: $PID)...${NC}"

# Tentar parar gracefully
kill $PID

# Aguardar até 10 segundos
for i in {1..10}; do
    if ! ps -p $PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Bot parado com sucesso!${NC}"
        rm -f "$PID_FILE"

        # Liberar wakelock no Termux
        if command -v termux-wake-unlock &> /dev/null; then
            termux-wake-unlock
            echo -e "${GREEN}✅ Wakelock liberado${NC}"
        fi

        echo ""
        exit 0
    fi
    echo -ne "   Aguardando... $i/10\r"
    sleep 1
done

# Se não parou, force kill
echo ""
echo -e "${RED}⚠️  Bot não respondeu, forçando parada...${NC}"
kill -9 $PID

sleep 1

if ! ps -p $PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Bot forçado a parar${NC}"
    rm -f "$PID_FILE"

    # Liberar wakelock
    if command -v termux-wake-unlock &> /dev/null; then
        termux-wake-unlock
    fi
else
    echo -e "${RED}❌ Não foi possível parar o bot!${NC}"
    exit 1
fi

echo ""
