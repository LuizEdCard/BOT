"""
Constantes e configurações centralizadas do Trading Bot

Contém mapeamentos de ícones, níveis de log e outras constantes
utilizadas em todo o projeto.
"""

# ═══════════════════════════════════════════════════════════════════
# SISTEMA DE ÍCONES
# ═══════════════════════════════════════════════════════════════════

class Icones:
    """Mapeamento centralizado de ícones para logs"""

    # Operações
    COMPRA = "🟢"
    VENDA = "🔴"
    AGUARDANDO = "🟡"

    # Estado
    STATUS = "📊"
    CAPITAL = "💰"
    SALDO = "💼"
    LUCRO = "📈"
    PREJUIZO = "📉"

    # Sistema
    OK = "✅"
    ERRO = "❌"
    AVISO = "⚠️"
    PROCESSANDO = "🔄"
    BLOQUEADO = "🔒"
    DESBLOQUEADO = "🔓"

    # Conexão
    CONECTADO = "🔌"
    DESCONECTADO = "🔌"
    API = "🌐"

    # Tempo
    TEMPO = "⏱️"
    AGENDADO = "⏰"
    COOLDOWN = "⌛"

    # Outros
    INICIALIZACAO = "🚀"
    IMPORTACAO = "📥"
    EXPORTACAO = "📤"
    HISTORICO = "📜"
    MERCADO = "📈"
    POSICAO = "💼"
    DEGRAU = "📶"
    META = "🎯"
    PICO = "⛰️"
    QUEDA = "📉"
    BANCO_DADOS = "💾"
    BACKUP = "💾"
    APORTE = "💵"


# ═══════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DE LOGGING
# ═══════════════════════════════════════════════════════════════════

class LogConfig:
    """Configuração do sistema de logging"""

    # Configuração padrão (Produção)
    DEFAULT = {
        'console': {
            'nivel': 'INFO',
            'formato': '%(asctime)s | %(levelname)s | %(message)s',
            'formato_data': '%H:%M:%S',  # Compacto
        },
        'arquivo': {
            'nivel': 'INFO',
            'formato': '%(levelname)-8s | %(asctime)s | %(name)s | %(message)s',
            'formato_data': '%Y-%m-%d %H:%M:%S',  # Completo
        }
    }

    # Modo Desenvolvimento
    DESENVOLVIMENTO = {
        'console': {
            'nivel': 'DEBUG',
            'formato': '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            'formato_data': '%H:%M:%S',
        },
        'arquivo': {
            'nivel': 'DEBUG',
            'formato': '%(levelname)-8s | %(asctime)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            'formato_data': '%Y-%m-%d %H:%M:%S',
        }
    }

    # Modo Monitoramento
    MONITORAMENTO = {
        'console': {
            'nivel': 'INFO',
            'formato': '%(asctime)s | %(message)s',
            'formato_data': '%H:%M',  # Ultra compacto
        },
        'arquivo': {
            'nivel': 'INFO',
            'formato': '%(levelname)-8s | %(asctime)s | %(name)s | %(message)s',
            'formato_data': '%Y-%m-%d %H:%M:%S',
        }
    }


# ═══════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DO PAINEL DE STATUS
# ═══════════════════════════════════════════════════════════════════

class PainelConfig:
    """Configuração do painel de status adaptativo"""

    # Intervalos base (em segundos)
    INTERVALO_NORMAL = 300      # 5 minutos
    INTERVALO_ALTA_VOL = 60     # 1 minuto
    INTERVALO_BAIXA_VOL = 600   # 10 minutos

    # Thresholds de volatilidade (%)
    VOLATILIDADE_ALTA = 5.0     # > 5% = alta volatilidade
    VOLATILIDADE_BAIXA = 1.0    # < 1% = baixa volatilidade

    # Janela de tempo para calcular volatilidade (segundos)
    JANELA_VOLATILIDADE = 3600  # 1 hora


# ═══════════════════════════════════════════════════════════════════
# OUTRAS CONSTANTES
# ═══════════════════════════════════════════════════════════════════

class Formatos:
    """Formatos padrão para exibição de números"""

    PRECO = '{:.6f}'           # 0.685000
    QUANTIDADE = '{:.2f}'       # 130.50
    VALOR_USDT = '{:.2f}'       # 89.40
    PERCENTUAL = '{:+.2f}%'     # +5.06%
    TEMPO_MIN = '{:.0f}min'     # 45min
    TEMPO_HORA = '{:.1f}h'      # 2.5h
