#!/usr/bin/env python3
"""
Strategy Sell - Estratégia de Vendas com High-Water Mark
"""

from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.core.position_manager import PositionManager
from src.persistencia.state_manager import StateManager
from src.utils.logger import get_loggers

logger, _ = get_loggers()


class StrategySell:
    """
    Estratégia de vendas com sistema de High-Water Mark e zonas de segurança.
    
    Implementa:
    1. Metas fixas de venda (6%, 11%, 18%)
    2. Sistema High-Water Mark para tracking do pico de lucro
    3. Vendas de segurança baseadas em reversões desde o pico
    """
    
    def __init__(
        self, 
        config: Dict[str, Any], 
        position_manager: PositionManager,
        state_manager: StateManager
    ):
        """
        Inicializa a estratégia de vendas
        
        Args:
            config: Configurações da estratégia
            position_manager: Gerenciador de posições
            state_manager: Gerenciador de estado
        """
        self.config = config
        self.position_manager = position_manager
        self.state = state_manager
        
        # Configurações extraídas
        self.metas_venda = config.get('METAS_VENDA', [])
        self.vendas_seguranca = config.get('VENDAS_DE_SEGURANCA', [])
        self.valor_minimo_ordem = Decimal(str(config.get('VALOR_MINIMO_ORDEM', 5.0)))
        
        # Estado do High-Water Mark
        self.high_water_mark_profit: Decimal = Decimal('0')
        self.zonas_de_seguranca_acionadas: set = set()
        self.capital_para_recompra: Dict[str, Dict] = {}
        
        # Carregar estado persistente
        self._carregar_estado_hwm()
        
        logger.debug(f"💰 Estratégia de vendas inicializada:")
        logger.debug(f"   Metas fixas: {len(self.metas_venda)}")
        logger.debug(f"   Vendas de segurança: {len(self.vendas_seguranca)}")
        logger.debug(f"   High-Water Mark atual: {self.high_water_mark_profit:.2f}%")
    
    def verificar_oportunidade(self, preco_atual: Decimal) -> Optional[Dict[str, Any]]:
        """
        Verifica se existe oportunidade de venda
        
        Args:
            preco_atual: Preço atual do ativo
            
        Returns:
            Dict com detalhes da oportunidade ou None se não houver
        """
        try:
            # Verificar se há posição para vender
            if not self.position_manager.tem_posicao():
                logger.debug("📊 Sem posição para vender")
                return None
            
            # Calcular lucro atual
            lucro_atual = self.position_manager.calcular_lucro_atual(preco_atual)
            if lucro_atual is None or lucro_atual <= 0:
                logger.debug(f"📊 Sem lucro para vender (atual: {lucro_atual:.2f}%)" if lucro_atual else "📊 Sem lucro calculável")
                return None
            
            # Atualizar High-Water Mark
            self._atualizar_high_water_mark(lucro_atual)
            
            # PRIORIDADE 1: Verificar metas fixas (em ordem decrescente)
            oportunidade_meta_fixa = self._verificar_metas_fixas(lucro_atual, preco_atual)
            if oportunidade_meta_fixa:
                return oportunidade_meta_fixa
            
            # PRIORIDADE 2: Verificar vendas de segurança
            oportunidade_seguranca = self._verificar_vendas_seguranca(lucro_atual, preco_atual)
            if oportunidade_seguranca:
                return oportunidade_seguranca
            
            # Nenhuma oportunidade encontrada
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar oportunidade de venda: {e}")
            return None
    
    def _verificar_metas_fixas(self, lucro_atual: Decimal, preco_atual: Decimal) -> Optional[Dict[str, Any]]:
        """
        Verifica se alguma meta fixa foi atingida
        
        Args:
            lucro_atual: Lucro percentual atual
            preco_atual: Preço atual do ativo
            
        Returns:
            Dict com oportunidade de meta fixa ou None
        """
        # Ordenar metas por lucro percentual (maior para menor)
        metas_ordenadas = sorted(
            self.metas_venda,
            key=lambda x: x['lucro_percentual'],
            reverse=True
        )
        
        # Verificar se alguma meta fixa foi atingida
        for meta in metas_ordenadas:
            meta_lucro_pct = Decimal(str(meta['lucro_percentual']))
            
            if lucro_atual >= meta_lucro_pct:
                logger.info(f"🎯 Meta fixa {meta['meta']} atingida ({meta_lucro_pct}%)")
                
                # Calcular quantidade a vender
                quantidade_total = self.position_manager.get_quantidade_total()
                percentual_venda = Decimal(str(meta['percentual_venda'])) / Decimal('100')
                quantidade_venda = quantidade_total * percentual_venda
                
                # Arredondar para 0.1 (step size ADA)
                quantidade_venda = self._arredondar_quantidade(quantidade_venda)
                valor_ordem = quantidade_venda * preco_atual
                
                # Validar valor mínimo
                if not self._validar_ordem_minima(valor_ordem, quantidade_venda):
                    logger.warning(f"⚠️ Meta {meta['meta']} atingida mas ordem abaixo do mínimo: ${valor_ordem:.2f}")
                    continue
                
                return {
                    'tipo': 'meta_fixa',
                    'meta': meta['meta'],
                    'meta_numero': meta['meta'],
                    'lucro_percentual_meta': meta_lucro_pct,
                    'lucro_percentual_atual': lucro_atual,
                    'percentual_venda': meta['percentual_venda'],
                    'quantidade_venda': quantidade_venda,
                    'preco_atual': preco_atual,
                    'valor_ordem': valor_ordem,
                    'motivo': f"Meta {meta['meta']} ({meta_lucro_pct}%)",
                    'reset_hwm': True,  # Metas fixas resetam o High-Water Mark
                    'meta_config': meta
                }
        
        return None
    
    def _verificar_vendas_seguranca(self, lucro_atual: Decimal, preco_atual: Decimal) -> Optional[Dict[str, Any]]:
        """
        Verifica vendas de segurança baseadas no High-Water Mark
        
        Args:
            lucro_atual: Lucro percentual atual
            preco_atual: Preço atual do ativo
            
        Returns:
            Dict com oportunidade de venda de segurança ou None
        """
        if not self.vendas_seguranca:
            return None
        
        quantidade_total = self.position_manager.get_quantidade_total()
        
        for zona in self.vendas_seguranca:
            nome_zona = zona['nome']
            
            # Verificar se zona já foi acionada
            if nome_zona in self.zonas_de_seguranca_acionadas:
                continue
            
            # GATILHO 1: Ativação - High-water mark deve ultrapassar este valor
            gatilho_ativacao_pct = Decimal(str(zona['gatilho_ativacao_lucro_pct']))
            
            # Verificar se high-water mark "armou" o gatilho da zona
            if self.high_water_mark_profit < gatilho_ativacao_pct:
                continue
            
            # GATILHO 2: Reversão - Quanto deve cair desde o pico para vender
            gatilho_reversao_pct = Decimal(str(zona['gatilho_venda_reversao_pct']))
            
            # Calcular gatilho de venda baseado na reversão configurada
            gatilho_venda = self.high_water_mark_profit - gatilho_reversao_pct
            
            # Verificar se lucro atual caiu abaixo do gatilho de venda
            if lucro_atual <= gatilho_venda:
                logger.info(f"🛡️ ZONA DE SEGURANÇA '{nome_zona}' ATIVADA!")
                logger.info(f"   📊 High-Water Mark: {self.high_water_mark_profit:.2f}%")
                logger.info(f"   🎯 Gatilho ativação: {gatilho_ativacao_pct:.2f}% (armada ✓)")
                logger.info(f"   📉 Lucro atual: {lucro_atual:.2f}%")
                logger.info(f"   🎯 Gatilho venda: {gatilho_venda:.2f}%")
                
                # Calcular quantidade a vender
                percentual_venda = Decimal(str(zona['percentual_venda_posicao'])) / Decimal('100')
                quantidade_venda = quantidade_total * percentual_venda
                
                # Arredondar para 0.1 (step size ADA)
                quantidade_venda = self._arredondar_quantidade(quantidade_venda)
                valor_ordem = quantidade_venda * preco_atual
                
                # Validar valor mínimo
                if not self._validar_ordem_minima(valor_ordem, quantidade_venda):
                    logger.warning(f"⚠️ Zona {nome_zona} ativada mas ordem abaixo do mínimo: ${valor_ordem:.2f}")
                    # Marcar como acionada mesmo assim para não tentar novamente
                    self.zonas_de_seguranca_acionadas.add(nome_zona)
                    self._salvar_estado_hwm()
                    continue
                
                return {
                    'tipo': 'venda_seguranca',
                    'zona_nome': nome_zona,
                    'high_water_mark': self.high_water_mark_profit,
                    'gatilho_ativacao': gatilho_ativacao_pct,
                    'gatilho_venda': gatilho_venda,
                    'lucro_atual': lucro_atual,
                    'percentual_venda': zona['percentual_venda_posicao'],
                    'quantidade_venda': quantidade_venda,
                    'preco_atual': preco_atual,
                    'valor_ordem': valor_ordem,
                    'gatilho_recompra_drop': Decimal(str(zona['gatilho_recompra_drop_pct'])),
                    'motivo': f"Venda Segurança {nome_zona}",
                    'reset_hwm': False,  # Vendas de segurança NÃO resetam HWM
                    'zona_config': zona
                }
        
        return None
    
    def _atualizar_high_water_mark(self, lucro_atual: Decimal):
        """
        Atualiza o High-Water Mark se lucro atual for maior
        
        Args:
            lucro_atual: Lucro percentual atual
        """
        if lucro_atual > self.high_water_mark_profit:
            anterior = self.high_water_mark_profit
            self.high_water_mark_profit = lucro_atual
            self._salvar_estado_hwm()
            
            logger.debug(f"📊 High-Water Mark atualizado: {anterior:.2f}% → {lucro_atual:.2f}%")
    
    def _arredondar_quantidade(self, quantidade: Decimal) -> Decimal:
        """
        Arredonda quantidade para step size da ADA (0.1)
        
        Args:
            quantidade: Quantidade original
            
        Returns:
            Decimal: Quantidade arredondada
        """
        return (quantidade * Decimal('10')).quantize(
            Decimal('1'), rounding='ROUND_DOWN'
        ) / Decimal('10')
    
    def _validar_ordem_minima(self, valor_ordem: Decimal, quantidade: Decimal) -> bool:
        """
        Valida se ordem atende aos requisitos mínimos
        
        Args:
            valor_ordem: Valor da ordem em USDT
            quantidade: Quantidade em ADA
            
        Returns:
            bool: True se ordem é válida
        """
        return valor_ordem >= self.valor_minimo_ordem and quantidade >= Decimal('1')
    
    def registrar_venda_executada(
        self, 
        oportunidade: Dict[str, Any], 
        quantidade_real: Optional[Decimal] = None
    ):
        """
        Registra que uma venda foi executada
        
        Args:
            oportunidade: Dados da oportunidade executada
            quantidade_real: Quantidade realmente vendida (opcional)
        """
        try:
            tipo_venda = oportunidade['tipo']
            
            # Se foi meta fixa, resetar High-Water Mark e zonas
            if tipo_venda == 'meta_fixa' and oportunidade.get('reset_hwm', True):
                logger.info("🔄 Resetando High-Water Mark após venda de meta fixa")
                self.high_water_mark_profit = Decimal('0')
                self.zonas_de_seguranca_acionadas.clear()
                self.capital_para_recompra.clear()
                self._salvar_estado_hwm()
            
            # Se foi venda de segurança, guardar capital para recompra
            elif tipo_venda == 'venda_seguranca':
                nome_zona = oportunidade['zona_nome']
                valor_ordem = oportunidade['valor_ordem']
                
                # Guardar capital obtido e high-water mark atual
                self.capital_para_recompra[nome_zona] = {
                    'capital_usdt': valor_ordem,  # Capital em USDT obtido da venda
                    'high_water_mark': self.high_water_mark_profit,  # Pico de lucro registrado
                    'gatilho_recompra_pct': oportunidade['gatilho_recompra_drop'],
                    'quantidade_vendida': quantidade_real or oportunidade['quantidade_venda'],
                    'preco_venda': oportunidade['preco_atual'],
                    'timestamp_venda': datetime.now().isoformat()
                }
                
                # Marcar zona como acionada
                self.zonas_de_seguranca_acionadas.add(nome_zona)
                self._salvar_estado_hwm()
                
                logger.info(f"💰 Capital reservado para recompra: ${valor_ordem:.2f} USDT")
                logger.info(f"   📌 Zona '{nome_zona}' marcada como acionada")
                logger.info(f"   🔄 Recompra será ativada se lucro cair {oportunidade['gatilho_recompra_drop']}% desde o pico")
            
        except Exception as e:
            logger.error(f"❌ Erro ao registrar venda executada: {e}")
    
    def verificar_recompra_de_seguranca(self, preco_atual: Decimal) -> Optional[Dict[str, Any]]:
        """
        Verifica se deve executar recompra após venda de segurança
        
        Args:
            preco_atual: Preço atual do ativo
            
        Returns:
            Dict com oportunidade de recompra ou None
        """
        if not self.capital_para_recompra:
            return None  # Nenhuma recompra pendente
        
        # Calcular lucro atual (se houver posição)
        lucro_atual = self.position_manager.calcular_lucro_atual(preco_atual)
        
        if lucro_atual is None:
            # Sem posição - não faz sentido recomprar sem preço médio
            return None
        
        for nome_zona, dados_zona in list(self.capital_para_recompra.items()):
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
                quantidade_ada = self._arredondar_quantidade(quantidade_ada)
                valor_ordem = quantidade_ada * preco_atual
                
                # Validar valor mínimo
                if self._validar_ordem_minima(valor_ordem, quantidade_ada):
                    return {
                        'tipo': 'recompra_seguranca',
                        'zona_nome': nome_zona,
                        'quantidade': quantidade_ada,
                        'preco_atual': preco_atual,
                        'valor_ordem': valor_ordem,
                        'high_water_mark': high_mark,
                        'gatilho_recompra': gatilho_recompra,
                        'lucro_atual': lucro_atual,
                        'dados_venda_original': dados_zona,
                        'motivo': f"Recompra Segurança {nome_zona}",
                        'marcar_zona_para_remocao': nome_zona
                    }
                else:
                    logger.warning(f"⚠️ Recompra ignorada - valor abaixo do mínimo: ${valor_ordem:.2f}")
                    # Remover da lista mesmo assim
                    del self.capital_para_recompra[nome_zona]
                    self._salvar_estado_hwm()
        
        return None
    
    def registrar_recompra_executada(self, oportunidade: Dict[str, Any]):
        """
        Registra que uma recompra foi executada
        
        Args:
            oportunidade: Dados da oportunidade de recompra executada
        """
        try:
            nome_zona = oportunidade.get('marcar_zona_para_remocao')
            if nome_zona and nome_zona in self.capital_para_recompra:
                del self.capital_para_recompra[nome_zona]
                logger.debug(f"✅ Capital de zona '{nome_zona}' removido após recompra")
                self._salvar_estado_hwm()
                
        except Exception as e:
            logger.error(f"❌ Erro ao registrar recompra executada: {e}")
    
    def _carregar_estado_hwm(self):
        """Carrega estado persistente do High-Water Mark"""
        try:
            # Carregar High-Water Mark
            hwm_str = self.state.get_state('high_water_mark_profit')
            if hwm_str:
                self.high_water_mark_profit = Decimal(str(hwm_str))
            
            # Carregar zonas acionadas
            zonas_str = self.state.get_state('zonas_seguranca_acionadas')
            if zonas_str and isinstance(zonas_str, list):
                self.zonas_de_seguranca_acionadas = set(zonas_str)
            
            # Carregar capital para recompra
            capital_str = self.state.get_state('capital_para_recompra')
            if capital_str and isinstance(capital_str, dict):
                # Converter strings de volta para Decimal nos campos numéricos
                for zona, dados in capital_str.items():
                    if isinstance(dados, dict):
                        for key in ['capital_usdt', 'high_water_mark', 'gatilho_recompra_pct', 
                                  'quantidade_vendida', 'preco_venda']:
                            if key in dados and dados[key] is not None:
                                dados[key] = Decimal(str(dados[key]))
                self.capital_para_recompra = capital_str
            
            logger.debug(f"📊 Estado HWM carregado: {self.high_water_mark_profit:.2f}%")
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao carregar estado HWM: {e}")
    
    def _salvar_estado_hwm(self):
        """Salva estado persistente do High-Water Mark"""
        try:
            # Salvar High-Water Mark
            self.state.set_state('high_water_mark_profit', float(self.high_water_mark_profit))
            
            # Salvar zonas acionadas
            self.state.set_state('zonas_seguranca_acionadas', list(self.zonas_de_seguranca_acionadas))
            
            # Salvar capital para recompra (converter Decimal para float para JSON)
            capital_serializable = {}
            for zona, dados in self.capital_para_recompra.items():
                capital_serializable[zona] = {
                    key: float(value) if isinstance(value, Decimal) else value
                    for key, value in dados.items()
                }
            self.state.set_state('capital_para_recompra', capital_serializable)
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar estado HWM: {e}")
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas da estratégia de vendas
        
        Returns:
            dict: Estatísticas da estratégia
        """
        try:
            return {
                'high_water_mark_profit': self.high_water_mark_profit,
                'total_metas_fixas': len(self.metas_venda),
                'total_vendas_seguranca': len(self.vendas_seguranca),
                'zonas_acionadas': list(self.zonas_de_seguranca_acionadas),
                'capital_reservado_recompra': {
                    zona: float(dados['capital_usdt'])
                    for zona, dados in self.capital_para_recompra.items()
                },
                'total_capital_recompra': sum(
                    float(dados['capital_usdt']) 
                    for dados in self.capital_para_recompra.values()
                )
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas de vendas: {e}")
            return {}
    
    def resetar_estado(self):
        """
        Reseta completamente o estado da estratégia (para testes ou reset manual)
        """
        logger.warning("🔄 Resetando estado da estratégia de vendas")
        self.high_water_mark_profit = Decimal('0')
        self.zonas_de_seguranca_acionadas.clear()
        self.capital_para_recompra.clear()
        self._salvar_estado_hwm()
        logger.info("✅ Estado resetado com sucesso")