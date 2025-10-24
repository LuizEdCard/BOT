#!/usr/bin/env python3
"""
Script de Treino Offline - Modelo de Deteção de Regime de Mercado

Este script treina um modelo KMeans para identificar 2 regimes de mercado:
- Regime 0 (Sideways): Baixa volatilidade e ADX
- Regime 1 (Trending): Alta volatilidade e ADX

O modelo treinado é salvo em disco e pode ser carregado pelo bot para
adaptar suas estratégias em tempo real.
"""

import pandas as pd
import joblib
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np

# Importar função de feature engineering do nosso módulo
from src.core.feature_engineering import calcular_features


def carregar_dados_historicos(caminho_csv: str) -> pd.DataFrame:
    """
    Carrega dados históricos OHLCV de um arquivo CSV.
    
    Args:
        caminho_csv: Caminho para o arquivo CSV com dados históricos
        
    Returns:
        DataFrame com dados OHLCV
    """
    print(f"📂 Carregando dados históricos de: {caminho_csv}")
    
    df = pd.read_csv(caminho_csv)
    
    # Normalizar nomes de colunas para minúsculas
    df.columns = df.columns.str.lower()
    
    # Verificar colunas necessárias
    colunas_necessarias = ['open', 'high', 'low', 'close', 'volume']
    for col in colunas_necessarias:
        if col not in df.columns:
            raise ValueError(f"Coluna '{col}' não encontrada no CSV")
    
    print(f"✅ {len(df)} velas carregadas")
    print(f"   Período: {df.index[0] if 'timestamp' in df.columns else 'N/A'} até {df.index[-1] if 'timestamp' in df.columns else 'N/A'}")
    
    return df


def preparar_features_para_clustering(df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """
    Prepara features para treino do modelo de clustering.
    
    Args:
        df: DataFrame com features calculadas
        
    Returns:
        Tupla (df_original, features_normalizadas)
    """
    # Selecionar features relevantes para deteção de regime
    features_regime = ['volatilidade', 'adx']
    
    # Verificar se features existem
    for feature in features_regime:
        if feature not in df.columns:
            raise ValueError(f"Feature '{feature}' não encontrada. Execute calcular_features() primeiro.")
    
    # Extrair features e remover NaNs
    X = df[features_regime].values
    
    # Verificar NaNs
    if np.isnan(X).any():
        print("⚠️  Aviso: NaNs encontrados nas features. Removendo...")
        mask = ~np.isnan(X).any(axis=1)
        X = X[mask]
        df = df[mask]
    
    print(f"\n📊 Features selecionadas para clustering:")
    print(f"   - volatilidade")
    print(f"   - adx")
    print(f"   Total de amostras: {len(X)}")
    
    # Normalizar features (importante para KMeans)
    scaler = StandardScaler()
    X_normalized = scaler.fit_transform(X)
    
    print(f"\n🔄 Features normalizadas (StandardScaler)")
    print(f"   Média: {X_normalized.mean(axis=0)}")
    print(f"   Desvio padrão: {X_normalized.std(axis=0)}")
    
    return df, X_normalized, scaler


def treinar_modelo_kmeans(X: np.ndarray, n_clusters: int = 2, random_state: int = 42) -> KMeans:
    """
    Treina modelo KMeans para deteção de regime.
    
    Args:
        X: Array de features normalizadas
        n_clusters: Número de clusters (regimes)
        random_state: Seed para reprodutibilidade
        
    Returns:
        Modelo KMeans treinado
    """
    print(f"\n🤖 Treinando modelo KMeans...")
    print(f"   n_clusters: {n_clusters}")
    print(f"   random_state: {random_state}")
    
    modelo = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        n_init=10,  # Número de inicializações
        max_iter=300  # Máximo de iterações
    )
    
    modelo.fit(X)
    
    print(f"✅ Modelo treinado com sucesso!")
    print(f"   Inércia: {modelo.inertia_:.2f}")
    print(f"   Iterações: {modelo.n_iter_}")
    
    return modelo


