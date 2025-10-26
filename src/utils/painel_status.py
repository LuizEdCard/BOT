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
        # Cache do último painel renderizado para evitar spam quando nada mudou
        self._ultimo_snapshot_str: Optional[str] = None

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
        Exibe o painel de status formatado com suporte a dual-wallet

        Args:
            dados: Dicionário com todos os dados necessários:
                - preco_atual: Decimal
                - sma_28: Decimal
                - saldo_usdt: Decimal
                - reserva: Decimal
                - capital_total: Decimal
                - stats_24h: Dict com 'compras', 'vendas', 'lucro_realizado'
                - base_currency: str (ex: 'ADA', 'XRP', 'BTC')
                - posicao_acumulacao: Dict com 'quantidade', 'preco_medio', 'lucro_percentual' (opcional)
                - posicao_giro_rapido: Dict com 'quantidade', 'preco_medio', 'lucro_percentual' (opcional)

                # Compatibilidade com formato antigo:
                - quantidade_ada: Decimal (usado se posicoes específicas não fornecidas)
                - preco_medio: Decimal (usado se posicoes específicas não fornecidas)
        """
        # Gerar uma string de snapshot compacta com os campos que importam
        try:
            preco_atual = float(dados['preco_atual'])
            pos_acum_qtd = float(dados.get('posicao_acumulacao', {}).get('quantidade', 0) or 0)
            pos_giro_qtd = float(dados.get('posicao_giro_rapido', {}).get('quantidade', 0) or 0)
            lucro_acum = float(dados.get('posicao_acumulacao', {}).get('lucro_percentual', 0) or 0)
            lucro_giro = float(dados.get('posicao_giro_rapido', {}).get('lucro_percentual', 0) or 0)
            saldo_usdt = float(dados['saldo_usdt'])
            estado_bot = dados.get('estado_bot', '')
        except Exception:
            # Se falta algum campo, cair para render completo (não bloquear exibicao)
            preco_atual = 0.0
            pos_acum_qtd = 0.0
            pos_giro_qtd = 0.0
            lucro_acum = 0.0
            lucro_giro = 0.0
            saldo_usdt = 0.0
            estado_bot = ''

        snapshot = f"{preco_atual:.6f}|{pos_acum_qtd:.4f}|{pos_giro_qtd:.4f}|{lucro_acum:.2f}|{lucro_giro:.2f}|{saldo_usdt:.2f}|{estado_bot}"

        # Se painel não mudou desde a última exibição, evitar reimpressão
        if snapshot == self._ultimo_snapshot_str:
            return False

        # Atualizar cache e timestamp apenas quando realmente for imprimir
        self._ultimo_snapshot_str = snapshot
        self.ultima_exibicao = time.time()
        agora = datetime.now().strftime('%H:%M:%S')
        uptime = self.calcular_uptime()

        # Extrair dados comuns
        preco_atual = float(dados['preco_atual'])
        sma_28 = float(dados['sma_28'])
        saldo_usdt = float(dados['saldo_usdt'])
        reserva = float(dados['reserva'])
        capital_total = float(dados['capital_total'])
        stats_24h = dados.get('stats_24h', {})
        base_currency = dados.get('base_currency', 'ADA')

        # Calcular métricas de mercado
        if sma_28 > 0:
            dist_sma = ((sma_28 - preco_atual) / sma_28) * 100
            sinal_sma = "+" if dist_sma > 0 else ""
        else:
            dist_sma = 0
            sinal_sma = ""

        # Extrair posições (suporte dual-wallet e legado)
        posicao_acumulacao = dados.get('posicao_acumulacao')
        posicao_giro_rapido = dados.get('posicao_giro_rapido')

        # Fallback para formato legado (sem dual-wallet)
        if not posicao_acumulacao and 'quantidade_ada' in dados:
            posicao_acumulacao = {
                'quantidade': float(dados['quantidade_ada']),
                'preco_medio': float(dados.get('preco_medio', 0)),
                'lucro_percentual': 0
            }
            if posicao_acumulacao['preco_medio'] > 0 and posicao_acumulacao['quantidade'] > 0:
                posicao_acumulacao['lucro_percentual'] = ((preco_atual - posicao_acumulacao['preco_medio']) / posicao_acumulacao['preco_medio']) * 100

        compras_24h = stats_24h.get('compras', 0)
        vendas_24h = stats_24h.get('vendas', 0)
        lucro_24h = stats_24h.get('lucro_realizado', 0)
        sinal_lucro_24h = "+" if lucro_24h > 0 else ""

        # Montar painel
        largura = 60
        self.logger.info("")
        self.logger.info("┌" + "─" * largura + "┐")
        self.logger.info(f"│ {Icones.STATUS} BOT STATUS | {agora} | Uptime: {uptime:>13} │")
        self.logger.info("├" + "─" * largura + "┤")

        # Mercado
        mercado_linha = f"│ {Icones.MERCADO} MERCADO  │ ${preco_atual:.6f} | SMA28: ${sma_28:.6f} ({sinal_sma}{dist_sma:.1f}%)"
        espacos = largura - len(mercado_linha) + 1
        self.logger.info(mercado_linha + " " * espacos + "│")

        # POSIÇÃO ACUMULAÇÃO
        if posicao_acumulacao and posicao_acumulacao.get('quantidade', 0) > 0:
            qtd = posicao_acumulacao['quantidade']
            pm = posicao_acumulacao['preco_medio']
            lucro_pct = posicao_acumulacao.get('lucro_percentual', 0)
            sinal_lucro = "+" if lucro_pct > 0 else ""

            linha_acum = f"│ 📊 ACUMULAÇÃO │ {qtd:.1f} {base_currency} @ ${pm:.6f} | {sinal_lucro}{lucro_pct:.2f}%"
            espacos = largura - len(linha_acum) + 1
            self.logger.info(linha_acum + " " * espacos + "│")
        else:
            linha_acum = f"│ 📊 ACUMULAÇÃO │ Sem posição aberta"
            espacos = largura - len(linha_acum) + 1
            self.logger.info(linha_acum + " " * espacos + "│")

        # POSIÇÃO GIRO RÁPIDO
        if posicao_giro_rapido and posicao_giro_rapido.get('quantidade', 0) > 0:
            qtd_giro = posicao_giro_rapido['quantidade']
            pm_giro = posicao_giro_rapido['preco_medio']
            lucro_pct_giro = posicao_giro_rapido.get('lucro_percentual', 0)
            sinal_lucro_giro = "+" if lucro_pct_giro > 0 else ""

            linha_giro = f"│ 🎯 GIRO RÁPIDO│ {qtd_giro:.1f} {base_currency} @ ${pm_giro:.6f} | {sinal_lucro_giro}{lucro_pct_giro:.2f}%"
            espacos = largura - len(linha_giro) + 1
            self.logger.info(linha_giro + " " * espacos + "│")
        else:
            linha_giro = f"│ 🎯 GIRO RÁPIDO│ Sem posição aberta"
            espacos = largura - len(linha_giro) + 1
            self.logger.info(linha_giro + " " * espacos + "│")

        # Capital
        capital_linha = f"│ {Icones.CAPITAL} CAPITAL  │ ${saldo_usdt:.2f} | Reserva: ${reserva:.2f} (8%)"
        espacos = largura - len(capital_linha) + 1
        self.logger.info(capital_linha + " " * espacos + "│")

        # 24H
        stats_linha = f"│ {Icones.HISTORICO} 24H      │ {compras_24h} compras | {vendas_24h} vendas | {sinal_lucro_24h}${lucro_24h:.2f}"
        espacos = largura - len(stats_linha) + 1
        self.logger.info(stats_linha + " " * espacos + "│")

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
