# 📚 SISTEMA DE VERSIONAMENTO GIT - GUIA COMPLETO

Data: 11 de outubro de 2025

---

## 🎯 O QUE É VERSIONAMENTO?

Versionamento é como ter um **"histórico de salvamentos"** do seu código, onde você pode:

- ✅ Voltar para versões anteriores se algo quebrar
- ✅ Testar mudanças sem afetar o código que funciona
- ✅ Ver o que foi alterado, quando e por quê
- ✅ Trabalhar em várias funcionalidades ao mesmo tempo

**Analogia:** É como salvar versões de um documento:
- `trabalho_v1.doc`
- `trabalho_v2.doc`
- `trabalho_final.doc`
- `trabalho_final_revisado.doc`

Mas o Git faz isso de forma **muito mais inteligente**!

---

## 🌳 O QUE SÃO BRANCHES (RAMOS)?

Uma **branch** é uma **linha separada de desenvolvimento**.

### **Visualização:**

```
main/master (produção - código que funciona)
    │
    ├─── commit 1
    │
    ├─── commit 2
    │
    └─── commit 3
         │
         └─── desenvolvimento (testes - pode quebrar)
              │
              ├─── testar correção BNB
              │
              └─── testar reserva capital
```

### **Por que usar branches?**

- 🟢 **main/master**: Código estável, em produção, funcionando
- 🟡 **desenvolvimento**: Código experimental, pode ter bugs
- 🔵 **feature/nova-funcao**: Nova funcionalidade sendo desenvolvida

**Vantagem:** Se o código na branch de desenvolvimento quebrar, a main continua funcionando!

---

## 🔄 WORKFLOW SEGURO (Como vamos usar)

### **Passo a passo:**

1. **Criar branch de desenvolvimento**
   ```bash
   git checkout -b desenvolvimento
   ```

2. **Fazer alterações no código**
   - Editar arquivos
   - Testar mudanças
   - Corrigir bugs

3. **Salvar mudanças (commit)**
   ```bash
   git add .
   git commit -m "Descrição do que foi feito"
   ```

4. **Se funcionar:** Integrar na main
   ```bash
   git checkout main
   git merge desenvolvimento
   ```

5. **Se quebrar:** Simplesmente voltar para a main
   ```bash
   git checkout main
   # Código original intacto!
   ```

---

## 🛡️ POR QUE ISSO É SEGURO?

### **Cenário 1: Mudança dá certo ✅**
```
main (funciona) → desenvolvimento (testar correção) → desenvolvimento (funciona!) → main (atualizada)
```

### **Cenário 2: Mudança quebra tudo ❌**
```
main (funciona) → desenvolvimento (testar correção) → desenvolvimento (quebrou!)
                                                                              ↓
                                            main (AINDA FUNCIONA - não foi afetada!)
```

**Segurança:** A main NUNCA é afetada até você ter certeza que está funcionando!

---

## 📋 COMANDOS PRINCIPAIS

### **Status e Informações**
```bash
# Ver estado atual
git status

# Ver histórico de commits
git log --oneline

# Ver qual branch está ativa
git branch
```

### **Criar e Trocar Branches**
```bash
# Criar nova branch e trocar para ela
git checkout -b desenvolvimento

# Trocar para branch existente
git checkout main
git checkout desenvolvimento

# Listar todas as branches
git branch
```

### **Salvar Mudanças (Commits)**
```bash
# Adicionar arquivos modificados
git add .
# ou adicionar arquivo específico
git add bot_trading.py

# Criar commit com mensagem
git commit -m "Correção da reserva de capital"

# Ver o que foi mudado
git diff
```

### **Integrar Mudanças (Merge)**
```bash
# Voltar para a main
git checkout main

# Trazer mudanças da branch desenvolvimento
git merge desenvolvimento

# Ver se houve conflitos
git status
```

### **Desfazer Mudanças (Emergência)**
```bash
# Descartar mudanças não commitadas
git checkout -- arquivo.py

# Voltar para commit anterior (CUIDADO!)
git reset --hard HEAD~1

# Ver diferenças entre branches
git diff main desenvolvimento
```

---

## 🎯 NOSSO PLANO ATUAL

### **Estado Atual:**
- ✅ Git inicializado
- ⏳ Nenhum commit ainda (repositório vazio)
- 📁 Muitos arquivos prontos para primeiro commit

### **Próximos Passos:**

#### **1. Fazer commit inicial (salvar estado atual)**
```bash
git add .
git commit -m "Commit inicial - Sistema funcionando com banco de dados"
```
**Isso salva o código ATUAL que está funcionando!**

#### **2. Criar branch de desenvolvimento**
```bash
git checkout -b desenvolvimento
```

