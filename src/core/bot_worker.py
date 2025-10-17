#!/usr/bin/env python3
"""
Bot Worker - Orquestrador de Estratégias de Trading
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import time
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
from src.persistencia.database import DatabaseManager
from src.persistencia.state_manager import StateManager
from src.utils.logger import get_loggers
from src.utils.constants import Icones, LogConfig


class BotWorker:
    """Bot Worker - Orquestrador de Estratégias de Trading"""

    def __init__(self, config: Dict[str, Any], exchange_api: ExchangeAPI):
        """Inicializar bot worker"""
        self.config = config
        self.exchange_api = exchange_api

        self.logger, self.panel_logger = get_loggers(
            nome=self.config.get('BOT_NAME', 'BotWorker'),
            log_dir=Path('logs'),
            config=LogConfig.DEFAULT,
            console=True
        )

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

        # ═══════════════════════════════════════════════════════════════════
        # NOVA ARQUITETURA: Componentes Estratégicos
        # ═══════════════════════════════════════════════════════════════════
        
        # Gerenciador de posições
        self.position_manager = PositionManager(self.db)
        
        # Estratégias
        self.strategy_dca = StrategyDCA(
            config=self.config,
            position_manager=self.position_manager,
            gestao_capital=self.gestao_capital,
            state_manager=self.state
        )
        
        self.strategy_sell = StrategySell(
            config=self.config,
            position_manager=self.position_manager,
            state_manager=self.state
        )

        # Estado do bot
        self.sma_referencia: Optional[Decimal] = None
        self.sma_1h: Optional[Decimal] = None
        self.sma_4h: Optional[Decimal] = None
        self.ultima_atualizacao_sma = None
        self.ultimo_backup = datetime.now()
        self.rodando = False
        self.inicio_bot = datetime.now()

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
        
        self.logger.info(f"🤖 BotWorker inicializado com arquitetura de estratégias")
        self.logger.info(f"   📊 PositionManager: {'COM POSIÇÃO' if self.position_manager.tem_posicao() else 'SEM POSIÇÃO'}")
        self.logger.info(f"   🎯 StrategyDCA: {len(self.strategy_dca.degraus_compra)} degraus")
        self.logger.info(f"   💰 StrategySell: {len(self.strategy_sell.metas_venda)} metas")

    def _sincronizar_saldos_exchange(self):
        """
        Sincroniza saldos reais da exchange com a gestão de capital.
        Implementa auto-correção do banco de dados se uma divergência for detectada.
        """
        try:
            self.logger.info(f"🔄 Sincronizando saldos com a exchange...")

            # Extrair moedas base e de cotação do par
            base_currency, quote_currency = self.config['par'].split('/')

            # 1. Buscar saldo REAL da API
            saldo_base_real = self.exchange_api.get_saldo_disponivel(base_currency)
            saldo_quote_real = self.exchange_api.get_saldo_disponivel(quote_currency)

            # 2. Carregar posição do banco de dados LOCAL
            quantidade_local = self.position_manager.get_quantidade_total()

            self.logger.info(f"📊 Saldo LOCAL (banco de dados): {quantidade_local:.1f} {base_currency}")
            self.logger.info(f"📊 Saldo EXCHANGE (API real): {saldo_base_real:.1f} {base_currency} | ${saldo_quote_real:.2f} {quote_currency}")

            # 3. Comparar os dois valores
            diferenca_absoluta = abs(Decimal(str(saldo_base_real)) - quantidade_local)
            
            # Calcular tolerância: 1% do saldo da API (mínimo 0.1)
            tolerancia = max(Decimal(str(saldo_base_real)) * Decimal('0.01'), Decimal('0.1'))
            
            self.logger.info(f"📏 Diferença detectada: {diferenca_absoluta:.2f} {base_currency} (tolerância: {tolerancia:.2f})")

            # 4. Se divergência for maior que a tolerância, considerar desincronização
            if diferenca_absoluta > tolerancia:
                self.logger.warning("⚠️" + "="*60)
                self.logger.warning("⚠️ DIVERGÊNCIA DETECTADA!")
                self.logger.warning(f"⚠️ Saldo da API ({saldo_base_real:.1f}) difere do banco local ({quantidade_local:.1f})")
                self.logger.warning(f"⚠️ Diferença de {diferenca_absoluta:.2f} {base_currency} excede a tolerância de {tolerancia:.2f}")
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
                    self.position_manager.carregar_posicao()
                    
                    # Verificar novamente após correção
                    quantidade_corrigida = self.position_manager.get_quantidade_total()
                    diferenca_pos_correcao = abs(Decimal(str(saldo_base_real)) - quantidade_corrigida)
                    
                    self.logger.info(f"✅ Auto-correção concluída!")
                    self.logger.info(f"   📊 Saldo LOCAL corrigido: {quantidade_corrigida:.1f} {base_currency}")
                    self.logger.info(f"   📊 Saldo EXCHANGE: {saldo_base_real:.1f} {base_currency}")
                    self.logger.info(f"   📏 Nova diferença: {diferenca_pos_correcao:.2f} {base_currency}")
                    
                    if diferenca_pos_correcao <= tolerancia:
                        self.logger.info("✅ Banco de dados sincronizado com sucesso com a exchange!")
                    else:
                        self.logger.warning(f"⚠️ Ainda há divergência de {diferenca_pos_correcao:.2f} {base_currency} após correção")
                        self.logger.warning("⚠️ Pode haver trades manuais ou operações não rastreadas")
                    
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
        if (self.ultima_atualizacao_sma is None or
            (agora - self.ultima_atualizacao_sma) >= timedelta(hours=1)):

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
        try:
            tipo = oportunidade['tipo']
            quantidade = oportunidade['quantidade']
            preco_atual = oportunidade['preco_atual']
            
            self.logger.info(f"🎯 Executando oportunidade de compra: {oportunidade['motivo']}")
            
            # Executar ordem na exchange
            ordem = self.exchange_api.place_ordem_compra_market(
                par=self.config['par'],
                quantidade=float(quantidade)
            )

            if ordem and ordem.get('status') == 'FILLED':
                quantidade_real = Decimal(str(ordem.get('executedQty', quantidade)))
                preco_real = Decimal(str(ordem.get('cummulativeQuoteQty', '0'))) / quantidade_real if quantidade_real > 0 else preco_atual

                self.logger.operacao_compra(
                    par=self.config['par'],
                    quantidade=float(quantidade_real),
                    preco=float(preco_real),
                    degrau=oportunidade.get('degrau', 'N/A'),
                    queda_pct=float(oportunidade.get('distancia_sma', 0))
                )

                # Atualizar position manager
                self.position_manager.atualizar_apos_compra(quantidade_real, preco_real)

                # Registrar na estratégia para ativar cooldowns
                self.strategy_dca.registrar_compra_executada(oportunidade, quantidade_real)

                # Salvar no banco de dados
                self._salvar_ordem_banco({
                    'tipo': 'COMPRA',
                    'par': self.config['par'],
                    'quantidade': quantidade_real,
                    'preco': preco_real,
                    'valor_total': quantidade_real * preco_real,
                    'taxa': ordem.get('fills', [{}])[0].get('commission', 0) if ordem.get('fills') else 0,
                    'meta': str(oportunidade.get('degrau', 'oportunidade')),
                    'order_id': ordem.get('orderId'),
                    'observacao': f"{tipo.upper()}: {oportunidade['motivo']}"
                })

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
            
            self.logger.info(f"💰 Executando oportunidade de venda: {oportunidade['motivo']}")
            
            # Executar ordem na exchange
            ordem = self.exchange_api.place_ordem_venda_market(
                par=self.config['par'],
                quantidade=float(quantidade)
            )

            if ordem and ordem.get('status') == 'FILLED':
                quantidade_real = Decimal(str(ordem.get('executedQty', quantidade)))
                valor_real = Decimal(str(ordem.get('cummulativeQuoteQty', '0')))
                preco_real = valor_real / quantidade_real if quantidade_real > 0 else preco_atual

                # Calcular lucro se possível
                preco_medio = self.position_manager.get_preco_medio()
                lucro_pct = 0
                lucro_usdt = 0
                
                if preco_medio:
                    lucro_pct = ((preco_real - preco_medio) / preco_medio) * Decimal('100')
                    lucro_usdt = (preco_real - preco_medio) * quantidade_real

                self.logger.operacao_venda(
                    par=self.config['par'],
                    quantidade=float(quantidade_real),
                    preco=float(preco_real),
                    meta=oportunidade.get('meta', oportunidade.get('zona_nome', 'N/A')),
                    lucro_pct=float(lucro_pct),
                    lucro_usd=float(lucro_usdt)
                )

                # Atualizar position manager
                self.position_manager.atualizar_apos_venda(quantidade_real)

                # Registrar na estratégia
                self.strategy_sell.registrar_venda_executada(oportunidade, quantidade_real)

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
                    'order_id': ordem.get('orderId'),
                    'observacao': f"{tipo.upper()}: {oportunidade['motivo']}"
                })

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

            if ordem and ordem.get('status') == 'FILLED':
                quantidade_real = Decimal(str(ordem.get('executedQty', quantidade)))
                valor_real = Decimal(str(ordem.get('cummulativeQuoteQty', '0')))
                preco_real = valor_real / quantidade_real if quantidade_real > 0 else preco_atual

                self.logger.operacao_compra(
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

                # Salvar no banco de dados
                self._salvar_ordem_banco({
                    'tipo': 'COMPRA',
                    'par': self.config['par'],
                    'quantidade': quantidade_real,
                    'preco': preco_real,
                    'valor_total': valor_real,
                    'taxa': ordem.get('fills', [{}])[0].get('commission', 0) if ordem.get('fills') else 0,
                    'meta': f"recompra_{oportunidade['zona_nome']}",
                    'order_id': ordem.get('orderId'),
                    'observacao': f"RECOMPRA: {oportunidade['motivo']}"
                })

                return True
            else:
                self.logger.error(f"❌ Erro ao executar recompra: {ordem}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Erro ao executar recompra: {e}")
            return False

    def _salvar_ordem_banco(self, ordem_dados: Dict[str, Any]):
        """
        Salva ordem no banco de dados
        
        Args:
            ordem_dados: Dados da ordem para salvar
        """
        try:
            # Adicionar dados de posição antes/depois
            ordem_dados.update({
                'preco_medio_antes': self.position_manager.get_preco_medio(),
                'preco_medio_depois': self.position_manager.get_preco_medio(),
                'saldo_ada_antes': self.position_manager.get_quantidade_total(),
                'saldo_ada_depois': self.position_manager.get_quantidade_total(),
                'saldo_usdt_antes': Decimal('0'),  # Placeholder
                'saldo_usdt_depois': Decimal('0'),  # Placeholder
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
            self.logger.banner("🤖 BOT DE TRADING INICIADO")
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

            # ═══════════════════════════════════════════════════════════════
            # LOOP PRINCIPAL SIMPLIFICADO
            # ═══════════════════════════════════════════════════════════════
            while self.rodando:
                try:
                    contador_ciclos += 1

                    # 1. Obter preço atual
                    preco_atual = Decimal(str(self.exchange_api.get_preco_atual(self.config['par'])))
                    
                    # Calcular distância da SMA
                    distancia_sma = self._calcular_distancia_sma(preco_atual)
                    
                    if contador_ciclos == 1:
                        self.logger.info(f"📊 Preço inicial ADA: ${preco_atual:.6f}")
                        if distancia_sma:
                            self.logger.info(f"📉 Distância da SMA: {distancia_sma:.2f}%")

                    # 2. Verificar oportunidade de compra (DCA)
                    if distancia_sma:
                        oportunidade_compra = self.strategy_dca.verificar_oportunidade(
                            preco_atual=preco_atual,
                            distancia_sma=distancia_sma
                        )

                        if oportunidade_compra:
                            if self._executar_oportunidade_compra(oportunidade_compra):
                                self.logger.info("✅ Compra executada com sucesso!")
                                time.sleep(10)  # Pausa após compra
                                continue

                    # 3. Verificar oportunidade de venda
                    oportunidade_venda = self.strategy_sell.verificar_oportunidade(preco_atual)

                    if oportunidade_venda:
                        if self._executar_oportunidade_venda(oportunidade_venda):
                            self.logger.info("✅ Venda executada com sucesso!")
                            time.sleep(10)  # Pausa após venda
                            continue

                    # 4. Verificar recompras de segurança
                    oportunidade_recompra = self.strategy_sell.verificar_recompra_de_seguranca(preco_atual)

                    if oportunidade_recompra:
                        if self._executar_oportunidade_recompra(oportunidade_recompra):
                            self.logger.info("✅ Recompra executada com sucesso!")
                            time.sleep(10)  # Pausa após recompra
                            continue

                    # 5. Tarefas periódicas
                    if self.intervalo_verificacao_aportes is not None:
                        self._verificar_aportes_brl()
                    self._fazer_backup_periodico()

                    # Log informativo a cada 20 ciclos
                    if contador_ciclos % 20 == 0:
                        posicao = self.position_manager.get_quantidade_total()
                        preco_medio = self.position_manager.get_preco_medio()
                        
                        if posicao > 0 and preco_medio:
                            lucro_atual = self.position_manager.calcular_lucro_atual(preco_atual)
                            self.logger.info(
                                f"📊 Status: {posicao:.1f} ADA | "
                                f"PM: ${preco_medio:.6f} | "
                                f"Lucro: {lucro_atual:+.2f}%" if lucro_atual else "📊 Sem posição ativa"
                            )

                    # Pausa entre ciclos
                    time.sleep(5)

                except KeyboardInterrupt:
                    self.logger.info("🛑 Interrupção solicitada pelo usuário")
                    break
                except Exception as e:
                    self.logger.error(f"❌ Erro fatal no loop principal: {e}")
                    import traceback
                    self.logger.error(f"Traceback:\n{traceback.format_exc()}")
                    break

        except Exception as e:
            self.logger.error(f"❌ Erro crítico no bot: {e}")
        finally:
            self.rodando = False
            self.logger.banner("🛑 BOT FINALIZADO")


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