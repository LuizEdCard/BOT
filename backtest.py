#!/usr/bin/env python3
"""
Assistente Interativo de Backtest
Script para executar simulações do bot de trading com dados históricos.
"""

import json
import tempfile
import os
from pathlib import Path
from decimal import Decimal
from typing import Dict, Any
import questionary
import argparse
import sys
import pandas as pd

from src.core.bot_worker import BotWorker
from src.exchange.simulated_api import SimulatedExchangeAPI
from src.persistencia.database import DatabaseManager
from src.persistencia.state_manager import StateManager

# Definir o diretório base do projeto
BASE_DIR = Path(__file__).parent.resolve()


def validar_numero(text: str) -> bool:
    """Valida se o texto é um número válido"""
    try:
        float(text)
        return True
    except ValueError:
        return False


def validar_float(text: str) -> bool:
    """Valida se o texto é um float válido"""
    try:
        float(text)
        return float(text) >= 0
    except ValueError:
        return False


def carregar_configuracao(caminho_config: str) -> Dict[str, Any]:
    """Carrega o arquivo de configuração JSON do bot"""
    try:
        with open(caminho_config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"✅ Configuração carregada: {caminho_config}")
        return config
    except Exception as e:
        print(f"❌ Erro ao carregar configuração: {e}")
        raise


def listar_arquivos_json(diretorio: str = "configs") -> list:
    """Lista todos os arquivos JSON disponíveis no diretório"""
    caminho_dir = BASE_DIR / diretorio
    if not caminho_dir.exists():
        return []
    
    arquivos = []
    for arquivo in caminho_dir.glob("*.json"):
        # Usar caminho relativo ao diretório base
        caminho_relativo = arquivo.relative_to(BASE_DIR)
        arquivos.append(
            questionary.Choice(
                title=f"{arquivo.name} ({caminho_relativo})",
                value=str(arquivo)
            )
        )
    return sorted(arquivos, key=lambda x: x.title)


def listar_arquivos_csv(diretorio: str = "dados/historicos") -> list:
    """Lista todos os arquivos CSV disponíveis no diretório"""
    caminho_dir = BASE_DIR / diretorio
    if not caminho_dir.exists():
        return []
    
    arquivos = []
    for arquivo in caminho_dir.glob("*.csv"):
        # Pegar informações do arquivo
        tamanho = arquivo.stat().st_size
        tamanho_mb = tamanho / (1024 * 1024)
        
        # Usar caminho relativo ao diretório base
        caminho_relativo = arquivo.relative_to(BASE_DIR)
        
        arquivos.append(
            questionary.Choice(
                title=f"{arquivo.name} ({tamanho_mb:.1f} MB)",
                value=str(arquivo)
            )
        )
    return sorted(arquivos, key=lambda x: x.title)


def listar_estrategias_disponiveis() -> list:
    """Retorna lista das estratégias disponíveis"""
    return [
        questionary.Choice(title="Ambas as Estratégias (DCA + Giro Rápido)", value="ambas"),
        questionary.Choice(title="DCA (Acumulação)", value="dca"),
        questionary.Choice(title="Giro Rápido (Swing Trade)", value="giro_rapido"),
    ]


def listar_timeframes_disponiveis() -> list:
    """Retorna lista dos timeframes disponíveis"""
    return [
        questionary.Choice(title="1 minuto", value="1m"),
        questionary.Choice(title="5 minutos", value="5m"),
        questionary.Choice(title="15 minutos", value="15m"),
        questionary.Choice(title="30 minutos", value="30m"),
        questionary.Choice(title="1 hora", value="1h"),
        questionary.Choice(title="4 horas", value="4h"),
        questionary.Choice(title="1 dia", value="1d"),
    ]


