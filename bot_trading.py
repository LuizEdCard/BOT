#!/usr/bin/env python3
"""
Bot de Trading ADA/USDT - Versão Completa
Compra em quedas (degraus) e vende em altas (metas)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import time
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from config.settings import settings
from src.comunicacao.api_manager import APIManager
from src.core.gerenciador_aportes import GerenciadorAportes
from src.core.gerenciador_bnb import GerenciadorBNB
from src.core.analise_tecnica import AnaliseTecnica
from src.core.gestao_capital import GestaoCapital
from src.persistencia.database import DatabaseManager
from src.persistencia.state_manager import StateManager
from src.utils.logger import get_logger
from src.utils.constants import Icones, LogConfig

# Configurar logger com formato configurável
logger = get_logger(
    log_dir=Path('logs'),
    config=LogConfig.DEFAULT,  # Usa configuração padrão (produção)
    console=True
)


class TradingBot:
    """Bot de Trading ADA/USDT"""

    def __init__(self):
        """Inicializar bot"""
        self.api = APIManager(
            api_key=settings.BINANCE_API_KEY,
            api_secret=settings.BINANCE_API_SECRET,
            base_url=settings.BINANCE_API_URL
        )

        self.gerenciador_aportes = GerenciadorAportes(self.api, settings)
        self.gerenciador_bnb = GerenciadorBNB(self.api, settings)
        self.analise_tecnica = AnaliseTecnica(self.api)
        self.gestao_capital = GestaoCapital()  # Gestor de capital com validação de reserva

        # Banco de dados (somente para ordens e histórico)
        self.db = DatabaseManager(
            db_path=settings.DATABASE_PATH,
            backup_dir=settings.BACKUP_DIR
        )

        # Gerenciador de estado operacional (cooldowns, timestamps)
        self.state = StateManager(state_file_path='dados/bot_state.json')

        # Estado do bot
        self.sma_referencia: Optional[Decimal] = None  # SMA de 4 semanas como referência
        self.sma_1h: Optional[Decimal] = None
        self.sma_4h: Optional[Decimal] = None
        self.ultima_atualizacao_sma = None
        self.ultimo_backup = datetime.now()
        self.rodando = False
        self.inicio_bot = datetime.now()  # Timestamp de início para calcular uptime

        # Controle de verificação de aportes BRL
        self.aportes_config = settings.APORTES
        self.intervalo_verificacao_aportes = timedelta(minutes=self.aportes_config['intervalo_verificacao_minutos'])
        self.ultima_verificacao_aportes = datetime.now() - self.intervalo_verificacao_aportes

        # Histórico de preços (últimos 100)
        self.historico_precos: List[Decimal] = []

        # ═══════════════════════════════════════════════════════════════════
        # NOVA ESTRATÉGIA: Largada a Frio + Cooldown Duplo
        # ═══════════════════════════════════════════════════════════════════
        self.primeira_execucao: bool = True  # Detecta se é a primeira execução
        # NOTA: timestamp_ultima_compra_global agora é gerenciado via StateManager

        # Controle de spam de logs (evita logar "Degrau X ativado" repetidamente)
        self.ultima_tentativa_log_degrau: Dict[int, datetime] = {}  # {nivel_degrau: timestamp_ultimo_log}

        # Rastreamento de degraus bloqueados (para notificações inteligentes)
        self.degraus_notificados_bloqueados: set = set()  # Degraus que já foram notificados como bloqueados

        # Controle de notificação de exposição máxima
        self.notificou_exposicao_maxima: bool = False

        # Estado operacional do bot
        self.estado_bot: str = "OPERANDO"  # "OPERANDO" ou "AGUARDANDO_SALDO"
        self.ja_avisou_sem_saldo: bool = False  # Evita avisar repetidamente

        # Rastreamento de preço médio de compra (para calcular lucro)
        self.preco_medio_compra: Optional[Decimal] = None
        self.quantidade_total_comprada: Decimal = Decimal('0')
        self.valor_total_investido: Decimal = Decimal('0')

        # ═══════════════════════════════════════════════════════════════════
        # ESTRATÉGIA AVANÇADA: High-Water Mark e Zonas de Segurança
        # ═══════════════════════════════════════════════════════════════════
        self.high_water_mark_profit: Decimal = Decimal('0')  # Maior lucro % atingido na escalada atual
        self.zonas_de_seguranca_acionadas: set = set()  # Nomes das zonas já acionadas
        self.capital_para_recompra: Dict[str, Dict] = {}  # {nome_zona: {'capital_usdt': X, 'high_mark': Y}}

        # Recuperar estado do banco de dados (se existir)
        self._recuperar_estado_do_banco()

    def _recuperar_estado_do_banco(self):
        """
        Recupera estado anterior do bot a partir do banco de dados.
        Isso permite que o bot continue de onde parou após reinício.
        """
        try:
            estado = self.db.recuperar_estado_bot()

            if estado:
                self.preco_medio_compra = estado.get('preco_medio_compra')
                self.quantidade_total_comprada = estado.get('quantidade_total_ada', Decimal('0'))

                # Recalcular valor total investido
                if self.preco_medio_compra and self.quantidade_total_comprada > 0:
                    self.valor_total_investido = self.preco_medio_compra * self.quantidade_total_comprada

                    logger.info("🔄 Estado recuperado do banco de dados:")
                    logger.info(f"   Preço médio: ${self.preco_medio_compra:.6f}")
                    logger.info(f"   Quantidade (local): {self.quantidade_total_comprada:.1f} ADA")
                    logger.info(f"   Valor investido: ${self.valor_total_investido:.2f} USDT")
                else:
                    logger.info("📊 Iniciando com estado limpo (sem posições anteriores)")
            else:
                logger.info("📊 Nenhum estado anterior encontrado - iniciando do zero")

            # Recuperar timestamp da última compra global (para cooldown global)
            self._recuperar_timestamp_ultima_compra_global()

        except Exception as e:
            logger.error(f"⚠️ Erro ao recuperar estado do banco: {e}")
            logger.info("📊 Continuando com estado limpo")

    def _sincronizar_saldos_binance(self):
        """
        CRÍTICO: Sincroniza saldos (ADA e USDT) reais da Binance com estado local.

        Isso garante que:
        1. O bot sempre inicia com o saldo REAL da Binance
        2. Divergências entre backup local e Binance são corrigidas
        3. Compras/vendas feitas manualmente são detectadas

        Executado no início do bot e após conversões de BRL.
        """
        try:
            logger.info("🔄 Sincronizando saldos com a Binance...")

            # Buscar saldo real da API Binance
            saldos_binance = self.obter_saldos()
            saldo_ada_real = saldos_binance['ada']
            saldo_usdt_real = saldos_binance['usdt']

            # Comparar com estado local
            saldo_ada_local = self.quantidade_total_comprada

            logger.info(f"📊 Saldo local (backup): {saldo_ada_local:.1f} ADA")
            logger.info(f"📊 Saldo Binance (real): {saldo_ada_real:.1f} ADA | ${saldo_usdt_real:.2f} USDT")

            # Verificar divergência
            diferenca = abs(saldo_ada_real - saldo_ada_local)

            if diferenca >= Decimal('0.1'):  # Diferença significativa (>= 0.1 ADA)
                logger.warning("⚠️ DIVERGÊNCIA DETECTADA entre backup local e Binance!")
                logger.warning(f"   Diferença: {diferenca:.1f} ADA")
                logger.warning("")
                logger.warning("🔄 Sincronizando com saldo REAL da Binance...")

                # Atualizar quantidade com saldo real da Binance
                self.quantidade_total_comprada = saldo_ada_real

                # Recalcular valor investido (mantendo preço médio se existir)
                if self.preco_medio_compra and self.quantidade_total_comprada > 0:
                    self.valor_total_investido = self.preco_medio_compra * self.quantidade_total_comprada
                    logger.info(f"✅ Posição sincronizada: {self.quantidade_total_comprada:.1f} ADA")
                    logger.info(f"   Preço médio mantido: ${self.preco_medio_compra:.6f}")
                    logger.info(f"   Valor investido recalculado: ${self.valor_total_investido:.2f} USDT")
                elif self.quantidade_total_comprada > 0:
                    # Tem ADA mas não tem preço médio - calcular baseado em preço atual
                    preco_atual = self.obter_preco_atual()
                    if preco_atual:
                        self.preco_medio_compra = preco_atual
                        self.valor_total_investido = self.quantidade_total_comprada * preco_atual
                        logger.warning("⚠️ Preço médio não encontrado - usando preço atual como referência")
                        logger.info(f"   Preço atual: ${preco_atual:.6f}")
                        logger.info(f"   Valor investido estimado: ${self.valor_total_investido:.2f} USDT")
                else:
                    # Não tem ADA - zerar estado
                    self.preco_medio_compra = None
                    self.valor_total_investido = Decimal('0')
                    logger.info("✅ Posição zerada (sem ADA na Binance)")

                # Atualizar estado no banco com valores sincronizados
                self.db.atualizar_estado_bot(
                    preco_medio=self.preco_medio_compra,
                    quantidade=self.quantidade_total_comprada
                )
                logger.info("💾 Backup local atualizado com saldo da Binance")
            else:
                logger.info("✅ Saldo local sincronizado com Binance")

            logger.info(f"💼 Saldo final confirmado: {self.quantidade_total_comprada:.1f} ADA | ${saldo_usdt_real:.2f} USDT")
            logger.info("")

        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar saldo com Binance: {e}")
            logger.warning("⚠️ Continuando com saldo local (pode estar desatualizado)")

    def _recuperar_timestamp_ultima_compra_global(self):
        """
        Recupera o timestamp da última compra global do StateManager.
        Isso garante que o cooldown global seja respeitado após reinício do bot.
        """
        try:
            timestamp_str = self.state.get_state('ultima_compra_global_ts')

            if timestamp_str:
                timestamp_compra = datetime.fromisoformat(timestamp_str)
                tempo_decorrido = datetime.now() - timestamp_compra
                minutos = int(tempo_decorrido.total_seconds() / 60)
                logger.info(f"🕒 Última compra global: há {minutos} minutos")
            # NOTA: Não loga nada se não encontrar timestamp, pois isso é esperado
            # quando o banco está vazio ou quando é realmente a primeira execução

        except Exception as e:
            logger.error(f"⚠️ Erro ao recuperar timestamp da última compra: {e}")
            logger.info("📋 Continuando sem histórico")

    def importar_historico_binance(self, simbolo: str = 'ADAUSDT', limite: int = 500):
        """
        Importa histórico de ordens da Binance para o banco de dados.

        Args:
            simbolo: Par de moedas (padrão: ADAUSDT)
            limite: Número máximo de ordens a importar (padrão: 500)

        Returns:
            Dicionário com estatísticas da importação
        """
        try:
            logger.info(f"📥 Importando histórico de ordens da Binance ({simbolo})...")

            # Buscar ordens da Binance
            ordens = self.api.obter_historico_ordens(simbolo=simbolo, limite=limite)

            if not ordens:
                logger.info("📭 Nenhuma ordem encontrada no histórico da Binance")
                return {'importadas': 0, 'duplicadas': 0, 'erros': 0}

            logger.info(f"📋 Encontradas {len(ordens)} ordens no histórico da Binance")

            # Importar para o banco de dados
            resultado = self.db.importar_ordens_binance(ordens, recalcular_preco_medio=True)

            logger.info(f"✅ Importação concluída:")
            logger.info(f"   Importadas: {resultado['importadas']}")
            logger.info(f"   Duplicadas: {resultado['duplicadas']}")
            logger.info(f"   Erros: {resultado['erros']}")

            # Atualizar estado do bot com valores recalculados
            if resultado['importadas'] > 0:
                self._recuperar_estado_do_banco()

            return resultado

        except Exception as e:
            logger.error(f"❌ Erro ao importar histórico: {e}")
            return {'importadas': 0, 'duplicadas': 0, 'erros': 1}

    def obter_preco_atual(self) -> Optional[Decimal]:
        """Obtém preço atual de ADA/USDT"""
        try:
            ticker = self.api.obter_ticker('ADAUSDT')
            preco = Decimal(str(ticker['price']))

            # Adicionar ao histórico
            self.historico_precos.append(preco)
            if len(self.historico_precos) > settings.TAMANHO_BUFFER_PRECOS:
                self.historico_precos.pop(0)

            return preco
        except Exception as e:
            logger.erro_api('obter_preco_atual', str(e))
            return None

    def obter_saldos(self) -> Dict:
        """Obtém saldos de USDT e ADA"""
        try:
            saldos_raw = self.api.obter_saldos()

            saldo_usdt = Decimal('0')
            saldo_ada = Decimal('0')

            for saldo in saldos_raw:
                if saldo['asset'] == 'USDT':
                    saldo_usdt = Decimal(str(saldo['free']))
                elif saldo['asset'] == 'ADA':
                    saldo_ada = Decimal(str(saldo['free']))

            return {
                'usdt': saldo_usdt,
                'ada': saldo_ada
            }
        except Exception as e:
            logger.erro_api('obter_saldos', str(e))
            return {'usdt': Decimal('0'), 'ada': Decimal('0')}

    def atualizar_sma(self):
        """
        Atualiza SMA de 4 semanas (referência de "pico")
        Atualiza a cada 1 hora para economizar API calls
        """
        agora = datetime.now()

        # Atualizar apenas se passou 1 hora ou se nunca foi calculada
        if (self.ultima_atualizacao_sma is None or
            (agora - self.ultima_atualizacao_sma) >= timedelta(hours=1)):

            logger.info("🔄 Atualizando SMA de referência (4 semanas)...")

            smas = self.analise_tecnica.calcular_sma_multiplos_timeframes(
                simbolo='ADAUSDT',
                periodo_dias=28  # 4 semanas
            )

            if smas:
                self.sma_1h = smas.get('1h')
                self.sma_4h = smas.get('4h')
                self.sma_referencia = smas.get('media')  # Média ponderada
                self.ultima_atualizacao_sma = agora

                logger.info(f"✅ SMA de referência atualizada: ${self.sma_referencia:.6f}")
            else:
                logger.error("❌ Não foi possível atualizar SMA")

    def calcular_queda_percentual(self, preco_atual: Decimal) -> Optional[Decimal]:
        """Calcula queda % desde a SMA de referência"""
        if self.sma_referencia is None:
            return None

        queda = ((self.sma_referencia - preco_atual) / self.sma_referencia) * Decimal('100')
        return queda

    def encontrar_degrau_ativo(self, queda_pct: Decimal) -> Optional[Dict]:
        """Encontra degrau de compra correspondente"""
        for degrau in settings.DEGRAUS_COMPRA:
            if queda_pct >= Decimal(str(degrau['queda_percentual'])):
                return degrau
        return None

    def encontrar_degrau_mais_profundo(self, queda_pct: Decimal) -> Optional[Dict]:
        """
        Encontra o degrau MAIS PROFUNDO que foi ativado pela queda atual.

        Usado na lógica de "Largada a Frio" para comprar no degrau mais agressivo
        disponível na primeira execução.

        Args:
            queda_pct: Percentual de queda desde a SMA de referência

        Returns:
            Degrau mais profundo ativado ou None se nenhum foi ativado
        """
        degrau_mais_profundo = None

        for degrau in settings.DEGRAUS_COMPRA:
            if queda_pct >= Decimal(str(degrau['queda_percentual'])):
                # Como os degraus estão ordenados por queda crescente,
                # o último que passar na verificação é o mais profundo
                degrau_mais_profundo = degrau

        return degrau_mais_profundo

    def pode_comprar_degrau(self, nivel_degrau: int, degrau_config: Dict) -> tuple[bool, Optional[str]]:
        """
        Verifica se pode comprar no degrau usando COOLDOWN DUPLO:
        1. Cooldown GLOBAL: Tempo mínimo desde QUALQUER compra
        2. Cooldown POR DEGRAU: Tempo mínimo desde última compra NO MESMO DEGRAU

        Args:
            nivel_degrau: Nível do degrau (1, 2, 3, etc)
            degrau_config: Configuração do degrau (incluindo intervalo_horas)

        Returns:
            Tuple (pode_comprar, motivo_bloqueio):
                - pode_comprar: True se pode comprar, False caso contrário
                - motivo_bloqueio: String com motivo do bloqueio ou None se pode comprar
        """
        agora = datetime.now()

        # VERIFICAÇÃO 1: COOLDOWN GLOBAL (após qualquer compra)
        cooldown_global_minutos = settings.COOLDOWN_GLOBAL_APOS_COMPRA_MINUTOS

        timestamp_global_str = self.state.get_state('ultima_compra_global_ts')
        if timestamp_global_str:
            timestamp_ultima_compra_global = datetime.fromisoformat(timestamp_global_str)
            tempo_desde_ultima_compra = agora - timestamp_ultima_compra_global
            minutos_decorridos = tempo_desde_ultima_compra.total_seconds() / 60

            if minutos_decorridos < cooldown_global_minutos:
                minutos_restantes = int(cooldown_global_minutos - minutos_decorridos)
                motivo = f"cooldown_global:{minutos_restantes}min"
                logger.debug(f"🕒 Cooldown global ativo (faltam {minutos_restantes} min)")
                return (False, motivo)

        # VERIFICAÇÃO 2: COOLDOWN POR DEGRAU (intervalo específico do degrau)
        chave_degrau = f'ultima_compra_degrau_{nivel_degrau}_ts'
        timestamp_degrau_str = self.state.get_state(chave_degrau)

        if timestamp_degrau_str:
            ultima_compra_degrau = datetime.fromisoformat(timestamp_degrau_str)
            tempo_desde_compra_degrau = agora - ultima_compra_degrau
            intervalo_horas = Decimal(str(degrau_config['intervalo_horas']))
            horas_decorridas = Decimal(str(tempo_desde_compra_degrau.total_seconds() / 3600))

            if horas_decorridas < intervalo_horas:
                horas_restantes = float(intervalo_horas - horas_decorridas)
                motivo = f"cooldown_degrau:{horas_restantes:.1f}h"
                logger.debug(f"🕒 Degrau {nivel_degrau} em cooldown (faltam {horas_restantes:.1f}h)")
                return (False, motivo)

        # Passou em todas as verificações
        return (True, None)

    def registrar_compra_global(self, nivel_degrau: Optional[int] = None):
        """
        Registra timestamp da última compra (COOLDOWN GLOBAL)

        Atualiza o timestamp global que bloqueia TODAS as compras
        por um período configurável após cada operação de compra.

        Args:
            nivel_degrau: Nível do degrau (para registrar cooldown por degrau)
        """
        agora = datetime.now()
        timestamp_iso = agora.isoformat()

        # Registrar cooldown global
        self.state.set_state('ultima_compra_global_ts', timestamp_iso)
        logger.debug(f"🕒 Cooldown global ativado: {settings.COOLDOWN_GLOBAL_APOS_COMPRA_MINUTOS} minutos")

        # Registrar cooldown por degrau (se especificado)
        if nivel_degrau is not None:
            chave_degrau = f'ultima_compra_degrau_{nivel_degrau}_ts'
            self.state.set_state(chave_degrau, timestamp_iso)
            logger.debug(f"🕒 Cooldown degrau {nivel_degrau} ativado")

    def atualizar_preco_medio_compra(self, quantidade: Decimal, preco: Decimal):
        """
        Atualiza o preço médio de compra após nova compra

        Fórmula: novo_preço_médio = (valor_anterior + valor_nova_compra) / (qtd_anterior + qtd_nova)
        """
        valor_compra = quantidade * preco

        self.valor_total_investido += valor_compra
        self.quantidade_total_comprada += quantidade

        if self.quantidade_total_comprada > 0:
            self.preco_medio_compra = self.valor_total_investido / self.quantidade_total_comprada
            logger.info(f"📊 Preço médio atualizado: ${self.preco_medio_compra:.6f} ({self.quantidade_total_comprada:.1f} ADA)")
        else:
            self.preco_medio_compra = None

    def calcular_lucro_atual(self, preco_atual: Decimal) -> Optional[Decimal]:
        """
        Calcula lucro % baseado no preço médio de compra

        Returns:
            Lucro em % (positivo = lucro, negativo = prejuízo)
            None se não houver preço médio calculado
        """
        if self.preco_medio_compra is None or self.preco_medio_compra == 0:
            return None

        lucro_pct = ((preco_atual - self.preco_medio_compra) / self.preco_medio_compra) * Decimal('100')
        return lucro_pct

    def executar_compra(self, degrau: Dict, preco_atual: Decimal, saldo_usdt: Decimal):
        """Executa compra no degrau com validação rigorosa de reserva"""
        quantidade_ada = Decimal(str(degrau['quantidade_ada']))
        valor_ordem = quantidade_ada * preco_atual

        # VALIDAÇÃO RIGOROSA DE SALDO E RESERVA
        # Atualizar saldos no gestor de capital
        valor_posicao_ada = self.quantidade_total_comprada * preco_atual if self.quantidade_total_comprada > 0 else Decimal('0')
        self.gestao_capital.atualizar_saldos(saldo_usdt, valor_posicao_ada)

        # Verificar se pode comprar (valida reserva + saldo mínimo)
        pode, motivo = self.gestao_capital.pode_comprar(valor_ordem)

        if not pode:
            # NOTA: o log já foi feito dentro de gestao_capital.pode_comprar()
            # Não relogar para evitar duplicação
            return False

        # Verificar valor mínimo de ordem
        if valor_ordem < settings.VALOR_MINIMO_ORDEM:
            logger.warning(f"⚠️ Valor de ordem abaixo do mínimo: ${valor_ordem:.2f}")
            return False

        try:
            # Capturar saldos antes da compra
            saldos_antes = self.obter_saldos()
            preco_medio_antes = self.preco_medio_compra

            # Criar ordem de compra
            ordem = self.api.criar_ordem_mercado(
                simbolo='ADAUSDT',
                lado='BUY',
                quantidade=float(quantidade_ada)
            )

            if ordem and ordem.get('status') == 'FILLED':
                logger.operacao_compra(
                    par='ADA/USDT',
                    quantidade=float(quantidade_ada),
                    preco=float(preco_atual),
                    degrau=degrau['nivel'],
                    queda_pct=float(degrau['queda_percentual'])
                )

                # Registrar compra e ativar cooldown global + cooldown por degrau
                self.registrar_compra_global(nivel_degrau=degrau['nivel'])

                # Atualizar preço médio de compra
                self.atualizar_preco_medio_compra(quantidade_ada, preco_atual)

                # Capturar saldos depois da compra
                saldos_depois = self.obter_saldos()

                # SALVAR NO BANCO DE DADOS
                self.db.registrar_ordem({
                    'tipo': 'COMPRA',
                    'par': 'ADA/USDT',
                    'quantidade': quantidade_ada,
                    'preco': preco_atual,
                    'valor_total': valor_ordem,
                    'taxa': ordem.get('fills', [{}])[0].get('commission', 0) if ordem.get('fills') else 0,
                    'meta': f"degrau{degrau['nivel']}",
                    'preco_medio_antes': preco_medio_antes,
                    'preco_medio_depois': self.preco_medio_compra,
                    'saldo_ada_antes': saldos_antes['ada'],
                    'saldo_ada_depois': saldos_depois['ada'],
                    'saldo_usdt_antes': saldos_antes['usdt'],
                    'saldo_usdt_depois': saldos_depois['usdt'],
                    'order_id': ordem.get('orderId'),
                    'observacao': f"Compra degrau {degrau['nivel']} - Queda {degrau['queda_percentual']}%"
                })

                # Atualizar estado do bot no banco
                self.db.atualizar_estado_bot(
                    preco_medio=self.preco_medio_compra,
                    quantidade=self.quantidade_total_comprada
                )

                return True
            else:
                logger.error(f"❌ Erro ao executar compra: {ordem}")
                return False

        except Exception as e:
            logger.erro_api('executar_compra', str(e))
            return False

    def executar_compra_por_valor(self, valor_usdt: Decimal, motivo: str) -> bool:
        """Executa uma compra baseada em um valor em USDT."""
        preco_atual = self.obter_preco_atual()
        if not preco_atual:
            logger.error("❌ Não foi possível obter o preço atual para a compra por valor.")
            return False

        # Calcula a quantidade de ADA a comprar
        quantidade_ada = valor_usdt / preco_atual

        # Validação de valor mínimo da ordem
        if valor_usdt < settings.VALOR_MINIMO_ORDEM:
            logger.warning(f"⚠️ Valor de ordem abaixo do mínimo: ${valor_usdt:.2f}")
            return False

        try:
            saldos_antes = self.obter_saldos()
            preco_medio_antes = self.preco_medio_compra

            ordem = self.api.criar_ordem_mercado(
                simbolo='ADAUSDT',
                lado='BUY',
                quantidade=float(quantidade_ada)
            )

            if ordem and ordem.get('status') == 'FILLED':
                quantidade_real = Decimal(str(ordem.get('executedQty', '0')))
                valor_real = Decimal(str(ordem.get('cummulativeQuoteQty', '0')))

                logger.operacao_compra(
                    par='ADA/USDT',
                    quantidade=float(quantidade_real),
                    preco=float(preco_atual),
                    degrau=motivo.replace(" ", "_"),
                    queda_pct=0  # Não aplicável para este tipo de compra
                )

                self.registrar_compra_global()
                self.atualizar_preco_medio_compra(quantidade_real, preco_atual)

                saldos_depois = self.obter_saldos()

                self.db.registrar_ordem({
                    'tipo': 'COMPRA',
                    'par': 'ADA/USDT',
                    'quantidade': quantidade_real,
                    'preco': preco_atual,
                    'valor_total': valor_real,
                    'taxa': ordem.get('fills', [{}])[0].get('commission', 0) if ordem.get('fills') else 0,
                    'meta': motivo.replace(" ", "_"),
                    'preco_medio_antes': preco_medio_antes,
                    'preco_medio_depois': self.preco_medio_compra,
                    'saldo_ada_antes': saldos_antes['ada'],
                    'saldo_ada_depois': saldos_depois['ada'],
                    'saldo_usdt_antes': saldos_antes['usdt'],
                    'saldo_usdt_depois': saldos_depois['usdt'],
                    'order_id': ordem.get('orderId'),
                    'observacao': f"Compra de Oportunidade: {motivo}"
                })

                self.db.atualizar_estado_bot(
                    preco_medio=self.preco_medio_compra,
                    quantidade=self.quantidade_total_comprada
                )

                return True
            else:
                logger.error(f"❌ Erro ao executar compra por valor: {ordem}")
                return False
        except Exception as e:
            logger.erro_api('executar_compra_por_valor', str(e))
            return False

    def encontrar_meta_ativa(self, lucro_pct: Decimal, saldo_ada: Decimal, preco_atual: Decimal) -> Optional[Dict]:
        """
        Encontra meta de venda correspondente ao lucro atual

        ESTRATÉGIA AVANÇADA COM ZONAS DE SEGURANÇA:

        1. Atualizar High-Water Mark se lucro atual é maior
        2. PRIORIDADE 1: Verificar METAS FIXAS (18%, 11%, 6%)
           - Se atingida: executar venda principal e RESETAR estado
        3. PRIORIDADE 2: Verificar ZONAS DE SEGURANÇA (vendas de proteção)
           - Verificar se high_water_mark ultrapassou gatilho
           - Verificar se lucro atual caiu (reversão detectada)
           - Executar venda de segurança parcial
        4. PRIORIDADE 3: Sistema ADAPTATIVO (3-6%)

        REGRA CRÍTICA: Só vende se houver LUCRO (nunca vende com prejuízo)
        """
        if lucro_pct <= 0:
            return None  # Sem lucro, não vende

        # ═══════════════════════════════════════════════════════════════════
        # ATUALIZAR HIGH-WATER MARK
        # ═══════════════════════════════════════════════════════════════════
        if lucro_pct > self.high_water_mark_profit:
            self.high_water_mark_profit = lucro_pct
            logger.debug(f"📊 High-Water Mark atualizado: {self.high_water_mark_profit:.2f}%")

        # ═══════════════════════════════════════════════════════════════════
        # PRIORIDADE 1: Verificar METAS FIXAS em ordem DECRESCENTE
        # ═══════════════════════════════════════════════════════════════════
        # Ordenar metas por lucro percentual (maior para menor)
        metas_ordenadas = sorted(
            settings.METAS_VENDA,
            key=lambda x: x['lucro_percentual'],
            reverse=True
        )

        # Verificar se alguma meta fixa foi atingida
        for meta in metas_ordenadas:
            if lucro_pct >= Decimal(str(meta['lucro_percentual'])):
                logger.debug(f"✅ Meta fixa {meta['meta']} atingida ({meta['lucro_percentual']}%)")

                # IMPORTANTE: Resetar estado para próxima escalada
                self.high_water_mark_profit = Decimal('0')
                self.zonas_de_seguranca_acionadas.clear()
                self.capital_para_recompra.clear()

                return meta

        # ═══════════════════════════════════════════════════════════════════
        # PRIORIDADE 2: Verificar ZONAS DE SEGURANÇA (vendas progressivas)
        # ═══════════════════════════════════════════════════════════════════
        # SISTEMA DE DOIS GATILHOS:
        # 1. gatilho_ativacao_lucro_pct: "arma" a zona quando high-water mark ultrapassa
        # 2. gatilho_venda_reversao_pct: dispara a venda quando lucro cai este valor desde o pico
        if hasattr(settings, 'VENDAS_DE_SEGURANCA') and settings.VENDAS_DE_SEGURANCA:
            for zona in settings.VENDAS_DE_SEGURANCA:
                nome_zona = zona['nome']

                # GATILHO 1: Ativação - High-water mark deve ultrapassar este valor
                gatilho_ativacao_pct = Decimal(str(zona['gatilho_ativacao_lucro_pct']))

                # GATILHO 2: Reversão - Quanto deve cair desde o pico para vender
                gatilho_reversao_pct = Decimal(str(zona['gatilho_venda_reversao_pct']))

                # Verificar se zona já foi acionada
                if nome_zona in self.zonas_de_seguranca_acionadas:
                    continue

                # PASSO 1: Verificar se high-water mark "armou" o gatilho da zona
                if self.high_water_mark_profit < gatilho_ativacao_pct:
                    continue

                # PASSO 2: Calcular reversão desde high-water mark
                queda_desde_pico = self.high_water_mark_profit - lucro_pct

                # PASSO 3: Calcular gatilho de venda baseado na reversão configurada
                gatilho_venda = self.high_water_mark_profit - gatilho_reversao_pct

                # PASSO 4: Verificar se lucro atual caiu abaixo do gatilho de venda
                if lucro_pct <= gatilho_venda:
                    # Calcular valor da ordem
                    percentual_venda = Decimal(str(zona['percentual_venda_posicao'])) / Decimal('100')
                    quantidade_venda = saldo_ada * percentual_venda

                    # Arredondar para 0.1 (step size ADA)
                    quantidade_venda = (quantidade_venda * Decimal('10')).quantize(
                        Decimal('1'), rounding='ROUND_DOWN'
                    ) / Decimal('10')

                    valor_ordem = quantidade_venda * preco_atual

                    # Validar valor mínimo
                    if valor_ordem >= settings.VALOR_MINIMO_ORDEM and quantidade_venda >= Decimal('1'):
                        logger.info(f"🛡️ ZONA DE SEGURANÇA '{nome_zona}' ATIVADA!")
                        logger.info(f"   📊 High-Water Mark: {self.high_water_mark_profit:.2f}%")
                        logger.info(f"   🎯 Gatilho ativação: {gatilho_ativacao_pct:.2f}% (armada ✓)")
                        logger.info(f"   📉 Lucro atual: {lucro_pct:.2f}%")
                        logger.info(f"   🎯 Gatilho venda: {gatilho_venda:.2f}% (atingido ✓)")
                        logger.info(f"   📊 Queda desde pico: {queda_desde_pico:.2f}%")
                        logger.info(f"   💰 Venda de segurança: {float(quantidade_venda):.1f} ADA (${valor_ordem:.2f})")

                        return {
                            'meta': f'seguranca_{nome_zona}',
                            'lucro_percentual': float(lucro_pct),
                            'percentual_venda': zona['percentual_venda_posicao'],
                            'zona_seguranca': zona,  # Incluir dados completos da zona
                            'tipo_venda': 'seguranca'
                        }

        # ═══════════════════════════════════════════════════════════════════
        # NOTA: Sistema adaptativo REMOVIDO
        # ═══════════════════════════════════════════════════════════════════
        # A lógica de "meta adaptativa" foi completamente removida para evitar
        # over-trading. Agora o bot opera APENAS com:
        # 1. Metas fixas (prioridade máxima)
        # 2. Zonas de segurança baseadas em reversão (proteção inteligente)
        #
        # Esta mudança garante que pequenas flutuações de mercado não causem
        # vendas repetitivas que impedem o lucro de atingir as metas principais.

        return None  # Nenhuma meta atingida

    def executar_venda(self, meta: Dict, preco_atual: Decimal, saldo_ada: Decimal):
        """
        Executa venda na meta

        PROTEÇÃO: Só executa se houver lucro confirmado

        VENDAS DE SEGURANÇA:
        - Se for venda de segurança, guarda capital para recompra futura
        - Marca zona como acionada para não repetir venda
        """
        # Verificar lucro novamente antes de vender
        lucro_pct = self.calcular_lucro_atual(preco_atual)

        if lucro_pct is None or lucro_pct <= 0:
            logger.warning(f"🛡️ VENDA BLOQUEADA: Sem lucro ({lucro_pct:.2f}% - aguardando lucro)")
            return False

        percentual_venda = Decimal(str(meta['percentual_venda'])) / Decimal('100')
        quantidade_venda = saldo_ada * percentual_venda

        # Arredondar para 0.1 (step size ADA na Binance)
        quantidade_venda = (quantidade_venda * Decimal('10')).quantize(Decimal('1'), rounding='ROUND_DOWN') / Decimal('10')

        if quantidade_venda < Decimal('1'):  # Mínimo 1 ADA
            logger.warning(f"⚠️ Quantidade ADA abaixo do mínimo: {quantidade_venda} ADA")
            return False

        valor_ordem = quantidade_venda * preco_atual

        # Verificar valor mínimo de ordem ($5.00)
        if valor_ordem < settings.VALOR_MINIMO_ORDEM:
            logger.warning(f"⚠️ Valor de ordem abaixo do mínimo: ${valor_ordem:.2f}")
            return False

        # Verificar se é venda de segurança
        eh_venda_seguranca = meta.get('tipo_venda') == 'seguranca'
        zona_seguranca = meta.get('zona_seguranca')

        try:
            # Capturar saldos antes da venda
            saldos_antes = self.obter_saldos()
            preco_medio_antes = self.preco_medio_compra

            # Criar ordem de venda
            ordem = self.api.criar_ordem_mercado(
                simbolo='ADAUSDT',
                lado='SELL',
                quantidade=float(quantidade_venda)
            )

            if ordem and ordem.get('status') == 'FILLED':
                # Calcular lucro real da venda
                valor_medio_compra = quantidade_venda * self.preco_medio_compra
                lucro_real = valor_ordem - valor_medio_compra

                logger.operacao_venda(
                    par='ADA/USDT',
                    quantidade=float(quantidade_venda),
                    preco=float(preco_atual),
                    meta=meta['meta'],
                    lucro_pct=float(lucro_pct),
                    lucro_usd=float(lucro_real)
                )

                # ═══════════════════════════════════════════════════════════════════
                # SE FOR VENDA DE SEGURANÇA: Guardar capital para recompra
                # ═══════════════════════════════════════════════════════════════════
                if eh_venda_seguranca and zona_seguranca:
                    nome_zona = zona_seguranca['nome']

                    # Guardar capital obtido e high-water mark atual
                    self.capital_para_recompra[nome_zona] = {
                        'capital_usdt': valor_ordem,  # Capital em USDT obtido da venda
                        'high_water_mark': self.high_water_mark_profit,  # Pico de lucro registrado
                        'gatilho_recompra_pct': Decimal(str(zona_seguranca['gatilho_recompra_drop_pct'])),
                        'quantidade_vendida': quantidade_venda,
                        'preco_venda': preco_atual
                    }

                    # Marcar zona como acionada
                    self.zonas_de_seguranca_acionadas.add(nome_zona)

                    logger.info(f"💰 Capital reservado para recompra: ${valor_ordem:.2f} USDT")
                    logger.info(f"   📌 Zona '{nome_zona}' marcada como acionada")
                    logger.info(f"   🔄 Recompra será ativada se lucro cair {zona_seguranca['gatilho_recompra_drop_pct']}% desde o pico")

                # Ajustar tracking após venda (reduzir quantidade total)
                self.quantidade_total_comprada -= quantidade_venda
                self.valor_total_investido -= valor_medio_compra

                # RECALCULAR PREÇO MÉDIO após ajustar valores
                if self.quantidade_total_comprada > 0:
                    self.preco_medio_compra = self.valor_total_investido / self.quantidade_total_comprada
                    logger.info(f"📊 Posição atualizada: {self.quantidade_total_comprada:.1f} ADA (preço médio: ${self.preco_medio_compra:.6f})")
                else:
                    self.preco_medio_compra = None  # Zerou posição
                    logger.info(f"📊 Posição zerada - todas as ADA vendidas!")

                # Capturar saldos depois da venda
                saldos_depois = self.obter_saldos()

                # SALVAR NO BANCO DE DADOS
                observacao = f"Venda {meta['meta']} - Lucro {lucro_pct:.2f}%"
                if eh_venda_seguranca:
                    observacao = f"Venda de Segurança '{zona_seguranca['nome']}' - Lucro {lucro_pct:.2f}% (capital reservado para recompra)"

                self.db.registrar_ordem({
                    'tipo': 'VENDA',
                    'par': 'ADA/USDT',
                    'quantidade': quantidade_venda,
                    'preco': preco_atual,
                    'valor_total': valor_ordem,
                    'taxa': ordem.get('fills', [{}])[0].get('commission', 0) if ordem.get('fills') else 0,
                    'meta': meta['meta'],
                    'lucro_percentual': lucro_pct,
                    'lucro_usdt': lucro_real,
                    'preco_medio_antes': preco_medio_antes,
                    'preco_medio_depois': self.preco_medio_compra,
                    'saldo_ada_antes': saldos_antes['ada'],
                    'saldo_ada_depois': saldos_depois['ada'],
                    'saldo_usdt_antes': saldos_antes['usdt'],
                    'saldo_usdt_depois': saldos_depois['usdt'],
                    'order_id': ordem.get('orderId'),
                    'observacao': observacao
                })

                # Atualizar estado do bot no banco
                self.db.atualizar_estado_bot(
                    preco_medio=self.preco_medio_compra,
                    quantidade=self.quantidade_total_comprada
                )

                return True
            else:
                logger.error(f"❌ Erro ao executar venda: {ordem}")
                return False

        except Exception as e:
            logger.erro_api('executar_venda', str(e))
            return False

    def verificar_recompra_de_seguranca(self, preco_atual: Decimal):
        """
        Verifica se deve executar recompra após venda de segurança.

        LÓGICA:
        1. Para cada zona com capital reservado
        2. Calcular lucro atual (se houver posição)
        3. Se lucro caiu o suficiente desde high-water mark, executar recompra
        4. Limpar capital reservado após recompra

        Args:
            preco_atual: Preço atual de ADA/USDT
        """
        if not self.capital_para_recompra:
            return  # Nenhuma recompra pendente

        # Calcular lucro atual (se houver posição)
        lucro_atual = self.calcular_lucro_atual(preco_atual)

        if lucro_atual is None:
            # Sem posição - não faz sentido recomprar sem preço médio
            return

        zonas_para_remover = []

        for nome_zona, dados_zona in self.capital_para_recompra.items():
            high_mark = dados_zona['high_water_mark']
            gatilho_recompra_pct = dados_zona['gatilho_recompra_pct']
            capital_usdt = dados_zona['capital_usdt']

            # Calcular gatilho de recompra
            gatilho_recompra = high_mark - gatilho_recompra_pct

            # Verificar se lucro atual caiu abaixo do gatilho
            if lucro_atual <= gatilho_recompra:
                logger.info(f"🔄 GATILHO DE RECOMPRA ATIVADO - Zona '{nome_zona}'")
                logger.info(f"   📊 High-Water Mark: {high_mark:.2f}%")
                logger.info(f"   📉 Lucro atual: {lucro_atual:.2f}%")
                logger.info(f"   🎯 Gatilho: {gatilho_recompra:.2f}% (queda de {gatilho_recompra_pct:.2f}%)")
                logger.info(f"   💰 Capital disponível: ${capital_usdt:.2f} USDT")

                # Calcular quantidade de ADA a comprar
                quantidade_ada = capital_usdt / preco_atual

                # Arredondar para 0.1 (step size ADA)
                quantidade_ada = (quantidade_ada * Decimal('10')).quantize(
                    Decimal('1'), rounding='ROUND_DOWN'
                ) / Decimal('10')

                valor_ordem = quantidade_ada * preco_atual

                # Validar valor mínimo
                if valor_ordem >= settings.VALOR_MINIMO_ORDEM and quantidade_ada >= Decimal('1'):
                    # Executar recompra
                    sucesso = self._executar_recompra(
                        nome_zona=nome_zona,
                        quantidade_ada=quantidade_ada,
                        preco_atual=preco_atual,
                        capital_usado=valor_ordem,
                        dados_zona=dados_zona
                    )

                    if sucesso:
                        # Marcar zona para remoção
                        zonas_para_remover.append(nome_zona)
                else:
                    logger.warning(f"⚠️ Recompra ignorada - valor abaixo do mínimo: ${valor_ordem:.2f}")
                    zonas_para_remover.append(nome_zona)

        # Remover zonas que foram recompradas
        for nome_zona in zonas_para_remover:
            del self.capital_para_recompra[nome_zona]
            logger.debug(f"✅ Capital de zona '{nome_zona}' removido após recompra")

    def _executar_recompra(self, nome_zona: str, quantidade_ada: Decimal, preco_atual: Decimal,
                          capital_usado: Decimal, dados_zona: Dict) -> bool:
        """
        Executa ordem de recompra após venda de segurança.

        Args:
            nome_zona: Nome da zona de segurança
            quantidade_ada: Quantidade de ADA a comprar
            preco_atual: Preço atual de ADA
            capital_usado: Capital USDT a ser usado
            dados_zona: Dados da zona (high_mark, preco_venda, etc)

        Returns:
            True se recompra foi executada com sucesso, False caso contrário
        """
        try:
            # Capturar saldos antes da recompra
            saldos_antes = self.obter_saldos()
            preco_medio_antes = self.preco_medio_compra

            # Criar ordem de compra
            ordem = self.api.criar_ordem_mercado(
                simbolo='ADAUSDT',
                lado='BUY',
                quantidade=float(quantidade_ada)
            )

            if ordem and ordem.get('status') == 'FILLED':
                # Comparar com venda original
                preco_venda_original = dados_zona['preco_venda']
                diferenca_preco = ((preco_atual - preco_venda_original) / preco_venda_original) * Decimal('100')

                logger.operacao_compra(
                    par='ADA/USDT',
                    quantidade=float(quantidade_ada),
                    preco=float(preco_atual),
                    degrau=f"recompra_{nome_zona}",
                    queda_pct=float(diferenca_preco)
                )

                logger.info(f"✅ RECOMPRA DE SEGURANÇA EXECUTADA!")
                logger.info(f"   📦 Comprado: {float(quantidade_ada):.1f} ADA por ${preco_atual:.6f}")
                logger.info(f"   💵 Custo: ${capital_usado:.2f} USDT")
                logger.info(f"   📊 Preço venda original: ${preco_venda_original:.6f}")
                logger.info(f"   📈 Diferença: {diferenca_preco:+.2f}%")

                # Atualizar preço médio de compra
                self.atualizar_preco_medio_compra(quantidade_ada, preco_atual)

                # Capturar saldos depois da recompra
                saldos_depois = self.obter_saldos()

                # SALVAR NO BANCO DE DADOS
                self.db.registrar_ordem({
                    'tipo': 'COMPRA',
                    'par': 'ADA/USDT',
                    'quantidade': quantidade_ada,
                    'preco': preco_atual,
                    'valor_total': capital_usado,
                    'taxa': ordem.get('fills', [{}])[0].get('commission', 0) if ordem.get('fills') else 0,
                    'meta': f'recompra_seguranca_{nome_zona}',
                    'preco_medio_antes': preco_medio_antes,
                    'preco_medio_depois': self.preco_medio_compra,
                    'saldo_ada_antes': saldos_antes['ada'],
                    'saldo_ada_depois': saldos_depois['ada'],
                    'saldo_usdt_antes': saldos_antes['usdt'],
                    'saldo_usdt_depois': saldos_depois['usdt'],
                    'order_id': ordem.get('orderId'),
                    'observacao': f"Recompra de Segurança zona '{nome_zona}' - Diferença {diferenca_preco:+.2f}% vs venda original"
                })

                # Atualizar estado do bot no banco
                self.db.atualizar_estado_bot(
                    preco_medio=self.preco_medio_compra,
                    quantidade=self.quantidade_total_comprada
                )

                return True
            else:
                logger.error(f"❌ Erro ao executar recompra: {ordem}")
                return False

        except Exception as e:
            logger.erro_api('_executar_recompra', str(e))
            return False

    def _verificar_aportes_brl(self):
        """Verifica novos aportes em BRL e os converte para USDT."""
        try:
            logger.info("🔍 Verificando possíveis aportes em BRL...")
            resultado = self.gerenciador_aportes.processar_aporte_automatico()

            if resultado.get('sucesso'):
                logger.info(f"✅ Aporte processado: {resultado.get('mensagem')}")
                # Forçar a sincronização de saldos para atualizar o capital do bot
                logger.info("🔄 Forçando a sincronização de saldos após o aporte...")
                self._sincronizar_saldos_binance()
            else:
                # Logar apenas se a mensagem não for de saldo insuficiente, para evitar spam
                if "insuficiente" not in resultado.get('mensagem', ""):
                    logger.info(f"ℹ️ Nenhum novo aporte detectado. {resultado.get('mensagem')}")

        except Exception as e:
            logger.error(f"❌ Erro ao verificar aportes BRL: {e}")


    def fazer_backup_periodico(self):
        """Faz backup do banco de dados periodicamente (1x por dia)"""
        agora = datetime.now()
        intervalo = timedelta(days=1)

        if agora - self.ultimo_backup >= intervalo:
            try:
                logger.info("💾 Criando backup do banco de dados...")
                backup_path = self.db.fazer_backup()
                logger.info(f"✅ Backup criado: {backup_path}")
                self.ultimo_backup = agora
            except Exception as e:
                logger.error(f"❌ Erro ao criar backup: {e}")

    def _calcular_volatilidade_mercado(self, preco_atual: Decimal) -> tuple[Decimal, str]:
        """
        Calcula volatilidade do mercado na última hora.

        Returns:
            Tuple (variacao_pct, classificacao)
            classificacao: 'Alta', 'Média', 'Baixa'
        """
        if len(self.historico_precos) < 2:
            return (Decimal('0'), 'Baixa')

        # Pegar preços da última hora (12 preços a cada 5 segundos = últimos 60 segundos)
        precos_recentes = list(self.historico_precos)[-12:]

        if len(precos_recentes) < 2:
            return (Decimal('0'), 'Baixa')

        preco_min = min(precos_recentes)
        preco_max = max(precos_recentes)

        if preco_min == 0:
            return (Decimal('0'), 'Baixa')

        variacao_pct = ((preco_max - preco_min) / preco_min) * Decimal('100')

        # Classificar volatilidade
        if variacao_pct >= Decimal('2.0'):
            classificacao = 'Alta'
        elif variacao_pct >= Decimal('0.5'):
            classificacao = 'Média'
        else:
            classificacao = 'Baixa'

        return (variacao_pct, classificacao)

    def _obter_proxima_meta(self, lucro_atual_pct: Optional[Decimal]) -> tuple[str, Decimal]:
        """
        Identifica a próxima meta de venda fixa a ser atingida.

        Args:
            lucro_atual_pct: Lucro percentual atual (ou None se sem posição)

        Returns:
            Tuple (nome_meta, distancia_pct)
            Ex: ("Venda Fixa 1 (6.0%)", Decimal('2.5'))
        """
        from config.settings import settings

        if lucro_atual_pct is None:
            # Sem posição - próxima meta é a primeira
            primeira_meta = min(settings.METAS_VENDA, key=lambda x: x['lucro_percentual'])
            meta_pct = Decimal(str(primeira_meta['lucro_percentual']))
            return (f"{primeira_meta['meta']} ({meta_pct}%)", meta_pct)

        # Com posição - encontrar próxima meta não atingida
        metas_ordenadas = sorted(settings.METAS_VENDA, key=lambda x: x['lucro_percentual'])

        for meta in metas_ordenadas:
            meta_pct = Decimal(str(meta['lucro_percentual']))
            if lucro_atual_pct < meta_pct:
                distancia = meta_pct - lucro_atual_pct
                return (f"{meta['meta']} ({meta_pct}%)", distancia)

        # Todas as metas já atingidas
        ultima_meta = max(settings.METAS_VENDA, key=lambda x: x['lucro_percentual'])
        meta_pct = Decimal(str(ultima_meta['lucro_percentual']))
        return (f"{ultima_meta['meta']} ({meta_pct}%)", Decimal('0'))

    def _obter_estado_bot(self) -> str:
        """
        Retorna string descritiva do estado atual do bot.

        Returns:
            String com estado atual (ex: "Acumulando", "Aguardando Meta", etc.)
        """
        # Verificar se tem capital reservado para recompra
        if self.capital_para_recompra:
            zonas = list(self.capital_para_recompra.keys())
            return f"Aguardando Recompra ({', '.join(zonas)})"

        # Verificar se está aguardando saldo
        if self.estado_bot == "AGUARDANDO_SALDO":
            return "Sem Saldo | Aguardando Venda/Aporte"

        # Verificar se tem posição
        if self.quantidade_total_comprada > 0:
            # Com posição - aguardando meta
            return "Acumulando | Aguardando Meta de Lucro"
        else:
            # Sem posição - aguardando compra
            return "Sem Posição | Aguardando Degrau"

    def _formatar_tempo_relativo(self, timestamp_str: str) -> str:
        """
        Converte timestamp ISO para formato relativo (ex: "há 3h", "há 15m").

        Args:
            timestamp_str: Timestamp no formato ISO

        Returns:
            String com tempo relativo
        """
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            agora = datetime.now()
            delta = agora - timestamp

            # Calcular componentes
            dias = delta.days
            horas = delta.seconds // 3600
            minutos = (delta.seconds % 3600) // 60

            if dias > 0:
                return f"há {dias}d{horas}h"
            elif horas > 0:
                return f"há {horas}h"
            elif minutos > 0:
                return f"há {minutos}m"
            else:
                return "agora"

        except Exception:
            return "N/A"

    def logar_painel_de_status(self, preco_atual: Decimal, saldos: Dict):
        """
        Loga painel avançado de status do bot com informações táticas.

        O painel é construído como uma única string para preservar formatação.

        Args:
            preco_atual: Preço atual de ADA
            saldos: Dicionário com saldos USDT e ADA
        """
        try:
            # Calcular métricas básicas
            valor_posicao = self.quantidade_total_comprada * preco_atual if self.quantidade_total_comprada > 0 else Decimal('0')
            self.gestao_capital.atualizar_saldos(saldos['usdt'], valor_posicao)
            capital_total = self.gestao_capital.calcular_capital_total()

            # Calcular lucro atual
            lucro_pct = self.calcular_lucro_atual(preco_atual) if self.preco_medio_compra else None
            if lucro_pct and self.quantidade_total_comprada > 0:
                lucro_usdt = (preco_atual - self.preco_medio_compra) * self.quantidade_total_comprada
            else:
                lucro_usdt = Decimal('0')

            # Calcular alocação de capital
            if capital_total > 0:
                pct_ada = (valor_posicao / capital_total) * Decimal('100')
                pct_usdt = Decimal('100') - pct_ada
            else:
                pct_ada = Decimal('0')
                pct_usdt = Decimal('100')

            # Obter volatilidade
            volatilidade_pct, volatilidade_classe = self._calcular_volatilidade_mercado(preco_atual)

            # Obter última compra e venda
            ultima_compra = self.db.obter_ultima_ordem('COMPRA')
            ultima_venda = self.db.obter_ultima_ordem('VENDA')

            # Obter próxima meta
            nome_meta, distancia_meta = self._obter_proxima_meta(lucro_pct)

            # Obter estado do bot
            estado = self._obter_estado_bot()

            # Calcular uptime
            agora = datetime.now()
            uptime_delta = agora - self.inicio_bot
            uptime_horas = int(uptime_delta.total_seconds() / 3600)
            uptime_minutos = int((uptime_delta.total_seconds() % 3600) / 60)
            hora_atual = agora.strftime('%H:%M:%S')

            # Formatar uptime
            uptime_str = f"{uptime_horas}h {uptime_minutos}m"

            # ═══════════════════════════════════════════════════════════════════
            # Construir linha de POSIÇÃO
            # ═══════════════════════════════════════════════════════════════════
            if self.quantidade_total_comprada > 0 and self.preco_medio_compra:
                linha_posicao = f"│ 💼 POSIÇÃO │ {self.quantidade_total_comprada:.1f} ADA @ ${self.preco_medio_compra:.4f} | L/P: {lucro_pct:+.2f}% (${lucro_usdt:+.2f})      │"
            else:
                linha_posicao = "│ 💼 POSIÇÃO │ Sem posição aberta                           │"

            # ═══════════════════════════════════════════════════════════════════
            # Construir linha de COMPRA
            # ═══════════════════════════════════════════════════════════════════
            if ultima_compra:
                tempo_compra = self._formatar_tempo_relativo(ultima_compra['timestamp'])
                qtd_compra = float(ultima_compra['quantidade'])
                preco_compra = float(ultima_compra['preco'])
                valor_compra = float(ultima_compra['valor_total'])
                linha_compra = f"│ 🟢 COMPRA │ {qtd_compra:.1f} ADA @ ${preco_compra:.4f} ({tempo_compra}) │ Total: ${valor_compra:.2f}       │"
            else:
                linha_compra = "│ 🟢 COMPRA │ Nenhuma compra registrada                    │"

            # ═══════════════════════════════════════════════════════════════════
            # Construir linha de VENDA (com encurtamento de nome)
            # ═══════════════════════════════════════════════════════════════════
            if ultima_venda:
                tempo_venda = self._formatar_tempo_relativo(ultima_venda['timestamp'])
                qtd_venda = float(ultima_venda['quantidade'])
                preco_venda = float(ultima_venda['preco'])
                lucro_venda = float(ultima_venda.get('lucro_usdt', 0))
                meta_venda = ultima_venda.get('meta', 'N/A')

                # Encurtar nome da meta de segurança
                # De: seguranca_Seguranca_Pre-Meta1-A
                # Para: Seg: Pre-Meta1-A
                if meta_venda.startswith('seguranca_'):
                    # Remover prefixo 'seguranca_' e 'Seguranca_'
                    meta_venda_curta = meta_venda.replace('seguranca_', '')
                    meta_venda_curta = meta_venda_curta.replace('Seguranca_', '')
                    meta_venda_curta = f"Seg: {meta_venda_curta}"
                else:
                    meta_venda_curta = meta_venda

                linha_venda = f"│ 🔴 VENDA  │ {qtd_venda:.1f} ADA @ ${preco_venda:.4f} ({tempo_venda}) │ Lucro: ${lucro_venda:.2f} ({meta_venda_curta})│"
            else:
                linha_venda = "│ 🔴 VENDA  │ Nenhuma venda registrada                     │"

            # ═══════════════════════════════════════════════════════════════════
            # Montar painel como UMA ÚNICA STRING
            # ═══════════════════════════════════════════════════════════════════
            painel = f"""
