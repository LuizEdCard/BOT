import sys
from pathlib import Path

# Garantir import relativo ao projeto
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.exchange.simulated_api import SimulatedExchangeAPI

CSV_PATH = r"e:\cardoso\Documentos\BOT\dados\historicos\BINANCE_adausdt_4h_2018-01-01_2025-10-23.csv"

def main():
    api = SimulatedExchangeAPI(
        caminho_csv=CSV_PATH,
        saldo_inicial=1000.0,
        taxa_pct=0.1,
        timeframe_base='4h'
    )

    print(f"Linhas carregadas: {len(api.dados)}")
    print(f"Primeira barra: {api.dados.iloc[0].to_dict() if len(api.dados) > 0 else None}")

    # Testar get_barra_atual
    for i in range(3):
        barra = api.get_barra_atual()
        print(f"Barra {i}: {barra}")

    # Testar históricos iniciais com timeframe igual ao base
    hist_4h = api.get_dados_historicos_iniciais('4h', 5)
    print(f"Historico 4h (5 linhas): shape={hist_4h.shape}")

    # Testar históricos iniciais com timeframe menor que o base (espera DF vazio)
    hist_1h = api.get_dados_historicos_iniciais('1h', 5)
    print(f"Historico 1h (5 linhas): shape={hist_1h.shape}")

if __name__ == '__main__':
    main()