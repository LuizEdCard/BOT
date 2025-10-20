#!/bin/bash
# Script para iniciar o bot com ambiente virtual ativado

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Iniciando Bot de Trading...${NC}"

# Verificar se está no diretório correto
if [ ! -f "manager.py" ]; then
    echo -e "${RED}❌ Erro: manager.py não encontrado!${NC}"
    echo -e "${YELLOW}Execute este script a partir do diretório raiz do projeto.${NC}"
    exit 1
fi

# Verificar se o ambiente virtual existe
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Erro: Ambiente virtual não encontrado!${NC}"
    echo -e "${YELLOW}Criando ambiente virtual...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Ambiente virtual criado!${NC}"
fi

# Ativar ambiente virtual
echo -e "${YELLOW}🔄 Ativando ambiente virtual...${NC}"
source venv/bin/activate

# Verificar se as dependências estão instaladas
echo -e "${YELLOW}🔄 Verificando dependências...${NC}"
if ! python -c "import telegram" 2>/dev/null; then
    echo -e "${YELLOW}📦 Instalando dependências...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependências instaladas!${NC}"
else
    echo -e "${GREEN}✅ Dependências já instaladas!${NC}"
fi

# Verificar variáveis de ambiente
if [ ! -f "configs/.env" ]; then
    echo -e "${RED}❌ Erro: Arquivo configs/.env não encontrado!${NC}"
    echo -e "${YELLOW}Crie o arquivo configs/.env com as credenciais necessárias.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Tudo pronto!${NC}"
echo -e "${YELLOW}🤖 Iniciando manager.py...${NC}"
echo ""

# Iniciar o bot
python manager.py
