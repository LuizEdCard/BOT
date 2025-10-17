#!/usr/bin/env python3
"""
Strategy DCA - Estratégia Dollar Cost Averaging
"""

from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from src.core.position_manager import PositionManager
from src.core.gestao_capital import GestaoCapital
from src.persistencia.state_manager import StateManager
from src.utils.logger import get_loggers

logger, _ = get_loggers()


class StrategyDCA:
    """
    Estratégia DCA (Dollar Cost Averaging) para compras em degraus
    baseada em queda percentual desde a SMA e melhora do preço médio.
    """
    
    def __init__(
        self, 
        config: Dict[str, Any], 
        position_manager: PositionManager,
        gestao_capital: GestaoCapital,
        state_manager: StateManager
    ):
        """
        Inicializa a estratégia DCA
        
        Args:
            config: Configurações da estratégia
            position_manager: Gerenciador de posições
            gestao_capital: Gerenciador de capital
            state_manager: Gerenciador de estado
        """
        self.config = config
        self.position_manager = position_manager
        self.gestao_capital = gestao_capital
        self.state = state_manager
        
        # Cache para evitar spam de logs
        self.ultima_tentativa_log_degrau: Dict[int, datetime] = {}
        self.degraus_notificados_bloqueados: set = set()
        self.notificou_exposicao_maxima: bool = False
        
        # Configurações extraídas
        self.degraus_compra = config.get('DEGRAUS_COMPRA', [])
        self.cooldown_global_minutos = config.get('COOLDOWN_GLOBAL_APOS_COMPRA_MINUTOS', 30)
        self.percentual_minimo_melhora_pm = config.get('PERCENTUAL_MINIMO_MELHORA_PM', 2.0)
        self.gestao_risco = config.get('GESTAO_DE_RISCO', {})
        
        logger.debug(f"🎯 Estratégia DCA inicializada com {len(self.degraus_compra)} degraus")
    
    def verificar_oportunidade(
        self, 
        preco_atual: Decimal, 
        distancia_sma: Decimal,
        saldo_usdt: Optional[Decimal] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Verifica se existe oportunidade de compra DCA
        
        Args:
            preco_atual: Preço atual do ativo
            distancia_sma: Distância percentual desde a SMA de referência
            saldo_usdt: Saldo USDT disponível (opcional)
            
        Returns:
            Dict com detalhes da oportunidade ou None se não houver
        """
        try:
            # Verificar guardião de exposição máxima
            if not self._verificar_guardiao_exposicao():
                return self._verificar_oportunidades_extremas(preco_atual)
            
            # Buscar degrau ativo baseado na distância da SMA
            degrau_ativo = self._encontrar_degrau_ativo(distancia_sma)
            if not degrau_ativo:
                logger.debug(f"📊 Nenhum degrau ativo para queda de {distancia_sma:.2f}%")
                return None
            
            # Verificar dupla-condição: SMA + melhora do preço médio
            if not self._verificar_dupla_condicao(degrau_ativo, preco_atual, distancia_sma):
                return None
            
            # Verificar cooldowns (global + por degrau)
            pode_comprar, motivo_bloqueio = self._verificar_cooldowns(degrau_ativo)
            if not pode_comprar:
                self._gerenciar_notificacao_bloqueio(degrau_ativo['nivel'], motivo_bloqueio)
                return None
            
            # Verificar se há capital suficiente
            quantidade_ada = Decimal(str(degrau_ativo['quantidade_ada']))
            valor_ordem = quantidade_ada * preco_atual
            
            pode_comprar_capital, motivo = self.gestao_capital.pode_comprar(valor_ordem)
            if not pode_comprar_capital:
                logger.debug(f"💰 Capital insuficiente para degrau {degrau_ativo['nivel']}: {motivo}")
                return None
            
            # Oportunidade encontrada!
            self._gerenciar_notificacao_desbloqueio(degrau_ativo['nivel'])
            
            oportunidade = {
                'tipo': 'dca',
                'degrau': degrau_ativo['nivel'],
                'quantidade': quantidade_ada,
                'preco_atual': preco_atual,
                'valor_ordem': valor_ordem,
                'queda_percentual': degrau_ativo['queda_percentual'],
                'distancia_sma': distancia_sma,
                'degrau_config': degrau_ativo,
                'motivo': f"Degrau {degrau_ativo['nivel']} - Queda {distancia_sma:.2f}%"
            }
            
            # Log anti-spam (só 1x a cada 5 minutos por degrau)
            self._log_oportunidade_encontrada(oportunidade)
            
            return oportunidade
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar oportunidade DCA: {e}")
            return None
    
    def _verificar_guardiao_exposicao(self) -> bool:
        """
        Verifica se o guardião de exposição máxima permite compras normais
        
        Returns:
            bool: True se pode fazer compras normais, False se exposição máxima atingida
        """
        try:
            # Obter configuração de exposição máxima
            limite_exposicao = Decimal(str(
                self.gestao_risco.get('exposicao_maxima_percentual_capital', 70.0)
            ))
            
            # Verificar alocação atual
            alocacao_atual = self.gestao_capital.get_alocacao_percentual_ada()
            
            if alocacao_atual > limite_exposicao:
                if not self.notificou_exposicao_maxima:
                    logger.warning("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    logger.warning(f"🛡️ GUARDIÃO ATIVADO: Exposição máxima de {limite_exposicao}% atingida.")
                    logger.warning(f"   Alocação atual em ADA: {alocacao_atual:.1f}%")
                    logger.warning("   Compras normais suspensas. Verificando camadas de oportunidade extrema...")
                    logger.warning("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    self.notificou_exposicao_maxima = True
                
                return False
            else:
                # Exposição normalizada - reativar compras
                if self.notificou_exposicao_maxima:
                    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    logger.info(f"✅ Exposição de capital normalizada ({alocacao_atual:.1f}%). Compras normais reativadas.")
                    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    self.notificou_exposicao_maxima = False
                    
                    # Resetar oportunidades extremas quando exposição normaliza
                    if self.state.get_state('oportunidades_extremas_usadas'):
                        self.state.set_state('oportunidades_extremas_usadas', [])
                        logger.info("🔓 Camadas de oportunidade extrema rearmadas.")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao verificar guardião de exposição: {e}")
            return True  # Em caso de erro, permitir compras normais
    
    def _verificar_oportunidades_extremas(self, preco_atual: Decimal) -> Optional[Dict[str, Any]]:
        """
        Verifica oportunidades de compra em camadas extremas quando exposição máxima atingida
        
        Args:
            preco_atual: Preço atual do ativo
            
        Returns:
            Dict com oportunidade extrema ou None
        """
        try:
            camadas_oportunidade = self.gestao_risco.get('compras_de_oportunidade_extrema', [])
            if not camadas_oportunidade:
                return None
            
            oportunidades_usadas = self.state.get_state('oportunidades_extremas_usadas', default=[])
            
            for camada in camadas_oportunidade:
                preco_alvo = Decimal(str(camada['preco_alvo']))
                
                # Verificar se preço atingiu o alvo e camada ainda não foi usada
                if preco_atual <= preco_alvo and str(preco_alvo) not in oportunidades_usadas:
                    logger.info(f"🚨 OPORTUNIDADE EXTREMA (Camada {preco_alvo}) DETECTADA!")
                    
                    percentual_a_usar = Decimal(str(camada['percentual_capital_usar']))
                    capital_disponivel = self.gestao_capital.calcular_capital_disponivel()
                    valor_compra_usdt = capital_disponivel * (percentual_a_usar / Decimal('100'))
                    quantidade_ada = valor_compra_usdt / preco_atual
                    
                    # Validar valor mínimo de ordem
                    valor_minimo = Decimal(str(self.config.get('VALOR_MINIMO_ORDEM', 5.0)))
                    if valor_compra_usdt >= valor_minimo and quantidade_ada >= Decimal('1'):
                        return {
                            'tipo': 'oportunidade_extrema',
                            'degrau': f"extrema_{preco_alvo}",
                            'quantidade': quantidade_ada,
                            'preco_atual': preco_atual,
                            'valor_ordem': valor_compra_usdt,
                            'preco_alvo': preco_alvo,
                            'percentual_capital': percentual_a_usar,
                            'motivo': f"Oportunidade Extrema {preco_alvo}",
                            'marcar_como_usada': str(preco_alvo)
                        }
                    else:
                        logger.warning(f"⚠️ Oportunidade extrema ignorada - valor abaixo do mínimo: ${valor_compra_usdt:.2f}")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar oportunidades extremas: {e}")
            return None
    
    def _encontrar_degrau_ativo(self, distancia_sma: Decimal) -> Optional[Dict[str, Any]]:
        """
        Encontra o primeiro degrau ativo baseado na distância da SMA
        
        Args:
            distancia_sma: Distância percentual desde a SMA
            
        Returns:
            Dicionário do degrau ativo ou None
        """
        for degrau in self.degraus_compra:
            queda_necessaria = Decimal(str(degrau['queda_percentual']))
            if distancia_sma >= queda_necessaria:
                return degrau
        return None
    
    def _verificar_dupla_condicao(
        self, 
        degrau: Dict[str, Any], 
        preco_atual: Decimal, 
        distancia_sma: Decimal
    ) -> bool:
        """
        Verifica a dupla-condição: SMA + melhora do preço médio
        
        Args:
            degrau: Configuração do degrau
            preco_atual: Preço atual
            distancia_sma: Distância da SMA
            
        Returns:
            bool: True se ambas condições atendidas
        """
        # CONDIÇÃO 1: Verificar se degrau está ativo (queda suficiente desde SMA)
        queda_necessaria = Decimal(str(degrau['queda_percentual']))
        condicao_sma_ok = distancia_sma >= queda_necessaria
        
        if not condicao_sma_ok:
            return False
        
        # CONDIÇÃO 2: Verificar se preço melhora o preço médio (DCA inteligente)
        preco_medio_atual = self.position_manager.get_preco_medio()
        
        if preco_medio_atual is None or preco_medio_atual <= 0:
            # Sem posição anterior - sempre pode comprar
            logger.debug(f"✅ Sem posição anterior - condição de melhora PM dispensada")
            return True
        
        # Verificar melhora mínima do preço médio
        percentual_melhora = Decimal(str(self.percentual_minimo_melhora_pm)) / Decimal('100')
        limite_preco_melhora = preco_medio_atual * (Decimal('1') - percentual_melhora)
        condicao_melhora_pm_ok = preco_atual <= limite_preco_melhora
        
        if not condicao_melhora_pm_ok:
            logger.debug(
                f"📊 Degrau {degrau['nivel']}: SMA OK ({distancia_sma:.2f}%), "
                f"mas preço ${preco_atual:.6f} não melhora PM (${preco_medio_atual:.6f}) "
                f"em {self.percentual_minimo_melhora_pm}%"
            )
            return False
        
        logger.debug(f"✅ Dupla-condição atendida para degrau {degrau['nivel']}")
        return True
    
    def _verificar_cooldowns(self, degrau: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Verifica cooldowns global e por degrau
        
        Args:
            degrau: Configuração do degrau
            
        Returns:
            Tuple (pode_comprar, motivo_bloqueio)
        """
        agora = datetime.now()
        nivel_degrau = degrau['nivel']
        
        # VERIFICAÇÃO 1: COOLDOWN GLOBAL (após qualquer compra)
        timestamp_global_str = self.state.get_state('ultima_compra_global_ts')
        if timestamp_global_str:
            timestamp_ultima_compra_global = datetime.fromisoformat(timestamp_global_str)
            tempo_desde_ultima_compra = agora - timestamp_ultima_compra_global
            minutos_decorridos = tempo_desde_ultima_compra.total_seconds() / 60
            
            if minutos_decorridos < self.cooldown_global_minutos:
                minutos_restantes = int(self.cooldown_global_minutos - minutos_decorridos)
                motivo = f"cooldown_global:{minutos_restantes}min"
                logger.debug(f"🕒 Cooldown global ativo (faltam {minutos_restantes} min)")
                return (False, motivo)
        
        # VERIFICAÇÃO 2: COOLDOWN POR DEGRAU (intervalo específico do degrau)
        chave_degrau = f'ultima_compra_degrau_{nivel_degrau}_ts'
        timestamp_degrau_str = self.state.get_state(chave_degrau)
        
        if timestamp_degrau_str:
            ultima_compra_degrau = datetime.fromisoformat(timestamp_degrau_str)
            tempo_desde_compra_degrau = agora - ultima_compra_degrau
            intervalo_horas = Decimal(str(degrau['intervalo_horas']))
            horas_decorridas = Decimal(str(tempo_desde_compra_degrau.total_seconds() / 3600))
            
            if horas_decorridas < intervalo_horas:
                horas_restantes = float(intervalo_horas - horas_decorridas)
                motivo = f"cooldown_degrau:{horas_restantes:.1f}h"
                logger.debug(f"🕒 Degrau {nivel_degrau} em cooldown (faltam {horas_restantes:.1f}h)")
                return (False, motivo)
        
        # Passou em todas as verificações
        return (True, None)
    
    def _gerenciar_notificacao_bloqueio(self, nivel_degrau: int, motivo: Optional[str]):
        """
        Gerencia notificações de degrau bloqueado para evitar spam
        
        Args:
            nivel_degrau: Nível do degrau
            motivo: Motivo do bloqueio
        """
        if nivel_degrau not in self.degraus_notificados_bloqueados:
            self.degraus_notificados_bloqueados.add(nivel_degrau)
            if motivo and motivo.startswith('cooldown_global'):
                logger.debug(f"🕒 Cooldown global ativo ({motivo})")
            elif motivo and motivo.startswith('cooldown_degrau'):
                logger.debug(f"🕒 Degrau {nivel_degrau} em cooldown ({motivo})")
    
    def _gerenciar_notificacao_desbloqueio(self, nivel_degrau: int):
        """
        Remove degrau do set de bloqueados e notifica desbloqueio
        
        Args:
            nivel_degrau: Nível do degrau
        """
        if nivel_degrau in self.degraus_notificados_bloqueados:
            self.degraus_notificados_bloqueados.remove(nivel_degrau)
            logger.info(f"🔓 Degrau {nivel_degrau} desbloqueado")
    
    def _log_oportunidade_encontrada(self, oportunidade: Dict[str, Any]):
        """
        Log anti-spam para oportunidades encontradas
        
        Args:
            oportunidade: Dados da oportunidade
        """
        nivel_degrau = oportunidade['degrau']
        if isinstance(nivel_degrau, str):  # Oportunidade extrema
            logger.info(f"🎯 {oportunidade['motivo']} encontrada!")
            return
        
        # Anti-spam: só loga "Degrau X ativado" 1x a cada 5 minutos
        agora = datetime.now()
        ultima_log = self.ultima_tentativa_log_degrau.get(nivel_degrau)
        
        if ultima_log is None or (agora - ultima_log) >= timedelta(minutes=5):
            logger.info(f"🎯 Degrau {nivel_degrau} ativado! Queda: {oportunidade['distancia_sma']:.2f}%")
            self.ultima_tentativa_log_degrau[nivel_degrau] = agora
    
    def registrar_compra_executada(
        self, 
        oportunidade: Dict[str, Any], 
        quantidade_real: Optional[Decimal] = None
    ):
        """
        Registra que uma compra foi executada para ativar cooldowns
        
        Args:
            oportunidade: Dados da oportunidade executada
            quantidade_real: Quantidade realmente comprada (opcional)
        """
        try:
            agora = datetime.now()
            timestamp_iso = agora.isoformat()
            
            # Registrar cooldown global
            self.state.set_state('ultima_compra_global_ts', timestamp_iso)
            logger.debug(f"🕒 Cooldown global ativado: {self.cooldown_global_minutos} minutos")
            
            # Se foi oportunidade extrema, marcar como usada
            if oportunidade['tipo'] == 'oportunidade_extrema':
                oportunidades_usadas = self.state.get_state('oportunidades_extremas_usadas', default=[])
                marca = oportunidade.get('marcar_como_usada')
                if marca and marca not in oportunidades_usadas:
                    oportunidades_usadas.append(marca)
                    self.state.set_state('oportunidades_extremas_usadas', oportunidades_usadas)
                    logger.debug(f"🔒 Oportunidade extrema {marca} marcada como usada")
            
            # Se foi compra DCA normal, registrar cooldown por degrau
            elif oportunidade['tipo'] == 'dca' and isinstance(oportunidade['degrau'], int):
                nivel_degrau = oportunidade['degrau']
                chave_degrau = f'ultima_compra_degrau_{nivel_degrau}_ts'
                self.state.set_state(chave_degrau, timestamp_iso)
                logger.debug(f"🕒 Cooldown degrau {nivel_degrau} ativado")
            
        except Exception as e:
            logger.error(f"❌ Erro ao registrar compra executada: {e}")
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas da estratégia
        
        Returns:
            dict: Estatísticas da estratégia
        """
        try:
            stats = {
                'total_degraus_configurados': len(self.degraus_compra),
                'cooldown_global_minutos': self.cooldown_global_minutos,
                'percentual_minimo_melhora_pm': self.percentual_minimo_melhora_pm,
                'exposicao_maxima': self.gestao_risco.get('exposicao_maxima_percentual_capital', 70.0),
                'notificou_exposicao_maxima': self.notificou_exposicao_maxima,
                'degraus_bloqueados': list(self.degraus_notificados_bloqueados)
            }
            
            # Adicionar informações de cooldowns ativos
            agora = datetime.now()
            
            # Cooldown global
            timestamp_global = self.state.get_state('ultima_compra_global_ts')
            if timestamp_global:
                ultima_compra = datetime.fromisoformat(timestamp_global)
                tempo_restante = self.cooldown_global_minutos - ((agora - ultima_compra).total_seconds() / 60)
                stats['cooldown_global_restante_min'] = max(0, int(tempo_restante))
            
            # Oportunidades extremas usadas
            stats['oportunidades_extremas_usadas'] = self.state.get_state('oportunidades_extremas_usadas', default=[])
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas da estratégia: {e}")
            return {}