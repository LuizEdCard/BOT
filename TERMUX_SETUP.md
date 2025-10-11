# 📱 TRADING BOT - SETUP TERMUX

Guia completo para rodar o bot 24/7 no Termux sem interrupções.

---

## 🚀 INSTALAÇÃO INICIAL NO TERMUX

### 1. Instalar Termux

Baixe do **F-Droid** (recomendado) ou Play Store:
- F-Droid: https://f-droid.org/en/packages/com.termux/
- **IMPORTANTE:** Versão do Play Store pode estar desatualizada!

### 2. Atualizar Pacotes

```bash
pkg update && pkg upgrade
```

### 3. Instalar Dependências

```bash
# Python e Git
pkg install python git

# Termux API (para wakelock)
pkg install termux-api

# Utilitários
pkg install nano wget curl
```

### 4. Configurar Armazenamento

```bash
termux-setup-storage
```

Permita acesso ao armazenamento quando solicitado.

---

## 📁 SETUP DO BOT

### 1. Clonar/Copiar o Projeto

Se estiver copiando de outro lugar:

```bash
cd storage/shared/
cp -r /path/to/BOT ~/trading_bot
cd ~/trading_bot
```

Ou se usar Git:

```bash
cd ~/
git clone <seu-repositorio> trading_bot
cd trading_bot
```

### 2. Configurar .env

```bash
# Copiar template
cp config/.env.example config/.env

# Editar com suas API keys
nano config/.env
```

**IMPORTANTE:** Configure suas API keys da Binance:
```
BINANCE_API_KEY=sua_key_aqui
BINANCE_API_SECRET=seu_secret_aqui
AMBIENTE=PRODUCAO
```

Para salvar no nano: `Ctrl+O`, `Enter`, `Ctrl+X`

### 3. Instalar Dependências Python

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar
source venv/bin/activate

# Instalar
pip install -r requirements.txt
```

### 4. Testar Configuração

```bash
python test_config.py
```

Deve mostrar:
```
✅ BINANCE_API_KEY: Configurada
✅ BINANCE_API_SECRET: Configurada
✅ Todas as validações passaram!
```

---

## 🎮 COMANDOS DE CONTROLE

### Iniciar Bot (Modo Interativo)

```bash
./start_bot.sh
```

Use `Ctrl+C` para parar.

### Iniciar Bot (Background)

```bash
./start_background.sh
```

**O bot rodará em background mesmo se você fechar o Termux!**

### Ver Status

```bash
./status_bot.sh
```

Mostra:
- Se está rodando
- PID do processo
- Tempo ativo
- Uso de memória/CPU
- Últimas 10 linhas do log

### Parar Bot

```bash
./stop_bot.sh
```

### Reiniciar Bot

```bash
./restart_bot.sh
```

### Ver Logs em Tempo Real

```bash
# Log principal
tail -f logs/bot_background.log

# Erros
tail -f logs/bot_errors.log

# Para sair: Ctrl+C
```

---

## 🔒 WAKELOCK (IMPEDIR SUSPENSÃO)

O bot usa **wakelock** para continuar rodando mesmo quando a tela trava.

### Verificar Wakelock

```bash
termux-wake-lock
```

### Liberar Wakelock (Manual)

```bash
termux-wake-unlock
```

**NOTA:** Os scripts já fazem isso automaticamente!

---

## 🔄 AUTO-RESTART (WATCHDOG)

O watchdog monitora o bot e reinicia automaticamente se cair.

### Iniciar Watchdog

```bash
# Em uma nova sessão do Termux
nohup ./watchdog.sh > /dev/null 2>&1 &
```

### Verificar Watchdog

```bash
ps aux | grep watchdog
```

### Parar Watchdog

```bash
pkill -f watchdog.sh
```

### Ver Log do Watchdog

```bash
tail -f logs/watchdog.log
```

---

## 📱 MÚLTIPLAS SESSÕES TERMUX

Para rodar bot + watchdog simultaneamente:

### Opção 1: Termux:Boot (Recomendado)

Instale o app **Termux:Boot** (F-Droid):

1. Criar script de inicialização:

```bash
mkdir -p ~/.termux/boot
nano ~/.termux/boot/start-bot.sh
```

2. Adicionar conteúdo:

```bash
#!/data/data/com.termux/files/usr/bin/bash
cd ~/trading_bot
./start_background.sh
sleep 10
./watchdog.sh &
```

3. Tornar executável:

```bash
chmod +x ~/.termux/boot/start-bot.sh
```

4. **Reiniciar dispositivo**

O bot iniciará automaticamente após o boot!

### Opção 2: tmux (Múltiplas Abas)

```bash
# Instalar tmux
pkg install tmux

# Criar sessão
tmux new -s trading

# Dividir tela: Ctrl+B depois "
# Alternar painéis: Ctrl+B depois setas

# Painel 1: Bot
./start_bot.sh

# Painel 2: Logs
tail -f logs/bot_background.log

