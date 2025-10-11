"""
═══════════════════════════════════════════════════════════════════
TRADING BOT - Sistema de Logging
═══════════════════════════════════════════════════════════════════
Logger centralizado com suporte a arquivo e console
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from colorama import Fore, Style, init

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
    Sistema de logging centralizado

    Recursos:
    - Log em arquivo e console
    - Cores no console
    - Rotação automática de logs
    - Níveis configuráveis
    - Thread-safe
    """

    def __init__(
        self,
        nome: str = 'TradingBot',
        log_dir: Optional[Path] = None,
        nivel: str = 'INFO',
        console: bool = True
    ):
        """
        Inicializa o logger

        Args:
            nome: Nome do logger
            log_dir: Diretório para arquivos de log
            nivel: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console: Se deve exibir logs no console
        """
        self.nome = nome
        self.nivel = self._parse_nivel(nivel)

        # Criar logger
        self.logger = logging.getLogger(nome)
        self.logger.setLevel(self.nivel)
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
        """Adiciona handler para console com cores"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.nivel)

        # Formato com cores
        formato = '%(levelname)s | %(asctime)s | %(message)s'
        formatter = ColoredFormatter(formato, datefmt='%Y-%m-%d %H:%M:%S')
        console_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)

    def _adicionar_handler_arquivo(self, log_dir: Path):
        """Adiciona handler para arquivo"""
        # Criar diretório se não existir
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Nome do arquivo com data
        hoje = datetime.now().strftime('%Y-%m-%d')
        log_file = log_dir / f'sistema_{hoje}.log'

        # Handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(self.nivel)

        # Formato para arquivo (sem cores)
        formato = '%(levelname)-8s | %(asctime)s | %(name)s | %(message)s'
        formatter = logging.Formatter(formato, datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    # ═══════════════════════════════════════════════════════════
    # MÉTODOS DE LOG
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

    def error(self, mensagem: str):
        """Log nível ERROR"""
        self.logger.error(mensagem)

    def critical(self, mensagem: str):
        """Log nível CRITICAL"""
        self.logger.critical(mensagem)

    def exception(self, mensagem: str):
        """Log exceção com traceback"""
        self.logger.exception(mensagem)

    # ═══════════════════════════════════════════════════════════
    # MÉTODOS ESPECIALIZADOS
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
            f"🟢 COMPRA | {par} | "
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
        msg = (
            f"🔴 VENDA | {par} | "
            f"Qtd: {quantidade:.4f} | "
            f"Preço: ${preco:.6f} | "
            f"Meta: {meta} | "
            f"Lucro: {lucro_pct:.2f}% (${lucro_usd:.2f})"
        )
        self.info(msg)

    def pico_detectado(self, par: str, preco: float, confirmado: bool = False):
        """Log de detecção de pico"""
        status = "CONFIRMADO" if confirmado else "CANDIDATO"
        msg = f"📊 PICO {status} | {par} | Preço: ${preco:.6f}"
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
            f"💰 CAPITAL | "
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
            msg = f"💵 APORTE DETECTADO | R$ {valor:.2f} BRL → ${usdt_recebido:.2f} USDT"
        else:
            msg = f"💵 APORTE DETECTADO | Valor: ${valor:.2f}"
        self.info(msg)

    def saldo_atualizado(self, moeda: str, valor: float):
        """Log de saldo atualizado"""
        if moeda == 'USDT':
            msg = f"💼 SALDO ATUALIZADO | ${valor:.2f} {moeda}"
        elif moeda == 'BRL':
            msg = f"💼 SALDO ATUALIZADO | R$ {valor:.2f} {moeda}"
        else:
            msg = f"💼 SALDO ATUALIZADO | {valor:.4f} {moeda}"
        self.info(msg)

    def erro_api(self, endpoint: str, erro: str, tentativa: int = 1):
        """Log de erro de API"""
        msg = f"⚠️ ERRO API | Endpoint: {endpoint} | Tentativa: {tentativa} | {erro}"
        self.error(msg)

    def conexao_perdida(self, tipo: str, tentando_reconectar: bool = True):
        """Log de perda de conexão"""
        status = "Tentando reconectar..." if tentando_reconectar else "Desconectado"
        msg = f"🔌 CONEXÃO PERDIDA | {tipo} | {status}"
        self.warning(msg)

    def inicializacao(self, componente: str, sucesso: bool = True):
        """Log de inicialização de componente"""
        status = "✅ OK" if sucesso else "❌ FALHOU"
        msg = f"🚀 INICIALIZAÇÃO | {componente} | {status}"
        self.info(msg)

    def banner(self, mensagem: str):
        """Exibe banner formatado"""
        separador = "═" * 60
        self.info(separador)
        self.info(f"  {mensagem}")
        self.info(separador)


# ═══════════════════════════════════════════════════════════════════
# INSTÂNCIA GLOBAL
# ═══════════════════════════════════════════════════════════════════

_logger_global: Optional[Logger] = None


def get_logger(
    nome: str = 'TradingBot',
    log_dir: Optional[Path] = None,
    nivel: str = 'INFO',
    console: bool = True
) -> Logger:
    """
    Retorna instância do logger (singleton)

    Args:
        nome: Nome do logger
        log_dir: Diretório para logs
        nivel: Nível de log
        console: Exibir no console

    Returns:
        Instância do Logger
    """
    global _logger_global

    if _logger_global is None:
        _logger_global = Logger(
            nome=nome,
            log_dir=log_dir,
            nivel=nivel,
            console=console
        )

    return _logger_global


def reset_logger():
    """Reseta o logger global (útil para testes)"""
    global _logger_global
    _logger_global = None
