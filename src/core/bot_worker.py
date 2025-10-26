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
import pandas as pd
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
        self.gestao_capital = GestaoCapital(
            percentual_reserva=Decimal(str(self.config.get('PERCENTUAL_RESERVA', 8))),
            modo_simulacao=modo_simulacao,
            exchange_api=self.exchange_api
        )
        
        # ===========================================================================
        # CONFIGURAR ALOCAÇÃO DE GIRO RÁPIDO (CRÍTICO!)
        # ===========================================================================
        # Obter percentual de alocação da configuração do giro rápido
        estrategia_giro_config = self.config.get('estrategia_giro_rapido', {})
        alocacao_giro_pct = estrategia_giro_config.get('alocacao_capital_pct', None)

        # ✅ Validação: garantir que foi configurado
        if alocacao_giro_pct is None:
            self.logger.warning("⚠️  AVISO: 'alocacao_capital_pct' não foi encontrado em config['estrategia_giro_rapido']")
            self.logger.warning("           Verifique se perguntar_parametros_giro_rapido() foi chamado em backtest.py")
            self.logger.warning("           Usando fallback: 20% (padrão de segurança)")
            alocacao_giro_pct = Decimal('20')
        else:
            alocacao_giro_pct = Decimal(str(alocacao_giro_pct))

        self.gestao_capital.configurar_alocacao_giro_rapido(alocacao_giro_pct)
        self.logger.info(f"✅ Alocação do Giro Rápido configurada: {alocacao_giro_pct}% do saldo livre")

        # Banco de dados e estado
        self.db = DatabaseManager(
            db_path=Path(self.config['DATABASE_PATH']),
            backup_dir=Path(self.config['BACKUP_DIR'])
        )
        self.state = StateManager(state_file_path=Path(self.config['STATE_FILE_PATH']))

        # Gerenciamento de Stop Loss / Trailing Stop Loss
        self.stops_ativos = {'acumulacao': None, 'giro_rapido': None}
        self._carregar_estado_stops()

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
            carteira='acumulacao',  # StrategySell gerencia vendas da carteira de acumulação
            logger=sell_logger
        )

        # Estratégia de Giro Rápido (Swing Trade)
        self.strategy_swing_trade = StrategySwingTrade(
            config=self.config,
            position_manager=self.position_manager,
            gestao_capital=self.gestao_capital,
            analise_tecnica=self.analise_tecnica,  # NOVO: Passar AnaliseTecnica para cálculo de RSI
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
        
        # Tempo simulado para backtesting
        self.tempo_simulado_atual: Optional[datetime] = None
        
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
        
        # Log de inicialização com status real das instâncias da estratégia
        self.logger.info(f"🤖 BotWorker inicializado. Verificando estado das estratégias:")
        
        # StrategyDCA
        dca_status = "HABILITADA" if self.strategy_dca.habilitado else "DESABILITADA"
        self.logger.info(f"   - StrategyDCA: {dca_status} ({len(self.strategy_dca.degraus_compra)} degraus)")

        # StrategySell (sempre ativa, opera com base na posição)
        self.logger.info(f"   - StrategySell: ATIVA (baseada em posição, {len(self.strategy_sell.metas_venda)} metas)")

        # StrategySwingTrade
        swing_status = "HABILITADA" if self.strategy_swing_trade.habilitado else "DESABILITADA"
        if self.strategy_swing_trade.habilitado:
            self.logger.info(f"   - StrategySwingTrade: {swing_status} (RSI Limite: {self.strategy_swing_trade.rsi_limite_compra}% | Timeframe: {self.strategy_swing_trade.rsi_timeframe_entrada})")
        else:
            self.logger.info(f"   - StrategySwingTrade: {swing_status}")

    def _carregar_estado_stops(self):
        """
        Carrega o estado dos Stop Loss e Trailing Stop Loss do StateManager.

        Recupera estados persistidos das duas carteiras (acumulacao, giro_rapido)
        e restaura as configurações de stop loss ativas.
        """
        try:
            stops_persistidos = self.state.get_state('stops_ativos_persistentes', {})

            if stops_persistidos:
                # Carregar estados para cada carteira
                for carteira in ['acumulacao', 'giro_rapido']:
                    if carteira in stops_persistidos and stops_persistidos[carteira]:
                        dados_stop = stops_persistidos[carteira]

                        # Reconstruir o estado do stop com conversão de tipos
                        self.stops_ativos[carteira] = {
                            'tipo': dados_stop.get('tipo'),
                            'nivel_stop': Decimal(str(dados_stop['nivel_stop'])),
                            'preco_pico': Decimal(str(dados_stop.get('preco_pico', 0))) if dados_stop.get('preco_pico') else None,
                            'distancia_pct': Decimal(str(dados_stop.get('distancia_pct', 0))) if dados_stop.get('distancia_pct') else None
                        }

                        tipo_nome = "Stop Loss" if dados_stop.get('tipo') == 'sl' else "Trailing Stop Loss"
                        self.logger.info(f"🔄 {tipo_nome} restaurado para carteira {carteira}: nível ${self.stops_ativos[carteira]['nivel_stop']:.4f}")
                    else:
                        self.stops_ativos[carteira] = None

                self.logger.info("✅ Estado dos stops carregado com sucesso")
            else:
                self.logger.info("📝 Nenhum stop ativo persistido encontrado - iniciando com estado limpo")

        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar estado dos stops: {e}")
            self.logger.warning("⚠️ Continuando com estado limpo de stops")
            self.stops_ativos = {'acumulacao': None, 'giro_rapido': None}

    def _salvar_estado_stops(self):
        """
        Salva o estado atual dos Stop Loss e Trailing Stop Loss no StateManager.

        Este método deve ser chamado sempre que um stop for:
        - Ativado
        - Desativado
        - Atualizado (ex: trailing stop ajustando o nível)
        """
        try:
            # Preparar dados para serialização JSON (converter Decimal para float)
            stops_serializaveis = {}

            for carteira, dados_stop in self.stops_ativos.items():
                if dados_stop:
                    stops_serializaveis[carteira] = {
                        'tipo': dados_stop['tipo'],
                        'nivel_stop': float(dados_stop['nivel_stop']),
                        'preco_pico': float(dados_stop['preco_pico']) if dados_stop.get('preco_pico') else None,
                        'distancia_pct': float(dados_stop['distancia_pct']) if dados_stop.get('distancia_pct') else None
                    }
                else:
                    stops_serializaveis[carteira] = None

            # Salvar no StateManager
            self.state.set_state('stops_ativos_persistentes', stops_serializaveis)

            self.logger.debug(f"💾 Estado dos stops salvo: {len([s for s in stops_serializaveis.values() if s])} stops ativos")

        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar estado dos stops: {e}")

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

            # Calcular tolerância: usar percentual configurável do saldo da API (mínimo configurável)
            # Tolerância mais alta para evitar reimports por pequenas divergências
            tolerancia_pct = Decimal(str(self.config.get('TOLERANCIA_DIVERGENCIA_PCT', 2.5))) / Decimal('100')
            tolerancia_minima = Decimal(str(self.config.get('TOLERANCIA_DIVERGENCIA_MINIMA', 0.5)))
            tolerancia = max(Decimal(str(saldo_base_real)) * tolerancia_pct, tolerancia_minima)
            
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
            
            # Em modo simulação, usar o método específico para atualizar saldo USDT
            if self.modo_simulacao:
                self.gestao_capital.atualizar_saldo_usdt_simulado(Decimal(str(saldo_quote_real)))
                # Atualizar valor da posição separadamente
                self.gestao_capital.atualizar_saldos(Decimal(str(saldo_quote_real)), valor_posicao_base)
            else:
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
    
    def _obter_tempo_atual(self) -> datetime:
        """
        Obtém o tempo atual correto baseado no modo de operação.
        
        IMPORTANTE: Em modo simulação, usa tempo_simulado_atual (dos dados históricos).
        Em modo tempo real, usa datetime.now() (tempo do sistema).
        
        Returns:
            datetime: Tempo atual (simulado ou real)
        """
        if self.modo_simulacao and self.tempo_simulado_atual is not None:
            return self.tempo_simulado_atual
        return datetime.now()

    def _atualizar_sma_referencia(self):
        """
        Atualiza SMA de referência (4 semanas)
        """
        agora = datetime.now()

        # Atualizar apenas se passou o intervalo configurado ou se nunca foi calculada
        intervalo_atualizacao_horas = self.config.get('INTERVALO_ATUALIZACAO_SMA_HORAS', 1)
        if (
            self.ultima_atualizacao_sma is None
            or (agora - self.ultima_atualizacao_sma) >= timedelta(hours=intervalo_atualizacao_horas)
        ):

            self.logger.info("📊 Calculando SMA de referência (4 semanas)...")
            self.logger.info("🔄 Atualizando SMA de referência (4 semanas)...")

            periodo_dias_sma = self.config.get('PERIODO_DIAS_SMA_REFERENCIA', 28)  # 4 semanas por padrão
            smas = self.analise_tecnica.calcular_sma_multiplos_timeframes(
                simbolo=self.config['par'],
                periodo_dias=periodo_dias_sma
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
            
            # Determinar valor em quote (USDT) para simulação
            # Em simulação, a API espera valor em USDT; em tempo real, espera quantidade do ativo
            valor_quote = None
            if self.modo_simulacao:
                valor_quote = oportunidade.get('valor_ordem') or oportunidade.get('valor_operacao')
                if valor_quote is None:
                    valor_quote = Decimal(str(quantidade)) * Decimal(str(preco_atual))

            # Executar ordem na exchange
            if self.modo_simulacao:
                ordem = self.exchange_api.place_ordem_compra_market(
                    par=self.config['par'],
                    quantidade=float(valor_quote),
                    motivo_compra=tipo.upper(),
                    carteira=carteira
                )
            else:
                ordem = self.exchange_api.place_ordem_compra_market(
                    par=self.config['par'],
                    quantidade=float(quantidade),
                    carteira=carteira
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
                # Usar dados retornados da ordem quando disponíveis (Binance/Simulada)
                executed_qty = ordem.get('executedQty')
                quote_total = ordem.get('cummulativeQuoteQty')
                if executed_qty is not None:
                    quantidade_real = Decimal(str(executed_qty))
                    if quote_total is not None and quantidade_real > 0:
                        preco_real = Decimal(str(quote_total)) / quantidade_real
                    else:
                        preco_real = preco_atual
                else:
                    # Fallback: usar quantidade solicitada e preço atual
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

                # MODO SIMULAÇÃO: Sincronizar saldo USDT com GestaoCapital
                if self.modo_simulacao:
                    novo_saldo_usdt = Decimal(str(self.exchange_api.get_saldo_disponivel('USDT')))
                    self.gestao_capital.set_saldo_usdt_simulado(novo_saldo_usdt, carteira)

                # Registrar na estratégia para ativar cooldowns (passa tempo simulado em backtest)
                if carteira == 'acumulacao':
                    self.strategy_dca.registrar_compra_executada(
                        oportunidade,
                        quantidade_real,
                        tempo_atual=self._obter_tempo_atual()
                    )
                elif carteira == 'giro_rapido':
                    # Passar tempo atual (timestamp em segundos) para swing trade
                    tempo_atual_timestamp = self.tempo_simulado_atual.timestamp() if self.modo_simulacao and self.tempo_simulado_atual else None
                    self.strategy_swing_trade.registrar_compra_executada(oportunidade, tempo_atual_timestamp)

                    # ═══════════════════════════════════════════════════════════════
                    # NOVO: ATIVAR STOP LOSS INICIAL PARA GIRO_RAPIDO
                    # ═══════════════════════════════════════════════════════════════
                    # Após compra, ativar automaticamente o SL inicial
                    stop_loss_inicial_pct = self.strategy_swing_trade.stop_loss_inicial_pct
                    nivel_sl = preco_real * (Decimal('1') - stop_loss_inicial_pct / Decimal('100'))

                    self.stops_ativos['giro_rapido'] = {
                        'tipo': 'sl',
                        'nivel_stop': nivel_sl,
                        'preco_compra': preco_real
                    }

                    self._salvar_estado_stops()

                    self.logger.info(f"🛡️ STOP LOSS INICIAL ATIVADO (Giro Rápido)")
                    self.logger.info(f"   Preço de Compra: ${preco_real:.6f}")
                    self.logger.info(f"   Nível SL: ${nivel_sl:.6f}")
                    self.logger.info(f"   Distância: {stop_loss_inicial_pct:.2f}%")

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
                    'observacao': f"{tipo.upper()}: {oportunidade['motivo']}",
                    'timestamp': self._obter_tempo_atual().isoformat()
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

            # Determinar motivo de saída para rastreamento em backtests
            # Tipos possíveis: META, SEGURANCA, MANUAL
            motivo_saida = 'META' if oportunidade.get('meta') else 'SEGURANCA'
            if tipo == 'manual':
                motivo_saida = 'MANUAL'

            # Executar ordem na exchange
            ordem = self.exchange_api.place_ordem_venda_market(
                par=self.config['par'],
                quantidade=float(quantidade),
                motivo_saida=motivo_saida,  # Passar motivo para API simulada
                carteira=carteira
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
                # Usar dados retornados da ordem quando disponíveis (Binance/Simulada)
                executed_qty = ordem.get('executedQty')
                quote_total = ordem.get('cummulativeQuoteQty')
                if executed_qty is not None:
                    quantidade_real = Decimal(str(executed_qty))
                    valor_real = Decimal(str(quote_total)) if quote_total is not None else quantidade_real * preco_atual
                    preco_real = valor_real / quantidade_real if quantidade_real > 0 else preco_atual
                else:
                    # Fallback: usar quantidade solicitada e preço atual
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

                # MODO SIMULAÇÃO: Sincronizar saldo USDT com GestaoCapital
                if self.modo_simulacao:
                    novo_saldo_usdt = Decimal(str(self.exchange_api.get_saldo_disponivel('USDT')))
                    self.gestao_capital.set_saldo_usdt_simulado(novo_saldo_usdt, carteira)

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
                    'observacao': f"{tipo.upper()}: {oportunidade['motivo']}",
                    'timestamp': self._obter_tempo_atual().isoformat()
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
            carteira = oportunidade.get('carteira', 'acumulacao')  # Padrão: acumulacao

            self.logger.info(f"🔄 Executando recompra: {oportunidade['motivo']}")

            # Determinar valor em quote (USDT) para simulação
            valor_quote = None
            if self.modo_simulacao:
                valor_quote = oportunidade.get('valor_ordem') or oportunidade.get('valor_operacao')
                if valor_quote is None:
                    valor_quote = Decimal(str(quantidade)) * Decimal(str(preco_atual))

            # Executar ordem na exchange
            if self.modo_simulacao:
                ordem = self.exchange_api.place_ordem_compra_market(
                    par=self.config['par'],
                    quantidade=float(valor_quote),
                    motivo_compra='RECOMPRA',
                    carteira=carteira
                )
            else:
                ordem = self.exchange_api.place_ordem_compra_market(
                    par=self.config['par'],
                    quantidade=float(quantidade),
                    carteira=carteira
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
                # Usar dados retornados da ordem quando disponíveis (Binance/Simulada)
                executed_qty = ordem.get('executedQty')
                quote_total = ordem.get('cummulativeQuoteQty')
                if executed_qty is not None:
                    quantidade_real = Decimal(str(executed_qty))
                    valor_real = Decimal(str(quote_total)) if quote_total is not None else quantidade_real * preco_atual
                    preco_real = valor_real / quantidade_real if quantidade_real > 0 else preco_atual
                else:
                    # Fallback: usar quantidade solicitada e preço atual
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

                # Atualizar position manager (recompras sempre são da carteira acumulação)
                carteira_recompra = 'acumulacao'
                self.position_manager.atualizar_apos_compra(quantidade_real, preco_real, carteira_recompra)

                # MODO SIMULAÇÃO: Sincronizar saldo USDT com GestaoCapital
                if self.modo_simulacao:
                    novo_saldo_usdt = Decimal(str(self.exchange_api.get_saldo_disponivel('USDT')))
                    self.gestao_capital.set_saldo_usdt_simulado(novo_saldo_usdt, carteira_recompra)

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
                    'observacao': f"RECOMPRA: {oportunidade['motivo']}",
                    'timestamp': self._obter_tempo_atual().isoformat()
                }, estrategia='acumulacao')

                return True
            else:
                self.logger.error(f"❌ Erro ao executar recompra: {ordem}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Erro ao executar recompra: {e}")
            return False

    def _executar_venda_stop(self, carteira: str, tipo_stop: str):
        """
        Executa venda por acionamento de Stop Loss ou Trailing Stop Loss.

        Args:
            carteira: Nome da carteira ('acumulacao' ou 'giro_rapido')
            tipo_stop: Tipo do stop ('sl' para Stop Loss, 'tsl' para Trailing Stop Loss)
        """
        try:
            tipo_nome = "Stop Loss" if tipo_stop == 'sl' else "Trailing Stop Loss"
            tipo_sigla = "SL" if tipo_stop == 'sl' else "TSL"

            self.logger.warning(f"🚨 {tipo_nome} ACIONADO para carteira '{carteira}'")
            self.logger.warning(f"   📊 Nível de stop: ${self.stops_ativos[carteira]['nivel_stop']:.4f}")

            if tipo_stop == 'tsl':
                self.logger.warning(f"   📈 Preço pico: ${self.stops_ativos[carteira]['preco_pico']:.4f}")
                self.logger.warning(f"   📏 Distância: {self.stops_ativos[carteira]['distancia_pct']:.2f}%")

            # ═══════════════════════════════════════════════════════════════════
            # 1. DETERMINAR QUANTIDADE A VENDER
            # ═══════════════════════════════════════════════════════════════════
            quantidade_total_carteira = self.position_manager.get_quantidade_total(carteira)

            if quantidade_total_carteira <= 0:
                self.logger.warning(f"⚠️ Carteira '{carteira}' não possui posição para vender no stop")
                # Limpar o stop mesmo sem posição
                self.stops_ativos[carteira] = None
                self._salvar_estado_stops()
                return

            # Determinar percentual de venda baseado na carteira
            # OPÇÃO A: VENDA TOTAL (100%) PARA AMBAS AS CARTEIRAS
            if carteira == 'giro_rapido':
                # Giro Rápido: vender 100% da posição
                percentual_venda = Decimal('100')
                quantidade_a_vender = quantidade_total_carteira
            else:
                # Acumulação: vender 100% da posição (OPÇÃO A - Venda Total)
                percentual_venda = Decimal('100')
                quantidade_a_vender = quantidade_total_carteira

            # Obter preço atual para cálculo de lucro
            preco_atual = self._obter_preco_atual_seguro()
            preco_medio = self.position_manager.get_preco_medio(carteira)

            # Calcular lucro antes da venda
            lucro_pct = Decimal('0')
            if preco_medio:
                lucro_pct = ((preco_atual - preco_medio) / preco_medio) * Decimal('100')

            self.logger.warning(f"💰 Executando venda por {tipo_nome}:")
            self.logger.warning(f"   • Quantidade total [{carteira}]: {quantidade_total_carteira:.4f}")
            self.logger.warning(f"   • Percentual de venda: {percentual_venda:.1f}%")
            self.logger.warning(f"   • Quantidade a vender: {quantidade_a_vender:.4f}")
            self.logger.warning(f"   • Preço médio: ${preco_medio:.6f}")
            self.logger.warning(f"   • Preço atual: ${preco_atual:.6f}")
            self.logger.warning(f"   • Lucro: {lucro_pct:.2f}%")

            # ═══════════════════════════════════════════════════════════════════
            # 2. EXECUTAR ORDEM DE VENDA NA EXCHANGE
            # ═══════════════════════════════════════════════════════════════════
            base_currency = self.config['par'].split('/')[0]

            # Determinar motivo de saída para rastreamento em backtests
            motivo_saida = tipo_sigla  # 'SL' ou 'TSL'

            ordem = self.exchange_api.place_ordem_venda_market(
                par=self.config['par'],
                quantidade=float(quantidade_a_vender),
                motivo_saida=motivo_saida,  # Passar motivo para API simulada
                carteira=carteira
            )

            # Verificar se a ordem foi executada com sucesso
            ordem_executada = False
            if hasattr(self.exchange_api, '__class__') and 'Binance' in self.exchange_api.__class__.__name__:
                ordem_executada = ordem and ordem.get('status') == 'FILLED'
            else:
                # KuCoin e outras exchanges
                ordem_executada = ordem and (ordem.get('orderId') or ordem.get('id'))

            # ═══════════════════════════════════════════════════════════════════
            # 3. PROCESSAR RESULTADO DA VENDA
            # ═══════════════════════════════════════════════════════════════════
            if ordem_executada:
                # Extrair dados da ordem executada (usar executedQty/cummulativeQuoteQty quando disponíveis)
                executed_qty = ordem.get('executedQty')
                quote_total = ordem.get('cummulativeQuoteQty')
                if executed_qty is not None:
                    quantidade_real = Decimal(str(executed_qty))
                    valor_real = Decimal(str(quote_total)) if quote_total is not None else quantidade_real * preco_atual
                    preco_real = valor_real / quantidade_real if quantidade_real > 0 else preco_atual
                else:
                    quantidade_real = Decimal(str(quantidade_a_vender))
                    valor_real = quantidade_real * preco_atual
                    preco_real = preco_atual

                # Recalcular lucro com preço real
                lucro_usdt = Decimal('0')
                if preco_medio:
                    lucro_pct = ((preco_real - preco_medio) / preco_medio) * Decimal('100')
                    lucro_usdt = (preco_real - preco_medio) * quantidade_real

                self.logger.warning(f"✅ Venda por {tipo_nome} EXECUTADA com sucesso!")
                self.logger.warning(f"   • Quantidade vendida: {quantidade_real:.4f} {base_currency}")
                self.logger.warning(f"   • Preço de venda: ${preco_real:.6f}")
                self.logger.warning(f"   • Valor total: ${valor_real:.2f}")
                self.logger.warning(f"   • Lucro: ${lucro_usdt:.2f} ({lucro_pct:.2f}%)")

                # Log estruturado de operação
                self.main_logger.operacao_venda(
                    par=self.config['par'],
                    quantidade=float(quantidade_real),
                    preco=float(preco_real),
                    meta=f"{tipo_sigla}_{carteira}",
                    lucro_pct=float(lucro_pct),
                    lucro_usd=float(lucro_usdt)
                )

                # a. Atualizar position manager com a carteira correta
                self.position_manager.atualizar_apos_venda(quantidade_real, carteira)

                # b. Limpar o stop ativo para essa carteira
                self.stops_ativos[carteira] = None

                # c. Salvar estado dos stops
                self._salvar_estado_stops()

                # d. Enviar notificação de sucesso
                if self.notifier:
                    carteira_emoji = "📊" if carteira == 'acumulacao' else "🎯"
                    carteira_nome = "Acumulação" if carteira == 'acumulacao' else "Giro Rápido"
                    self.notifier.enviar_alerta(
                        f"🚨 VENDA POR {tipo_sigla} [{carteira_emoji} {carteira_nome}]",
                        f"Tipo: {tipo_nome}\n"
                        f"Quantidade: {quantidade_real:.2f} {base_currency}\n"
                        f"Preço: ${preco_real:.6f}\n"
                        f"Valor: ${valor_real:.2f}\n"
                        f"Lucro: ${lucro_usdt:.2f} ({lucro_pct:.2f}%)"
                    )

                # Extrair order_id com fallback
                order_id = ordem.get('orderId') or ordem.get('id')
                if not order_id:
                    self.logger.warning(f"⚠️ Ordem de VENDA por {tipo_sigla} executada mas sem ID retornado pela exchange")

                # Determinar estratégia com base na carteira
                estrategia_nome = 'acumulacao' if carteira == 'acumulacao' else 'giro_rapido'

                # Salvar no banco de dados
                self._salvar_ordem_banco({
                    'tipo': 'VENDA',
                    'par': self.config['par'],
                    'quantidade': quantidade_real,
                    'preco': preco_real,
                    'valor_total': valor_real,
                    'taxa': ordem.get('fills', [{}])[0].get('commission', 0) if ordem.get('fills') else 0,
                    'meta': f"{tipo_sigla}_{carteira}",
                    'lucro_percentual': lucro_pct,
                    'lucro_usdt': lucro_usdt,
                    'order_id': order_id,
                    'observacao': f"VENDA POR {tipo_nome.upper()} - Carteira: {carteira}",
                    'timestamp': self._obter_tempo_atual().isoformat()
                }, estrategia=estrategia_nome)

                self.logger.warning(f"🛡️ Stop {tipo_sigla} desativado para carteira '{carteira}'")

            else:
                # Falha na execução da ordem
                self.logger.error(f"❌ FALHA ao executar venda por {tipo_nome}!")
                self.logger.error(f"   Resposta da exchange: {ordem}")

                # Enviar notificação de falha
                if self.notifier:
                    carteira_emoji = "📊" if carteira == 'acumulacao' else "🎯"
                    carteira_nome = "Acumulação" if carteira == 'acumulacao' else "Giro Rápido"
                    self.notifier.enviar_alerta(
                        f"❌ FALHA VENDA POR {tipo_sigla} [{carteira_emoji} {carteira_nome}]",
                        f"Tipo: {tipo_nome}\n"
                        f"Quantidade tentada: {quantidade_a_vender:.2f} {base_currency}\n"
                        f"Erro: Ordem não foi executada pela exchange\n"
                        f"Verifique logs e estado da API"
                    )

                # Manter o stop ativo em caso de falha
                self.logger.warning(f"⚠️ Stop {tipo_sigla} mantido ativo para carteira '{carteira}' devido à falha")

        except Exception as e:
            self.logger.error(f"❌ Erro crítico ao executar venda por {tipo_nome}: {e}")
            import traceback
            self.logger.error(f"Traceback:\n{traceback.format_exc()}")

            # Enviar notificação de erro crítico
            if self.notifier:
                self.notifier.enviar_alerta(
                    f"❌ ERRO CRÍTICO - VENDA POR {tipo_sigla}",
                    f"Carteira: {carteira}\n"
                    f"Tipo: {tipo_nome}\n"
                    f"Erro: {str(e)}\n"
                    f"Verifique logs imediatamente!"
                )

    def _ativar_stop_loss_inicial(self, oportunidade: Dict[str, Any]):
        """
        Ativa Stop Loss inicial após uma compra (usado principalmente por Giro Rápido).

        Args:
            oportunidade: Dicionário da oportunidade de compra que contém 'stop_loss_nivel'
        """
        try:
            carteira = oportunidade.get('carteira', 'giro_rapido')
            stop_loss_nivel = oportunidade.get('stop_loss_nivel')

            if not stop_loss_nivel:
                self.logger.warning(f"⚠️ Compra realizada sem nível de stop loss definido [{carteira}]")
                return

            # Ativar Stop Loss para a carteira
            self.stops_ativos[carteira] = {
                'tipo': 'sl',
                'nivel_stop': Decimal(str(stop_loss_nivel)),
                'preco_pico': None,  # SL fixo não usa pico
                'distancia_pct': None  # SL fixo não usa distância
            }

            # Salvar estado persistente
            self._salvar_estado_stops()

            self.logger.info(f"🛡️ Stop Loss ATIVADO [{carteira}]")
            self.logger.info(f"   📍 Nível: ${stop_loss_nivel:.6f}")
            self.logger.info(f"   📊 Preco compra: ${oportunidade.get('preco_atual', 0):.6f}")

            # Notificação
            if self.notifier:
                carteira_nome = "Giro Rápido" if carteira == 'giro_rapido' else "Acumulação"
                self.notifier.enviar_info(
                    f"🛡️ Stop Loss Ativado [{carteira_nome}]",
                    f"Nível: ${stop_loss_nivel:.6f}"
                )

        except Exception as e:
            self.logger.error(f"❌ Erro ao ativar Stop Loss inicial: {e}")

    def _ativar_trailing_stop(self, oportunidade: Dict[str, Any], preco_atual: Decimal):
        """
        Ativa Trailing Stop Loss quando uma meta é atingida PELA PRIMEIRA VEZ.
        
        IMPORTANTE: Este método só deve ser chamado UMA ÚNICA VEZ por trade.
        Depois de ativado, o TSL será apenas ATUALIZADO no loop principal.

        Args:
            oportunidade: Dicionário com dados da oportunidade (acao: 'ativar_tsl')
            preco_atual: Preço atual da moeda
        """
        try:
            carteira = oportunidade.get('carteira', 'acumulacao')
            distancia_pct = oportunidade.get('distancia_pct')

            if not distancia_pct:
                self.logger.error(f"❌ Tentativa de ativar TSL sem distância_pct definida [{carteira}]")
                return

            distancia_pct = Decimal(str(distancia_pct))

            # ═══════════════════════════════════════════════════════════════════
            # VERIFICAÇÃO CRÍTICA: Se já existe um TSL ativo, NÃO reativar
            # ═══════════════════════════════════════════════════════════════════
            if self.stops_ativos.get(carteira) and self.stops_ativos[carteira]['tipo'] == 'tsl':
                self.logger.warning(f"⚠️ TSL já está ATIVO para [{carteira}] - ignorando reativação")
                self.logger.debug(f"   📊 Pico atual: ${self.stops_ativos[carteira]['preco_pico']:.6f}")
                self.logger.debug(f"   📍 Nível stop atual: ${self.stops_ativos[carteira]['nivel_stop']:.6f}")
                return

            # Calcular nível inicial do TSL baseado no preço atual
            nivel_stop_inicial = preco_atual * (Decimal('1') - distancia_pct / Decimal('100'))

            # ═══════════════════════════════════════════════════════════════════
            # ATIVAÇÃO ÚNICA: Criar novo TSL
            # ═══════════════════════════════════════════════════════════════════
            self.stops_ativos[carteira] = {
                'tipo': 'tsl',
                'nivel_stop': nivel_stop_inicial,
                'preco_pico': preco_atual,  # Pico inicial é o preço atual
                'distancia_pct': distancia_pct
            }

            # Cancelar qualquer Stop Loss inicial (sl) que estivesse ativo
            # (relevante principalmente para Giro Rápido que pode ter sl inicial)
            if self.stops_ativos.get(carteira) and self.stops_ativos[carteira].get('tipo') == 'sl':
                self.logger.info(f"🔄 Cancelando Stop Loss inicial [{carteira}] (TSL assume controle)")

            # Salvar estado persistente
            self._salvar_estado_stops()

            self.logger.info(f"🛡️ Trailing Stop Loss ATIVADO PELA PRIMEIRA VEZ [{carteira}]")
            self.logger.info(f"   📈 Pico inicial: ${preco_atual:.6f}")
            self.logger.info(f"   📍 Nível stop inicial: ${nivel_stop_inicial:.6f}")
            self.logger.info(f"   📏 Distância configurada: {distancia_pct:.2f}%")
            self.logger.info(f"   🎯 Meta atingida: {oportunidade.get('meta_atingida', 'N/A')}")

            # Notificação
            if self.notifier:
                carteira_nome = "Acumulação" if carteira == 'acumulacao' else "Giro Rápido"
                lucro_atual = oportunidade.get('lucro_atual', 0)
                self.notifier.enviar_sucesso(
                    f"🛡️ Trailing Stop Ativado [{carteira_nome}]",
                    f"Meta atingida: {oportunidade.get('meta_atingida', 'N/A')}\n"
                    f"Lucro atual: {lucro_atual:.2f}%\n"
                    f"Nível stop: ${nivel_stop_inicial:.6f} ({distancia_pct:.2f}%)"
                )

        except Exception as e:
            self.logger.error(f"❌ Erro ao ativar Trailing Stop Loss: {e}")

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
        Loop principal do bot worker.
        """
        try:
            self.main_logger.banner("🤖 BOT DE TRADING INICIADO")
            self.logger.info(f"Par: {self.config['par']}")
            self.logger.info(f"Ambiente: {self.config['AMBIENTE']}")
            self.logger.info(f"Modo Simulação: {'ATIVADO' if self.modo_simulacao else 'DESATIVADO'}")
            self.logger.info(f"Capital inicial: ${self.config['CAPITAL_INICIAL']}")

            if not self.modo_simulacao:
                if not self.exchange_api.check_connection():
                    self.logger.error("❌ Falha na conexão com a exchange")
                    return
                self.logger.info("✅ Conectado à Exchange")
                self._sincronizar_saldos_exchange()
                self._atualizar_sma_referencia()

            self.rodando = True
            
            if self.modo_simulacao:
                self._sincronizar_saldos_exchange()
                self._run_simulacao()
            else:
                # Lógica de operação em tempo real (produção)
                self.logger.info("🟢 Iniciando worker em MODO DE TEMPO REAL.")
                while self.rodando:
                    try:
                        preco_atual = self._obter_preco_atual_seguro()
                        # Capturar tempo real para passar para funções de cooldown
                        tempo_atual = datetime.now()
                        
                        self._executar_ciclo_decisao(preco_atual, tempo_atual)
                        
                        intervalo_ciclo_segundos = self.config.get('INTERVALO_CICLO_SEGUNDOS', 5)
                        time.sleep(intervalo_ciclo_segundos)

                    except KeyboardInterrupt:
                        self.logger.info("🛑 Interrupção solicitada pelo usuário.")
                        self.rodando = False
                        continue
                    except Exception as e:
                        self.logger.error(f'Erro inesperado no loop principal: {e}', exc_info=True)
                        self.estado_bot = 'ERRO'
                        pausa_apos_erro = self.config.get('PAUSA_APOS_ERRO_SEGUNDOS', 60)
                        time.sleep(pausa_apos_erro)
                        continue
        
        except Exception as e:
            self.logger.error(f"❌ Erro fatal no bot: {e}", exc_info=True)
            raise

    def _run_simulacao(self):
        """
        Executa o loop principal para o modo de simulação (backtesting).
        Itera sobre os dados históricos e usa o timestamp da vela como o tempo atual.
        """
        self.logger.info("🏁 Iniciando worker em MODO DE SIMULAÇÃO.")
        # Atualizar SMA de referência antes de iniciar o loop de simulação
        try:
            self._atualizar_sma_referencia()
        except Exception as e:
            self.logger.warning(f"⚠️ Não foi possível calcular SMA de referência antes da simulação: {e}")
        
        # Loop principal do backtest
        while self.rodando and (barra := self.exchange_api.get_barra_atual()) is not None:
            try:
                # TEMPO SIMULADO: Capturar timestamp da barra
                tempo_simulado = pd.to_datetime(barra['timestamp'])
                preco_atual = Decimal(str(barra['close']))
                
                # Executa o ciclo de decisão com os dados e tempo da simulação
                # Passando tempo_simulado para todas as funções que verificam cooldowns
                self._executar_ciclo_decisao(preco_atual, tempo_simulado)

            except KeyboardInterrupt:
                self.logger.info("🛑 Interrupção solicitada pelo usuário durante a simulação.")
                self.rodando = False
                break
            except Exception as e:
                self.logger.error(f'❌ Erro inesperado no loop de simulação: {e}', exc_info=True)
                self.rodando = False
                break
        
        self.logger.info("🏁 Simulação finalizada.")
        if hasattr(self.exchange_api, 'get_resultados'):
            self._logar_resultados_simulacao()

    def _executar_ciclo_decisao(self, preco_atual: Decimal, tempo_atual: datetime):
        """
        Contém a lógica de decisão principal do bot, chamada em cada ciclo.
        É agnóstico ao modo (simulação ou tempo real), operando com o tempo e preço fornecidos.
        """
        # Atualizar o tempo do worker (relevante para simulação)
        self.tempo_simulado_atual = tempo_atual if self.modo_simulacao else None

        # Processar comandos remotos
        self._processar_comandos()

        # ═══════════════════════════════════════════════════════════════════
        # VERIFICAÇÃO E ATUALIZAÇÃO DE STOP LOSS E TRAILING STOP LOSS
        # ═══════════════════════════════════════════════════════════════════
        for carteira in ['acumulacao', 'giro_rapido']:
            stop_ativo = self.stops_ativos.get(carteira)

            if stop_ativo:
                # ═══════════════════════════════════════════════════════════════
                # ATUALIZAÇÃO CONTÍNUA: Se for TSL JÁ ATIVO, apenas atualizar
                # ═══════════════════════════════════════════════════════════════
                if stop_ativo['tipo'] == 'tsl':
                    # a) Verificar se preço atual ultrapassou o pico registrado
                    if preco_atual > stop_ativo['preco_pico']:
                        # Atualizar pico e recalcular nível de stop
                        stop_ativo['preco_pico'] = preco_atual
                        stop_ativo['nivel_stop'] = preco_atual * (Decimal('1') - stop_ativo['distancia_pct'] / Decimal('100'))
                        self._salvar_estado_stops()
                        self.logger.debug(f"🔄 TSL ATUALIZADO [{carteira}]: Pico ${preco_atual:.4f}, Nível ${stop_ativo['nivel_stop']:.4f}")
                    
                    # b) Verificar se preço caiu abaixo do nível de stop
                    if preco_atual <= stop_ativo['nivel_stop']:
                        self.logger.warning(f"⚠️ Trailing Stop Loss ACIONADO [{carteira}]!")
                        self.logger.warning(f"   📈 Pico máximo: ${stop_ativo['preco_pico']:.6f}")
                        self.logger.warning(f"   📍 Nível stop: ${stop_ativo['nivel_stop']:.6f}")
                        self.logger.warning(f"   📉 Preço atual: ${preco_atual:.6f}")
                        self._executar_venda_stop(carteira, 'tsl')
                        continue  # Pular resto do ciclo após executar venda
                
                # ═══════════════════════════════════════════════════════════════
                # STOP LOSS FIXO: Com PROMOÇÃO para TSL (Giro Rápido apenas)
                # ═══════════════════════════════════════════════════════════════
                elif stop_ativo['tipo'] == 'sl':
                    # VERIFICAÇÃO 1: Se Stop Loss foi disparado → VENDER
                    if preco_atual <= stop_ativo['nivel_stop']:
                        self.logger.warning(f"⚠️ Stop Loss ACIONADO [{carteira}]!")
                        self.logger.warning(f"   📍 Nível stop: ${stop_ativo['nivel_stop']:.6f}")
                        self.logger.warning(f"   📉 Preço atual: ${preco_atual:.6f}")
                        self._executar_venda_stop(carteira, 'sl')
                        continue  # Pular resto do ciclo após executar venda

                    # VERIFICAÇÃO 2: PROMOÇÃO (SL → TSL) APENAS PARA GIRO_RAPIDO
                    # Promover SL para TSL quando atingir gatilho de lucro mínimo
                    if carteira == 'giro_rapido':
                        preco_medio = self.position_manager.get_preco_medio('giro_rapido')
                        if preco_medio:
                            # Calcular lucro percentual
                            lucro_pct = ((preco_atual - preco_medio) / preco_medio) * Decimal('100')

                            # Obter gatilho de lucro mínimo da config (padrão: 0% para breakeven)
                            estrategia_config = self.config.get('estrategia_giro_rapido', {})
                            tsl_gatilho_lucro = Decimal(str(estrategia_config.get('tsl_gatilho_lucro_pct', 0)))

                            # Verificar se atingiu o gatilho de lucro mínimo
                            if lucro_pct >= tsl_gatilho_lucro:
                                # GATILHO ATINGIDO: Promover para TSL
                                distancia_tsl_pct = self.strategy_swing_trade.trailing_stop_distancia_pct

                                self.logger.info(f"🎯 PROMOÇÃO DE STOP [{carteira}] - GATILHO DE LUCRO ATINGIDO")
                                self.logger.info(f"   Stop Loss Inicial → Trailing Stop Loss")
                                self.logger.info(f"   Preço Médio: ${preco_medio:.6f}")
                                self.logger.info(f"   Preço Atual: ${preco_atual:.6f}")
                                self.logger.info(f"   Lucro: {lucro_pct:+.2f}% (Gatilho: {tsl_gatilho_lucro:.2f}%)")
                                self.logger.info(f"   TSL Distância: {distancia_tsl_pct:.2f}%")

                                # Desativar SL e ativar TSL
                                nivel_tsl_inicial = preco_atual * (Decimal('1') - distancia_tsl_pct / Decimal('100'))

                                self.stops_ativos['giro_rapido'] = {
                                    'tipo': 'tsl',
                                    'nivel_stop': nivel_tsl_inicial,
                                    'preco_pico': preco_atual,
                                    'distancia_pct': distancia_tsl_pct
                                }

                                self._salvar_estado_stops()

                                # Notificar
                                if self.notifier:
                                    self.notifier.enviar_sucesso(
                                        f"🎯 Stop Promovido [Giro Rápido]",
                                        f"SL Inicial → Trailing Stop Loss\n"
                                        f"Lucro mínimo atingido: {lucro_pct:+.2f}% (gatilho: {tsl_gatilho_lucro:.2f}%)\n"
                                        f"Preço atual: ${preco_atual:.6f}\n"
                                        f"TSL Nível: ${nivel_tsl_inicial:.6f}\n"
                                        f"TSL Distância: {distancia_tsl_pct:.2f}%"
                                    )

                                continue  # Pular resto do ciclo após promoção

        # Calcular distância da SMA
        distancia_sma = self._calcular_distancia_sma(preco_atual)

        # ═══════════════════════════════════════════════════════════════════
        # ESTRATÉGIA DCA/ACUMULAÇÃO (apenas se ativa)
        # ═══════════════════════════════════════════════════════════════════
        if self.estrategia_ativa in ['dca', 'ambas']:
            # 2. Verificar oportunidade de compra (DCA) - Carteira Acumulação
            if distancia_sma:
                oportunidade_compra = self.strategy_dca.verificar_oportunidade(
                    preco_atual=preco_atual,
                    distancia_sma=distancia_sma,
                    tempo_atual=self._obter_tempo_atual()  # Usa tempo simulado em backtest
                )
                if oportunidade_compra and self._executar_oportunidade_compra(oportunidade_compra):
                    self.logger.info("✅ Compra executada com sucesso (Acumulação)!")
                    pausa_apos_operacao = self.config.get('PAUSA_APOS_OPERACAO_SEGUNDOS', 10)
                    if not self.modo_simulacao: time.sleep(pausa_apos_operacao)
                    return

            # 3. Verificar oportunidade de venda - Carteira Acumulação
            oportunidade_venda = self.strategy_sell.verificar_oportunidade(preco_atual)
            if oportunidade_venda:
                # Verificar se é ativação de TSL
                if oportunidade_venda.get('acao') == 'ativar_tsl':
                    self._ativar_trailing_stop(oportunidade_venda, preco_atual)
                    return
                # Senão, é venda direta (vendas de segurança)
                elif self._executar_oportunidade_venda(oportunidade_venda):
                    self.logger.info("✅ Venda executada com sucesso (Acumulação)!")
                    pausa_apos_operacao = self.config.get('PAUSA_APOS_OPERACAO_SEGUNDOS', 10)
                    if not self.modo_simulacao: time.sleep(pausa_apos_operacao)
                    return

            # 4. Verificar recompras de segurança - Carteira Acumulação
            oportunidade_recompra = self.strategy_sell.verificar_recompra_de_seguranca(preco_atual)
            if oportunidade_recompra and self._executar_oportunidade_recompra(oportunidade_recompra):
                self.logger.info("✅ Recompra executada com sucesso!")
                pausa_apos_operacao = self.config.get('PAUSA_APOS_OPERACAO_SEGUNDOS', 10)
                if not self.modo_simulacao: time.sleep(pausa_apos_operacao)
                return

        # ESTRATÉGIA GIRO RÁPIDO (apenas se ativa)
        # ═══════════════════════════════════════════════════════════════════
        if self.estrategia_ativa in ['giro', 'ambas']:
            # 2b. Verificar oportunidade de Swing Trade (Giro Rápido)
            if self.strategy_swing_trade.habilitado:
                # Passar tempo atual (timestamp em segundos) para swing trade
                tempo_atual_timestamp = self.tempo_simulado_atual.timestamp() if self.modo_simulacao and self.tempo_simulado_atual else None
                oportunidade_swing = self.strategy_swing_trade.verificar_oportunidade(preco_atual, tempo_atual_timestamp)
                if oportunidade_swing:
                    if oportunidade_swing.get('tipo') == 'compra':
                        if self._executar_oportunidade_compra(oportunidade_swing):
                            self.logger.info("✅ Compra executada com sucesso (Giro Rápido)!")
                            # NOTA: Stop Loss Inicial é ativado automaticamente em _executar_oportunidade_compra
                            pausa_apos_operacao = self.config.get('PAUSA_APOS_OPERACAO_SEGUNDOS', 10)
                            if not self.modo_simulacao: time.sleep(pausa_apos_operacao)
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