# manager.py
import json
import threading
import time
import os
import sys
import psutil
from datetime import datetime
from dotenv import load_dotenv
from decimal import Decimal
from pathlib import Path

# Importa as classes que criamos
from src.exchange.binance_api import BinanceAPI
from src.exchange.kucoin_api import KucoinAPI
from src.core.bot_worker import BotWorker
from src.telegram_bot import TelegramBot
from src.utils.logger import get_loggers # Supondo que a função agora retorne os 2 loggers

# Carrega as variáveis de ambiente (API keys) do arquivo .env
load_dotenv('configs/.env')

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

def mesclar_configuracoes(config_bot, config_estrategia):
    """Mescla configuração do bot com configuração de estratégia."""
    config_mesclada = config_bot.copy()

    for key, value in config_estrategia.items():
        upper_key = key.upper()
        if upper_key in config_mesclada and isinstance(config_mesclada[upper_key], dict) and isinstance(value, dict):
            config_mesclada[upper_key].update(value)
        else:
            config_mesclada[upper_key] = value

    return config_mesclada

def gerar_relatorio_detalhado(bot_workers, inicio_gerente):
    """
    Gera relatório horário detalhado com métricas de sistema e bots.

    Args:
        bot_workers: Lista de workers ativos
        inicio_gerente: Timestamp de início do gerenciador

    Returns:
        str: Mensagem formatada em Markdown para Telegram
    """
    try:
        # Coletar métricas do sistema
        cpu_percent = psutil.cpu_percent(interval=1)
        memoria = psutil.virtual_memory()
        memoria_percent = memoria.percent

        # Calcular uptime do gerenciador
        uptime_gerente = datetime.now() - inicio_gerente
        horas = int(uptime_gerente.total_seconds() // 3600)
        minutos = int((uptime_gerente.total_seconds() % 3600) // 60)
        uptime_str = f"{horas}h {minutos}m"

        # Coletar tamanhos dos bancos de dados
        db_info = []
        for worker in bot_workers:
            try:
                db_path = Path(worker.config.get('DATABASE_PATH', ''))
                if db_path.exists():
                    tamanho_mb = os.path.getsize(db_path) / (1024 * 1024)
                    exchange = worker.config.get('exchange', 'Unknown').title()
                    db_info.append(f"DB {exchange}: {tamanho_mb:.2f} MB")
            except:
                pass

        # Status das threads
        threads_status = []
        for worker in bot_workers:
            nome = worker.config.get('nome_instancia', 'N/A')
            ativo = "✅" if worker.rodando else "❌"
            threads_status.append(f"[{nome} {ativo}]")

        # Timestamp atual
        timestamp_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Construir cabeçalho do relatório
        linhas = [
            "🔔 *RELATÓRIO DE INTELIGÊNCIA DOS BOTS*",
            "-----------------------------------",
            f"Atualizado em: `{timestamp_atual}`",
            "",
            "💻 *SAÚDE DO SISTEMA*",
            f"CPU: *{cpu_percent:.1f}%* | Memória: *{memoria_percent:.1f}%*",
        ]

        if db_info:
            linhas.append(" | ".join(db_info))

        linhas.extend([
            f"Uptime do Gerente: *{uptime_str}*",
            f"Threads: {' '.join(threads_status)}",
            "-----------------------------------",
            ""
        ])

        # Coletar informações de cada bot
        total_capital_global = Decimal('0')
        total_lucro_nao_realizado = Decimal('0')
        total_lucro_realizado_24h = Decimal('0')

        for worker in bot_workers:
            try:
                status = worker.get_status_dict()

                nome = status.get('nome_instancia', 'N/A')
                par = status.get('par', 'N/A')
                estado = status.get('estado_bot', 'N/A')

                # Dados de posição
                posicao = status.get('status_posicao', {})
                quantidade = posicao.get('quantidade', 0)
                preco_medio = posicao.get('preco_medio', 0)
                lp_pct = posicao.get('lucro_percentual', 0)
                lp_usdt = posicao.get('lucro_usdt', 0)

                # Dados 24h
                compras_24h = status.get('compras_24h', 0)
                vendas_24h = status.get('vendas_24h', 0)
                lucro_realizado_24h = status.get('lucro_realizado_24h', 0)

                # Saldo disponível
                saldo_usdt = status.get('saldo_disponivel_usdt', 0)
                valor_posicao = posicao.get('valor_total', 0)

                # Atualizar totais globais
                total_capital_global += Decimal(str(saldo_usdt)) + Decimal(str(valor_posicao))
                total_lucro_nao_realizado += Decimal(str(lp_usdt))
                total_lucro_realizado_24h += Decimal(str(lucro_realizado_24h))

                # Formatar seção do bot
                ativo_base = par.split('/')[0] if '/' in par else 'N/A'
                exchange = worker.config.get('exchange', 'Unknown').title()

                linhas.extend([
                    f"🤖 *BOT: {nome}-{exchange}* `({par})`",
                    f"*Estado:* {estado}",
                    f"*Posição:* `{quantidade:.1f} {ativo_base}` @ `${preco_medio:.4f}`",
                    f"*L/P Posição:* {lp_pct:+.2f}% ({lp_usdt:+.2f} USDT)",
                    f"*Desempenho 24h:* {compras_24h} Compra(s) | {vendas_24h} Venda(s)",
                    f"*Lucro Realizado 24h:* {lucro_realizado_24h:+.2f} USDT",
                    ""
                ])

            except Exception as e:
                logger.error(f"❌ Erro ao processar status do bot {worker.config.get('nome_instancia', 'N/A')}: {e}")
                linhas.extend([
                    f"🤖 *BOT: {worker.config.get('nome_instancia', 'N/A')}*",
                    f"*Estado:* ❌ ERRO ao coletar dados",
                    ""
                ])

        # Resumo final
        linhas.extend([
            "-----------------------------------",
            "🌐 *RESUMO FINANCEIRO GLOBAL*",
            f"*Capital Total:* `${total_capital_global:.2f} USDT`",
            f"*L/P Global (Não Realizado):* {total_lucro_nao_realizado:+.2f} USDT",
            f"*Lucro Global (Realizado 24h):* {total_lucro_realizado_24h:+.2f} USDT"
        ])

        return "\n".join(linhas)

    except Exception as e:
        logger.error(f"❌ Erro ao gerar relatório detalhado: {e}")
        return f"❌ Erro ao gerar relatório: {str(e)}"

def main():
    """Função principal que orquestra a inicialização dos bots."""
    logger.info("🚀 INICIANDO O GERENCIADOR DE BOTS...")

    # Timestamp de início do gerenciador
    inicio_gerente = datetime.now()

    main_config = carregar_config_bot('configs/config.json')
    if not main_config:
        logger.error("❌ Não foi possível carregar a configuração principal")
        sys.exit(1)

    logger.info("✅ Configuração principal 'configs/config.json' carregada.")

    # Carregar configuração do relatório horário
    relatorio_config = main_config.get('relatorio_horario', {})
    relatorio_habilitado = relatorio_config.get('habilitado', False)
    intervalo_horas = relatorio_config.get('intervalo_horas', 1)
    ultimo_relatorio_timestamp = time.time() if relatorio_habilitado else None

    # Flag de controle de desligamento
    shutdown_flag = {'shutdown': False}

    active_bots = main_config.get('bots_ativos', [])
    if not active_bots:
        logger.warning("⚠️ Nenhum bot ativo encontrado em 'configs/config.json'. Encerrando.")
        sys.exit(0)

    bot_workers = []
    threads = []
    for bot_name in active_bots:
        logger.info(f"\n⚙️ Configurando bot: {bot_name}...")
        bot_config_file = f"configs/{bot_name}.json"
        config_instancia = carregar_config_bot(bot_config_file)
        if not config_instancia:
            continue
        
        config_estrategia = carregar_config_bot('configs/estrategia.json')
        if not config_estrategia:
            logger.error("❌ Não foi possível carregar a configuração de estratégia")
            continue
        
        config_instancia = mesclar_configuracoes(config_instancia, config_estrategia)
        logger.info("✅ Configurações de bot e estratégia mescladas")
        
        if 'GESTAO_DE_RISCO' in config_instancia:
            logger.info(f"🔍 GESTAO_DE_RISCO presente com chaves: {list(config_instancia['GESTAO_DE_RISCO'].keys())}")
        if 'DEGRAUS_COMPRA' in config_instancia:
            logger.info(f"🔍 DEGRAUS_COMPRA presente com {len(config_instancia['DEGRAUS_COMPRA'])} degraus")

        api = None
        exchange_name = config_instancia.get('exchange')
        
        if exchange_name == 'binance':
            api = BinanceAPI(
                api_key=os.getenv(config_instancia['api_key_env']),
                api_secret=os.getenv(config_instancia['api_secret_env']),
                base_url='https://api.binance.com'
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

        logger.info(f"✅ Configuração carregada: Lançando bot '{config_instancia['nome_instancia']}' para o par '{config_instancia['par']}' na exchange '{config_instancia['exchange']}'.")

        bot_worker = BotWorker(config=config_instancia, exchange_api=api)
        bot_workers.append(bot_worker)
        
        thread = threading.Thread(target=bot_worker.run, name=config_instancia['nome_instancia'])
        thread.start()
        threads.append(thread)
        
        time.sleep(5) 

    logger.info(f"✅ {len(threads)} instâncias de bot iniciadas e a operar em background.")

    # Função de desligamento gracioso
    def shutdown_callback():
        """Callback para desligar todos os bots graciosamente"""
        logger.info("🛑 Iniciando desligamento gracioso...")
        shutdown_flag['shutdown'] = True
        
        # Parar todos os workers
        for worker in bot_workers:
            worker.rodando = False
            logger.info(f"🛑 Sinalizando parada para {worker.config.get('nome_instancia', 'Worker')}")
        
        # Aguardar threads finalizarem (com timeout)
        logger.info("⏳ Aguardando threads finalizarem...")
        for thread in threads:
            thread.join(timeout=10)
            if thread.is_alive():
                logger.warning(f"⚠️  Thread {thread.name} não finalizou no tempo esperado")
            else:
                logger.info(f"✅ Thread {thread.name} finalizada")
        
        logger.info("✅ Todos os bots foram parados")
        logger.info("🛑 Encerrando processo principal...")
        sys.exit(0)
    
    # Inicia o bot do Telegram
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    authorized_user_id = os.getenv("TELEGRAM_AUTHORIZED_USER_ID")
    telegram_bot = None

    if telegram_token and authorized_user_id:
        logger.info("🤖 Iniciando o bot do Telegram...")
        telegram_bot = TelegramBot(
            token=telegram_token, 
            authorized_user_id=int(authorized_user_id), 
            workers=bot_workers,
            shutdown_callback=shutdown_callback
        )
        
        def run_telegram_bot():
            import asyncio
            asyncio.run(telegram_bot.run())
        
        telegram_thread = threading.Thread(target=run_telegram_bot, name="TelegramBot")
        telegram_thread.daemon = True
        telegram_thread.start()
        logger.info("✅ Bot do Telegram iniciado em background.")
    else:
        logger.warning("⚠️  Variáveis de ambiente do Telegram (TELEGRAM_BOT_TOKEN, TELEGRAM_AUTHORIZED_USER_ID) não configuradas. Bot do Telegram não iniciado.")

    try:
        while not shutdown_flag['shutdown']:
            panel_logger.info("\n" + 
"╔══════════════════════════════════════════════════════════════════════════════╗\n" + 
"║                                PAINEL DE STATUS CONSOLIDADO                                \n" + 
"╚══════════════════════════════════════════════════════════════════════════════╝")
            total_capital_global = Decimal('0')
            total_lucro_usdt_global = Decimal('0')
            quote_currency = 'USDT' # Moeda de cotação padrão

            for worker in bot_workers:
                try:
                    status = worker.get_status_dict()
                except Exception as e:
                    logger.warning(f'Falha ao obter status do bot {worker.config.get("nome_instancia", "Desconhecido")}: {e}')
                    status = {
                        'nome_instancia': worker.config.get("nome_instancia", "Desconhecido"), 
                        'par': worker.config.get("par", "N/A"),
                        'estado_bot': 'ERRO DE COMUNICAÇÃO',
                        'error': str(e)
                    }

                if 'error' in status:
                    panel_logger.info(f"║ 🤖 Bot: {status.get('nome_instancia', 'N/A')} ({status.get('par', 'N/A')}) - {status.get('estado_bot', 'ERRO')}: {status.get('error', 'Desconhecido')}")
                    panel_logger.info("╟──────────────────────────────────────────────────────────────────────────────╢")
                    continue

                # Extrair dados do status
                par = status.get('par', 'N/A')
                ativo_base = status.get('ativo_base', par.split('/')[0] if '/' in par else 'N/A')
                quote_currency = par.split('/')[1] if '/' in par else 'USDT'
                posicao = status.get('status_posicao', {})
                saldo_usdt_disponivel = status.get('saldo_disponivel_usdt', Decimal('0'))
                valor_posicao_usdt = posicao.get('valor_total', Decimal('0'))

                # Calcular totais globais
                total_capital_global += valor_posicao_usdt + saldo_usdt_disponivel
                total_lucro_usdt_global += posicao.get('lucro_usdt', Decimal('0'))

                # Imprimir informações do bot
                panel_logger.info(f"║ 🤖 Bot: {status['nome_instancia']} ({par}) | 🕒 Uptime: {status['uptime']}")
                panel_logger.info(f"║    🧠 Estado: {status['estado_bot']}")
                panel_logger.info(f"║    💰 Saldo {quote_currency}: ${saldo_usdt_disponivel:.2f}")
                
                preco_atual_str = f"${status.get('preco_atual', 0):.6f}"
                sma_ref_str = f"${status.get('sma_referencia', 0):.6f}" if status.get('sma_referencia') is not None else "N/A"
                dist_sma_str = f"{status.get('distancia_sma', 0):.2f}%" if status.get('distancia_sma') is not None else "N/A"
                panel_logger.info(f"║    📈 Preço {ativo_base}: {preco_atual_str} | SMA Ref: {sma_ref_str} | Dist SMA: {dist_sma_str}")
                
                pm_str = f"${posicao.get('preco_medio', 0):.6f}" if posicao.get('preco_medio') else "N/A"
                panel_logger.info(f"║    📊 Posição: {posicao.get('quantidade', 0):.2f} {ativo_base} | PM: {pm_str} | Total: ${valor_posicao_usdt:.2f}")
                
                lp_perc_str = f"{posicao.get('lucro_percentual', 0):.2f}%" if posicao.get('lucro_percentual') is not None else "N/A"
                lp_usdt_str = f"${posicao.get('lucro_usdt', 0):.2f}"
                panel_logger.info(f"║    💹 L/P: {lp_perc_str} ({lp_usdt_str})")

                if status.get('ultima_compra'):
                    compra = status['ultima_compra']
                    panel_logger.info(f"║    🟢 Última Compra: {compra.get('quantidade', 0):.2f} {ativo_base} @ ${compra.get('preco', 0):.6f} em {compra.get('timestamp', 'N/A')}")
                if status.get('ultima_venda'):
                    venda = status['ultima_venda']
                    lucro_venda_str = f"${venda.get('lucro_usdt', 0):.2f}" if venda.get('lucro_usdt') is not None else "N/A"
                    panel_logger.info(f"║    🔴 Última Venda: {venda.get('quantidade', 0):.2f} {ativo_base} @ ${venda.get('preco', 0):.6f} em {venda.get('timestamp', 'N/A')} (Lucro: {lucro_venda_str})")
                
                panel_logger.info("╟──────────────────────────────────────────────────────────────────────────────╢")

            panel_logger.info(f"║ 🌐 SUMMARY TOTAL: Capital Total: ${total_capital_global:.2f} {quote_currency} | L/P Global: ${total_lucro_usdt_global:.2f} {quote_currency}")
            panel_logger.info("╚══════════════════════════════════════════════════════════════════════════════╝")
            
            # Verificar se é hora de enviar relatório horário via Telegram
            if relatorio_habilitado and telegram_bot and authorized_user_id:
                tempo_decorrido = time.time() - ultimo_relatorio_timestamp
                intervalo_segundos = intervalo_horas * 3600

                if tempo_decorrido >= intervalo_segundos:
                    logger.info("📊 Gerando relatório horário detalhado para envio via Telegram...")

                    # Gerar relatório completo usando a nova função
                    mensagem_relatorio = gerar_relatorio_detalhado(bot_workers, inicio_gerente)

                    # Enviar mensagem via Telegram
                    try:
                        import asyncio
                        # Criar task para enviar mensagem via Telegram de forma assíncrona
                        asyncio.run(telegram_bot.enviar_mensagem(
                            user_id=int(authorized_user_id),
                            mensagem=mensagem_relatorio
                        ))
                        logger.info("✅ Relatório horário enviado via Telegram com sucesso!")
                    except Exception as e:
                        logger.error(f"❌ Erro ao enviar relatório via Telegram: {e}")
                        logger.info(f"📊 Conteúdo do relatório:\n{mensagem_relatorio}")

                    ultimo_relatorio_timestamp = time.time()
            
            time.sleep(300)
            
    except KeyboardInterrupt:
        logger.info("🛑 Interrupção detectada (Ctrl+C)...")
        shutdown_callback()
    
    # Se chegou aqui por shutdown remoto
    if shutdown_flag['shutdown']:
        logger.info("🛑 Desligamento remoto concluído")
    
    logger.info("🛑 Finalizando o gerenciador de bots...")

if __name__ == '__main__':
    main()
