from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from decimal import Decimal
import hashlib
import hmac
import time
from urllib.parse import urlencode

import requests

from src.utils.logger import get_loggers
from src.exchange.base import ExchangeAPI # New import

logger, _ = get_loggers()


class BinanceAPI(ExchangeAPI):
    """
    Implementação da API da Binance, herdando da classe base ExchangeAPI.
    Gerencia a comunicação com a Binance API para operações de trading.
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str):
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

    # --- Métodos da Interface ExchangeAPI ---

    def get_preco_atual(self, par: str) -> float:
        """
        Obtém o preço atual de um par de moedas.
        Implementa o método abstrato de ExchangeAPI.
        """
        try:
            # Binance API expects 'ADAUSDT', not 'ADA/USDT'
            binance_symbol = par.replace('/', '').upper()
            resposta = self._fazer_requisicao(
                'GET',
                '/api/v3/ticker/price',
                params={'symbol': binance_symbol}
            )
            return float(resposta['price'])
        except Exception as e:
            logger.erro_api(f'get_preco_atual/{par}', str(e))
            raise

    def get_saldo_disponivel(self, moeda: str) -> float:
        """
        Obtém o saldo disponível de uma moeda específica.
        Implementa o método abstrato de ExchangeAPI.
        """
        try:
            saldos_raw = self._get_all_balances() # Call internal helper
            for saldo in saldos_raw:
                if saldo['asset'].upper() == moeda.upper():
                    return float(saldo['free'])
            return 0.0 # Return 0 if currency not found
        except Exception as e:
            logger.erro_api(f'get_saldo_disponivel/{moeda}', str(e))
            raise

    def place_ordem_compra_market(self, par: str, quantidade: float) -> Dict[str, Any]:
        """
        Coloca uma ordem de compra a mercado.
        Implementa o método abstrato de ExchangeAPI.
        """
        # Binance API expects 'ADAUSDT', not 'ADA/USDT'
        binance_symbol = par.replace('/', '').upper()
        return self._criar_ordem_mercado(binance_symbol, 'BUY', quantidade)

    def place_ordem_venda_market(self, par: str, quantidade: float) -> Dict[str, Any]:
        """
        Coloca uma ordem de venda a mercado.
        Implementa o método abstrato de ExchangeAPI.
        """
        # Binance API expects 'ADAUSDT', not 'ADA/USDT'
        binance_symbol = par.replace('/', '').upper()
        return self._criar_ordem_mercado(binance_symbol, 'SELL', quantidade)

    def get_info_conta(self) -> Dict[str, Any]:
        """
        Obtém informações gerais da conta, incluindo saldos.
        Implementa o método abstrato de ExchangeAPI.
        """
        try:
            resposta = self._fazer_requisicao(
                'GET',
                '/api/v3/account',
                assinado=True
            )
            return resposta
        except Exception as e:
            logger.erro_api('get_info_conta', str(e))
            raise

    def check_connection(self) -> bool:
        """
        Verifica a conectividade com a API da exchange.
        Implementa o método abstrato de ExchangeAPI.
        """
        try:
            self._fazer_requisicao('GET', '/api/v3/ping')
            return True
        except:
            return False

    def get_historico_ordens(self, par: str, limite: int = 500, order_id: Optional[int] = None) -> List[Dict]:
        """
        Obtém o histórico de ordens de um par específico.
        Implementa o método abstrato de ExchangeAPI.
        """
        try:
            binance_symbol = par.replace('/', '').upper()
            params = {
                'symbol': binance_symbol,
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
            logger.erro_api(f'get_historico_ordens/{par}', str(e))
            return []

    # --- Métodos Auxiliares (antigos métodos do APIManager, adaptados) ---

    def _get_all_balances(self) -> List[Dict]: # Renamed from obter_saldos
        """
        Obtém todos os saldos da conta.
        Usado internamente por get_saldo_disponivel.
        """
        try:
            resposta = self._fazer_requisicao(
                'GET',
                '/api/v3/account',
                assinado=True
            )

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
            logger.erro_api('_get_all_balances', str(e))
            raise # Re-raise to be handled by calling method

    def _criar_ordem_mercado( # Renamed from criar_ordem_mercado
        self,
        simbolo: str, # This is now the Binance format, e.g., 'ADAUSDT'
        lado: str,
        quantidade: float
    ) -> Optional[Dict]:
        """
        Cria ordem a mercado (auxiliar para place_ordem_compra/venda_market).
        """
        try:
            # Obter informações do símbolo para aplicar filtros corretos
            info_simbolo = self.obter_info_simbolo(simbolo)

            if info_simbolo:
                # Encontrar o filtro LOT_SIZE
                lot_size_filter = None
                for filtro in info_simbolo.get('filters', []):
                    if filtro['filterType'] == 'LOT_SIZE':
                        lot_size_filter = filtro
                        break

                if lot_size_filter:
                    step_size = float(lot_size_filter['stepSize'])

                    # Arredondar quantidade para o stepSize mais próximo
                    from decimal import Decimal, ROUND_DOWN
                    quantidade_decimal = Decimal(str(quantidade))
                    step_decimal = Decimal(str(step_size))

                    # Calcular número de casas decimais do step_size
                    step_str = f"{step_size:.8f}".rstrip('0')
                    if '.' in step_str:
                        decimais = len(step_str.split('.')[1])
                    else:
                        decimais = 0

                    # Arredondar para baixo para múltiplo do stepSize
                    quantidade_ajustada = (quantidade_decimal // step_decimal) * step_decimal
                    quantidade_formatada = f"{float(quantidade_ajustada):.{decimais}f}"

                    logger.debug(f"📏 Ajuste LOT_SIZE: {quantidade} → {quantidade_formatada} (step: {step_size})")
                else:
                    # Fallback se não encontrar LOT_SIZE
                    quantidade_formatada = f"{quantidade:.8f}".rstrip('0').rstrip('.')
            else:
                # Fallback: formatar com precisão padrão
                quantidade_formatada = f"{quantidade:.8f}".rstrip('0').rstrip('.')

            params = {
                'symbol': simbolo.upper(),
                'side': lado.upper(),
                'type': 'MARKET',
                'quantity': quantidade_formatada
            }

            logger.info(f"📤 Criando ordem: {lado} {quantidade_formatada} {simbolo}")

            resposta = self._fazer_requisicao(
                'POST',
                '/api/v3/order',
                assinado=True,
                params=params
            )

            logger.info(f"✅ Ordem executada: {resposta.get('orderId')}")
            return resposta

        except Exception as e:
            logger.erro_api(f'_criar_ordem_mercado/{simbolo}', str(e))
            raise # Re-raise to be handled by calling method

    def obter_info_simbolo(self, simbolo: str) -> Optional[Dict]:
        """
        Obtém informações do símbolo

        Args:
            simbolo: Par (ex: ADAUSDT)

        Returns:
            Informações do símbolo (filters, precision, etc)
        """
        try:
            binance_symbol = simbolo.replace('/', '').upper()
            resposta = self._fazer_requisicao(
                'GET',
                '/api/v3/exchangeInfo',
                params={'symbol': binance_symbol}
            )

            symbols = resposta.get('symbols', [])
            if symbols:
                return symbols[0]
            return None

        except Exception as e:
            logger.erro_api(f'obter_info_simbolo/{simbolo}', str(e))
            return None

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
            binance_symbol = simbolo.replace('/', '').upper()
            params = {
                'symbol': binance_symbol,
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

    def importar_historico_para_db(self, database_manager, par: str):
        """
        Sincroniza histórico de trades dos últimos 60 dias com o banco de dados local.
        
        Este método é chamado quando há uma divergência significativa entre o saldo
        da exchange e o saldo registrado no banco de dados local.
        
        IMPORTANTE: Este método NÃO apaga dados antigos. Ele apenas sincroniza
        os últimos 60 dias, mantendo ordens mais antigas intactas e evitando duplicações.
        
        Args:
            database_manager: Instância do DatabaseManager
            par: Par de trading (ex: 'ADA/USDT')
        """
        try:
            binance_symbol = par.replace('/', '').upper()
            logger.info(f"🔄 Iniciando sincronização de histórico da Binance para {binance_symbol}...")
            
            # Calcular timestamp de 60 dias atrás (em milissegundos)
            from datetime import datetime, timedelta
            inicio_timestamp = int((datetime.now() - timedelta(days=60)).timestamp() * 1000)
            inicio_data_str = datetime.fromtimestamp(inicio_timestamp / 1000).isoformat()
            
            # Buscar histórico de ordens dos últimos 60 dias
            logger.info(f"📥 Buscando ordens dos últimos 60 dias da exchange...")
            historico_ordens = self.get_historico_ordens(par=par, limite=1000)
            
            # Filtrar apenas ordens FILLED (executadas) dos últimos 60 dias
            ordens_recentes = [
                ordem for ordem in historico_ordens
                if ordem.get('status') == 'FILLED' and ordem.get('time', 0) >= inicio_timestamp
            ]
            
            logger.info(f"📋 Encontradas {len(ordens_recentes)} ordens executadas nos últimos 60 dias na exchange")
            
            if not ordens_recentes:
                logger.warning("⚠️ Nenhuma ordem encontrada no histórico da exchange")
                return
            
            # SINCRONIZAÇÃO INTELIGENTE:
            # 1. SALVAR estratégias das ordens recentes ANTES de apagar
            # 2. Apagar APENAS ordens dos últimos 60 dias do banco local
            # 3. Manter ordens mais antigas intactas
            logger.info(f"🗑️ Preparando sincronização dos últimos 60 dias (>= {inicio_data_str[:10]})...")
            logger.info("📌 Ordens mais antigas e estratégias serão preservadas")

            # Dicionário para salvar estratégias: order_id -> estrategia
            estrategias_salvas = {}

            with database_manager._conectar() as conn:
                cursor = conn.cursor()

                # SALVAR estratégias das ordens que serão removidas
                cursor.execute("""
                    SELECT order_id, estrategia FROM ordens
                    WHERE timestamp >= ? AND order_id IS NOT NULL AND estrategia IS NOT NULL
                """, (inicio_data_str,))

                for row in cursor.fetchall():
                    order_id, estrategia = row
                    estrategias_salvas[order_id] = estrategia

                logger.info(f"💾 Salvando estratégias de {len(estrategias_salvas)} ordens")

                # Contar ordens que serão removidas
                cursor.execute("""
                    SELECT COUNT(*) FROM ordens
                    WHERE timestamp >= ?
                """, (inicio_data_str,))
                total_remover = cursor.fetchone()[0]

                # Contar ordens antigas que serão mantidas
                cursor.execute("""
                    SELECT COUNT(*) FROM ordens
                    WHERE timestamp < ?
                """, (inicio_data_str,))
                total_manter = cursor.fetchone()[0]

                logger.info(f"   • Ordens a remover (últimos 60 dias): {total_remover}")
                logger.info(f"   • Ordens a preservar (> 60 dias): {total_manter}")

                # Apagar apenas ordens dos últimos 60 dias
                cursor.execute("""
                    DELETE FROM ordens
                    WHERE timestamp >= ?
                """, (inicio_data_str,))

                logger.info("✅ Ordens recentes removidas, histórico antigo preservado")
            
            # Importar ordens do histórico da exchange (últimos 60 dias)
            logger.info(f"📥 Importando {len(ordens_recentes)} ordens da exchange...")
            resultado = database_manager.importar_ordens_binance(
                ordens_binance=ordens_recentes,
                recalcular_preco_medio=True
            )

            # RESTAURAR estratégias salvas
            if estrategias_salvas:
                logger.info(f"🔄 Restaurando estratégias de {len(estrategias_salvas)} ordens...")
                restauradas = 0

                with database_manager._conectar() as conn:
                    cursor = conn.cursor()

                    for order_id, estrategia in estrategias_salvas.items():
                        try:
                            cursor.execute("""
                                UPDATE ordens
                                SET estrategia = ?
                                WHERE order_id = ? AND estrategia IS NULL
                            """, (estrategia, str(order_id)))

                            if cursor.rowcount > 0:
                                restauradas += 1

                        except Exception as e:
                            logger.warning(f"⚠️ Erro ao restaurar estratégia para ordem {order_id}: {e}")

                    conn.commit()

                logger.info(f"✅ Estratégias restauradas: {restauradas}/{len(estrategias_salvas)}")

            logger.info(f"✅ Sincronização concluída:")
            logger.info(f"   • Importadas: {resultado['importadas']}")
            logger.info(f"   • Duplicadas: {resultado['duplicadas']}")
            logger.info(f"   • Erros: {resultado['erros']}")
            logger.info(f"   • Histórico antigo preservado: {total_manter} ordens")
            logger.info(f"   • Estratégias preservadas: {len(estrategias_salvas)} ordens")

            if resultado['erros'] > 0:
                logger.warning(f"⚠️ {resultado['erros']} ordens não puderam ser importadas")
            
        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar histórico da Binance: {e}")
            import traceback
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise
