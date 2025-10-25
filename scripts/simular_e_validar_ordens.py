"""
Non-interactive simulation to validate timestamps and executed values.

- Loads a BINANCE_adausdt CSV with SimulatedExchangeAPI (current implementation).
- Performs a forced buy and sell to generate orders.
- Prints the last orders from the temp SQLite DB for inspection.

Usage:
  python scripts/simular_e_validar_ordens.py
"""
from __future__ import annotations
import sys
from pathlib import Path
from decimal import Decimal
import pandas as pd

# Ensure project root is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.bot_worker import BotWorker
from src.exchange.simulated_api import SimulatedExchangeAPI

# Config
PAR = 'ADA/USDT'
CSV_DIR = Path(r"e:\cardoso\Documentos\BOT\dados\historicos")
CSV_BASE = 'BINANCE_adausdt_30m_2017-01-01_2025-10-24.csv'
CSV_PATH = CSV_DIR / CSV_BASE

DB_TMP = Path(__file__).parent / 'dados' / 'sim_test.db'
STATE_TMP = Path(__file__).parent / 'dados' / 'sim_state.json'
DB_TMP.parent.mkdir(parents=True, exist_ok=True)

CONFIG = {
    'BOT_NAME': 'SimTest',
    'DATABASE_PATH': str(DB_TMP),
    'BACKUP_DIR': str(Path(__file__).parent / 'dados' / 'backups'),
    'STATE_FILE_PATH': str(STATE_TMP),
    'PERCENTUAL_RESERVA': 8,
    'par': PAR,
    'AMBIENTE': 'SIMULACAO',
    'CAPITAL_INICIAL': 200.0,
    'ESTRATEGIA_ATIVA': 'ambas',
    'INTERVALO_CICLO_SEGUNDOS': 1,
    # Disable RSI filter to avoid requiring rsi_limite_compra in minimal config
    'usar_filtro_rsi': False,
}


def main():
    if not CSV_PATH.exists():
        print(f"❌ CSV not found: {CSV_PATH}")
        return

    # Initialize simulated exchange (taxa_pct is percent, 0.1 => 0.1%)
    exchange = SimulatedExchangeAPI(
        caminho_csv=str(CSV_PATH),
        saldo_inicial=CONFIG['CAPITAL_INICIAL'],
        taxa_pct=0.1,
        timeframe_base='30m'
    )

    # Initialize bot (simulation mode)
    bot = BotWorker(CONFIG, exchange, modo_simulacao=True)

    # 1) Use first bar as timestamp for a test buy
    barra1 = exchange.get_barra_atual()
    if not barra1:
        print("❌ No bars available from CSV.")
        return
    preco1 = Decimal(str(barra1['close']))
    tempo1 = pd.to_datetime(barra1['timestamp']).to_pydatetime()
    bot.tempo_simulado_atual = tempo1

    oportunidade_compra = {
        'tipo': 'compra',
        'quantidade': Decimal('20') / preco1,  # placeholder quantity
        'preco_atual': preco1,
        'carteira': 'acumulacao',
        'motivo': 'Teste compra',
        'valor_ordem': Decimal('20'),
        'degrau': 'teste_1'
    }
    ok_compra = bot._executar_oportunidade_compra(oportunidade_compra)
    print(f"Compra executada: {ok_compra}")

    # 2) Advance to next bar and perform a test sell of all available asset
    barra2 = exchange.get_barra_atual()
    if not barra2:
        print("⚠️ Only one bar available; skipping sell.")
    else:
        preco2 = Decimal(str(barra2['close']))
        tempo2 = pd.to_datetime(barra2['timestamp']).to_pydatetime()
        bot.tempo_simulado_atual = tempo2

        quantidade_venda = float(exchange.get_saldo_disponivel('ADA'))  # sell entire position
        oportunidade_venda = {
            'tipo': 'venda',
            'quantidade_venda': quantidade_venda,
            'preco_atual': preco2,
            'carteira': 'acumulacao',
            'motivo': 'Teste venda'
        }
        ok_venda = bot._executar_oportunidade_venda(oportunidade_venda)
        print(f"Venda executada: {ok_venda}")

    # Show last orders from the temp DB
    try:
        from scripts.consultar_banco import ConsultorBanco
        consultor = ConsultorBanco(DB_TMP)
        consultor.ultimas_ordens(limite=20)
    except Exception as e:
        print(f"❌ Failed to inspect DB: {e}")


if __name__ == '__main__':
    main()