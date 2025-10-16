# 🎓 Exemplos Práticos: Nova Estratégia de Compra

Este documento apresenta exemplos práticos de como o bot se comportará com a nova estratégia de compra implementada.

---

## 📋 Configuração Atual

### Cooldown Global
```json
"cooldown_global_apos_compra_minutos": 30
```

### Degraus e Intervalos
| Degrau | Queda % | Quantidade ADA | Intervalo |
|--------|---------|----------------|-----------|
| 1 | 1.5% | 8 ADA | 1.5h |
| 2 | 3.0% | 13 ADA | 2.0h |
| 3 | 5.5% | 20 ADA | 3.0h |
| 4 | 8.5% | 28 ADA | 4.0h |
| 5 | 13.0% | 38 ADA | 8.0h |
| 6 | 19.0% | 50 ADA | 12.0h |
| 7 | 26.0% | 55 ADA | 24.0h |

---

## 🥶 Exemplo 1: Largada a Frio

### Cenário
O mercado caiu 13% antes de você iniciar o bot. Você liga o bot pela primeira vez.

### Timeline

**🕐 10:00 - Bot iniciado**
```
SMA de referência: $0.8500
Preço atual: $0.7395 (queda de 13% desde SMA)

Degraus ativados: 1, 2, 3, 4, 5
Degrau mais profundo: 5 (13% de queda)
```

**Log do bot:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🥶 LARGADA A FRIO DETECTADA!
   Queda desde SMA: 13.00%
   Degrau mais profundo ativado: Nível 5
   Executando compra controlada no degrau 5...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Compra de 'Largada a Frio' executada!
   Quantidade: 38 ADA
   Preço: $0.7395
   Total: $28.10 USDT
   🕒 Cooldown global ativado
```

**Estado após compra:**
- ✅ `primeira_execucao = False`
- ✅ `timestamp_ultima_compra_global = 10:00`
- ✅ Cooldown global de 30 minutos ativo até 10:30
- ✅ Degrau 5 não poderá comprar novamente por 8 horas (até 18:00)

---

**🕐 10:15 - Preço continua caindo (14% de queda)**
```
Degrau 5 novamente ativado, mas:
- ❌ Cooldown global bloqueando (faltam 15 min)
- ❌ Cooldown do degrau 5 bloqueando (faltam 7h45m)

Resultado: Compra NÃO executada
```

---

**🕐 10:35 - Cooldown global expirou**
```
Cooldown global: ✅ OK (passou 35 min)
Cooldown degrau 5: ❌ BLOQUEADO (faltam 7h25m)

Resultado: Compra no degrau 5 NÃO executada
```

---

**🕐 18:10 - Ambos cooldowns expiraram**
```
Cooldown global: ✅ OK (passou 8h10m)
Cooldown degrau 5: ✅ OK (passou 8h10m)
Preço: $0.7250 (queda de 14.7%)

Resultado: ✅ Nova compra executada!
   Quantidade: 38 ADA
   Preço: $0.7250
   Total: $27.55 USDT
```

---

## 🔄 Exemplo 2: Operação Normal (Múltiplos Degraus)

### Cenário
Bot operando há vários dias. Preço começa em $0.8500 (na SMA) e cai gradualmente.

### Timeline

**🕐 08:00 - Preço: $0.8372 (queda de 1.5%)**
```
Degrau 1 ativado (1.5%)
Cooldown global: ✅ OK (última compra ontem)
Cooldown degrau 1: ✅ OK (última compra há 24h)

Resultado: ✅ Compra executada!
   Degrau 1: 8 ADA @ $0.8372 = $6.70 USDT
   🕒 Cooldown global ativado (30 min)
```

**Estado:**
- `timestamp_ultima_compra_global = 08:00`

---

**🕐 08:15 - Preço: $0.8245 (queda de 3.0%)**
```
Degrau 2 ativado (3.0%)
Cooldown global: ❌ BLOQUEADO (faltam 15 min)
Cooldown degrau 2: ✅ OK

Resultado: ❌ Compra bloqueada pelo cooldown global
```

---

**🕐 08:35 - Preço: $0.8245 (queda de 3.0%)**
```
Degrau 2 ativado (3.0%)
Cooldown global: ✅ OK (passou 35 min)
Cooldown degrau 2: ✅ OK

Resultado: ✅ Compra executada!
   Degrau 2: 13 ADA @ $0.8245 = $10.72 USDT
   🕒 Cooldown global ativado (30 min)
```

**Estado:**
- `timestamp_ultima_compra_global = 08:35`

---

**🕐 09:10 - Preço: $0.8032 (queda de 5.5%)**
```
Degrau 3 ativado (5.5%)
Cooldown global: ✅ OK (passou 35 min)
Cooldown degrau 3: ✅ OK

