"""
Sistema de Painel de Status Adaptativo

Gerencia a exibição periódica e inteligente do painel de status do bot,
ajustando a frequência baseado na volatilidade do mercado.
"""

import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, Deque
from collections import deque

from .constants import Icones, PainelConfig, Formatos
from .logger import Logger


class PainelStatus:
    """
    Gerenciador de painel de status com frequência adaptativa

    Características:
    - Ajusta frequência baseado na volatilidade
    - Calcula volatilidade em janela de tempo configurável
    - Formato de painel limpo e informativo
    """

    def __init__(self, logger: Logger):
        """
        Inicializa o painel de status

        Args:
            logger: Instância do logger para exibição
        """
        self.logger = logger

        # Controle de tempo
        self.ultima_exibicao = 0
        self.intervalo_atual = PainelConfig.INTERVALO_NORMAL
        self.tempo_inicio = time.time()

        # Buffer de preços para cálculo de volatilidade
        self.historico_precos: Deque[tuple[float, float]] = deque(
            maxlen=100  # timestamp, preco
        )

    def registrar_preco(self, preco: Decimal):
        """
        Registra um preço para cálculo de volatilidade

        Args:
            preco: Preço atual do ativo
        """
        self.historico_precos.append((time.time(), float(preco)))

    def calcular_volatilidade(self) -> float:
        """
        Calcula a volatilidade percentual na janela de tempo configurada

        Returns:
            Percentual de variação (0-100)
        """
        if len(self.historico_precos) < 2:
            return 0.0

        # Filtrar preços da janela de tempo
        agora = time.time()
        janela_inicio = agora - PainelConfig.JANELA_VOLATILIDADE

        precos_janela = [
            preco for timestamp, preco in self.historico_precos
            if timestamp >= janela_inicio
        ]

        if len(precos_janela) < 2:
            return 0.0

        # Calcular variação percentual
        preco_min = min(precos_janela)
        preco_max = max(precos_janela)

        if preco_min == 0:
            return 0.0

        volatilidade = ((preco_max - preco_min) / preco_min) * 100
        return volatilidade

    def ajustar_frequencia(self):
        """Ajusta o intervalo de exibição baseado na volatilidade"""
        volatilidade = self.calcular_volatilidade()

        if volatilidade >= PainelConfig.VOLATILIDADE_ALTA:
            # Alta volatilidade: atualizar mais frequentemente
            self.intervalo_atual = PainelConfig.INTERVALO_ALTA_VOL
        elif volatilidade <= PainelConfig.VOLATILIDADE_BAIXA:
            # Baixa volatilidade: atualizar menos frequentemente
            self.intervalo_atual = PainelConfig.INTERVALO_BAIXA_VOL
        else:
            # Volatilidade normal
            self.intervalo_atual = PainelConfig.INTERVALO_NORMAL

    def deve_exibir(self) -> bool:
        """
        Verifica se deve exibir o painel agora

        Returns:
            True se passou o intervalo configurado
        """
        agora = time.time()
        tempo_decorrido = agora - self.ultima_exibicao

        return tempo_decorrido >= self.intervalo_atual

    def calcular_uptime(self) -> str:
        """
        Calcula tempo de execução do bot

        Returns:
            String formatada (ex: "9h 15m")
        """
        uptime_segundos = time.time() - self.tempo_inicio

        horas = int(uptime_segundos // 3600)
        minutos = int((uptime_segundos % 3600) // 60)

        if horas > 0:
            return f"{horas}h {minutos}m"
        else:
            return f"{minutos}m"

    def exibir(self, dados: Dict[str, Any]):
        """
        Exibe o painel de status formatado

        Args:
            dados: Dicionário com todos os dados necessários:
                - preco_atual: Decimal
                - sma_28: Decimal
                - quantidade_ada: Decimal (quantidade do ativo base)
                - preco_medio: Decimal
                - saldo_usdt: Decimal
                - reserva: Decimal
                - capital_total: Decimal
                - stats_24h: Dict com 'compras', 'vendas', 'lucro_realizado'
                - base_currency: str (ex: 'ADA', 'XRP', 'BTC')
        """
        # Atualizar timestamp
        self.ultima_exibicao = time.time()
        agora = datetime.now().strftime('%H:%M:%S')
        uptime = self.calcular_uptime()

        # Extrair dados
        preco_atual = float(dados['preco_atual'])
        sma_28 = float(dados['sma_28'])
        quantidade_ada = float(dados['quantidade_ada'])
        preco_medio = float(dados.get('preco_medio', 0))
        saldo_usdt = float(dados['saldo_usdt'])
        reserva = float(dados['reserva'])
        capital_total = float(dados['capital_total'])
        stats_24h = dados.get('stats_24h', {})
        base_currency = dados.get('base_currency', 'ADA')  # Default para retrocompatibilidade

        # Calcular métricas
        if sma_28 > 0:
            dist_sma = ((sma_28 - preco_atual) / sma_28) * 100
            sinal_sma = "+" if dist_sma > 0 else ""
        else:
            dist_sma = 0
            sinal_sma = ""

        valor_posicao = quantidade_ada * preco_atual

        if preco_medio > 0 and quantidade_ada > 0:
            lucro_pct = ((preco_atual - preco_medio) / preco_medio) * 100
            sinal_lucro = "+" if lucro_pct > 0 else ""
        else:
            lucro_pct = 0
            sinal_lucro = ""

        compras_24h = stats_24h.get('compras', 0)
        vendas_24h = stats_24h.get('vendas', 0)
        lucro_24h = stats_24h.get('lucro_realizado', 0)
        sinal_lucro_24h = "+" if lucro_24h > 0 else ""

        # Montar painel
        largura = 54
        self.logger.info("")
        self.logger.info("┌" + "─" * largura + "┐")
        self.logger.info(f"│ {Icones.STATUS} BOT STATUS | {agora} | Uptime: {uptime:>13} │")
        self.logger.info("├" + "─" * largura + "┤")
        self.logger.info(
            f"│ {Icones.MERCADO} MERCADO  │ ${preco_atual:.6f} | "
            f"SMA28: ${sma_28:.6f} ({sinal_sma}{dist_sma:.1f}%)"
            + " " * (largura - len(f"│ {Icones.MERCADO} MERCADO  │ ${preco_atual:.6f} | SMA28: ${sma_28:.6f} ({sinal_sma}{dist_sma:.1f}%)")) + "│"
        )

        if quantidade_ada > 0:
            self.logger.info(
                f"│ {Icones.POSICAO} POSIÇÃO  │ {quantidade_ada:.1f} {base_currency} @ ${preco_medio:.6f} | "
                f"{sinal_lucro}{lucro_pct:.2f}%"
                + " " * (largura - len(f"│ {Icones.POSICAO} POSIÇÃO  │ {quantidade_ada:.1f} {base_currency} @ ${preco_medio:.6f} | {sinal_lucro}{lucro_pct:.2f}%")) + "│"
            )
        else:
            self.logger.info(
                f"│ {Icones.POSICAO} POSIÇÃO  │ Sem posição aberta"
                + " " * (largura - len(f"│ {Icones.POSICAO} POSIÇÃO  │ Sem posição aberta")) + "│"
            )

        self.logger.info(
            f"│ {Icones.CAPITAL} CAPITAL  │ ${saldo_usdt:.2f} | "
            f"Reserva: ${reserva:.2f} (8%)"
            + " " * (largura - len(f"│ {Icones.CAPITAL} CAPITAL  │ ${saldo_usdt:.2f} | Reserva: ${reserva:.2f} (8%)")) + "│"
        )
        self.logger.info(
            f"│ {Icones.HISTORICO} 24H      │ {compras_24h} compras | "
            f"{vendas_24h} vendas | {sinal_lucro_24h}${lucro_24h:.2f}"
            + " " * (largura - len(f"│ {Icones.HISTORICO} 24H      │ {compras_24h} compras | {vendas_24h} vendas | {sinal_lucro_24h}${lucro_24h:.2f}")) + "│"
        )
        self.logger.info("└" + "─" * largura + "┘")
        self.logger.info("")

    def processar_tick(
        self,
        preco_atual: Decimal,
        dados_completos: Optional[Dict[str, Any]] = None
    ):
        """
        Processa um tick do bot (chamado a cada iteração)

        Args:
            preco_atual: Preço atual para registro de volatilidade
            dados_completos: Dados completos para exibição do painel (opcional)
        """
        # Registrar preço para volatilidade
        self.registrar_preco(preco_atual)

        # Ajustar frequência baseado em volatilidade
        self.ajustar_frequencia()

        # Verificar se deve exibir painel
        if self.deve_exibir() and dados_completos:
            self.exibir(dados_completos)
