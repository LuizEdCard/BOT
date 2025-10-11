#!/usr/bin/env python3
"""
Script de teste para sistema de aportes BRL

Testa:
1. Detecção de saldo BRL
2. Conversão BRL → USDT
3. Atualização de saldo USDT
4. Logging de aportes
"""

import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from decimal import Decimal
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
    """Função principal de teste"""

    logger.banner("🧪 TESTE DE SISTEMA DE APORTES BRL")

    # 1. Verificar configurações
    logger.info("📋 Verificando configurações...")
    logger.info(f"   Ambiente: {settings.AMBIENTE}")
    logger.info(f"   API URL: {settings.BINANCE_API_URL}")
    logger.info(f"   Capital inicial: ${settings.CAPITAL_INICIAL}")
    logger.info(f"   Valor mínimo aporte: ${settings.VALOR_MINIMO_APORTE}")

    # 2. Inicializar API Manager
    logger.info("\n🔌 Inicializando API Manager...")
    try:
        api = APIManager(
            api_key=settings.BINANCE_API_KEY,
            api_secret=settings.BINANCE_API_SECRET,
            base_url=settings.BINANCE_API_URL
        )

        # Verificar conexão
        if api.verificar_conexao():
            logger.inicializacao("API Manager", sucesso=True)
        else:
            logger.inicializacao("API Manager", sucesso=False)
            logger.error("❌ Não foi possível conectar à API Binance")
            return

    except Exception as e:
        logger.error(f"❌ Erro ao inicializar API: {e}")
        return

    # 3. Inicializar Gerenciador de Aportes
    logger.info("\n💰 Inicializando Gerenciador de Aportes...")
    try:
        gerenciador = GerenciadorAportes(api, settings)
        logger.inicializacao("Gerenciador de Aportes", sucesso=True)
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar gerenciador: {e}")
        return

    # 4. Verificar saldos atuais
    logger.info("\n💼 Verificando saldos atuais...")
    try:
        resumo = gerenciador.obter_resumo_saldos()

        if resumo['brl'] > 0:
            logger.info(f"   ✅ Saldo BRL detectado: R$ {resumo['brl']:.2f}")
        else:
            logger.info(f"   ⚠️ Nenhum saldo BRL (R$ {resumo['brl']:.2f})")

        logger.info(f"   USDT: ${resumo['usdt']:.2f}")
        logger.info(f"   ADA: {resumo['ada']:.4f}")
        logger.info(f"   Total (USD equiv): ${resumo['total_usdt_equivalente']:.2f}")

    except Exception as e:
        logger.error(f"❌ Erro ao obter saldos: {e}")
        return

    # 5. Verificar cotação USDT/BRL
    logger.info("\n📊 Verificando cotação USDT/BRL...")
    try:
        preco_usdt = gerenciador.obter_preco_usdt_brl()
        if preco_usdt:
            logger.info(f"   ✅ USDT/BRL: R$ {preco_usdt:.4f}")
        else:
            logger.error("   ❌ Não foi possível obter cotação")
            return
    except Exception as e:
        logger.error(f"❌ Erro ao obter cotação: {e}")
        return

    # 6. Processar aporte automático (se houver BRL)
    logger.info("\n🔄 Processando aporte automático...")
    try:
        resultado = gerenciador.processar_aporte_automatico()

        if resultado['sucesso']:
            logger.info(f"   ✅ {resultado['mensagem']}")
            logger.info(f"   💵 Valor BRL: R$ {resultado['valor_brl']:.2f}")
            logger.info(f"   💰 USDT recebido: ${resultado['quantidade_usdt']:.2f}")
            logger.info(f"   📈 Cotação: R$ {resultado['preco']:.4f}")
            logger.info(f"   📝 Order ID: {resultado.get('order_id', 'N/A')}")

            # Verificar saldo final
            logger.info("\n💼 Verificando saldo final USDT...")
            saldo_final_usdt = gerenciador.verificar_saldo_usdt()
            logger.info(f"   ✅ Saldo USDT atualizado: ${saldo_final_usdt:.2f}")

        else:
            logger.warning(f"   ⚠️ {resultado['mensagem']}")

    except Exception as e:
        logger.error(f"❌ Erro ao processar aporte: {e}")
        logger.exception("Traceback completo:")
        return

    # 7. Resumo final
    logger.info("\n" + "="*60)
    logger.info("📊 RESUMO FINAL")
    logger.info("="*60)

    try:
        resumo_final = gerenciador.obter_resumo_saldos()
        logger.info(f"💰 BRL:  R$ {resumo_final['brl']:.2f}")
        logger.info(f"💵 USDT: ${resumo_final['usdt']:.2f}")
        logger.info(f"🪙 ADA:  {resumo_final['ada']:.4f}")
        logger.info(f"💼 Total (USD): ${resumo_final['total_usdt_equivalente']:.2f}")
    except Exception as e:
        logger.error(f"❌ Erro ao obter resumo final: {e}")

    logger.info("="*60)
    logger.banner("✅ TESTE CONCLUÍDO")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Teste interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        logger.exception("Traceback:")
        sys.exit(1)
