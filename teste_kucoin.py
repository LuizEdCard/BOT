# teste_kucoin.py
import os
from dotenv import load_dotenv
from src.exchange.kucoin_api import KucoinAPI
from pathlib import Path

print("🚀 Iniciando teste de conexão com a KuCoin...")

# Carrega as chaves do seu arquivo .env
load_dotenv(dotenv_path=Path(__file__).parent / 'config' / '.env')

try:
    # Pega as chaves específicas da KuCoin
    api_key = os.getenv('KUCOIN_API_KEY')
    api_secret = os.getenv('KUCOIN_API_SECRET')
    api_passphrase = os.getenv('KUCOIN_API_PASSPHRASE')

    if not all([api_key, api_secret, api_passphrase]):
        print("❌ ERRO: Verifique se as variáveis KUCOIN_API_KEY, KUCOIN_API_SECRET e KUCOIN_API_PASSPHRASE estão no seu arquivo .env")
    else:
        print("✅ Chaves carregadas do .env")

        # Cria uma instância da API da KuCoin
        kucoin_client = KucoinAPI(api_key, api_secret, api_passphrase)

        print("🔄 Tentando buscar saldos da conta...")

        # Tenta chamar um método simples, como buscar o saldo de USDT
        saldo_usdt = kucoin_client.get_saldo_disponivel('USDT')

        print("\n🎉 CONEXÃO BEM-SUCEDIDA! 🎉")
        print(f"Saldo de USDT detectado na KuCoin: {saldo_usdt} USDT")

except Exception as e:
    print(f"\n🔥 FALHA NA CONEXÃO! 🔥")
    print(f"Ocorreu um erro: {e}")
