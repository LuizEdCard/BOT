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
                    "asset": account['currency'],
                    "free": float(account['available']),
                    "locked": float(account['holds'])
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

    def obter_klines(
        self,
        simbolo: str,
        intervalo: str,
        limite: int = 500,
        inicio: Optional[int] = None,
        fim: Optional[int] = None
    ) -> List[List]:
        """
        Obtém histórico de candlesticks (klines) da KuCoin.
        """
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

            # KuCoin timestamps are in seconds
            start_at = int(inicio / 1000) if inicio else None
            end_at = int(fim / 1000) if fim else None

            klines_raw = self.market_client.get_kline(
                symbol=kucoin_par,
                kline_type=kline_type
            )

            # Convert to Binance format: [ts, open, high, low, close, volume, ...]
            klines_formatados = []
            for kline in klines_raw:
                # KuCoin: [ts, open, close, high, low, amount, volume]
                # Binance: [ts, open, high, low, close, volume, ...]
                klines_formatados.append([
                    int(kline[0]) * 1000,  # Convert to ms
                    kline[1],  # open
                    kline[3],  # high
                    kline[4],  # low
                    kline[2],  # close
                    kline[6],  # volume
                    (int(kline[0]) * 1000) + self._intervalo_para_ms(intervalo) - 1
                ])
            
            return klines_formatados[::-1][:limite]

        except Exception as e:
            logger.error(f"Erro ao obter klines para {simbolo} na KuCoin: {e}")
            return []

    def _intervalo_para_ms(self, intervalo: str) -> int:
        multiplicadores = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800}
        unidade = intervalo[-1]
        valor = int(intervalo[:-1])
        return valor * multiplicadores.get(unidade, 0) * 1000

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
            kucoin_par = self._format_pair(par)
            logger.info(f"🔄 Iniciando sincronização de histórico da KuCoin para {kucoin_par}...")
            
            # Calcular timestamp de 60 dias atrás (em segundos para KuCoin)
            from datetime import datetime, timedelta
            inicio_timestamp = int((datetime.now() - timedelta(days=60)).timestamp())
            inicio_data_str = datetime.fromtimestamp(inicio_timestamp).isoformat()
            fim_timestamp = int(datetime.now().timestamp())
            
            # Buscar histórico de ordens dos últimos 60 dias
            logger.info(f"📥 Buscando ordens dos últimos 60 dias da exchange...")
            
            # KuCoin usa get_order_list para histórico de ordens
            try:
                historico_ordens = self.trade_client.get_order_list(
                    symbol=kucoin_par,
                    status='done',  # Ordens completas
                    start=inicio_timestamp * 1000,  # Converter para ms
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
            
            # SINCRONIZAÇÃO INTELIGENTE:
            # 1. Apagar APENAS ordens dos últimos 60 dias do banco local
            # 2. Manter ordens mais antigas intactas
            logger.info(f"🗑️ Removendo ordens dos últimos 60 dias do banco local (>= {inicio_data_str[:10]})...")
            logger.info("📌 Ordens mais antigas serão preservadas")
            
            with database_manager._conectar() as conn:
                cursor = conn.cursor()
                
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
            
            # Converter ordens da KuCoin para formato compatível com o banco de dados
            logger.info(f"📥 Importando {len(ordens_list)} ordens da exchange...")
            
            importadas = 0
            duplicadas = 0
            erros = 0
            
            # Usar uma única conexão para todas as inserções
            with database_manager._conectar() as conn:
                cursor = conn.cursor()
                
                for ordem in ordens_list:
                    try:
                        order_id = str(ordem.get('id'))
                        
                        # Verificar se já existe (dentro da mesma transação)
                        cursor.execute("SELECT COUNT(*) FROM ordens WHERE order_id = ?", (order_id,))
                        if cursor.fetchone()[0] > 0:
                            duplicadas += 1
                            continue
                        
                        # Converter dados da KuCoin para o formato do banco
                        timestamp_ms = int(ordem.get('createdAt', 0))
                        timestamp = datetime.fromtimestamp(timestamp_ms / 1000).isoformat()
                        tipo = 'COMPRA' if ordem.get('side', '').lower() == 'buy' else 'VENDA'
                        quantidade = float(ordem.get('dealSize', 0))
                        valor_total = float(ordem.get('dealFunds', 0))
                        preco = valor_total / quantidade if quantidade > 0 else 0
                        taxa = float(ordem.get('fee', 0))
                        
                        # Inserir no banco
                        cursor.execute("""
                            INSERT INTO ordens (
                                timestamp, tipo, par, quantidade, preco, valor_total, taxa,
                                order_id, observacao
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            timestamp,
                            tipo,
                            par,
                            quantidade,
                            preco,
                            valor_total,
                            taxa,
                            order_id,
                            f"Importado do histórico da KuCoin - Status: {ordem.get('status')}"
                        ))
                        
                        importadas += 1
                        
                    except Exception as e:
                        logger.error(f"❌ Erro ao importar ordem {ordem.get('id')}: {e}")
                        erros += 1
            
            # Recalcular preço médio DEPOIS de fechar a conexão
            if importadas > 0:
                try:
                    with database_manager._conectar() as conn:
                        cursor = conn.cursor()
                        
                        # Buscar todas as compras
                        cursor.execute("""
                            SELECT quantidade, preco FROM ordens
                            WHERE tipo = 'COMPRA'
                            ORDER BY timestamp ASC
                        """)
                        compras = cursor.fetchall()
                        
                        # Buscar todas as vendas
                        cursor.execute("""
                            SELECT quantidade FROM ordens
                            WHERE tipo = 'VENDA'
                            ORDER BY timestamp ASC
                        """)
                        vendas = cursor.fetchall()
                        
                        # Calcular total comprado
                        total_comprado = sum(float(c[0]) for c in compras)
                        valor_total_calc = sum(float(c[0]) * float(c[1]) for c in compras)
                        
                        # Subtrair total vendido
                        total_vendido = sum(float(v[0]) for v in vendas)
                        quantidade_atual = total_comprado - total_vendido
                        
                        # Calcular preço médio
                        if total_comprado > 0:
                            preco_medio = valor_total_calc / total_comprado
                        else:
                            preco_medio = None
                        
                        # Atualizar estado do bot
                        cursor.execute("""
                            INSERT OR REPLACE INTO estado_bot (
                                id, timestamp_atualizacao, preco_medio_compra, quantidade_total_ada
                            ) VALUES (1, ?, ?, ?)
                        """, (
                            datetime.now().isoformat(),
                            preco_medio,
                            quantidade_atual
                        ))
                        
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
            
        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar histórico da KuCoin: {e}")
            import traceback
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise
