#!/bin/bash
# ═══════════════════════════════════════════════════════════
# COMPRA MANUAL DE ADA - Script de Conveniência
# ═══════════════════════════════════════════════════════════
#
# Uso:
#   ./comprar.sh              # Compra com valor padrão ($5)
#   ./comprar.sh 10           # Compra com $10 USDT
#   ./comprar.sh 15.5 ada     # Compra 15.5 ADA
# ═══════════════════════════════════════════════════════════

cd "$(dirname "$0")"

# Ativar ambiente virtual
source venv/bin/activate

# Verificar argumentos
if [ $# -eq 0 ]; then
    # Sem argumentos: valor padrão
    python comprar_manual.py
elif [ $# -eq 1 ]; then
    # Um argumento: valor em USDT
    python comprar_manual.py --usdt "$1"
elif [ $# -eq 2 ] && [ "$2" = "ada" ]; then
    # Dois argumentos com "ada": quantidade em ADA
    python comprar_manual.py --ada "$1"
else
    echo "❌ Uso incorreto!"
    echo ""
    echo "Exemplos:"
    echo "  ./comprar.sh              # Compra com valor padrão (\$5)"
    echo "  ./comprar.sh 10           # Compra com \$10 USDT"
    echo "  ./comprar.sh 15.5 ada     # Compra 15.5 ADA"
    exit 1
fi
