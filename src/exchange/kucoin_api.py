from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from decimal import Decimal # KuCoin client might return strings, convert to float
import time

# KuCoin library imports
from kucoin.client import Market, Trade, User

from src.utils.logger import get_loggers
from src.exchange.base import ExchangeAPI

logger, _ = get_loggers()

class KucoinAPI(ExchangeAPI):
    def __init__(self, api_key: str, api_secret: str, api_passphrase: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase

        self.market_client = Market(api_key, api_secret, api_passphrase)
        self.trade_client = Trade(api_key, api_secret, api_passphrase)
        self.user_client = User(api_key, api_secret, api_passphrase)

    def _format_pair(self, par: str) -> str:
        """Converte o par de 'ADA/USDT' para 'ADA-USDT'."""
        return par.replace('/', '-')

    def get_preco_atual(self, par: str) -> float:
        try:
            kucoin_par = self._format_pair(par)
            ticker = self.market_client.get_ticker(symbol=kucoin_par)
            if ticker and 'price' in ticker:
                return float(ticker['price'])
            raise ValueError(f"Preço não encontrado para {kucoin_par}")
        except Exception as e:
            logger.error(f"Erro ao obter preço atual para {par} na KuCoin: {e}")
            raise

    def get_saldo_disponivel(self, moeda: str) -> float:
        try:
            accounts = self.user_client.get_account_list()
            for account in accounts:
                if account['currency'].upper() == moeda.upper():
                    return float(account['available'])
            return 0.0
        except Exception as e:
            logger.error(f"Erro ao obter saldo disponível para {moeda} na KuCoin: {e}")
            raise

    def place_ordem_compra_market(self, par: str, quantidade: float) -> Dict[str, Any]:
        try:
            kucoin_par = self._format_pair(par)
            # KuCoin market order 'size' is base currency amount
            order = self.trade_client.create_market_order(
                symbol=kucoin_par,
                side='buy',
                size=str(quantidade) # KuCoin API expects string for quantity
            )
            return order
        except Exception as e:
            logger.error(f"Erro ao colocar ordem de compra a mercado para {par} ({quantidade}) na KuCoin: {e}")
            raise

    def place_ordem_venda_market(self, par: str, quantidade: float) -> Dict[str, Any]:
        try:
            kucoin_par = self._format_pair(par)
            order = self.trade_client.create_market_order(
                symbol=kucoin_par,
                side='sell',
                size=str(quantidade) # KuCoin API expects string for quantity
            )
            return order
        except Exception as e:
            logger.error(f"Erro ao colocar ordem de venda a mercado para {par} ({quantidade}) na KuCoin: {e}")
            raise

    def get_info_conta(self) -> Dict[str, Any]:
        try:
            accounts = self.user_client.get_account_list()
            # Return a summary of accounts, or just the raw list
            # For now, return a simplified summary
            summary = {"balances": []}
            for account in accounts:
                summary["balances"].append({
                    "currency": account['currency'],
                    "available": float(account['available']),
                    "holds": float(account['holds'])
                })
            return summary
        except Exception as e:
            logger.error(f"Erro ao obter informações da conta na KuCoin: {e}")
            raise

    def check_connection(self) -> bool:
        """
        Verifica a conexão com a API da KuCoin tentando obter informações do usuário.
        """
        try:
            # O método get_account_list() é uma boa forma de verificar se a autenticação está OK
            self.user_client.get_account_list()
            return True
        except Exception as e:
            logger.error(f"Falha na verificação de conexão com a KuCoin: {e}") # Changed print to logger.error
            return False

    def get_historico_ordens(self, par: str, limite: int = 500, order_id: Optional[int] = None) -> List[Dict]:
        """
        Busca o histórico de ordens para um par.
        ATENÇÃO: A lógica real precisa ser implementada.
        """
        # TODO: Implementar a busca de histórico de ordens na API da KuCoin.
        # Por enquanto, esta função retornará uma lista vazia para não quebrar o programa.
        logger.warning(f"AVISO: A função get_historico_ordens para o par {par} ainda não foi totalmente implementada para a KuCoin.") # Changed print to logger.warning
        return []
