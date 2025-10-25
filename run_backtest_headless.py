import json
from pathlib import Path
from decimal import Decimal

from src.exchange.simulated_api import SimulatedExchangeAPI
from src.core.bot_worker import BotWorker
import os

BASE = Path(__file__).parent

# Carregar template de configuração
config_path = BASE / 'configs' / 'backtest_template.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# Ajustes mínimos para execução headless
config['DATABASE_PATH'] = str(BASE / 'dados' / 'backtest_temp.db')
config['BACKUP_DIR'] = str(BASE / 'dados' / 'backups')
config['STATE_FILE_PATH'] = str(BASE / 'dados' / 'backtest_state_temp.json')
config['CAPITAL_INICIAL'] = 1000.0
config['VALOR_MINIMO_ORDEM'] = 5.0
config['AMBIENTE'] = 'backtest'
config['par'] = 'ADA/USDT'

# Habilitar estratégias explicitamente
config['ESTRATEGIA_ATIVA'] = 'ambas'
if 'ESTRATEGIAS' not in config:
    config['ESTRATEGIAS'] = {}
config['ESTRATEGIAS']['dca'] = {'habilitado': True}
config['ESTRATEGIAS']['giro_rapido'] = {'habilitado': True}

# Usar um CSV existente (4h ou 30m). Preferir 4h para velocidade.
csv_path = BASE / 'dados' / 'historicos' / 'BINANCE_adausdt_4h_2017-01-01_2025-10-23.csv'
if not csv_path.exists():
    csv_path = BASE / 'dados' / 'historicos' / 'BINANCE_adausdt_30m_2017-01-01_2025-10-24.csv'

print(f"Usando CSV: {csv_path}")

# Garantir que a execução headless comece limpa: remover DB/temp state se existirem
db_path = Path(config['DATABASE_PATH'])
state_path = Path(config['STATE_FILE_PATH'])
if db_path.exists():
    try:
        os.remove(db_path)
        print(f"Arquivo de DB existente removido: {db_path}")
    except Exception as e:
        print(f"Não foi possível remover {db_path}: {e}")
if state_path.exists():
    try:
        os.remove(state_path)
        print(f"Arquivo de state existente removido: {state_path}")
    except Exception as e:
        print(f"Não foi possível remover {state_path}: {e}")

# Instanciar API simulada
exchange_api = SimulatedExchangeAPI(
    caminho_csv=str(csv_path),
    saldo_inicial=float(config.get('CAPITAL_INICIAL', 1000.0)),
    taxa_pct=0.1,
    timeframe_base='4h'
)

# Ajustar capital inicial interno do GestaoCapital via BotWorker inicialization
bot = BotWorker(config=config, exchange_api=exchange_api, modo_simulacao=True)

# Executar a simulação
bot.run()

# Resultado
res = exchange_api.get_resultados()
print('\nResumo da simulação:')
print(f"Trades executados: {len(res.get('trades', []))}")
print(f"Saldo final USDT: {res.get('saldo_final_usdt')}")
print(f"Saldo final ativo: {res.get('saldo_final_ativo')}")
print('\nLista de trades (primeiras 10):')
for t in res.get('trades', [])[:10]:
    print(t)
