"""
═══════════════════════════════════════════════════════════════════
TRADING BOT - Sistema de Logging Configurável
═══════════════════════════════════════════════════════════════════
Logger centralizado com suporte a:
- Configuração dinâmica de formatos e níveis
- Timestamps diferentes para console e arquivo
- Cores no console
- Sistema de ícones padronizado
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from colorama import Fore, Style, init

from .constants import Icones, LogConfig

# Inicializar colorama
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """Formatter com cores para o console"""

    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        # Adicionar contexto se não existir (evita erro de formatação)
        if not hasattr(record, 'context'):
            record.context = ''

        # Adicionar cor ao nível
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"

        # Formatar
        result = super().format(record)

        # Restaurar levelname original
        record.levelname = levelname

        return result


class Logger:
    """
    Sistema de logging centralizado e configurável

    Recursos:
    - Configuração dinâmica de formatos e níveis
    - Timestamps diferentes para console (compacto) e arquivo (completo)
    - Cores no console
    - Sistema de ícones padronizado
    - Thread-safe
    """

    def __init__(
        self,
        nome: str = 'TradingBot',
        log_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        console: bool = True
    ):
        """
        Inicializa o logger

        Args:
            nome: Nome do logger
            log_dir: Diretório para arquivos de log
            config: Dicionário de configuração (usa LogConfig.DEFAULT se None)
            console: Se deve exibir logs no console
        """
        self.nome = nome
        self.config = config or LogConfig.DEFAULT

        # Criar logger
        self.logger = logging.getLogger(nome)
        self.logger.setLevel(logging.DEBUG)  # Nível mais baixo, filtros nos handlers
        self.logger.handlers.clear()  # Limpar handlers existentes

        # Handler para console
        if console:
            self._adicionar_handler_console()

        # Handler para arquivo
        if log_dir:
            self._adicionar_handler_arquivo(log_dir)

    def _parse_nivel(self, nivel: str) -> int:
        """Converte string de nível para constante logging"""
        niveis = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return niveis.get(nivel.upper(), logging.INFO)

    def _adicionar_handler_console(self):
        """Adiciona handler para console com cores e formato configurável"""
        console_handler = logging.StreamHandler(sys.stdout)

        # Obter configuração do console
        console_config = self.config.get('console', {})
        nivel = self._parse_nivel(console_config.get('nivel', 'INFO'))
        formato = console_config.get('formato', '%(asctime)s | %(levelname)s | [%(context)s] | %(message)s')
        formato_data = console_config.get('formato_data', '%H:%M:%S')

        console_handler.setLevel(nivel)

        # Formato com cores
        formatter = ColoredFormatter(formato, datefmt=formato_data)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)

    def _adicionar_handler_arquivo(self, log_dir: Path):
        """Adiciona handler para arquivo com formato configurável"""
        # Criar diretório se não existir
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Nome do arquivo com data
        hoje = datetime.now().strftime('%Y-%m-%d')
        log_file = log_dir / f'sistema_{hoje}.log'

        # Handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')

        # Obter configuração do arquivo
        arquivo_config = self.config.get('arquivo', {})
        nivel = self._parse_nivel(arquivo_config.get('nivel', 'INFO'))
        formato = arquivo_config.get('formato', '%(levelname)-8s | %(asctime)s | [%(context)s] | %(name)s | %(message)s')
        formato_data = arquivo_config.get('formato_data', '%Y-%m-%d %H:%M:%S')

        file_handler.setLevel(nivel)

        # Formatter customizado para arquivo (adiciona context se não existir)
        class ContextFormatter(logging.Formatter):
            def format(self, record):
                if not hasattr(record, 'context'):
                    record.context = ''
                return super().format(record)

        formatter = ContextFormatter(formato, datefmt=formato_data)
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    # ═══════════════════════════════════════════════════════════
    # MÉTODOS DE LOG BÁSICOS
    # ═══════════════════════════════════════════════════════════

    def debug(self, mensagem: str):
        """Log nível DEBUG"""
        self.logger.debug(mensagem)

    def info(self, mensagem: str):
        """Log nível INFO"""
        self.logger.info(mensagem)

    def warning(self, mensagem: str):
        """Log nível WARNING"""
        self.logger.warning(mensagem)

    def error(self, mensagem: str, exc_info: bool = False):
        """Log nível ERROR"""
        self.logger.error(mensagem, exc_info=exc_info)

    def critical(self, mensagem: str):
        """Log nível CRITICAL"""
        self.logger.critical(mensagem)

    def exception(self, mensagem: str):
        """Log exceção com traceback"""
        self.logger.exception(mensagem)

    # ═══════════════════════════════════════════════════════════
    # MÉTODOS ESPECIALIZADOS COM ÍCONES
    # ═══════════════════════════════════════════════════════════

    def operacao_compra(
        self,
        par: str,
        quantidade: float,
        preco: float,
        degrau: int,
        queda_pct: float
    ):
        """Log de operação de compra"""
        msg = (
            f"{Icones.COMPRA} COMPRA | {par} | "
            f"Qtd: {quantidade:.4f} | "
            f"Preço: ${preco:.6f} | "
            f"Degrau: {degrau} | "
            f"Queda: {queda_pct:.2f}%"
        )
        self.info(msg)

    def operacao_venda(
        self,
        par: str,
        quantidade: float,
        preco: float,
        meta: int,
        lucro_pct: float,
        lucro_usd: float
    ):
        """Log de operação de venda"""
        icone = Icones.LUCRO if lucro_pct > 0 else Icones.PREJUIZO
        msg = (
            f"{Icones.VENDA} VENDA | {par} | "
            f"Qtd: {quantidade:.4f} | "
            f"Preço: ${preco:.6f} | "
            f"Meta: {meta} | "
            f"{icone} Lucro: {lucro_pct:.2f}% (${lucro_usd:.2f})"
        )
        self.info(msg)

    def pico_detectado(self, par: str, preco: float, confirmado: bool = False):
        """Log de detecção de pico"""
        status = "CONFIRMADO" if confirmado else "CANDIDATO"
        msg = f"{Icones.PICO} PICO {status} | {par} | Preço: ${preco:.6f}"
        self.info(msg)

    def capital_atualizado(
        self,
        capital_ativo: float,
        reserva: float,
        total: float,
        motivo: str = ''
    ):
        """Log de atualização de capital"""
        msg = (
            f"{Icones.CAPITAL} CAPITAL | "
            f"Ativo: ${capital_ativo:.2f} | "
            f"Reserva: ${reserva:.2f} | "
            f"Total: ${total:.2f}"
        )
        if motivo:
            msg += f" | {motivo}"
        self.info(msg)

    def aporte_detectado(self, valor: float, moeda: str = 'USD', usdt_recebido: float = None):
        """Log de aporte"""
        if moeda == 'BRL' and usdt_recebido:
            msg = f"{Icones.APORTE} APORTE DETECTADO | R$ {valor:.2f} BRL → ${usdt_recebido:.2f} USDT"
        else:
            msg = f"{Icones.APORTE} APORTE DETECTADO | Valor: ${valor:.2f}"
        self.info(msg)

    def saldo_atualizado(self, moeda: str, valor: float):
        """Log de saldo atualizado"""
        if moeda == 'USDT':
            msg = f"{Icones.SALDO} SALDO ATUALIZADO | ${valor:.2f} {moeda}"
        elif moeda == 'BRL':
            msg = f"{Icones.SALDO} SALDO ATUALIZADO | R$ {valor:.2f} {moeda}"
        else:
            msg = f"{Icones.SALDO} SALDO ATUALIZADO | {valor:.4f} {moeda}"
        self.info(msg)

    def erro_api(self, endpoint: str, erro: str, tentativa: int = 1):
        """Log de erro de API"""
        msg = f"{Icones.AVISO} ERRO API | Endpoint: {endpoint} | Tentativa: {tentativa} | {erro}"
        self.error(msg)

    def conexao_perdida(self, tipo: str, tentando_reconectar: bool = True):
        """Log de perda de conexão"""
        status = "Tentando reconectar..." if tentando_reconectar else "Desconectado"
        msg = f"{Icones.DESCONECTADO} CONEXÃO PERDIDA | {tipo} | {status}"
        self.warning(msg)

    def inicializacao(self, componente: str, sucesso: bool = True):
        """Log de inicialização de componente"""
        icone = Icones.OK if sucesso else Icones.ERRO
        status = "OK" if sucesso else "FALHOU"
        msg = f"{Icones.INICIALIZACAO} INICIALIZAÇÃO | {componente} | {icone} {status}"
        self.info(msg)

    def degrau_bloqueado(self, degrau: int, motivo: str = ''):
        """Log de degrau bloqueado"""
        msg = f"{Icones.BLOQUEADO} Degrau {degrau} bloqueado"
        if motivo:
            msg += f" | {motivo}"
        self.info(msg)

    def degrau_desbloqueado(self, degrau: int):
        """Log de degrau desbloqueado"""
        msg = f"{Icones.DESBLOQUEADO} Degrau {degrau} desbloqueado e disponível"
        self.info(msg)

    def banner(self, mensagem: str):
        """Exibe banner formatado"""
        separador = "═" * 60
        self.info(separador)
        self.info(f"  {mensagem}")
        self.info(separador)


# ═══════════════════════════════════════════════════════════════════
# INSTÂNCIAS GLOBAIS
# ═══════════════════════════════════════════════════════════════════

_bot_logger_global: Optional[Logger] = None
_panel_logger_global: Optional[logging.Logger] = None

def get_loggers(
    nome: str = 'TradingBot',
    log_dir: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None,
    console: bool = True
) -> (Logger, logging.Logger):
    """
    Retorna as instâncias dos loggers (padrão e painel) em modo singleton.

    Args:
        nome: Nome base para os loggers
        log_dir: Diretório para logs de arquivo (usado apenas pelo bot_logger)
        config: Dicionário de configuração (usa LogConfig.DEFAULT se None)
        console: Se deve exibir logs no console

    Returns:
        Tupla contendo a instância do Logger principal e do logger do painel
    """
    global _bot_logger_global, _panel_logger_global

    if _bot_logger_global is None:
        # 1. Logger principal do Bot (usa a classe Logger customizada)
        _bot_logger_global = Logger(
            nome=nome,
            log_dir=log_dir,
            config=config,
            console=console
        )

    if _panel_logger_global is None:
        # 2. Logger dedicado para o painel (usa logging padrão)
        _panel_logger_global = logging.getLogger('panel_logger')
        _panel_logger_global.setLevel(logging.INFO)

        # Prevenir que os logs do painel subam para o logger root
        _panel_logger_global.propagate = False

        # Limpar handlers para evitar duplicação em re-execuções
        if _panel_logger_global.hasHandlers():
            _panel_logger_global.handlers.clear()

        # Formatter minimalista apenas com a mensagem
        panel_formatter = logging.Formatter('%(message)s')

        # Handler do console para o painel
        panel_handler = logging.StreamHandler(sys.stdout)
        panel_handler.setFormatter(panel_formatter)

        _panel_logger_global.addHandler(panel_handler)

    return _bot_logger_global, _panel_logger_global


def reset_loggers():
    """Reseta os loggers globais (útil para testes)"""
    global _bot_logger_global, _panel_logger_global
    _bot_logger_global = None
    _panel_logger_global = None