Resultado: ✅ Compra executada!
   Degrau 3: 20 ADA @ $0.8032 = $16.06 USDT
   🕒 Cooldown global ativado (30 min)
```

---

**🕐 10:00 - Preço: $0.7778 (queda de 8.5%)**
```
Degrau 4 ativado (8.5%)
Cooldown global: ✅ OK (passou 50 min)
Cooldown degrau 4: ✅ OK

Resultado: ✅ Compra executada!
   Degrau 4: 28 ADA @ $0.7778 = $21.78 USDT
   🕒 Cooldown global ativado (30 min)
```

---

**🕐 10:15 - Preço: $0.7735 (queda de 9.0%)**
```
Degrau 4 AINDA ativado (9.0% > 8.5%)
Cooldown global: ❌ BLOQUEADO (faltam 15 min)
Cooldown degrau 4: ❌ BLOQUEADO (última compra há 15 min, intervalo = 4h)

Resultado: ❌ Compra bloqueada
```

---

**🕐 14:10 - Preço recuperou: $0.8200 (queda de 3.5%)**
```
Degrau 2 ativado (3.5% > 3.0%)
Cooldown global: ✅ OK (passou 4h10m)
Cooldown degrau 2: ✅ OK (passou 5h35m, intervalo = 2h)

Resultado: ✅ Compra executada!
   Degrau 2: 13 ADA @ $0.8200 = $10.66 USDT
```

---

## 🎯 Exemplo 3: Sistema Comparativo (Antes vs Depois)

### Cenário
Preço caiu 5.5% (degrau 3 ativo). Bot precisa fazer compras ao longo do dia.

### ANTES (Sistema Antigo: 3 compras/24h)

**🕐 08:00 - Compra #1**
```
✅ Compra executada (1/3)
Próxima compra: aguardar 1h
```

**🕐 09:05 - Compra #2**
```
✅ Compra executada (2/3)
Próxima compra: aguardar 1h
```

**🕐 10:10 - Compra #3**
```
✅ Compra executada (3/3)
⚠️ LIMITE ATINGIDO!
❌ Degrau 3 BLOQUEADO por 24 horas
Próxima compra possível: amanhã 08:00
```

**🕐 11:00 - Preço continua em queda**
```
❌ Degrau 3 bloqueado (ainda faltam 21h para desbloquear)
Bot PARALISADO no degrau 3
```

**Resultado:**
- ❌ Bot não pode aproveitar quedas adicionais no degrau 3
- ❌ Trava rígida de 24h

---

### DEPOIS (Sistema Novo: Cooldown Duplo)

**🕐 08:00 - Compra #1**
```
✅ Compra executada
🕒 Cooldown global: 30 min
🕒 Cooldown degrau 3: 3 horas
Próxima compra no degrau 3: 11:00
```

**🕐 11:05 - Compra #2**
```
✅ Compra executada
🕒 Cooldown global: 30 min
🕒 Cooldown degrau 3: 3 horas
Próxima compra no degrau 3: 14:05
```

**🕐 14:10 - Compra #3**
```
✅ Compra executada
🕒 Cooldown global: 30 min
🕒 Cooldown degrau 3: 3 horas
Próxima compra no degrau 3: 17:10
```

**🕐 17:15 - Compra #4**
```
✅ Compra executada
🕒 Cooldown global: 30 min
🕒 Cooldown degrau 3: 3 horas
Próxima compra no degrau 3: 20:15
```

**🕐 20:20 - Compra #5**
```
✅ Compra executada
Continua operando normalmente...
```

**Resultado:**
- ✅ Bot consegue fazer 5 compras ao longo do dia
- ✅ Sistema flexível baseado em tempo
- ✅ Sem paralisia por bloqueio de 24h

---

## 💡 Exemplo 4: Degraus Profundos (Crash de Mercado)

### Cenário
Crash severo: preço cai de $0.8500 para $0.6290 em 2 horas (queda de 26%)

### Timeline

**🕐 14:00 - Início do crash: $0.8500**
```
Tudo normal, sem degraus ativados
```

---

**🕐 14:30 - Queda rápida: $0.8075 (5% de queda)**
```
Degrau 3 ativado (5.5%)
✅ Compra: 20 ADA @ $0.8075 = $16.15 USDT
🕒 Cooldown global: 30 min (até 15:00)
🕒 Cooldown degrau 3: 3h (até 17:30)
```

---

**🕐 15:05 - Continua caindo: $0.7778 (8.5% de queda)**
```
Degrau 4 ativado (8.5%)
Cooldown global: ✅ OK (passou 35 min)
Cooldown degrau 4: ✅ OK (nunca comprou neste degrau)

