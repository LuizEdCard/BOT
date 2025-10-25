#!/usr/bin/env python3
"""
Strategy Swing Trade - Estratégia de Giro Rápido (RSI + Stop Promovido)
Focada em capitalizar oscilações rápidas com proteção inteligente de Stop Loss
"""

from decimal import Decimal
from typing import Optional, Dict, Any
from pathlib import Path
import sys

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.position_manager import PositionManager
from src.core.gestao_capital import GestaoCapital
from src.core.analise_tecnica import AnaliseTecnica


class StrategySwingTrade:
    """
    Estratégia de Swing Trade (Giro Rápido) - Versão 2.0

    Características:
    - Opera com capital separado da carteira de acumulação
    - Entrada: RSI < 30 (sobrevenda)
    - Saída: Sistema "Stop Promovido"
      * Fase 1: Stop Loss inicial (proteção)
      * Fase 2: Promoção para Trailing Stop quando atinge breakeven (0%)
      * Fase 3: TSL segue o preço com distância configurada

    Regras:
    - Compra: RSI cai abaixo do limite configurado
    - Venda: Stop Loss disparado OU Trailing Stop disparado
    - Proteção: Stop promovido de SL → TSL no ponto de breakeven
    """

    def __init__(
        self,
        config: Dict[str, Any],
        position_manager: PositionManager,
        gestao_capital: GestaoCapital,
        analise_tecnica: AnaliseTecnica,
        logger=None,
        notifier=None,
        exchange_api=None
    ):
        """
        Inicializa a estratégia de swing trade

        Args:
            config: Configuração completa do bot
            position_manager: Gerenciador de posições
            gestao_capital: Gerenciador de capital
            analise_tecnica: Calculador de indicadores técnicos
            logger: Logger contextual (opcional)
            notifier: Instância do Notifier para notificações
            exchange_api: API da exchange para buscar dados (opcional)
        """
        # Logger contextual (fallback para logger global se não fornecido)
        if logger:
            self.logger = logger
        else:
            from src.utils.logger import get_loggers
            self.logger, _ = get_loggers()

        self.config = config
        self.position_manager = position_manager
        self.gestao_capital = gestao_capital
        self.analise_tecnica = analise_tecnica
        self.notifier = notifier
        self.exchange_api = exchange_api

        # Verificação de habilitação da estratégia
        self.habilitado = bool(config.get('ESTRATEGIAS', {}).get('giro_rapido', False))

        if not self.habilitado:
            return

        # Configuração da estratégia
        self.estrategia_config = config.get('estrategia_giro_rapido', {})

        # Parâmetros de alocação
        self.alocacao_capital_pct = Decimal(str(self.estrategia_config.get('alocacao_capital_pct', 20)))

        # ═══════════════════════════════════════════════════════════════
        # PARÂMETROS DE ENTRADA (RSI)
        # ═══════════════════════════════════════════════════════════════
        self.usar_filtro_rsi_entrada = self.estrategia_config.get('usar_filtro_rsi_entrada', True)
        self.rsi_timeframe_entrada = self.estrategia_config.get('rsi_timeframe_entrada', '15m')
        self.rsi_limite_compra = Decimal(str(self.estrategia_config.get('rsi_limite_compra', 30)))

        # ═══════════════════════════════════════════════════════════════
        # PARÂMETROS DE SAÍDA (Stop Promovido)
        # ═══════════════════════════════════════════════════════════════
        self.stop_loss_inicial_pct = Decimal(str(self.estrategia_config.get('stop_loss_inicial_pct', 2.5)))
        self.trailing_stop_distancia_pct = Decimal(str(self.estrategia_config.get('trailing_stop_distancia_pct', 0.8)))

        # Estado interno
        self.ultima_compra_timestamp: Optional[float] = None
        self.cooldown_segundos: int = self.estrategia_config.get('cooldown_compra_segundos', 60)
        self.ultima_log_status: Optional[float] = None

        # Configurar alocação na gestão de capital
        self.gestao_capital.configurar_alocacao_giro_rapido(self.alocacao_capital_pct)

        self.logger.info(f"✅ StrategySwingTrade inicializada (v2.0 - RSI + Stop Promovido)")
        self.logger.info(f"   RSI Entrada: {self.rsi_limite_compra} | Timeframe: {self.rsi_timeframe_entrada}")
        self.logger.info(f"   SL Inicial: {self.stop_loss_inicial_pct}% | TSL Distância: {self.trailing_stop_distancia_pct}%")

    def verificar_oportunidade(self, preco_atual: Decimal, tempo_atual: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Verifica se existe oportunidade de trade (compra ou venda)

        Args:
            preco_atual: Preço atual do ativo
            tempo_atual: Timestamp atual em segundos (opcional - para backtesting). Se None, usa time.time()

        Returns:
            Dict com dados da oportunidade ou None
        """
        if not self.habilitado:
            self.logger.debug("[SwingTrade] Estratégia DESABILITADA nas configurações")
            return None

        # Verificar se já tem posição
        tem_posicao = self.position_manager.tem_posicao('giro_rapido')
        quantidade = self.position_manager.get_quantidade_total('giro_rapido')

        # Log de estado a cada 60 segundos (não a cada verificação para evitar spam)
        import time
        agora_timestamp = tempo_atual if tempo_atual is not None else time.time()
        if self.ultima_log_status is None or (agora_timestamp - self.ultima_log_status) >= 60:
            rsi_atual = self._obter_rsi_atual()
            rsi_str = f"{rsi_atual:.2f}" if rsi_atual is not None else "N/A"
            self.logger.info(
                f"📊 Giro Rápido | Preço: ${preco_atual:.6f} | "
                f"RSI: {rsi_str} | "
                f"Posição: {quantidade:.4f} | "
                f"Status: {'COM posição' if tem_posicao else 'SEM posição'}"
            )
            self.ultima_log_status = agora_timestamp

        if not tem_posicao:
            # SEM POSIÇÃO: Verificar oportunidade de COMPRA
            return self._verificar_oportunidade_compra(preco_atual, agora_timestamp)
        else:
            # COM POSIÇÃO: Verificar oportunidade de VENDA (SL ou TSL)
            return self._verificar_oportunidade_venda(preco_atual)

    def _obter_rsi_atual(self) -> Optional[Decimal]:
        """
        Obtém o RSI atual do ativo no timeframe configurado

        Returns:
            Valor do RSI (0-100) ou None se não conseguir calcular
        """
        try:
            if self.exchange_api is None:
                return None

            par = self.config.get('par', 'ADA/USDT')
            klines = self.exchange_api.obter_klines(
                simbolo=par,
                intervalo=self.rsi_timeframe_entrada,
                limite=14  # RSI padrão usa 14 períodos
            )

            if not klines or len(klines) < 14:
                self.logger.debug(f"⚠️ Insuficientes klines para RSI ({len(klines) if klines else 0} < 14)")
                return None

            # Extrair preços de fechamento
            closes = [Decimal(str(candle[4])) for candle in klines]

            # Calcular RSI manualmente (versão simplificada)
            rsi = self._calcular_rsi_manual(closes)
            return rsi

        except Exception as e:
            self.logger.debug(f"⚠️ Erro ao obter RSI: {e}")
            return None

    def _calcular_rsi_manual(self, closes: list, period: int = 14) -> Decimal:
        """
        Calcula RSI manualmente a partir de uma lista de preços de fechamento

        Args:
            closes: Lista de preços de fechamento
            period: Período do RSI (padrão: 14)

        Returns:
            Valor do RSI (0-100) como Decimal
        """
        if len(closes) < period + 1:
            return Decimal('50')  # RSI neutro se dados insuficientes

        closes = [Decimal(str(c)) for c in closes]

        # Calcular variações
        variações = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

        # Separar ganhos e perdas
        ganhos = [v if v > 0 else Decimal('0') for v in variações[-period:]]
        perdas = [abs(v) if v < 0 else Decimal('0') for v in variações[-period:]]

        # Média de ganhos e perdas
        media_ganhos = sum(ganhos) / Decimal(period)
        media_perdas = sum(perdas) / Decimal(period)

        # Calcular RS e RSI
        if media_perdas == 0:
            rsi = Decimal('100') if media_ganhos > 0 else Decimal('50')
        else:
            rs = media_ganhos / media_perdas
            rsi = Decimal('100') - (Decimal('100') / (Decimal('1') + rs))

        return rsi

    def _verificar_oportunidade_compra(self, preco_atual: Decimal, tempo_atual: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Verifica oportunidade de compra quando NÃO há posição

        Lógica:
        1. Verificar cooldown
        2. Verificar RSI < limite
        3. Calcular capital disponível
        4. Registrar stop loss inicial

        Args:
            preco_atual: Preço atual do ativo
            tempo_atual: Timestamp atual em segundos

        Returns:
            Dict com dados da oportunidade de compra ou None
        """
        # VERIFICAR COOLDOWN: Evitar múltiplas compras em sequência rápida
        if self.ultima_compra_timestamp is not None:
            import time
            agora = tempo_atual if tempo_atual is not None else time.time()
            tempo_desde_ultima_compra = agora - self.ultima_compra_timestamp
            if tempo_desde_ultima_compra < self.cooldown_segundos:
                self.logger.debug(f"⏱️ Cooldown ativo: {int(self.cooldown_segundos - tempo_desde_ultima_compra)}s restantes")
                return None

        # VERIFICAR ENTRADA: RSI < Limite
        if not self.usar_filtro_rsi_entrada:
            self.logger.debug("[SwingTrade] Filtro RSI DESABILITADO - ignorando lógica de compra")
            return None

        rsi_atual = self._obter_rsi_atual()

        if rsi_atual is None:
            self.logger.debug("[SwingTrade] Não conseguiu obter RSI - ignorando compra")
            return None

        self.logger.debug(
            f"[SwingTrade] Verificando entrada: RSI={rsi_atual:.2f}, Limite={self.rsi_limite_compra:.2f}"
        )

        # Log sobre o RSI (usando INFO para garantir visibilidade)
        self.logger.info(
            f"📊 Giro Rápido | RSI: {rsi_atual:.2f} | "
            f"Limite: {self.rsi_limite_compra:.2f} | "
            f"Gatilho: {'SIM ✓' if rsi_atual < self.rsi_limite_compra else 'NÃO ✗'}"
        )

        # Verificar se RSI atingiu o gatilho
        if rsi_atual < self.rsi_limite_compra:
            self.logger.debug(f"[SwingTrade] ✅ Gatilho RSI ATINGIDO!")

            # Calcular quanto comprar (100% do capital disponível da carteira giro_rapido)
            capital_disponivel = self.gestao_capital.calcular_capital_disponivel('giro_rapido')

            self.logger.debug(f"💰 Giro Rápido | Capital disponível: ${capital_disponivel:.2f}")

            if capital_disponivel <= 0:
                self.logger.debug(
                    f"[SwingTrade] Compra BLOQUEADA. Capital disponível: ${capital_disponivel:.2f} "
                    f"(alocação: {self.alocacao_capital_pct}%)"
                )
                self.logger.debug("⚠️ Oportunidade de compra detectada, mas SEM CAPITAL disponível!")
                self.logger.debug(f"   Verifique saldo USDT e configuração de alocação ({self.alocacao_capital_pct}%)")
                return None

            # Verificar valor mínimo de ordem
            valor_minimo = Decimal(str(self.config.get('VALOR_MINIMO_ORDEM', 5.0)))
            if capital_disponivel < valor_minimo:
                self.logger.debug(
                    f"[SwingTrade] Compra BLOQUEADA. Capital ${capital_disponivel:.2f} < mínimo ${valor_minimo:.2f}"
                )
                self.logger.debug(f"⚠️ Capital disponível (${capital_disponivel:.2f}) abaixo do mínimo (${valor_minimo:.2f})")
                return None

            # Validar com gestão de capital
            pode_comprar, motivo = self.gestao_capital.pode_comprar(capital_disponivel, 'giro_rapido')

            if not pode_comprar:
                self.logger.debug(f"[SwingTrade] Compra BLOQUEADA pela gestão de capital: {motivo}")
                self.logger.debug(f"⚠️ Compra bloqueada pela gestão de capital: {motivo}")
                if self.notifier:
                    titulo = "Compra Bloqueada (Giro Rápido)"
                    mensagem = (
                        f"Oportunidade de compra para Giro Rápido foi encontrada, mas não executada.\n\n"
                        f"🔒 **Bloqueio:** Gestão de Capital\n"
                        f"📄 **Motivo:** {motivo}"
                    )
                    self.notifier.enviar_alerta(titulo, mensagem)
                return None

            quantidade = capital_disponivel / preco_atual

            # Calcular nível de stop loss inicial
            stop_loss_nivel = preco_atual * (Decimal('1') - self.stop_loss_inicial_pct / Decimal('100'))

            self.logger.info(f"🎯 OPORTUNIDADE DE COMPRA (Giro Rápido)")
            self.logger.info(f"   RSI: {rsi_atual:.2f}% (limite: {self.rsi_limite_compra:.2f}%)")
            self.logger.info(f"   Preço atual: ${preco_atual:.6f}")
            self.logger.info(f"   Valor: ${capital_disponivel:.2f} ({quantidade:.4f} moedas)")
            self.logger.info(f"   🛡️ Stop Loss (Inicial): ${stop_loss_nivel:.6f} ({self.stop_loss_inicial_pct}%)")

            return {
                'tipo': 'compra',
                'carteira': 'giro_rapido',
                'quantidade': quantidade,
                'preco_atual': preco_atual,
                'valor_operacao': capital_disponivel,
                'motivo': f'RSI {rsi_atual:.2f}% < {self.rsi_limite_compra:.2f}% - Giro Rápido',
                'rsi_entrada': rsi_atual,
                'stop_loss_nivel': stop_loss_nivel  # Nível de stop loss inicial
            }
        else:
            # DEBUG: Log quando compra é bloqueada
            self.logger.debug(
                f"[SwingTrade] Compra bloqueada. RSI {rsi_atual:.2f}% >= limite {self.rsi_limite_compra:.2f}%"
            )

        return None

    def _verificar_oportunidade_venda(self, preco_atual: Decimal) -> Optional[Dict[str, Any]]:
        """
        Verifica oportunidade de venda quando HÁ posição

        Lógica:
        1. Calcular lucro atual
        2. Verificar se Stop Loss foi disparado
        3. Verificar se TSL foi disparado
        4. Retornar sinal de venda se algum stop disparou

        Args:
            preco_atual: Preço atual do ativo

        Returns:
            Dict com dados da oportunidade de venda ou None
        """
        # Calcular lucro atual
        lucro_atual = self.position_manager.calcular_lucro_atual(preco_atual, 'giro_rapido')

        if lucro_atual is None:
            self.logger.warning("⚠️ Não foi possível calcular lucro atual (giro rápido)")
            return None

        preco_medio = self.position_manager.get_preco_medio('giro_rapido')

        # DEBUG: Log detalhado da lógica de venda
        self.logger.debug(
            f"[SwingTrade] Posição ATIVA. Lucro: {lucro_atual:.2f}%. "
            f"Preço Médio: ${preco_medio:.6f}. Preço Atual: ${preco_atual:.6f}."
        )

        # Calcular níveis de stops
        stop_loss_nivel = preco_medio * (Decimal('1') - self.stop_loss_inicial_pct / Decimal('100'))

        self.logger.debug(
            f"📈 Giro Rápido - Lucro: {lucro_atual:.2f}% | "
            f"SL Inicial: ${stop_loss_nivel:.6f}"
        )

        # ═════════════════════════════════════════════════════════════════
        # VERIFICAÇÃO 1: STOP LOSS INICIAL
        # ═════════════════════════════════════════════════════════════════
        if preco_atual <= stop_loss_nivel:
            self.logger.debug(f"[SwingTrade] ✅ STOP LOSS INICIAL DISPARADO!")
            self.logger.info(f"🛑 STOP LOSS INICIAL DISPARADO (Giro Rápido)")
            self.logger.info(f"   Lucro: {lucro_atual:.2f}%")
            self.logger.info(f"   Preço: ${preco_atual:.6f} <= SL: ${stop_loss_nivel:.6f}")

            return {
                'tipo': 'venda',
                'carteira': 'giro_rapido',
                'preco_atual': preco_atual,
                'lucro_percentual': lucro_atual,
                'motivo': f'Stop Loss Inicial - Lucro: {lucro_atual:.2f}%',
                'motivo_venda': 'stop_loss'
            }

        # ═════════════════════════════════════════════════════════════════
        # VERIFICAÇÃO 2: PROMOÇÃO DE STOP (SL → TSL no breakeven)
        # ═════════════════════════════════════════════════════════════════
        # Retornar sinal para promover o stop de SL para TSL
        if lucro_atual >= 0:
            self.logger.debug(f"[SwingTrade] ✅ BREAKEVEN ATINGIDO - Promover SL para TSL!")
            self.logger.info(f"🎯 PROMOÇÃO DE STOP (Giro Rápido)")
            self.logger.info(f"   Lucro atingiu: {lucro_atual:.2f}% (breakeven)")
            self.logger.info(f"   Promovendo Stop Loss Inicial → Trailing Stop Loss")
            self.logger.info(f"   TSL Distância: {self.trailing_stop_distancia_pct}%")

            return {
                'acao': 'promover_stop',
                'carteira': 'giro_rapido',
                'preco_atual': preco_atual,
                'lucro_atual': lucro_atual,
                'distancia_tsl_pct': self.trailing_stop_distancia_pct,
                'motivo': f'Breakeven atingido ({lucro_atual:.2f}%) - Promover para TSL'
            }

        return None

    def registrar_compra_executada(self, oportunidade: Dict[str, Any], tempo_atual: Optional[float] = None):
        """
        Registra que uma compra foi executada

        Args:
            oportunidade: Dados da oportunidade que foi executada
            tempo_atual: Timestamp atual em segundos (opcional - para backtesting). Se None, usa time.time()
        """
        import time

        # Registrar timestamp da compra para ativar cooldown
        self.ultima_compra_timestamp = tempo_atual if tempo_atual is not None else time.time()

        self.logger.info(f"📈 Compra executada (Giro Rápido)")
        self.logger.info(f"⏱️ Cooldown ativado: próxima compra permitida em {self.cooldown_segundos}s")

    def registrar_venda_executada(self, oportunidade: Dict[str, Any]):
        """
        Registra que uma venda foi executada

        Args:
            oportunidade: Dados da oportunidade que foi executada
        """
        # Resetar cooldown após venda (permitir nova compra imediatamente)
        self.ultima_compra_timestamp = None

        lucro = oportunidade.get('lucro_percentual', 0)
        self.logger.info(f"💰 Venda executada (Giro Rápido) - Ciclo completo. Lucro: {lucro:.2f}%")
        self.logger.info(f"✅ Cooldown resetado - próxima compra pode ocorrer imediatamente")

    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Retorna estatísticas da estratégia

        Returns:
            Dict com estatísticas
        """
        quantidade = self.position_manager.get_quantidade_total('giro_rapido')
        preco_medio = self.position_manager.get_preco_medio('giro_rapido')

        return {
            'estrategia': 'Giro Rápido (RSI + Stop Promovido)',
            'habilitada': self.habilitado,
            'quantidade_posicao': quantidade,
            'preco_medio': preco_medio,
            'alocacao_capital_pct': self.alocacao_capital_pct,
            'rsi_limite_compra': self.rsi_limite_compra,
            'rsi_timeframe': self.rsi_timeframe_entrada,
            'stop_loss_inicial_pct': self.stop_loss_inicial_pct,
            'trailing_stop_distancia_pct': self.trailing_stop_distancia_pct
        }


if __name__ == '__main__':
    """Teste básico"""
    from src.persistencia.database import DatabaseManager

    # Configuração de teste
    config_teste = {
        'DATABASE_PATH': 'dados/bot_trading.db',
        'BACKUP_DIR': 'dados/backup',
        'VALOR_MINIMO_ORDEM': 5.0,
        'par': 'ADA/USDT',
        'ESTRATEGIAS': {
            'giro_rapido': True
        },
        'estrategia_giro_rapido': {
            'habilitado': True,
            'alocacao_capital_pct': 20,
            'usar_filtro_rsi_entrada': True,
            'rsi_timeframe_entrada': '15m',
            'rsi_limite_compra': 30,
            'stop_loss_inicial_pct': 2.5,
            'trailing_stop_distancia_pct': 0.8
        }
    }

    db = DatabaseManager(Path('dados/bot_trading.db'), Path('dados/backup'))
    position_mgr = PositionManager(db)
    gestao_cap = GestaoCapital(saldo_usdt=Decimal('100'), percentual_reserva=Decimal('8'))
    analise = AnaliseTecnica(None)

    strategy = StrategySwingTrade(config_teste, position_mgr, gestao_cap, analise)

    print("\n" + "="*60)
    print("TESTE: Strategy Swing Trade v2.0")
    print("="*60)

    stats = strategy.obter_estatisticas()
    print(f"\nEstratégia: {stats['estrategia']}")
    print(f"Habilitada: {stats['habilitada']}")
    print(f"Alocação: {stats['alocacao_capital_pct']}%")
    print(f"RSI Limite: {stats['rsi_limite_compra']}%")
    print(f"SL Inicial: {stats['stop_loss_inicial_pct']}%")
    print(f"TSL Distância: {stats['trailing_stop_distancia_pct']}%")
    print(f"\n✅ Estratégia de Giro Rápido v2.0 inicializada com sucesso!")
