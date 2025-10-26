"""
Gestão de Capital - Validação rigorosa de saldo e reserva

PROTEÇÃO CRÍTICA:
- Nunca permitir operações que violem a reserva de 8%
- Sempre manter mínimo de $5 USDT em saldo
- Validar ANTES e DEPOIS de cada operação
"""

from decimal import Decimal
from typing import Optional, Tuple
from pathlib import Path
import sys

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.logger import get_loggers

# Logger usa configuração padrão (não precisa especificar nível)
logger, _ = get_loggers(
    log_dir=Path('logs'),
    console=True
)


class GestaoCapital:
    """
    Gerenciador de capital com validação rigorosa de reserva

    Suporta múltiplas carteiras lógicas:
    - 'acumulacao': Carteira principal de acumulação (DCA)
    - 'giro_rapido': Carteira de swing trade (operações rápidas)

    REGRAS:
    - Reserva obrigatória: 8% do capital total
    - Saldo mínimo: $5.00 USDT
    - Capital ativo: 92% disponível para trading
    - Cada carteira tem seu próprio saldo alocado
    """

    def __init__(self, saldo_usdt: Decimal = Decimal('0'), valor_posicao_ada: Decimal = Decimal('0'), percentual_reserva: Decimal = Decimal('8'), modo_simulacao: bool = False, exchange_api=None):
        """
        Inicializar gestor de capital

        Args:
            saldo_usdt: Saldo total atual em USDT
            valor_posicao_ada: Valor da posição em ADA (em USDT) - carteira acumulação
            percentual_reserva: Percentual da reserva (padrão: 8%)
            modo_simulacao: Se True, permite atualização direta de saldo (para backtesting)
            exchange_api: Referência à API de exchange (necessária para sincronização em modo simulação)
        """
        self.saldo_usdt = saldo_usdt
        self.percentual_reserva = percentual_reserva / Decimal('100')
        self.saldo_minimo = Decimal('5.00')
        self.modo_simulacao = modo_simulacao
        self.exchange_api = exchange_api  # Necessário para modo simulação

        # Carteiras separadas
        self.carteiras = {
            'acumulacao': {
                'valor_posicao': valor_posicao_ada,
                'saldo_alocado': Decimal('0')  # Calculado dinamicamente
            },
            'giro_rapido': {
                'valor_posicao': Decimal('0'),
                'saldo_alocado': Decimal('0')  # Percentual do saldo livre
            }
        }

        # ✅ Alocação será configurada via configurar_alocacao_giro_rapido()
        # NÃO usar padrão hardcoded aqui - deixar None para detectar se foi configurado
        self.alocacao_giro_rapido_pct = None
        # Último motivo de bloqueio registrado (para evitar spam de logs)
        # Guardamos a última mensagem de motivo retornada por pode_comprar e só
        # logamos novamente se o motivo mudar (ou se a operação for aprovada).
        self._ultimo_motivo_bloqueio = None

    def configurar_alocacao_giro_rapido(self, percentual: Decimal):
        """
        Configura o percentual de alocação para a carteira de giro rápido

        Args:
            percentual: Percentual do saldo livre a alocar para giro rápido
        """
        self.alocacao_giro_rapido_pct = percentual
        logger.debug(f"⚙️ Alocação giro rápido configurada: {percentual}%")

    def atualizar_saldo_usdt_simulado(self, novo_saldo: Decimal):
        """
        Atualiza o saldo USDT diretamente (usado em modo simulação)

        IMPORTANTE: Este método só deve ser chamado em modo simulação,
        quando o BotWorker precisa sincronizar o saldo após operações
        na SimulatedExchangeAPI.

        Args:
            novo_saldo: Novo saldo USDT obtido da API simulada
        """
        if not self.modo_simulacao:
            logger.warning("⚠️ Tentativa de atualizar saldo simulado fora do modo simulação - ignorando")
            return

        saldo_anterior = self.saldo_usdt
        self.saldo_usdt = novo_saldo
        
        diferenca = novo_saldo - saldo_anterior
        simbolo = "+" if diferenca >= 0 else ""
        logger.debug(f"💰 Saldo USDT atualizado: ${saldo_anterior:.2f} → ${novo_saldo:.2f} ({simbolo}{diferenca:.2f})")

    def set_saldo_usdt_simulado(self, novo_saldo: Decimal, carteira: str):
        """
        Sincroniza o saldo USDT total com base nos saldos individuais das carteiras.

        IMPORTANTE: Este método é específico para modo simulação. Ele NÃO sobrescreve
        o saldo total com o valor de uma carteira. Em vez disso, calcula o saldo total
        como a soma dos saldos de AMBAS as carteiras (giro_rapido + acumulacao).

        Isso previne desincronização entre GestaoCapital e SimulatedExchangeAPI.

        Args:
            novo_saldo: Novo saldo USDT da carteira especificada (usado apenas para log)
            carteira: Nome da carteira ('acumulacao' ou 'giro_rapido')
        """
        if not self.modo_simulacao:
            logger.warning("⚠️ Tentativa de usar set_saldo_usdt_simulado fora do modo simulação - ignorando")
            return

        # IMPORTANTE: Calcular saldo total como SOMA de ambas as carteiras
        # em vez de sobrescrever com o valor de uma única carteira
        try:
            saldo_giro = Decimal(str(self.exchange_api.saldos_por_carteira['giro_rapido']['saldo_usdt']))
            saldo_acum = Decimal(str(self.exchange_api.saldos_por_carteira['acumulacao']['saldo_usdt']))
            saldo_total_novo = saldo_giro + saldo_acum
        except (KeyError, AttributeError, TypeError) as e:
            # Fallback se algo der errado com o acesso à API
            logger.warning(f"⚠️ Erro ao sincronizar saldo total: {e}. Usando valor fornecido como fallback.")
            saldo_total_novo = novo_saldo

        saldo_anterior = self.saldo_usdt
        self.saldo_usdt = saldo_total_novo

        diferenca = saldo_total_novo - saldo_anterior
        simbolo = "+" if diferenca >= 0 else ""
        logger.debug(f"💰 Saldo USDT sincronizado [{carteira}]: ${saldo_anterior:.2f} → ${saldo_total_novo:.2f} ({simbolo}{diferenca:.2f})")

    def atualizar_saldos(self, saldo_usdt: Decimal, valor_posicao_ada: Decimal = Decimal('0'), carteira: str = 'acumulacao'):
        """
        Atualizar saldos para recálculo

        Args:
            saldo_usdt: Novo saldo USDT total
            valor_posicao_ada: Novo valor da posição (em USDT)
            carteira: Nome da carteira ('acumulacao' ou 'giro_rapido')
        """
        self.saldo_usdt = saldo_usdt

        if carteira in self.carteiras:
            self.carteiras[carteira]['valor_posicao'] = valor_posicao_ada
        else:
            logger.warning(f"⚠️ Carteira '{carteira}' não reconhecida. Use 'acumulacao' ou 'giro_rapido'")

    def get_valor_posicao_total(self) -> Decimal:
        """
        Retorna o valor total investido em todas as carteiras

        Returns:
            Valor total das posições em USDT
        """
        return sum(carteira['valor_posicao'] for carteira in self.carteiras.values())

    def calcular_capital_total(self) -> Decimal:
        """
        Calcula capital total (USDT + todas as posições)

        Returns:
            Capital total em USDT
        """
        return self.saldo_usdt + self.get_valor_posicao_total()

    def calcular_reserva_obrigatoria(self) -> Decimal:
        """
        Calcula reserva obrigatória (8% do capital total)

        Returns:
            Valor da reserva em USDT
        """
        capital_total = self.calcular_capital_total()
        return capital_total * self.percentual_reserva

    def calcular_capital_disponivel(self, carteira: str = 'acumulacao') -> Decimal:
        """
        Calcula capital disponível para trading por carteira

        Em modo simulação, usa o saldo REAL da carteira (não recalcula percentual).
        Em modo real, calcula a divisão dinamicamente com base no saldo total.

        Args:
            carteira: Nome da carteira ('acumulacao' ou 'giro_rapido')

        Returns:
            Capital disponível em USDT para a carteira especificada
        """
        if self.modo_simulacao:
            # ✅ CRÍTICO: Em modo simulação, usar o saldo REAL da API
            # Não recalcular percentuais! A SimulatedExchangeAPI já mantém
            # os saldos separados corretamente após cada trade.
            try:
                saldo_carteira = Decimal(str(
                    self.exchange_api.saldos_por_carteira[carteira]['saldo_usdt']
                ))
                # Aplicar reserva apenas se necessário
                reserva = self.calcular_reserva_obrigatoria()
                return max(saldo_carteira - reserva, Decimal('0'))
            except (KeyError, AttributeError, TypeError) as e:
                logger.warning(f"⚠️ Erro ao obter saldo da carteira '{carteira}': {e}")
                return Decimal('0')
        else:
            # Em modo real: calcular dividindo o saldo livre
            reserva = self.calcular_reserva_obrigatoria()
            saldo_livre = self.saldo_usdt - reserva

            if saldo_livre <= 0:
                return Decimal('0')

            if carteira == 'giro_rapido':
                # ✅ Validação: alocacao_giro_rapido_pct DEVE ter sido configurado
                if self.alocacao_giro_rapido_pct is None:
                    logger.error("❌ ERRO CRÍTICO: alocacao_giro_rapido_pct não foi configurada! "
                                 "BotWorker.configurar_alocacao_giro_rapido() deve ser chamado durante inicialização.")
                    raise ValueError("alocacao_giro_rapido_pct não foi configurada - impossível alocar capital")

                # Giro rápido usa um percentual do saldo livre
                return saldo_livre * (self.alocacao_giro_rapido_pct / Decimal('100'))
            elif carteira == 'acumulacao':
                # ✅ Validação: alocacao_giro_rapido_pct DEVE ter sido configurado
                if self.alocacao_giro_rapido_pct is None:
                    logger.error("❌ ERRO CRÍTICO: alocacao_giro_rapido_pct não foi configurada! "
                                 "BotWorker.configurar_alocacao_giro_rapido() deve ser chamado durante inicialização.")
                    raise ValueError("alocacao_giro_rapido_pct não foi configurada - impossível alocar capital")

                # Acumulação usa o restante do saldo livre
                saldo_giro_rapido = saldo_livre * (self.alocacao_giro_rapido_pct / Decimal('100'))
                return saldo_livre - saldo_giro_rapido

        logger.warning(f"⚠️ Carteira '{carteira}' desconhecida. Retornando 0.")
        return Decimal('0')

    def get_alocacao_percentual_ada(self, carteira: str = 'acumulacao') -> Decimal:
        """
        Calcula o percentual do capital total que está alocado em ADA por carteira

        Args:
            carteira: Nome da carteira ('acumulacao' ou 'giro_rapido')

        Returns:
            Percentual de alocação
        """
        capital_total = self.calcular_capital_total()
        if capital_total <= 0:
            return Decimal('0')

        if carteira in self.carteiras:
            valor_posicao = self.carteiras[carteira]['valor_posicao']
            return (valor_posicao / capital_total) * Decimal('100')
        else:
            # Retornar total de todas as carteiras
            valor_total_posicoes = self.get_valor_posicao_total()
            return (valor_total_posicoes / capital_total) * Decimal('100')

    def pode_comprar(self, valor_operacao: Decimal, carteira: str = 'acumulacao') -> Tuple[bool, str]:
        """
        Valida se pode comprar sem violar reserva, respeitando alocação por carteira.

        VALIDAÇÕES:
        1. Capital disponível suficiente para a carteira especificada
        2. Saldo após compra mantém reserva global
        3. Saldo após compra >= $5.00

        Args:
            valor_operacao: Valor da operação em USDT
            carteira: Nome da carteira ('acumulacao' ou 'giro_rapido')

        Returns:
            (pode: bool, motivo: str)
        """
        # 1. Calcular reserva obrigatória
        capital_total = self.calcular_capital_total()
        reserva_obrigatoria = self.calcular_reserva_obrigatoria()

        logger.debug(f"💰 Capital total: ${capital_total:.2f}")
        logger.debug(f"🛡️ Reserva obrigatória (8%): ${reserva_obrigatoria:.2f}")

        # 2. Capital disponível para a carteira específica
        capital_disponivel = self.calcular_capital_disponivel(carteira)

        logger.debug(f"✅ Capital disponível ({carteira}): ${capital_disponivel:.2f}")
        logger.debug(f"🎯 Valor operação: ${valor_operacao:.2f}")

        # 3. Verificar se tem saldo disponível na carteira
        if capital_disponivel < valor_operacao:
            motivo = (
                f"Capital insuficiente na carteira '{carteira}': ${capital_disponivel:.2f} < ${valor_operacao:.2f} "
                f"(Reserva protegida: ${reserva_obrigatoria:.2f})"
            )
            # Evitar spam: logar apenas se o motivo mudou desde a última vez
            if motivo != getattr(self, '_ultimo_motivo_bloqueio', None):
                logger.warning(f"⚠️ {motivo}")
                self._ultimo_motivo_bloqueio = motivo
            return False, motivo

        # 4. Simular saldo após compra
        saldo_apos = self.saldo_usdt - valor_operacao

        logger.debug(f"📊 Saldo após compra: ${saldo_apos:.2f}")

        # 5. Verificar se mantém reserva APÓS compra
        if saldo_apos < reserva_obrigatoria:
            motivo = (
                f"Operação violaria reserva de 8%: saldo após (${saldo_apos:.2f}) < "
                f"reserva (${reserva_obrigatoria:.2f})"
            )
            # Evitar spam: logar apenas se o motivo mudou desde a última vez
            if motivo != getattr(self, '_ultimo_motivo_bloqueio', None):
                logger.warning(f"🛡️ {motivo}")
                self._ultimo_motivo_bloqueio = motivo
            return False, motivo

        # 6. Nunca deixar menos de $5
        if saldo_apos < self.saldo_minimo:
            motivo = f"Saldo ficaria abaixo do mínimo: ${saldo_apos:.2f} < ${self.saldo_minimo:.2f}"
            # Evitar spam: logar apenas se o motivo mudou desde a última vez
            if motivo != getattr(self, '_ultimo_motivo_bloqueio', None):
                logger.warning(f"⚠️ {motivo}")
                self._ultimo_motivo_bloqueio = motivo
            return False, motivo

        # ✅ APROVADO
        # Limpar último motivo de bloqueio quando uma operação é aprovada
        self._ultimo_motivo_bloqueio = None
        logger.debug(f"✅ Operação aprovada ({carteira}): ${valor_operacao:.2f}")
        logger.debug(f"   Saldo após: ${saldo_apos:.2f} (reserva: ${reserva_obrigatoria:.2f})")

        return True, ""

    def pode_vender(self, quantidade_ada: Decimal, preco_ada: Decimal) -> Tuple[bool, str]:
        """
        Valida se pode vender (sempre permitido, aumenta USDT)

        Args:
            quantidade_ada: Quantidade de ADA a vender
            preco_ada: Preço do ADA

        Returns:
            (pode: bool, motivo: str)
        """
        valor_venda = quantidade_ada * preco_ada

        # Venda sempre é permitida (aumenta capital)
        logger.debug(f"✅ Venda aprovada: {quantidade_ada} ADA @ ${preco_ada:.6f} = ${valor_venda:.2f}")

        return True, ""

    def obter_resumo(self) -> dict:
        """
        Obtém resumo do capital e reserva com detalhamento por carteira

        Returns:
            Dicionário com informações do capital
        """
        capital_total = self.calcular_capital_total()
        reserva_obrigatoria = self.calcular_reserva_obrigatoria()
        capital_disponivel_acumulacao = self.calcular_capital_disponivel('acumulacao')
        capital_disponivel_giro = self.calcular_capital_disponivel('giro_rapido')

        return {
            'saldo_usdt': self.saldo_usdt,
            'capital_total': capital_total,
            'reserva_obrigatoria': reserva_obrigatoria,
            'percentual_reserva': float(self.percentual_reserva * 100),
            'saldo_minimo': self.saldo_minimo,
            'carteiras': {
                'acumulacao': {
                    'valor_posicao': self.carteiras['acumulacao']['valor_posicao'],
                    'capital_disponivel': capital_disponivel_acumulacao
                },
                'giro_rapido': {
                    'valor_posicao': self.carteiras['giro_rapido']['valor_posicao'],
                    'capital_disponivel': capital_disponivel_giro,
                    'alocacao_pct': float(self.alocacao_giro_rapido_pct)
                }
            }
        }

    def log_resumo(self):
        """Exibe resumo do capital no log com detalhamento por carteira"""
        resumo = self.obter_resumo()

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("💰 GESTÃO DE CAPITAL (Múltiplas Carteiras)")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"   Saldo USDT Total: ${resumo['saldo_usdt']:.2f}")
        logger.info(f"   Capital Total: ${resumo['capital_total']:.2f}")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"   🛡️ Reserva ({resumo['percentual_reserva']:.0f}%): ${resumo['reserva_obrigatoria']:.2f}")
        logger.info(f"   ⚠️ Mínimo obrigatório: ${resumo['saldo_minimo']:.2f}")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("   📊 CARTEIRA ACUMULAÇÃO:")
        logger.info(f"      Posição: ${resumo['carteiras']['acumulacao']['valor_posicao']:.2f}")
        logger.info(f"      Disponível: ${resumo['carteiras']['acumulacao']['capital_disponivel']:.2f}")
        logger.info("   📈 CARTEIRA GIRO RÁPIDO:")
        logger.info(f"      Posição: ${resumo['carteiras']['giro_rapido']['valor_posicao']:.2f}")
        logger.info(f"      Disponível: ${resumo['carteiras']['giro_rapido']['capital_disponivel']:.2f}")
        logger.info(f"      Alocação: {resumo['carteiras']['giro_rapido']['alocacao_pct']:.0f}%")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# Função auxiliar para uso direto
def validar_compra(saldo_usdt: Decimal, valor_operacao: Decimal,
                   valor_posicao_ada: Decimal = Decimal('0')) -> Tuple[bool, str]:
    """
    Função auxiliar para validar compra rapidamente

    Args:
        saldo_usdt: Saldo atual USDT
        valor_operacao: Valor da operação
        valor_posicao_ada: Valor da posição ADA

    Returns:
        (pode: bool, motivo: str)
    """
    gestor = GestaoCapital(saldo_usdt, valor_posicao_ada)
    return gestor.pode_comprar(valor_operacao)
