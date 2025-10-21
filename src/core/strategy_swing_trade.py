#!/usr/bin/env python3
"""
Strategy Swing Trade - Estratégia de Giro Rápido
Focada em capitalizar pequenas oscilações de preço com proteção de lucro
"""

from decimal import Decimal
from typing import Optional, Dict, Any
from pathlib import Path
import sys

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.position_manager import PositionManager
from src.core.gestao_capital import GestaoCapital


class StrategySwingTrade:
    """
    Estratégia de Swing Trade (Giro Rápido)

    Características:
    - Opera com capital separado da carteira de acumulação
    - Compra em quedas de preço (gatilho_compra_pct)
    - Meta de lucro principal (meta_lucro_pct)
    - Proteção de lucro parcial com trailing stop

    Regras:
    - Compra: Preço caiu X% de uma máxima recente
    - Venda: Lucro atingiu meta OU proteção de lucro ativada
    - Proteção: Se lucro >= ativacao_pct, vende se cair venda_reversao_pct
    """

    def __init__(
        self,
        config: Dict[str, Any],
        position_manager: PositionManager,
        gestao_capital: GestaoCapital,
        logger=None,
        notifier=None
    ):
        """
        Inicializa a estratégia de swing trade

        Args:
            config: Configuração completa do bot
            position_manager: Gerenciador de posições
            gestao_capital: Gerenciador de capital
            logger: Logger contextual (opcional)
            notifier: Instância do Notifier para notificações
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
        self.notifier = notifier

        # Configuração da estratégia
        self.estrategia_config = config.get('estrategia_giro_rapido', {})
        self.habilitado = self.estrategia_config.get('habilitado', False)

        if not self.habilitado:
            self.logger.info("📈 Estratégia de Giro Rápido DESABILITADA")
            return

        # Parâmetros de alocação
        self.alocacao_capital_pct = Decimal(str(self.estrategia_config.get('alocacao_capital_pct', 20)))

        # Parâmetros de compra
        self.gatilho_compra_pct = Decimal(str(self.estrategia_config.get('gatilho_compra_pct', 2.0)))

        # Parâmetros de venda
        self.meta_lucro_pct = Decimal(str(self.estrategia_config.get('meta_lucro_pct', 3.5)))

        # Proteção de lucro
        protecao = self.estrategia_config.get('protecao_lucro', {})
        self.protecao_ativacao_pct = Decimal(str(protecao.get('ativacao_pct', 2.0)))
        self.protecao_reversao_pct = Decimal(str(protecao.get('venda_reversao_pct', 0.5)))

        # Estado interno
        self.preco_referencia_maxima: Optional[Decimal] = None  # Máxima recente para gatilho de compra
        self.ultima_compra_timestamp: Optional[float] = None  # Timestamp da última compra para cooldown
        self.cooldown_segundos: int = 60  # Cooldown mínimo entre compras (60 segundos)

        # Configurar alocação na gestão de capital
        self.gestao_capital.configurar_alocacao_giro_rapido(self.alocacao_capital_pct)

        self.logger.info("📈 Estratégia de Giro Rápido HABILITADA")
        self.logger.info(f"   Alocação: {self.alocacao_capital_pct}% do capital livre")
        self.logger.info(f"   Gatilho compra: queda de {self.gatilho_compra_pct}%")
        self.logger.info(f"   Meta lucro: {self.meta_lucro_pct}%")
        self.logger.info(f"   Proteção: ativa em {self.protecao_ativacao_pct}%, vende se cair {self.protecao_reversao_pct}%")

    def verificar_oportunidade(self, preco_atual: Decimal) -> Optional[Dict[str, Any]]:
        """
        Verifica se existe oportunidade de trade (compra ou venda)

        Args:
            preco_atual: Preço atual do ativo

        Returns:
            Dict com dados da oportunidade ou None
        """
        if not self.habilitado:
            return None

        # Atualizar preço de referência máxima
        self._atualizar_preco_referencia(preco_atual)

        # Verificar se já tem posição
        tem_posicao = self.position_manager.tem_posicao('giro_rapido')

        if not tem_posicao:
            # SEM POSIÇÃO: Verificar oportunidade de COMPRA
            return self._verificar_oportunidade_compra(preco_atual)
        else:
            # COM POSIÇÃO: Verificar oportunidade de VENDA
            return self._verificar_oportunidade_venda(preco_atual)

    def _atualizar_preco_referencia(self, preco_atual: Decimal):
        """
        Atualiza o preço de referência máxima para detectar quedas

        Args:
            preco_atual: Preço atual do ativo
        """
        if self.preco_referencia_maxima is None or preco_atual > self.preco_referencia_maxima:
            self.preco_referencia_maxima = preco_atual
            self.logger.debug(f"📊 Preço referência máxima atualizado: ${preco_atual:.6f}")

    def _verificar_oportunidade_compra(self, preco_atual: Decimal) -> Optional[Dict[str, Any]]:
        """
        Verifica oportunidade de compra quando NÃO há posição

        Args:
            preco_atual: Preço atual do ativo

        Returns:
            Dict com dados da oportunidade de compra ou None
        """
        if self.preco_referencia_maxima is None:
            return None

        # VERIFICAR COOLDOWN: Evitar múltiplas compras em sequência rápida
        if self.ultima_compra_timestamp is not None:
            import time
            tempo_desde_ultima_compra = time.time() - self.ultima_compra_timestamp
            if tempo_desde_ultima_compra < self.cooldown_segundos:
                self.logger.debug(f"⏱️ Cooldown ativo: {int(self.cooldown_segundos - tempo_desde_ultima_compra)}s restantes")
                return None

        # Calcular queda percentual desde a máxima
        queda_pct = ((self.preco_referencia_maxima - preco_atual) / self.preco_referencia_maxima) * Decimal('100')

        # Verificar se atingiu o gatilho de compra
        if queda_pct >= self.gatilho_compra_pct:
            # Calcular quanto comprar (100% do capital disponível da carteira giro_rapido)
            capital_disponivel = self.gestao_capital.calcular_capital_disponivel('giro_rapido')

            if capital_disponivel <= 0:
                self.logger.debug("📈 Oportunidade de compra detectada, mas sem capital disponível")
                return None

            # Verificar valor mínimo de ordem
            valor_minimo = Decimal(str(self.config.get('VALOR_MINIMO_ORDEM', 5.0)))
            if capital_disponivel < valor_minimo:
                self.logger.debug(f"📈 Capital disponível (${capital_disponivel:.2f}) abaixo do mínimo (${valor_minimo:.2f})")
                return None

            # Validar com gestão de capital
            pode_comprar, motivo = self.gestao_capital.pode_comprar(capital_disponivel, 'giro_rapido')

            if not pode_comprar:
                self.logger.debug(f"📈 Compra bloqueada pela gestão de capital: {motivo}")
                if self.notifier:
                    titulo = "Compra Bloqueada (Giro Rápido)"
                    mensagem = (
                        f"Oportunidade de compra para Giro Rápido foi encontrada, mas não executada.\n\n"
                        f"🔒 **Bloqueio:** Gestão de Capital\n"
                        f"📄 **Motivo:** {motivo}"
                    )
                    # Para evitar spam, podemos adicionar um mecanismo de state com TTL aqui se necessário
                    self.notifier.enviar_alerta(titulo, mensagem)
                return None

            quantidade = capital_disponivel / preco_atual

            self.logger.info(f"🎯 OPORTUNIDADE DE COMPRA (Giro Rápido)")
            self.logger.info(f"   Queda: {queda_pct:.2f}% desde ${self.preco_referencia_maxima:.6f}")
            self.logger.info(f"   Preço atual: ${preco_atual:.6f}")
            self.logger.info(f"   Valor: ${capital_disponivel:.2f} ({quantidade:.4f} moedas)")

            return {
                'tipo': 'compra',
                'carteira': 'giro_rapido',
                'quantidade': quantidade,
                'preco_atual': preco_atual,
                'valor_operacao': capital_disponivel,
                'motivo': f'Queda de {queda_pct:.2f}% - Giro Rápido',
                'queda_pct': queda_pct,
                'preco_referencia': self.preco_referencia_maxima
            }

        return None

    def _verificar_oportunidade_venda(self, preco_atual: Decimal) -> Optional[Dict[str, Any]]:
        """
        Verifica oportunidade de venda quando HÁ posição

        Lógica:
        1. Calcular lucro atual
        2. Atualizar high water mark
        3. Verificar meta principal de lucro
        4. Verificar proteção de lucro (trailing stop)

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

        # Atualizar high water mark
        self.position_manager.atualizar_high_water_mark(lucro_atual, 'giro_rapido')
        high_water_mark = self.position_manager.get_high_water_mark('giro_rapido')

        self.logger.debug(f"📊 Giro Rápido - Lucro: {lucro_atual:.2f}% | HWM: {high_water_mark:.2f}%")

        # 1. Verificar META PRINCIPAL de lucro
        if lucro_atual >= self.meta_lucro_pct:
            quantidade_total = self.position_manager.get_quantidade_total('giro_rapido')

            self.logger.info(f"🎯 META DE LUCRO ATINGIDA (Giro Rápido)")
            self.logger.info(f"   Lucro atual: {lucro_atual:.2f}%")
            self.logger.info(f"   Meta: {self.meta_lucro_pct:.2f}%")
            self.logger.info(f"   Quantidade: {quantidade_total:.4f} moedas")

            return {
                'tipo': 'venda',
                'carteira': 'giro_rapido',
                'quantidade_venda': quantidade_total,
                'percentual_venda': 100,
                'preco_atual': preco_atual,
                'lucro_percentual': lucro_atual,
                'motivo': f'Meta de lucro atingida: {lucro_atual:.2f}% - Giro Rápido',
                'tipo_venda': 'meta_lucro'
            }

        # 2. Verificar PROTEÇÃO DE LUCRO (trailing stop)
        if high_water_mark >= self.protecao_ativacao_pct:
            # Proteção ativada - verificar se houve reversão
            gatilho_venda = high_water_mark - self.protecao_reversao_pct

            if lucro_atual <= gatilho_venda:
                quantidade_total = self.position_manager.get_quantidade_total('giro_rapido')

                self.logger.info(f"🛡️ PROTEÇÃO DE LUCRO ATIVADA (Giro Rápido)")
                self.logger.info(f"   High water mark: {high_water_mark:.2f}%")
                self.logger.info(f"   Lucro atual: {lucro_atual:.2f}%")
                self.logger.info(f"   Gatilho venda: {gatilho_venda:.2f}%")
                self.logger.info(f"   Reversão: {self.protecao_reversao_pct:.2f}%")

                return {
                    'tipo': 'venda',
                    'carteira': 'giro_rapido',
                    'quantidade_venda': quantidade_total,
                    'percentual_venda': 100,
                    'preco_atual': preco_atual,
                    'lucro_percentual': lucro_atual,
                    'motivo': f'Proteção de lucro: reversão de {self.protecao_reversao_pct:.2f}% - Giro Rápido',
                    'tipo_venda': 'protecao_lucro',
                    'high_water_mark': high_water_mark
                }

        return None

    def registrar_compra_executada(self, oportunidade: Dict[str, Any]):
        """
        Registra que uma compra foi executada

        Args:
            oportunidade: Dados da oportunidade que foi executada
        """
        import time

        # Resetar preço de referência após compra (nova base de cálculo)
        self.preco_referencia_maxima = oportunidade['preco_atual']

        # Registrar timestamp da compra para ativar cooldown
        self.ultima_compra_timestamp = time.time()

        self.logger.info(f"📈 Compra executada (Giro Rápido) - Nova referência: ${self.preco_referencia_maxima:.6f}")
        self.logger.info(f"⏱️ Cooldown ativado: próxima compra permitida em {self.cooldown_segundos}s")

    def registrar_venda_executada(self, oportunidade: Dict[str, Any]):
        """
        Registra que uma venda foi executada

        Args:
            oportunidade: Dados da oportunidade que foi executada
        """
        # Após venda, resetar estado
        self.preco_referencia_maxima = oportunidade['preco_atual']

        # Resetar cooldown após venda (permitir nova compra imediatamente)
        self.ultima_compra_timestamp = None

        self.logger.info(f"💰 Venda executada (Giro Rápido) - Ciclo completo. Lucro: {oportunidade.get('lucro_percentual', 0):.2f}%")
        self.logger.info(f"✅ Cooldown resetado - nova compra permitida")

    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Retorna estatísticas da estratégia

        Returns:
            Dict com estatísticas
        """
        quantidade = self.position_manager.get_quantidade_total('giro_rapido')
        preco_medio = self.position_manager.get_preco_medio('giro_rapido')
        high_water_mark = self.position_manager.get_high_water_mark('giro_rapido')

        return {
            'estrategia': 'Giro Rápido',
            'habilitada': self.habilitado,
            'quantidade_posicao': quantidade,
            'preco_medio': preco_medio,
            'alocacao_capital_pct': self.alocacao_capital_pct,
            'gatilho_compra_pct': self.gatilho_compra_pct,
            'meta_lucro_pct': self.meta_lucro_pct,
            'protecao_ativacao_pct': self.protecao_ativacao_pct,
            'protecao_reversao_pct': self.protecao_reversao_pct,
            'preco_referencia_maxima': self.preco_referencia_maxima,
            'high_water_mark': high_water_mark
        }


if __name__ == '__main__':
    """Teste básico"""
    from src.persistencia.database import DatabaseManager

    # Configuração de teste
    config_teste = {
        'DATABASE_PATH': 'dados/bot_trading.db',
        'BACKUP_DIR': 'dados/backup',
        'VALOR_MINIMO_ORDEM': 5.0,
        'estrategia_giro_rapido': {
            'habilitado': True,
            'alocacao_capital_pct': 20,
            'gatilho_compra_pct': 2.0,
            'meta_lucro_pct': 3.5,
            'protecao_lucro': {
                'ativacao_pct': 2.0,
                'venda_reversao_pct': 0.5
            }
        }
    }

    db = DatabaseManager(Path('dados/bot_trading.db'), Path('dados/backup'))
    position_mgr = PositionManager(db)
    gestao_cap = GestaoCapital(saldo_usdt=Decimal('100'), percentual_reserva=Decimal('8'))

    strategy = StrategySwingTrade(config_teste, position_mgr, gestao_cap)

    print("\n" + "="*60)
    print("TESTE: Strategy Swing Trade")
    print("="*60)

    stats = strategy.obter_estatisticas()
    print(f"\nEstratégia: {stats['estrategia']}")
    print(f"Habilitada: {stats['habilitada']}")
    print(f"Alocação: {stats['alocacao_capital_pct']}%")
    print(f"Gatilho compra: {stats['gatilho_compra_pct']}%")
    print(f"Meta lucro: {stats['meta_lucro_pct']}%")
    print(f"\n✅ Estratégia de Giro Rápido inicializada com sucesso!")
