#!/bin/bash

# Script para reproduzir erro de saldo em backtest longo
# Salva logs e permite análise posterior

echo "🔍 Reproduzindo erro de saldo insuficiente..."
echo ""

# Criar diretório de logs se não existir
mkdir -p logs

# Nome do arquivo de log com timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/backtest_problema_saldo_${TIMESTAMP}.log"

echo "📝 Executando backtest longo..."
echo "📂 Logs serão salvos em: $LOG_FILE"
echo ""

# Executar backtest com arquivo longo (você pode mudar os parâmetros)
python backtest.py \
  --non-interactive \
  --config configs/backtest_template.json \
  --csv "dados/historicos/BINANCE_ADAUSDT_1m_2025-01-01_2025-02-01.csv" \
  --timeframe "1h" \
  --saldo "1000" \
  --taxa "0.1" \
  --estrategias "ambas" \
  2>&1 | tee "$LOG_FILE"

echo ""
echo "✅ Backtest completado!"
echo ""
echo "📊 Analisando resultado..."
python analisar_problema_saldo.py "$LOG_FILE"

echo ""
echo "💾 Para revisar o log completo:"
echo "   less $LOG_FILE"
echo ""
echo "🔍 Para procurar erros específicos:"
echo "   grep 'Saldo insuficiente' $LOG_FILE"
echo "   grep 'ERROR' $LOG_FILE"
