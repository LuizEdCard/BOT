# 📊 RELATÓRIO COMPLETO DO PROJETO - PARTE 1

**Data:** 12 de outubro de 2025
**Versão:** 1.0
**Ambiente:** PRODUCAO
**Branch:** master / desenvolvimento

---

## 📁 1. ESTRUTURA DE PASTAS

```
BOT/
├── .bot.pid                          # PID do processo em execução
├── .gitignore                        # Arquivos ignorados pelo git
├── bot_trading.py                    # ⭐ CORE - Bot principal (789 linhas)
├── main.py                           # ⭐ CORE - Idêntico ao bot_trading.py (789 linhas)
├── comprar_manual.py                 # Script auxiliar para compras manuais
├── consultar_banco.py                # Script para consultar banco de dados
├── importar_historico.py             # Import de histórico de ordens
├── importar_historico_simple.py      # Import simplificado
├── validar_correcoes.py              # Validação de correções
├── verificar_aporte.py               # Verificação de aportes
├── requirements.txt                  # Dependências Python (88 linhas)
│
├── config/                           # 📂 Configurações
│   ├── __init__.py
│   ├── settings.py                   # ⭐ Configurações principais (212 linhas)
│   ├── estrategia.json               # ⭐ Estratégia de trading (128 linhas)
│   └── .env.example                  # Template de variáveis de ambiente
│
├── src/                              # 📂 Código-fonte modular
│   ├── __init__.py
│   │
│   ├── comunicacao/                  # 📂 Comunicação com APIs
│   │   ├── __init__.py
│   │   └── api_manager.py            # ⭐ Gerenciador API Binance (360 linhas)
│   │
│   ├── core/                         # 📂 Lógica de negócio
│   │   ├── __init__.py
│   │   ├── gestao_capital.py         # ⭐ Gestão de capital e reserva (225 linhas)
│   │   ├── analise_tecnica.py        # ⭐ Análise técnica e SMA (257 linhas)
│   │   ├── gerenciador_aportes.py    # ⭐ Aportes BRL→USDT (321 linhas)
│   │   └── gerenciador_bnb.py        # ⭐ Gestão de BNB para taxas (199 linhas)
│   │
│   ├── persistencia/                 # 📂 Banco de dados
│   │   ├── __init__.py
│   │   └── database.py               # ⭐ Gerenciador SQLite (622 linhas)
│   │
│   ├── utils/                        # 📂 Utilitários
│   │   ├── __init__.py
│   │   └── logger.py                 # ⭐ Sistema de logs (310 linhas)
│   │
│   └── modelos/                      # 📂 Modelos de dados (futuro)
│       └── __init__.py
│
├── dados/                            # 📂 Banco de dados SQLite
│   └── trading_bot.db                # Banco de dados de ordens
│
├── logs/                             # 📂 Logs do sistema
│   ├── bot.log                       # Log principal
│   ├── bot_errors.log                # Erros
│   └── bot_background.log            # Log do processo background
│
├── scripts/                          # 📂 Scripts auxiliares
│   ├── start_bot.sh                  # Iniciar bot
│   ├── stop_bot.sh                   # Parar bot
│   ├── restart_bot.sh                # Reiniciar bot
│   ├── status_bot.sh                 # Status do bot
│   ├── start_background.sh           # Iniciar em background
│   └── watchdog.sh                   # Monitor de saúde
│
├── tests/                            # 📂 Testes
│   ├── __init__.py
│   ├── test_config.py                # Testa configurações
│   ├── test_logger.py                # Testa logger
│   ├── test_aportes_brl.py           # Testa aportes
│   ├── test_ordem_debug.py           # Debug de ordens
│   └── test_sma.py                   # Testa cálculo SMA
│
└── docs/                             # 📂 Documentação (arquivos .md)
    ├── DIA1_CONCLUIDO.md             # Resumo do dia 1
    ├── PRODUCAO_PRONTO.md            # Preparação para produção
    ├── SEGURANCA_VERIFICADA.md       # Checklist de segurança
    ├── TERMUX_SETUP.md               # Setup Android
    ├── CORRECAO_RESERVA_APLICADA.md  # Correção crítica de reserva
    ├── RELATORIO_VENDAS_12OUT.md     # Relatório de vendas
    ├── BANCO_DE_DADOS_IMPLEMENTADO.md
    ├── LIMITE_COMPRAS_IMPLEMENTADO.md
    ├── APORTES_BRL.md
    └── [outros 15+ arquivos .md]
```