# Desanexar sessão: Ctrl+B depois D
# Reanexar: tmux attach -t trading
```

---

## ⚡ OTIMIZAÇÕES TERMUX

### 1. Evitar Timeout de Sessão

No `~/.bashrc`:

```bash
echo "TMOUT=0" >> ~/.bashrc
source ~/.bashrc
```

### 2. Manter Processo Ativo

```bash
# Usar nohup
nohup ./start_bot.sh &

# Ou tmux
tmux new -s bot -d ./start_bot.sh
```

### 3. Monitoramento de Recursos

```bash
# Ver processos
top

# Ver uso de memória
free -h

# Ver uso de CPU
ps aux | grep python
```

---

## 🛡️ SEGURANÇA NO TERMUX

### 1. Proteger .env

```bash
chmod 600 config/.env
```

### 2. Backup Regular

```bash
# Criar backup
tar -czf backup_$(date +%Y%m%d).tar.gz \
    config/.env \
    dados/ \
    logs/

# Mover para armazenamento seguro
mv backup_*.tar.gz ~/storage/downloads/
```

### 3. Limpar Logs Antigos

```bash
# Limpar logs com mais de 7 dias
find logs/ -name "*.log" -mtime +7 -delete
```

---

## 🆘 TROUBLESHOOTING

### Bot Não Inicia

```bash
# Verificar logs de erro
cat logs/bot_errors.log

# Verificar configuração
python test_config.py

# Verificar dependências
pip list | grep colorama
```

### Bot Para Quando Tela Trava

```bash
# Verificar se termux-api está instalado
pkg list-installed | grep termux-api

# Reinstalar se necessário
pkg install termux-api

# Testar wakelock
termux-wake-lock
sleep 5
termux-wake-unlock
```

### "Permission Denied"

```bash
# Tornar scripts executáveis
chmod +x *.sh
```

### "Module Not Found"

```bash
# Ativar venv
source venv/bin/activate

# Reinstalar dependências
pip install -r requirements.txt
```

### Bot Consumindo Muita Memória

```bash
# Ver uso
ps aux | grep python

# Reiniciar bot
./restart_bot.sh
```

---

## 📊 MONITORAMENTO

### Dashboard Simples (watch)

```bash
watch -n 5 './status_bot.sh'
```

Atualiza status a cada 5 segundos.

### Script de Monitoramento

Crie `monitor.sh`:

```bash
#!/bin/bash
while true; do
    clear
    ./status_bot.sh
    sleep 10
done
```

Execute:
```bash
chmod +x monitor.sh
./monitor.sh
```

---

## 🔧 MANUTENÇÃO

### Atualizar Código

```bash
# Parar bot
./stop_bot.sh

# Atualizar
git pull  # ou copiar novos arquivos

# Reinstalar dependências se necessário
source venv/bin/activate
pip install -r requirements.txt

# Reiniciar
./start_background.sh
```

### Verificar Saúde do Bot

```bash
# Status
./status_bot.sh

# Últimas operações
tail -n 50 dados/historico_$(date +%Y-%m).txt

# Erros recentes
tail -n 20 logs/bot_errors.log
```

---

## ⚙️ CONFIGURAÇÕES AVANÇADAS

### Inicialização Automática (sem Termux:Boot)

Use cron (requer root):

```bash
# Editar crontab
crontab -e

# Adicionar linha:
@reboot sleep 60 && cd ~/trading_bot && ./start_background.sh
```

### Notificações Termux

No seu bot Python, adicione:

```python
import subprocess

def enviar_notificacao(titulo, mensagem):
    subprocess.run([
        'termux-notification',
        '-t', titulo,
        '-c', mensagem
    ])

# Usar:
enviar_notificacao('Trading Bot', 'Compra executada!')
```

---

## 📞 COMANDOS RÁPIDOS

```bash
# Status
./status_bot.sh

# Iniciar
./start_background.sh

# Parar
./stop_bot.sh

# Reiniciar
./restart_bot.sh

# Logs
tail -f logs/bot_background.log

# Watchdog
nohup ./watchdog.sh &
```

---

## ✅ CHECKLIST PÓS-INSTALAÇÃO

- [ ] Termux instalado (F-Droid)
- [ ] Termux-API instalado
- [ ] Python 3.10+ instalado
- [ ] Dependências instaladas
- [ ] config/.env configurado
- [ ] API keys válidas
- [ ] test_config.py passou
- [ ] Bot inicia sem erros
- [ ] Wakelock funcionando
- [ ] Watchdog configurado
- [ ] Logs sendo gerados

---

## 🎯 PRÓXIMOS PASSOS

1. ✅ Bot rodando em background
2. ✅ Wakelock ativado
3. ✅ Watchdog monitorando
4. 📱 Configurar Termux:Boot (opcional)
5. 📊 Monitorar por 24h
6. 💰 Acompanhar trades!

---

**Pronto para rodar 24/7 sem interrupções! 🚀**
