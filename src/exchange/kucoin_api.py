import time
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from decimal import Decimal 
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
        return par.replace('/', '-')

    def get_preco_atual(self, par: str) -> float:
        max_retries = 3
        last_exception = None
        for tentativa in range(max_retries):
            try:
                kucoin_par = self._format_pair(par)
                ticker = self.market_client.get_ticker(symbol=kucoin_par)
                if ticker and 'price' in ticker:
                    return float(ticker['price'])
                raise ValueError(f"Preço não encontrado para {kucoin_par}")
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"⚠️ Falha na API da KuCoin (tentativa {tentativa + 1}/{max_retries}): {e}")
                last_exception = e
                if tentativa < max_retries - 1:
                    time.sleep(3)
            except Exception as e:
                logger.error(f"Erro ao obter preço atual para {par} na KuCoin: {e}")
                raise
        logger.error("❌ Falha na API da KuCoin após todas as tentativas. Desistindo.")
        raise last_exception

    def get_saldo_disponivel(self, moeda: str) -> float:
        max_retries = 3
        last_exception = None
        for tentativa in range(max_retries):
            try:
                accounts = self.user_client.get_account_list()
                for account in accounts:
                    if account['currency'].upper() == moeda.upper():
                        return float(account['available'])
                return 0.0
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"⚠️ Falha na API da KuCoin (tentativa {tentativa + 1}/{max_retries}): {e}")
                last_exception = e
                if tentativa < max_retries - 1:
                    time.sleep(3)
            except Exception as e:
                logger.error(f"Erro ao obter saldo disponível para {moeda} na KuCoin: {e}")
                raise
        logger.error("❌ Falha na API da KuCoin após todas as tentativas. Desistindo.")
        raise last_exception

    def place_ordem_compra_market(self, par: str, quantidade: float) -> Dict[str, Any]:
        max_retries = 3
        last_exception = None
        for tentativa in range(max_retries):
            try:
                kucoin_par = self._format_pair(par)
                order = self.trade_client.create_market_order(
                    symbol=kucoin_par,
                    side='buy',
                    size=str(quantidade)
                )
                return order
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"⚠️ Falha na API da KuCoin (tentativa {tentativa + 1}/{max_retries}): {e}")
                last_exception = e
                if tentativa < max_retries - 1:
                    time.sleep(3)
            except Exception as e:
                logger.error(f"Erro ao colocar ordem de compra a mercado para {par} ({quantidade}) na KuCoin: {e}")
                raise
        logger.error("❌ Falha na API da KuCoin após todas as tentativas. Desistindo.")
        raise last_exception

    def place_ordem_venda_market(self, par: str, quantidade: float) -> Dict[str, Any]:
        max_retries = 3
        last_exception = None
        for tentativa in range(max_retries):
            try:
                kucoin_par = self._format_pair(par)
                order = self.trade_client.create_market_order(
                    symbol=kucoin_par,
                    side='sell',
                    size=str(quantidade)
                )
                return order
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"⚠️ Falha na API da KuCoin (tentativa {tentativa + 1}/{max_retries}): {e}")
                last_exception = e
                if tentativa < max_retries - 1:
                    time.sleep(3)
            except Exception as e:
                logger.error(f"Erro ao colocar ordem de venda a mercado para {par} ({quantidade}) na KuCoin: {e}")
                raise
        logger.error("❌ Falha na API da KuCoin após todas as tentativas. Desistindo.")
        raise last_exception

    def get_info_conta(self) -> Dict[str, Any]:
        max_retries = 3
        last_exception = None
        for tentativa in range(max_retries):
            try:
                accounts = self.user_client.get_account_list()
                summary = {"balances": []}
                for account in accounts:
                    summary["balances"].append({
                        "asset": account['currency'],
                        "free": float(account['available']),
                        "locked": float(account['holds'])
                    })
                return summary
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"⚠️ Falha na API da KuCoin (tentativa {tentativa + 1}/{max_retries}): {e}")
                last_exception = e
                if tentativa < max_retries - 1:
                    time.sleep(3)
            except Exception as e:
                logger.error(f"Erro ao obter informações da conta na KuCoin: {e}")
                raise
        logger.error("❌ Falha na API da KuCoin após todas as tentativas. Desistindo.")
        raise last_exception

    def check_connection(self) -> bool:
        max_retries = 3
        last_exception = None
        for tentativa in range(max_retries):
            try:
                self.user_client.get_account_list()
                return True
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"⚠️ Falha na API da KuCoin (tentativa {tentativa + 1}/{max_retries}): {e}")
                last_exception = e
                if tentativa < max_retries - 1:
                    time.sleep(3)
            except Exception as e:
                logger.error(f"Falha na verificação de conexão com a KuCoin: {e}")
                return False
        logger.error("❌ Falha na API da KuCoin após todas as tentativas. Desistindo.")
        return False

    def get_historico_ordens(self, par: str, limite: int = 500, order_id: Optional[int] = None) -> List[Dict]:
        logger.warning(f"AVISO: A função get_historico_ordens para o par {par} ainda não foi totalmente implementada para a KuCoin.")
        return []

    def obter_klines(
        self,
        simbolo: str,
        intervalo: str,
        limite: int = 500,
        inicio: Optional[int] = None,
        fim: Optional[int] = None
    ) -> List[List]:
        max_retries = 3
        last_exception = None
        for tentativa in range(max_retries):
            try:
                kucoin_par = self._format_pair(simbolo)
                intervalo_map = {
                    '1m': '1min', '3m': '3min', '5m': '5min', '15m': '15min', '30m': '30min',
                    '1h': '1hour', '2h': '2hour', '4h': '4hour', '6h': '6hour', 
                    '8h': '8hour', '12h': '12hour', '1d': '1day', '1w': '1week'
                }
                kline_type = intervalo_map.get(intervalo)
                if not kline_type:
                    raise ValueError(f"Intervalo '{intervalo}' não suportado pela KuCoin API.")

                start_at = int(inicio / 1000) if inicio else None
                end_at = int(fim / 1000) if fim else None

                klines_raw = self.market_client.get_kline(
                    symbol=kucoin_par,
                    kline_type=kline_type
                )

                klines_formatados = []
                for kline in klines_raw:
                    klines_formatados.append([
                        int(kline[0]) * 1000,
                        kline[1],
                        kline[3],
                        kline[4],
                        kline[2],
                        kline[6],
                        (int(kline[0]) * 1000) + self._intervalo_para_ms(intervalo) - 1
                    ])
                
                return klines_formatados[::-1][:limite]
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"⚠️ Falha na API da KuCoin (tentativa {tentativa + 1}/{max_retries}): {e}")
                last_exception = e
                if tentativa < max_retries - 1:
                    time.sleep(3)
            except Exception as e:
                logger.error(f"Erro ao obter klines para {simbolo} na KuCoin: {e}")
                return []
        logger.error("❌ Falha na API da KuCoin após todas as tentativas. Desistindo.")
        if last_exception:
            raise last_exception
        return []

    def _intervalo_para_ms(self, intervalo: str) -> int:
        multiplicadores = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800}
        unidade = intervalo[-1]
        valor = int(intervalo[:-1])
        return valor * multiplicadores.get(unidade, 0) * 1000

    def importar_historico_para_db(self, database_manager, par: str):
        max_retries = 3
        last_exception = None
        for tentativa in range(max_retries):
            try:
                kucoin_par = self._format_pair(par)
                logger.info(f"🔄 Iniciando sincronização de histórico da KuCoin para {kucoin_par}...")
                
                from datetime import datetime, timedelta
                inicio_timestamp = int((datetime.now() - timedelta(days=60)).timestamp())
                inicio_data_str = datetime.fromtimestamp(inicio_timestamp).isoformat()
                fim_timestamp = int(datetime.now().timestamp())
                
                logger.info(f"📥 Buscando ordens dos últimos 60 dias da exchange...")
                
                try:
                    historico_ordens = self.trade_client.get_order_list(
                        symbol=kucoin_par,
                        status='done',
                        start=inicio_timestamp * 1000,
                        end=fim_timestamp * 1000
                    )
                    ordens_list = historico_ordens.get('items', [])
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao buscar histórico da KuCoin: {e}")
                    logger.warning("⚠️ A função get_historico_ordens ainda não está totalmente implementada para KuCoin")
                    return
                
                logger.info(f"📋 Encontradas {len(ordens_list)} ordens executadas nos últimos 60 dias na exchange")
                
                if not ordens_list:
                    logger.warning("⚠️ Nenhuma ordem encontrada no histórico da exchange")
                    return
                
                logger.info(f"🗑️ Removendo ordens dos últimos 60 dias do banco local (>= {inicio_data_str[:10]})...")
                logger.info("📌 Ordens mais antigas serão preservadas")
                
                with database_manager._conectar() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM ordens WHERE timestamp >= ?", (inicio_data_str,))
                    total_remover = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM ordens WHERE timestamp < ?", (inicio_data_str,))
                    total_manter = cursor.fetchone()[0]
                    logger.info(f"   • Ordens a remover (últimos 60 dias): {total_remover}")
                    logger.info(f"   • Ordens a preservar (> 60 dias): {total_manter}")
                    cursor.execute("DELETE FROM ordens WHERE timestamp >= ?", (inicio_data_str,))
                    logger.info("✅ Ordens recentes removidas, histórico antigo preservado")
                
                logger.info(f"📥 Importando {len(ordens_list)} ordens da exchange...")
                importadas = 0
                duplicadas = 0
                erros = 0
                
                with database_manager._conectar() as conn:
                    cursor = conn.cursor()
                    for ordem in ordens_list:
                        try:
                            order_id = str(ordem.get('id'))
                            cursor.execute("SELECT COUNT(*) FROM ordens WHERE order_id = ?", (order_id,))
                            if cursor.fetchone()[0] > 0:
                                duplicadas += 1
                                continue
                            
                            timestamp_ms = int(ordem.get('createdAt', 0))
                            timestamp = datetime.fromtimestamp(timestamp_ms / 1000).isoformat()
                            tipo = 'COMPRA' if ordem.get('side', '').lower() == 'buy' else 'VENDA'
                            quantidade = float(ordem.get('dealSize', 0))
                            valor_total = float(ordem.get('dealFunds', 0))
                            preco = valor_total / quantidade if quantidade > 0 else 0
                            taxa = float(ordem.get('fee', 0))
                            
                            cursor.execute("""
                                INSERT INTO ordens (
                                    timestamp, tipo, par, quantidade, preco, valor_total, taxa,
                                    order_id, observacao
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                timestamp, tipo, par, quantidade, preco, valor_total, taxa,
                                order_id, f"Importado do histórico da KuCoin - Status: {ordem.get('status')}"
                            ))
                            importadas += 1
                        except Exception as e:
                            logger.error(f"❌ Erro ao importar ordem {ordem.get('id')}: {e}")
                            erros += 1
                
                if importadas > 0:
                    try:
                        with database_manager._conectar() as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT quantidade, preco FROM ordens WHERE tipo = 'COMPRA' ORDER BY timestamp ASC")
                            compras = cursor.fetchall()
                            cursor.execute("SELECT quantidade FROM ordens WHERE tipo = 'VENDA' ORDER BY timestamp ASC")
                            vendas = cursor.fetchall()
                            total_comprado = sum(float(c[0]) for c in compras)
                            valor_total_calc = sum(float(c[0]) * float(c[1]) for c in compras)
                            total_vendido = sum(float(v[0]) for v in vendas)
                            quantidade_atual = total_comprado - total_vendido
                            if total_comprado > 0:
                                preco_medio = valor_total_calc / total_comprado
                            else:
                                preco_medio = None
                            cursor.execute("""
                                INSERT OR REPLACE INTO estado_bot (
                                    id, timestamp_atualizacao, preco_medio_compra, quantidade_total_ada
                                ) VALUES (1, ?, ?, ?)
                            """, (datetime.now().isoformat(), preco_medio, quantidade_atual))
                            if preco_medio:
                                logger.info(f"📊 Preço médio recalculado: ${preco_medio:.6f} ({quantidade_atual:.1f})")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao recalcular preço médio: {e}")
                
                logger.info(f"✅ Sincronização concluída:")
                logger.info(f"   • Importadas: {importadas}")
                logger.info(f"   • Duplicadas: {duplicadas}")
                logger.info(f"   • Erros: {erros}")
                logger.info(f"   • Histórico antigo preservado: {total_manter} ordens")
                
                if erros > 0:
                    logger.warning(f"⚠️ {erros} ordens não puderam ser importadas")
                
                return # Success, exit loop
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"⚠️ Falha na API da KuCoin (tentativa {tentativa + 1}/{max_retries}): {e}")
                last_exception = e
                if tentativa < max_retries - 1:
                    time.sleep(3)
            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar histórico da KuCoin: {e}")
                import traceback
                logger.error(f"Traceback:\n{traceback.format_exc()}")
                raise
        
        logger.error("❌ Falha na API da KuCoin após todas as tentativas. Desistindo.")
        if last_exception:
            raise last_exception

