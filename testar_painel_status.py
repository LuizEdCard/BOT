#!/usr/bin/env python3
"""
Script de teste para validar o painel de status do bot
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from decimal import Decimal
from src.persistencia.database import DatabaseManager
from src.core.gestao_capital import GestaoCapital
from config.settings import settings
from src.utils.logger import get_logger

# Configurar logger
logger = get_logger(
    log_dir=Path('logs'),
    # config usa LogConfig.DEFAULT,
    console=True
)

# Simular dados do bot
preco_atual = Decimal('0.6850')
saldo_usdt = Decimal('25.50')
saldo_ada = Decimal('130.5')
quantidade_total_comprada = Decimal('130.5')
preco_medio_compra = Decimal('0.6520')
sma_referencia = Decimal('0.6940')

# Calcular métricas
valor_posicao = quantidade_total_comprada * preco_atual

# Usar GestaoCapital para calcular reserva (centralizado)
gestao = GestaoCapital()
gestao.atualizar_saldos(saldo_usdt, valor_posicao)
reserva = gestao.calcular_reserva_obrigatoria()
capital_total = gestao.calcular_capital_total()

# Calcular lucro/prejuízo não realizado
lucro_pct = ((preco_atual - preco_medio_compra) / preco_medio_compra) * Decimal('100')
lucro_usdt = (preco_atual - preco_medio_compra) * quantidade_total_comprada

# Calcular distância da SMA
distancia_sma = ((sma_referencia - preco_atual) / sma_referencia) * Decimal('100')

# Buscar estatísticas de 24h
db = DatabaseManager(
    db_path=settings.DATABASE_PATH,
    backup_dir=settings.BACKUP_DIR
)
stats_24h = db.obter_estatisticas_24h()

# Formatar painel (exatamente como no bot)
logger.info("")
logger.info(" V V V V V V V V V V V V V V V V V V V V V V V V V V V V V V V V V V V V")
logger.info("")
logger.info(" -- PAINEL DE STATUS DO BOT --")
logger.info("")

# MERCADO
logger.info(" 📈 MERCADO [ADA/USDT]")
logger.info(f"    - Preço Atual:    ${preco_atual:.6f}")
logger.info(f"    - SMA (28d):      ${sma_referencia:.6f}")
logger.info(f"    - Distância SMA:  {distancia_sma:+.2f}%")
logger.info("")

# POSIÇÃO ATUAL
logger.info(" 💼 POSIÇÃO ATUAL")
logger.info(f"    - Ativo em Pos.:  {quantidade_total_comprada:.2f} ADA")
logger.info(f"    - Preço Médio:    ${preco_medio_compra:.6f}")
logger.info(f"    - Valor Posição:  ${valor_posicao:.2f} USDT")
logger.info("")

# PERFORMANCE (NÃO REALIZADA)
logger.info(" 📊 PERFORMANCE (NÃO REALIZADA)")
emoji = "📈" if lucro_pct > 0 else "📉"
logger.info(f"    - Lucro/Prejuízo: {emoji} {lucro_pct:+.2f}%")
logger.info(f"    - Valor L/P:      ${lucro_usdt:+.2f} USDT")
logger.info("")

# CAPITAL
logger.info(" 💰 CAPITAL")
logger.info(f"    - Saldo Livre:    ${saldo_usdt:.2f} USDT")
logger.info(f"    - Reserva (8%):   ${reserva:.2f} USDT")
logger.info(f"    - Capital Total:  ${capital_total:.2f} USDT")
logger.info("")

# HISTÓRICO (ÚLTIMAS 24H)
logger.info(" 📜 HISTÓRICO (ÚLTIMAS 24H)")
logger.info(f"    - Compras:        {stats_24h['compras']}")
logger.info(f"    - Vendas:         {stats_24h['vendas']}")
lucro_24h = stats_24h['lucro_realizado']
emoji_24h = "📈" if lucro_24h > 0 else "📊"
logger.info(f"    - Lucro Realizado: {emoji_24h} ${lucro_24h:+.2f} USDT")
logger.info("")

logger.info(" ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^")
logger.info("")

print("\n✅ Teste do painel de status concluído com sucesso!")
