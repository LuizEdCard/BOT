import pandas as pd
import pathlib
import questionary
import os
from dotenv import load_dotenv
from src.exchange.binance_api import BinanceAPI
from src.exchange.kucoin_api import KucoinAPI

# Carregar variáveis de ambiente
load_dotenv('configs/.env')

def main():
    """
    Assistente interativo para baixar dados históricos de candles.
    """
    exchange = questionary.select(
        "Selecione a exchange:",
        choices=['binance', 'kucoin']
    ).ask()

    symbol = questionary.text("Digite o par de moedas (ex: ADA/USDT):").ask()
    timeframe = questionary.select(
        "Selecione o timeframe:",
        choices=['1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w']
    ).ask()
    start_date = questionary.text("Digite a data de início (YYYY-MM-DD):").ask()
    end_date = questionary.text("Digite a data de fim (YYYY-MM-DD):").ask()

    if exchange == 'binance':
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        if not api_key or not api_secret:
            print("Erro: API Keys da Binance não encontradas no arquivo .env")
            return
        api = BinanceAPI(api_key=api_key, api_secret=api_secret, base_url='https://api.binance.com')
    elif exchange == 'kucoin':
        api = KucoinAPI()
    else:
        print("Exchange inválida.")
        return

    try:
        ohlcv = api.fetch_ohlcv(symbol, timeframe, start_date, end_date)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Criar a pasta de dados históricos se não existir
        data_dir = pathlib.Path('dados/historicos')
        data_dir.mkdir(parents=True, exist_ok=True)

        # Salvar o arquivo
        filename = f'{exchange.upper()}_{symbol.replace("/", "")}_{timeframe}_{start_date}_{end_date}.csv'
        filepath = data_dir / filename
        df.to_csv(filepath, index=False)

        print(f"\nDados salvos com sucesso em: {filepath}")

    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    main()