**Estatísticas:**
- **Total de arquivos Python:** 28 arquivos
- **Total de linhas de código:** ~3.997 linhas (apenas arquivos principais)
- **Módulos implementados:** 10 módulos principais
- **Scripts shell:** 6 scripts
- **Documentação:** 25+ arquivos markdown

---

## 🧩 2. MÓDULOS IMPLEMENTADOS

### 2.1. **bot_trading.py** (789 linhas)
**Localização:** `/home/cardoso/Documentos/BOT/bot_trading.py`

**Classes:**
- `BotTrading`: Classe principal do bot

**Principais métodos:**
- `__init__()`: Inicialização do bot
- `recuperar_estado()`: Recupera estado do banco de dados
- `executar()`: Loop principal do bot
- `processar_preco()`: Processa cada tick de preço
- `verificar_degraus_compra()`: Verifica ativação de degraus
- `executar_compra()`: Executa compra com validação rigorosa
- `verificar_metas_venda()`: Verifica metas de lucro
- `executar_venda()`: Executa venda
- `pode_comprar_no_degrau()`: Valida cooldown e limite de compras
- `atualizar_preco_medio()`: Recalcula preço médio

**Responsabilidades:**
1. ✅ Loop principal de trading
2. ✅ Streaming de preços via WebSocket Binance
3. ✅ Detecção de quedas baseada em SMA 28 dias
4. ✅ Sistema de degraus progressivos (7 níveis)
5. ✅ Sistema adaptativo de vendas (3-6% lucro)
6. ✅ Metas fixas de venda (6%, 11%, 18%)
7. ✅ Cooldown entre compras (1-24h por degrau)
8. ✅ Limite de 3 compras por degrau em 24h
9. ✅ Validação de saldo com proteção de reserva 8%
10. ✅ Recuperação de estado do banco de dados
11. ✅ Logs detalhados de todas as operações

**Integrações:**
- `config.settings`: Configurações
- `src.comunicacao.api_manager`: API Binance
- `src.core.gestao_capital`: Validação de capital
- `src.core.analise_tecnica`: Cálculo de SMA
- `src.persistencia.database`: Persistência de ordens
- `src.utils.logger`: Sistema de logs

---

### 2.2. **config/settings.py** (212 linhas)
**Localização:** `/home/cardoso/Documentos/BOT/config/settings.py`

**Funções principais:**
- `load_dotenv()`: Carrega variáveis de ambiente do `.env`
- `validar_configuracoes()`: Valida todas as configurações

**Configurações exportadas:**
```python
# API Binance
BINANCE_API_KEY: str
BINANCE_API_SECRET: str
AMBIENTE: str ('TESTNET' | 'PRODUCAO')

# Capital
CAPITAL_INICIAL: Decimal
PERCENTUAL_CAPITAL_ATIVO: int (92%)
PERCENTUAL_RESERVA: int (8%)

# Segurança
LIMITE_GASTO_DIARIO: Decimal
VALOR_MINIMO_APORTE: Decimal
VALOR_MINIMO_ORDEM: Decimal (5.00)

# Trading
PAR_TRADING: str ('ADAUSDT')
PERIODO_SMA_DIAS: int (28)
INTERVALO_VERIFICACAO_SALDO: int (3600)

# Logs
LOG_LEVEL: str ('INFO' | 'DEBUG')
LOG_RETENTION_DAYS: int (30)

# Sistema
REQUEST_TIMEOUT: int (30)
MAX_RETRIES: int (3)
```

**Responsabilidades:**
1. ✅ Carregar variáveis de ambiente
2. ✅ Carregar estratégia do JSON
3. ✅ Validar configurações obrigatórias
4. ✅ Fornecer valores padrão seguros
5. ✅ Exportar configurações para todo o sistema

---

### 2.3. **config/estrategia.json** (128 linhas)
**Localização:** `/home/cardoso/Documentos/BOT/config/estrategia.json`

