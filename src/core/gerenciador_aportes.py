"""
Gerenciador de Aportes - Conversão BRL → USDT
"""
from decimal import Decimal
from typing import Optional, Dict
from datetime import datetime
import time

from src.utils.logger import get_loggers

logger, _ = get_loggers()


class GerenciadorAportes:
    """
    Gerencia depósitos em BRL e conversão automática para USDT

    Fluxo:
    1. Detecta saldo BRL na conta
    2. Converte todo saldo BRL → USDT (par USDT/BRL)
    3. Registra como aporte
    4. Disponibiliza USDT para trading ADA/USDT
    """

    def __init__(self, api_manager, settings):
        """
        Args:
            api_manager: Instância do APIManager
            settings: Configurações do sistema (dict ou objeto)
        """
        self.api = api_manager
        self.settings = settings
        # Support both dict and object config
        if isinstance(settings, dict):
            self.aportes_config = settings.get('APORTES', {})
        else:
            self.aportes_config = settings.APORTES

    def verificar_saldo_brl(self) -> Decimal:
        """
        Verifica saldo disponível em BRL

        Returns:
            Decimal: Saldo BRL disponível
        """
        try:
            # Use get_saldo_disponivel method from BinanceAPI
            saldo_brl = Decimal(str(self.api.get_saldo_disponivel('BRL')))
            logger.info(f"💰 Saldo BRL detectado: R$ {saldo_brl:.2f}")
            return saldo_brl

        except Exception as e:
            logger.erro_api("verificar_saldo_brl", f"Erro ao verificar saldo BRL: {e}")
            return Decimal('0')

    def verificar_saldo_usdt(self) -> Decimal:
        """
        Verifica saldo disponível em USDT

        Returns:
            Decimal: Saldo USDT disponível
        """
        try:
            # Use get_saldo_disponivel method from BinanceAPI
            saldo_usdt = Decimal(str(self.api.get_saldo_disponivel('USDT')))
            logger.info(f"💵 Saldo USDT detectado: $ {saldo_usdt:.2f}")
            return saldo_usdt

        except Exception as e:
            logger.erro_api("verificar_saldo_usdt", f"Erro ao verificar saldo USDT: {e}")
            return Decimal('0')

    def obter_preco_usdt_brl(self) -> Optional[Decimal]:
        """
        Obtém preço atual USDT/BRL

        Returns:
            Decimal: Preço USDT em BRL (ex: 5.80)
            None: Se houver erro
        """
        try:
            # Use get_preco_atual method from BinanceAPI
            preco = Decimal(str(self.api.get_preco_atual('USDT/BRL')))
            logger.info(f"📊 Cotação USDT/BRL: R$ {preco:.4f}")
            return preco

        except Exception as e:
            logger.erro_api("obter_preco_usdt_brl", f"Erro ao obter preço USDT/BRL: {e}")
            return None

    def calcular_quantidade_usdt(self, valor_brl: Decimal, preco_usdt_brl: Decimal) -> Decimal:
        """
        Calcula quanto USDT será obtido com valor BRL

        Args:
            valor_brl: Valor em BRL a ser convertido
            preco_usdt_brl: Preço USDT em BRL

        Returns:
            Decimal: Quantidade de USDT a receber
        """
        # BRL / Preço_USDT = USDT
        # Exemplo: 100 BRL / 5.80 = 17.24 USDT
        quantidade_usdt = valor_brl / preco_usdt_brl

        # Binance USDTBRL exige múltiplos de 0.1 (LOT_SIZE filter)
        # Arredondar para baixo para 1 casa decimal
        quantidade_usdt = (quantidade_usdt * Decimal('10')).quantize(Decimal('1'), rounding='ROUND_DOWN') / Decimal('10')

        logger.info(f"🔄 Conversão: R$ {valor_brl:.2f} → $ {quantidade_usdt:.1f} USDT")
        return quantidade_usdt

    def converter_brl_para_usdt(self, valor_brl: Optional[Decimal] = None) -> Dict:
        """
        Converte BRL para USDT usando par USDT/BRL

        Args:
            valor_brl: Valor específico a converter (None = todo saldo BRL)

        Returns:
            dict: {
                'sucesso': bool,
                'valor_brl': Decimal,
                'quantidade_usdt': Decimal,
                'preco': Decimal,
                'order_id': str,
                'mensagem': str
            }
        """
        try:
            saldo_brl = self.verificar_saldo_brl()

            valor_minimo_brl = Decimal(str(self.aportes_config['valor_minimo_brl_para_converter']))

            if saldo_brl < valor_minimo_brl:
                return {
                    'sucesso': False,
                    'valor_brl': saldo_brl,
                    'mensagem': f"Saldo BRL insuficiente: R$ {saldo_brl:.2f} (mínimo: R$ {valor_minimo_brl:.2f})"
                }

            # 2. Definir valor a converter
            valor_converter = valor_brl if valor_brl else saldo_brl

            if valor_converter > saldo_brl:
                return {
                    'sucesso': False,
                    'valor_brl': valor_converter,
                    'mensagem': f"Valor solicitado (R$ {valor_converter:.2f}) maior que saldo (R$ {saldo_brl:.2f})"
                }

            # 3. Obter preço USDT/BRL
            preco_usdt_brl = self.obter_preco_usdt_brl()
            if not preco_usdt_brl:
                return {
                    'sucesso': False,
                    'valor_brl': valor_converter,
                    'mensagem': "Não foi possível obter preço USDT/BRL"
                }

            # 4. Calcular quantidade USDT
            quantidade_usdt = self.calcular_quantidade_usdt(valor_converter, preco_usdt_brl)

            # 5. Criar ordem SELL USDT/BRL (vender USDT por BRL = comprar USDT com BRL)
            # Na Binance, USDT/BRL:
            # - BUY = comprar USDT pagando em BRL
            # - SELL = vender USDT recebendo BRL
            # Queremos COMPRAR USDT com BRL

            logger.info(f"🔄 Criando ordem: COMPRAR {quantidade_usdt} USDT com R$ {valor_converter:.2f}")

            # Converter para float garantindo 1 casa decimal
            qtd_float = round(float(quantidade_usdt), 1)

            # Use place_ordem_compra_market method from BinanceAPI
            ordem = self.api.place_ordem_compra_market(
                par='USDT/BRL',
                quantidade=qtd_float
            )

            if ordem and ordem.get('status') == 'FILLED':
                logger.aporte_detectado(
                    valor=float(valor_converter),
                    moeda='BRL',
                    usdt_recebido=float(quantidade_usdt)
                )

                return {
                    'sucesso': True,
                    'valor_brl': valor_converter,
                    'quantidade_usdt': quantidade_usdt,
                    'preco': preco_usdt_brl,
                    'order_id': ordem.get('orderId'),
                    'mensagem': f"✅ Convertido: R$ {valor_converter:.2f} → $ {quantidade_usdt:.2f} USDT"
                }
            else:
                return {
                    'sucesso': False,
                    'valor_brl': valor_converter,
                    'mensagem': f"Erro ao executar ordem: {ordem}"
                }

        except Exception as e:
            logger.erro_api("converter_brl_para_usdt", f"Erro ao converter BRL → USDT: {e}")
            return {
                'sucesso': False,
                'mensagem': f"Exceção: {str(e)}"
            }

    def processar_aporte_automatico(self) -> Dict:
        """
        Verifica se há BRL disponível e converte automaticamente para USDT

        Esta função deve ser chamada periodicamente para detectar novos depósitos

        Returns:
            dict: Resultado da conversão
        """
        logger.info("🔍 Verificando aportes em BRL...")

        saldo_brl = self.verificar_saldo_brl()
        valor_minimo_brl = Decimal(str(self.aportes_config['valor_minimo_brl_para_converter']))

        if saldo_brl >= valor_minimo_brl:
            logger.info(f"💰 Aporte detectado: R$ {saldo_brl:.2f}")
            logger.info("🔄 Iniciando conversão automática BRL → USDT...")

            resultado = self.converter_brl_para_usdt()

            if resultado['sucesso']:
                logger.info(f"✅ {resultado['mensagem']}")

                # Aguardar 2 segundos para saldo atualizar
                time.sleep(2)

                # Verificar novo saldo USDT
                saldo_usdt = self.verificar_saldo_usdt()
                logger.saldo_atualizado('USDT', float(saldo_usdt))

            return resultado
        else:
            return {
                'sucesso': False,
                'valor_brl': saldo_brl,
                'mensagem': f"Nenhum aporte detectado (saldo BRL: R$ {saldo_brl:.2f})"
            }

    def obter_resumo_saldos(self) -> Dict:
        """
        Obtém resumo de todos os saldos relevantes

        Returns:
            dict: {
                'brl': Decimal,
                'usdt': Decimal,
                'ada': Decimal,
                'total_usdt_equivalente': Decimal
            }
        """
        try:
            # Use individual balance calls instead of obter_saldos()
            saldo_brl = Decimal(str(self.api.get_saldo_disponivel('BRL')))
            saldo_usdt = Decimal(str(self.api.get_saldo_disponivel('USDT')))
            saldo_ada = Decimal(str(self.api.get_saldo_disponivel('ADA')))

            # Calcular total em USDT equivalente
            total_usdt = saldo_usdt

            # Converter BRL para USDT equivalente
            if saldo_brl > 0:
                preco_usdt_brl = self.obter_preco_usdt_brl()
                if preco_usdt_brl:
                    total_usdt += (saldo_brl / preco_usdt_brl)

            # Converter ADA para USDT equivalente
            if saldo_ada > 0:
                preco_ada = Decimal(str(self.api.get_preco_atual('ADA/USDT')))
                total_usdt += (saldo_ada * preco_ada)

            resumo = {
                'brl': saldo_brl,
                'usdt': saldo_usdt,
                'ada': saldo_ada,
                'total_usdt_equivalente': total_usdt.quantize(Decimal('0.01'))
            }

            logger.info("=" * 50)
            logger.info("💼 RESUMO DE SALDOS")
            logger.info(f"   BRL:  R$ {saldo_brl:.2f}")
            logger.info(f"   USDT: $ {saldo_usdt:.2f}")
            logger.info(f"   ADA:  {saldo_ada:.2f} ADA")
            logger.info(f"   TOTAL (USD equivalente): $ {resumo['total_usdt_equivalente']:.2f}")
            logger.info("=" * 50)

            return resumo

        except Exception as e:
            logger.erro_api("obter_resumo_saldos", f"Erro ao obter resumo de saldos: {e}")
            return {
                'brl': Decimal('0'),
                'usdt': Decimal('0'),
                'ada': Decimal('0'),
                'total_usdt_equivalente': Decimal('0')
            }
