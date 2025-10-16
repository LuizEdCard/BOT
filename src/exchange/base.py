from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

class ExchangeAPI(ABC):
    """
    Classe base abstrata para APIs de corretoras.
    Define a interface que todas as classes de API de corretora devem implementar.
    """

    @abstractmethod
    def get_preco_atual(self, par: str) -> float:
        """
        Obtém o preço atual de um par de moedas.

        Args:
            par: O par de moedas (ex: 'ADA/USDT').

        Returns:
            O preço atual como um float.
        """
        raise NotImplementedError

    @abstractmethod
    def get_saldo_disponivel(self, moeda: str) -> float:
        """
        Obtém o saldo disponível de uma moeda específica.

        Args:
            moeda: A sigla da moeda (ex: 'USDT').

        Returns:
            O saldo disponível como um float.
        """
        raise NotImplementedError

    @abstractmethod
    def place_ordem_compra_market(self, par: str, quantidade: float) -> Dict[str, Any]:
        """
        Coloca uma ordem de compra a mercado.

        Args:
            par: O par de moedas (ex: 'ADA/USDT').
            quantidade: A quantidade a ser comprada.

        Returns:
            Um dicionário com as informações da ordem.
        """
        raise NotImplementedError

    @abstractmethod
    def place_ordem_venda_market(self, par: str, quantidade: float) -> Dict[str, Any]:
        """
        Coloca uma ordem de venda a mercado.

        Args:
            par: O par de moedas (ex: 'ADA/USDT').
            quantidade: A quantidade a ser vendida.

        Returns:
            Um dicionário com as informações da ordem.
        """
        raise NotImplementedError

    @abstractmethod
    def get_info_conta(self) -> Dict[str, Any]:
        """
        Obtém informações gerais da conta.

        Returns:
            Um dicionário com as informações da conta.
        """
        raise NotImplementedError

    @abstractmethod
    def check_connection(self) -> bool:
        """
        Verifica a conectividade com a API da exchange.

        Returns:
            True se a conexão for bem-sucedida, False caso contrário.
        """
        raise NotImplementedError

    @abstractmethod
    def get_historico_ordens(self, par: str, limite: int = 500, order_id: Optional[int] = None) -> List[Dict]:
        """
        Obtém o histórico de ordens de um par específico.

        Args:
            par: O par de moedas (ex: 'ADA/USDT').
            limite: O número máximo de ordens a serem retornadas.
            order_id: O ID da ordem a partir da qual buscar (opcional).

        Returns:
            Uma lista de dicionários, onde cada dicionário representa uma ordem.
        """
        raise NotImplementedError
