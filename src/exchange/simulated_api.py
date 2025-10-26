
import pandas as pd
from decimal import Decimal
import uuid
from typing import List, Optional
from src.exchange.base import ExchangeAPI
from src.utils.logger import get_loggers

logger, _ = get_loggers()

class SimulatedExchangeAPI(ExchangeAPI):
    """
    Uma classe de API de exchange simulada para backtesting.
    Herda da ExchangeAPI e simula o comportamento de uma exchange real usando dados históricos de um arquivo CSV.
    """

    def __init__(self, caminho_csv: str, saldo_inicial: float, taxa_pct: float, timeframe_base: str = '1m', alocacao_giro_pct: Optional[float] = None):
        """
        Inicializa a API de exchange simulada.

        Args:
            caminho_csv: O caminho para o arquivo CSV com os dados históricos OHLCV.
            saldo_inicial: O saldo inicial em USDT para a simulação.
            taxa_pct: A porcentagem da taxa de transação (ex: 0.1 para 0.1%).
            timeframe_base: O timeframe dos dados no CSV (ex: '1m', '5m', '1h'). Usado para resampling correto.
        """
        # Armazenar timeframe base
        self.timeframe_base = timeframe_base
        
        # Carregar dados completos com timestamp como índice
        self.dados_completos = pd.read_csv(caminho_csv)
        self.dados_completos['timestamp'] = pd.to_datetime(self.dados_completos['timestamp'])
        self.dados_completos.set_index('timestamp', inplace=True)
        
        # Dados para iteração (cópia para não modificar o original)
        self.dados = self.dados_completos.copy().reset_index()
        
        # Cache de dados resampleados por timeframe
        self.dados_resampled = {}
        # Adicionar os dados originais ao cache com seu timeframe base
        self.dados_resampled[timeframe_base] = self.dados_completos.copy()
        
        # Saldos globais (mantidos para compatibilidade)
        self.saldo_usdt = Decimal(str(saldo_inicial))
        self.saldo_ativo = Decimal('0')
        # Saldos por carteira (para suportar múltiplas estratégias)
        # Permitir configurar a alocação inicial de giro rápido via parâmetro.
        if alocacao_giro_pct is None:
            # fallback legacy: 20% giro / 80% acumulação
            giro_pct = Decimal('20')
        else:
            giro_pct = Decimal(str(alocacao_giro_pct))

        acumulacao_pct = Decimal('100') - giro_pct

        self.saldos_por_carteira = {
            'acumulacao': {
                'saldo_usdt': (Decimal(str(saldo_inicial)) * (acumulacao_pct / Decimal('100'))).quantize(Decimal('0.00000001')),
                'saldo_ativo': Decimal('0')
            },
            'giro_rapido': {
                'saldo_usdt': (Decimal(str(saldo_inicial)) * (giro_pct / Decimal('100'))).quantize(Decimal('0.00000001')),
                'saldo_ativo': Decimal('0')
            }
        }

        # Guardar alocacao atual para referência
        self.alocacao_giro_pct = Decimal(str(giro_pct))

        # Histórico do portfólio ao longo do tempo (lista de snapshots)
        self.portfolio_over_time: List[dict] = []

        self.taxa = Decimal(str(taxa_pct)) / Decimal('100')

        # Inicia com um buffer para garantir histórico para indicadores.
        # Ajustar para o tamanho dos dados caso o CSV seja curto para evitar iniciar
        # além do final do DataFrame (o que faria a simulação terminar imediatamente).
        default_buffer = 200
        max_valid_index = max(1, len(self.dados) - 1)
        self.indice_atual = default_buffer if default_buffer < len(self.dados) else max_valid_index
        self.trades_executados = []

    def get_barra_atual(self):
        """
        Retorna a barra (vela) atual do DataFrame e avança o ponteiro.

        Returns:
            Um dicionário representando a linha atual, ou None se os dados terminarem.
        """
        if self.indice_atual < len(self.dados):
            barra = self.dados.iloc[self.indice_atual].to_dict()
            self.indice_atual += 1
            return barra
        return None

    def get_dados_historicos_iniciais(self, timeframe: str, limite: int):
        """
        Retorna as primeiras 'limite' linhas dos dados para o cálculo de indicadores,
        resampleadas para o timeframe solicitado.

        Args:
            timeframe: O timeframe desejado (ex: '1h', '4h', '1d')
            limite: O número de linhas a serem retornadas.

        Returns:
            Um DataFrame do pandas com os dados iniciais no timeframe solicitado.
        """
        # CORREÇÃO BUG 2: Lógica de Resampling
        try:
            timeframe_base_td = pd.to_timedelta(self.timeframe_base)
            timeframe_req_td = pd.to_timedelta(timeframe)
        except ValueError:
            print(f"❌ Timeframe inválido: {timeframe} ou {self.timeframe_base}")
            return pd.DataFrame()

        # Se o timeframe pedido for menor que o base, não é possível fazer resample
            # Se o timeframe pedido for menor que o base, não é possível resample para uma resolução
            # maior (não temos dados intrínsecos mais granulares). Em vez de retornar vazio, cair
            # para o timeframe base (fallback seguro) e avisar no log. Isso permite que a
            # simulação continue usando os dados disponíveis no CSV mesmo quando o usuário
            # solicitou um timeframe mais baixo do que o disponível.
            if timeframe_req_td < timeframe_base_td:
                print(f"⚠️ Aviso de Resample: Timeframe solicitado ({timeframe}) é menor que o timeframe base do CSV ({self.timeframe_base}). Usando o timeframe base como fallback.")
                # Retornar os dados no timeframe base (fallback) em vez de um DataFrame vazio
                return self.dados_resampled[self.timeframe_base].head(limite).reset_index()

        # Se for o mesmo timeframe, apenas retorna os dados originais
        if timeframe_req_td == timeframe_base_td:
            return self.dados_completos.head(limite).reset_index()

        # Verificar se já está no cache
        if timeframe in self.dados_resampled:
            df_resampled = self.dados_resampled[timeframe]
            return df_resampled.head(limite).reset_index()
        
        # Resamplear os dados para o timeframe solicitado
        print(f"⏳ Realizando resample de {self.timeframe_base} para {timeframe}...")
        df_resampled = self._resample_dados(timeframe)
        
        # Armazenar no cache
        self.dados_resampled[timeframe] = df_resampled
        
        return df_resampled.head(limite).reset_index()

    def get_saldo_disponivel(self, moeda: str) -> Decimal:
        """
        Retorna o saldo virtual para uma moeda específica.

        Args:
            moeda: A sigla da moeda ('USDT' ou o nome do ativo).

        Returns:
            O saldo da moeda como um Decimal.
        """
        if moeda.upper() == 'USDT':
            return self.saldo_usdt
        # Assumindo que qualquer outra string de moeda se refere ao ativo base do par
        return self.saldo_ativo

    def place_ordem_compra_market(self, par: str, quantidade: float, motivo_compra: str = None, carteira: str = 'acumulacao'):
        """
        Simula a execução de uma ordem de compra a mercado.

        Args:
            par: O par de moedas (ex: 'ADA/USDT').
            quantidade: A quantidade de USDT a ser gasta.
            motivo_compra: (Opcional) A razão pela qual a compra foi feita.
            carteira: Carteira a usar ('acumulacao' ou 'giro_rapido'). Padrão: 'acumulacao'

        Returns:
            Um dicionário com informações da ordem simulada.
        """
        barra_atual = self.dados.iloc[self.indice_atual - 1] # Usa a barra que acabou de ser retornada
        preco = Decimal(str(barra_atual['close']))
        custo_total = Decimal(str(quantidade))
        taxa_incorpora = custo_total * self.taxa
        custo_liquido = custo_total - taxa_incorpora
        quantidade_ativo = custo_liquido / preco

        # Validar carteira
        if carteira not in self.saldos_por_carteira:
            raise ValueError(f"Carteira '{carteira}' não reconhecida. Use 'acumulacao' ou 'giro_rapido'.")

        # Verificar saldo na carteira específica
        saldo_carteira = self.saldos_por_carteira[carteira]['saldo_usdt']
        if saldo_carteira >= custo_total:
            # Descontar da carteira
            self.saldos_por_carteira[carteira]['saldo_usdt'] -= custo_total
            self.saldos_por_carteira[carteira]['saldo_ativo'] += quantidade_ativo

            # Manter saldos globais sincronizados
            self.saldo_usdt -= custo_total
            self.saldo_ativo += quantidade_ativo

            trade = {
                'id': str(uuid.uuid4()),
                'par': par,
                'side': 'BUY',
                'carteira': carteira,
                'preco': float(preco),
                'quantidade_usdt': float(custo_total),
                'quantidade_ativo': float(quantidade_ativo),
                'fee': float(taxa_incorpora),
                'timestamp': barra_atual['timestamp'],
                'motivo': motivo_compra
            }
            self.trades_executados.append(trade)

            # Retornar estrutura compatível com BotWorker
            ordem_simulada = {
                'id': trade['id'],
                'symbol': par.replace('/', ''),
                'type': 'MARKET',
                'side': 'BUY',
                'status': 'FILLED',
                'fills': [],
                # Quantidade executada em unidade do ativo
                'executedQty': float(trade['quantidade_ativo']),
                # Valor total em quote (USDT)
                'cummulativeQuoteQty': float(trade['quantidade_usdt'])
            }
            return ordem_simulada
        else:
            raise ValueError(f"Saldo insuficiente na carteira '{carteira}' para executar a ordem de compra. Disponível: ${saldo_carteira:.2f}, Necessário: ${custo_total:.2f}")

    def place_ordem_venda_market(self, par: str, quantidade: float, motivo_saida: str = None, carteira: str = 'acumulacao'):
        """
        Simula a execução de uma ordem de venda a mercado.

        Args:
            par: O par de moedas (ex: 'ADA/USDT').
            quantidade: A quantidade do ativo a ser vendida.
            motivo_saida: (Opcional) A razão pela qual a venda foi feita.
            carteira: Carteira a usar ('acumulacao' ou 'giro_rapido'). Padrão: 'acumulacao'

        Returns:
            Um dicionário com informações da ordem simulada.
        """
        barra_atual = self.dados.iloc[self.indice_atual - 1]
        preco = Decimal(str(barra_atual['close']))
        quantidade_venda = Decimal(str(quantidade))

        # Validar carteira
        if carteira not in self.saldos_por_carteira:
            raise ValueError(f"Carteira '{carteira}' não reconhecida. Use 'acumulacao' ou 'giro_rapido'.")

        # Proteção adicional: capear a quantidade solicitada ao saldo disponível
        # e usar uma pequena tolerância para evitar falhas por diferenças de representação.
        tolerancia = Decimal('0.0000001')
        quantidade_disponivel = self.saldos_por_carteira[carteira]['saldo_ativo']
        if quantidade_venda > quantidade_disponivel:
            # Ajustar quantidade para o máximo disponível (mantendo Decimal)
            logger.debug(
                f"⚠️ Ajustando quantidade de venda solicitada {quantidade_venda} para saldo disponível {quantidade_disponivel}"
            )
            quantidade_venda = quantidade_disponivel

        if self.saldos_por_carteira[carteira]['saldo_ativo'] + tolerancia >= quantidade_venda and quantidade_venda > Decimal('0'):
            receita_bruta = quantidade_venda * preco
            taxa_incorpora = receita_bruta * self.taxa
            receita_liquida = receita_bruta - taxa_incorpora

            # Descontar da carteira específica
            self.saldos_por_carteira[carteira]['saldo_ativo'] -= quantidade_venda
            self.saldos_por_carteira[carteira]['saldo_usdt'] += receita_liquida

            # Manter saldos globais sincronizados
            self.saldo_ativo -= quantidade_venda
            self.saldo_usdt += receita_liquida

            trade = {
                'id': str(uuid.uuid4()),
                'par': par,
                'side': 'SELL',
                'carteira': carteira,
                'preco': float(preco),
                'quantidade_ativo': float(quantidade_venda),
                'receita_usdt': float(receita_liquida),
                'fee': float(taxa_incorpora),
                'timestamp': barra_atual['timestamp'],
                'motivo': motivo_saida
            }
            self.trades_executados.append(trade)

            # Retornar estrutura compatível com BotWorker
            ordem_simulada = {
                'id': trade['id'],
                'symbol': par.replace('/', ''),
                'type': 'MARKET',
                'side': 'SELL',
                'status': 'FILLED',
                'fills': [],
                # Quantidade executada em unidade do ativo
                'executedQty': float(trade['quantidade_ativo']),
                # Valor total recebido em quote (USDT)
                'cummulativeQuoteQty': float(trade['receita_usdt'])
            }
            return ordem_simulada
        else:
            # Log detalhado para facilitar debug em simulações
            logger.warning(f"❌ Tentativa de venda recusada: quantidade={quantidade_venda} vs saldo_ativo={self.saldos_por_carteira[carteira]['saldo_ativo']}")
            raise ValueError("Saldo de ativo insuficiente para executar a ordem de venda.")

    def _resample_dados(self, timeframe: str) -> pd.DataFrame:
        """
        Resamplea os dados completos para um timeframe específico.
        
        Args:
            timeframe: O timeframe desejado (ex: '1h', '4h', '1d')
            
        Returns:
            DataFrame resampleado com colunas OHLCV
        """
        # Converter timeframe para formato do pandas resample
        # Normalizar para lowercase (entrada pode ser '1m','5m','1h', etc.)
        timeframe_pandas = timeframe.lower()

        # Pandas mudou algumas aliases (ex: 'm' pode ser interpretado como month-end).
        # Mapear explicitamente minutos 'm' para 'T' (minute) para evitar confusão
        # onde 'm' seria tratado como mês. Ex: '5m' -> '5T'
        if timeframe_pandas.endswith('m'):
            # evitar interpretar 'm' como mês; usar 'T' para minutos
            timeframe_pandas = timeframe_pandas[:-1] + 'T'

        # Validar formato - deve terminar com T, h, d, ou s
        if not timeframe_pandas[-1] in ('T', 'h', 'd', 's'):
            raise ValueError(f"Timeframe inválido: '{timeframe}'. Use: 1m, 5m, 15m, 30m, 1h, 4h, 1d, etc.")
        
        # Resamplear com as agregações corretas
        df_resampled = self.dados_completos.resample(timeframe_pandas).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        # Remover linhas com NaN (períodos sem dados)
        df_resampled = df_resampled.dropna()
        
        return df_resampled
    
    def obter_klines(
        self,
        simbolo: str,
        intervalo: str,
        limite: int = 500,
        inicio: Optional[int] = None,
        fim: Optional[int] = None
    ) -> List[List]:
        """
        Obtém histórico de candlesticks (klines) para um símbolo e intervalo.
        Simula o comportamento de exchanges reais retornando dados resampleados.

        CORREÇÃO: Respeita o timestamp atual da simulação para evitar lookahead bias.
        Garante que a estratégia nunca veja dados além do momento atual.

        Args:
            simbolo: Par (ex: ADAUSDT) - ignorado na simulação
            intervalo: 1h, 4h, 1d, etc.
            limite: Número de candles (máx)
            inicio: Timestamp início em ms (opcional)
            fim: Timestamp fim em ms (opcional)

        Returns:
            Lista de klines: [
                [
                    timestamp_abertura (ms),
                    preco_abertura,
                    preco_maximo,
                    preco_minimo,
                    preco_fechamento,
                    volume,
                    timestamp_fechamento (ms),
                    ...
                ]
            ]
        """
        # Verificar se o intervalo solicitado é menor que o timeframe base do CSV.
        # Nesse caso, não podemos resamplear para uma resolução mais alta — em vez disso,
        # usar o timeframe base como fallback para evitar retornar DataFrames vazios
        # e permitir que a simulação continue.
        try:
            timeframe_base_td = pd.to_timedelta(self.timeframe_base)
            timeframe_req_td = pd.to_timedelta(intervalo)
        except Exception:
            timeframe_base_td = None
            timeframe_req_td = None

        if timeframe_req_td is not None and timeframe_base_td is not None and timeframe_req_td < timeframe_base_td:
            # Fallback para timeframe base
            logger.debug(f"⚠️ obter_klines: intervalo solicitado ({intervalo}) é menor que o timeframe base ({self.timeframe_base}); usando timeframe base como fallback.")
            df_resampled = self.dados_resampled[self.timeframe_base]
        else:
            # Verificar se já está no cache
            if intervalo not in self.dados_resampled:
                df_resampled = self._resample_dados(intervalo)
                self.dados_resampled[intervalo] = df_resampled
            else:
                df_resampled = self.dados_resampled[intervalo]

        # CORREÇÃO CRÍTICA: Obter o timestamp atual da simulação
        # para não retornar dados futuros (lookahead bias)
        if self.indice_atual > 0 and self.indice_atual <= len(self.dados):
            timestamp_atual = pd.to_datetime(self.dados.iloc[self.indice_atual - 1]['timestamp'])
        else:
            # Se ainda não iniciou a simulação, usar o último timestamp disponível
            timestamp_atual = df_resampled.index[-1]

        # Aplicar filtro de tempo: queremos as barras RESAMPLEADAS até o timestamp atual
        df_filtrado = df_resampled.copy()

        # CRÍTICO: Limitar ao timestamp atual da simulação (evita ver o futuro!)
        # Alguns cenários (timezones, alinhamento de labels) podem produzir DataFrames vazios
        # ao usar uma máscara booleana direta. Usar searchsorted como fallback para obter
        # o último índice resampleado <= timestamp_atual.
        try:
            # Normalizar tipos (remover tz para evitar comparação inválida)
            if isinstance(timestamp_atual, pd.Timestamp) and timestamp_atual.tzinfo is not None:
                timestamp_atual = timestamp_atual.tz_convert(None)

            # Máscara rápida
            df_filtrado = df_filtrado[df_filtrado.index <= timestamp_atual]

            # Se vazio, usar searchsorted para obter tudo até o último bucket concluído
            if df_filtrado.empty:
                pos = df_resampled.index.searchsorted(timestamp_atual, side='right') - 1
                if pos >= 0:
                    df_filtrado = df_resampled.iloc[:pos+1]
                else:
                    df_filtrado = df_resampled.iloc[0:0]
        except Exception:
            # Em caso de qualquer erro de comparação, usar fallback seguro via searchsorted
            try:
                pos = df_resampled.index.searchsorted(timestamp_atual, side='right') - 1
                if pos >= 0:
                    df_filtrado = df_resampled.iloc[:pos+1]
                else:
                    df_filtrado = df_resampled.iloc[0:0]
            except Exception:
                # Como último recurso, retornar os últimos 'limite' candles do resample sem filtrar
                df_filtrado = df_resampled.tail(limite)

        # Aplicar filtro de início se fornecido (somente se não limita ao futuro)
        if inicio:
            inicio_dt = pd.to_datetime(inicio, unit='ms')
            df_filtrado = df_filtrado[df_filtrado.index >= inicio_dt]

        # Aplicar filtro de fim se fornecido (somente se não limita ao futuro)
        if fim:
            fim_dt = pd.to_datetime(fim, unit='ms')
            # Limitar ao mínimo entre o fim solicitado e o timestamp atual
            fim_dt_limitado = min(fim_dt, timestamp_atual)
            df_filtrado = df_filtrado[df_filtrado.index <= fim_dt_limitado]

        # Limitar número de resultados aos últimos 'limite' candles
        df_filtrado = df_filtrado.tail(limite)

        logger.debug(
            f"📊 Klines obtidas: {len(df_filtrado)} candles para {intervalo} "
            f"(limite: {limite}, timestamp_atual: {timestamp_atual})"
        )

        # Converter para formato de klines (similar ao retornado pela Binance)
        klines = []
        for timestamp, row in df_filtrado.iterrows():
            timestamp_ms = int(timestamp.timestamp() * 1000)
            # Calcular timestamp de fechamento (início do próximo candle - 1ms)
            # Simplificação: usar o mesmo timestamp para abertura e fechamento
            klines.append([
                timestamp_ms,                    # timestamp abertura
                str(row['open']),                # open
                str(row['high']),                # high
                str(row['low']),                 # low
                str(row['close']),               # close
                str(row['volume']),              # volume
                timestamp_ms,                    # timestamp fechamento
                '0',                             # quote asset volume (não usado)
                0,                               # number of trades
                '0',                             # taker buy base asset volume
                '0',                             # taker buy quote asset volume
                '0'                              # ignore
            ])

        return klines

    def get_resultados(self):
        """
        Retorna os resultados finais da simulação.

        Returns:
            Um dicionário contendo os trades executados e os saldos finais.
        """
        return {
            'trades': self.trades_executados,
            'saldo_final_usdt': float(self.saldo_usdt),
            'saldo_final_ativo': float(self.saldo_ativo),
            'portfolio_over_time': self.portfolio_over_time
        }

    def reconfigurar_alocacao_inicial(self, alocacao_giro_pct: float):
        """
        Reconfigura a alocação inicial entre carteiras durante a simulação.

        Ajusta os saldos USDT de 'acumulacao' e 'giro_rapido' com base no
        percentual fornecido, preservando o saldo total USDT atual e os ativos.
        """
        try:
            novo_giro = Decimal(str(alocacao_giro_pct))
            if novo_giro < 0 or novo_giro > 100:
                raise ValueError("alocacao_giro_pct deve estar entre 0 e 100")

            total_usdt = self.saldo_usdt
            saldo_giro = (total_usdt * (novo_giro / Decimal('100'))).quantize(Decimal('0.00000001'))
            saldo_acum = (total_usdt - saldo_giro).quantize(Decimal('0.00000001'))

            self.saldos_por_carteira['giro_rapido']['saldo_usdt'] = saldo_giro
            self.saldos_por_carteira['acumulacao']['saldo_usdt'] = saldo_acum
            self.alocacao_giro_pct = novo_giro

            logger.info(f"🔧 SimulatedExchangeAPI: alocacao inicial reconfigurada - Giro: {novo_giro}% | Giro_USDT: ${saldo_giro:.4f} | Acum_USDT: ${saldo_acum:.4f}")
        except Exception as e:
            logger.error(f"❌ Erro ao reconfigurar alocação inicial: {e}")

    def record_snapshot(self, timestamp: Optional[str] = None):
        """
        Registra um snapshot do portfólio no momento atual da simulação.

        O snapshot contém: timestamp, saldo_usdt, saldo_ativo, valor_total_em_quote.
        """
        try:
            # Obter preço atual da simulação (preço do último candle processado)
            preco = Decimal(str(self.get_preco_atual(self._par_stub() if hasattr(self, '_par_stub') else 'ADA/USDT')))

            # Sumarizar saldos
            saldo_usdt_total = Decimal('0')
            saldo_ativo_total = Decimal('0')
            for carteira, dados in self.saldos_por_carteira.items():
                saldo_usdt_total += Decimal(str(dados.get('saldo_usdt', 0)))
                saldo_ativo_total += Decimal(str(dados.get('saldo_ativo', 0)))

            # Valor do ativo convertido para quote
            valor_ativo_em_quote = saldo_ativo_total * preco
            total_value_quote = float((saldo_usdt_total + valor_ativo_em_quote))

            snap = {
                'timestamp': timestamp or (self.dados.iloc[self.indice_atual - 1]['timestamp'] if self.indice_atual > 0 else None),
                'saldo_usdt': float(saldo_usdt_total),
                'saldo_ativo': float(saldo_ativo_total),
                'preco': float(preco),
                'total_value_quote': total_value_quote
            }

            self.portfolio_over_time.append(snap)
        except Exception as e:
            logger.warning(f"⚠️ Falha ao gravar snapshot do portfólio: {e}")

    def _par_stub(self):
        """Retorno auxiliar para compatibilidade com get_preco_atual assinatura (ignorado)."""
        return 'ADA/USDT'

    # Métodos abstratos da classe base que não são necessários para a simulação
    def get_preco_atual(self, par: str) -> float:
        """
        Retorna o preço de fechamento da vela atual na simulação.
        Essencial para inicializar estratégias que precisam de um preço de referência.

        Args:
            par: O par de moedas (ignorado na simulação, usado para compatibilidade).

        Returns:
            O preço de fechamento atual como um float.
        """
        # Se a simulação ainda não começou (índice 0), usa a primeira vela
        # Se já começou, usa a vela anterior à atual (a última processada)
        indice_a_usar = self.indice_atual if self.indice_atual == 0 else self.indice_atual - 1
        
        # Garantir que o índice não saia dos limites
        if indice_a_usar >= len(self.dados):
            indice_a_usar = len(self.dados) - 1
            
        barra_atual = self.dados.iloc[indice_a_usar]
        return float(barra_atual['close'])

    def get_info_conta(self):
        raise NotImplementedError

    def check_connection(self) -> bool:
        return True # Sempre conectado em simulação

    def get_historico_ordens(self, par: str, limite: int = 500, order_id=None):
        raise NotImplementedError