def perguntar_override_timeframes(config_bot: Dict[str, Any], estrategias_selecionadas: list) -> Dict[str, Any]:
    """
    Pergunta ao usuário se deseja sobrescrever os timeframes da estratégia.
    
    Args:
        config_bot: Configuração carregada do arquivo JSON
        estrategias_selecionadas: Lista de estratégias que o usuário escolheu testar
        
    Returns:
        Dicionário com os timeframes escolhidos (overrides)
    """
    print("\n" + "="*80)
    print("⚙️  CONFIGURAÇÃO DE TIMEFRAMES")
    print("="*80)
    
    timeframes_choices = listar_timeframes_disponiveis()
    
    # Dicionário para armazenar os timeframes escolhidos
    overrides = {}
    
    # Verificar se DCA foi selecionada (ou 'ambas')
    dca_ativa = 'dca' in estrategias_selecionadas or 'ambas' in estrategias_selecionadas
    
    # Se DCA está ativa
    if dca_ativa:
        print("\n📊 Estratégia DCA (Acumulação) ativa")
        
        # Timeframe da SMA de referência
        periodo_dias_sma = config_bot.get('PERIODO_DIAS_SMA_REFERENCIA', 28)
        intervalo_horas_sma = config_bot.get('INTERVALO_ATUALIZACAO_SMA_HORAS', 1)
        timeframe_sma_atual = f"{intervalo_horas_sma}h" if intervalo_horas_sma < 24 else f"{intervalo_horas_sma // 24}d"
        
        # Encontrar o índice do timeframe atual para usar como padrão
        default_idx_sma = next((i for i, choice in enumerate(timeframes_choices) if choice.value == timeframe_sma_atual), 4)
        
        timeframe_sma = questionary.select(
            f"   Qual timeframe usar para a SMA do DCA? (atual: {timeframe_sma_atual}, período: {periodo_dias_sma} dias)",
            choices=timeframes_choices,
            default=timeframes_choices[default_idx_sma]
        ).ask()
        
        if timeframe_sma:
            overrides['dca_sma_timeframe'] = timeframe_sma
        
        # Timeframe do RSI (se habilitado)
        if config_bot.get('usar_filtro_rsi', False):
            timeframe_rsi_atual = config_bot.get('rsi_timeframe', '1h')
            default_idx_rsi = next((i for i, choice in enumerate(timeframes_choices) if choice.value == timeframe_rsi_atual), 4)
            
            timeframe_rsi = questionary.select(
                f"   Qual timeframe usar para o RSI do DCA? (atual: {timeframe_rsi_atual})",
                choices=timeframes_choices,
                default=timeframes_choices[default_idx_rsi]
            ).ask()
            
            if timeframe_rsi:
                overrides['dca_rsi_timeframe'] = timeframe_rsi
    
    # Verificar se Giro Rápido foi selecionado (ou 'ambas')
    giro_ativo = 'giro_rapido' in estrategias_selecionadas or 'ambas' in estrategias_selecionadas
    
    # Se Giro Rápido está ativo
    if giro_ativo:
        print("\n💨 Estratégia Giro Rápido (Swing Trade) ativa")
        
        estrategia_giro = config_bot.get('estrategia_giro_rapido', {})
        timeframe_giro_atual = estrategia_giro.get('timeframe', '15m')
        default_idx_giro = next((i for i, choice in enumerate(timeframes_choices) if choice.value == timeframe_giro_atual), 2)
        
        timeframe_giro = questionary.select(
            f"   Qual timeframe usar para o Giro Rápido? (atual: {timeframe_giro_atual})",
            choices=timeframes_choices,
            default=timeframes_choices[default_idx_giro]
        ).ask()
        
        if timeframe_giro:
            overrides['giro_timeframe'] = timeframe_giro
        
        # Timeframe do RSI de entrada (se habilitado)
        if estrategia_giro.get('usar_filtro_rsi_entrada', False):
            timeframe_rsi_giro_atual = estrategia_giro.get('rsi_timeframe_entrada', '15m')
            default_idx_rsi_giro = next((i for i, choice in enumerate(timeframes_choices) if choice.value == timeframe_rsi_giro_atual), 2)
            
            timeframe_rsi_giro = questionary.select(
                f"   Qual timeframe usar para o RSI do Giro Rápido? (atual: {timeframe_rsi_giro_atual})",
                choices=timeframes_choices,
                default=timeframes_choices[default_idx_rsi_giro]
            ).ask()
            
            if timeframe_rsi_giro:
                overrides['giro_rsi_timeframe'] = timeframe_rsi_giro
    
    return overrides


