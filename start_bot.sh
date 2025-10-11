#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# TRADING BOT - Script de Inicialização para Termux
# ═══════════════════════════════════════════════════════════════════

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}         TRADING BOT ADA/USDT - INICIALIZAÇÃO${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Diretório do projeto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${YELLOW}📁 Diretório:${NC} $SCRIPT_DIR"
echo ""

# Verificar se .env existe
if [ ! -f "config/.env" ]; then
    echo -e "${RED}❌ ERRO: config/.env não encontrado!${NC}"
    echo -e "   Execute: cp config/.env.example config/.env"
    exit 1
fi

# Verificar se venv existe
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚙️  Criando ambiente virtual...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Ambiente virtual criado${NC}"
fi

# Ativar venv
echo -e "${YELLOW}🔄 Ativando ambiente virtual...${NC}"
source venv/bin/activate

# Verificar dependências
echo -e "${YELLOW}📦 Verificando dependências...${NC}"
if ! pip list | grep -q "colorama"; then
    echo -e "${YELLOW}⚙️  Instalando dependências...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependências instaladas${NC}"
else
    echo -e "${GREEN}✅ Dependências OK${NC}"
fi

echo ""

# Validar configuração
echo -e "${YELLOW}🔍 Validando configurações...${NC}"
if python test_config.py > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Configurações válidas${NC}"
else
    echo -e "${RED}❌ ERRO: Configurações inválidas!${NC}"
    echo -e "   Execute: python test_config.py"
    exit 1
fi

echo ""

# Verificar ambiente
AMBIENTE=$(grep "^AMBIENTE=" config/.env | cut -d'=' -f2)
if [ "$AMBIENTE" == "PRODUCAO" ]; then
    echo -e "${RED}⚠️  ATENÇÃO: MODO PRODUÇÃO ATIVADO${NC}"
    echo -e "${RED}   Trades REAIS serão executados!${NC}"
    echo ""

    # Confirmação de segurança
    read -p "Deseja continuar? (digite SIM para confirmar): " confirmacao
    if [ "$confirmacao" != "SIM" ]; then
        echo -e "${YELLOW}❌ Inicialização cancelada${NC}"
        exit 0
    fi
else
    echo -e "${GREEN}✅ Modo: $AMBIENTE${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🚀 Iniciando Trading Bot...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}💡 Dicas:${NC}"
echo -e "   - Use Ctrl+C para parar o bot"
echo -e "   - Logs salvos em: logs/"
echo -e "   - Para rodar em background: ./start_background.sh"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Iniciar bot
python main.py