**Estrutura:**
```json
{
  "versao": "1.0",
  "pares_ativos": ["ADA/USDT"],

  "degraus_compra": [
    {
      "nivel": 1,
      "queda_percentual": 1.5,
      "quantidade_ada": 8,
      "valor_aproximado_usd": 6.50,
      "intervalo_horas": 1.5
    },
    // ... 7 degraus total
  ],

  "metas_venda": [
    {
      "meta": 1,
      "lucro_percentual": 6,
      "percentual_venda": 30
    },
    // ... 3 metas total
  ],

  "limites_seguranca": {
    "limite_gasto_diario": 100.00,
    "percentual_capital_ativo": 92,
    "percentual_reserva": 8,
    "valor_minimo_ordem": 5.00
  }
}
```

**Responsabilidades:**
1. ✅ Definir degraus de compra (7 níveis: 1.5% até 26%)
2. ✅ Definir metas de venda (6%, 11%, 18%)
3. ✅ Definir limites de segurança
4. ✅ Configurar detecção de picos e volatilidade
5. ✅ Centralizar estratégia em formato legível

---

### 2.4. **src/comunicacao/api_manager.py** (360 linhas)
**Localização:** `/home/cardoso/Documentos/BOT/src/comunicacao/api_manager.py`

**Classe:**
- `APIManager`: Gerenciador de comunicação com Binance API

**Principais métodos:**
```python
# Conexão
conectar_stream(simbolo, callback)  # WebSocket streaming
fechar_stream()                      # Fecha conexão

# Ordens
criar_ordem_mercado(simbolo, lado, quantidade)  # Ordem de mercado
obter_ordem(simbolo, order_id)                  # Busca ordem por ID

# Dados de mercado
obter_ticker(simbolo)                # Preço atual
obter_klines(simbolo, intervalo, limite)  # Histórico de candles

# Conta
obter_saldos()                       # Todos os saldos
obter_saldo_especifico(asset)        # Saldo de um ativo

# Utilidades
_assinar_requisicao(params)          # HMAC SHA256
_fazer_requisicao(metodo, endpoint)  # HTTP com retry
```

**Responsabilidades:**
1. ✅ WebSocket streaming de preços em tempo real
2. ✅ Criação de ordens de mercado (BUY/SELL)
3. ✅ Consulta de saldos (USDT, ADA, BRL, BNB)
4. ✅ Busca de dados históricos (klines)
5. ✅ Assinatura HMAC SHA256 de requisições
6. ✅ Retry automático em caso de falha de rede
7. ✅ Tratamento de erros da API Binance
8. ✅ Suporte para TESTNET e PRODUCAO

**URLs utilizadas:**
- **TESTNET:** `testnet.binance.vision`
- **PRODUCAO:** `api.binance.com`
- **WebSocket:** `stream.binance.com:9443`

---

### 2.5. **src/core/gestao_capital.py** (225 linhas) ⭐ NOVO
**Localização:** `/home/cardoso/Documentos/BOT/src/core/gestao_capital.py`

**Classe:**
- `GestaoCapital`: Gestão rigorosa de capital e reserva

**Principais métodos:**
```python
atualizar_saldos(saldo_usdt, valor_posicao_ada)
calcular_capital_total() -> Decimal
calcular_reserva_obrigatoria() -> Decimal
calcular_capital_disponivel() -> Decimal
pode_comprar(valor_operacao) -> (bool, str)
obter_resumo() -> Dict
```

**Fluxo de validação em `pode_comprar()`:**
```python
1. Calcular capital total = USDT + valor_posicao_ADA
2. Calcular reserva obrigatória = capital_total * 8%
3. Calcular capital disponível = saldo_USDT - reserva
4. Verificar: capital_disponivel >= valor_operacao?
5. Simular: saldo_após = saldo_USDT - valor_operacao
6. Verificar: saldo_após >= reserva? AND saldo_após >= $5.00?
7. Retornar: (True, "") ou (False, "motivo detalhado")
```

**Responsabilidades:**
1. ✅ **CRÍTICO:** Proteger reserva de 8% SEMPRE
2. ✅ Garantir mínimo de $5.00 USDT sempre
3. ✅ Validar ANTES e DEPOIS de cada compra
4. ✅ Considerar valor da posição ADA no capital total
5. ✅ Fornecer mensagens detalhadas de bloqueio
6. ✅ Evitar que bot gaste TODO o saldo