def analisar_clusters(modelo: KMeans, scaler: StandardScaler, df: pd.DataFrame) -> None:
    """
    Analisa os centros dos clusters para identificar regimes.
    
    Args:
        modelo: Modelo KMeans treinado
        scaler: Scaler usado na normalização
        df: DataFrame original com features
    """
    print(f"\n" + "=" * 70)
    print("ANÁLISE DOS CLUSTERS (REGIMES DE MERCADO)")
    print("=" * 70)
    
    # Desnormalizar centros dos clusters
    centros_normalizados = modelo.cluster_centers_
    centros_originais = scaler.inverse_transform(centros_normalizados)
    
    # Predizer labels para todo o dataset
    features = df[['volatilidade', 'adx']].values
    features_normalizadas = scaler.transform(features)
    labels = modelo.predict(features_normalizadas)
    
    # Adicionar labels ao dataframe
    df['regime'] = labels
    
    # Analisar cada cluster
    for i in range(len(centros_originais)):
        print(f"\n{'─' * 70}")
        print(f"CLUSTER {i}")
        print(f"{'─' * 70}")
        
        # Centro do cluster
        volatilidade_centro = centros_originais[i][0]
        adx_centro = centros_originais[i][1]
        
        print(f"Centro do cluster:")
        print(f"  Volatilidade: {volatilidade_centro:.4f}")
        print(f"  ADX:          {adx_centro:.2f}")
        
        # Estatísticas das amostras deste cluster
        cluster_samples = df[df['regime'] == i]
        n_samples = len(cluster_samples)
        percentual = (n_samples / len(df)) * 100
        
        print(f"\nEstatísticas ({n_samples} amostras, {percentual:.1f}% do total):")
        print(f"  Volatilidade: média={cluster_samples['volatilidade'].mean():.4f}, "
              f"std={cluster_samples['volatilidade'].std():.4f}")
        print(f"  ADX:          média={cluster_samples['adx'].mean():.2f}, "
              f"std={cluster_samples['adx'].std():.2f}")
        
        # Identificar tipo de regime
        if adx_centro > 25 or volatilidade_centro > df['volatilidade'].median():
            regime_tipo = "🔥 TRENDING (Alta volatilidade/tendência)"
        else:
            regime_tipo = "📊 SIDEWAYS (Baixa volatilidade/consolidação)"
        
        print(f"\nInterpretação: {regime_tipo}")
    
    print(f"\n{'═' * 70}")
    
    # Distribuição dos regimes
    print(f"\n📈 Distribuição dos Regimes:")
    print(df['regime'].value_counts().sort_index())
    print(f"\nProporção:")
    print(df['regime'].value_counts(normalize=True).sort_index())


def salvar_modelo_e_scaler(modelo: KMeans, scaler: StandardScaler, 
                           caminho_modelo: str = 'dados/modelo_regime_kmeans.pkl',
                           caminho_scaler: str = 'dados/scaler_regime.pkl') -> None:
    """
    Salva o modelo treinado e o scaler em disco.
    
    Args:
        modelo: Modelo KMeans treinado
        scaler: StandardScaler usado
        caminho_modelo: Caminho para salvar o modelo
        caminho_scaler: Caminho para salvar o scaler
    """
    # Criar diretório se não existir
    Path(caminho_modelo).parent.mkdir(parents=True, exist_ok=True)
    
    # Salvar modelo
    joblib.dump(modelo, caminho_modelo)
    print(f"\n💾 Modelo salvo em: {caminho_modelo}")
    
    # Salvar scaler
    joblib.dump(scaler, caminho_scaler)
    print(f"💾 Scaler salvo em: {caminho_scaler}")
    
    # Verificar tamanhos dos arquivos
    tamanho_modelo = Path(caminho_modelo).stat().st_size / 1024  # KB
    tamanho_scaler = Path(caminho_scaler).stat().st_size / 1024  # KB
    
    print(f"\n📦 Tamanho dos arquivos:")
    print(f"   Modelo: {tamanho_modelo:.2f} KB")
    print(f"   Scaler: {tamanho_scaler:.2f} KB")


