#!/usr/bin/env bash
# Script de monitoramento do bot - Executa verificações a cada 15 minutos por 2 horas

DURACAO_HORAS=2
INTERVALO_MINUTOS=15
ARQUIVO_LOG="logs/monitoramento_$(date +%Y%m%d_%H%M%S).log"

# Cores
VERDE='\033[0;32m'
AZUL='\033[0;34m'
AMARELO='\033[1;33m'
VERMELHO='\033[0;31m'
NC='\033[0m' # Sem cor

# Função para registrar com timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$ARQUIVO_LOG"
}

# Função para verificar status do bot
verificar_bot() {
    local iteracao=$1
    local tempo_decorrido=$2

    log "════════════════════════════════════════════════════════════"
    log "📊 VERIFICAÇÃO #$iteracao (Tempo decorrido: ${tempo_decorrido} minutos)"
    log "════════════════════════════════════════════════════════════"

    # 1. Verificar se o bot está rodando
    if [ -f .bot.pid ]; then
        PID=$(head -1 .bot.pid)
        if ps -p "$PID" > /dev/null 2>&1; then
            UPTIME=$(ps -p "$PID" -o etime= | tr -d ' ')
            log "✅ Bot está rodando (PID: $PID, Uptime: $UPTIME)"
        else
            log "❌ Bot NÃO está rodando (PID antigo: $PID)"
            return 1
        fi
    else
        log "❌ Arquivo .bot.pid não encontrado"
        return 1
    fi

    # 2. Verificar últimas linhas do log
    log ""
    log "📋 Últimas 5 linhas do log:"
    tail -5 logs/bot_background.log | while read line; do
        log "   $line"
    done

    # 3. Contar erros nas últimas 15 minutos
    ERROS_RECENTES=$(grep -c "ERROR" logs/bot_background.log | tail -100)
    log ""
    log "⚠️  Erros nas últimas 100 linhas: $ERROS_RECENTES"

    # 4. Verificar estado do banco de dados
    if [ -f dados/trading_bot.db ]; then
        TAMANHO_DB=$(du -h dados/trading_bot.db | cut -f1)
        TOTAL_ORDENS=$(sqlite3 dados/trading_bot.db "SELECT COUNT(*) FROM ordens" 2>/dev/null || echo "0")
        log ""
        log "💾 Banco de dados:"
        log "   Tamanho: $TAMANHO_DB"
        log "   Total de ordens: $TOTAL_ORDENS"

        # Estado do bot
        ESTADO=$(sqlite3 dados/trading_bot.db "SELECT preco_medio_compra, quantidade_total_ada FROM estado_bot WHERE id = 1" 2>/dev/null)
        if [ -n "$ESTADO" ]; then
            log "   Estado: $ESTADO"
        fi
    fi

    # 5. Uso de memória e CPU do processo
    if ps -p "$PID" > /dev/null 2>&1; then
        MEM_CPU=$(ps -p "$PID" -o %mem,%cpu,rss | tail -1)
        log ""
        log "💻 Recursos do processo:"
        log "   $MEM_CPU (MEM% CPU% RSS)"
    fi

    log ""
}

# Banner inicial
echo -e "${AZUL}════════════════════════════════════════════════════════════${NC}"
echo -e "${AZUL}      MONITORAMENTO AUTOMÁTICO DO BOT${NC}"
echo -e "${AZUL}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${AMARELO}Duração:${NC} $DURACAO_HORAS horas"
echo -e "${AMARELO}Intervalo:${NC} $INTERVALO_MINUTOS minutos"
echo -e "${AMARELO}Verificações totais:${NC} $((DURACAO_HORAS * 60 / INTERVALO_MINUTOS))"
echo -e "${AMARELO}Arquivo de log:${NC} $ARQUIVO_LOG"
echo ""
echo -e "${AZUL}════════════════════════════════════════════════════════════${NC}"
echo ""

# Registrar início
log "🚀 Iniciando monitoramento automático"
log "   Duração: $DURACAO_HORAS horas"
log "   Intervalo: $INTERVALO_MINUTOS minutos"
log ""

# Loop de monitoramento
ITERACAO=1
TOTAL_VERIFICACOES=$((DURACAO_HORAS * 60 / INTERVALO_MINUTOS))
TEMPO_DECORRIDO=0

# Primeira verificação imediata
verificar_bot $ITERACAO $TEMPO_DECORRIDO
ITERACAO=$((ITERACAO + 1))

# Loop com intervalo
while [ $ITERACAO -le $TOTAL_VERIFICACOES ]; do
    echo -e "${AMARELO}⏳ Aguardando $INTERVALO_MINUTOS minutos...${NC}"
    log "⏳ Aguardando $INTERVALO_MINUTOS minutos até próxima verificação..."
    log ""

    sleep $((INTERVALO_MINUTOS * 60))

    TEMPO_DECORRIDO=$((TEMPO_DECORRIDO + INTERVALO_MINUTOS))

    verificar_bot $ITERACAO $TEMPO_DECORRIDO

    ITERACAO=$((ITERACAO + 1))
done

# Resumo final
log "════════════════════════════════════════════════════════════"
log "✅ MONITORAMENTO CONCLUÍDO"
log "════════════════════════════════════════════════════════════"
log "Total de verificações: $TOTAL_VERIFICACOES"
log "Tempo total: $DURACAO_HORAS horas"
log ""

echo ""
echo -e "${VERDE}✅ Monitoramento concluído!${NC}"
echo -e "${AZUL}Log completo salvo em: $ARQUIVO_LOG${NC}"
echo ""
