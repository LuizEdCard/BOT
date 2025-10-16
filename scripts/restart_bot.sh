#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# TRADING BOT - Reiniciar Bot
# ═══════════════════════════════════════════════════════════════════

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}         REINICIAR TRADING BOT${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Parar bot
echo -e "${YELLOW}1/2 Parando bot...${NC}"
"$SCRIPT_DIR/stop_bot.sh"

echo ""

# Aguardar 2 segundos
sleep 2

# Iniciar bot
echo -e "${YELLOW}2/2 Iniciando bot...${NC}"
"$SCRIPT_DIR/start_background.sh"