✅ Compra: 28 ADA @ $0.7778 = $21.78 USDT
🕒 Cooldown global: 30 min (até 15:35)
🕒 Cooldown degrau 4: 4h (até 19:05)
```

---

**🕐 15:40 - Crash intensifica: $0.7395 (13% de queda)**
```
Degrau 5 ativado (13%)
Cooldown global: ✅ OK (passou 35 min)
Cooldown degrau 5: ✅ OK (nunca comprou neste degrau)

✅ Compra: 38 ADA @ $0.7395 = $28.10 USDT
🕒 Cooldown global: 30 min (até 16:10)
🕒 Cooldown degrau 5: 8h (até 23:40)
```

---

**🕐 16:15 - Crash severo: $0.6290 (26% de queda)**
```
Degrau 7 ativado (26%)
Cooldown global: ✅ OK (passou 35 min)
Cooldown degrau 7: ✅ OK (nunca comprou neste degrau)

✅ Compra: 55 ADA @ $0.6290 = $34.60 USDT
🕒 Cooldown global: 30 min (até 16:45)
🕒 Cooldown degrau 7: 24h (até amanhã 16:15)
```

---

**Resumo:**
- ✅ 4 compras executadas em 1h45min
- ✅ Total comprado: 141 ADA por $100.63 USDT
- ✅ Preço médio: $0.7137 por ADA
- ✅ Respeitou cooldowns entre compras (30 min mínimo)

---

## 🔍 Logs Esperados

### Largada a Frio
```
07:38:45 | INFO | 🔄 Sincronizando saldo com Binance...
07:38:45 | INFO | ✅ Saldo local sincronizado com Binance
07:38:45 | INFO | 📋 Nenhuma compra anterior encontrada - primeira execução

07:38:50 | INFO | ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
07:38:50 | INFO | 🥶 LARGADA A FRIO DETECTADA!
07:38:50 | INFO |    Queda desde SMA: 13.00%
07:38:50 | INFO |    Degrau mais profundo ativado: Nível 5
07:38:50 | INFO |    Executando compra controlada no degrau 5...
07:38:50 | INFO | ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
07:38:51 | INFO | 🟢 COMPRA | ADA/USDT | 38.0 ADA @ $0.7395 | Degrau 5 | Queda: 13.00%
07:38:51 | INFO | ✅ Compra de 'Largada a Frio' executada!
07:38:51 | INFO |    🕒 Cooldown global ativado
```

### Cooldown Global Bloqueando
```
08:15:30 | DEBUG | 🕒 Cooldown global ativo (faltam 15 min)
```

### Cooldown Degrau Bloqueando
```
08:45:22 | DEBUG | 🕒 Degrau 3 em cooldown (faltam 1.5h)
```

### Compra Normal
```
11:05:45 | INFO | 🎯 Degrau 3 ativado! Queda: 5.50%
11:05:46 | INFO | 🟢 COMPRA | ADA/USDT | 20.0 ADA @ $0.8032 | Degrau 3 | Queda: 5.50%
11:05:46 | DEBUG | 🕒 Cooldown global ativado: 30 minutos
11:05:46 | INFO | ✅ Compra executada com sucesso!
```

---

## 📊 Estatísticas Comparativas

### Sistema Antigo (3 compras/24h por degrau)

**Dia típico de volatilidade:**
- Compras possíveis: 3 compras por degrau
- Bloqueio: 24 horas após 3 compras
- Total máximo: 21 compras (3 x 7 degraus)
- **Problema:** Paralisia após 3 compras em um degrau

---

### Sistema Novo (Cooldown Duplo)

**Dia típico de volatilidade:**
- Compras possíveis: Ilimitadas (respeitando cooldowns)
- Bloqueio: 30 min global + intervalo do degrau
- Total máximo: Depende do intervalo de cada degrau
- **Vantagem:** Flexibilidade para aproveitar quedas prolongadas

**Exemplo - Degrau 3 (intervalo de 3h):**
- 1ª compra: 08:00
- 2ª compra: 11:00 (após 3h)
- 3ª compra: 14:00 (após 3h)
- 4ª compra: 17:00 (após 3h)
- 5ª compra: 20:00 (após 3h)
- **Total:** 5 compras em 12h (vs 3 compras no sistema antigo)

---

## ✅ Conclusão

A nova estratégia oferece:

1. **🥶 Proteção contra Largada a Frio:** Evita gastar todo capital de uma vez
2. **🕒 Cooldown Inteligente:** 30 min global + intervalo específico por degrau
3. **🔓 Menos Paralisia:** Sem bloqueio rígido de 24h
4. **📈 Mais Flexibilidade:** Sistema baseado em tempo ao invés de contador
5. **💰 Melhor DCA:** Permite mais compras em quedas prolongadas

O sistema é mais dinâmico, inteligente e adaptável às condições reais de mercado!
