"""
Análise Técnica - Cálculo de Médias Móveis e Indicadores
"""
from decimal import Decimal
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
import pandas_ta as ta

from src.utils.logger import get_loggers

logger, _ = get_loggers()


class AnaliseTecnica:
    """
    Calcula indicadores técnicos baseados em histórico de preços

    Principais funcionalidades:
    - SMA (Simple Moving Average) de 4 semanas
    - Suporte para múltiplos timeframes (1h, 4h)
    - Cache de dados para eficiência
    """

    def __init__(self, api_manager):
        """
        Args:
            api_manager: Instância do APIManager
        """
        self.api = api_manager
        self.cache_klines = {}  # Cache de klines por símbolo/intervalo
        self.cache_timestamp = {}  # Timestamp do último cache
        self.cache_ttl_seconds = 300  # Cache válido por 5 minutos

    def obter_klines_cached(
        self,
        simbolo: str,
        intervalo: str,
        periodo_dias: int
    ) -> List[Dict]:
        """
        Obtém klines com cache

        Args:
            simbolo: Par (ex: ADAUSDT)
            intervalo: 1h, 4h, etc
            periodo_dias: Número de dias de histórico

        Returns:
            Lista de klines processados: [{
                'timestamp': datetime,
                'open': Decimal,
                'high': Decimal,
                'low': Decimal,
                'close': Decimal,
                'volume': Decimal
            }]
        """
        cache_key = f"{simbolo}_{intervalo}_{periodo_dias}"

        # Verificar cache
        agora = datetime.now()
        if cache_key in self.cache_klines:
            tempo_cache = self.cache_timestamp.get(cache_key)
            if tempo_cache and (agora - tempo_cache).total_seconds() < self.cache_ttl_seconds:
                logger.debug(f"📦 Usando cache para {cache_key}")
                return self.cache_klines[cache_key]

        # Calcular quantos candles precisamos
        # 1h = 24 candles/dia, 4h = 6 candles/dia
        candles_por_dia = {
            '1h': 24,
            '4h': 6,
            '1d': 1
        }

        candles_necessarios = periodo_dias * candles_por_dia.get(intervalo, 24)
        candles_necessarios = min(candles_necessarios, 1000)  # Limite da Binance

        logger.info(f"📊 Buscando {candles_necessarios} candles de {simbolo} ({intervalo})...")

        # Buscar klines da API
        klines_raw = self.api.obter_klines(
            simbolo=simbolo,
            intervalo=intervalo,
            limite=candles_necessarios
        )

        if not klines_raw:
            logger.error(f"❌ Não foi possível obter klines de {simbolo}")
            return []

        # Processar klines
        klines_processados = []
        for kline in klines_raw:
            klines_processados.append({
                'timestamp': datetime.fromtimestamp(int(kline[0]) / 1000),
                'open': Decimal(str(kline[1])),
                'high': Decimal(str(kline[2])),
                'low': Decimal(str(kline[3])),
                'close': Decimal(str(kline[4])),
                'volume': Decimal(str(kline[5]))
            })

        # Atualizar cache
        self.cache_klines[cache_key] = klines_processados
        self.cache_timestamp[cache_key] = agora

        logger.info(f"✅ {len(klines_processados)} candles obtidos")
        return klines_processados

    def calcular_sma(
        self,
        simbolo: str,
        intervalo: str,
        periodo_dias: int
    ) -> Optional[Decimal]:
        """
        Calcula SMA (Simple Moving Average) de N dias

        Args:
            simbolo: Par (ex: ADAUSDT)
            intervalo: 1h, 4h, etc
            periodo_dias: Número de dias (ex: 28 = 4 semanas)

        Returns:
            SMA calculada ou None se houver erro
        """
        klines = self.obter_klines_cached(simbolo, intervalo, periodo_dias)

        if not klines or len(klines) == 0:
            logger.error(f"❌ Não há dados suficientes para calcular SMA")
            return None

        # Calcular média dos preços de fechamento
        soma = Decimal('0')
        for kline in klines:
            soma += kline['close']

        sma = soma / Decimal(str(len(klines)))

        logger.info(
            f"📈 SMA {periodo_dias}d ({intervalo}): ${sma:.6f} "
            f"(baseado em {len(klines)} candles)"
        )

        return sma

    def calcular_sma_multiplos_timeframes(
        self,
        simbolo: str,
        periodo_dias: int = 28
    ) -> Dict[str, Decimal]:
        """
        Calcula SMA em múltiplos timeframes

        Args:
            simbolo: Par (ex: ADAUSDT)
            periodo_dias: Número de dias (default: 28 = 4 semanas)

        Returns:
            Dict com SMAs: {
                '1h': Decimal,
                '4h': Decimal,
                'media': Decimal  # Média das duas
            }
        """
        logger.info(f"📊 Calculando SMA {periodo_dias}d para {simbolo}...")

        sma_1h = self.calcular_sma(simbolo, '1h', periodo_dias)
        sma_4h = self.calcular_sma(simbolo, '4h', periodo_dias)

        if not sma_1h or not sma_4h:
            logger.error("❌ Não foi possível calcular SMAs")
            return {}

        # Calcular média ponderada dos dois timeframes
        # Dando mais peso ao 4h (60%) vs 1h (40%)
        sma_media = (sma_1h * Decimal('0.4')) + (sma_4h * Decimal('0.6'))

        resultado = {
            '1h': sma_1h,
            '4h': sma_4h,
            'media': sma_media
        }

        logger.info("=" * 60)
        logger.info(f"📊 SMA {periodo_dias} DIAS - {simbolo}")
        logger.info(f"   SMA 1h:  ${sma_1h:.6f}")
        logger.info(f"   SMA 4h:  ${sma_4h:.6f}")
        logger.info(f"   Média ponderada: ${sma_media:.6f} (40% 1h + 60% 4h)")
        logger.info("=" * 60)

        return resultado

    def calcular_queda_desde_sma(
        self,
        preco_atual: Decimal,
        sma: Decimal
    ) -> Decimal:
        """
        Calcula percentual de queda desde a SMA

        Args:
            preco_atual: Preço atual
            sma: SMA de referência

        Returns:
            Percentual de queda (positivo se caiu, negativo se subiu)
        """
        if sma == 0:
            return Decimal('0')

        variacao = ((sma - preco_atual) / sma) * Decimal('100')
        return variacao

    def obter_estatisticas_periodo(
        self,
        simbolo: str,
        intervalo: str,
        periodo_dias: int
    ) -> Dict:
        """
        Obtém estatísticas do período

        Args:
            simbolo: Par
            intervalo: Timeframe
            periodo_dias: Período

        Returns:
            Dict com estatísticas: {
                'sma': Decimal,
                'preco_maximo': Decimal,
                'preco_minimo': Decimal,
                'volatilidade': Decimal
            }
        """
        klines = self.obter_klines_cached(simbolo, intervalo, periodo_dias)

        if not klines:
            return {}

        precos_fechamento = [k['close'] for k in klines]
        precos_maximos = [k['high'] for k in klines]
        precos_minimos = [k['low'] for k in klines]

        sma = sum(precos_fechamento) / Decimal(str(len(precos_fechamento)))
        preco_max = max(precos_maximos)
        preco_min = min(precos_minimos)
        volatilidade = ((preco_max - preco_min) / preco_min) * Decimal('100')

        return {
            'sma': sma,
            'preco_maximo': preco_max,
            'preco_minimo': preco_min,
            'volatilidade': volatilidade,
            'num_candles': len(klines)
        }

    def get_rsi(self, par, timeframe='4h', periodo=14, limite_candles=100) -> Optional[Decimal]:
        """Busca o valor do RSI para um par de moedas."""
        try:
            # Sanitizar timeframe (pode estar malformado como "30Mh")
            timeframe_clean = str(timeframe).lower() if timeframe else '4h'
            if timeframe_clean.endswith('mh'):
                timeframe_clean = timeframe_clean[:-1]  # Remove 'h' final de "30Mh" → "30m"
            elif timeframe_clean.endswith('hh'):
                timeframe_clean = timeframe_clean[:-1]  # Remove 'h' final de "1hh" → "1h"

            klines = self.api.obter_klines(par, timeframe_clean, limite_candles)
            if not klines:
                return None

            # Fix: Handle variable number of columns from different exchanges
            # Some exchanges return 6 columns, others 7 or more
            if len(klines[0]) >= 6:
                # Take only the first 6 columns we need
                klines_clean = [[k[0], k[1], k[2], k[3], k[4], k[5]] for k in klines]
                df = pd.DataFrame(klines_clean, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            else:
                logger.error(f"Insufficient kline data columns: {len(klines[0])} < 6")
                return None
                
            df['close'] = pd.to_numeric(df['close'])

            rsi = df.ta.rsi(length=periodo)
            if rsi is None or rsi.empty:
                return None

            return Decimal(str(rsi.iloc[-1]))
        except Exception as e:
            logger.error(f"Erro ao calcular RSI para {par}: {e}")
            return None
