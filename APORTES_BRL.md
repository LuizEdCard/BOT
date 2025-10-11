# 💰 Sistema de Aportes em BRL

**Status:** ✅ IMPLEMENTADO
**Data:** 2025-10-11
**Versão:** 1.0

---

## 📋 Visão Geral

O bot agora suporta **depósitos em BRL (Real Brasileiro)** com conversão automática para USDT.

### Fluxo Completo

```
1. Você deposita BRL na Binance
   ↓
2. Bot detecta saldo BRL
   ↓
3. Bot converte BRL → USDT automaticamente (par USDT/BRL)
   ↓
4. USDT disponível para trading ADA/USDT
   ↓
5. Bot opera normalmente comprando/vendendo ADA
```

---

## 🔄 Como Funciona

### 1. Detecção de Depósitos

O bot **verifica periodicamente** se há saldo BRL na conta:

```python
# A cada X minutos (configurável)
saldo_brl = gerenciador.verificar_saldo_brl()

if saldo_brl >= valor_minimo_aporte:
    # Aporte detectado!
    converter_para_usdt()
```

### 2. Conversão Automática

Quando detecta BRL, o bot:

1. Obtém cotação atual USDT/BRL (~R$ 5.80)
2. Calcula quanto USDT será recebido
3. Cria ordem BUY no par USDT/BRL
4. **TODO o saldo BRL é convertido**
5. Registra aporte no histórico

**Exemplo:**
```
Depósito: R$ 100,00 BRL
Cotação: R$ 5,80 / USDT
Resultado: 17,24 USDT
```

### 3. Disponibilização para Trading

Após conversão:
- USDT fica disponível na carteira Spot
- Bot pode usar para comprar ADA
- Trading continua normalmente com ADA/USDT

---

## ⚙️ Configuração

### Valor Mínimo de Aporte

Configurado em `config/.env`:

```bash
# Valor mínimo para detectar aporte (USD equivalente)
VALOR_MINIMO_APORTE=10.00
```

Se você depositar menos que isso, o bot **não converterá** automaticamente.

### Intervalo de Verificação

```bash
# Verificar saldo BRL a cada X segundos
INTERVALO_VERIFICACAO_SALDO=3600  # 1 hora
```

---

## 🧪 Como Testar

### 1. Fazer Depósito BRL na Binance

**Opções:**
- PIX (recomendado - instantâneo)
- TED/DOC
- P2P

**Passos:**
1. Acesse Binance → Carteira → Fiat e Spot
2. Depositar → BRL
3. Escolha PIX
4. Faça o depósito
5. Aguarde confirmação (geralmente < 5 min)

### 2. Executar Teste Manual

```bash
# Ativar ambiente
source venv/bin/activate

# Executar teste
python test_aportes_brl.py
```

**O que o teste faz:**
- ✅ Conecta com Binance
- ✅ Verifica saldo BRL
- ✅ Obtém cotação USDT/BRL
- ✅ Converte BRL → USDT (se houver saldo)
- ✅ Exibe resumo de saldos

### 3. Saída Esperada

```
═══════════════════════════════════════════════════════════
  🧪 TESTE DE SISTEMA DE APORTES BRL
═══════════════════════════════════════════════════════════

📋 Verificando configurações...
   Ambiente: PRODUCAO
   API URL: https://api.binance.com
   Capital inicial: $180.0
   Valor mínimo aporte: $10.0

🔌 Inicializando API Manager...
✅ INICIALIZAÇÃO | API Manager | ✅ OK

💰 Inicializando Gerenciador de Aportes...
✅ INICIALIZAÇÃO | Gerenciador de Aportes | ✅ OK

💼 Verificando saldos atuais...
💰 Saldo BRL detectado: R$ 100.00
   ✅ Saldo BRL detectado: R$ 100.00
   USDT: $50.00
   ADA: 0.0000
   Total (USD equiv): $67.24

📊 Verificando cotação USDT/BRL...
📊 Cotação USDT/BRL: R$ 5.8000
   ✅ USDT/BRL: R$ 5.8000

🔄 Processando aporte automático...
💰 Aporte detectado: R$ 100.00
🔄 Iniciando conversão automática BRL → USDT...
🔄 Conversão: R$ 100.00 → $ 17.24 USDT
📤 Criando ordem: BUY 17.24 USDTBRL
✅ Ordem executada: 12345678
💵 APORTE DETECTADO | R$ 100.00 BRL → $17.24 USDT
   ✅ ✅ Convertido: R$ 100.00 → $ 17.24 USDT
   💵 Valor BRL: R$ 100.00
   💰 USDT recebido: $17.24
   📈 Cotação: R$ 5.8000
   📝 Order ID: 12345678

💼 Verificando saldo final USDT...
💵 Saldo USDT detectado: $ 67.24
   ✅ Saldo USDT atualizado: $67.24

════════════════════════════════════════════════════════════
📊 RESUMO FINAL
════════════════════════════════════════════════════════════
💰 BRL:  R$ 0.00
💵 USDT: $67.24
🪙 ADA:  0.0000
💼 Total (USD): $67.24
════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════
  ✅ TESTE CONCLUÍDO
═══════════════════════════════════════════════════════════
```

