#!/usr/bin/env python3
"""
Position Manager - Gerenciamento de Posições de Trading
"""

from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.persistencia.database import DatabaseManager
from src.utils.logger import get_loggers

logger, _ = get_loggers()


class PositionManager:
    """
    Gerencia posições de trading, calculando quantidade total e preço médio
    ponderado baseado no histórico de ordens do banco de dados.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Inicializa o Position Manager
        
        Args:
            db_manager: Instância do DatabaseManager
        """
        self.db = db_manager
        
        # Estado interno da posição
        self._quantidade_total: Decimal = Decimal('0')
        self._preco_medio: Optional[Decimal] = None
        self._valor_total_investido: Decimal = Decimal('0')
        self._posicao_carregada: bool = False
        
        # Carregar posição inicial do banco de dados
        self.carregar_posicao()
    
    def carregar_posicao(self) -> Dict[str, Any]:
        """
        Lê todas as ordens do banco de dados para calcular e armazenar
        internamente a quantidade total do ativo e o preço médio ponderado.
        
        Returns:
            dict: Dados da posição carregada
        """
        try:
            logger.info("📊 Carregando posição do banco de dados...")
            
            # Buscar todas as ordens do banco de dados
            ordens = self._buscar_ordens_completas()
            
            if not ordens:
                logger.info("📊 Nenhuma ordem encontrada - posição zerada")
                self._resetar_posicao()
                return self._obter_resumo_posicao()
            
            # Calcular posição baseada nas ordens
            self._calcular_posicao_das_ordens(ordens)
            
            self._posicao_carregada = True
            
            resumo = self._obter_resumo_posicao()
            
            if self._quantidade_total > 0:
                logger.info(f"✅ Posição carregada:")
                logger.info(f"   Quantidade total: {self._quantidade_total:.4f}")
                logger.info(f"   Preço médio: ${self._preco_medio:.6f}")
                logger.info(f"   Valor investido: ${self._valor_total_investido:.2f}")
            else:
                logger.info("📊 Posição zerada (todas as moedas vendidas)")
            
            return resumo
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar posição: {e}")
            self._resetar_posicao()
            return self._obter_resumo_posicao()
    
    def _buscar_ordens_completas(self) -> List[Dict[str, Any]]:
        """
        Busca todas as ordens do banco de dados ordenadas por data
        
        Returns:
            Lista de ordens
        """
        try:
            # Buscar ordens usando context manager do DatabaseManager
            with self.db._conectar() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        id, tipo, par, quantidade, preco, valor_total,
                        taxa, meta, lucro_percentual, lucro_usdt,
                        preco_medio_antes, preco_medio_depois,
                        saldo_ada_antes, saldo_ada_depois,
                        saldo_usdt_antes, saldo_usdt_depois,
                        order_id, observacao, timestamp
                    FROM ordens 
                    ORDER BY timestamp ASC
                """)
                
                colunas = [desc[0] for desc in cursor.description]
                ordens = []
                
                for linha in cursor.fetchall():
                    ordem = dict(zip(colunas, linha))
                    # Converter strings para Decimal nos campos numéricos
                    campos_numericos = ['quantidade', 'preco', 'valor_total', 'taxa', 
                                      'lucro_percentual', 'lucro_usdt', 'preco_medio_antes', 
                                      'preco_medio_depois', 'saldo_ada_antes', 'saldo_ada_depois',
                                      'saldo_usdt_antes', 'saldo_usdt_depois']
                    
                    for campo in campos_numericos:
                        if ordem.get(campo) is not None:
                            ordem[campo] = Decimal(str(ordem[campo]))
                    
                    ordens.append(ordem)
                
                logger.debug(f"📋 Encontradas {len(ordens)} ordens no banco de dados")
                return ordens
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar ordens: {e}")
            return []
    
    def _calcular_posicao_das_ordens(self, ordens: List[Dict[str, Any]]):
        """
        Calcula posição atual baseada na lista de ordens
        
        Args:
            ordens: Lista de ordens do banco de dados
        """
        quantidade_total = Decimal('0')
        valor_total_investido = Decimal('0')
        
        for ordem in ordens:
            tipo = ordem['tipo'].upper()
            quantidade = ordem['quantidade']
            preco = ordem['preco']
            valor_ordem = quantidade * preco
            
            if tipo == 'COMPRA':
                # Compra: aumenta quantidade e valor investido
                quantidade_total += quantidade
                valor_total_investido += valor_ordem
                
                logger.debug(f"🔵 COMPRA: +{quantidade:.4f} @ ${preco:.6f}")
                
            elif tipo == 'VENDA':
                # Venda: diminui quantidade proporcionalmente
                if quantidade_total > 0:
                    # Calcular proporção vendida
                    proporcao_vendida = min(quantidade / quantidade_total, Decimal('1'))
                    
                    # Reduzir quantidade e valor investido proporcionalmente
                    quantidade_total -= quantidade
                    valor_total_investido *= (Decimal('1') - proporcao_vendida)
                    
                    # Garantir que não ficou negativo por arredondamentos
                    if quantidade_total < Decimal('0.0001'):
                        quantidade_total = Decimal('0')
                        valor_total_investido = Decimal('0')
                    
                    logger.debug(f"🔴 VENDA: -{quantidade:.4f} @ ${preco:.6f}")
        
        # Atualizar estado interno
        self._quantidade_total = quantidade_total
        self._valor_total_investido = valor_total_investido
        
        # Calcular preço médio
        if quantidade_total > 0 and valor_total_investido > 0:
            self._preco_medio = valor_total_investido / quantidade_total
        else:
            self._preco_medio = None
    
    def get_quantidade_total(self) -> Decimal:
        """
        Retorna a quantidade total atual do ativo
        
        Returns:
            Decimal: Quantidade total
        """
        if not self._posicao_carregada:
            self.carregar_posicao()
        
        return self._quantidade_total
    
    def get_preco_medio(self) -> Optional[Decimal]:
        """
        Retorna o preço médio ponderado atual
        
        Returns:
            Decimal: Preço médio ou None se não houver posição
        """
        if not self._posicao_carregada:
            self.carregar_posicao()
        
        return self._preco_medio
    
    def get_valor_total_investido(self) -> Decimal:
        """
        Retorna o valor total investido atual
        
        Returns:
            Decimal: Valor total investido
        """
        if not self._posicao_carregada:
            self.carregar_posicao()
        
        return self._valor_total_investido
    
    def atualizar_apos_compra(self, quantidade: Decimal, preco: Decimal):
        """
        Atualiza o estado interno após uma compra sem precisar reler todo o banco
        
        Args:
            quantidade: Quantidade comprada
            preco: Preço da compra
        """
        valor_compra = quantidade * preco
        
        # Atualizar valores totais
        self._valor_total_investido += valor_compra
        self._quantidade_total += quantidade
        
        # Recalcular preço médio
        if self._quantidade_total > 0:
            self._preco_medio = self._valor_total_investido / self._quantidade_total
        else:
            self._preco_medio = None
        
        logger.debug(f"📈 Posição atualizada após COMPRA:")
        logger.debug(f"   +{quantidade:.4f} @ ${preco:.6f}")
        logger.debug(f"   Total: {self._quantidade_total:.4f}")
        logger.debug(f"   Preço médio: ${self._preco_medio:.6f}" if self._preco_medio else "   Preço médio: N/A")
    
    def atualizar_apos_venda(self, quantidade: Decimal):
        """
        Atualiza o estado interno após uma venda sem precisar reler todo o banco
        
        Args:
            quantidade: Quantidade vendida
        """
        if self._quantidade_total <= 0:
            logger.warning("⚠️ Tentativa de venda sem posição")
            return
        
        # Calcular proporção vendida
        proporcao_vendida = min(quantidade / self._quantidade_total, Decimal('1'))
        
        # Reduzir quantidade e valor investido proporcionalmente
        self._quantidade_total -= quantidade
        self._valor_total_investido *= (Decimal('1') - proporcao_vendida)
        
        # Garantir que não ficou negativo por arredondamentos
        if self._quantidade_total < Decimal('0.0001'):
            self._quantidade_total = Decimal('0')
            self._valor_total_investido = Decimal('0')
            self._preco_medio = None
        elif self._quantidade_total > 0:
            self._preco_medio = self._valor_total_investido / self._quantidade_total
        
        logger.debug(f"📉 Posição atualizada após VENDA:")
        logger.debug(f"   -{quantidade:.4f}")
        logger.debug(f"   Total: {self._quantidade_total:.4f}")
        logger.debug(f"   Preço médio: ${self._preco_medio:.6f}" if self._preco_medio else "   Preço médio: N/A")
    
    def calcular_lucro_atual(self, preco_atual: Decimal) -> Optional[Decimal]:
        """
        Calcula o lucro percentual atual baseado no preço médio
        
        Args:
            preco_atual: Preço atual do ativo
            
        Returns:
            Decimal: Lucro em % ou None se não houver posição
        """
        if not self._preco_medio or self._preco_medio <= 0 or self._quantidade_total <= 0:
            return None
        
        lucro_pct = ((preco_atual - self._preco_medio) / self._preco_medio) * Decimal('100')
        return lucro_pct
    
    def tem_posicao(self) -> bool:
        """
        Verifica se há posição ativa (quantidade > 0)
        
        Returns:
            bool: True se há posição ativa
        """
        return self._quantidade_total > 0
    
    def _resetar_posicao(self):
        """Reseta o estado interno da posição"""
        self._quantidade_total = Decimal('0')
        self._preco_medio = None
        self._valor_total_investido = Decimal('0')
        self._posicao_carregada = True
    
    def _obter_resumo_posicao(self) -> Dict[str, Any]:
        """
        Obtém resumo da posição atual
        
        Returns:
            dict: Resumo da posição
        """
        return {
            'quantidade_total': self._quantidade_total,
            'preco_medio': self._preco_medio,
            'valor_total_investido': self._valor_total_investido,
            'tem_posicao': self.tem_posicao(),
            'posicao_carregada': self._posicao_carregada
        }
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas completas da posição
        
        Returns:
            dict: Estatísticas da posição
        """
        stats = self._obter_resumo_posicao()
        
        # Adicionar estatísticas extras
        try:
            with self.db._conectar() as conn:
                cursor = conn.cursor()
                
                # Contar ordens
                cursor.execute("SELECT COUNT(*) as total, tipo FROM ordens GROUP BY tipo")
                contadores = {row[1]: row[0] for row in cursor.fetchall()}
                
                # Primeira e última ordem
                cursor.execute("""
                    SELECT MIN(timestamp) as primeira, MAX(timestamp) as ultima 
                    FROM ordens
                """)
                result = cursor.fetchone()
                
                stats.update({
                    'total_compras': contadores.get('COMPRA', 0),
                    'total_vendas': contadores.get('VENDA', 0),
                    'primeira_ordem': result[0] if result else None,
                    'ultima_ordem': result[1] if result else None
                })
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao obter estatísticas extras: {e}")
        
        return stats