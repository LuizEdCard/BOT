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
from src.persistencia.database import DatabaseManager
from src.utils.logger import get_logger

# Configurar logger
logger = get_logger(
    log_dir=Path('logs'),
    nivel=settings.LOG_LEVEL,
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

        # Banco de dados
        self.db = DatabaseManager(
            db_path=settings.DATABASE_PATH,
            backup_dir=settings.BACKUP_DIR
        )

        # Estado do bot
        self.sma_referencia: Optional[Decimal] = None  # SMA de 4 semanas como referência
        self.sma_1h: Optional[Decimal] = None
        self.sma_4h: Optional[Decimal] = None
        self.ultima_atualizacao_sma = None
        self.ultima_verificacao_aporte = datetime.now()
        self.ultimo_backup = datetime.now()
        self.rodando = False

        # Histórico de preços (últimos 100)
        self.historico_precos: List[Decimal] = []

        # Controle de compras por degrau (para evitar compras repetidas)
        self.historico_compras_degraus: Dict[int, datetime] = {}  # {nivel_degrau: timestamp_ultima_compra}

        # Rastreamento de preço médio de compra (para calcular lucro)
        self.preco_medio_compra: Optional[Decimal] = None
        self.quantidade_total_comprada: Decimal = Decimal('0')
        self.valor_total_investido: Decimal = Decimal('0')

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
                    logger.info(f"   Quantidade: {self.quantidade_total_comprada:.1f} ADA")
                    logger.info(f"   Valor investido: ${self.valor_total_investido:.2f} USDT")
                else:
                    logger.info("📊 Iniciando com estado limpo (sem posições anteriores)")
            else:
                logger.info("📊 Nenhum estado anterior encontrado - iniciando do zero")

        except Exception as e:
            logger.error(f"⚠️ Erro ao recuperar estado do banco: {e}")
            logger.info("📊 Continuando com estado limpo")

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

    def pode_comprar_degrau(self, nivel_degrau: int, cooldown_horas: int = 1) -> bool:
        """
        Verifica se pode comprar no degrau (cooldown)

        Args:
            nivel_degrau: Nível do degrau (1, 2, 3, etc)
            cooldown_horas: Horas mínimas entre compras no mesmo degrau

        Returns:
            True se pode comprar, False caso contrário
        """
        if nivel_degrau not in self.historico_compras_degraus:
            return True  # Nunca comprou neste degrau

        ultima_compra = self.historico_compras_degraus[nivel_degrau]
        tempo_decorrido = datetime.now() - ultima_compra

        if tempo_decorrido >= timedelta(hours=cooldown_horas):
            return True  # Cooldown expirado

        # Ainda em cooldown
        tempo_restante = timedelta(hours=cooldown_horas) - tempo_decorrido
        minutos_restantes = int(tempo_restante.total_seconds() / 60)
        logger.debug(f"🕒 Degrau {nivel_degrau} em cooldown (faltam {minutos_restantes} min)")
        return False

    def registrar_compra_degrau(self, nivel_degrau: int):
        """Registra timestamp da compra no degrau"""
        self.historico_compras_degraus[nivel_degrau] = datetime.now()
        logger.debug(f"✅ Compra registrada: Degrau {nivel_degrau} às {datetime.now().strftime('%H:%M:%S')}")

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
        """Executa compra no degrau"""
        quantidade_ada = Decimal(str(degrau['quantidade_ada']))
        valor_ordem = quantidade_ada * preco_atual

        # Calcular saldo utilizável (respeitando reserva de capital)
        percentual_capital_ativo = Decimal(str(settings.PERCENTUAL_CAPITAL_ATIVO)) / Decimal('100')
        saldo_utilizavel = saldo_usdt * percentual_capital_ativo

        # Verificar se tem saldo suficiente (considerando a reserva)
        if valor_ordem > saldo_utilizavel:
            logger.warning(
                f"⚠️ Saldo utilizável insuficiente: ${saldo_utilizavel:.2f} < ${valor_ordem:.2f} "
                f"(Reserva de {settings.PERCENTUAL_RESERVA}% mantida: ${saldo_usdt - saldo_utilizavel:.2f})"
            )
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

                # Registrar compra no degrau para cooldown
                self.registrar_compra_degrau(degrau['nivel'])

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

    def calcular_lucro_percentual(self, preco_atual: Decimal, preco_medio_compra: Decimal) -> Decimal:
        """Calcula lucro % sobre preço médio de compra"""
        if preco_medio_compra == 0:
            return Decimal('0')

        lucro = ((preco_atual - preco_medio_compra) / preco_medio_compra) * Decimal('100')
        return lucro

    def encontrar_meta_ativa(self, lucro_pct: Decimal) -> Optional[Dict]:
        """
        Encontra meta de venda correspondente ao lucro atual

        REGRA 1: Só vende se houver LUCRO (nunca vende com prejuízo)
        REGRA 2 (ADAPTATIVA): Se lucro entre 3-6%, vende pequena quantidade (5%)
                              para aproveitar oscilações e realizar algum lucro
        """
        if lucro_pct <= 0:
            return None  # Sem lucro, não vende

        # SISTEMA ADAPTATIVO: Vender com lucro menor que as metas principais
        # Se está entre 3% e 6%, vende uma quantidade pequena (5%)
        if Decimal('3.0') <= lucro_pct < Decimal('6.0'):
            return {
                'meta': 'adaptativa',
                'lucro_percentual': float(lucro_pct),
                'percentual_venda': 5  # Vende apenas 5%
            }

        # Buscar a meta fixa correspondente ao lucro atual
        for meta in settings.METAS_VENDA:
            if lucro_pct >= Decimal(str(meta['lucro_percentual'])):
                return meta

        return None

    def executar_venda(self, meta: Dict, preco_atual: Decimal, saldo_ada: Decimal):
        """
        Executa venda na meta

        PROTEÇÃO: Só executa se houver lucro confirmado
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

                # Ajustar tracking após venda (reduzir quantidade total)
                self.quantidade_total_comprada -= quantidade_venda
                self.valor_total_investido -= valor_medio_compra

                logger.info(f"📊 Posição atualizada: {self.quantidade_total_comprada:.1f} ADA (preço médio: ${self.preco_medio_compra:.6f})")

                # Capturar saldos depois da venda
                saldos_depois = self.obter_saldos()

                # SALVAR NO BANCO DE DADOS
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
                    'observacao': f"Venda {meta['meta']} - Lucro {lucro_pct:.2f}%"
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

    def verificar_aportes_periodico(self):
        """Verifica aportes BRL periodicamente"""
        agora = datetime.now()
        intervalo = timedelta(seconds=settings.INTERVALO_VERIFICACAO_SALDO)

        if agora - self.ultima_verificacao_aporte >= intervalo:
            logger.info("🔍 Verificando aportes BRL...")
            resultado = self.gerenciador_aportes.processar_aporte_automatico()

            if resultado['sucesso']:
                logger.info(f"✅ {resultado['mensagem']}")

            self.ultima_verificacao_aporte = agora

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

        # Obter saldos iniciais
        saldos = self.obter_saldos()
        logger.info(f"💼 Saldo inicial: ${saldos['usdt']:.2f} USDT | {saldos['ada']:.2f} ADA")

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

                # LÓGICA DE COMPRA
                if queda_pct and queda_pct > Decimal('0.5'):  # Só verificar se caiu pelo menos 0.5%
                    degrau = self.encontrar_degrau_ativo(queda_pct)

                    if degrau:
                        nivel_degrau = degrau['nivel']

                        # Verificar cooldown do degrau
                        if not self.pode_comprar_degrau(nivel_degrau, cooldown_horas=settings.COOLDOWN_DEGRAU_HORAS):
                            # Em cooldown, pular esta compra
                            pass
                        else:
                            logger.info(f"🎯 Degrau {nivel_degrau} ativado! Queda: {queda_pct:.2f}%")

                            # Tentar executar compra
                            if self.executar_compra(degrau, preco_atual, saldos['usdt']):
                                logger.info("✅ Compra executada com sucesso!")

                                # Aguardar 10 segundos após compra
                                time.sleep(10)

                # LÓGICA DE VENDA (só vende com lucro!)
                if self.preco_medio_compra and saldos['ada'] >= Decimal('1'):
                    # Calcular lucro atual
                    lucro_atual = self.calcular_lucro_atual(preco_atual)

                    if lucro_atual and lucro_atual > 0:
                        # Buscar meta de venda ativa
                        meta = self.encontrar_meta_ativa(lucro_atual)

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

                # Verificar aportes BRL (a cada hora)
                self.verificar_aportes_periodico()

                # Verificar e comprar BNB para desconto em taxas (1x por dia)
                if saldos['usdt'] >= Decimal('5.0'):
                    resultado_bnb = self.gerenciador_bnb.verificar_e_comprar_bnb(saldos['usdt'])
                    if resultado_bnb.get('sucesso') and resultado_bnb.get('precisa_comprar'):
                        logger.info(f"💎 BNB: {resultado_bnb['mensagem']}")

                # Fazer backup do banco de dados (1x por dia)
                self.fazer_backup_periodico()

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