#### **3. Fazer correções na branch desenvolvimento:**
- Implementar reserva de capital (bot_trading.py:214)
- Corrigir precisão decimal do BNB (gerenciador_bnb.py)

#### **4. Testar as correções:**
```bash
# Rodar bot na branch desenvolvimento
./start_bot.sh
# Monitorar por 30 minutos
# Verificar se está funcionando
```

#### **5a. Se funcionar:**
```bash
git checkout main
git merge desenvolvimento
# Agora a main tem as correções funcionando!
```

#### **5b. Se quebrar:**
```bash
git checkout main
# Volta para código original, SEM as mudanças que quebraram!
```

---

## 📊 ESTRUTURA DO PROJETO

```
BOT/
├── main (branch principal - código estável)
│   ├── bot_trading.py ✅ funcionando
│   ├── src/
│   │   ├── persistencia/database.py ✅
│   │   ├── comunicacao/api_manager.py ✅
│   │   └── core/gerenciador_bnb.py ✅
│   └── config/settings.py ✅
│
└── desenvolvimento (branch de testes)
    ├── bot_trading.py 🔧 com correção da reserva
    ├── src/
    │   └── core/gerenciador_bnb.py 🔧 com correção decimal
    └── (resto igual à main)
```

---

## ⚠️ BOAS PRÁTICAS

### ✅ **FAZER:**
- Sempre commitar antes de fazer mudanças grandes
- Usar mensagens de commit descritivas
- Testar na branch desenvolvimento antes de merge
- Commitar mudanças relacionadas juntas

### ❌ **NÃO FAZER:**
- Nunca editar direto na main (sempre usar branch)
- Não fazer commits com código quebrado na main
- Não misturar várias mudanças em um commit
- Não usar `git reset --hard` sem backup

---

## 🆘 COMANDOS DE EMERGÊNCIA

### **Se algo der muito errado:**

```bash
# Ver todos os commits (encontrar versão boa)
git log --oneline

# Voltar para commit específico (SEM perder histórico)
git checkout abc1234

# Criar branch a partir desse ponto
git checkout -b recuperacao

# Descartar TODAS mudanças não commitadas (CUIDADO!)
git reset --hard HEAD
```

### **Se você commitou algo errado na main:**
```bash
# Voltar 1 commit (mantém arquivos modificados)
git reset --soft HEAD~1

# Voltar 1 commit (DESCARTA mudanças - CUIDADO!)
git reset --hard HEAD~1
```

---

## 📝 EXEMPLO PRÁTICO DO NOSSO CASO

### **Situação:**
Queremos corrigir 2 problemas:
1. Reserva de capital não está sendo usada
2. BNB não compra (erro de precisão)

### **Com Git (SEGURO):**

```bash
# 1. Salvar estado atual (funcionando)
git add .
git commit -m "Estado atual - sistema funcionando"

# 2. Criar branch de desenvolvimento
git checkout -b desenvolvimento

# 3. Fazer correções
# Editar bot_trading.py (linha 214)
# Editar gerenciador_bnb.py

# 4. Commitar correções
git add .
git commit -m "Correção: reserva de capital e precisão BNB"

# 5. Testar
./start_bot.sh
# ... aguardar 30 minutos ...
# ... verificar logs ...

# 6a. Se funcionou:
git checkout main
git merge desenvolvimento
echo "✅ Correções aplicadas com sucesso!"

# 6b. Se quebrou:
git checkout main
./start_bot.sh
echo "✅ Voltamos para versão que funciona!"
```

### **Sem Git (ARRISCADO):**
```bash
# 1. Editar arquivos diretamente
# 2. Se quebrar... 😱
# 3. Tentar lembrar o que mudou
# 4. Editar manualmente de volta
# 5. Pode esquecer alguma coisa
# 6. Sistema não volta a funcionar
```

---

## 🎓 RESUMO EM 3 PONTOS

1. **Git = Máquina do tempo para código**
   - Salva versões, permite voltar atrás

2. **Branches = Ambientes paralelos**
   - `main` = produção (sempre funciona)
   - `desenvolvimento` = testes (pode quebrar)

3. **Workflow = Segurança**
   - Mudar em branch → Testar → Se OK, aplicar na main
   - Se quebrar, main não é afetada!

---

## ✅ VANTAGENS NO NOSSO CASO

- 🛡️ **Segurança**: Bot em produção não para se teste falhar
- 🔄 **Reversão**: Pode voltar se correção causar problemas
- 📊 **Histórico**: Ver exatamente o que foi mudado
- 🧪 **Testes**: Experimentar sem medo de quebrar produção
- 📝 **Documentação**: Commits explicam cada mudança

---

**Próximo passo:** Executar o plano acima para implementar as correções de forma segura!
