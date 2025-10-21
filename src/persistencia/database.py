"""
Módulo de persistência em banco de dados SQLite.
Gerencia todas as operações de armazenamento e recuperação de dados do bot.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict, List, Any
import shutil
from src.utils.logger import get_loggers
from src.utils.conversoes import decimal_para_float

logger, _ = get_loggers()


class DatabaseManager:
    """Gerencia todas as operações com o banco de dados SQLite."""

    def __init__(self, db_path: Path, backup_dir: Path):
        """
        Inicializa o gerenciador de banco de dados.

        Args:
            db_path: Caminho para o arquivo do banco de dados
            backup_dir: Diretório para backups
        """
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # SQLite não permite compartilhar conexões entre threads
        # Usar sempre context manager para evitar problemas de thread
        self.conn = None

        # Criar banco e tabelas se não existirem
        self._criar_banco()
        logger.info(f"✅ DatabaseManager inicializado: {db_path}")

    def connect(self):
        """
        DEPRECATED: Use context manager _conectar() para thread safety.
        Mantido para compatibilidade, mas não recomendado.
        """
        logger.warning("⚠️ connect() deprecated: use context manager para thread safety")
        return sqlite3.connect(self.db_path)
    
    def close(self):
        """
        DEPRECATED: Conexões são gerenciadas via context manager.
        """
        logger.debug("🔌 close() chamado - usando context manager para conexões")
    
    def __del__(self):
        """
        Destrutor - nada a fazer pois usamos context manager.
        """
        pass
    
    @contextmanager
    def _conectar(self):
        """
        Context manager para conexões SQLite.

        Garante que a conexão seja fechada corretamente,
        mesmo em caso de exceção.

        Yields:
            sqlite3.Connection: Conexão com o banco de dados

        Example:
            with self._conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM ordens")
        """
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _criar_banco(self):
        """Cria o banco de dados e todas as tabelas necessárias."""
        with self._conectar() as conn:
            cursor = conn.cursor()

            # Tabela de ordens (compras e vendas)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ordens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    tipo TEXT NOT NULL,  -- 'COMPRA' ou 'VENDA'
                    par TEXT NOT NULL,   -- 'ADA/USDT'
                    quantidade REAL NOT NULL,
                    preco REAL NOT NULL,
                    valor_total REAL NOT NULL,
                    taxa REAL NOT NULL,
                    meta TEXT,  -- 'adaptativa', 'meta1', 'meta2', 'meta3', 'degrau1', etc
                    lucro_percentual REAL,
                    lucro_usdt REAL,
                    preco_medio_antes REAL,
                    preco_medio_depois REAL,
                    saldo_ada_antes REAL,
                    saldo_ada_depois REAL,
                    saldo_usdt_antes REAL,
                    saldo_usdt_depois REAL,
                    order_id TEXT,  -- ID da ordem na Binance
                    observacao TEXT,
                    estrategia TEXT  -- 'DCA', 'SELL', 'SWING_TRADE', etc
                )
            """)

            # Tabela de saldos (snapshot periódico)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saldos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    ada_livre REAL NOT NULL,
                    ada_bloqueado REAL NOT NULL,
                    ada_total REAL NOT NULL,
                    usdt_livre REAL NOT NULL,
                    usdt_bloqueado REAL NOT NULL,
                    usdt_total REAL NOT NULL,
                    bnb_livre REAL,
                    bnb_bloqueado REAL,
                    bnb_total REAL,
                    valor_total_usdt REAL,
                    preco_ada REAL
                )
            """)

            # Tabela de preços (histórico)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS precos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    par TEXT NOT NULL,
                    preco REAL NOT NULL,
                    sma_20 REAL,
                    sma_50 REAL
                )
            """)

            # Tabela de métricas de performance
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metricas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_compras INTEGER NOT NULL,
                    total_vendas INTEGER NOT NULL,
                    volume_comprado REAL NOT NULL,
                    volume_vendido REAL NOT NULL,
                    lucro_realizado REAL NOT NULL,
                    taxa_total REAL NOT NULL,
                    roi_percentual REAL,
                    maior_lucro REAL,
                    menor_lucro REAL,
                    lucro_medio REAL,
                    trades_lucrativos INTEGER,
                    trades_totais INTEGER
                )
            """)

            # Tabela de conversões BNB
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversoes_bnb (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    quantidade_bnb REAL NOT NULL,
                    valor_usdt REAL NOT NULL,
                    preco_bnb REAL NOT NULL,
                    saldo_bnb_antes REAL NOT NULL,
                    saldo_bnb_depois REAL NOT NULL,
                    saldo_usdt_antes REAL NOT NULL,
                    saldo_usdt_depois REAL NOT NULL,
                    order_id TEXT
                )
            """)

            # Tabela de estado do bot (para recuperação)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS estado_bot (
                    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Apenas 1 registro
                    timestamp_atualizacao TEXT NOT NULL,
                    preco_medio_compra REAL,
                    quantidade_total_ada REAL,
                    ultima_compra TEXT,
                    ultima_venda TEXT,
                    cooldown_ativo INTEGER DEFAULT 0,
                    bot_ativo INTEGER DEFAULT 1
                )
            """)

            # Criar índices para melhorar performance de queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ordens_timestamp ON ordens(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ordens_tipo ON ordens(tipo)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_saldos_timestamp ON saldos(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_precos_timestamp ON precos(timestamp)")

            # Garantir que a coluna 'order_id' existe em bancos de dados existentes
            try:
                cursor.execute("ALTER TABLE ordens ADD COLUMN order_id TEXT")
                logger.info("✅ Coluna 'order_id' adicionada à tabela 'ordens'")
            except sqlite3.OperationalError as e:
                # Coluna já existe
                if "duplicate column name" in str(e).lower():
                    logger.debug("Coluna 'order_id' já existe na tabela 'ordens'")
                else:
                    raise

            # Garantir que a coluna 'estrategia' existe em bancos de dados existentes
            try:
                cursor.execute("ALTER TABLE ordens ADD COLUMN estrategia TEXT")
                logger.info("✅ Coluna 'estrategia' adicionada à tabela 'ordens'")
            except sqlite3.OperationalError as e:
                # Coluna já existe
                if "duplicate column name" in str(e).lower():
                    logger.debug("Coluna 'estrategia' já existe na tabela 'ordens'")
                else:
                    raise

        logger.info("✅ Banco de dados criado/verificado com sucesso")

    def registrar_ordem(self, dados: Dict[str, Any]) -> int:
        """
        Registra uma ordem de compra ou venda no banco.

        Args:
            dados: Dicionário com os dados da ordem (deve incluir 'estrategia')

        Returns:
            ID da ordem inserida
        """
        with self._conectar() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO ordens (
                    timestamp, tipo, par, quantidade, preco, valor_total, taxa,
                    meta, lucro_percentual, lucro_usdt,
                    preco_medio_antes, preco_medio_depois,
                    saldo_ada_antes, saldo_ada_depois,
                    saldo_usdt_antes, saldo_usdt_depois,
                    order_id, observacao, estrategia
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dados.get('timestamp', datetime.now().isoformat()),
                dados['tipo'],
                dados['par'],
                decimal_para_float(dados['quantidade']),
                decimal_para_float(dados['preco']),
                decimal_para_float(dados['valor_total']),
                decimal_para_float(dados.get('taxa', 0)),
                dados.get('meta'),
                decimal_para_float(dados.get('lucro_percentual')),
                decimal_para_float(dados.get('lucro_usdt')),
                decimal_para_float(dados.get('preco_medio_antes')),
                decimal_para_float(dados.get('preco_medio_depois')),
                decimal_para_float(dados.get('saldo_ada_antes')),
                decimal_para_float(dados.get('saldo_ada_depois')),
                decimal_para_float(dados.get('saldo_usdt_antes')),
                decimal_para_float(dados.get('saldo_usdt_depois')),
                dados.get('order_id'),
                dados.get('observacao'),
                dados.get('estrategia')
            ))

            return cursor.lastrowid

    def registrar_saldo(self, dados: Dict[str, Any]):
        """Registra um snapshot dos saldos."""
        with self._conectar() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO saldos (
                    timestamp, ada_livre, ada_bloqueado, ada_total,
                    usdt_livre, usdt_bloqueado, usdt_total,
                    bnb_livre, bnb_bloqueado, bnb_total,
                    valor_total_usdt, preco_ada
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dados.get('timestamp', datetime.now().isoformat()),
                decimal_para_float(dados['ada_livre']),
                decimal_para_float(dados['ada_bloqueado']),
                decimal_para_float(dados['ada_total']),
                decimal_para_float(dados['usdt_livre']),
                decimal_para_float(dados['usdt_bloqueado']),
                decimal_para_float(dados['usdt_total']),
                decimal_para_float(dados.get('bnb_livre', 0)),
                decimal_para_float(dados.get('bnb_bloqueado', 0)),
                decimal_para_float(dados.get('bnb_total', 0)),
                decimal_para_float(dados.get('valor_total_usdt', 0)),
                decimal_para_float(dados.get('preco_ada', 0))
            ))

    def registrar_preco(self, par: str, preco: float, sma_20: Optional[float] = None,
                       sma_50: Optional[float] = None):
        """Registra o preço atual e médias móveis."""
        with self._conectar() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO precos (timestamp, par, preco, sma_20, sma_50)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                par,
                decimal_para_float(preco),
                decimal_para_float(sma_20),
                decimal_para_float(sma_50)
            ))

    def atualizar_estado_bot(self, preco_medio: Optional[Decimal] = None,
                            quantidade: Optional[Decimal] = None,
                            cooldown_ativo: Optional[bool] = None):
        """Atualiza o estado atual do bot para recuperação futura."""
        with self._conectar() as conn:
            cursor = conn.cursor()

            # Verificar se já existe um registro de estado
            cursor.execute("SELECT id FROM estado_bot WHERE id = 1")
            existe = cursor.fetchone()

            if existe:
                # Atualizar registro existente
                updates = ["timestamp_atualizacao = ?"]
                params = [datetime.now().isoformat()]

                if preco_medio is not None:
                    updates.append("preco_medio_compra = ?")
                    params.append(decimal_para_float(preco_medio))

                if quantidade is not None:
                    updates.append("quantidade_total_ada = ?")
                    params.append(decimal_para_float(quantidade))

                if cooldown_ativo is not None:
                    updates.append("cooldown_ativo = ?")
                    params.append(1 if cooldown_ativo else 0)

                sql = f"UPDATE estado_bot SET {', '.join(updates)} WHERE id = 1"
                cursor.execute(sql, params)
            else:
                # Inserir novo registro
                cursor.execute("""
                    INSERT INTO estado_bot (
                        id, timestamp_atualizacao, preco_medio_compra,
                        quantidade_total_ada, cooldown_ativo
                    ) VALUES (1, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    decimal_para_float(preco_medio),
                    decimal_para_float(quantidade),
                    1 if cooldown_ativo else 0
                ))

    def recuperar_estado_bot(self) -> Optional[Dict[str, Any]]:
        """Recupera o último estado salvo do bot."""
        with self._conectar() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT preco_medio_compra, quantidade_total_ada,
                       ultima_compra, ultima_venda, cooldown_ativo
                FROM estado_bot WHERE id = 1
            """)

            resultado = cursor.fetchone()

            if resultado:
                return {
                    'preco_medio_compra': Decimal(str(resultado[0])) if resultado[0] else None,
                    'quantidade_total_ada': Decimal(str(resultado[1])) if resultado[1] else None,
                    'ultima_compra': resultado[2],
                    'ultima_venda': resultado[3],
                    'cooldown_ativo': bool(resultado[4])
                }

            return None

    def calcular_metricas(self) -> Dict[str, Any]:
        """Calcula métricas de performance baseadas nas ordens."""
        with self._conectar() as conn:
            cursor = conn.cursor()

            # Total de compras e vendas
            cursor.execute("SELECT COUNT(*) FROM ordens WHERE tipo = 'COMPRA'")
            total_compras = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM ordens WHERE tipo = 'VENDA'")
            total_vendas = cursor.fetchone()[0]

            # Volume comprado e vendido
            cursor.execute("SELECT COALESCE(SUM(valor_total), 0) FROM ordens WHERE tipo = 'COMPRA'")
            volume_comprado = cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(SUM(valor_total), 0) FROM ordens WHERE tipo = 'VENDA'")
            volume_vendido = cursor.fetchone()[0]

            # Lucro realizado total
            cursor.execute("SELECT COALESCE(SUM(lucro_usdt), 0) FROM ordens WHERE tipo = 'VENDA'")
            lucro_realizado = cursor.fetchone()[0]

            # Taxas totais
            cursor.execute("SELECT COALESCE(SUM(taxa), 0) FROM ordens")
            taxa_total = cursor.fetchone()[0]

            # Estatísticas de lucro
            cursor.execute("""
                SELECT
                    MAX(lucro_usdt) as maior_lucro,
                    MIN(lucro_usdt) as menor_lucro,
                    AVG(lucro_usdt) as lucro_medio,
                    COUNT(*) as trades_lucrativos
                FROM ordens
                WHERE tipo = 'VENDA' AND lucro_usdt > 0
            """)
            stats = cursor.fetchone()

            roi = (lucro_realizado / volume_comprado * 100) if volume_comprado > 0 else 0

            return {
                'total_compras': total_compras,
                'total_vendas': total_vendas,
                'volume_comprado': volume_comprado,
                'volume_vendido': volume_vendido,
                'lucro_realizado': lucro_realizado,
                'taxa_total': taxa_total,
                'roi_percentual': roi,
                'maior_lucro': stats[0] or 0,
                'menor_lucro': stats[1] or 0,
                'lucro_medio': stats[2] or 0,
                'trades_lucrativos': stats[3] or 0,
                'trades_totais': total_vendas
            }

    def salvar_metricas(self):
        """Calcula e salva as métricas atuais no banco."""
        metricas = self.calcular_metricas()

        with self._conectar() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO metricas (
                    timestamp, total_compras, total_vendas,
                    volume_comprado, volume_vendido, lucro_realizado, taxa_total,
                    roi_percentual, maior_lucro, menor_lucro, lucro_medio,
                    trades_lucrativos, trades_totais
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                metricas['total_compras'],
                metricas['total_vendas'],
                metricas['volume_comprado'],
                metricas['volume_vendido'],
                metricas['lucro_realizado'],
                metricas['taxa_total'],
                metricas['roi_percentual'],
                metricas['maior_lucro'],
                metricas['menor_lucro'],
                metricas['lucro_medio'],
                metricas['trades_lucrativos'],
                metricas['trades_totais']
            ))

    def obter_ultimas_ordens(self, limite: int = 10) -> List[Dict[str, Any]]:
        """Retorna as últimas N ordens."""
        with self._conectar() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM ordens
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limite,))

            ordens = [dict(row) for row in cursor.fetchall()]

            return ordens

    def fazer_backup(self) -> str:
        """Cria um backup do banco de dados."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"trading_bot_backup_{timestamp}.db"

        shutil.copy2(self.db_path, backup_path)
        logger.info(f"💾 Backup criado: {backup_path}")

        return str(backup_path)

    def registrar_conversao_bnb(self, dados: Dict[str, Any]):
        """Registra uma conversão de USDT para BNB."""
        with self._conectar() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO conversoes_bnb (
                    timestamp, quantidade_bnb, valor_usdt, preco_bnb,
                    saldo_bnb_antes, saldo_bnb_depois,
                    saldo_usdt_antes, saldo_usdt_depois, order_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dados.get('timestamp', datetime.now().isoformat()),
                decimal_para_float(dados['quantidade_bnb']),
                decimal_para_float(dados['valor_usdt']),
                decimal_para_float(dados['preco_bnb']),
                decimal_para_float(dados['saldo_bnb_antes']),
                decimal_para_float(dados['saldo_bnb_depois']),
                decimal_para_float(dados['saldo_usdt_antes']),
                decimal_para_float(dados['saldo_usdt_depois']),
                dados.get('order_id')
            ))

    def ordem_ja_existe(self, order_id: str) -> bool:
        """Verifica se uma ordem já está no banco de dados."""
        with self._conectar() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM ordens WHERE order_id = ?", (order_id,))
            existe = cursor.fetchone()[0] > 0

            return existe

    def importar_ordens_binance(self, ordens_binance: List[Dict], recalcular_preco_medio: bool = True):
        """
        Importa ordens do histórico da Binance para o banco de dados.

        Args:
            ordens_binance: Lista de ordens da API da Binance
            recalcular_preco_medio: Se deve recalcular preço médio após importação

        Returns:
            Dicionário com estatísticas da importação
        """
        importadas = 0
        duplicadas = 0
        erros = 0
        
        with self._conectar() as conn:
            cursor = conn.cursor()

            for ordem in ordens_binance:
                try:
                    order_id = str(ordem.get('orderId'))

                    # Verificar se já existe (dentro da mesma transação)
                    cursor.execute("SELECT COUNT(*) FROM ordens WHERE order_id = ?", (order_id,))
                    if cursor.fetchone()[0] > 0:
                        duplicadas += 1
                        continue

                    # Extrair dados da ordem
                    timestamp = datetime.fromtimestamp(ordem['time'] / 1000).isoformat()
                    tipo = 'COMPRA' if ordem['side'] == 'BUY' else 'VENDA'
                    quantidade = float(ordem['executedQty'])

                    # Calcular preço médio da ordem
                    preco = float(ordem['cummulativeQuoteQty']) / quantidade if quantidade > 0 else 0
                    valor_total = float(ordem['cummulativeQuoteQty'])

                    # Taxa (se disponível nos fills)
                    taxa = 0
                    if 'fills' in ordem and ordem['fills']:
                        taxa = sum(float(fill.get('commission', 0)) for fill in ordem['fills'])

                    # Inserir no banco
                    cursor.execute("""
                        INSERT INTO ordens (
                            timestamp, tipo, par, quantidade, preco, valor_total, taxa,
                            order_id, observacao, estrategia
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        timestamp,
                        tipo,
                        ordem['symbol'],
                        quantidade,
                        preco,
                        valor_total,
                        taxa,
                        order_id,
                        f"Importado do histórico da Binance - Status: {ordem.get('status')}",
                        'acumulacao'  # Ordens importadas são atribuídas à estratégia de acumulação
                    ))

                    importadas += 1

                except Exception as e:
                    logger.error(f"Erro ao importar ordem {ordem.get('orderId')}: {e}")
                    erros += 1
        
        # Recalcular preço médio DEPOIS de fechar a conexão anterior
        if recalcular_preco_medio and importadas > 0:
            self._recalcular_preco_medio_historico()

        return {
            'importadas': importadas,
            'duplicadas': duplicadas,
            'erros': erros,
            'total_processadas': len(ordens_binance)
        }

    def _recalcular_preco_medio_historico(self):
        """
        Recalcula o preço médio de compra baseado no histórico completo.
        Atualiza o estado do bot com os valores calculados.
        """
        with self._conectar() as conn:
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
            valor_total = sum(float(c[0]) * float(c[1]) for c in compras)

            # Subtrair total vendido
            total_vendido = sum(float(v[0]) for v in vendas)
            quantidade_atual = total_comprado - total_vendido

            # Calcular preço médio
            if total_comprado > 0:
                preco_medio = valor_total / total_comprado
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

            logger.info(f"📊 Preço médio recalculado: ${preco_medio:.6f} ({quantidade_atual:.1f} ADA)")

            return {
                'preco_medio': preco_medio,
                'quantidade_atual': quantidade_atual,
                'total_comprado': total_comprado,
                'total_vendido': total_vendido
            }

    def obter_estatisticas_24h(self) -> Dict[str, Any]:
        """
        Retorna estatísticas das últimas 24 horas.

        Returns:
            Dicionário com estatísticas: compras, vendas, lucro realizado
        """
        with self._conectar() as conn:
            cursor = conn.cursor()

            # Timestamp de 24 horas atrás
            from datetime import timedelta
            limite_24h = (datetime.now() - timedelta(hours=24)).isoformat()

            # Total de compras nas últimas 24h
            cursor.execute("""
                SELECT COUNT(*) FROM ordens
                WHERE tipo = 'COMPRA' AND timestamp >= ?
            """, (limite_24h,))
            total_compras = cursor.fetchone()[0]

            # Total de vendas nas últimas 24h
            cursor.execute("""
                SELECT COUNT(*) FROM ordens
                WHERE tipo = 'VENDA' AND timestamp >= ?
            """, (limite_24h,))
            total_vendas = cursor.fetchone()[0]

            # Lucro realizado nas últimas 24h
            cursor.execute("""
                SELECT COALESCE(SUM(lucro_usdt), 0) FROM ordens
                WHERE tipo = 'VENDA' AND timestamp >= ?
            """, (limite_24h,))
            lucro_realizado = cursor.fetchone()[0]

            return {
                'compras': total_compras,
                'vendas': total_vendas,
                'lucro_realizado': lucro_realizado
            }

    def obter_ultima_ordem(self, tipo: str) -> Optional[Dict[str, Any]]:
        """
        Obtém a última ordem de um tipo específico (COMPRA ou VENDA).

        Args:
            tipo: 'COMPRA' ou 'VENDA'

        Returns:
            Dicionário com dados da última ordem ou None se não houver
        """
        with self._conectar() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM ordens
                WHERE tipo = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (tipo,))

            resultado = cursor.fetchone()

            if resultado:
                return dict(resultado)

            return None

    def obter_historico_precos(self, limite_minutos: int = 60) -> List[float]:
        """
        Obtém histórico de preços recente para cálculo de volatilidade.

        Args:
            limite_minutos: Quantos minutos de histórico buscar

        Returns:
            Lista de preços
        """
        with self._conectar() as conn:
            cursor = conn.cursor()

            from datetime import timedelta
            limite_tempo = (datetime.now() - timedelta(minutes=limite_minutos)).isoformat()

            cursor.execute("""
                SELECT preco FROM precos
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            """, (limite_tempo,))

            resultados = cursor.fetchall()

            return [float(r[0]) for r in resultados]

    def obter_timestamp_ultima_compra_degrau(self, nivel_degrau: int) -> Optional[str]:
        """
        Obtém o timestamp da última compra em um degrau específico.

        Args:
            nivel_degrau: Nível do degrau (1, 2, 3, etc)

        Returns:
            Timestamp ISO da última compra ou None se nunca comprou
        """
        with self._conectar() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT timestamp FROM ordens
                WHERE tipo = 'COMPRA' AND meta = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (f'degrau{nivel_degrau}',))

            resultado = cursor.fetchone()

            if resultado:
                return resultado[0]

            return None

    def obter_timestamp_ultima_compra_global(self) -> Optional[str]:
        """
        Obtém o timestamp da última compra em qualquer degrau.

        Returns:
            Timestamp ISO da última compra ou None se nunca comprou
        """
        with self._conectar() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT timestamp FROM ordens
                WHERE tipo = 'COMPRA'
                ORDER BY timestamp DESC
                LIMIT 1
            """)

            resultado = cursor.fetchone()

            if resultado:
                return resultado[0]

            return None