"""
API Manager - Comunicação com Binance API
"""
import hashlib
import hmac
import time
from decimal import Decimal
from typing import Dict, List, Optional
from urllib.parse import urlencode

import requests

from src.utils.logger import get_logger

logger = get_logger()


class APIManager:
    """
    Gerencia comunicação com Binance API

    Recursos:
    - Autenticação HMAC SHA256
    - Requisições REST
    - Tratamento de erros
    - Rate limiting
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str):
        """
        Args:
            api_key: API Key da Binance
            api_secret: API Secret da Binance
            base_url: URL base da API
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': self.api_key
        })

    def _gerar_assinatura(self, query_string: str) -> str:
        """
        Gera assinatura HMAC SHA256

        Args:
            query_string: String de parâmetros

        Returns:
            Assinatura hexadecimal
        """
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _fazer_requisicao(
        self,
        metodo: str,
        endpoint: str,
        assinado: bool = False,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Faz requisição para API

        Args:
            metodo: GET, POST, DELETE, etc
            endpoint: Endpoint da API
            assinado: Se requer assinatura
            params: Parâmetros da requisição

        Returns:
            Resposta JSON
        """
        url = f"{self.base_url}{endpoint}"
        params = params or {}

        if assinado:
            params['timestamp'] = int(time.time() * 1000)
            query_string = urlencode(params)
            params['signature'] = self._gerar_assinatura(query_string)

        try:
            response = self.session.request(
                metodo,
                url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            # Tentar extrair mensagem de erro do JSON
            try:
                erro_json = e.response.json() if hasattr(e, 'response') and e.response else {}
                mensagem_erro = erro_json.get('msg', str(e))
                logger.erro_api(endpoint, f"{str(e)} | Detalhes: {mensagem_erro}")
            except:
                logger.erro_api(endpoint, str(e))
            raise

    def obter_saldos(self) -> List[Dict]:
        """
        Obtém saldos da conta

        Returns:
            Lista de saldos: [{'asset': 'BRL', 'free': '100.00', 'locked': '0.00'}, ...]
        """
        try:
            resposta = self._fazer_requisicao(
                'GET',
                '/api/v3/account',
                assinado=True
            )

            # Filtrar apenas saldos > 0
            saldos = []
            for balance in resposta.get('balances', []):
                free = Decimal(balance['free'])
                locked = Decimal(balance['locked'])
                total = free + locked

                if total > 0:
                    saldos.append({
                        'asset': balance['asset'],
                        'free': str(free),
                        'locked': str(locked),
                        'total': str(total)
                    })

            return saldos

        except Exception as e:
            logger.erro_api('obter_saldos', str(e))
            return []

    def obter_ticker(self, simbolo: str) -> Dict:
        """
        Obtém ticker de preço

        Args:
            simbolo: Par (ex: ADAUSDT, USDTBRL)

        Returns:
            {'symbol': 'ADAUSDT', 'price': '0.8150'}
        """
        try:
            resposta = self._fazer_requisicao(
                'GET',
                '/api/v3/ticker/price',
                params={'symbol': simbolo.upper()}
            )
            return resposta

        except Exception as e:
            logger.erro_api(f'obter_ticker/{simbolo}', str(e))
            raise

    def criar_ordem_mercado(
        self,
        simbolo: str,
        lado: str,
        quantidade: float
    ) -> Optional[Dict]:
        """
        Cria ordem a mercado

        Args:
            simbolo: Par (ex: ADAUSDT, USDTBRL)
            lado: BUY ou SELL
            quantidade: Quantidade da moeda base

        Returns:
            Dados da ordem executada ou None se falhou
        """
        try:
            params = {
                'symbol': simbolo.upper(),
                'side': lado.upper(),
                'type': 'MARKET',
                'quantity': quantidade
            }

            logger.info(f"📤 Criando ordem: {lado} {quantidade} {simbolo}")

            resposta = self._fazer_requisicao(
                'POST',
                '/api/v3/order',
                assinado=True,
                params=params
            )

            logger.info(f"✅ Ordem executada: {resposta.get('orderId')}")
            return resposta

        except Exception as e:
            logger.erro_api(f'criar_ordem/{simbolo}', str(e))
            return None

    def obter_info_simbolo(self, simbolo: str) -> Optional[Dict]:
        """
        Obtém informações do símbolo

        Args:
            simbolo: Par (ex: ADAUSDT)

        Returns:
            Informações do símbolo (filters, precision, etc)
        """
        try:
            resposta = self._fazer_requisicao(
                'GET',
                '/api/v3/exchangeInfo',
                params={'symbol': simbolo.upper()}
            )

            symbols = resposta.get('symbols', [])
            if symbols:
                return symbols[0]
            return None

        except Exception as e:
            logger.erro_api(f'obter_info_simbolo/{simbolo}', str(e))
            return None

    def verificar_conexao(self) -> bool:
        """
        Verifica se API está acessível

        Returns:
            True se conectado, False caso contrário
        """
        try:
            self._fazer_requisicao('GET', '/api/v3/ping')
            return True
        except:
            return False

    def obter_klines(
        self,
        simbolo: str,
        intervalo: str,
        limite: int = 500,
        inicio: Optional[int] = None,
        fim: Optional[int] = None
    ) -> List[List]:
        """
        Obtém histórico de candlesticks (klines)

        Args:
            simbolo: Par (ex: ADAUSDT)
            intervalo: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
            limite: Número de candles (max 1000)
            inicio: Timestamp início em ms (opcional)
            fim: Timestamp fim em ms (opcional)

        Returns:
            Lista de klines: [
                [
                    timestamp_abertura,
                    preco_abertura,
                    preco_maximo,
                    preco_minimo,
                    preco_fechamento,
                    volume,
                    timestamp_fechamento,
                    ...
                ]
            ]
        """
        try:
            params = {
                'symbol': simbolo.upper(),
                'interval': intervalo,
                'limit': min(limite, 1000)  # Binance limita em 1000
            }

            if inicio:
                params['startTime'] = inicio
            if fim:
                params['endTime'] = fim

            resposta = self._fazer_requisicao(
                'GET',
                '/api/v3/klines',
                params=params
            )

            return resposta

        except Exception as e:
            logger.erro_api(f'obter_klines/{simbolo}/{intervalo}', str(e))
            return []

    def obter_historico_ordens(
        self,
        simbolo: str,
        limite: int = 500,
        order_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Obtém histórico de ordens de um símbolo

        Args:
            simbolo: Par (ex: ADAUSDT)
            limite: Número máximo de ordens (default: 500, max: 1000)
            order_id: ID da ordem para buscar a partir dela (opcional)

        Returns:
            Lista de ordens: [
                {
                    'symbol': 'ADAUSDT',
                    'orderId': 123456,
                    'clientOrderId': 'web_xxx',
                    'price': '0.00',
                    'origQty': '10.0',
                    'executedQty': '10.0',
                    'cummulativeQuoteQty': '6.50',
                    'status': 'FILLED',
                    'type': 'MARKET',
                    'side': 'BUY',
                    'time': 1234567890000,
                    'updateTime': 1234567890000,
                    'isWorking': False,
                    ...
                }
            ]
        """
        try:
            params = {
                'symbol': simbolo.upper(),
                'limit': min(limite, 1000)  # Binance limita em 1000
            }

            if order_id:
                params['orderId'] = order_id

            resposta = self._fazer_requisicao(
                'GET',
                '/api/v3/allOrders',
                assinado=True,
                params=params
            )

            # Filtrar apenas ordens FILLED (executadas)
            ordens_executadas = [
                ordem for ordem in resposta
                if ordem.get('status') == 'FILLED'
            ]

            return ordens_executadas

        except Exception as e:
            logger.erro_api(f'obter_historico_ordens/{simbolo}', str(e))
            return []
