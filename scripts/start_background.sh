#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# TRADING BOT - Script para Rodar em Background (Termux)
# ═══════════════════════════════════════════════════════════════════

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Diretório do projeto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Arquivos de controle
PID_FILE="$SCRIPT_DIR/.bot.pid"
LOG_FILE="$SCRIPT_DIR/logs/bot_background.log"
ERROR_LOG="$SCRIPT_DIR/logs/bot_errors.log"

# Função para verificar se o bot está rodando
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            return 0  # Está rodando
        fi
    fi
    return 1  # Não está rodando
}

# Banner
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}      TRADING BOT - MODO BACKGROUND (TERMUX)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Verificar se já está rodando
if is_running; then
    echo -e "${YELLOW}⚠️  Bot já está rodando!${NC}"
    echo -e "   PID: $(cat $PID_FILE)"
    echo -e "   Use: ./stop_bot.sh para parar"
    exit 1
fi

# Adquirir wakelock no Termux
if command -v termux-wake-lock &> /dev/null; then
    echo -e "${YELLOW}🔒 Adquirindo wakelock (Termux)...${NC}"
    termux-wake-lock
    echo -e "${GREEN}✅ Wakelock adquirido (tela pode travar, bot continua)${NC}"
else
    echo -e "${YELLOW}⚠️  termux-wake-lock não encontrado${NC}"
    echo -e "   O bot pode parar se a tela travar"
    echo -e "   Instale: pkg install termux-api"
fi

echo ""

# Criar diretório de logs
mkdir -p logs

# Iniciar bot em background
echo -e "${YELLOW}🚀 Iniciando bot em background...${NC}"
echo ""

# Ambiente de produção - sem confirmação interativa
AMBIENTE=$(grep "^AMBIENTE=" config/.env | cut -d'=' -f2)
if [ "$AMBIENTE" == "PRODUCAO" ]; then
    echo -e "${RED}⚠️  MODO PRODUÇÃO - TRADES REAIS${NC}"
fi

# Ativar venv e rodar
source venv/bin/activate

# Rodar bot em background com nohup
nohup python main.py > "$LOG_FILE" 2> "$ERROR_LOG" &

# Salvar PID
BOT_PID=$!
echo $BOT_PID > "$PID_FILE"

echo -e "${GREEN}✅ Bot iniciado com sucesso!${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "📊 INFORMAÇÕES:"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "   PID: ${GREEN}$BOT_PID${NC}"
echo -e "   Log: ${YELLOW}$LOG_FILE${NC}"
echo -e "   Erros: ${YELLOW}$ERROR_LOG${NC}"
echo -e "   PID File: ${YELLOW}$PID_FILE${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "📱 COMANDOS ÚTEIS:"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "   Ver status:    ${GREEN}./status_bot.sh${NC}"
echo -e "   Ver logs:      ${GREEN}tail -f $LOG_FILE${NC}"
echo -e "   Ver erros:     ${GREEN}tail -f $ERROR_LOG${NC}"
echo -e "   Parar bot:     ${GREEN}./stop_bot.sh${NC}"
echo -e "   Reiniciar:     ${GREEN}./restart_bot.sh${NC}"
echo ""
echo -e "${YELLOW}💡 O bot continuará rodando mesmo se a tela travar!${NC}"
echo -e "${YELLOW}   Use 'termux-wake-lock' foi ativado.${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

# Aguardar 2 segundos e verificar se ainda está rodando
sleep 2

if is_running; then
    echo -e "${GREEN}✅ Bot verificado - rodando corretamente!${NC}"
    echo ""
else
    echo -e "${RED}❌ ERRO: Bot não está rodando!${NC}"
    echo -e "   Verifique os logs de erro:"
    echo -e "   ${YELLOW}cat $ERROR_LOG${NC}"
    rm -f "$PID_FILE"
    exit 1
fi
