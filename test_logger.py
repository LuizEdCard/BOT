#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════
TRADING BOT - Teste de Logger
═══════════════════════════════════════════════════════════════════
Script para testar o sistema de logging
"""

import sys
from pathlib import Path

# Adicionar diretório src ao path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import get_logger


def testar_logger():
    """Testa todas as funcionalidades do logger"""

    # Criar logger
    logger = get_logger(
        nome='TestLogger',
        log_dir=Path(__file__).parent / 'logs',
        nivel='DEBUG',
        console=True
    )

    # Banner inicial
    logger.banner("TESTE DO SISTEMA DE LOGGING")

    # Testar níveis básicos
    logger.debug("Mensagem de DEBUG - detalhes técnicos")
    logger.info("Mensagem de INFO - informação normal")
    logger.warning("Mensagem de WARNING - atenção!")
    logger.error("Mensagem de ERROR - algo deu errado")
    logger.critical("Mensagem de CRITICAL - situação grave!")

    print()

    # Testar métodos especializados
    logger.operacao_compra(
        par='ADA/USDT',
        quantidade=8.0,
        preco=0.8123,
        degrau=1,
        queda_pct=1.5
    )

    logger.operacao_venda(
        par='ADA/USDT',
        quantidade=2.4,
        preco=0.8987,
        meta=1,
        lucro_pct=6.0,
        lucro_usd=5.23
    )

    print()

    logger.pico_detectado(par='ADA/USDT', preco=0.8500, confirmado=False)
    logger.pico_detectado(par='ADA/USDT', preco=0.8500, confirmado=True)

    print()

    logger.capital_atualizado(
        capital_ativo=165.60,
        reserva=14.40,
        total=180.00,
        motivo='Capital inicial'
    )

    logger.aporte_detectado(valor=50.00)

    print()

    logger.saldo_atualizado(cripto=208.5, usdt=15.23, par='ADA/USDT')

    print()

    logger.erro_api(
        endpoint='/api/v3/order',
        erro='Timeout após 30s',
        tentativa=1
    )

    logger.conexao_perdida(tipo='WebSocket', tentando_reconectar=True)

    print()

    logger.inicializacao(componente='Database', sucesso=True)
    logger.inicializacao(componente='WebSocket', sucesso=True)
    logger.inicializacao(componente='API Manager', sucesso=True)

    print()

    # Banner final
    logger.banner("TESTE CONCLUÍDO COM SUCESSO")

    # Informações
    print()
    print("✅ Teste concluído!")
    print(f"📁 Logs salvos em: {Path(__file__).parent / 'logs'}")
    print()


if __name__ == '__main__':
    testar_logger()