┌─ 📊 BOT STATUS ──────────────── {hora_atual} | Uptime: {uptime_str} ─┐
│ 📈 MERCADO │ ${preco_atual:.4f} │ Volatilidade (1h): {volatilidade_pct:+.2f}% ({volatilidade_classe})    │
{linha_posicao}
│ 💰 CAPITAL │ Total: ${capital_total:.2f} │ Alocação: [{pct_ada:.0f}% ADA|{pct_usdt:.0f}% USDT] │
├─ ÚLTIMAS OPERAÇÕES ────────────────────────────────────────┤
{linha_compra}
{linha_venda}
├─ ESTRATÉGIA ATUAL ─────────────────────────────────────────┤
│ 🎯 PRÓXIMA META │ {nome_meta:20s} │ Faltam: {distancia_meta:+.2f}%                 │
│ 🧠 ESTADO       │ {estado:50s} │
└────────────────────────────────────────────────────────────┘
"""

            # Logar como uma única string (preserva formatação)
            logger.info(painel)

        except Exception as e:
            logger.error(f"❌ Erro ao gerar painel de status: {e}")

    def loop_principal(self):
        """Loop principal do bot"""
        logger.banner("🤖 BOT DE TRADING INICIADO")
        logger.info(f"Par: {settings.PAR_PRINCIPAL}")
        logger.info(f"Ambiente: {settings.AMBIENTE}")
        logger.info(f"Capital inicial: ${settings.CAPITAL_INICIAL}")

        # Verificar conexão
        if not self.api.verificar_conexao():
            logger.error("❌ Não foi possível conectar à API Binance")
            return

        logger.info("✅ Conectado à Binance")

        # CRÍTICO: Sincronizar saldo real da Binance com backup local
        # Isso garante que divergências (compras/vendas manuais) sejam detectadas
        self._sincronizar_saldos_binance()

        # Calcular SMA de referência (4 semanas)
        logger.info("📊 Calculando SMA de referência (4 semanas)...")
        self.atualizar_sma()

        if not self.sma_referencia:
            logger.error("❌ Não foi possível calcular SMA. Bot não pode operar.")
            return

        # Obter preço inicial
        preco_inicial = self.obter_preco_atual()
        if preco_inicial:
            logger.info(f"📊 Preço inicial ADA: ${preco_inicial:.6f}")
            queda_inicial = self.calcular_queda_percentual(preco_inicial)
            if queda_inicial is not None:
                logger.info(f"📉 Distância da SMA: {queda_inicial:.2f}%")

        self.rodando = True
        contador_ciclos = 0

        try:
            while self.rodando:
                contador_ciclos += 1

                # Obter preço atual
                preco_atual = self.obter_preco_atual()
                if not preco_atual:
                    logger.warning("⚠️ Não foi possível obter preço, aguardando...")
                    time.sleep(10)
                    continue

                # Atualizar SMA periodicamente (a cada 1 hora)
                self.atualizar_sma()

                # Calcular queda desde SMA
                queda_pct = self.calcular_queda_percentual(preco_atual)

                # Log a cada 10 ciclos (aproximadamente 1 minuto)
                if contador_ciclos % 10 == 0:
                    if queda_pct and self.sma_referencia:
                        logger.info(f"📊 Preço: ${preco_atual:.6f} | SMA 4sem: ${self.sma_referencia:.6f} | Distância: {queda_pct:.2f}%")
                    else:
                        logger.info(f"📊 Preço: ${preco_atual:.6f}")

                # Obter saldos atuais
                saldos = self.obter_saldos()

                # ═══════════════════════════════════════════════════════════════════
                # VERIFICAÇÃO DE SALDO DISPONÍVEL (Modo "Aguardando Saldo")
                # ═══════════════════════════════════════════════════════════════════
                # Calcular saldo disponível considerando reserva
                valor_posicao = self.quantidade_total_comprada * preco_atual if self.quantidade_total_comprada > 0 else Decimal('0')

                # Usar GestaoCapital para calcular reserva e capital disponível
                self.gestao_capital.atualizar_saldos(saldos['usdt'], valor_posicao)
                reserva = self.gestao_capital.calcular_reserva_obrigatoria()
                capital_total = self.gestao_capital.calcular_capital_total()
                saldo_disponivel = self.gestao_capital.calcular_capital_disponivel()
                valor_minimo_operar = Decimal('10.00')  # Mínimo para tentar compras

                if saldo_disponivel < valor_minimo_operar:
                    # SEM SALDO SUFICIENTE - Entrar em modo "Aguardando Saldo"
                    if self.estado_bot != "AGUARDANDO_SALDO":
                        self.estado_bot = "AGUARDANDO_SALDO"
                        logger.warning("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                        logger.warning("⏸️  BOT EM MODO 'AGUARDANDO SALDO'")
                        logger.warning("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                        logger.warning(f"   💰 Saldo disponível: ${saldo_disponivel:.2f}")
                        logger.warning(f"   ⚠️  Mínimo necessário: ${valor_minimo_operar:.2f}")
                        logger.warning(f"   🛡️  Reserva protegida: ${reserva:.2f}")
                        logger.warning("")
                        logger.warning("   📌 Bot pausou verificações de degraus")
                        logger.warning("   📌 Aguardando venda ou novo aporte para retomar")
                        logger.warning("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

                    # NÃO verificar degraus de compra - pular para lógica de venda
                    # (Vendas ainda são permitidas para liberar saldo)
                else:
                    # TEM SALDO SUFICIENTE - Sair de modo "Aguardando Saldo" se estava nele
                    if self.estado_bot == "AGUARDANDO_SALDO":
                        self.estado_bot = "OPERANDO"
                        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                        logger.info("✅ SALDO RESTAURADO - Bot retomando operações")
                        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                        logger.info(f"   💰 Saldo disponível: ${saldo_disponivel:.2f}")
                        logger.info(f"   🛡️  Reserva mantida: ${reserva:.2f}")
                        logger.info("")
                        logger.info("   ✅ Verificações de degraus reativadas")
                        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

                # LÓGICA DE COMPRA (só executa se estado == "OPERANDO")
                # ═══════════════════════════════════════════════════════════════════
                if self.estado_bot == "OPERANDO" and queda_pct and queda_pct > Decimal('0.5'):
                    # 🛡️ GUARDIÃO DE GESTÃO DE RISCO 🛡️
                    # Verifica a exposição antes de qualquer tentativa de compra
                    alocacao_atual_ada = self.gestao_capital.get_alocacao_percentual_ada()
                    limite_exposicao = Decimal(str(settings.GESTAO_DE_RISCO['exposicao_maxima_percentual_capital']))

                    if alocacao_atual_ada > limite_exposicao:
                        if not self.notificou_exposicao_maxima:
                            logger.warning("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                            logger.warning(f"🛡️ GUARDIÃO ATIVADO: Exposição máxima de {limite_exposicao}% atingida.")
                            logger.warning(f"   Alocação atual em ADA: {alocacao_atual_ada:.1f}%")
                            logger.warning("   Compras normais suspensas. Verificando camadas de oportunidade extrema...")
                            logger.warning("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                            self.notificou_exposicao_maxima = True

                        # Lógica de Compras em Camadas para Oportunidades Extremas
                        oportunidades_usadas = self.state.get_state('oportunidades_extremas_usadas', default=[])
                        camadas_oportunidade = settings.GESTAO_DE_RISCO['compras_de_oportunidade_extrema']

                        for camada in camadas_oportunidade:
                            preco_alvo = Decimal(str(camada['preco_alvo']))

                            if preco_atual <= preco_alvo and str(preco_alvo) not in oportunidades_usadas:
                                logger.info(f"🚨 OPORTUNIDADE EXTREMA (Camada {preco_alvo}) DETECTADA!")

                                percentual_a_usar = Decimal(str(camada['percentual_capital_usar']))
                                capital_disponivel = self.gestao_capital.calcular_capital_disponivel()
                                valor_da_compra_usdt = capital_disponivel * (percentual_a_usar / Decimal('100'))

                                sucesso = self.executar_compra_por_valor(valor_da_compra_usdt, f"Oportunidade Extrema {preco_alvo}")

                                if sucesso:
                                    oportunidades_usadas.append(str(preco_alvo))
                                    self.state.set_state('oportunidades_extremas_usadas', oportunidades_usadas)
                                
                                return # Sai após tratar a primeira oportunidade válida

                        # Se o loop terminar, nenhuma camada foi ativada
                        logger.debug(f"🛡️ Exposição máxima atingida. Nenhuma nova camada de oportunidade ativada.")

                    else:
                        # Se a exposição voltar ao normal, reativa as notificações e a lógica de compra
                        if self.notificou_exposicao_maxima:
                            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                            logger.info(f"✅ Exposição de capital normalizada ({alocacao_atual_ada:.1f}%). Compras normais reativadas.")
                            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                            self.notificou_exposicao_maxima = False
                        
                        # Limpa o estado das oportunidades usadas quando a exposição é normalizada
                        if self.state.get_state('oportunidades_extremas_usadas'):
                            self.state.set_state('oportunidades_extremas_usadas', [])
                            logger.info("🔓 Camadas de oportunidade extrema rearmadas.")

                        # ═══════════════════════════════════════════════════════════════
                        # ESTRATÉGIA: LARGADA A FRIO
                        # ═══════════════════════════════════════════════════════════════
                        if self.primeira_execucao:
                            # Encontrar degrau MAIS PROFUNDO ativado
                            degrau_profundo = self.encontrar_degrau_mais_profundo(queda_pct)

                            if degrau_profundo:
                                logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                                logger.info("🥶 LARGADA A FRIO DETECTADA!")
                                logger.info(f"   Queda desde SMA: {queda_pct:.2f}%")
                                logger.info(f"   Degrau mais profundo ativado: Nível {degrau_profundo['nivel']}")
                                logger.info(f"   Executando compra controlada no degrau {degrau_profundo['nivel']}")
                                logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

                                # CORREÇÃO CRÍTICA: Marcar como tratada ANTES da compra
                                # Isso evita loop infinito se a compra falhar por falta de capital
                                self.primeira_execucao = False

                                # Persistir estado no StateManager
                                self.state.set_state('cold_start_executado_ts', datetime.now().isoformat())

                                # Executar APENAS UMA compra no degrau mais profundo
                                if self.executar_compra(degrau_profundo, preco_atual, saldos['usdt']):
                                    logger.info("✅ Compra de 'Largada a Frio' executada!")
                                    logger.info("   🕒 Cooldown global ativado")
                                    compra_executada = True

                                    # Aguardar 10 segundos após compra
                                    time.sleep(10)
                                else:
                                    logger.info("⚠️ Compra de 'Largada a Frio' não executada (sem capital disponível)")
                                    logger.info("   Bot continuará em modo normal")
                            else:
                                # Nenhum degrau ativado - continuar normalmente
                                self.primeira_execucao = False
                                logger.debug("Primeira execução, mas nenhum degrau ativado")

                        # ═══════════════════════════════════════════════════════════════
                        # ESTRATÉGIA NORMAL: Tentar comprar em degraus com cooldown duplo
                        # ═══════════════════════════════════════════════════════════════
                        if not compra_executada and not self.primeira_execucao:
                            for degrau in settings.DEGRAUS_COMPRA:
                                # ═══════════════════════════════════════════════════════════
                                # DUPLA-CONDIÇÃO: Verificar SMA + Preço Médio
                                # ═══════════════════════════════════════════════════════════

                                # CONDIÇÃO 1: Verificar se degrau está ativo (queda suficiente desde SMA)
                                condicao_sma_ok = queda_pct >= Decimal(str(degrau['queda_percentual']))

                                # CONDIÇÃO 2: Verificar se preço melhora o preço médio (DCA inteligente)
                                condicao_melhora_pm_ok = True  # Default: permite compra

                                if self.preco_medio_compra is not None and self.preco_medio_compra > 0:
                                    # Se já tem posição, verificar se preço atual melhora o preço médio
                                    percentual_melhora = settings.PERCENTUAL_MINIMO_MELHORA_PM / Decimal('100')
                                    limite_preco_melhora = self.preco_medio_compra * (Decimal('1') - percentual_melhora)
                                    condicao_melhora_pm_ok = preco_atual <= limite_preco_melhora

                                # Verificar se AMBAS as condições foram atendidas
                                if condicao_sma_ok and condicao_melhora_pm_ok:
                                    nivel_degrau = degrau['nivel']

                                    # Verificar se pode comprar (cooldown duplo)
                                    pode_comprar, motivo_bloqueio = self.pode_comprar_degrau(nivel_degrau, degrau)

                                    if pode_comprar:
                                        # DESBLOQUEADO: Remover do set se estava bloqueado
                                        if nivel_degrau in self.degraus_notificados_bloqueados:
                                            self.degraus_notificados_bloqueados.remove(nivel_degrau)
                                            logger.info(f"🔓 Degrau {nivel_degrau} desbloqueado")

                                        # ANTI-SPAM: Só loga "Degrau X ativado" 1x a cada 5 minutos
                                        agora = datetime.now()
                                        ultima_log = self.ultima_tentativa_log_degrau.get(nivel_degrau)

                                        if ultima_log is None or (agora - ultima_log) >= timedelta(minutes=5):
                                            logger.info(f"🎯 Degrau {nivel_degrau} ativado! Queda: {queda_pct:.2f}%")
                                            self.ultima_tentativa_log_degrau[nivel_degrau] = agora

                                        # Tentar executar compra
                                        if self.executar_compra(degrau, preco_atual, saldos['usdt']):
                                            logger.info("✅ Compra executada com sucesso!")
                                            compra_executada = True

                                            # Aguardar 10 segundos após compra
                                            time.sleep(10)
                                            break  # Compra executada, sair do loop
                                    else:
                                        # BLOQUEADO: Notificar apenas uma vez
                                        if nivel_degrau not in self.degraus_notificados_bloqueados:
                                            self.degraus_notificados_bloqueados.add(nivel_degrau)
                                            if motivo_bloqueio and motivo_bloqueio.startswith('cooldown_global'):
                                                logger.debug(f"🕒 Cooldown global ativo ({motivo_bloqueio})")
                                            elif motivo_bloqueio and motivo_bloqueio.startswith('cooldown_degrau'):
                                                logger.debug(f"🕒 Degrau {nivel_degrau} em cooldown ({motivo_bloqueio})")

                                    # Se não pode comprar neste degrau (cooldown), tenta o próximo
                                else:
                                    # Uma das condições não foi atendida - ignorar degrau
                                    if condicao_sma_ok and not condicao_melhora_pm_ok:
                                        # Degrau ativo pela SMA, mas preço não melhora suficiente o PM
                                        logger.debug(
                                            f"📊 Degrau {degrau['nivel']}: SMA OK ({queda_pct:.2f}%), mas preço ${preco_atual:.6f} "
                                            f"não melhora PM (${self.preco_medio_compra:.6f}) em {settings.PERCENTUAL_MINIMO_MELHORA_PM}%"
                                        )

                # LÓGICA DE VENDA (só vende com lucro!)
                if self.preco_medio_compra and saldos['ada'] >= Decimal('1'):
                    # Calcular lucro atual
                    lucro_atual = self.calcular_lucro_atual(preco_atual)

                    if lucro_atual and lucro_atual > 0:
                        # Buscar meta de venda ativa (passando saldo e preço para validação)
                        meta = self.encontrar_meta_ativa(lucro_atual, saldos['ada'], preco_atual)

                        if meta:
                            logger.info(f"🎯 Meta {meta['meta']} atingida! Lucro: +{lucro_atual:.2f}%")

                            # Tentar executar venda
                            if self.executar_venda(meta, preco_atual, saldos['ada']):
                                logger.info("✅ Venda executada com lucro!")

                                # Aguardar 10 segundos após venda
                                time.sleep(10)
                    else:
                        # Log informativo a cada 20 ciclos (≈ 2 minutos) quando não há lucro
                        if contador_ciclos % 20 == 0 and lucro_atual is not None:
                            logger.info(f"🛡️ Aguardando lucro (atual: {lucro_atual:+.2f}% | preço médio: ${self.preco_medio_compra:.6f})")

                # ═══════════════════════════════════════════════════════════════════
                # VERIFICAR RECOMPRAS DE SEGURANÇA
                # ═══════════════════════════════════════════════════════════════════
                # Se houver capital reservado para recompra, verificar se deve executar
                if self.capital_para_recompra and self.preco_medio_compra:
                    self.verificar_recompra_de_seguranca(preco_atual)

                # Verificar aportes BRL periodicamente
                agora = datetime.now()
                if agora - self.ultima_verificacao_aportes >= self.intervalo_verificacao_aportes:
                    self._verificar_aportes_brl()
                    self.ultima_verificacao_aportes = agora

                # Verificar e comprar BNB para desconto em taxas (1x por dia)
                if saldos['usdt'] >= Decimal('5.0'):
                    resultado_bnb = self.gerenciador_bnb.verificar_e_comprar_bnb(saldos['usdt'])
                    if resultado_bnb.get('sucesso') and resultado_bnb.get('precisa_comprar'):
                        logger.info(f"💎 BNB: {resultado_bnb['mensagem']}")

                # Fazer backup do banco de dados (1x por dia)
                self.fazer_backup_periodico()

                # PAINEL DE STATUS AVANÇADO
                # Exibir painel periodicamente (a cada 5 minutos ou 60 ciclos)
                if contador_ciclos % 60 == 0:
                    self.logar_painel_de_status(preco_atual, saldos)

                # Aguardar 5 segundos antes do próximo ciclo
                time.sleep(5)

        except KeyboardInterrupt:
            logger.warning("\n⚠️ Bot interrompido pelo usuário")
            self.rodando = False
        except Exception as e:
            logger.error(f"❌ Erro fatal no loop principal: {e}")
            logger.exception("Traceback:")
            self.rodando = False

        logger.banner("🛑 BOT FINALIZADO")


def main():
    """Função principal"""
    bot = TradingBot()
    bot.loop_principal()


if __name__ == '__main__':
    main()
