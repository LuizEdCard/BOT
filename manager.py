# manager.py
import json
import threading
import time
import os
from dotenv import load_dotenv

# Importa as classes que criamos
from src.exchange.binance_api import BinanceAPI
from src.exchange.kucoin_api import KucoinAPI
from src.core.bot_trading import TradingBot
from src.utils.logger import get_loggers # Supondo que a função agora retorne os 2 loggers

# Carrega as variáveis de ambiente (API keys) do arquivo .env
load_dotenv()

# Pega as instâncias dos loggers
logger, panel_logger = get_loggers()

def carregar_config_bot(nome_arquivo_bot):
    """Função auxiliar para carregar um arquivo de configuração JSON."""
    try:
        with open(nome_arquivo_bot, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"❌ Arquivo de configuração não encontrado: {nome_arquivo_bot}")
        return None
    except json.JSONDecodeError:
        logger.error(f"❌ Erro de formatação no arquivo JSON: {nome_arquivo_bot}")
        return None

def main():
    """Função principal que orquestra a inicialização dos bots."""
    logger.info("🚀 INICIANDO O GERENCIADOR DE BOTS...")
    
    # 1. Carregar configuração principal
    main_config = load_config('configs/config.json')
    manager_logger.info("✅ Configuração principal 'configs/config.json' carregada.")

    active_bots = main_config.get('bots_ativos', [])
    if not active_bots:
        manager_logger.warning("⚠️ Nenhum bot ativo encontrado em 'configs/config.json'. Encerrando.")
        sys.exit(0)

    threads = []
    for bot_name in active_bots:
        manager_logger.info(f"\n⚙️ Configurando bot: {bot_name}...")
        bot_config_file = f"configs/{bot_name}.json" # Assumindo que as configs dos bots estão na pasta 'configs'
        bot_config = load_config(bot_config_file)
        if not config_instancia:
            continue # Pula para o próximo bot se a config falhar

        api = None
        exchange_name = config_instancia.get('exchange')
        
        # Instancia a classe de API correta com base na configuração
        if exchange_name == 'binance':
            api = BinanceAPI(
                api_key=os.getenv(config_instancia['api_key_env']),
                api_secret=os.getenv(config_instancia['api_secret_env'])
            )
        elif exchange_name == 'kucoin':
            api = KucoinAPI(
                api_key=os.getenv(config_instancia['api_key_env']),
                api_secret=os.getenv(config_instancia['api_secret_env']),
                api_passphrase=os.getenv(config_instancia['api_passphrase_env'])
            )
        else:
            logger.error(f"❌ Exchange '{exchange_name}' não suportada para o bot '{config_instancia['nome_instancia']}'.")
            continue

        # Log de verificação para garantir que estamos a usar os dados corretos
        logger.info(f"✅ Configuração carregada: Lançando bot '{config_instancia['nome_instancia']}' para o par '{config_instancia['par']}' na exchange '{config_instancia['exchange']}'.")

        # Cria a instância do worker do bot, passando sua configuração e API específicas
        bot_worker = BotTrading(config=config_instancia, exchange_api=api)
        
        # Cria e inicia a thread para este bot
        thread = threading.Thread(target=bot_worker.run, name=config_instancia['nome_instancia'])
        thread.start()
        threads.append(thread)
        
        # Pequena pausa para não sobrecarregar as APIs na inicialização
        time.sleep(5) 

    logger.info(f"✅ {len(threads)} instâncias de bot iniciadas e a operar em background.")
    
    # Loop para manter o script principal vivo
    # No futuro, este loop será usado para montar o painel consolidado
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("🛑 Finalizando o gerenciador de bots...")

if __name__ == '__main__':
    main()