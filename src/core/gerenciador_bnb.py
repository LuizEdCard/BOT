#!/usr/bin/env python3
"""
Gerenciador de BNB - Mantém saldo mínimo de BNB para desconto em taxas
"""
from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime, timedelta


class GerenciadorBNB:
    """
    Gerencia saldo de BNB para desconto nas taxas da Binance

    Benefícios:
    - 25% de desconto nas taxas quando paga com BNB
    - Taxa normal: 0.10% → Com BNB: 0.075%
    """

    def __init__(self, api_manager, settings):
        """
        Inicializa gerenciador

        Args:
            api_manager: Instância do APIManager
            settings: Configurações do bot
        """
        self.api = api_manager
        self.settings = settings

        # Controle de verificação
        self.ultima_verificacao = None
        self.intervalo_verificacao = timedelta(hours=24)  # Verifica 1x por dia

        # Configurações
        self.valor_minimo_bnb_usdt = Decimal('5.0')  # Manter pelo menos $5 em BNB
        self.valor_compra_bnb = Decimal('5.0')  # Comprar $5 USDT de BNB quando precisar

    def obter_saldo_bnb(self) -> Decimal:
        """Obtém saldo atual de BNB"""
        try:
            saldos = self.api.obter_saldos()

            for saldo in saldos:
                if saldo['asset'] == 'BNB':
                    return Decimal(str(saldo['free']))

            return Decimal('0')
        except Exception:
            return Decimal('0')

    def obter_preco_bnb_usdt(self) -> Optional[Decimal]:
        """Obtém preço atual de BNB em USDT"""
        try:
            ticker = self.api.obter_ticker('BNBUSDT')
            return Decimal(str(ticker['price']))
        except Exception:
            return None

    def calcular_valor_bnb_em_usdt(self, quantidade_bnb: Decimal) -> Optional[Decimal]:
        """Calcula valor do BNB em USDT"""
        preco_bnb = self.obter_preco_bnb_usdt()
        if preco_bnb is None:
            return None

        return quantidade_bnb * preco_bnb

    def precisa_comprar_bnb(self) -> bool:
        """
        Verifica se precisa comprar BNB

        Returns:
            True se saldo BNB < $5 USDT
        """
        saldo_bnb = self.obter_saldo_bnb()

        if saldo_bnb == 0:
            return True

        valor_bnb_usdt = self.calcular_valor_bnb_em_usdt(saldo_bnb)

        if valor_bnb_usdt is None:
            return False

        return valor_bnb_usdt < self.valor_minimo_bnb_usdt

    def comprar_bnb(self, saldo_usdt: Decimal) -> Dict:
        """
        Compra BNB com USDT

        Args:
            saldo_usdt: Saldo disponível de USDT

        Returns:
            Dict com resultado da operação
        """
        # Verificar se tem USDT suficiente
        if saldo_usdt < self.valor_compra_bnb:
            return {
                'sucesso': False,
                'mensagem': f'Saldo USDT insuficiente para comprar BNB: ${saldo_usdt:.2f} < ${self.valor_compra_bnb:.2f}'
            }

        # Obter preço do BNB
        preco_bnb = self.obter_preco_bnb_usdt()
        if preco_bnb is None:
            return {
                'sucesso': False,
                'mensagem': 'Não foi possível obter preço do BNB'
            }

        # Calcular quantidade de BNB a comprar
        quantidade_bnb = self.valor_compra_bnb / preco_bnb

        # Arredondar para 0.00001 (step size BNB)
        quantidade_bnb = (quantidade_bnb * Decimal('100000')).quantize(
            Decimal('1'), rounding='ROUND_DOWN'
        ) / Decimal('100000')

        # Verificar mínimo (0.00001 BNB)
        if quantidade_bnb < Decimal('0.00001'):
            return {
                'sucesso': False,
                'mensagem': f'Quantidade BNB muito baixa: {quantidade_bnb:.5f}'
            }

        try:
            # Executar compra
            ordem = self.api.criar_ordem_mercado(
                simbolo='BNBUSDT',
                lado='BUY',
                quantidade=float(quantidade_bnb)
            )

            if ordem and ordem.get('status') == 'FILLED':
                valor_gasto = Decimal(ordem.get('cummulativeQuoteQty', '0'))
                qtd_recebida = Decimal(ordem.get('executedQty', '0'))

                return {
                    'sucesso': True,
                    'mensagem': f'Comprou {qtd_recebida:.5f} BNB por ${valor_gasto:.2f} USDT',
                    'quantidade_bnb': qtd_recebida,
                    'valor_usdt': valor_gasto,
                    'preco': preco_bnb,
                    'order_id': ordem.get('orderId')
                }
            else:
                return {
                    'sucesso': False,
                    'mensagem': f'Erro ao executar ordem BNB: {ordem}'
                }

        except Exception as e:
            return {
                'sucesso': False,
                'mensagem': f'Erro ao comprar BNB: {str(e)}'
            }

    def verificar_e_comprar_bnb(self, saldo_usdt: Decimal, forcar: bool = False) -> Dict:
        """
        Verifica e compra BNB se necessário

        Args:
            saldo_usdt: Saldo disponível de USDT
            forcar: Se True, ignora intervalo de verificação

        Returns:
            Dict com resultado
        """
        agora = datetime.now()

        # Verificar intervalo (não verificar toda hora)
        if not forcar and self.ultima_verificacao is not None:
            tempo_desde_ultima = agora - self.ultima_verificacao
            if tempo_desde_ultima < self.intervalo_verificacao:
                return {
                    'sucesso': False,
                    'mensagem': 'Verificação de BNB já foi feita recentemente',
                    'precisa_comprar': False
                }

        # Atualizar timestamp
        self.ultima_verificacao = agora

        # Verificar se precisa comprar
        if not self.precisa_comprar_bnb():
            saldo_bnb = self.obter_saldo_bnb()
            valor_bnb = self.calcular_valor_bnb_em_usdt(saldo_bnb)

            return {
                'sucesso': True,
                'mensagem': f'Saldo BNB suficiente: {saldo_bnb:.5f} BNB (≈ ${valor_bnb:.2f})',
                'precisa_comprar': False
            }

        # Precisa comprar BNB
        resultado = self.comprar_bnb(saldo_usdt)
        resultado['precisa_comprar'] = True

        return resultado
