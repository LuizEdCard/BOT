#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Script de Instalação de Dependências - Trading Bot
# ═══════════════════════════════════════════════════════════

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     INSTALAÇÃO DE DEPENDÊNCIAS - TRADING BOT            ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verificar se Python está instalado
echo -e "${YELLOW}🔍 Verificando instalação do Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 não encontrado. Por favor, instale Python 3.10+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✅ Python instalado: ${PYTHON_VERSION}${NC}"

# Verificar se pip está instalado
echo -e "${YELLOW}🔍 Verificando instalação do pip...${NC}"
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ pip3 não encontrado. Instalando...${NC}"
    python3 -m ensurepip --upgrade
fi

PIP_VERSION=$(pip3 --version | awk '{print $2}')
echo -e "${GREEN}✅ pip instalado: ${PIP_VERSION}${NC}"
echo ""

# Perguntar sobre ambiente virtual
echo -e "${YELLOW}📦 Deseja criar um ambiente virtual? (recomendado)${NC}"
read -p "Digite 'y' para sim ou 'n' para não: " USE_VENV

if [[ "$USE_VENV" == "y" || "$USE_VENV" == "Y" ]]; then
    echo -e "${BLUE}🔧 Criando ambiente virtual 'venv'...${NC}"

    if [ -d "venv" ]; then
        echo -e "${YELLOW}⚠️  Ambiente virtual já existe. Removendo...${NC}"
        rm -rf venv
    fi

    python3 -m venv venv

    echo -e "${BLUE}🔌 Ativando ambiente virtual...${NC}"
    source venv/bin/activate

    echo -e "${GREEN}✅ Ambiente virtual criado e ativado!${NC}"
    echo -e "${YELLOW}💡 Para ativar manualmente no futuro: source venv/bin/activate${NC}"
    echo ""
fi

# Atualizar pip
echo -e "${BLUE}📦 Atualizando pip...${NC}"
pip install --upgrade pip

# Perguntar sobre modo de instalação
echo -e "${YELLOW}📋 Escolha o modo de instalação:${NC}"
echo "  1) Produção (apenas dependências essenciais)"
echo "  2) Desenvolvimento (inclui pytest, black, flake8, mypy)"
echo "  3) Completo (produção + desenvolvimento + análise técnica)"
read -p "Digite o número (1-3): " INSTALL_MODE

# Instalar dependências do requirements.txt
echo -e "${BLUE}📥 Instalando dependências obrigatórias...${NC}"
pip install -r requirements.txt

# Instalar dependências adicionais baseado na escolha
if [[ "$INSTALL_MODE" == "2" || "$INSTALL_MODE" == "3" ]]; then
    echo -e "${BLUE}🧪 Instalando ferramentas de desenvolvimento...${NC}"
    pip install pytest==7.4.3 black==23.11.0 flake8==6.1.0 mypy==1.7.0
fi

if [[ "$INSTALL_MODE" == "3" ]]; then
    echo -e "${BLUE}📊 Instalando bibliotecas de análise técnica...${NC}"
    pip install ta==0.11.0 pandas==2.2.0 numpy==1.26.4

    echo -e "${BLUE}📈 Instalando bibliotecas de visualização...${NC}"
    pip install matplotlib==3.8.3 plotly==5.19.0
fi

# Verificar instalação
echo ""
echo -e "${BLUE}🔍 Verificando instalação...${NC}"
pip check

# Listar pacotes instalados
echo ""
echo -e "${GREEN}✅ Instalação concluída!${NC}"
echo ""
echo -e "${BLUE}📋 Pacotes instalados:${NC}"
pip list | grep -E "requests|websocket|cryptography|python-telegram-bot|python-dotenv|psutil|colorama|pytz|dateutil"

# Criar arquivo de confirmação
echo ""
echo -e "${BLUE}📝 Gerando arquivo de confirmação...${NC}"
pip freeze > requirements_installed.txt
echo -e "${GREEN}✅ Lista de pacotes instalados salva em 'requirements_installed.txt'${NC}"

# Instruções finais
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           INSTALAÇÃO CONCLUÍDA COM SUCESSO!              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📋 Próximos passos:${NC}"
echo ""
echo "  1. Configure o arquivo .env com suas API keys:"
echo -e "     ${BLUE}cp configs/.env.example configs/.env${NC}"
echo -e "     ${BLUE}nano configs/.env${NC}"
echo ""
echo "  2. Configure os bots ativos:"
echo -e "     ${BLUE}nano configs/config.json${NC}"
echo ""
echo "  3. Execute o bot:"
echo -e "     ${BLUE}python manager.py${NC}"
echo ""

if [[ "$USE_VENV" == "y" || "$USE_VENV" == "Y" ]]; then
    echo -e "${YELLOW}⚠️  LEMBRE-SE: Ative o ambiente virtual antes de executar:${NC}"
    echo -e "     ${BLUE}source venv/bin/activate${NC}"
    echo ""
fi

echo -e "${BLUE}📚 Documentação disponível:${NC}"
echo "  - DEPENDENCIAS.md - Lista completa de dependências"
echo "  - RELATORIO_HORARIO.md - Configuração de relatórios"
echo "  - MODO_CRASH_EXPLICACAO.md - Explicação do modo crash"
echo ""
