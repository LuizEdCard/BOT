#!/usr/bin/env python3
"""
Feature Engineering - Preparação de dados OHLCV para Machine Learning

Este módulo contém funções para calcular indicadores técnicos e features
a partir de dados de candlestick (OHLCV) para uso em modelos de ML.
"""

import pandas as pd
import pandas_ta as ta
from typing import Optional


def calcular_features(dataframe: pd.DataFrame, periodo_volatilidade: int = 20, periodo_adx: int = 14) -> pd.DataFrame:
    """
    Calcula features técnicas a partir de dados OHLCV para Machine Learning.
    
    Features calculadas:
    - retornos: Retorno percentual entre fechamentos consecutivos
    - volatilidade: Desvio padrão dos retornos em janela móvel
    - adx: Average Directional Index (força da tendência)
    
    Args:
        dataframe: DataFrame com colunas ['open', 'high', 'low', 'close', 'volume']
        periodo_volatilidade: Janela móvel para cálculo de volatilidade (padrão: 20)
        periodo_adx: Período para cálculo do ADX (padrão: 14)
        
    Returns:
        DataFrame com features adicionadas (linhas com NaN são removidas)
        
    Raises:
        ValueError: Se colunas necessárias não estiverem presentes
        
    Example:
        >>> df = pd.DataFrame({
        ...     'open': [100, 101, 102],
        ...     'high': [103, 104, 105],
        ...     'low': [99, 100, 101],
        ...     'close': [102, 103, 104],
        ...     'volume': [1000, 1100, 1200]
        ... })
        >>> df_features = calcular_features(df)
    """
    # Validar colunas necessárias
    colunas_necessarias = ['open', 'high', 'low', 'close', 'volume']
    colunas_faltantes = [col for col in colunas_necessarias if col not in dataframe.columns]
    
    if colunas_faltantes:
        raise ValueError(f"Colunas faltantes no DataFrame: {colunas_faltantes}")
    
    # Criar cópia para não modificar o original
    df = dataframe.copy()
    
    # ═══════════════════════════════════════════════════════════════════
    # 1. RETORNOS: Percentual de mudança entre fechamentos consecutivos
    # ═══════════════════════════════════════════════════════════════════
    df['retornos'] = df['close'].pct_change() * 100  # Em percentual
    
    # ═══════════════════════════════════════════════════════════════════
    # 2. VOLATILIDADE: Desvio padrão dos retornos (janela móvel)
    # ═══════════════════════════════════════════════════════════════════
    df['volatilidade'] = df['retornos'].rolling(window=periodo_volatilidade).std()
    
    # ═══════════════════════════════════════════════════════════════════
    # 3. ADX: Average Directional Index (força da tendência)
    # ═══════════════════════════════════════════════════════════════════
    # pandas-ta retorna um DataFrame com ADX, DMP e DMN
    adx_df = ta.adx(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        length=periodo_adx
    )
    
    # Adicionar apenas a coluna ADX (ignora DMP e DMN por enquanto)
    if adx_df is not None and f'ADX_{periodo_adx}' in adx_df.columns:
        df['adx'] = adx_df[f'ADX_{periodo_adx}']
    else:
        # Fallback se pandas-ta não retornar ADX
        df['adx'] = None
    
    # ═══════════════════════════════════════════════════════════════════
    # 4. LIMPEZA: Remover linhas com NaN (início das séries temporais)
    # ═══════════════════════════════════════════════════════════════════
    df_limpo = df.dropna()
    
    # Log de quantas linhas foram removidas
    linhas_removidas = len(df) - len(df_limpo)
    if linhas_removidas > 0:
        print(f"ℹ️  {linhas_removidas} linhas com NaN removidas (warm-up dos indicadores)")
    
    return df_limpo


def calcular_features_avancadas(
    dataframe: pd.DataFrame,
    incluir_basicas: bool = True,
    periodo_rsi: int = 14,
    periodo_macd_rapido: int = 12,
    periodo_macd_lento: int = 26,
    periodo_macd_sinal: int = 9
) -> pd.DataFrame:
    """
    Calcula features técnicas avançadas para Machine Learning.
    
    Esta função estende calcular_features() com indicadores adicionais:
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - Bandas de Bollinger
    
    Args:
        dataframe: DataFrame com colunas OHLCV
        incluir_basicas: Se True, inclui features básicas (retornos, volatilidade, adx)
        periodo_rsi: Período para RSI (padrão: 14)
        periodo_macd_rapido: Período rápido do MACD (padrão: 12)
        periodo_macd_lento: Período lento do MACD (padrão: 26)
        periodo_macd_sinal: Período da linha de sinal do MACD (padrão: 9)
        
    Returns:
        DataFrame com features avançadas
        
    Example:
        >>> df_avancado = calcular_features_avancadas(df, incluir_basicas=True)
    """
    # Começar com features básicas se solicitado
    if incluir_basicas:
        df = calcular_features(dataframe)
    else:
        df = dataframe.copy()
    
    # ═══════════════════════════════════════════════════════════════════
    # RSI: Relative Strength Index
    # ═══════════════════════════════════════════════════════════════════
    df['rsi'] = ta.rsi(df['close'], length=periodo_rsi)
    
    # ═══════════════════════════════════════════════════════════════════
    # MACD: Moving Average Convergence Divergence
    # ═══════════════════════════════════════════════════════════════════
    macd_df = ta.macd(
        df['close'],
        fast=periodo_macd_rapido,
        slow=periodo_macd_lento,
        signal=periodo_macd_sinal
    )
    
    if macd_df is not None:
        df['macd'] = macd_df[f'MACD_{periodo_macd_rapido}_{periodo_macd_lento}_{periodo_macd_sinal}']
        df['macd_signal'] = macd_df[f'MACDs_{periodo_macd_rapido}_{periodo_macd_lento}_{periodo_macd_sinal}']
        df['macd_histogram'] = macd_df[f'MACDh_{periodo_macd_rapido}_{periodo_macd_lento}_{periodo_macd_sinal}']
    
    # ═══════════════════════════════════════════════════════════════════
    # Bandas de Bollinger
    # ═══════════════════════════════════════════════════════════════════
    bb_df = ta.bbands(df['close'], length=20, std=2)
    
    if bb_df is not None:
        df['bb_upper'] = bb_df['BBU_20_2.0']
        df['bb_middle'] = bb_df['BBM_20_2.0']
        df['bb_lower'] = bb_df['BBL_20_2.0']
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']  # Largura normalizada
    
    # Limpar NaNs
    df_limpo = df.dropna()
    
    linhas_removidas = len(df) - len(df_limpo)
    if linhas_removidas > 0:
        print(f"ℹ️  {linhas_removidas} linhas com NaN removidas (warm-up dos indicadores)")
    
    return df_limpo


