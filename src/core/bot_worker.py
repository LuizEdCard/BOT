#!/usr/bin/env python3
"""
Bot Worker - Orquestrador de Estratégias de Trading
"""

import sys
import asyncio
import math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import time
import queue
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from src.exchange.base import ExchangeAPI
from src.exchange.binance_api import BinanceAPI
from src.core.gerenciador_aportes import GerenciadorAportes
from src.core.gerenciador_bnb import GerenciadorBNB
from src.core.analise_tecnica import AnaliseTecnica
from src.core.gestao_capital import GestaoCapital
from src.core.position_manager import PositionManager
from src.core.strategy_dca import StrategyDCA
from src.core.strategy_sell import StrategySell
from src.core.strategy_swing_trade import StrategySwingTrade
from src.persistencia.database import DatabaseManager
from src.persistencia.state_manager import StateManager
from src.utils.logger import get_loggers
from src.utils.constants import Icones, LogConfig


class BotWorker:
    """Bot Worker - Orquestrador de Estratégias de Trading"""

    def __init__(self, config: Dict[str, Any], exchange_api: ExchangeAPI, telegram_notifier=None, notifier=None, modo_simulacao: bool = False):
        """
        Inicializar bot worker

        Args:
            config: Configuração do bot
            exchange_api: Instância da API de exchange
            telegram_notifier: Instância do TelegramBot (legado)
            notifier: Instância do Notifier para notificações proativas
        """
        self.config = config
        self.exchange_api = exchange_api
        self.telegram_notifier = telegram_notifier
        self.notifier = notifier
        self.modo_simulacao = modo_simulacao

        # Escolha de estratégia (dca, giro, ou ambas)
        self.estrategia_ativa = config.get('ESTRATEGIA_ATIVA', 'ambas')

        main_logger, self.panel_logger = get_loggers(
            nome=self.config.get('BOT_NAME', 'BotWorker'),
            log_dir=Path('logs'),
            config=LogConfig.DESENVOLVIMENTO,
            console=True
        )

        # Store the main logger for banner methods
        self.main_logger = main_logger

        # Criar LoggerAdapters contextuais para o worker e cada especialista
        nome_instancia = self.config.get('nome_instancia', self.config.get('BOT_NAME', 'BotWorker'))

        # Logger do worker com contexto
        self.logger = logging.LoggerAdapter(main_logger.logger, {'context': nome_instancia})

        # Loggers contextuais para especialistas
        dca_logger = logging.LoggerAdapter(main_logger.logger, {'context': f"{nome_instancia}-StrategyDCA"})
        sell_logger = logging.LoggerAdapter(main_logger.logger, {'context': f"{nome_instancia}-StrategySell"})
        swing_logger = logging.LoggerAdapter(main_logger.logger, {'context': f"{nome_instancia}-StrategySwing"})

        # Componentes auxiliares
        self.gerenciador_aportes = GerenciadorAportes(self.exchange_api, self.config)
        self.gerenciador_bnb = GerenciadorBNB(self.exchange_api, self.config)
        self.analise_tecnica = AnaliseTecnica(self.exchange_api)
        self.gestao_capital = GestaoCapital(percentual_reserva=Decimal(str(self.config.get('PERCENTUAL_RESERVA', 8))))

        # Banco de dados e estado
        self.db = DatabaseManager(
            db_path=Path(self.config['DATABASE_PATH']),
            backup_dir=Path(self.config['BACKUP_DIR'])
        )
        self.state = StateManager(state_file_path=Path(self.config['STATE_FILE_PATH']))

        # ═══════════════════════════════════════
        # NOVA ARQUITETURA: Componentes Estratégicos
        # ═══════════════════════════════════════

        # Gerenciador de posições
        self.position_manager = PositionManager(self.db)

        # Estratégias (agora com loggers contextuais)
        self.strategy_dca = StrategyDCA(
            config=self.config,
            position_manager=self.position_manager,
            gestao_capital=self.gestao_capital,
            state_manager=self.state,
            worker=self,
            logger=dca_logger,
            notifier=self.notifier
        )

        self.strategy_sell = StrategySell(
            config=self.config,
            position_manager=self.position_manager,
            state_manager=self.state,
            logger=sell_logger
        )

        # Estratégia de Giro Rápido (Swing Trade)
        self.strategy_swing_trade = StrategySwingTrade(
            config=self.config,
            position_manager=self.position_manager,
            gestao_capital=self.gestao_capital,
            logger=swing_logger,
            notifier=self.notifier,
            exchange_api=self.exchange_api  # CRÍTICO: Passar API para buscar histórico
        )

        # Estado do bot
        self.sma_referencia: Optional[Decimal] = None
        self.sma_1h: Optional[Decimal] = None
        self.sma_4h: Optional[Decimal] = None
        self.ultima_atualizacao_sma = None
        self.ultimo_backup = datetime.now()
        self.rodando = False
        self.inicio_bot = datetime.now()
        
        # Fila de comandos para controle remoto
        self.command_queue = queue.Queue()
        self.compras_pausadas_manualmente = False
        self.guardiao_suspenso_temporariamente = False
        self.modo_crash_ativo = False

        # Configuração de aportes BRL
        self.aportes_config = self.config.get('APORTES', {})
        if self.aportes_config.get('habilitado', False):
            self.intervalo_verificacao_aportes = timedelta(minutes=self.aportes_config['intervalo_verificacao_minutos'])
            self.ultima_verificacao_aportes = datetime.now() - self.intervalo_verificacao_aportes
        else:
            self.intervalo_verificacao_aportes = None
            self.ultima_verificacao_aportes = None

        # Estado operacional
        self.estado_bot: str = "OPERANDO"
        self.ja_avisou_sem_saldo: bool = False
        
        # Log de inicialização com status das estratégias
        estrategias_config = self.config.get('ESTRATEGIAS', {})
        dca_habilitada = estrategias_config.get('dca', True)
        giro_habilitado = estrategias_config.get('giro_rapido', False)
        
        self.logger.info(f"🤖 BotWorker inicializado com arquitetura de estratégias")
        self.logger.info(f"   📊 PositionManager (acumulação): {'COM POSIÇÃO' if self.position_manager.tem_posicao('acumulacao') else 'SEM POSIÇÃO'}")
        self.logger.info(f"   🎯 StrategyDCA: {'HABILITADA' if dca_habilitada else 'DESABILITADA'} ({len(self.strategy_dca.degraus_compra)} degraus)")
        self.logger.info(f"   💰 StrategySell: {len(self.strategy_sell.metas_venda)} metas")
        self.logger.info(f"   📈 StrategySwingTrade: {'HABILITADA' if giro_habilitado else 'DESABILITADA'}")

    def _sincronizar_saldos_exchange(self):
        """
        Sincroniza saldos reais da exchange com a gestão de capital.
        Implementa auto-correção do banco de dados se uma divergência for detectada.

        IMPORTANTE: Em modo simulação, não faz auto-correção - confia no saldo inicial fornecido.
        """
        try:
            self.logger.info(f"🔄 Sincronizando saldos com a exchange...")

            # Extrair moedas base e de cotação do par
            base_currency, quote_currency = self.config['par'].split('/')

            # 1. Buscar saldo REAL da API
            saldo_base_real = self.exchange_api.get_saldo_disponivel(base_currency)
            saldo_quote_real = self.exchange_api.get_saldo_disponivel(quote_currency)

            # 2. Carregar posição do banco de dados LOCAL (TODAS as carteiras)
            quantidade_acumulacao = self.position_manager.get_quantidade_total('acumulacao')
            quantidade_giro = self.position_manager.get_quantidade_total('giro_rapido')
            quantidade_local = quantidade_acumulacao + quantidade_giro

            self.logger.info(f"📊 Saldo LOCAL (banco de dados):")
            self.logger.info(f"   • Acumulação: {quantidade_acumulacao:.1f} {base_currency}")
            self.logger.info(f"   • Giro Rápido: {quantidade_giro:.1f} {base_currency}")
            self.logger.info(f"   • TOTAL: {quantidade_local:.1f} {base_currency}")
            self.logger.info(f"📊 Saldo EXCHANGE (API real): {saldo_base_real:.1f} {base_currency} | ${saldo_quote_real:.2f} {quote_currency}")

            # 3. Comparar os dois valores
            diferenca_absoluta = abs(Decimal(str(saldo_base_real)) - quantidade_local)

            # Calcular tolerância: 2.5% do saldo da API (mínimo 0.5)
            # Tolerância mais alta para evitar reimports por pequenas divergências
            tolerancia = max(Decimal(str(saldo_base_real)) * Decimal('0.025'), Decimal('0.5'))
            
            self.logger.info(f"📏 Diferença detectada: {diferenca_absoluta:.2f} {base_currency} (tolerância: {tolerancia:.2f})")

            # 4. Se divergência for maior que a tolerância, considerar desincronização
            # IMPORTANTE: Pular auto-correção em modo simulação
            if diferenca_absoluta > tolerancia:
                self.logger.warning("⚠️" + "="*60)
                self.logger.warning("⚠️ DIVERGÊNCIA DETECTADA!")
                self.logger.warning(f"⚠️ Saldo da API ({saldo_base_real:.1f}) difere do banco local ({quantidade_local:.1f})")
                self.logger.warning(f"⚠️ Diferença de {diferenca_absoluta:.2f} {base_currency} excede a tolerância de {tolerancia:.2f}")

                # ═══════════════════════════════════════════════════════════════
                # MODO SIMULAÇÃO: NÃO fazer auto-correção
                # ═══════════════════════════════════════════════════════════════
                if self.modo_simulacao:
                    self.logger.info("🔬 MODO SIMULAÇÃO: Auto-correção desabilitada")
                    self.logger.info("🔬 Confiando no saldo inicial fornecido para o backtest")
                else:
                    # Modo real: aplicar auto-correção
                    self.logger.warning("⚠️ Sincronizando histórico dos últimos 60 dias com a exchange...")
                    self.logger.warning("⚠️ Histórico antigo (> 60 dias) será preservado")
                    self.logger.warning("⚠️" + "="*60)

                    try:
                        # 4a. Chamar método de importação de histórico
                        self.logger.info("🔄 Iniciando auto-correção do banco de dados...")
                        self.exchange_api.importar_historico_para_db(
                            database_manager=self.db,
                            par=self.config['par']
                        )

                        # 4b. Recarregar o PositionManager para refletir os dados corretos
                        self.logger.info("🔄 Recarregando PositionManager com dados corrigidos...")
                        self.position_manager.carregar_posicao('acumulacao')
                        self.position_manager.carregar_posicao('giro_rapido')

                        # Verificar novamente após correção (TOTAL de ambas carteiras)
                        quantidade_acum_corrigida = self.position_manager.get_quantidade_total('acumulacao')
                        quantidade_giro_corrigida = self.position_manager.get_quantidade_total('giro_rapido')
                        quantidade_corrigida = quantidade_acum_corrigida + quantidade_giro_corrigida
                        diferenca_pos_correcao = abs(Decimal(str(saldo_base_real)) - quantidade_corrigida)

                        self.logger.info(f"✅ Auto-correção concluída!")
                        self.logger.info(f"   📊 Saldo LOCAL corrigido: {quantidade_corrigida:.1f} {base_currency}")
                        self.logger.info(f"   📊 Saldo EXCHANGE: {saldo_base_real:.1f} {base_currency}")
                        self.logger.info(f"   📏 Nova diferença: {diferenca_pos_correcao:.2f} {base_currency}")

                        if diferenca_pos_correcao <= tolerancia:
                            self.logger.info("✅ Banco de dados sincronizado com sucesso com a exchange!")
                        else:
                            self.logger.warning(f"⚠️ Ainda há divergência de {diferenca_pos_correcao:.2f} {base_currency} após correção")
                            self.logger.warning("⚠️ Não forçando quantidade - verifique manualmente as estratégias no banco")
                            # NÃO forçar quantidade porque isso pode misturar as carteiras
                            # O usuário deve verificar manualmente o banco de dados

                    except Exception as erro_correcao:
                        self.logger.error(f"❌ Erro durante auto-correção: {erro_correcao}")
                        self.logger.warning("⚠️ Continuando com dados locais existentes")
                        import traceback
                        self.logger.error(f"Traceback:\n{traceback.format_exc()}")
            else:
                self.logger.info(f"✅ Saldo local sincronizado com a exchange (diferença: {diferenca_absoluta:.2f} dentro da tolerância)")

            # Atualizar gestão de capital com saldos reais
            valor_posicao_base = Decimal(str(saldo_base_real)) * self._obter_preco_atual_seguro()
            self.gestao_capital.atualizar_saldos(Decimal(str(saldo_quote_real)), valor_posicao_base)

            self.logger.info(f"💼 Saldo final confirmado: {saldo_base_real:.1f} {base_currency} | ${saldo_quote_real:.2f} {quote_currency}")

        except Exception as e:
            self.logger.error(f"❌ Erro ao sincronizar saldo com a exchange: {e}")
            self.logger.warning("⚠️ Continuando com saldo local (pode estar desatualizado)")
            import traceback
            self.logger.error(f"Traceback:\n{traceback.format_exc()}")

    def _processar_comandos(self):
        """
        Processa comandos da fila de comandos remotos
        """
        try:
            while not self.command_queue.empty():
                comando = self.command_queue.get_nowait()
                
                if comando.get('comando') == 'pausar_compras':
                    self.compras_pausadas_manualmente = True
                    self.logger.info("⏸️  COMPRAS PAUSADAS MANUALMENTE via comando remoto")
                    
                elif comando.get('comando') == 'liberar_compras':
                    self.compras_pausadas_manualmente = False
                    self.logger.info("▶️  COMPRAS LIBERADAS via comando remoto")
                    
                elif comando.get('comando') == 'suspender_guardiao':
                    self.guardiao_suspenso_temporariamente = True
                    self.logger.warning("🔓 GUARDIÃO SUSPENSO TEMPORARIAMENTE via comando remoto")
                    
                elif comando.get('comando') == 'reativar_guardiao':
                    self.guardiao_suspenso_temporariamente = False
                    self.logger.info("🛡️  GUARDIÃO REATIVADO via comando remoto")
                    
                elif comando.get('comando') == 'ativar_modo_crash':
                    self.modo_crash_ativo = True
                    self.logger.warning("💥" + "="*60)
                    self.logger.warning("💥 MODO CRASH ATIVADO!")
                    self.logger.warning("💥 Compras agressivas liberadas")
                    self.logger.warning("💥 Restrições de exposição e preço médio IGNORADAS")
                    self.logger.warning("💥" + "="*60)
                    
                elif comando.get('comando') == 'desativar_modo_crash':
                    self.modo_crash_ativo = False
                    self.logger.info("✅ MODO CRASH DESATIVADO - Retornando ao modo normal")

                elif comando.get('comando') == 'force_buy':
                    valor_usdt = Decimal(comando.get('valor'))
                    self.logger.info(f"🚨 COMPRA FORÇADA de {valor_usdt} USDT")
                    preco_atual = self._obter_preco_atual_seguro()
                    quantidade = valor_usdt / preco_atual
                    self._executar_oportunidade_compra({
                        'tipo': 'manual',
                        'quantidade': quantidade,
                        'preco_atual': preco_atual,
                        'motivo': 'Compra forçada via Telegram'
                    })

                elif comando.get('comando') == 'force_sell':
                    percentual = Decimal(comando.get('percentual'))
                    self.logger.info(f"🚨 VENDA FORÇADA de {percentual}% da posição")
                    quantidade_total = self.position_manager.get_quantidade_total()
                    quantidade_a_vender = quantidade_total * (percentual / 100)
                    preco_atual = self._obter_preco_atual_seguro()
                    self._executar_oportunidade_venda({
                        'tipo': 'manual',
                        'quantidade_venda': quantidade_a_vender,
                        'preco_atual': preco_atual,
                        'motivo': f'Venda forçada de {percentual}% via Telegram'
                    })
                elif comando.get('comando') == 'ajustar_risco':
                    novo_limite = comando.get('novo_limite')
                    if isinstance(novo_limite, (int, float)) and 0 <= novo_limite <= 100:
                        self.config['GESTAO_DE_RISCO']['exposicao_maxima_percentual_capital'] = novo_limite
                        self.logger.info(f"⚙️ Limite de exposição ajustado para {novo_limite}% para '{self.config.get('nome_instancia')}' via comando remoto.")
                    else:
                        self.logger.error(f"❌ Valor de risco inválido: {novo_limite}. O valor deve ser um número entre 0 e 100.")
                    
                else:
                    self.logger.warning(f"⚠️  Comando desconhecido: {comando}")
                    
        except queue.Empty:
            pass
        except Exception as e:
            self.logger.error(f"❌ Erro ao processar comandos: {e}")
    
    def _obter_preco_atual_seguro(self) -> Decimal:
        """Obtém preço atual com fallback seguro"""
        try:
            return Decimal(str(self.exchange_api.get_preco_atual(self.config['par'])))
        except:
            return Decimal('1.0')  # Fallback para evitar divisão por zero

    def _atualizar_sma_referencia(self):
        """
        Atualiza SMA de referência (4 semanas)
        """
        agora = datetime.now()

        # Atualizar apenas se passou 1 hora ou se nunca foi calculada
        if (
            self.ultima_atualizacao_sma is None
            or (agora - self.ultima_atualizacao_sma) >= timedelta(hours=1)
        ):

            self.logger.info("📊 Calculando SMA de referência (4 semanas)...")
            self.logger.info("🔄 Atualizando SMA de referência (4 semanas)...")

            smas = self.analise_tecnica.calcular_sma_multiplos_timeframes(
                simbolo=self.config['par'],
                periodo_dias=28  # 4 semanas
            )

            if smas:
                self.sma_1h = smas.get('1h')
                self.sma_4h = smas.get('4h')
                self.sma_referencia = smas.get('media')  # Média ponderada
                self.ultima_atualizacao_sma = agora

                self.logger.info(f"✅ SMA de referência atualizada: ${self.sma_referencia:.6f}")
            else:
                self.logger.error("❌ Não foi possível atualizar SMA")

    def _calcular_distancia_sma(self, preco_atual: Decimal) -> Optional[Decimal]:
        """
        Calcula distância percentual desde a SMA de referência
        """
        if self.sma_referencia is None:
            return None

        distancia = ((self.sma_referencia - preco_atual) / self.sma_referencia) * Decimal('100')
        return distancia

    def _executar_oportunidade_compra(self, oportunidade: Dict[str, Any]) -> bool:
        """
        Executa uma oportunidade de compra identificada pela estratégia

        Args:
            oportunidade: Dados da oportunidade retornados pela estratégia

        Returns:
            bool: True se compra foi executada com sucesso
        """
        # Verificar se compras estão pausadas manualmente
        if self.compras_pausadas_manualmente:
            self.logger.debug("⏸️  Compra bloqueada: compras pausadas manualmente")
            return False

        try:
            tipo = oportunidade['tipo']
            quantidade = oportunidade['quantidade']
            preco_atual = oportunidade['preco_atual']
            carteira = oportunidade.get('carteira', 'acumulacao')  # Padrão: acumulacao
            
            self.logger.info(f"🎯 Executando oportunidade de compra: {oportunidade['motivo']}")
            
            # Executar ordem na exchange
            ordem = self.exchange_api.place_ordem_compra_market(
                par=self.config['par'],
                quantidade=float(quantidade)
            )

            # Para KuCoin, market orders são executadas imediatamente, não retornam status FILLED
            # Para Binance, verifica o status
            ordem_executada = False
            if hasattr(self.exchange_api, '__class__') and 'Binance' in self.exchange_api.__class__.__name__:
                # Binance: verifica status FILLED
                ordem_executada = ordem and ordem.get('status') == 'FILLED'
            else:
                # KuCoin e outras: market orders são executadas se retornaram orderId
                ordem_executada = ordem and (ordem.get('orderId') or ordem.get('id'))
            
            if ordem_executada:
                # Binance: usa executedQty e cummulativeQuoteQty
                if hasattr(self.exchange_api, '__class__') and 'Binance' in self.exchange_api.__class__.__name__:
                    quantidade_real = Decimal(str(ordem.get('executedQty', quantidade)))
                    preco_real = Decimal(str(ordem.get('cummulativeQuoteQty', '0'))) / quantidade_real if quantidade_real > 0 else preco_atual
                else:
                    # KuCoin: market orders usam a quantidade solicitada
                    quantidade_real = Decimal(str(quantidade))
                    preco_real = preco_atual

                self.main_logger.operacao_compra(
                    par=self.config['par'],
                    quantidade=float(quantidade_real),
                    preco=float(preco_real),
                    degrau=oportunidade.get('degrau', 'N/A'),
                    queda_pct=float(oportunidade.get('distancia_sma', 0))
                )

                # Notificação com identificação da carteira
                if self.notifier:
                    carteira_emoji = "📊" if carteira == 'acumulacao' else "🎯"
                    carteira_nome = "Acumulação" if carteira == 'acumulacao' else "Giro Rápido"
                    mensagem = f"{quantidade_real:.2f} {self.config['par'].split('/')[0]} @ ${preco_real:.4f}"
                    self.notifier.enviar_sucesso(
                        f"COMPRA REALIZADA [{carteira_emoji} {carteira_nome}]",
                        mensagem
                    )

                # Atualizar position manager (com carteira correta)
                self.position_manager.atualizar_apos_compra(quantidade_real, preco_real, carteira)

                # Registrar na estratégia para ativar cooldowns
                if carteira == 'acumulacao':
                    self.strategy_dca.registrar_compra_executada(oportunidade, quantidade_real)
                elif carteira == 'giro_rapido':
                    self.strategy_swing_trade.registrar_compra_executada(oportunidade)

                # Determinar estratégia com base na carteira
                estrategia_nome = 'acumulacao' if carteira == 'acumulacao' else 'giro_rapido'

                # Extrair order_id com fallback para diferentes exchanges
                order_id = ordem.get('orderId') or ordem.get('id')
                if not order_id:
                    self.logger.warning(f"⚠️ Ordem de COMPRA executada mas sem ID retornado pela exchange")

                # Salvar no banco de dados
                self._salvar_ordem_banco({
                    'tipo': 'COMPRA',
                    'par': self.config['par'],
                    'quantidade': quantidade_real,
                    'preco': preco_real,
                    'valor_total': quantidade_real * preco_real,
                    'taxa': ordem.get('fills', [{}])[0].get('commission', 0) if ordem.get('fills') else 0,
                    'meta': str(oportunidade.get('degrau', 'oportunidade')),
                    'order_id': order_id,
                    'observacao': f"{tipo.upper()}: {oportunidade['motivo']}"
                }, estrategia=estrategia_nome)

                return True
            else:
                self.logger.error(f"❌ Erro ao executar compra: {ordem}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Erro ao executar oportunidade de compra: {e}")
            return False

    def _executar_oportunidade_venda(self, oportunidade: Dict[str, Any]) -> bool:
        """
        Executa uma oportunidade de venda identificada pela estratégia

        Args:
            oportunidade: Dados da oportunidade retornados pela estratégia

        Returns:
            bool: True se venda foi executada com sucesso
        """
        try:
            tipo = oportunidade['tipo']
            quantidade = oportunidade['quantidade_venda']
            preco_atual = oportunidade['preco_atual']
            carteira = oportunidade.get('carteira', 'acumulacao')  # Padrão: acumulacao

            self.logger.info(f"💰 Executando oportunidade de venda: {oportunidade['motivo']}")

            # ═══════════════════════════════════════════════════════════════════
            # VERIFICAÇÃO DE SALDO REAL ANTES DE VENDER
            # ═══════════════════════════════════════════════════════════════════
            # Previne vendas duplicadas e tentativas de vender mais do que se tem
            base_currency = self.config['par'].split('/')[0]
            saldo_real_exchange = Decimal(str(self.exchange_api.get_saldo_disponivel(base_currency)))
            saldo_carteira_db = self.position_manager.get_quantidade_total(carteira)

            self.logger.info(f"🔍 Verificação de saldo antes da venda [{carteira}]:")
            self.logger.info(f"   • Saldo REAL na exchange: {saldo_real_exchange:.4f} {base_currency}")
            self.logger.info(f"   • Saldo carteira {carteira} (DB): {saldo_carteira_db:.4f} {base_currency}")
            self.logger.info(f"   • Quantidade a vender: {quantidade:.4f} {base_currency}")

            # Verificar se há saldo suficiente na exchange
            # Usar math.isclose para comparar floats com tolerância
            if saldo_real_exchange < quantidade and not math.isclose(saldo_real_exchange, quantidade):
                self.logger.error(f"❌ VENDA BLOQUEADA: Saldo insuficiente!")
                self.logger.error(f"   • Tentativa de vender: {quantidade:.4f} {base_currency}")
                self.logger.error(f"   • Saldo disponível: {saldo_real_exchange:.4f} {base_currency}")
                self.logger.error(f"   • Faltam: {(quantidade - saldo_real_exchange):.4f} {base_currency}")

                # Alerta crítico via notifier
                if self.notifier:
                    carteira_nome = "Acumulação" if carteira == 'acumulacao' else "Giro Rápido"
                    self.notifier.enviar_alerta(
                        f"VENDA BLOQUEADA - Saldo Insuficiente [{carteira_nome}]",
                        f"Tentou vender {quantidade:.4f} {base_currency}\n"
                        f"Saldo disponível: {saldo_real_exchange:.4f} {base_currency}\n"
                        f"Verifique sincronização do banco!"
                    )

                return False

            # Verificar se a carteira especificada realmente tem essa posição
            if saldo_carteira_db < quantidade:
                self.logger.warning(f"⚠️ ATENÇÃO: Carteira {carteira} no DB tem menos que o solicitado!")
                self.logger.warning(f"   • Carteira {carteira} DB: {saldo_carteira_db:.4f} {base_currency}")
                self.logger.warning(f"   • Quantidade a vender: {quantidade:.4f} {base_currency}")
                self.logger.warning(f"   • Possível interferência entre carteiras ou dessincronia!")

                # Verificar se há interferência: outra carteira tentando vender da posição errada
                outra_carteira = 'acumulacao' if carteira == 'giro_rapido' else 'giro_rapido'
                saldo_outra_carteira = self.position_manager.get_quantidade_total(outra_carteira)

                if saldo_outra_carteira >= quantidade:
                    self.logger.error(f"❌ VENDA BLOQUEADA: Interferência detectada!")
                    self.logger.error(f"   • Carteira {carteira} tem apenas: {saldo_carteira_db:.4f} {base_currency}")
                    self.logger.error(f"   • Mas carteira {outra_carteira} tem: {saldo_outra_carteira:.4f} {base_currency}")
                    self.logger.error(f"   • Estratégia {carteira} NÃO PODE vender de {outra_carteira}!")

                    if self.notifier:
                        self.notifier.enviar_alerta(
                            f"VENDA BLOQUEADA - Interferência Entre Carteiras",
                            f"Carteira {carteira} tentou vender {quantidade:.4f} {base_currency}\n"
                            f"Mas só tem {saldo_carteira_db:.4f} no DB!\n"
                            f"Possível contaminação com carteira {outra_carteira}"
                        )

                    return False

            self.logger.info(f"✅ Verificação de saldo OK - Prosseguindo com venda")

            # Executar ordem na exchange
            ordem = self.exchange_api.place_ordem_venda_market(
                par=self.config['par'],
                quantidade=float(quantidade)
            )

            # Para KuCoin, market orders são executadas imediatamente, não retornam status FILLED
            # Para Binance, verifica o status
            ordem_executada = False
            if hasattr(self.exchange_api, '__class__') and 'Binance' in self.exchange_api.__class__.__name__:
                # Binance: verifica status FILLED
                ordem_executada = ordem and ordem.get('status') == 'FILLED'
            else:
                # KuCoin e outras: market orders são executadas se retornaram orderId
                ordem_executada = ordem and (ordem.get('orderId') or ordem.get('id'))
            
            if ordem_executada:
                # Binance: usa executedQty e cummulativeQuoteQty
                if hasattr(self.exchange_api, '__class__') and 'Binance' in self.exchange_api.__class__.__name__:
                    quantidade_real = Decimal(str(ordem.get('executedQty', quantidade)))
                    valor_real = Decimal(str(ordem.get('cummulativeQuoteQty', '0')))
                    preco_real = valor_real / quantidade_real if quantidade_real > 0 else preco_atual
                else:
                    # KuCoin: market orders usam a quantidade solicitada
                    quantidade_real = Decimal(str(quantidade))
                    valor_real = quantidade_real * preco_atual
                    preco_real = preco_atual

                # Calcular lucro ANTES de atualizar PositionManager
                # IMPORTANTE: Usar PM da carteira que está vendendo
                preco_medio = self.position_manager.get_preco_medio(carteira)
                lucro_pct = Decimal('0')
                lucro_usdt = Decimal('0')

                if preco_medio:
                    lucro_pct = ((preco_real - preco_medio) / preco_medio) * Decimal('100')
                    lucro_usdt = (preco_real - preco_medio) * quantidade_real

                self.main_logger.operacao_venda(
                    par=self.config['par'],
                    quantidade=float(quantidade_real),
                    preco=float(preco_real),
                    meta=oportunidade.get('meta', oportunidade.get('zona_nome', 'N/A')),
                    lucro_pct=float(lucro_pct),
                    lucro_usd=float(lucro_usdt)
                )

                # Notificação com identificação da carteira
                if self.notifier:
                    carteira_emoji = "📊" if carteira == 'acumulacao' else "🎯"
                    carteira_nome = "Acumulação" if carteira == 'acumulacao' else "Giro Rápido"
                    mensagem = f"{quantidade_real:.2f} {self.config['par'].split('/')[0]} @ ${preco_real:.4f}\nLucro: ${lucro_usdt:.2f} ({lucro_pct:.2f}%)"
                    self.notifier.enviar_sucesso(
                        f"VENDA REALIZADA [{carteira_emoji} {carteira_nome}]",
                        mensagem
                    )

                # Atualizar position manager (com carteira correta)
                self.position_manager.atualizar_apos_venda(quantidade_real, carteira)

                # Registrar na estratégia
                if carteira == 'acumulacao':
                    self.strategy_sell.registrar_venda_executada(oportunidade, quantidade_real)
                elif carteira == 'giro_rapido':
                    self.strategy_swing_trade.registrar_venda_executada(oportunidade)

                # Determinar estratégia com base na carteira
                estrategia_nome = 'acumulacao' if carteira == 'acumulacao' else 'giro_rapido'

                # Extrair order_id com fallback para diferentes exchanges
                order_id = ordem.get('orderId') or ordem.get('id')
                if not order_id:
                    self.logger.warning(f"⚠️ Ordem de VENDA executada mas sem ID retornado pela exchange")

                # Salvar no banco de dados
                self._salvar_ordem_banco({
                    'tipo': 'VENDA',
                    'par': self.config['par'],
                    'quantidade': quantidade_real,
                    'preco': preco_real,
                    'valor_total': valor_real,
                    'taxa': ordem.get('fills', [{}])[0].get('commission', 0) if ordem.get('fills') else 0,
                    'meta': str(oportunidade.get('meta', oportunidade.get('zona_nome', 'venda'))),
                    'lucro_percentual': lucro_pct,
                    'lucro_usdt': lucro_usdt,
                    'order_id': order_id,
                    'observacao': f"{tipo.upper()}: {oportunidade['motivo']}"
                }, estrategia=estrategia_nome)

                return True
            else:
                self.logger.error(f"❌ Erro ao executar venda: {ordem}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Erro ao executar oportunidade de venda: {e}")
            return False

    def _executar_oportunidade_recompra(self, oportunidade: Dict[str, Any]) -> bool:
        """
        Executa uma oportunidade de recompra de segurança
        
        Args:
            oportunidade: Dados da oportunidade de recompra
            
        Returns:
            bool: True se recompra foi executada com sucesso
        """
        try:
            quantidade = oportunidade['quantidade']
            preco_atual = oportunidade['preco_atual']
            
            self.logger.info(f"🔄 Executando recompra: {oportunidade['motivo']}")
            
            # Executar ordem na exchange
            ordem = self.exchange_api.place_ordem_compra_market(
                par=self.config['par'],
                quantidade=float(quantidade)
            )

            # Para KuCoin, market orders são executadas imediatamente, não retornam status FILLED
            # Para Binance, verifica o status
            ordem_executada = False
            if hasattr(self.exchange_api, '__class__') and 'Binance' in self.exchange_api.__class__.__name__:
                # Binance: verifica status FILLED
                ordem_executada = ordem and ordem.get('status') == 'FILLED'
            else:
                # KuCoin e outras: market orders são executadas se retornaram orderId
                ordem_executada = ordem and (ordem.get('orderId') or ordem.get('id'))
            
            if ordem_executada:
                # Binance: usa executedQty e cummulativeQuoteQty
                if hasattr(self.exchange_api, '__class__') and 'Binance' in self.exchange_api.__class__.__name__:
                    quantidade_real = Decimal(str(ordem.get('executedQty', quantidade)))
                    valor_real = Decimal(str(ordem.get('cummulativeQuoteQty', '0')))
                    preco_real = valor_real / quantidade_real if quantidade_real > 0 else preco_atual
                else:
                    # KuCoin: market orders usam a quantidade solicitada
                    quantidade_real = Decimal(str(quantidade))
                    valor_real = quantidade_real * preco_atual
                    preco_real = preco_atual

                self.main_logger.operacao_compra(
                    par=self.config['par'],
                    quantidade=float(quantidade_real),
                    preco=float(preco_real),
                    degrau=f"recompra_{oportunidade['zona_nome']}",
                    queda_pct=0
                )

                # Atualizar position manager
                self.position_manager.atualizar_apos_compra(quantidade_real, preco_real)

                # Registrar na estratégia de vendas
                self.strategy_sell.registrar_recompra_executada(oportunidade)

                # Extrair order_id com fallback para diferentes exchanges
                order_id = ordem.get('orderId') or ordem.get('id')
                if not order_id:
                    self.logger.warning(f"⚠️ Ordem de RECOMPRA executada mas sem ID retornado pela exchange")

                # Salvar no banco de dados (recompras são sempre da estratégia de acumulação)
                self._salvar_ordem_banco({
                    'tipo': 'COMPRA',
                    'par': self.config['par'],
                    'quantidade': quantidade_real,
                    'preco': preco_real,
                    'valor_total': valor_real,
                    'taxa': ordem.get('fills', [{}])[0].get('commission', 0) if ordem.get('fills') else 0,
                    'meta': f"recompra_{oportunidade['zona_nome']}",
                    'order_id': order_id,
                    'observacao': f"RECOMPRA: {oportunidade['motivo']}"
                }, estrategia='acumulacao')

                return True
            else:
                self.logger.error(f"❌ Erro ao executar recompra: {ordem}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Erro ao executar recompra: {e}")
            return False

    def _salvar_ordem_banco(self, ordem_dados: Dict[str, Any], estrategia: str):
        """
        Salva ordem no banco de dados

        Args:
            ordem_dados: Dados da ordem para salvar
            estrategia: Nome da estratégia ('acumulacao' ou 'giro_rapido')
        """
        try:
            # Adicionar dados de posição antes/depois e estratégia
            ordem_dados.update({
                'preco_medio_antes': self.position_manager.get_preco_medio(),
                'preco_medio_depois': self.position_manager.get_preco_medio(),
                'saldo_ada_antes': self.position_manager.get_quantidade_total(),
                'saldo_ada_depois': self.position_manager.get_quantidade_total(),
                'saldo_usdt_antes': Decimal('0'),  # Placeholder
                'saldo_usdt_depois': Decimal('0'),  # Placeholder
                'estrategia': estrategia
            })

            self.db.registrar_ordem(ordem_dados)

        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar ordem no banco: {e}")

    def _verificar_aportes_brl(self):
        """Verifica aportes em BRL periodicamente"""
        try:
            agora = datetime.now()
            if agora - self.ultima_verificacao_aportes >= self.intervalo_verificacao_aportes:
                self.logger.info("🔍 Verificando possíveis aportes em BRL...")
                resultado = self.gerenciador_aportes.processar_aporte_automatico()

                if resultado.get('sucesso'):
                    self.logger.info(f"✅ Aporte processado: {resultado.get('mensagem')}")
                    # Forçar sincronização após aporte
                    self._sincronizar_saldos_exchange()

                self.ultima_verificacao_aportes = agora
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao verificar aportes BRL: {e}")

    def _fazer_backup_periodico(self):
        """Faz backup do banco de dados periodicamente"""
        agora = datetime.now()
        if agora - self.ultimo_backup >= timedelta(days=1):
            try:
                self.logger.info("💾 Criando backup do banco de dados...")
                backup_path = self.db.fazer_backup()
                self.logger.info(f"✅ Backup criado: {backup_path}")
                self.ultimo_backup = agora
            except Exception as e:
                self.logger.error(f"❌ Erro ao criar backup: {e}")

    def run(self):
        """
        Loop principal simplificado do bot worker
        """
        try:
            self.main_logger.banner("🤖 BOT DE TRADING INICIADO")
            self.logger.info(f"Par: {self.config['par']}")
            self.logger.info(f"Ambiente: {self.config['AMBIENTE']}")
            self.logger.info(f"Capital inicial: ${self.config['CAPITAL_INICIAL']}")

            # Verificar conectividade
            if not self.exchange_api.check_connection():
                self.logger.error("❌ Falha na conexão com a exchange")
                return

            self.logger.info("✅ Conectado à Exchange")

            # Sincronização inicial
            self._sincronizar_saldos_exchange()

            # Calcular SMA inicial
            self._atualizar_sma_referencia()

            self.rodando = True
            contador_ciclos = 0

            # ═══════════════════════════════════════
            # SELEÇÃO DO MODO DE OPERAÇÃO
            # ═══════════════════════════════════════
            if self.modo_simulacao:
                self._run_simulacao()
            else:
                self._run_tempo_real()
        
        except Exception as e:
            self.logger.error(f"❌ Erro fatal no bot: {e}", exc_info=True)
            raise

    def _run_simulacao(self):
        """
        Loop de execução para o modo de simulação (backtesting).

        REFATORADO: Itera explicitamente pelos dados históricos usando indice_atual
        para garantir que todos os candles sejam processados.
        """
        self.logger.info("🏁 Iniciando worker em MODO DE SIMULAÇÃO.")

        # Verificar se a API tem o atributo indice_atual e dados_completos
        if not hasattr(self.exchange_api, 'indice_atual') or not hasattr(self.exchange_api, 'dados_completos'):
            self.logger.error("❌ SimulatedExchangeAPI não possui atributos necessários (indice_atual/dados_completos)")
            self.rodando = False
            return

        total_candles = len(self.exchange_api.dados_completos)
        self.logger.info(f"📊 Total de candles para processar: {total_candles}")

        # ═══════════════════════════════════════════════════════════════════
        # LOOP PRINCIPAL: Iterar enquanto há dados históricos
        # ═══════════════════════════════════════════════════════════════════
        while self.rodando and self.exchange_api.indice_atual < total_candles:
            try:
                # Executar ciclo de decisão (que internamente chama get_preco_atual e avança o índice)
                self._executar_ciclo_decisao()

                # Log de progresso a cada 100 candles
                if self.exchange_api.indice_atual % 100 == 0:
                    progresso = (self.exchange_api.indice_atual / total_candles) * 100
                    self.logger.info(f"📊 Progresso: {self.exchange_api.indice_atual}/{total_candles} ({progresso:.1f}%)")

            except StopIteration:
                # StopIteration é lançado quando get_preco_atual não tem mais dados
                self.logger.info("🏁 Fim dos dados históricos (StopIteration).")
                self.rodando = False
                break

            except KeyboardInterrupt:
                self.logger.info("🛑 Interrupção solicitada pelo usuário durante a simulação.")
                self.rodando = False
                break

            except Exception as e:
                self.logger.error(f'❌ Erro inesperado no loop de simulação: {e}', exc_info=True)
                import traceback
                self.logger.error(f"Traceback:\n{traceback.format_exc()}")
                self.rodando = False
                break

        # ═══════════════════════════════════════════════════════════════════
        # FINALIZAÇÃO: Logar resultados
        # ═══════════════════════════════════════════════════════════════════
        self.logger.info(f"🏁 Simulação finalizada. Candles processados: {self.exchange_api.indice_atual}/{total_candles}")

        if hasattr(self.exchange_api, 'get_resultados'):
            self._logar_resultados_simulacao()

    def _run_tempo_real(self):
        """Loop de execução para o modo de operação em tempo real."""
        self.logger.info("🟢 Iniciando worker em MODO DE TEMPO REAL.")
        
        while self.rodando:
            try:
                self._executar_ciclo_decisao()
                
                # Pausa entre os ciclos no modo de tempo real
                time.sleep(5)

            except KeyboardInterrupt:
                self.logger.info("🛑 Interrupção solicitada pelo usuário.")
                self.rodando = False
                continue
            except Exception as e:
                self.logger.error(f'Erro inesperado no loop principal: {e}', exc_info=True)
                self.estado_bot = 'ERRO'
                time.sleep(60)  # Pausa maior em caso de erro
                continue

    def _executar_ciclo_decisao(self):
        """
        Contém a lógica de decisão principal do bot, chamada em cada ciclo
        seja em tempo real ou em simulação.
        """
        # Processar comandos remotos (relevante em ambos os modos)
        self._processar_comandos()
        
        # 1. Obter preço atual
        preco_atual = Decimal(str(self.exchange_api.get_preco_atual(self.config['par'])))
        
        # Calcular distância da SMA
        distancia_sma = self._calcular_distancia_sma(preco_atual)

        # 2. Verificar oportunidade de compra (DCA) - Carteira Acumulação
        if distancia_sma:
            oportunidade_compra = self.strategy_dca.verificar_oportunidade(
                preco_atual=preco_atual,
                distancia_sma=distancia_sma
            )
            if oportunidade_compra and self._executar_oportunidade_compra(oportunidade_compra):
                self.logger.info("✅ Compra executada com sucesso (Acumulação)!")
                if not self.modo_simulacao: time.sleep(10)
                return

        # 2b. Verificar oportunidade de Swing Trade (Giro Rápido)
        if self.strategy_swing_trade.habilitado:
            oportunidade_swing = self.strategy_swing_trade.verificar_oportunidade(preco_atual)
            if oportunidade_swing:
                if oportunidade_swing['tipo'] == 'compra':
                    if self._executar_oportunidade_compra(oportunidade_swing):
                        self.logger.info("✅ Compra executada com sucesso (Giro Rápido)!")
                        if not self.modo_simulacao: time.sleep(10)
                        return
                elif oportunidade_swing['tipo'] == 'venda':
                    if self._executar_oportunidade_venda(oportunidade_swing):
                        self.logger.info("✅ Venda executada com sucesso (Giro Rápido)!")
                        if not self.modo_simulacao: time.sleep(10)
                        return

        # 3. Verificar oportunidade de venda - Carteira Acumulação
        oportunidade_venda = self.strategy_sell.verificar_oportunidade(preco_atual)
        if oportunidade_venda and self._executar_oportunidade_venda(oportunidade_venda):
            self.logger.info("✅ Venda executada com sucesso (Acumulação)!")
            if not self.modo_simulacao: time.sleep(10)
            return

        # 4. Verificar recompras de segurança - Carteira Acumulação
        oportunidade_recompra = self.strategy_sell.verificar_recompra_de_seguranca(preco_atual)
        if oportunidade_recompra and self._executar_oportunidade_recompra(oportunidade_recompra):
            self.logger.info("✅ Recompra executada com sucesso!")
            if not self.modo_simulacao: time.sleep(10)
            return

        # 5. Tarefas periódicas (só executam em tempo real)
        if not self.modo_simulacao:
            if self.intervalo_verificacao_aportes is not None:
                self._verificar_aportes_brl()
            self._fazer_backup_periodico()

    def _logar_resultados_simulacao(self):
        """Imprime um resumo dos resultados do backtest."""
        self.logger.info("📊" + "="*60)
        self.logger.info("📊 RESULTADOS DA SIMULAÇÃO")
        self.logger.info("📊" + "="*60)

        resultados = self.exchange_api.get_resultados()
        trades = resultados.get('trades', [])
        portfolio_history = resultados.get('portfolio_over_time', [])

        if not portfolio_history:
            self.logger.warning("⚠️ Nenhum histórico de portfólio para analisar.")
            return

        # Análise do Portfólio
        valor_inicial = portfolio_history[0]['total_value_quote']
        valor_final = portfolio_history[-1]['total_value_quote']
        retorno_total = valor_final - valor_inicial
        retorno_percentual = (retorno_total / valor_inicial) * 100 if valor_inicial > 0 else 0

        self.logger.info(f"Valor Inicial do Portfólio: ${valor_inicial:.2f}")
        self.logger.info(f"Valor Final do Portfólio:   ${valor_final:.2f}")
        self.logger.info(f"Retorno Total:              ${retorno_total:.2f} ({retorno_percentual:.2f}%)")

        # Análise de Trades
        if trades:
            total_trades = len(trades)
            compras = [t for t in trades if t['side'] == 'BUY']
            vendas = [t for t in trades if t['side'] == 'SELL']
            total_taxas = sum(t['fee'] for t in trades)

            self.logger.info(f"Total de Trades Executados: {total_trades}")
            self.logger.info(f"  - Compras: {len(compras)}")
            self.logger.info(f"  - Vendas: {len(vendas)}")
            self.logger.info(f"Total de Taxas Pagas:       ${total_taxas:.4f}")
        else:
            self.logger.info("Nenhum trade foi executado durante a simulação.")

        self.logger.info("="*62)

    def get_status_dict(self) -> Dict[str, Any]:
        """
        Coleta e retorna um dicionário com o estado atual do bot.
        Inclui estatísticas das últimas 24h e status da thread.
        Agora inclui informações de AMBAS as carteiras: acumulacao e giro_rapido.
        """
        try:
            preco_atual = self._obter_preco_atual_seguro()
            base_currency, _ = self.config['par'].split('/')
            saldo_disponivel_usdt = self.gestao_capital.saldo_usdt

            # ═══════════════════════════════════════
            # CARTEIRA ACUMULAÇÃO
            # ═══════════════════════════════════════
            quantidade_acumulacao = self.position_manager.get_quantidade_total('acumulacao')
            preco_medio_acumulacao = self.position_manager.get_preco_medio('acumulacao')
            valor_investido_acumulacao = self.position_manager.get_valor_total_investido('acumulacao')
            valor_total_acumulacao = quantidade_acumulacao * preco_atual
            lucro_atual_acumulacao = self.position_manager.calcular_lucro_atual(preco_atual, 'acumulacao')
            lucro_usdt_acumulacao = valor_total_acumulacao - valor_investido_acumulacao

            status_posicao_acumulacao = {
                'quantidade': quantidade_acumulacao,
                'preco_medio': preco_medio_acumulacao,
                'valor_total': valor_total_acumulacao,
                'lucro_percentual': lucro_atual_acumulacao,
                'lucro_usdt': lucro_usdt_acumulacao
            }

            # ═══════════════════════════════════════
            # CARTEIRA GIRO RÁPIDO
            # ═══════════════════════════════════════
            quantidade_giro = self.position_manager.get_quantidade_total('giro_rapido')
            preco_medio_giro = self.position_manager.get_preco_medio('giro_rapido')
            valor_investido_giro = self.position_manager.get_valor_total_investido('giro_rapido')
            valor_total_giro = quantidade_giro * preco_atual
            lucro_atual_giro = self.position_manager.calcular_lucro_atual(preco_atual, 'giro_rapido')
            lucro_usdt_giro = valor_total_giro - valor_investido_giro
            high_water_mark_giro = self.position_manager.get_high_water_mark('giro_rapido')

            status_posicao_giro_rapido = {
                'quantidade': quantidade_giro,
                'preco_medio': preco_medio_giro,
                'valor_total': valor_total_giro,
                'lucro_percentual': lucro_atual_giro,
                'lucro_usdt': lucro_usdt_giro,
                'high_water_mark': high_water_mark_giro
            }

            # ═══════════════════════════════════════
            # TOTAIS CONSOLIDADOS
            # ═══════════════════════════════════════
            quantidade_total = quantidade_acumulacao + quantidade_giro
            valor_total_atual = valor_total_acumulacao + valor_total_giro
            valor_investido_total = valor_investido_acumulacao + valor_investido_giro
            lucro_usdt_total = valor_total_atual - valor_investido_total

            # Calcular lucro percentual consolidado
            lucro_atual_consolidado = None
            if valor_investido_total > 0:
                lucro_atual_consolidado = ((valor_total_atual - valor_investido_total) / valor_investido_total) * Decimal('100')

            # Lógica de estado inteligente
            estado_bot = 'Operando | Aguardando Oportunidade'
            if saldo_disponivel_usdt < 10:
                estado_bot = 'Sem Saldo | Aguardando Venda/Aporte'
            else:
                limite_exposicao = Decimal(str(self.config.get('GESTAO_DE_RISCO', {}).get('exposicao_maxima_percentual_capital', 70.0)))
                alocacao_atual = self.gestao_capital.get_alocacao_percentual_ada()
                if alocacao_atual > limite_exposicao:
                    estado_bot = 'Exposição Máxima | Compras Suspensas'

            # Status consolidado (mantido para compatibilidade)
            status_posicao = {
                'quantidade': quantidade_total,
                'preco_medio': preco_medio_acumulacao,  # Usa PM da acumulação como principal
                'valor_total': valor_total_atual,
                'lucro_percentual': lucro_atual_consolidado,
                'lucro_usdt': lucro_usdt_total
            }

            # Estatísticas das últimas 24h
            try:
                estatisticas_24h = self.db.obter_estatisticas_24h()
            except Exception as e:
                self.logger.warning(f"⚠️ Erro ao obter estatísticas 24h: {e}")
                estatisticas_24h = {
                    'compras': 0,
                    'vendas': 0,
                    'lucro_realizado': 0
                }

            uptime = datetime.now() - self.inicio_bot

            # Obter referência máxima do Giro Rápido (se disponível)
            referencia_maxima_giro = None
            if self.strategy_swing_trade.habilitado and self.strategy_swing_trade.preco_referencia_maxima:
                referencia_maxima_giro = self.strategy_swing_trade.preco_referencia_maxima

            return {
                'nome_instancia': self.config.get('nome_instancia', self.config.get('BOT_NAME')),
                'par': self.config['par'],
                'preco_atual': preco_atual,
                'status_posicao': status_posicao,
                'status_posicao_acumulacao': status_posicao_acumulacao,
                'status_posicao_giro_rapido': status_posicao_giro_rapido,
                'estado_bot': estado_bot,
                'sma_referencia': self.sma_referencia,
                'distancia_sma': self._calcular_distancia_sma(preco_atual),
                'rodando_desde': self.inicio_bot.strftime('%Y-%m-%d %H:%M:%S'),
                'uptime': str(uptime).split('.')[0],
                # Últimas ordens globais (mantido para compatibilidade)
                'ultima_compra': self.db.obter_ultima_ordem('COMPRA'),
                'ultima_venda': self.db.obter_ultima_ordem('VENDA'),
                # Últimas ordens POR ESTRATÉGIA
                'ultima_compra_acumulacao': self.db.obter_ultima_ordem_por_estrategia('COMPRA', 'acumulacao'),
                'ultima_venda_acumulacao': self.db.obter_ultima_ordem_por_estrategia('VENDA', 'acumulacao'),
                'ultima_compra_giro_rapido': self.db.obter_ultima_ordem_por_estrategia('COMPRA', 'giro_rapido'),
                'ultima_venda_giro_rapido': self.db.obter_ultima_ordem_por_estrategia('VENDA', 'giro_rapido'),
                'saldo_disponivel_usdt': saldo_disponivel_usdt,
                'ativo_base': base_currency,
                # Referência máxima do Giro Rápido
                'referencia_maxima_giro': referencia_maxima_giro,
                # Novos campos para relatório horário
                'compras_24h': estatisticas_24h['compras'],
                'vendas_24h': estatisticas_24h['vendas'],
                'lucro_realizado_24h': estatisticas_24h['lucro_realizado'],
                'thread_ativa': self.rodando
            }
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar dicionário de status: {e}", exc_info=True)
            return {
                'nome_instancia': self.config.get('nome_instancia', self.config.get('BOT_NAME')),
                'par': self.config.get('par', 'N/A'),
                'error': str(e),
                'estado_bot': 'ERRO INTERNO',
                'thread_ativa': False
            }

    def get_detailed_status_dict(self) -> Dict[str, Any]:
        """Coleta e retorna um dicionário com o estado detalhado do bot."""
        status = self.get_status_dict()
        strategy_stats = self.strategy_dca.obter_estatisticas()
        status.update(strategy_stats)
        return status


