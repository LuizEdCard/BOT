# 🔄 COMANDOS PARA FAZER MERGE

## ✅ PRÉ-REQUISITOS

- [x] Bot testado na branch desenvolvimento
- [x] Correção 1 (Reserva) validada
- [x] Nenhum erro crítico detectado
- [x] Funcionamento geral confirmado

---

## 📝 PASSO A PASSO PARA MERGE

### **1. Verificar status atual**
```bash
git status
git branch --show-current
```

Deve mostrar: `desenvolvimento`

---

### **2. Parar o bot**
```bash
./stop_bot.sh
```

---

### **3. Voltar para a branch master**
```bash
git checkout master
```

---

### **4. Fazer merge das correções**
```bash
git merge desenvolvimento
```

**Saída esperada:**
```
Updating a31292e..843571f
Fast-forward
 CORRECOES_IMPLEMENTADAS.md   | 448 +++++++++++++++
 bot_trading.py                |  12 +-
 src/core/gerenciador_bnb.py   |  13 +-
 ...
```

---

### **5. Verificar o merge**
```bash
git log --oneline -5
```

**Deve mostrar:**
```
843571f - 📝 Documentação completa das correções implementadas
e1554eb - 🔧 Correções críticas: Reserva de capital e precisão BNB
a31292e - 🎉 Commit inicial - Sistema de trading bot funcional
```

---

### **6. Confirmar que está na master**
```bash
git branch --show-current
```

Deve mostrar: `master`

---

### **7. Reiniciar bot com código atualizado**
```bash
./start_background.sh
```

---

### **8. Verificar que está funcionando**
```bash
./status_bot.sh
```

---

### **9. Monitorar logs para confirmar**
```bash
tail -20 logs/bot_background.log
```

**Deve ver:**
- ✅ Bot iniciado
- ✅ Mensagens de reserva de capital
- ✅ Sem erros críticos

---

## 🆘 SE ALGO DER ERRADO

### **Cenário 1: Merge deu conflito**

```bash
# Ver arquivos com conflito
git status

# Opção A: Abortar merge
git merge --abort
git checkout desenvolvimento

# Opção B: Resolver conflitos manualmente
# (editar arquivos, depois)
git add .
git commit
```

### **Cenário 2: Bot não inicia após merge**

```bash
# Parar bot
./stop_bot.sh

# Voltar para última versão funcionando
git reset --hard a31292e  # Commit inicial

# Reiniciar
./start_background.sh

# Investigar problema
tail -50 logs/bot_errors.log
```

### **Cenário 3: Bot inicia mas dá erros**

```bash
# Parar bot imediatamente
./stop_bot.sh

# Desfazer merge (mantém arquivos)
git reset --soft HEAD~2

# Ou desfazer completamente
git reset --hard a31292e

# Voltar para desenvolvimento para investigar
git checkout desenvolvimento
```

---

## 📊 ESTRUTURA FINAL APÓS MERGE

```
master (com todas as correções)
    │
    ├─── a31292e - Commit inicial
    ├─── e1554eb - Correções implementadas
    └─── 843571f - Documentação
         │
         └─── desenvolvimento (igual à master após merge)
```

---

## ✅ CHECKLIST PÓS-MERGE

Após fazer merge, verificar:

- [ ] Bot iniciou sem erros
- [ ] Logs mostram reserva de capital funcionando
- [ ] Conexão com Binance OK
- [ ] SMA calculada corretamente
- [ ] Nenhum erro crítico nos logs
- [ ] Status do bot mostra "RODANDO"

**Se todos os itens OK:** ✅ Merge bem-sucedido!

---

## 🎯 COMANDOS RÁPIDOS

### **Merge completo (copiar/colar tudo):**
```bash
./stop_bot.sh && \
git checkout master && \
git merge desenvolvimento && \
git log --oneline -3 && \
./start_background.sh && \
sleep 5 && \
./status_bot.sh
```

### **Rollback rápido (se necessário):**
```bash
./stop_bot.sh && \
git reset --hard a31292e && \
./start_background.sh
```

---

**Pronto para executar!** 🚀
