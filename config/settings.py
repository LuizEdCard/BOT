"""
═══════════════════════════════════════════════════════════════════
TRADING BOT - Configurações Globais
═══════════════════════════════════════════════════════════════════
Carrega configurações do .env e estrategia.json
"""

import os
import json
from pathlib import Path
from decimal import Decimal
from dotenv import load_dotenv


class Settings:
    """Gerencia todas as configurações do bot"""

    def __init__(self):
        # Diretórios base
        self.BASE_DIR = Path(__file__).parent.parent
        self.CONFIG_DIR = self.BASE_DIR / 'config'
        self.DADOS_DIR = self.BASE_DIR / 'dados'
        self.LOGS_DIR = self.BASE_DIR / 'logs'

        # Carregar .env
        env_path = self.CONFIG_DIR / '.env'
        if not env_path.exists():
            raise FileNotFoundError(
                f"❌ Arquivo .env não encontrado em {env_path}\n"
                f"   Copie config/.env.example para config/.env e configure suas API keys"
            )

        load_dotenv(env_path)

        # Carregar estrategia.json
        estrategia_path = self.CONFIG_DIR / 'estrategia.json'
        if not estrategia_path.exists():
            raise FileNotFoundError(f"❌ Arquivo estrategia.json não encontrado em {estrategia_path}")

        with open(estrategia_path, 'r', encoding='utf-8') as f:
            self.estrategia = json.load(f)

        # ═══════════════════════════════════════════════════════════
        # API BINANCE
        # ═══════════════════════════════════════════════════════════
        self.BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
        self.BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')

        if not self.BINANCE_API_KEY or not self.BINANCE_API_SECRET:
            raise ValueError(
                "❌ API keys não encontradas!\n"
                "   Configure BINANCE_API_KEY e BINANCE_API_SECRET no arquivo config/.env"
            )

        # ═══════════════════════════════════════════════════════════
        # AMBIENTE
        # ═══════════════════════════════════════════════════════════
        self.AMBIENTE = os.getenv('AMBIENTE', 'TESTNET').upper()

        if self.AMBIENTE == 'TESTNET':
            self.BINANCE_API_URL = 'https://testnet.binance.vision'
            self.BINANCE_WS_URL = 'wss://testnet.binance.vision/ws'
        else:
            self.BINANCE_API_URL = 'https://api.binance.com'
            self.BINANCE_WS_URL = 'wss://stream.binance.com:9443/ws'

        # ═══════════════════════════════════════════════════════════
        # CAPITAL
        # ═══════════════════════════════════════════════════════════
        self.CAPITAL_INICIAL = Decimal(os.getenv('CAPITAL_INICIAL', '180.00'))
        self.PERCENTUAL_CAPITAL_ATIVO = int(os.getenv('PERCENTUAL_CAPITAL_ATIVO', '92'))
        self.PERCENTUAL_RESERVA = int(os.getenv('PERCENTUAL_RESERVA', '8'))

        # ═══════════════════════════════════════════════════════════
        # LIMITES DE SEGURANÇA
        # ═══════════════════════════════════════════════════════════
        self.LIMITE_GASTO_DIARIO = Decimal(os.getenv('LIMITE_GASTO_DIARIO', '100.00'))
        self.VALOR_MINIMO_APORTE = Decimal(os.getenv('VALOR_MINIMO_APORTE', '10.00'))
        self.VALOR_MINIMO_ORDEM = Decimal(
            str(self.estrategia['limites_seguranca']['valor_minimo_ordem'])
        )

        # ═══════════════════════════════════════════════════════════
        # PARES DE TRADING
        # ═══════════════════════════════════════════════════════════
        self.PARES_ATIVOS = self.estrategia['pares_ativos']
        self.PAR_PRINCIPAL = self.PARES_ATIVOS[0]  # ADA/USDT

        # ═══════════════════════════════════════════════════════════
        # DEGRAUS E METAS
        # ═══════════════════════════════════════════════════════════
        self.DEGRAUS_COMPRA = self.estrategia['degraus_compra']
        self.METAS_VENDA = self.estrategia['metas_venda']

        # ═══════════════════════════════════════════════════════════
        # VENDAS DE SEGURANÇA (Estratégia Avançada)
        # ═══════════════════════════════════════════════════════════
        self.VENDAS_DE_SEGURANCA = self.estrategia.get('vendas_de_seguranca', [])

        # ═══════════════════════════════════════════════════════════
        # APORTES BRL (Verificação Periódica)
        # ═══════════════════════════════════════════════════════════
        self.APORTES = self.estrategia.get('aportes', {
            'intervalo_verificacao_minutos': 30,
            'valor_minimo_brl_para_converter': 50.0
        })

        # ═══════════════════════════════════════════════════════════
        # GESTÃO DE RISCO (Guardião Estratégico)
        # ═══════════════════════════════════════════════════════════
        self.GESTAO_DE_RISCO = self.estrategia.get('gestao_de_risco', {})
        self.GESTAO_DE_RISCO.setdefault('exposicao_maxima_percentual_capital', 70.0)
        self.GESTAO_DE_RISCO.setdefault('reativar_compras_apos_venda', True)
        self.GESTAO_DE_RISCO.setdefault('compras_de_oportunidade_extrema', [])

        # ═══════════════════════════════════════════════════════════
        # TAXAS
        # ═══════════════════════════════════════════════════════════
        self.TAXA_BINANCE = Decimal(str(self.estrategia['taxas']['binance_spot']))
        self.TAXA_ROUNDTRIP = Decimal(str(self.estrategia['taxas']['total_roundtrip']))

        # ═══════════════════════════════════════════════════════════
        # DETECÇÃO DE PICOS
        # ═══════════════════════════════════════════════════════════
        picos_cfg = self.estrategia['deteccao_picos']
        self.JANELA_CONFIRMACAO_MINUTOS = picos_cfg['janela_confirmacao_minutos']
        self.JANELA_HISTORICO_HORAS = picos_cfg['janela_historico_horas']
        self.TAMANHO_BUFFER_PRECOS = picos_cfg['tamanho_buffer_precos']

        # ═══════════════════════════════════════════════════════════
        # VOLATILIDADE
        # ═══════════════════════════════════════════════════════════
        vol_cfg = self.estrategia['volatilidade']
        self.LIMITE_ALTA_VOLATILIDADE = Decimal(str(vol_cfg['limite_alta_volatilidade']))
        self.REDUCAO_INTERVALOS_PERCENTUAL = vol_cfg['reducao_intervalos_percentual']
        self.QUEDA_EMERGENCIAL_PERCENTUAL = Decimal(str(vol_cfg['queda_emergencial_percentual']))
        self.TEMPO_EMERGENCIAL_HORAS = vol_cfg['tempo_emergencial_horas']

        # ═══════════════════════════════════════════════════════════
        # LOGGING
        # ═══════════════════════════════════════════════════════════
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.LOG_RETENTION_DAYS = int(os.getenv('LOG_RETENTION_DAYS', '30'))

        # ═══════════════════════════════════════════════════════════
        # TIMEOUTS E RETRIES
        # ═══════════════════════════════════════════════════════════
        self.REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
        self.MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
        self.INTERVALO_VERIFICACAO_SALDO = int(os.getenv('INTERVALO_VERIFICACAO_SALDO', '3600'))

        # ═══════════════════════════════════════════════════════════
        # CONTROLE DE COMPRAS - COOLDOWN DUPLO + DCA INTELIGENTE
        # ═══════════════════════════════════════════════════════════
        # NOVO SISTEMA: Cooldown global após qualquer compra (minutos)
        self.COOLDOWN_GLOBAL_APOS_COMPRA_MINUTOS = int(
            self.estrategia.get('cooldown_global_apos_compra_minutos', 30)
        )

        # DCA INTELIGENTE: Percentual mínimo de melhora do preço médio para comprar
        # Ex: 2.0 = só compra se preço atual for 2% menor que preço médio
        self.PERCENTUAL_MINIMO_MELHORA_PM = Decimal(
            str(self.estrategia.get('percentual_minimo_melhora_pm', 2.0))
        )

        # ═══════════════════════════════════════════════════════════
        # NOTIFICAÇÕES (FUTURO)
        # ═══════════════════════════════════════════════════════════
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

        # ═══════════════════════════════════════════════════════════
        # BANCO DE DADOS
        # ═══════════════════════════════════════════════════════════
        self.DATABASE_PATH = self.DADOS_DIR / 'trading_bot.db'
        self.BACKUP_DIR = self.DADOS_DIR / 'backup'
        self.RELATORIOS_DIR = self.DADOS_DIR / 'relatorios'

        # Criar diretórios se não existirem
        self._criar_diretorios()

    def _criar_diretorios(self):
        """Cria diretórios necessários"""
        self.DADOS_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)
        self.BACKUP_DIR.mkdir(exist_ok=True)
        self.RELATORIOS_DIR.mkdir(exist_ok=True)

    def validar(self):
        """Valida configurações críticas"""
        erros = []

        # Validar API keys
        if self.BINANCE_API_KEY == 'your_api_key_here':
            erros.append("BINANCE_API_KEY não foi configurada (ainda é o valor padrão)")

        if self.BINANCE_API_SECRET == 'your_api_secret_here':
            erros.append("BINANCE_API_SECRET não foi configurada (ainda é o valor padrão)")

        # Validar percentuais
        if self.PERCENTUAL_CAPITAL_ATIVO + self.PERCENTUAL_RESERVA != 100:
            erros.append(
                f"Percentuais devem somar 100% "
                f"(atual: {self.PERCENTUAL_CAPITAL_ATIVO}% + {self.PERCENTUAL_RESERVA}%)"
            )

        # Validar capital
        if self.CAPITAL_INICIAL <= 0:
            erros.append(f"Capital inicial deve ser > 0 (atual: {self.CAPITAL_INICIAL})")

        if erros:
            raise ValueError(
                "❌ Erros de configuração:\n" +
                "\n".join(f"   - {erro}" for erro in erros)
            )

    def info(self):
        """Retorna informações de configuração (sem secrets)"""
        return {
            'ambiente': self.AMBIENTE,
            'par_principal': self.PAR_PRINCIPAL,
            'capital_inicial': float(self.CAPITAL_INICIAL),
            'capital_ativo_pct': self.PERCENTUAL_CAPITAL_ATIVO,
            'reserva_pct': self.PERCENTUAL_RESERVA,
            'limite_gasto_diario': float(self.LIMITE_GASTO_DIARIO),
            'degraus_compra': len(self.DEGRAUS_COMPRA),
            'metas_venda': len(self.METAS_VENDA),
            'log_level': self.LOG_LEVEL,
            'api_url': self.BINANCE_API_URL,
            'ws_url': self.BINANCE_WS_URL
        }


# Instância global de configurações
settings = Settings()


# Função de conveniência para obter configurações
def get_settings():
    """Retorna a instância global de configurações"""
    return settings