def criar_target_label(
    dataframe: pd.DataFrame,
    periodos_futuros: int = 5,
    threshold_positivo: float = 1.0
) -> pd.DataFrame:
    """
    Cria label (target) para classificação binária baseada em retornos futuros.
    
    Label = 1 se o preço subir mais que threshold_positivo% nos próximos N períodos
    Label = 0 caso contrário
    
    Args:
        dataframe: DataFrame com coluna 'close'
        periodos_futuros: Quantos períodos olhar para frente (padrão: 5)
        threshold_positivo: Threshold em % para classificar como positivo (padrão: 1.0)
        
    Returns:
        DataFrame com coluna 'target' adicionada
        
    Example:
        >>> df_com_target = criar_target_label(df, periodos_futuros=5, threshold_positivo=1.5)
    """
    df = dataframe.copy()
    
    # Calcular retorno futuro máximo nos próximos N períodos
    df['preco_futuro_max'] = df['close'].rolling(window=periodos_futuros).max().shift(-periodos_futuros)
    df['retorno_futuro'] = ((df['preco_futuro_max'] - df['close']) / df['close']) * 100
    
    # Criar label binário
    df['target'] = (df['retorno_futuro'] >= threshold_positivo).astype(int)
    
    # Remover colunas auxiliares
    df.drop(['preco_futuro_max', 'retorno_futuro'], axis=1, inplace=True)
    
    # Remover últimas linhas onde não há dados futuros
    df = df[:-periodos_futuros]
    
    return df


if __name__ == '__main__':
    """Teste básico das funções"""
    import numpy as np
    
    print("=" * 60)
    print("TESTE: Feature Engineering para Machine Learning")
    print("=" * 60)
    
    # Criar dados sintéticos de teste
    np.random.seed(42)
    n_candles = 100
    
    df_teste = pd.DataFrame({
        'open': 100 + np.cumsum(np.random.randn(n_candles) * 0.5),
        'high': 101 + np.cumsum(np.random.randn(n_candles) * 0.5),
        'low': 99 + np.cumsum(np.random.randn(n_candles) * 0.5),
        'close': 100 + np.cumsum(np.random.randn(n_candles) * 0.5),
        'volume': np.random.randint(1000, 5000, n_candles)
    })
    
    # Ajustar high/low para serem coerentes
    df_teste['high'] = df_teste[['open', 'high', 'low', 'close']].max(axis=1)
    df_teste['low'] = df_teste[['open', 'high', 'low', 'close']].min(axis=1)
    
    print(f"\n✅ Dados de teste criados: {len(df_teste)} candles")
    print(f"   Preço inicial: ${df_teste['close'].iloc[0]:.2f}")
    print(f"   Preço final: ${df_teste['close'].iloc[-1]:.2f}")
    
    # Testar features básicas
    print("\n" + "-" * 60)
    print("1. Testando features básicas (retornos, volatilidade, ADX)")
    print("-" * 60)
    
    df_features = calcular_features(df_teste)
    
    print(f"✅ Features básicas calculadas")
    print(f"   Shape: {df_features.shape}")
    print(f"   Colunas: {list(df_features.columns)}")
    print(f"\nEstatísticas das features:")
    print(df_features[['retornos', 'volatilidade', 'adx']].describe())
    
    # Testar features avançadas
    print("\n" + "-" * 60)
    print("2. Testando features avançadas (RSI, MACD, Bollinger)")
    print("-" * 60)
    
    df_avancado = calcular_features_avancadas(df_teste)
    
    print(f"✅ Features avançadas calculadas")
    print(f"   Shape: {df_avancado.shape}")
    print(f"   Colunas adicionais: {[col for col in df_avancado.columns if col not in df_features.columns]}")
    
    # Testar criação de target
    print("\n" + "-" * 60)
    print("3. Testando criação de target/label")
    print("-" * 60)
    
    df_com_target = criar_target_label(df_avancado, periodos_futuros=5, threshold_positivo=1.0)
    
    print(f"✅ Target criado")
    print(f"   Shape: {df_com_target.shape}")
    print(f"   Distribuição do target:")
    print(df_com_target['target'].value_counts())
    print(f"   Proporção positivos: {df_com_target['target'].mean():.2%}")
    
    print("\n" + "=" * 60)
    print("✅ Todos os testes concluídos com sucesso!")
    print("=" * 60)
