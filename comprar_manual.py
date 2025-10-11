#!/usr/bin/env python3
"""
Compra Manual - Permite comprar ADA fora da estratégia
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from decimal import Decimal
from config.settings import settings
from src.comunicacao.api_manager import APIManager
from src.utils.logger import get_logger

logger = get_logger(log_dir=Path('logs'), nivel='INFO', console=True)


def comprar_ada_manual(quantidade_ada: float = None, valor_usdt: float = None):
    """
    Compra ADA manualmente (fora da estratégia)

    Args:
        quantidade_ada: Quantidade de ADA a comprar (ex: 10)
        valor_usdt: Valor em USDT a gastar (ex: 5.0)
                   Se informado, calcula quantidade baseado no preço atual
    """
    logger.banner("💰 COMPRA MANUAL DE ADA")

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

    # Obter preço atual
    ticker = api.obter_ticker('ADAUSDT')
    preco_atual = Decimal(str(ticker['price']))
    logger.info(f"📊 Preço atual ADA: ${preco_atual:.6f}")

    # Calcular quantidade
    if valor_usdt:
        # Calcular quantidade baseada no valor USDT
        valor_usdt_dec = Decimal(str(valor_usdt))
        quantidade_ada_calc = valor_usdt_dec / preco_atual
        quantidade_ada = float(quantidade_ada_calc)
        logger.info(f"💵 Valor a gastar: ${valor_usdt:.2f} USDT")
        logger.info(f"🔢 Quantidade calculada: {quantidade_ada:.2f} ADA")
    elif quantidade_ada:
        valor_usdt = float(Decimal(str(quantidade_ada)) * preco_atual)
        logger.info(f"🔢 Quantidade: {quantidade_ada:.2f} ADA")
        logger.info(f"💵 Valor aproximado: ${valor_usdt:.2f} USDT")
    else:
        # Padrão: comprar valor mínimo (R$5)
        valor_usdt_dec = Decimal('5.0')
        quantidade_ada_calc = valor_usdt_dec / preco_atual
        quantidade_ada = float(quantidade_ada_calc)
        logger.info(f"💵 Valor padrão: $5.00 USDT")
        logger.info(f"🔢 Quantidade: {quantidade_ada:.2f} ADA")

    # Arredondar para 1 casa decimal (step size ADA na Binance é 0.1)
    quantidade_ada = round(quantidade_ada, 1)

    # Verificar valor mínimo da ordem (NOTIONAL mínimo = $5.00)
    valor_ordem_estimado = Decimal(str(quantidade_ada)) * preco_atual
    min_notional = Decimal('5.0')

    if valor_ordem_estimado < min_notional:
        # Ajustar quantidade para atingir o mínimo
        quantidade_minima = (min_notional / preco_atual).quantize(Decimal('0.1'), rounding='ROUND_UP')
        quantidade_ada = float(quantidade_minima)
        logger.warning(f"⚠️ Ajustando quantidade para valor mínimo ($5.00 USDT)")
        logger.info(f"🔢 Nova quantidade: {quantidade_ada:.1f} ADA")

    # Verificar mínimo (1 ADA na Binance)
    if quantidade_ada < 1.0:
        logger.error(f"❌ Quantidade muito baixa: {quantidade_ada:.2f} ADA (mínimo: 1 ADA)")
        logger.info("💡 Use pelo menos $0.80 USDT para comprar ao preço atual")
        return

    # Verificar saldo
    saldos = api.obter_saldos()
    saldo_usdt = Decimal('0')
    for saldo in saldos:
        if saldo['asset'] == 'USDT':
            saldo_usdt = Decimal(str(saldo['free']))
            break

    logger.info(f"💼 Saldo USDT disponível: ${saldo_usdt:.2f}")

    valor_ordem = Decimal(str(quantidade_ada)) * preco_atual
    if valor_ordem > saldo_usdt:
        logger.error(f"❌ Saldo insuficiente!")
        logger.error(f"   Necessário: ${valor_ordem:.2f} USDT")
        logger.error(f"   Disponível: ${saldo_usdt:.2f} USDT")
        return

    # Confirmar compra
    logger.info("\n" + "="*60)
    logger.info("⚠️  CONFIRMAR COMPRA MANUAL")
    logger.info("="*60)
    logger.info(f"   Quantidade: {quantidade_ada:.2f} ADA")
    logger.info(f"   Preço: ${preco_atual:.6f}")
    logger.info(f"   Total: ${valor_ordem:.2f} USDT")
    logger.info("="*60)

    resposta = input("\n🔔 Confirmar compra? (S/n): ").strip().lower()

    if resposta not in ['s', 'sim', 'y', 'yes', '']:
        logger.warning("❌ Compra cancelada pelo usuário")
        return

    # Executar ordem
    logger.info("\n📤 Executando ordem de compra...")

    try:
        ordem = api.criar_ordem_mercado(
            simbolo='ADAUSDT',
            lado='BUY',
            quantidade=quantidade_ada
        )

        if ordem and ordem.get('status') == 'FILLED':
            logger.info("\n" + "="*60)
            logger.info("✅ COMPRA MANUAL EXECUTADA COM SUCESSO!")
            logger.info("="*60)
            logger.info(f"   Quantidade: {quantidade_ada:.2f} ADA")
            logger.info(f"   Preço médio: ${preco_atual:.6f}")
            logger.info(f"   Total gasto: ${valor_ordem:.2f} USDT")
            logger.info(f"   Order ID: {ordem.get('orderId')}")
            logger.info("="*60)

            # Verificar novo saldo
            import time
            time.sleep(2)
            saldos_novos = api.obter_saldos()
            for saldo in saldos_novos:
                if saldo['asset'] == 'USDT':
                    novo_saldo_usdt = Decimal(str(saldo['free']))
                    logger.info(f"\n💼 Novo saldo USDT: ${novo_saldo_usdt:.2f}")
                elif saldo['asset'] == 'ADA':
                    novo_saldo_ada = Decimal(str(saldo['free']))
                    logger.info(f"🪙 Novo saldo ADA: {novo_saldo_ada:.2f} ADA")

        else:
            logger.error(f"❌ Erro ao executar ordem: {ordem}")

    except Exception as e:
        logger.error(f"❌ Erro ao executar compra: {e}")
        logger.exception("Traceback:")


def main():
    """Função principal"""
    import argparse

    parser = argparse.ArgumentParser(description='Compra manual de ADA')
    parser.add_argument(
        '--ada',
        type=float,
        help='Quantidade de ADA a comprar (ex: 10)'
    )
    parser.add_argument(
        '--usdt',
        type=float,
        help='Valor em USDT a gastar (ex: 5.0)'
    )

    args = parser.parse_args()

    comprar_ada_manual(
        quantidade_ada=args.ada,
        valor_usdt=args.usdt
    )

    logger.banner("✅ FINALIZADO")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Operação cancelada")
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        logger.exception("Traceback:")