def aplicar_overrides_timeframes(config_bot: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplica os overrides de timeframe na configuração do bot.
    
    Args:
        config_bot: Configuração original
        overrides: Dicionário com os timeframes escolhidos
        
    Returns:
        Configuração atualizada
    """
    if 'dca_sma_timeframe' in overrides:
        timeframe = overrides['dca_sma_timeframe']
        # Converter timeframe para horas
        if timeframe.endswith('m'):
            horas = int(timeframe[:-1]) / 60
        elif timeframe.endswith('h'):
            horas = int(timeframe[:-1])
        elif timeframe.endswith('d'):
            horas = int(timeframe[:-1]) * 24
        else:
            horas = 1
        
        config_bot['INTERVALO_ATUALIZACAO_SMA_HORAS'] = int(horas) if horas >= 1 else 1
    
    if 'dca_rsi_timeframe' in overrides:
        config_bot['rsi_timeframe'] = overrides['dca_rsi_timeframe']
    
    if 'giro_timeframe' in overrides:
        if 'estrategia_giro_rapido' not in config_bot:
            config_bot['estrategia_giro_rapido'] = {}
        config_bot['estrategia_giro_rapido']['timeframe'] = overrides['giro_timeframe']
    
    if 'giro_rsi_timeframe' in overrides:
        if 'estrategia_giro_rapido' not in config_bot:
            config_bot['estrategia_giro_rapido'] = {}
        config_bot['estrategia_giro_rapido']['rsi_timeframe_entrada'] = overrides['giro_rsi_timeframe']
    
    return config_bot


def perguntar_parametros_dca(config_bot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pergunta ao usuário sobre os parâmetros da estratégia DCA.
    
    Args:
        config_bot: Configuração carregada do arquivo JSON
        
    Returns:
        Dicionário com os parâmetros modificados
    """
    print("\n" + "="*80)
    print("📊 CONFIGURAÇÃO DE PARÂMETROS - DCA (ACUMULAÇÃO)")
    print("="*80)
    
    params = {}
    
    # 1. Filtro RSI
    usar_rsi_atual = config_bot.get('usar_filtro_rsi', False)
    usar_rsi = questionary.confirm(
        f"Ativar filtro RSI do DCA? (atual: {'Sim' if usar_rsi_atual else 'Não'})",
        default=usar_rsi_atual
    ).ask()
    
    if usar_rsi is not None:
        params['usar_filtro_rsi'] = usar_rsi
        
        if usar_rsi:
            # Limite do RSI
            rsi_limite_atual = config_bot.get('rsi_limite_compra', 35)
            rsi_limite_str = questionary.text(
                f"Qual o limite do RSI para compra? (atual: {rsi_limite_atual})",
                default=str(rsi_limite_atual),
                validate=lambda t: validar_numero(t) or "Digite um número válido"
            ).ask()

            if rsi_limite_str is None:
                print("❌ Configuração cancelada pelo usuário.")
                return {}
            if rsi_limite_str:
                params['rsi_limite_compra'] = float(rsi_limite_str)
            
            # Timeframe do RSI
            timeframes_choices = listar_timeframes_disponiveis()
            rsi_tf_atual = config_bot.get('rsi_timeframe', '1h')
            default_idx = next((i for i, c in enumerate(timeframes_choices) if c.value == rsi_tf_atual), 4)
            
            rsi_tf = questionary.select(
                f"Qual o timeframe do RSI? (atual: {rsi_tf_atual})",
                choices=timeframes_choices,
                default=timeframes_choices[default_idx]
            ).ask()

            if rsi_tf is None:
                print("❌ Configuração cancelada pelo usuário.")
                return {}
            if rsi_tf:
                params['rsi_timeframe'] = rsi_tf
    
    # 2. Timeframe da SMA
    intervalo_sma_atual = config_bot.get('INTERVALO_ATUALIZACAO_SMA_HORAS', 4)
    tf_sma_atual = f"{intervalo_sma_atual}h" if intervalo_sma_atual < 24 else f"{intervalo_sma_atual // 24}d"
    
    timeframes_choices = listar_timeframes_disponiveis()
    default_idx_sma = next((i for i, c in enumerate(timeframes_choices) if c.value == tf_sma_atual), 5)
    
    tf_sma = questionary.select(
        f"Qual o timeframe da SMA de referência? (atual: {tf_sma_atual})",
        choices=timeframes_choices,
        default=timeframes_choices[default_idx_sma]
    ).ask()

    if tf_sma is None:
        print("❌ Configuração cancelada pelo usuário.")
        return {}
    if tf_sma:
        # Converter para horas
        if tf_sma.endswith('m'):
            horas = int(tf_sma[:-1]) / 60
        elif tf_sma.endswith('h'):
            horas = int(tf_sma[:-1])
        elif tf_sma.endswith('d'):
            horas = int(tf_sma[:-1]) * 24
        else:
            horas = 1
        params['INTERVALO_ATUALIZACAO_SMA_HORAS'] = int(horas) if horas >= 1 else 1
    
    # 3. Percentual Mínimo de Melhora do PM
    pm_melhora_atual = config_bot.get('PERCENTUAL_MINIMO_MELHORA_PM', 1.25)
    pm_melhora_str = questionary.text(
        f"Qual o % mínimo de melhora do Preço Médio para comprar? (atual: {pm_melhora_atual}%)",
        default=str(pm_melhora_atual),
        validate=lambda t: validar_float(t) or "Digite um número válido >= 0"
    ).ask()

    if pm_melhora_str is None:
        print("❌ Configuração cancelada pelo usuário.")
        return {}
    if pm_melhora_str:
        params['PERCENTUAL_MINIMO_MELHORA_PM'] = float(pm_melhora_str)
    
    # 4. Gestão de Saída (Stops)
    gestao_saida = config_bot.get('gestao_saida_acumulacao', {})
    
    tsl_dist_atual = gestao_saida.get('trailing_stop_distancia_pct', 2.0)
    tsl_dist_str = questionary.text(
        f"Qual a distância do Trailing Stop Loss (%)? (atual: {tsl_dist_atual}%)",
        default=str(tsl_dist_atual),
        validate=lambda t: validar_float(t) or "Digite um número válido >= 0"
    ).ask()

    if tsl_dist_str is None:
        print("❌ Configuração cancelada pelo usuário.")
        return {}
    if tsl_dist_str:
        if 'gestao_saida_acumulacao' not in params:
            params['gestao_saida_acumulacao'] = gestao_saida.copy()
        params['gestao_saida_acumulacao']['trailing_stop_distancia_pct'] = float(tsl_dist_str)
    
    sl_catastrofico_atual = gestao_saida.get('stop_loss_catastrofico_pct', 10.0)
    sl_catastrofico_str = questionary.text(
        f"Qual o Stop Loss catastrófico (%)? (atual: {sl_catastrofico_atual}%)",
        default=str(sl_catastrofico_atual),
        validate=lambda t: validar_float(t) or "Digite um número válido >= 0"
    ).ask()

    if sl_catastrofico_str is None:
        print("❌ Configuração cancelada pelo usuário.")
        return {}
    if sl_catastrofico_str:
        if 'gestao_saida_acumulacao' not in params:
            params['gestao_saida_acumulacao'] = gestao_saida.copy()
        params['gestao_saida_acumulacao']['stop_loss_catastrofico_pct'] = float(sl_catastrofico_str)
    
    return params


def perguntar_parametros_giro_rapido(config_bot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pergunta ao usuário sobre os parâmetros da estratégia Giro Rápido.
    
    Args:
        config_bot: Configuração carregada do arquivo JSON
        
    Returns:
        Dicionário com os parâmetros modificados
    """
    print("\n" + "="*80)
    print("💨 CONFIGURAÇÃO DE PARÂMETROS - GIRO RÁPIDO (SWING TRADE)")
    print("="*80)
    
    params = {}
    estrategia_giro = config_bot.get('estrategia_giro_rapido', {})
    
    # 1. Timeframe Principal
    tf_atual = estrategia_giro.get('timeframe', '15m')
    timeframes_choices = listar_timeframes_disponiveis()
    default_idx = next((i for i, c in enumerate(timeframes_choices) if c.value == tf_atual), 2)
    
    tf_giro = questionary.select(
        f"Qual o timeframe principal do Giro Rápido? (atual: {tf_atual})",
        choices=timeframes_choices,
        default=timeframes_choices[default_idx]
    ).ask()

    if tf_giro is None:
        print("❌ Configuração cancelada pelo usuário.")
        return {}
    if tf_giro:
        params['timeframe'] = tf_giro
    
    # 2. Gatilho de Compra
    gatilho_atual = estrategia_giro.get('gatilho_compra_pct', 2.0)
    gatilho_str = questionary.text(
        f"Qual o gatilho de compra (% de queda)? (atual: {gatilho_atual}%)",
        default=str(gatilho_atual),
        validate=lambda t: validar_float(t) or "Digite um número válido >= 0"
    ).ask()

    if gatilho_str is None:
        print("❌ Configuração cancelada pelo usuário.")
        return {}
    if gatilho_str:
        params['gatilho_compra_pct'] = float(gatilho_str)
    
    # 3. Filtro RSI de Entrada
    usar_rsi_atual = estrategia_giro.get('usar_filtro_rsi_entrada', True)
    usar_rsi = questionary.confirm(
        f"Ativar filtro RSI de entrada? (atual: {'Sim' if usar_rsi_atual else 'Não'})",
        default=usar_rsi_atual
    ).ask()
    
    if usar_rsi is not None:
        params['usar_filtro_rsi_entrada'] = usar_rsi
        
        if usar_rsi:
            # Limite do RSI
            rsi_limite_atual = estrategia_giro.get('rsi_limite_compra', 30)
            rsi_limite_str = questionary.text(
                f"Qual o limite do RSI de entrada? (atual: {rsi_limite_atual})",
                default=str(rsi_limite_atual),
                validate=lambda t: validar_numero(t) or "Digite um número válido"
            ).ask()

            if rsi_limite_str is None:
                print("❌ Configuração cancelada pelo usuário.")
                return {}
            if rsi_limite_str:
                params['rsi_limite_compra'] = float(rsi_limite_str)
            
            # Timeframe do RSI
            rsi_tf_atual = estrategia_giro.get('rsi_timeframe_entrada', '15m')
            default_idx_rsi = next((i for i, c in enumerate(timeframes_choices) if c.value == rsi_tf_atual), 2)
            
            rsi_tf = questionary.select(
                f"Qual o timeframe do RSI de entrada? (atual: {rsi_tf_atual})",
                choices=timeframes_choices,
                default=timeframes_choices[default_idx_rsi]
            ).ask()

            if rsi_tf is None:
                print("❌ Configuração cancelada pelo usuário.")
                return {}
            if rsi_tf:
                params['rsi_timeframe_entrada'] = rsi_tf
    
    # 4. Stop Loss Inicial
    sl_inicial_atual = estrategia_giro.get('stop_loss_inicial_pct', 2.5)
    sl_inicial_str = questionary.text(
        f"Qual o Stop Loss inicial (%)? (atual: {sl_inicial_atual}%)",
        default=str(sl_inicial_atual),
        validate=lambda t: validar_float(t) or "Digite um número válido >= 0"
    ).ask()

    if sl_inicial_str is None:
        print("❌ Configuração cancelada pelo usuário.")
        return {}
    if sl_inicial_str:
        params['stop_loss_inicial_pct'] = float(sl_inicial_str)
    
    # 5. Distância do Trailing Stop
    tsl_dist_atual = estrategia_giro.get('trailing_stop_distancia_pct', 0.8)
    tsl_dist_str = questionary.text(
        f"Qual a distância do Trailing Stop (%)? (atual: {tsl_dist_atual}%)",
        default=str(tsl_dist_atual),
        validate=lambda t: validar_float(t) or "Digite um número válido >= 0"
    ).ask()

    if tsl_dist_str is None:
        print("❌ Configuração cancelada pelo usuário.")
        return {}
    if tsl_dist_str:
        params['trailing_stop_distancia_pct'] = float(tsl_dist_str)
    
    # 6. Alocação de Capital
    alocacao_atual = estrategia_giro.get('alocacao_capital_pct', 20)
    alocacao_str = questionary.text(
        f"Qual o % de capital para Giro Rápido? (atual: {alocacao_atual}%)",
        default=str(alocacao_atual),
        validate=lambda t: validar_float(t) or "Digite um número válido >= 0"
    ).ask()

    if alocacao_str is None:
        print("❌ Configuração cancelada pelo usuário.")
        return {}
    if alocacao_str:
        params['alocacao_capital_pct'] = float(alocacao_str)
    
    return params


def aplicar_parametros_estrategias(config_bot: Dict[str, Any], params_dca: Dict[str, Any], params_giro: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplica os parâmetros personalizados nas estratégias.
    
    Args:
        config_bot: Configuração original
        params_dca: Parâmetros personalizados do DCA
        params_giro: Parâmetros personalizados do Giro Rápido
        
    Returns:
        Configuração atualizada
    """
    # Aplicar parâmetros do DCA
    for key, value in params_dca.items():
        config_bot[key] = value
    
    # Aplicar parâmetros do Giro Rápido
    if params_giro:
        if 'estrategia_giro_rapido' not in config_bot:
            config_bot['estrategia_giro_rapido'] = {}
        
        for key, value in params_giro.items():
            config_bot['estrategia_giro_rapido'][key] = value
    
    return config_bot


def imprimir_resumo_parametros(config_bot: Dict[str, Any], estrategias_selecionadas: list):
    """
    Imprime um resumo dos parâmetros finais que serão usados.
    
    Args:
        config_bot: Configuração final
        estrategias_selecionadas: Estratégias que foram selecionadas
    """
    print("\n   📊 Parâmetros Finais das Estratégias:")
    
    # DCA
    dca_ativa = 'dca' in estrategias_selecionadas or 'ambas' in estrategias_selecionadas
    if dca_ativa:
        print("\n      📊 DCA (Acumulação):")
        print(f"         Filtro RSI: {'Ativo' if config_bot.get('usar_filtro_rsi', False) else 'Inativo'}")
        if config_bot.get('usar_filtro_rsi', False):
            print(f"         RSI Limite: {config_bot.get('rsi_limite_compra', 35)}")
            print(f"         RSI Timeframe: {config_bot.get('rsi_timeframe', '1h')}")
        
        intervalo_sma = config_bot.get('INTERVALO_ATUALIZACAO_SMA_HORAS', 4)
        tf_sma = f"{intervalo_sma}h" if intervalo_sma < 24 else f"{intervalo_sma // 24}d"
        print(f"         SMA Timeframe: {tf_sma}")
        print(f"         Melhora PM Mínima: {config_bot.get('PERCENTUAL_MINIMO_MELHORA_PM', 1.25)}%")
        
        gestao = config_bot.get('gestao_saida_acumulacao', {})
        print(f"         Trailing Stop: {gestao.get('trailing_stop_distancia_pct', 2.0)}%")
        print(f"         Stop Loss Catastrófico: {gestao.get('stop_loss_catastrofico_pct', 10.0)}%")
    
    # Giro Rápido
    giro_ativo = 'giro_rapido' in estrategias_selecionadas or 'ambas' in estrategias_selecionadas
    if giro_ativo:
        print("\n      💨 Giro Rápido (Swing Trade):")
        estrategia_giro = config_bot.get('estrategia_giro_rapido', {})
        print(f"         Timeframe Principal: {estrategia_giro.get('timeframe', '15m')}")
        print(f"         Gatilho de Compra: {estrategia_giro.get('gatilho_compra_pct', 2.0)}%")
        print(f"         Filtro RSI: {'Ativo' if estrategia_giro.get('usar_filtro_rsi_entrada', True) else 'Inativo'}")
        if estrategia_giro.get('usar_filtro_rsi_entrada', True):
            print(f"         RSI Limite: {estrategia_giro.get('rsi_limite_compra', 30)}")
            print(f"         RSI Timeframe: {estrategia_giro.get('rsi_timeframe_entrada', '15m')}")
        print(f"         Stop Loss Inicial: {estrategia_giro.get('stop_loss_inicial_pct', 2.5)}%")
        print(f"         Trailing Stop: {estrategia_giro.get('trailing_stop_distancia_pct', 0.8)}%")
        print(f"         Alocação de Capital: {estrategia_giro.get('alocacao_capital_pct', 20)}%")


def calcular_benchmark_buy_hold(dados_csv: str, saldo_inicial: float, taxa_pct: float) -> Dict[str, float]:
    """
    Calcula o benchmark Buy & Hold (comprar no início e segurar até o final)
    
    Args:
        dados_csv: Caminho para o arquivo CSV com dados históricos
        saldo_inicial: Saldo inicial em USDT
        taxa_pct: Taxa percentual da exchange (ex: 0.1 para 0.1%)
        
    Returns:
        Dicionário com os resultados do Buy & Hold
    """
    df = pd.read_csv(dados_csv)
    
    # Compra no início (primeira vela)
    preco_inicial = Decimal(str(df.iloc[0]['close']))
    taxa = Decimal(str(taxa_pct)) / Decimal('100')
    
    # Calcular quantidade comprada (descontando taxa)
    custo_total = Decimal(str(saldo_inicial))
    taxa_compra = custo_total * taxa
    custo_liquido = custo_total - taxa_compra
    quantidade_ativo = custo_liquido / preco_inicial
    
    # Venda no final (última vela)
    preco_final = Decimal(str(df.iloc[-1]['close']))
    receita_bruta = quantidade_ativo * preco_final
    taxa_venda = receita_bruta * taxa
    receita_liquida = receita_bruta - taxa_venda
    
    # Calcular lucro
    lucro_total = receita_liquida - custo_total
    lucro_percentual = (lucro_total / custo_total) * Decimal('100')
    
    return {
        'saldo_final': float(receita_liquida),
        'lucro_total': float(lucro_total),
        'lucro_percentual': float(lucro_percentual),
        'preco_inicial': float(preco_inicial),
        'preco_final': float(preco_final),
        'quantidade_ativo': float(quantidade_ativo),
        'taxa_compra': float(taxa_compra),
        'taxa_venda': float(taxa_venda)
    }


def analisar_saidas_por_motivo(trades: list) -> Dict[str, int]:
    """
    Analisa os trades de venda e conta quantos foram por cada motivo
    
    Args:
        trades: Lista de trades executados
        
    Returns:
        Dicionário com contagem por motivo de saída
    """
    saidas = {
        'Stop Loss (SL)': 0,
        'Trailing Stop Loss (TSL)': 0,
        'Meta de Lucro': 0,
        'Outros': 0
    }
    
    for trade in trades:
        if trade.get('tipo') == 'venda':
            motivo = trade.get('motivo', '').lower()
            
            if 'stop loss' in motivo and 'trailing' not in motivo:
                saidas['Stop Loss (SL)'] += 1
            elif 'trailing' in motivo or 'tsl' in motivo:
                saidas['Trailing Stop Loss (TSL)'] += 1
            elif 'meta' in motivo or 'lucro' in motivo or 'venda' in motivo:
                saidas['Meta de Lucro'] += 1
            else:
                saidas['Outros'] += 1
    
    return saidas


def imprimir_relatorio_final(resultados: Dict[str, Any], benchmark: Dict[str, float], 
                              saldo_inicial: float, dados_csv: str):
    """
    Imprime o relatório final detalhado do backtest
    
    Args:
        resultados: Resultados da simulação
        benchmark: Resultados do Buy & Hold
        saldo_inicial: Saldo inicial usado
        dados_csv: Caminho do arquivo de dados
    """
    print("\n" + "="*80)
    print("📊 RELATÓRIO FINAL DO BACKTEST")
    print("="*80)
    
    # Informações gerais
    df = pd.read_csv(dados_csv)
    data_inicial = df.iloc[0]['timestamp']
    data_final = df.iloc[-1]['timestamp']
    total_velas = len(df)
    
    print(f"\n📅 Período Simulado:")
    print(f"   Início: {data_inicial}")
    print(f"   Fim: {data_final}")
    print(f"   Total de velas: {total_velas}")
    
    # Resultados da estratégia
    trades = resultados['trades']
    compras = [t for t in trades if t['tipo'] == 'compra']
    vendas = [t for t in trades if t['tipo'] == 'venda']
    
    saldo_final_usdt = resultados['saldo_final_usdt']
    saldo_final_ativo = resultados['saldo_final_ativo']
    
    # Valor final da posição (se ainda houver ativo)
    preco_final = benchmark['preco_final']
    valor_final_total = saldo_final_usdt + (saldo_final_ativo * preco_final)
    
    lucro_total = valor_final_total - saldo_inicial
    lucro_percentual = (lucro_total / saldo_inicial) * 100
    
    print(f"\n💰 Resultados da Estratégia:")
    print(f"   Saldo inicial: ${saldo_inicial:.2f} USDT")
    print(f"   Saldo final USDT: ${saldo_final_usdt:.2f}")
    print(f"   Saldo final Ativo: {saldo_final_ativo:.4f}")
    print(f"   Valor final total: ${valor_final_total:.2f}")
    print(f"   Lucro/Prejuízo: ${lucro_total:.2f} ({lucro_percentual:+.2f}%)")
    
    print(f"\n📈 Operações Executadas:")
    print(f"   Total de compras: {len(compras)}")
    print(f"   Total de vendas: {len(vendas)}")
    print(f"   Total de trades: {len(trades)}")
    
    if compras:
        volume_comprado = sum(c['quantidade_usdt'] for c in compras)
        print(f"   Volume comprado: ${volume_comprado:.2f} USDT")
    
    if vendas:
        volume_vendido = sum(v['receita_usdt'] for v in vendas)
        print(f"   Volume vendido: ${volume_vendido:.2f} USDT")
    
    # Análise de saídas
    if vendas:
        print(f"\n🎯 Análise de Saídas:")
        saidas = analisar_saidas_por_motivo(trades)
        for motivo, count in saidas.items():
            if count > 0:
                percentual = (count / len(vendas)) * 100
                print(f"   {motivo}: {count} ({percentual:.1f}%)")
    
    # Benchmark Buy & Hold
    print(f"\n📊 Benchmark Buy & Hold:")
    print(f"   Preço inicial: ${benchmark['preco_inicial']:.6f}")
    print(f"   Preço final: ${benchmark['preco_final']:.6f}")
    print(f"   Quantidade comprada: {benchmark['quantidade_ativo']:.4f}")
    print(f"   Saldo final: ${benchmark['saldo_final']:.2f}")
    print(f"   Lucro/Prejuízo: ${benchmark['lucro_total']:.2f} ({benchmark['lucro_percentual']:+.2f}%)")
    
    # Comparação
    print(f"\n🔍 Comparação Estratégia vs Buy & Hold:")
    diferenca_absoluta = lucro_total - benchmark['lucro_total']
    diferenca_percentual = lucro_percentual - benchmark['lucro_percentual']
    
    if diferenca_absoluta > 0:
        print(f"   ✅ Estratégia superou Buy & Hold em ${diferenca_absoluta:.2f} ({diferenca_percentual:+.2f}pp)")
    elif diferenca_absoluta < 0:
        print(f"   ⚠️ Estratégia ficou abaixo de Buy & Hold em ${abs(diferenca_absoluta):.2f} ({diferenca_percentual:.2f}pp)")
    else:
        print(f"   ➖ Estratégia empatou com Buy & Hold")
    
    print("\n" + "="*80)


def main():
    """Função principal do assistente de backtest"""
    print("="*80)
    print("🔬 LABORATÓRIO DE OTIMIZAÇÃO DE BACKTEST")
    print("="*80)
    # --- Argumentos de linha de comando (modo não-interativo) ---
    parser = argparse.ArgumentParser(description='Backtest runner (interactive or non-interactive)')
    parser.add_argument('--non-interactive', action='store_true', help='Executa o backtest sem prompts interativos')
    parser.add_argument('--config', type=str, help='Caminho para arquivo de configuração JSON')
    parser.add_argument('--csv', type=str, help='Caminho para arquivo CSV de histórico')
    parser.add_argument('--timeframe', type=str, help='Timeframe base do CSV (ex: 1m, 5m, 15m, 1h)')
    parser.add_argument('--saldo', type=float, help='Saldo inicial em USDT (ex: 1000)')
    parser.add_argument('--taxa', type=float, help='Taxa da exchange em porcentagem (ex: 0.1)')
    parser.add_argument('--estrategias', type=str, help='Estratégias a executar (ex: dca,giro_rapido ou ambas)')
    args = parser.parse_args()

    # Pré-preencher variáveis quando rodando em modo não-interativo
    pref_config = args.config if args.config else None
    pref_csv = args.csv if args.csv else None
    pref_timeframe = args.timeframe if args.timeframe else None
    pref_saldo = args.saldo if args.saldo is not None else None
    pref_taxa = args.taxa if args.taxa is not None else None
    pref_estrategias = None
    if args.estrategias:
        # aceitar 'ambas' diretamente ou lista separada por vírgula
        raw = args.estrategias
        if raw.strip().lower() == 'ambas':
            pref_estrategias = ['ambas']
        else:
            pref_estrategias = [s.strip() for s in raw.split(',') if s.strip()]
    
    # 1. Arquivo de configuração (interactive ou pré-preenchido)
    if pref_config:
        arquivo_config = pref_config
        print(f"✅ Usando configuração fornecida via CLI: {arquivo_config}")
        try:
            config = carregar_configuracao(arquivo_config)
        except Exception:
            print(f"❌ Não foi possível carregar a configuração fornecida: {arquivo_config}")
            return
    else:
        arquivos_json = listar_arquivos_json("configs")
        if not arquivos_json:
            print("❌ Nenhum arquivo de configuração encontrado em 'configs/'.")
            return
        arquivo_config = questionary.select(
            "📁 Selecione o arquivo de configuração do bot:",
            choices=arquivos_json
        ).ask()
        if not arquivo_config:
            print("❌ Configuração não selecionada. Encerrando.")
            return
        # Carregar configuração
        config = carregar_configuracao(arquivo_config)
    
    # 2. Arquivo CSV (interactive ou pré-preenchido)
    if pref_csv:
        arquivo_csv = pref_csv
        print(f"✅ Usando CSV fornecido via CLI: {arquivo_csv}")
    else:
        arquivos_csv = listar_arquivos_csv("dados/historicos")
        if not arquivos_csv:
            print("❌ Nenhum arquivo CSV encontrado em 'dados/historicos'.")
            return
        arquivo_csv = questionary.select(
            "📁 Selecione o arquivo de dados históricos (CSV):",
            choices=arquivos_csv
        ).ask()
        if not arquivo_csv:
            print("❌ Arquivo CSV não selecionado. Encerrando.")
            return
    
    # 3. Timeframe base (interactive ou pré-preenchido)
    if pref_timeframe:
        timeframe_base = pref_timeframe
        print(f"✅ Usando timeframe fornecido via CLI: {timeframe_base}")
    else:
        timeframes_choices = listar_timeframes_disponiveis()
        timeframe_base = questionary.select(
            "⏱️  Qual é o timeframe do arquivo CSV?",
            choices=timeframes_choices,
            default=timeframes_choices[0]  # 1m como padrão
        ).ask()
        if not timeframe_base:
            print("❌ Timeframe base não selecionado. Encerrando.")
            return
    
    # 4. Saldo inicial (interactive ou pré-preenchido)
    if pref_saldo is not None:
        saldo_inicial = float(pref_saldo)
        print(f"✅ Usando saldo inicial via CLI: {saldo_inicial}")
    else:
        saldo_inicial_str = questionary.text(
            "💵 Digite o saldo inicial em USDT:",
            default="1000",
            validate=lambda text: validar_numero(text) or "Por favor, digite um número válido"
        ).ask()
        if not saldo_inicial_str:
            print("❌ Saldo inicial não fornecido. Encerrando.")
            return
        saldo_inicial = float(saldo_inicial_str)
    
    # 5. Taxa (interactive ou pré-preenchido)
    if pref_taxa is not None:
        taxa = float(pref_taxa)
        print(f"✅ Usando taxa via CLI: {taxa}%")
    else:
        taxa_str = questionary.text(
            "📊 Digite a taxa da exchange (em %):",
            default="0.1",
            validate=lambda text: validar_float(text) or "Por favor, digite um número válido >= 0"
        ).ask()
        if not taxa_str:
            print("❌ Taxa não fornecida. Encerrando.")
            return
        taxa = float(taxa_str)
    
    # 6. Perguntar quais estratégias testar
    # 6. Estratégias (interactive ou pré-preenchido)
    if pref_estrategias is not None:
        # suportar 'ambas' ou lista
        estrategias_selecionadas = pref_estrategias
        print(f"✅ Usando estratégias via CLI: {estrategias_selecionadas}")
    else:
        estrategias_choices = listar_estrategias_disponiveis()
        estrategias_selecionadas = questionary.checkbox(
            "🎯 Selecione as estratégias para testar (use ESPAÇO para selecionar, ENTER para confirmar):",
            choices=estrategias_choices
        ).ask()
        if estrategias_selecionadas is None:
            print("❌ Seleção cancelada pelo usuário.")
            return
        if not estrategias_selecionadas or estrategias_selecionadas == []:
            print("❌ Nenhuma estratégia selecionada. Use ESPAÇO para marcar as opções antes de pressionar ENTER.")
            return
    
    # 7. Perguntar sobre parâmetros das estratégias
    print("\n🔬 LABORATÓRIO DE OTIMIZAÇÃO DE PARÂMETROS")
    print("Você pode agora personalizar todos os parâmetros chave das estratégias...\n")
    
    params_dca = {}
    params_giro = {}

    # Verificar quais estratégias foram selecionadas
    dca_selecionada = 'dca' in estrategias_selecionadas or 'ambas' in estrategias_selecionadas
    giro_selecionado = 'giro_rapido' in estrategias_selecionadas or 'ambas' in estrategias_selecionadas

    # Se estivermos em modo não-interativo, não chamar os questionarios de parâmetros
    if dca_selecionada:
        if args.non_interactive:
            # Usar valores já presentes em config (ou defaults)
            params_dca = {}
            print("ℹ️ Modo não-interativo: pulando perguntas de parâmetros do DCA; usando valores do arquivo de configuração.")
        else:
            params_dca = perguntar_parametros_dca(config)

    # Perguntar parâmetros do Giro Rápido (ou pular em non-interactive)
    if giro_selecionado:
        if args.non_interactive:
            params_giro = {}
            print("ℹ️ Modo não-interativo: pulando perguntas de parâmetros do Giro Rápido; usando valores do arquivo de configuração.")
        else:
            params_giro = perguntar_parametros_giro_rapido(config)
    
    # Aplicar todos os parâmetros personalizados
    config = aplicar_parametros_estrategias(config, params_dca, params_giro)
    
    # 8. Confirmação com resumo completo
    print("\n" + "="*80)
    print("📋 RESUMO FINAL DA CONFIGURAÇÃO")
    print("="*80)
    print(f"   Arquivo de configuração: {arquivo_config}")
    print(f"   Arquivo de dados: {arquivo_csv}")
    print(f"   Timeframe base do CSV: {timeframe_base}")
    print(f"   Saldo inicial: ${saldo_inicial:.2f} USDT")
    print(f"   Taxa da exchange: {taxa}%")
    print(f"   Estratégias selecionadas: {', '.join(estrategias_selecionadas)}")
    
    # Mostrar parâmetros finais de cada estratégia
    imprimir_resumo_parametros(config, estrategias_selecionadas)
    
    print("\n" + "="*80)

    # Em modo não-interativo, pular confirmação
    if args.non_interactive:
        print("ℹ️  Modo não-interativo: executando backtest automaticamente...")
        confirmar = True
    else:
        confirmar = questionary.confirm(
            "Deseja executar o backtest com estas configurações?",
            default=True
        ).ask()

        if confirmar is None:
            print("❌ Backtest cancelado pelo usuário.")
            return

    if not confirmar:
        print("❌ Backtest cancelado pelo usuário.")
        return
    
    # 9. Executar simulação
    print("\n🚀 Iniciando simulação...\n")
    
    try:
        # Calcular benchmark Buy & Hold
        print("📊 Calculando benchmark Buy & Hold...")
        benchmark = calcular_benchmark_buy_hold(arquivo_csv, saldo_inicial, taxa)
        print("✅ Benchmark calculado\n")
        
        # Sobrescrever configurações para simulação (usar banco em memória temporário)
        # SQLite :memory: não funciona bem com Path objects, então usamos arquivo temporário
        temp_db_file = tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False)
        temp_db_file.close()  # Fechar para que o SQLite possa abrir
        config['DATABASE_PATH'] = temp_db_file.name
        config['BACKUP_DIR'] = tempfile.gettempdir() + '/backtest_backup'  # Diretório temporário para backups

        # Criar arquivo temporário para o state
        temp_state_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump({}, temp_state_file)  # Escrever JSON vazio válido
        temp_state_file.close()
        config['STATE_FILE_PATH'] = temp_state_file.name
        
        # ============================================================================
        # CORREÇÃO BUG 1: SOBRESCREVER CONFIG DE ESTRATÉGIA
        # ============================================================================
        # Determinar quais estratégias estão ativas
        dca_ativa = 'dca' in estrategias_selecionadas or 'ambas' in estrategias_selecionadas
        giro_ativo = 'giro_rapido' in estrategias_selecionadas or 'ambas' in estrategias_selecionadas

        # Definir o modo de operação principal do BotWorker
        if dca_ativa and giro_ativo:
            config['ESTRATEGIA_ATIVA'] = 'ambas'
        elif dca_ativa:
            config['ESTRATEGIA_ATIVA'] = 'dca'
        elif giro_ativo:
            config['ESTRATEGIA_ATIVA'] = 'giro'
        else:
            config['ESTRATEGIA_ATIVA'] = 'nenhuma' # Fallback de segurança

        # Garantir que a estrutura ESTRATEGIAS exista para os flags 'habilitado'
        if 'ESTRATEGIAS' not in config:
            config['ESTRATEGIAS'] = {}
        if 'dca' not in config['ESTRATEGIAS']:
            config['ESTRATEGIAS']['dca'] = {}
        if 'giro_rapido' not in config['ESTRATEGIAS']:
            config['ESTRATEGIAS']['giro_rapido'] = {}

        # Forçar a sobrescrita dos flags 'habilitado' individuais para consistência
        config['ESTRATEGIAS']['dca']['habilitado'] = dca_ativa
        config['ESTRATEGIAS']['giro_rapido']['habilitado'] = giro_ativo

        # Log de confirmação para o usuário
        print(f"🔧 Modo de operação do bot ('ESTRATEGIA_ATIVA') definido para: '{config['ESTRATEGIA_ATIVA']}'")
        # ============================================================================
        
        # Instanciar API simulada com timeframe base (CORREÇÃO BUG 2)
        print("🔧 Configurando API simulada...")
        exchange_api = SimulatedExchangeAPI(
            caminho_csv=arquivo_csv,
            saldo_inicial=saldo_inicial,
            taxa_pct=taxa,
            timeframe_base=timeframe_base
        )
        
        # Instanciar BotWorker em modo simulação
        print("🤖 Inicializando BotWorker...")
        bot_worker = BotWorker(
            config=config,
            exchange_api=exchange_api,
            telegram_notifier=None,
            notifier=None,
            modo_simulacao=True
        )
        
        # Executar simulação
        print("▶️ Executando simulação...\n")
        bot_worker.run()
        
        # Obter resultados
        resultados = exchange_api.get_resultados()
        
        # Imprimir relatório final
        imprimir_relatorio_final(resultados, benchmark, saldo_inicial, arquivo_csv)

        # Limpar arquivos temporários
        try:
            Path(temp_state_file.name).unlink()
            Path(temp_db_file.name).unlink()
        except:
            pass

        print("\n✅ Backtest concluído com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro durante a simulação: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação cancelada pelo usuário (Ctrl+C).")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