**Proteções implementadas:**
- ❌ NUNCA permite saldo < reserva obrigatória
- ❌ NUNCA permite saldo < $5.00
- ❌ NUNCA permite operação que viole reserva
- ✅ SEMPRE mantém 8% de segurança
- ✅ SEMPRE valida saldo após simulação

---

### 2.6. **src/core/analise_tecnica.py** (257 linhas)
**Localização:** `/home/cardoso/Documentos/BOT/src/core/analise_tecnica.py`

**Classe:**
- `AnaliseTecnica`: Cálculos de indicadores técnicos

**Principais métodos:**
```python
obter_klines_cached(simbolo, intervalo, periodo_dias)
calcular_sma(simbolo, intervalo, periodo_dias) -> Decimal
calcular_sma_multiplos_timeframes(simbolo, periodo_dias) -> Dict
calcular_queda_desde_sma(preco_atual, sma) -> Decimal
obter_estatisticas_periodo(simbolo, intervalo, periodo_dias) -> Dict
```

**SMA (Simple Moving Average):**
- **Timeframes:** 1h e 4h
- **Período:** 28 dias (4 semanas)
- **Ponderação:** 40% (1h) + 60% (4h) = SMA média
- **Cache:** 5 minutos para otimização

**Responsabilidades:**
1. ✅ Calcular SMA de 28 dias em múltiplos timeframes
2. ✅ Calcular percentual de queda desde SMA
3. ✅ Cache de klines para evitar chamadas excessivas à API
4. ✅ Estatísticas de período (máximo, mínimo, volatilidade)
5. ✅ Base para detecção de quedas nos degraus

**Exemplo de uso:**
```python
analise = AnaliseTecnica(api_manager)
smas = analise.calcular_sma_multiplos_timeframes('ADAUSDT', 28)
# Retorna: {'1h': 0.831234, '4h': 0.831456, 'media': 0.831367}

queda = analise.calcular_queda_desde_sma(preco_atual=0.650, sma=0.831)
# Retorna: Decimal('21.77')  (queda de 21.77%)
```

---

### 2.7. **src/core/gerenciador_aportes.py** (321 linhas)
**Localização:** `/home/cardoso/Documentos/BOT/src/core/gerenciador_aportes.py`

**Classe:**
- `GerenciadorAportes`: Conversão automática BRL → USDT

**Principais métodos:**
```python
verificar_saldo_brl() -> Decimal
verificar_saldo_usdt() -> Decimal
obter_preco_usdt_brl() -> Decimal
calcular_quantidade_usdt(valor_brl, preco) -> Decimal
converter_brl_para_usdt(valor_brl=None) -> Dict
processar_aporte_automatico() -> Dict
obter_resumo_saldos() -> Dict
```

**Fluxo de conversão:**
```
1. Detectar saldo BRL na conta
2. Verificar se >= R$ 10.00 (mínimo)
3. Obter preço USDT/BRL da Binance
4. Calcular quantidade USDT a receber
5. Arredondar para 0.1 USDT (LOT_SIZE filter)
6. Criar ordem BUY USDT/BRL (comprar USDT com BRL)
7. Registrar aporte no log
8. Aguardar 2 segundos
9. Verificar novo saldo USDT
```

**Responsabilidades:**
1. ✅ Detectar novos depósitos em BRL
2. ✅ Converter automaticamente BRL → USDT
3. ✅ Respeitar limite mínimo de R$ 10.00
4. ✅ Respeitar filtro LOT_SIZE da Binance (0.1 USDT)
5. ✅ Registrar aportes no log
6. ✅ Fornecer resumo consolidado de saldos

---

### 2.8. **src/core/gerenciador_bnb.py** (199 linhas)
**Localização:** `/home/cardoso/Documentos/BOT/src/core/gerenciador_bnb.py`

**Classe:**
- `GerenciadorBNB`: Gestão de BNB para desconto em taxas

**Principais métodos:**
```python
obter_saldo_bnb() -> Decimal
obter_preco_bnb_usdt() -> Decimal
calcular_valor_bnb_em_usdt(quantidade_bnb) -> Decimal
precisa_comprar_bnb() -> bool
comprar_bnb(saldo_usdt) -> Dict
verificar_e_comprar_bnb(saldo_usdt, forcar=False) -> Dict
```