---

## 📊 Pares Utilizados

### USDT/BRL (Binance)

- **Ticker:** `USDTBRL`
- **Base:** USDT
- **Quote:** BRL
- **Tipo de ordem:** MARKET

**Como funciona:**
- `BUY USDTBRL` = Comprar USDT com BRL ✅
- `SELL USDTBRL` = Vender USDT por BRL

**Usamos:** `BUY` para converter BRL → USDT

### Não Existe: ADA/BRL

⚠️ Binance **NÃO** tem par direto ADA/BRL.

Por isso o fluxo é:
```
BRL → USDT (via USDTBRL)
USDT → ADA (via ADAUSDT)
```

---

## 🔍 Monitoramento

### Logs

O bot registra todas as operações:

```bash
# Ver logs de aportes
tail -f logs/sistema_$(date +%Y-%m-%d).log | grep "APORTE"

# Ver conversões BRL → USDT
tail -f logs/sistema_$(date +%Y-%m-%d).log | grep "Conversão"
```

### Histórico

Todas as conversões ficam registradas em:
```
dados/historico_2025-10.txt
```

Formato:
```
[2025-10-11 14:30:00] APORTE | R$ 100.00 BRL → $17.24 USDT | Cotação: R$ 5.80
```

---

## 🛠️ Arquivos Criados

### Código

1. **`src/core/gerenciador_aportes.py`**
   - Classe `GerenciadorAportes`
   - Métodos:
     - `verificar_saldo_brl()`
     - `verificar_saldo_usdt()`
     - `obter_preco_usdt_brl()`
     - `calcular_quantidade_usdt()`
     - `converter_brl_para_usdt()`
     - `processar_aporte_automatico()`
     - `obter_resumo_saldos()`

2. **`src/comunicacao/api_manager.py`**
   - Classe `APIManager`
   - Comunicação com Binance API
   - Autenticação HMAC SHA256
   - Métodos de ordem e saldos

### Testes

3. **`test_aportes_brl.py`**
   - Script de teste standalone
   - Simula depósito e conversão
   - Verifica saldos e cotações

### Documentação

4. **`APORTES_BRL.md`** (este arquivo)

---

## ⚠️ Importante

### Taxas Binance

**USDT/BRL:**
- Taxa Maker: 0.10%
- Taxa Taker: 0.10%
- **Ordem MARKET usa taxa Taker**

**Exemplo:**
```
Deposita: R$ 100,00
Cotação: R$ 5,80
Sem taxa: 17,24 USDT
Taxa 0.1%: -0,017 USDT
Recebe: ~17,22 USDT
```

### Limites Mínimos

**Binance USDT/BRL:**
- Ordem mínima: R$ 10,00
- Quantidade mínima USDT: 1 USDT

Se depositar menos de R$ 10, a conversão **falhará**.

### Liquidez

USDT/BRL geralmente tem boa liquidez, mas:
- Verifique spread antes de converter
- Ordem MARKET pode ter slippage
- Cotação varia ao longo do dia

---

## 🚀 Integração com Bot Principal

### Bot deve chamar periodicamente:

