#!/usr/bin/env python3
"""
Teste do sistema de SMA de 4 semanas
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from decimal import Decimal
from config.settings import settings
from src.comunicacao.api_manager import APIManager
from src.core.analise_tecnica import AnaliseTecnica
from src.utils.logger import get_loggers

logger, _ = get_loggers(log_dir=Path('logs'), nivel='INFO', console=True)


def main():
    logger.banner("🧪 TESTE DE SISTEMA SMA 4 SEMANAS")

    # Inicializar API
    api = APIManager(
        api_key=settings.BINANCE_API_KEY,
        api_secret=settings.BINANCE_API_SECRET,
        base_url=settings.BINANCE_API_URL
    )

    if not api.verificar_conexao():
        logger.error("❌ Não foi possível conectar à API")
        return

    logger.info("✅ Conectado à Binance")

    # Inicializar análise técnica
    analise = AnaliseTecnica(api)

    # Calcular SMAs
    logger.info("\n📊 Calculando SMAs de 4 semanas (28 dias)...")
    smas = analise.calcular_sma_multiplos_timeframes(
        simbolo='ADAUSDT',
        periodo_dias=28
    )

    if not smas:
        logger.error("❌ Falha ao calcular SMAs")
        return

    # Obter preço atual
    logger.info("\n💹 Obtendo preço atual...")
    ticker = api.obter_ticker('ADAUSDT')
    preco_atual = Decimal(str(ticker['price']))
    logger.info(f"   Preço atual: ${preco_atual:.6f}")

    # Calcular distância da SMA
    sma_ref = smas['media']
    queda_pct = ((sma_ref - preco_atual) / sma_ref) * Decimal('100')

    logger.info("\n" + "="*60)
    logger.info("📈 ANÁLISE FINAL")
    logger.info("="*60)
    logger.info(f"   SMA 1h (4 sem):      ${smas['1h']:.6f}")
    logger.info(f"   SMA 4h (4 sem):      ${smas['4h']:.6f}")
    logger.info(f"   SMA Média (40/60):   ${sma_ref:.6f}")
    logger.info(f"   Preço atual:         ${preco_atual:.6f}")
    logger.info(f"   Distância da SMA:    {queda_pct:+.2f}%")
    logger.info("="*60)

    # Verificar degraus
    logger.info("\n🎯 Verificação de degraus:")
    for degrau in settings.DEGRAUS_COMPRA[:3]:  # Primeiros 3
        nivel = degrau['nivel']
        gatilho = Decimal(str(degrau['queda_percentual']))
        qtd_ada = degrau['quantidade_ada']

        if queda_pct >= gatilho:
            logger.info(f"   ✅ Degrau {nivel} ATIVADO (-{gatilho}%) → Comprar {qtd_ada} ADA")
        else:
            falta = gatilho - queda_pct
            logger.info(f"   ⏳ Degrau {nivel} aguardando (falta {falta:.2f}%) → Comprar {qtd_ada} ADA")

    logger.banner("✅ TESTE CONCLUÍDO")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Teste interrompido")
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        logger.exception("Traceback:")