**Benefícios do BNB:**
- **Desconto:** 25% nas taxas da Binance
- **Taxa normal:** 0.10%
- **Taxa com BNB:** 0.075%

**Lógica de compra:**
```
1. Verificar saldo BNB atual
2. Calcular valor em USDT
3. Se valor < $5.00 USDT:
   - Comprar $5.00 de BNB
   - Usar par BNB/USDT
   - Arredondar para 0.001 BNB (precisão Binance)
4. Verificar apenas 1x por dia (intervalo de 24h)
```

**Responsabilidades:**
1. ✅ Manter saldo mínimo de BNB ($5.00 USDT)
2. ✅ Comprar BNB automaticamente quando necessário
3. ✅ Respeitar intervalo de 24h entre verificações
4. ✅ Garantir desconto de 25% nas taxas
5. ✅ Arredondar quantidade para precisão da Binance

---

### 2.9. **src/persistencia/database.py** (622 linhas)
**Localização:** `/home/cardoso/Documentos/BOT/src/persistencia/database.py`

**Classe:**
- `DatabaseManager`: Gerenciador SQLite para persistência

**Tabelas:**
1. **`ordens`**: Histórico de todas as ordens
   - Campos: timestamp, tipo (COMPRA/VENDA), degrau, quantidade, preco, valor_total, lucro_percentual, lucro_usdt, order_id, status

2. **`saldos`**: Histórico de saldos (futuro)
3. **`configuracoes`**: Configurações persistidas (futuro)

**Principais métodos:**
```python
# Ordens
registrar_compra(degrau, quantidade, preco, valor, order_id)
registrar_venda(quantidade, preco, valor, lucro_pct, lucro_usdt, order_id)
obter_todas_ordens() -> List[Dict]
obter_ordens_compra() -> List[Dict]
obter_ordens_venda() -> List[Dict]

# Estatísticas
obter_total_comprado() -> Decimal
obter_total_vendido() -> Decimal
calcular_preco_medio_compra() -> Decimal
obter_ultima_compra_degrau(nivel_degrau) -> Dict
contar_compras_degrau_24h(nivel_degrau) -> int

# Utilidades
executar_query(query, params)
fechar_conexao()
```

**Responsabilidades:**
1. ✅ Persistir todas as ordens (compra e venda)
2. ✅ Recuperar histórico de ordens
3. ✅ Calcular preço médio de compra
4. ✅ Calcular quantidade total comprada/vendida
5. ✅ Consultar última compra por degrau (cooldown)
6. ✅ Contar compras por degrau em 24h (limite)
7. ✅ Fornecer dados para recuperação de estado
8. ✅ Transações ACID garantidas (SQLite)

---

### 2.10. **src/utils/logger.py** (310 linhas)
**Localização:** `/home/cardoso/Documentos/BOT/src/utils/logger.py`

**Classe:**
- `TradingLogger`: Sistema de logs personalizados

**Níveis de log:**
- `DEBUG`: Detalhes técnicos
- `INFO`: Informações gerais
- `WARNING`: Avisos
- `ERROR`: Erros
- `CRITICAL`: Erros críticos

**Métodos especializados:**
```python
compra_executada(degrau, quantidade, preco, valor, queda)
venda_executada(quantidade, preco, valor, lucro_pct, lucro_usdt)
degrau_ativado(nivel, queda)
saldo_atualizado(moeda, valor)
erro_api(mensagem)
aporte_detectado(valor, moeda, usdt_recebido)
sma_calculada(sma_1h, sma_4h, sma_media)
```

**Configuração:**
```python
# Arquivos de log
logs/bot.log           # Log completo (rotação diária)
logs/bot_errors.log    # Apenas erros
logs/bot_background.log # Processo background

# Formato
[NÍVEL] | HH:MM:SS | Mensagem
INFO | 12:34:56 | ✅ Compra executada...
```

**Responsabilidades:**
1. ✅ Logs formatados e legíveis
2. ✅ Rotação de logs diária
3. ✅ Separação de erros em arquivo próprio
4. ✅ Métodos especializados para eventos de trading
5. ✅ Suporte a múltiplos handlers (console + arquivo)
6. ✅ Retenção de logs configurável (30 dias)

---

**Continue na PARTE 2:**
- Código dos arquivos principais
- Fluxo atual do sistema
- Problemas conhecidos
- Dependências
- Configurações

