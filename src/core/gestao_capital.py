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

    REGRAS:
    - Reserva obrigatória: 8% do capital total
    - Saldo mínimo: $5.00 USDT
    - Capital ativo: 92% disponível para trading
    """

    def __init__(self, saldo_usdt: Decimal = Decimal('0'), valor_posicao_ada: Decimal = Decimal('0'), percentual_reserva: Decimal = Decimal('8')):
        """
        Inicializar gestor de capital

        Args:
            saldo_usdt: Saldo atual em USDT
            valor_posicao_ada: Valor da posição em ADA (em USDT)
            percentual_reserva: Percentual da reserva (padrão: 8%)
        """
        self.saldo_usdt = saldo_usdt
        self.valor_posicao_ada = valor_posicao_ada
        self.percentual_reserva = percentual_reserva / Decimal('100')
        self.saldo_minimo = Decimal('5.00')

    def atualizar_saldos(self, saldo_usdt: Decimal, valor_posicao_ada: Decimal = Decimal('0')):
        """
        Atualizar saldos para recálculo

        Args:
            saldo_usdt: Novo saldo USDT
            valor_posicao_ada: Novo valor da posição ADA
        """
        self.saldo_usdt = saldo_usdt
        self.valor_posicao_ada = valor_posicao_ada

    def calcular_capital_total(self) -> Decimal:
        """
        Calcula capital total (USDT + posição ADA)

        Returns:
            Capital total em USDT
        """
        return self.saldo_usdt + self.valor_posicao_ada

    def calcular_reserva_obrigatoria(self) -> Decimal:
        """
        Calcula reserva obrigatória (8% do capital total)

        Returns:
            Valor da reserva em USDT
        """
        capital_total = self.calcular_capital_total()
        return capital_total * self.percentual_reserva

    def calcular_capital_disponivel(self) -> Decimal:
        """
        Calcula capital disponível para trading (92% do capital ativo)

        Returns:
            Capital disponível em USDT
        """
        reserva = self.calcular_reserva_obrigatoria()
        return self.saldo_usdt - reserva

    def get_alocacao_percentual_ada(self) -> Decimal:
        """Calcula o percentual do capital total que está alocado em ADA."""
        capital_total = self.calcular_capital_total()
        if capital_total <= 0:
            return Decimal('0')

        # self.valor_posicao_ada é o valor da posição ADA em USDT
        return (self.valor_posicao_ada / capital_total) * Decimal('100')

    def pode_comprar(self, valor_operacao: Decimal) -> Tuple[bool, str]:
        """
        Valida se pode comprar sem violar reserva.

        VALIDAÇÕES:
        1. Capital disponível suficiente (descontando reserva)
        2. Saldo após compra mantém reserva
        3. Saldo após compra >= $5.00

        Args:
            valor_operacao: Valor da operação em USDT

        Returns:
            (pode: bool, motivo: str)
        """
        # 1. Calcular reserva obrigatória
        capital_total = self.calcular_capital_total()
        reserva_obrigatoria = self.calcular_reserva_obrigatoria()

        logger.debug(f"💰 Capital total: ${capital_total:.2f}")
        logger.debug(f"🛡️ Reserva obrigatória (8%): ${reserva_obrigatoria:.2f}")

        # 2. Capital disponível (descontando reserva)
        capital_disponivel = self.calcular_capital_disponivel()

        logger.debug(f"✅ Capital disponível: ${capital_disponivel:.2f}")
        logger.debug(f"🎯 Valor operação: ${valor_operacao:.2f}")

        # 3. Verificar se tem saldo disponível
        if capital_disponivel < valor_operacao:
            motivo = (
                f"Capital ativo insuficiente: ${capital_disponivel:.2f} < ${valor_operacao:.2f} "
                f"(Reserva protegida: ${reserva_obrigatoria:.2f})"
            )
            logger.warning(f"⚠️ {motivo}")
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
            logger.warning(f"🛡️ {motivo}")
            return False, motivo

        # 6. Nunca deixar menos de $5
        if saldo_apos < self.saldo_minimo:
            motivo = f"Saldo ficaria abaixo do mínimo: ${saldo_apos:.2f} < ${self.saldo_minimo:.2f}"
            logger.warning(f"⚠️ {motivo}")
            return False, motivo

        # ✅ APROVADO
        logger.debug(f"✅ Operação aprovada: ${valor_operacao:.2f}")
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
        Obtém resumo do capital e reserva

        Returns:
            Dicionário com informações do capital
        """
        capital_total = self.calcular_capital_total()
        reserva_obrigatoria = self.calcular_reserva_obrigatoria()
        capital_disponivel = self.calcular_capital_disponivel()

        return {
            'saldo_usdt': self.saldo_usdt,
            'valor_posicao_ada': self.valor_posicao_ada,
            'capital_total': capital_total,
            'reserva_obrigatoria': reserva_obrigatoria,
            'capital_disponivel': capital_disponivel,
            'percentual_reserva': float(self.percentual_reserva * 100),
            'saldo_minimo': self.saldo_minimo
        }

    def log_resumo(self):
        """Exibe resumo do capital no log"""
        resumo = self.obter_resumo()

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("💰 GESTÃO DE CAPITAL")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"   Saldo USDT: ${resumo['saldo_usdt']:.2f}")
        logger.info(f"   Posição ADA: ${resumo['valor_posicao_ada']:.2f}")
        logger.info(f"   Capital Total: ${resumo['capital_total']:.2f}")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"   🛡️ Reserva ({resumo['percentual_reserva']:.0f}%): ${resumo['reserva_obrigatoria']:.2f}")
        logger.info(f"   ✅ Disponível (92%): ${resumo['capital_disponivel']:.2f}")
        logger.info(f"   ⚠️ Mínimo obrigatório: ${resumo['saldo_minimo']:.2f}")
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