if __name__ == '__main__':
    """Exemplo de uso direto"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv('configs/.env')
    
    # Configuração de exemplo
    config = {
        'BOT_NAME': 'TestBot',
        'DATABASE_PATH': 'dados/bot_trading.db',
        'BACKUP_DIR': 'dados/backup',
        'STATE_FILE_PATH': 'dados/bot_state.json',
        'PERCENTUAL_RESERVA': 8,
        'par': 'ADA/USDT',
        'AMBIENTE': 'teste',
        'CAPITAL_INICIAL': 100.0,
        'VALOR_MINIMO_ORDEM': 5.0,
        'APORTES': {
            'intervalo_verificacao_minutos': 30,
            'valor_minimo_brl_para_converter': 50.0
        },
        'DEGRAUS_COMPRA': [],
        'METAS_VENDA': [],
        'VENDAS_DE_SEGURANCA': [],
        'GESTAO_DE_RISCO': {
            'exposicao_maxima_percentual_capital': 70.0
        }
    }
    
    # API de exemplo
    api = BinanceAPI(
        api_key=os.getenv('BINANCE_API_KEY'),
        api_secret=os.getenv('BINANCE_API_SECRET'),
        base_url='https://api.binance.com'
    )
    
    # Inicializar e executar bot
    bot = BotWorker(config, api)
    bot.run()