def main():
    """Função principal do script de treino."""
    
    print("=" * 70)
    print("🚀 TREINO DO MODELO DE DETEÇÃO DE REGIME DE MERCADO")
    print("=" * 70)
    
    # ══════════════════════════════════════════════════════════════════════
    # CONFIGURAÇÃO
    # ══════════════════════════════════════════════════════════════════════
    CAMINHO_CSV = 'dados/historico_btcusdt_1h.csv'  # Ajuste conforme necessário
    CAMINHO_MODELO = 'dados/modelo_regime_kmeans.pkl'
    CAMINHO_SCALER = 'dados/scaler_regime.pkl'
    N_CLUSTERS = 2  # Sideways vs Trending
    RANDOM_STATE = 42
    
    try:
        # ══════════════════════════════════════════════════════════════════
        # 1. CARREGAR DADOS HISTÓRICOS
        # ══════════════════════════════════════════════════════════════════
        df = carregar_dados_historicos(CAMINHO_CSV)
        
        # ══════════════════════════════════════════════════════════════════
        # 2. CALCULAR FEATURES
        # ══════════════════════════════════════════════════════════════════
        print(f"\n{'─' * 70}")
        print("CALCULANDO FEATURES TÉCNICAS")
        print(f"{'─' * 70}")
        
        df_features = calcular_features(df)
        
        print(f"✅ Features calculadas")
        print(f"   Shape final: {df_features.shape}")
        
        # ══════════════════════════════════════════════════════════════════
        # 3. PREPARAR FEATURES PARA CLUSTERING
        # ══════════════════════════════════════════════════════════════════
        print(f"\n{'─' * 70}")
        print("PREPARANDO FEATURES PARA CLUSTERING")
        print(f"{'─' * 70}")
        
        df_preparado, X_normalized, scaler = preparar_features_para_clustering(df_features)
        
        # ══════════════════════════════════════════════════════════════════
        # 4. TREINAR MODELO KMEANS
        # ══════════════════════════════════════════════════════════════════
        print(f"\n{'─' * 70}")
        print("TREINO DO MODELO")
        print(f"{'─' * 70}")
        
        modelo = treinar_modelo_kmeans(X_normalized, n_clusters=N_CLUSTERS, random_state=RANDOM_STATE)
        
        # ══════════════════════════════════════════════════════════════════
        # 5. ANALISAR CLUSTERS
        # ══════════════════════════════════════════════════════════════════
        analisar_clusters(modelo, scaler, df_preparado)
        
        # ══════════════════════════════════════════════════════════════════
        # 6. SALVAR MODELO E SCALER
        # ══════════════════════════════════════════════════════════════════
        print(f"\n{'─' * 70}")
        print("SALVANDO MODELO")
        print(f"{'─' * 70}")
        
        salvar_modelo_e_scaler(modelo, scaler, CAMINHO_MODELO, CAMINHO_SCALER)
        
        # ══════════════════════════════════════════════════════════════════
        # SUCESSO
        # ══════════════════════════════════════════════════════════════════
        print(f"\n{'═' * 70}")
        print("✅ TREINO CONCLUÍDO COM SUCESSO!")
        print(f"{'═' * 70}")
        
        print(f"\n📋 Próximos passos:")
        print(f"   1. Verifique os centros dos clusters acima")
        print(f"   2. Identifique qual cluster é 'Trending' e qual é 'Sideways'")
        print(f"   3. Integre o modelo no bot usando joblib.load()")
        print(f"   4. Use modelo.predict() em tempo real para adaptar estratégias")
        
        print(f"\n💡 Exemplo de uso no bot:")
        print(f"   modelo = joblib.load('{CAMINHO_MODELO}')")
        print(f"   scaler = joblib.load('{CAMINHO_SCALER}')")
        print(f"   features = scaler.transform([[volatilidade, adx]])")
        print(f"   regime = modelo.predict(features)[0]  # 0 ou 1")
        
    except FileNotFoundError as e:
        print(f"\n❌ ERRO: Arquivo não encontrado")
        print(f"   {e}")
        print(f"\n💡 Certifique-se de que existe um arquivo CSV com dados históricos em:")
        print(f"   {CAMINHO_CSV}")
        print(f"\n   O arquivo deve conter colunas: open, high, low, close, volume")
        
    except ValueError as e:
        print(f"\n❌ ERRO: {e}")
        
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
