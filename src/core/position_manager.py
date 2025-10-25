#!/usr/bin/env python3
"""
Position Manager - Gerenciamento de Posições de Trading
"""

from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from src.persistencia.database import DatabaseManager
from src.utils.logger import get_loggers

logger, _ = get_loggers()


class PositionManager:
    """
    Gerencia posições de trading com suporte a múltiplas carteiras lógicas.
    Calcula quantidade total e preço médio ponderado baseado no histórico
    de ordens do banco de dados.

    Carteiras suportadas:
    - 'acumulacao': Posição principal de longo prazo (DCA)
    - 'giro_rapido': Posição de swing trade (operações rápidas)
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Inicializa o Position Manager

        Args:
            db_manager: Instância do DatabaseManager
        """
        self.db = db_manager

        # Estado interno por carteira
        self.carteiras = {
            'acumulacao': {
                'quantidade_total': Decimal('0'),
                'preco_medio': None,
                'valor_total_investido': Decimal('0'),
                'posicao_carregada': False
            },
            'giro_rapido': {
                'quantidade_total': Decimal('0'),
                'preco_medio': None,
                'valor_total_investido': Decimal('0'),
                'posicao_carregada': False,
                'high_water_mark_lucro': Decimal('0')  # Para proteção de lucro
            }
        }

        # Carregar posição inicial do banco de dados
        # IMPORTANTE: Carregar histórico APENAS para 'acumulacao'
        # A carteira 'giro_rapido' sempre inicia zerada
        self.carregar_posicao_inicial()

    def carregar_posicao_inicial(self):
        """
        Carrega a posição inicial do banco de dados.

        ISOLAMENTO DAS CARTEIRAS (REFATORADO):
        - Carteira 'acumulacao': Carrega ordens com estrategia='acumulacao'
        - Carteira 'giro_rapido': Carrega ordens com estrategia='giro_rapido'
        - Ordens antigas (sem estrategia): Atribuídas à 'acumulacao'

        Esta separação garante que:
        1. Cada estratégia carrega APENAS suas ordens do banco
        2. Isolamento total baseado na coluna 'estrategia'
        3. Compatibilidade com ordens antigas
        """
        try:
            logger.info("📊 Inicializando carteiras do Position Manager...")

            # Buscar todas as ordens históricas do banco de dados
            ordens = self._buscar_ordens_completas()

            if not ordens:
                logger.info("📊 Nenhuma ordem histórica encontrada")
                # Marcar ambas carteiras como carregadas (zeradas)
                self._resetar_posicao('acumulacao')
                self._resetar_posicao('giro_rapido')
                return

            # ═══════════════════════════════════════════════════════════
            # CARTEIRA ACUMULAÇÃO: Carregar ordens com estrategia='acumulacao'
            # ═══════════════════════════════════════════════════════════
            logger.info("📊 Carregando histórico para carteira 'acumulacao'...")
            self._calcular_posicao_das_ordens(ordens, 'acumulacao')
            self.carteiras['acumulacao']['posicao_carregada'] = True

            quantidade_acum = self.carteiras['acumulacao']['quantidade_total']
            if quantidade_acum > 0:
                logger.info(f"✅ Posição ACUMULAÇÃO carregada:")
                logger.info(f"   Quantidade: {quantidade_acum:.4f}")
                logger.info(f"   Preço médio: ${self.carteiras['acumulacao']['preco_medio']:.6f}")
                logger.info(f"   Valor investido: ${self.carteiras['acumulacao']['valor_total_investido']:.2f}")
            else:
                logger.info(f"📊 Posição ACUMULAÇÃO zerada")

            # ═══════════════════════════════════════════════════════════
            # CARTEIRA GIRO RÁPIDO: Carregar ordens com estrategia='giro_rapido'
            # ═══════════════════════════════════════════════════════════
            logger.info("🎯 Carregando histórico para carteira 'giro_rapido'...")
            self._calcular_posicao_das_ordens(ordens, 'giro_rapido')
            self.carteiras['giro_rapido']['posicao_carregada'] = True

            quantidade_giro = self.carteiras['giro_rapido']['quantidade_total']
            if quantidade_giro > 0:
                logger.info(f"✅ Posição GIRO RÁPIDO carregada:")
                logger.info(f"   Quantidade: {quantidade_giro:.4f}")
                logger.info(f"   Preço médio: ${self.carteiras['giro_rapido']['preco_medio']:.6f}")
                logger.info(f"   Valor investido: ${self.carteiras['giro_rapido']['valor_total_investido']:.2f}")
            else:
                logger.info(f"📊 Posição GIRO RÁPIDO zerada")

        except Exception as e:
            logger.error(f"❌ Erro ao carregar posições iniciais: {e}")
            # Em caso de erro, resetar ambas
            self._resetar_posicao('acumulacao')
            self._resetar_posicao('giro_rapido')

    def carregar_posicao(self, carteira: str = 'acumulacao') -> Dict[str, Any]:
        """
        Recarrega a posição de uma carteira específica do banco de dados.

        REFATORADO: Agora ambas carteiras podem ser recarregadas do BD
        - Para 'acumulacao': Recarrega ordens com estrategia='acumulacao'
        - Para 'giro_rapido': Recarrega ordens com estrategia='giro_rapido'

        Args:
            carteira: Nome da carteira a carregar

        Returns:
            dict: Dados da posição carregada
        """
        try:
            logger.info(f"🔄 Recarregando posição do banco de dados (carteira: {carteira})...")

            # Buscar todas as ordens e filtrar por estratégia
            ordens = self._buscar_ordens_completas()

            if not ordens:
                logger.info("📊 Nenhuma ordem encontrada - posição zerada")
                self._resetar_posicao(carteira)
                return self._obter_resumo_posicao(carteira)

            # Calcular posição baseada nas ordens (com filtro por estratégia)
            self._calcular_posicao_das_ordens(ordens, carteira)
            self.carteiras[carteira]['posicao_carregada'] = True

            resumo = self._obter_resumo_posicao(carteira)

            quantidade = self.carteiras[carteira]['quantidade_total']
            if quantidade > 0:
                logger.info(f"✅ Posição recarregada ({carteira}):")
                logger.info(f"   Quantidade total: {quantidade:.4f}")
                logger.info(f"   Preço médio: ${self.carteiras[carteira]['preco_medio']:.6f}")
                logger.info(f"   Valor investido: ${self.carteiras[carteira]['valor_total_investido']:.2f}")
            else:
                logger.info(f"📊 Posição zerada ({carteira})")

            return resumo

        except Exception as e:
            logger.error(f"❌ Erro ao carregar posição ({carteira}): {e}")
            self._resetar_posicao(carteira)
            return self._obter_resumo_posicao(carteira)
    
    def _buscar_ordens_completas(self) -> List[Dict[str, Any]]:
        """
        Busca todas as ordens do banco de dados ordenadas por data
        INCLUINDO a coluna 'estrategia' para isolamento de carteiras

        Returns:
            Lista de ordens com a coluna 'estrategia'
        """
        try:
            # Buscar ordens usando context manager do DatabaseManager
            with self.db._conectar() as conn:
                cursor = conn.cursor()

                # Verificar se a tabela existe antes de tentar consultar
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='ordens'
                """)
                
                if not cursor.fetchone():
                    logger.debug("📊 Tabela 'ordens' ainda não existe")
                    return []

                cursor.execute("""
                    SELECT
                        id, tipo, par, quantidade, preco, valor_total,
                        taxa, meta, lucro_percentual, lucro_usdt,
                        preco_medio_antes, preco_medio_depois,
                        saldo_ada_antes, saldo_ada_depois,
                        saldo_usdt_antes, saldo_usdt_depois,
                        order_id, observacao, timestamp, estrategia
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
    
    def _calcular_posicao_das_ordens(self, ordens: List[Dict[str, Any]], carteira: str = 'acumulacao'):
        """
        Calcula posição atual baseada na lista de ordens FILTRANDO por estratégia

        ISOLAMENTO POR ESTRATÉGIA:
        - Processa apenas ordens onde estrategia == carteira
        - Ordens antigas (sem estrategia) são atribuídas a 'acumulacao'

        Args:
            ordens: Lista de ordens do banco de dados
            carteira: Nome da carteira ('acumulacao' ou 'giro_rapido')
        """
        quantidade_total = Decimal('0')
        valor_total_investido = Decimal('0')
        ordens_processadas = 0

        for ordem in ordens:
            # ═══════════════════════════════════════════════════════════
            # FILTRO CRÍTICO: Processar apenas ordens da carteira atual
            # ═══════════════════════════════════════════════════════════
            estrategia_ordem = ordem.get('estrategia')

            # Fallback para ordens antigas sem estrategia → acumulacao
            if not estrategia_ordem:
                estrategia_ordem = 'acumulacao'

            # PULAR ordens que não pertencem a esta carteira
            if estrategia_ordem != carteira:
                continue

            # Processar ordem da carteira atual
            tipo = ordem['tipo'].upper()
            quantidade = ordem['quantidade']
            preco = ordem['preco']
            valor_ordem = quantidade * preco

            if tipo == 'COMPRA':
                # Compra: aumenta quantidade e valor investido
                quantidade_total += quantidade
                valor_total_investido += valor_ordem
                ordens_processadas += 1

                logger.debug(f"🔵 COMPRA ({carteira}): +{quantidade:.4f} @ ${preco:.6f}")

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

                    ordens_processadas += 1
                    logger.debug(f"🔴 VENDA ({carteira}): -{quantidade:.4f} @ ${preco:.6f}")

        # Atualizar estado interno da carteira
        self.carteiras[carteira]['quantidade_total'] = quantidade_total
        self.carteiras[carteira]['valor_total_investido'] = valor_total_investido

        # Calcular preço médio
        if quantidade_total > 0 and valor_total_investido > 0:
            self.carteiras[carteira]['preco_medio'] = valor_total_investido / quantidade_total
        else:
            self.carteiras[carteira]['preco_medio'] = None

        logger.debug(f"📊 Processadas {ordens_processadas} ordens para carteira '{carteira}'")
    
    def get_quantidade_total(self, carteira: str = 'acumulacao') -> Decimal:
        """
        Retorna a quantidade total atual do ativo por carteira

        Args:
            carteira: Nome da carteira ('acumulacao' ou 'giro_rapido')

        Returns:
            Decimal: Quantidade total
        """
        if carteira not in self.carteiras:
            logger.warning(f"⚠️ Carteira '{carteira}' não existe. Retornando 0.")
            return Decimal('0')

        # Não tentar recarregar se não foi carregada
        # (a inicialização já carregou corretamente)
        return self.carteiras[carteira]['quantidade_total']

    def get_preco_medio(self, carteira: str = 'acumulacao') -> Optional[Decimal]:
        """
        Retorna o preço médio ponderado atual por carteira

        Args:
            carteira: Nome da carteira ('acumulacao' ou 'giro_rapido')

        Returns:
            Decimal: Preço médio ou None se não houver posição
        """
        if carteira not in self.carteiras:
            logger.warning(f"⚠️ Carteira '{carteira}' não existe.")
            return None

        return self.carteiras[carteira]['preco_medio']

    def get_valor_total_investido(self, carteira: str = 'acumulacao') -> Decimal:
        """
        Retorna o valor total investido atual por carteira

        Args:
            carteira: Nome da carteira ('acumulacao' ou 'giro_rapido')

        Returns:
            Decimal: Valor total investido
        """
        if carteira not in self.carteiras:
            logger.warning(f"⚠️ Carteira '{carteira}' não existe. Retornando 0.")
            return Decimal('0')

        return self.carteiras[carteira]['valor_total_investido']
    
    def atualizar_apos_compra(self, quantidade: Decimal, preco: Decimal, carteira: str = 'acumulacao'):
        """
        Atualiza o estado interno após uma compra sem precisar reler todo o banco

        Args:
            quantidade: Quantidade comprada
            preco: Preço da compra
            carteira: Nome da carteira ('acumulacao' ou 'giro_rapido')
        """
        if carteira not in self.carteiras:
            logger.error(f"❌ Carteira '{carteira}' não existe!")
            return

        valor_compra = quantidade * preco

        # Atualizar valores totais da carteira
        self.carteiras[carteira]['valor_total_investido'] += valor_compra
        self.carteiras[carteira]['quantidade_total'] += quantidade

        # Recalcular preço médio
        if self.carteiras[carteira]['quantidade_total'] > 0:
            self.carteiras[carteira]['preco_medio'] = (
                self.carteiras[carteira]['valor_total_investido'] /
                self.carteiras[carteira]['quantidade_total']
            )
        else:
            self.carteiras[carteira]['preco_medio'] = None

        logger.debug(f"📈 Posição atualizada após COMPRA ({carteira}):")
        logger.debug(f"   +{quantidade:.4f} @ ${preco:.6f}")
        logger.debug(f"   Total: {self.carteiras[carteira]['quantidade_total']:.4f}")
        pm = self.carteiras[carteira]['preco_medio']
        logger.debug(f"   Preço médio: ${pm:.6f}" if pm else "   Preço médio: N/A")

    def atualizar_apos_venda(self, quantidade: Decimal, carteira: str = 'acumulacao'):
        """
        Atualiza o estado interno após uma venda sem precisar reler todo o banco

        Args:
            quantidade: Quantidade vendida
            carteira: Nome da carteira ('acumulacao' ou 'giro_rapido')
        """
        if carteira not in self.carteiras:
            logger.error(f"❌ Carteira '{carteira}' não existe!")
            return

        if self.carteiras[carteira]['quantidade_total'] <= 0:
            logger.warning(f"⚠️ Tentativa de venda sem posição ({carteira})")
            return

        # Calcular proporção vendida
        proporcao_vendida = min(
            quantidade / self.carteiras[carteira]['quantidade_total'],
            Decimal('1')
        )

        # Reduzir quantidade e valor investido proporcionalmente
        self.carteiras[carteira]['quantidade_total'] -= quantidade
        self.carteiras[carteira]['valor_total_investido'] *= (Decimal('1') - proporcao_vendida)

        # Garantir que não ficou negativo por arredondamentos
        if self.carteiras[carteira]['quantidade_total'] < Decimal('0.0001'):
            self.carteiras[carteira]['quantidade_total'] = Decimal('0')
            self.carteiras[carteira]['valor_total_investido'] = Decimal('0')
            self.carteiras[carteira]['preco_medio'] = None
            # Resetar high water mark se for giro rápido
            if carteira == 'giro_rapido':
                self.carteiras[carteira]['high_water_mark_lucro'] = Decimal('0')
        elif self.carteiras[carteira]['quantidade_total'] > 0:
            self.carteiras[carteira]['preco_medio'] = (
                self.carteiras[carteira]['valor_total_investido'] /
                self.carteiras[carteira]['quantidade_total']
            )

        logger.debug(f"📉 Posição atualizada após VENDA ({carteira}):")
        logger.debug(f"   -{quantidade:.4f}")
        logger.debug(f"   Total: {self.carteiras[carteira]['quantidade_total']:.4f}")
        pm = self.carteiras[carteira]['preco_medio']
        logger.debug(f"   Preço médio: ${pm:.6f}" if pm else "   Preço médio: N/A")
    
    def calcular_lucro_atual(self, preco_atual: Decimal, carteira: str = 'acumulacao') -> Optional[Decimal]:
        """
        Calcula o lucro percentual atual baseado no preço médio

        Args:
            preco_atual: Preço atual do ativo
            carteira: Nome da carteira ('acumulacao' ou 'giro_rapido')

        Returns:
            Decimal: Lucro em % ou None se não houver posição
        """
        if carteira not in self.carteiras:
            return None

        preco_medio = self.carteiras[carteira]['preco_medio']
        quantidade = self.carteiras[carteira]['quantidade_total']

        if not preco_medio or preco_medio <= 0 or quantidade <= 0:
            return None

        lucro_pct = ((preco_atual - preco_medio) / preco_medio) * Decimal('100')
        return lucro_pct

    def tem_posicao(self, carteira: str = 'acumulacao') -> bool:
        """
        Verifica se há posição ativa (quantidade > 0) em uma carteira

        Args:
            carteira: Nome da carteira ('acumulacao' ou 'giro_rapido')

        Returns:
            bool: True se há posição ativa
        """
        if carteira not in self.carteiras:
            return False

        return self.carteiras[carteira]['quantidade_total'] > 0

    def _resetar_posicao(self, carteira: str = 'acumulacao'):
        """
        Reseta o estado interno da posição de uma carteira

        Args:
            carteira: Nome da carteira a resetar
        """
        if carteira in self.carteiras:
            self.carteiras[carteira]['quantidade_total'] = Decimal('0')
            self.carteiras[carteira]['preco_medio'] = None
            self.carteiras[carteira]['valor_total_investido'] = Decimal('0')
            self.carteiras[carteira]['posicao_carregada'] = True
            if carteira == 'giro_rapido':
                self.carteiras[carteira]['high_water_mark_lucro'] = Decimal('0')

    def _obter_resumo_posicao(self, carteira: str = 'acumulacao') -> Dict[str, Any]:
        """
        Obtém resumo da posição atual de uma carteira

        Args:
            carteira: Nome da carteira

        Returns:
            dict: Resumo da posição
        """
        if carteira not in self.carteiras:
            return {}

        return {
            'carteira': carteira,
            'quantidade_total': self.carteiras[carteira]['quantidade_total'],
            'preco_medio': self.carteiras[carteira]['preco_medio'],
            'valor_total_investido': self.carteiras[carteira]['valor_total_investido'],
            'tem_posicao': self.tem_posicao(carteira),
            'posicao_carregada': self.carteiras[carteira]['posicao_carregada']
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

    def atualizar_high_water_mark(self, lucro_percentual: Decimal, carteira: str = 'giro_rapido'):
        """
        Atualiza o high water mark de lucro para a carteira de giro rápido

        Args:
            lucro_percentual: Lucro percentual atual
            carteira: Nome da carteira (geralmente 'giro_rapido')
        """
        if carteira not in self.carteiras:
            return

        if 'high_water_mark_lucro' not in self.carteiras[carteira]:
            self.carteiras[carteira]['high_water_mark_lucro'] = Decimal('0')

        if lucro_percentual > self.carteiras[carteira]['high_water_mark_lucro']:
            self.carteiras[carteira]['high_water_mark_lucro'] = lucro_percentual
            logger.debug(f"📈 High water mark atualizado ({carteira}): {lucro_percentual:.2f}%")

    def get_high_water_mark(self, carteira: str = 'giro_rapido') -> Decimal:
        """
        Obtém o high water mark de lucro para uma carteira

        Args:
            carteira: Nome da carteira

        Returns:
            Decimal: High water mark de lucro
        """
        if carteira not in self.carteiras:
            return Decimal('0')

        return self.carteiras[carteira].get('high_water_mark_lucro', Decimal('0'))

    def forcar_quantidade(self, quantidade: Decimal, carteira: str = 'acumulacao'):
        """
        Força a quantidade total da posição para um valor específico.
        PRESERVA o preço médio existente e ajusta o valor_total_investido proporcionalmente.

        Args:
            quantidade: Nova quantidade (geralmente do saldo da exchange)
            carteira: Nome da carteira
        """
        if carteira in self.carteiras:
            preco_medio_atual = self.carteiras[carteira]['preco_medio']
            quantidade_anterior = self.carteiras[carteira]['quantidade_total']

            # Atualizar quantidade
            self.carteiras[carteira]['quantidade_total'] = quantidade

            # PRESERVAR PREÇO MÉDIO: Ajustar valor_total_investido para manter PM
            if quantidade > 0 and preco_medio_atual and preco_medio_atual > 0:
                # Recalcular valor investido baseado no PM atual
                self.carteiras[carteira]['valor_total_investido'] = quantidade * preco_medio_atual
                self.carteiras[carteira]['preco_medio'] = preco_medio_atual

                logger.warning(
                    f"⚠️ Quantidade ajustada de {quantidade_anterior:.4f} → {quantidade:.4f} ({carteira}). "
                    f"Preço médio PRESERVADO: ${preco_medio_atual:.6f}"
                )
            elif quantidade > 0 and self.carteiras[carteira]['valor_total_investido'] > 0:
                # Fallback: Recalcular PM se não havia PM anterior
                self.carteiras[carteira]['preco_medio'] = (
                    self.carteiras[carteira]['valor_total_investido'] / quantidade
                )
                logger.warning(
                    f"⚠️ Quantidade forçada para {quantidade:.4f} ({carteira}). "
                    f"Preço médio recalculado: ${self.carteiras[carteira]['preco_medio']:.6f}"
                )
            else:
                # Sem PM anterior e sem valor investido
                self.carteiras[carteira]['preco_medio'] = None
                logger.warning(
                    f"⚠️ Quantidade forçada para {quantidade:.4f} ({carteira}). "
                    f"Preço médio: N/A (sem dados históricos)"
                )

    def get_lucro_realizado_periodo(self, dias: int) -> Decimal:
        """Calcula o lucro realizado em um período de dias."""
        try:
            with self.db._conectar() as conn:
                cursor = conn.cursor()
                data_limite = datetime.now() - timedelta(days=dias)
                cursor.execute("""
                    SELECT SUM(lucro_usdt) 
                    FROM ordens 
                    WHERE tipo = 'VENDA' AND timestamp >= ?
                """, (data_limite,))
                resultado = cursor.fetchone()
                return Decimal(str(resultado[0])) if resultado and resultado[0] else Decimal('0')
        except Exception as e:
            logger.error(f"Erro ao calcular lucro realizado: {e}")
            return Decimal('0')

    def get_ultimas_ordens(self, limite: int) -> List[Dict[str, Any]]:
        """Busca as últimas ordens do banco de dados."""
        try:
            with self.db._conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM ordens ORDER BY timestamp DESC LIMIT ?
                """, (limite,))
                colunas = [desc[0] for desc in cursor.description]
                ordens = []
                for linha in cursor.fetchall():
                    ordem = dict(zip(colunas, linha))
                    ordens.append(ordem)
                return ordens
        except Exception as e:
            logger.error(f"Erro ao buscar últimas ordens: {e}")
            return []