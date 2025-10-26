#!/usr/bin/env python3
"""
Strategy Swing Trade - Estratégia de Giro Rápido (RSI + Stop Promovido)
Versão 2.0 - Lógica de saída 100% gerenciada pelo BotWorker

IMPORTANTE:
- Esta estratégia APENAS verifica entrada (RSI)
- Toda lógica de saída (SL, TSL, promoção) é gerenciada pelo BotWorker
- O método verificar_oportunidade só retorna decisões de COMPRA
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

    Escopo REDUZIDO:
    - RESPONSABILIDADE: Apenas verificar oportunidades de COMPRA (RSI)
    - Entrada: RSI < 30 (sobrevenda)
    - Saída: 100% gerenciada pelo BotWorker
      * BotWorker ativa SL inicial após compra
      * BotWorker promove SL → TSL no breakeven
      * BotWorker atualiza TSL no loop principal
      * BotWorker executa vendas ao atingir stops

    Separação de Responsabilidades:
    - StrategySwingTrade: Decisões de entrada (RSI)
    - BotWorker: Gestão de stops, promoções, vendas
    - PositionManager: Estado da posição
    - StateManager: Persistência de stops
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
            analise_tecnica: Calculador de indicadores técnicos (CRÍTICO)
            logger: Logger contextual (opcional)
            notifier: Instância do Notifier para notificações
            exchange_api: API da exchange (para logs apenas)
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
        self.analise_tecnica = analise_tecnica  # CRÍTICO: Para get_rsi()
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

        # Normalizar timeframe de RSI (pode estar em maiúsculo ou malformado)
        rsi_tf_raw = self.estrategia_config.get('rsi_timeframe_entrada', '15m')
        # Limpar timeframes malformados como "30Mh"
        rsi_tf_cleaned = rsi_tf_raw.lower() if rsi_tf_raw else '15m'
        # Se resultou em algo como "30mh", extrair apenas "30m"
        if rsi_tf_cleaned.endswith('mh'):
            rsi_tf_cleaned = rsi_tf_cleaned[:-1]  # Remove 'h' final
        self.rsi_timeframe_entrada = rsi_tf_cleaned

        self.rsi_limite_compra = Decimal(str(self.estrategia_config.get('rsi_limite_compra', 30)))

        # ═══════════════════════════════════════════════════════════════
        # PARÂMETROS DE SAÍDA (Gerenciados pelo BotWorker)
        # ═══════════════════════════════════════════════════════════════
        self.stop_loss_inicial_pct = Decimal(str(self.estrategia_config.get('stop_loss_inicial_pct', 2.5)))
        self.trailing_stop_distancia_pct = Decimal(str(self.estrategia_config.get('trailing_stop_distancia_pct', 0.8)))

        # Estado interno
        self.ultima_compra_timestamp: Optional[float] = None
        self.cooldown_segundos: int = self.estrategia_config.get('cooldown_compra_segundos', 60)
        # Track last known position status so we only log on changes
        self.ultima_log_status: Optional[float] = None
        self.ultimo_status_posicao: Optional[bool] = None
        self.notificou_esperando_rsi: bool = False

        # Configurar alocação na gestão de capital
        self.gestao_capital.configurar_alocacao_giro_rapido(self.alocacao_capital_pct)

        self.logger.info(f"✅ StrategySwingTrade v2.0 inicializada (RSI only)")
        self.logger.info(f"   Responsabilidade: APENAS verificar entrada")
        self.logger.info(f"   RSI Entrada: {self.rsi_limite_compra}% | Timeframe: {self.rsi_timeframe_entrada}")
        self.logger.info(f"   Saída gerenciada por: BotWorker")

    def verificar_oportunidade(self, preco_atual: Decimal, tempo_atual: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Verifica oportunidade de COMPRA baseada em RSI

        IMPORTANTE: Este método APENAS verifica entrada.
        Nenhuma lógica de venda/stop é implementada aqui.
        O BotWorker é 100% responsável pela gestão de stops e saída.

        Args:
            preco_atual: Preço atual do ativo
            tempo_atual: Timestamp atual em segundos (opcional - para backtesting)

        Returns:
            Dict com dados da oportunidade de compra ou None
        """
        if not self.habilitado:
            self.logger.debug("[SwingTrade] Estratégia DESABILITADA nas configurações")
            return None

        # Verificar se já tem posição
        tem_posicao = self.position_manager.tem_posicao('giro_rapido')

        # Se JÁ tem posição, não fazer nada (saída é gerenciada pelo BotWorker)
        if tem_posicao:
            return None

        # ═══════════════════════════════════════════════════════════════
        # SEM POSIÇÃO: Verificar oportunidade de COMPRA
        # ═══════════════════════════════════════════════════════════════

        # Log de estado apenas quando houver mudança de status (posse/sem posse)
        quantidade = self.position_manager.get_quantidade_total('giro_rapido')
        if self.ultimo_status_posicao is None or (tem_posicao != self.ultimo_status_posicao):
            # Logamos somente quando o estado da posição muda (ex.: abriu ou fechou)
            self.logger.info(
                f"📊 Giro Rápido | Preço: ${preco_atual:.6f} | "
                f"Posição: {quantidade:.4f} | "
                f"Status: {'COM posição' if tem_posicao else 'SEM posição'}"
            )
            self.ultimo_status_posicao = tem_posicao

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

        # ═══════════════════════════════════════════════════════════════
        # OBTER RSI DA AnaliseTecnica
        # ═══════════════════════════════════════════════════════════════
        par = self.config.get('par', 'ADA/USDT')
        rsi_atual = self.analise_tecnica.get_rsi(
            par=par,
            timeframe=self.rsi_timeframe_entrada,
            periodo=14,
            limite_candles=100
        )

        if rsi_atual is None:
            self.logger.debug("[SwingTrade] Não conseguiu obter RSI - ignorando compra")
            return None

        rsi_atual = Decimal(str(rsi_atual))

        self.logger.debug(
            f"[SwingTrade] Verificando entrada: RSI={rsi_atual:.2f}, Limite={self.rsi_limite_compra:.2f}"
        )

        # Não logar RSI em INFO a cada verificação para reduzir spam no terminal.
        # Mantemos o debug para inspeção quando o nível DEBUG estiver ativo.

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

            self.logger.info(f"🎯 OPORTUNIDADE DE COMPRA (Giro Rápido)")
            self.logger.info(f"   RSI: {rsi_atual:.2f}% (limite: {self.rsi_limite_compra:.2f}%)")
            self.logger.info(f"   Preço atual: ${preco_atual:.6f}")
            self.logger.info(f"   Valor: ${capital_disponivel:.2f} ({quantidade:.4f} moedas)")
            self.logger.info(f"   🛡️ SL Inicial será ativado pelo BotWorker: {self.stop_loss_inicial_pct}%")

            return {
                'tipo': 'compra',
                'carteira': 'giro_rapido',
                'quantidade': quantidade,
                'preco_atual': preco_atual,
                'valor_operacao': capital_disponivel,
                'motivo': f'RSI {rsi_atual:.2f}% < {self.rsi_limite_compra:.2f}% - Giro Rápido',
                'rsi_entrada': rsi_atual
            }
        else:
            # DEBUG: Log quando compra é bloqueada
            self.logger.debug(
                f"[SwingTrade] Compra bloqueada. RSI {rsi_atual:.2f}% >= limite {self.rsi_limite_compra:.2f}%"
            )

        return None

    def registrar_compra_executada(self, oportunidade: Dict[str, Any], tempo_atual: Optional[float] = None):
        """
        Registra que uma compra foi executada

        Args:
            oportunidade: Dados da oportunidade que foi executada
            tempo_atual: Timestamp atual em segundos (opcional - para backtesting)
        """
        import time

        # Registrar timestamp da compra para ativar cooldown
        self.ultima_compra_timestamp = tempo_atual if tempo_atual is not None else time.time()

        self.logger.info(f"📈 Compra executada (Giro Rápido)")
        self.logger.info(f"⏱️ Cooldown ativado: próxima compra permitida em {self.cooldown_segundos}s")
        self.logger.info(f"🛡️ BotWorker irá ativar SL inicial: {self.stop_loss_inicial_pct}%")

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
            'versao': '2.0',
            'escopo': 'Entrada (RSI) | Saída gerenciada por BotWorker',
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
    print(f"Versão: {stats['versao']}")
    print(f"Escopo: {stats['escopo']}")
    print(f"Habilitada: {stats['habilitada']}")
    print(f"RSI Limite: {stats['rsi_limite_compra']}%")
    print(f"SL Inicial: {stats['stop_loss_inicial_pct']}%")
    print(f"TSL Distância: {stats['trailing_stop_distancia_pct']}%")
    print(f"\n✅ Estratégia de Giro Rápido v2.0 inicializada com sucesso!")