```python
# main.py ou bot_principal.py

from src.core.gerenciador_aportes import GerenciadorAportes

# Inicializar
gerenciador_aportes = GerenciadorAportes(api, settings)

# Loop principal
while True:
    # ... lógica de trading ...

    # A cada X minutos
    if tempo_desde_ultima_verificacao > intervalo:
        resultado = gerenciador_aportes.processar_aporte_automatico()

        if resultado['sucesso']:
            # Aporte convertido!
            # Atualizar capital ativo
            capital_ativo += resultado['quantidade_usdt']
            logger.capital_atualizado(...)

    time.sleep(60)
```

---

## 📞 Comandos Úteis

```bash
# Verificar saldo BRL manualmente (via Binance CLI)
# (requer binance-cli instalado)
binance account

# Verificar cotação USDT/BRL
curl "https://api.binance.com/api/v3/ticker/price?symbol=USDTBRL"

# Testar conversão (DRY RUN)
python test_aportes_brl.py

# Ver logs em tempo real
tail -f logs/sistema_$(date +%Y-%m-%d).log
```

---

## ✅ Checklist de Uso

Antes de depositar BRL:

- [x] ✅ AMBIENTE=PRODUCAO configurado
- [x] ✅ API keys com permissão Spot Trading
- [x] ✅ Bot rodando e conectado
- [x] ✅ Verificação de aportes ativa
- [x] ✅ Valor mínimo configurado (VALOR_MINIMO_APORTE)
- [ ] 🔄 Fazer depósito BRL via PIX
- [ ] 🔄 Aguardar detecção automática
- [ ] 🔄 Verificar conversão nos logs
- [ ] 🔄 Confirmar USDT recebido

---

## 🎯 Próximos Passos

1. ✅ Sistema de aportes implementado
2. ✅ Teste manual disponível
3. 🔄 **VOCÊ:** Fazer primeiro depósito BRL
4. 🔄 **VOCÊ:** Executar `python test_aportes_brl.py`
5. 🔄 Verificar conversão bem-sucedida
6. 🔄 Confirmar USDT disponível
7. 🔄 Bot iniciar trading ADA/USDT

---

## 💡 Dicas

### Depósito via PIX (Recomendado)

- ✅ **Rápido:** Geralmente < 5 minutos
- ✅ **Sem taxa:** Binance não cobra taxa PIX
- ✅ **Fácil:** Escaneia QR Code e pronto
- ✅ **24/7:** Funciona finais de semana e feriados

### Valores Recomendados

- **Primeiro teste:** R$ 50 - R$ 100
- **Aportes mensais:** R$ 100 - R$ 500
- **Evite:** Depósitos < R$ 20 (taxa fixa pode não compensar)

### Timing

- **Melhor horário:** 9h-17h (maior liquidez)
- **Evitar:** Madrugada (spread maior)
- **Finais de semana:** OK, mas pode ter menos liquidez

---

## 🆘 Troubleshooting

### Problema: Bot não detecta BRL

**Soluções:**
1. Verificar se depósito foi confirmado na Binance
2. Executar teste manual: `python test_aportes_brl.py`
3. Ver logs: `tail -f logs/sistema_*.log`
4. Verificar VALOR_MINIMO_APORTE

### Problema: Conversão falha

**Causas comuns:**
- Valor abaixo do mínimo (< R$ 10)
- API sem permissão Spot Trading
- Par USDTBRL indisponível
- Problemas de rede

**Debug:**
```bash
# Testar conexão API
python test_config.py

# Testar ordem manualmente
python test_aportes_brl.py
```

### Problema: Taxa muito alta

**Explicação:**
- Ordem MARKET paga taxa Taker (0.1%)
- Spread pode adicionar custo
- Depósitos pequenos sofrem mais com taxas proporcionalmente

**Solução:**
- Fazer depósitos maiores (R$ 100+)
- Considerar ordem LIMIT (requer implementação)

---

## 📚 Referências

- [Binance API Docs](https://binance-docs.github.io/apidocs/spot/en/)
- [USDT/BRL no Binance](https://www.binance.com/en/trade/USDT_BRL)
- [Taxas Binance Brasil](https://www.binance.com/en/fee/schedule)

---

**Última atualização:** 2025-10-11
**Versão:** 1.0
**Status:** ✅ PRONTO PARA USO
