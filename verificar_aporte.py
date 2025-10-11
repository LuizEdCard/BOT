#!/usr/bin/env python3
"""
Script para verificar e processar aportes BRL imediatamente
Útil quando você acabou de fazer um depósito e quer converter agora
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from src.comunicacao.api_manager import APIManager
from src.core.gerenciador_aportes import GerenciadorAportes
from src.utils.logger import get_logger

# Configurar logger
logger = get_logger(
    log_dir=Path('logs'),
    nivel=settings.LOG_LEVEL,
    console=True
)


def main():
    """Verificar aportes BRL agora"""
    logger.banner("💰 VERIFICAÇÃO MANUAL DE APORTES BRL")

    # Inicializar API
    logger.info("🔌 Conectando à Binance...")
    api = APIManager(
        api_key=settings.BINANCE_API_KEY,
        api_secret=settings.BINANCE_API_SECRET,
        base_url=settings.BINANCE_API_URL
    )

    if not api.verificar_conexao():
        logger.error("❌ Não foi possível conectar à API Binance")
        return

    logger.info("✅ Conectado")

    # Inicializar gerenciador de aportes
    gerenciador = GerenciadorAportes(api, settings)

    # Verificar saldos atuais
    logger.info("\n💼 Saldos atuais:")
    resumo = gerenciador.obter_resumo_saldos()

    # Processar aporte se houver BRL
    logger.info("\n🔍 Verificando aportes BRL...")
    resultado = gerenciador.processar_aporte_automatico()

    if resultado['sucesso']:
        logger.info(f"\n✅ {resultado['mensagem']}")
        logger.info(f"   💵 BRL convertido: R$ {resultado['valor_brl']:.2f}")
        logger.info(f"   💰 USDT recebido: ${resultado['quantidade_usdt']:.2f}")
        logger.info(f"   📈 Cotação: R$ {resultado['preco']:.4f}")
        logger.info(f"   📝 Order ID: {resultado.get('order_id', 'N/A')}")

        # Saldos finais
        logger.info("\n💼 Saldos finais:")
        gerenciador.obter_resumo_saldos()
    else:
        logger.warning(f"\n⚠️ {resultado['mensagem']}")

    logger.banner("✅ VERIFICAÇÃO CONCLUÍDA")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Verificação interrompida")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        logger.exception("Traceback:")
        sys.exit(1)
