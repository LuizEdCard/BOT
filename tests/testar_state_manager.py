#!/usr/bin/env python3
"""
Script de teste para o StateManager.

Testa:
1. Criação e inicialização
2. Persistência de timestamps
3. Recuperação após "reinício"
4. Robustez (arquivo corrompido, faltando, etc)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta
import json
import os

from src.persistencia.state_manager import StateManager


def teste_1_criacao_inicial():
    """Teste 1: Criação e inicialização"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("TESTE 1: Criação e inicialização do StateManager")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Limpar arquivo de teste se existir
    test_file = 'dados/test_state.json'
    if os.path.exists(test_file):
        os.remove(test_file)
        print(f"✅ Arquivo de teste removido: {test_file}")

    # Criar StateManager
    state = StateManager(state_file_path=test_file)
    print(f"✅ StateManager criado: {state}")

    # Verificar arquivo criado
    if os.path.exists(test_file):
        print(f"✅ Arquivo JSON criado: {test_file}")
    else:
        print(f"❌ ERRO: Arquivo não foi criado!")
        return False

    # Verificar estado vazio
    estado_completo = state.get_all_state()
    if estado_completo == {}:
        print(f"✅ Estado inicial vazio: {estado_completo}")
    else:
        print(f"❌ ERRO: Estado deveria estar vazio!")
        return False

    print("\n✅ TESTE 1 PASSOU!\n")
    return True


def teste_2_persistencia_timestamps():
    """Teste 2: Salvar e recuperar timestamps"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("TESTE 2: Persistência de timestamps")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    test_file = 'dados/test_state.json'
    state = StateManager(state_file_path=test_file)

    # Simular cooldowns
    agora = datetime.now()
    timestamp_iso = agora.isoformat()

    print(f"📝 Salvando timestamp global: {timestamp_iso}")
    state.set_state('ultima_compra_global_ts', timestamp_iso)

    print(f"📝 Salvando timestamp degrau 1")
    state.set_state('ultima_compra_degrau_1_ts', timestamp_iso)

    print(f"📝 Salvando timestamp degrau 3")
    state.set_state('ultima_compra_degrau_3_ts', timestamp_iso)

    # Verificar valores salvos
    ts_recuperado = state.get_state('ultima_compra_global_ts')
    if ts_recuperado == timestamp_iso:
        print(f"✅ Timestamp global recuperado: {ts_recuperado}")
    else:
        print(f"❌ ERRO: Timestamp não corresponde!")
        return False

    # Verificar arquivo JSON diretamente
    with open(test_file, 'r') as f:
        conteudo = json.load(f)

    print(f"\n📄 Conteúdo do arquivo JSON:")
    print(json.dumps(conteudo, indent=2, ensure_ascii=False))

    if 'ultima_compra_global_ts' in conteudo:
        print(f"✅ Timestamp persistido no arquivo JSON")
    else:
        print(f"❌ ERRO: Timestamp não encontrado no arquivo!")
        return False

    print("\n✅ TESTE 2 PASSOU!\n")
    return True


def teste_3_recuperacao_apos_reinicio():
    """Teste 3: Simular reinício do bot"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("TESTE 3: Recuperação após reinício")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    test_file = 'dados/test_state.json'

    # PRIMEIRA INSTÂNCIA - Salvar dados
    print("🔵 PRIMEIRA INSTÂNCIA: Salvando estado...")
    state1 = StateManager(state_file_path=test_file)

    timestamp_compra = (datetime.now() - timedelta(minutes=15)).isoformat()
    state1.set_state('ultima_compra_global_ts', timestamp_compra)
    state1.set_state('ultima_compra_degrau_2_ts', timestamp_compra)

    print(f"   Timestamp salvo: {timestamp_compra}")

    # SEGUNDA INSTÂNCIA - Simular reinício
    print("\n🟢 SEGUNDA INSTÂNCIA: Simulando reinício do bot...")
    state2 = StateManager(state_file_path=test_file)

    # Recuperar timestamps
    ts_global = state2.get_state('ultima_compra_global_ts')
    ts_degrau = state2.get_state('ultima_compra_degrau_2_ts')

    if ts_global == timestamp_compra:
        print(f"✅ Timestamp global recuperado: {ts_global}")
    else:
        print(f"❌ ERRO: Timestamp global não corresponde!")
        return False

    if ts_degrau == timestamp_compra:
        print(f"✅ Timestamp degrau 2 recuperado: {ts_degrau}")
    else:
        print(f"❌ ERRO: Timestamp degrau não corresponde!")
        return False

    # Calcular tempo decorrido
    timestamp_dt = datetime.fromisoformat(ts_global)
    tempo_decorrido = datetime.now() - timestamp_dt
    minutos = int(tempo_decorrido.total_seconds() / 60)

    print(f"\n⏱️  Tempo desde última compra: {minutos} minutos")

    print("\n✅ TESTE 3 PASSOU!\n")
    return True


def teste_4_arquivo_corrompido():
    """Teste 4: Robustez com arquivo corrompido"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("TESTE 4: Robustez com arquivo corrompido")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    test_file = 'dados/test_state_corrupted.json'

    # Criar arquivo corrompido
    with open(test_file, 'w') as f:
        f.write("{ isso não é JSON válido }")

    print(f"📝 Arquivo corrompido criado: {test_file}")

    # Tentar carregar StateManager (deve criar backup e reiniciar)
    state = StateManager(state_file_path=test_file)

    # Verificar se backup foi criado
    backup_file = 'dados/test_state_corrupted.json.corrupted'
    if os.path.exists(backup_file):
        print(f"✅ Backup criado: {backup_file}")
        os.remove(backup_file)
    else:
        print(f"⚠️  Backup não foi criado (pode ter falhado)")

    # Verificar estado vazio
    estado = state.get_all_state()
    if estado == {}:
        print(f"✅ Estado reiniciado como vazio")
    else:
        print(f"❌ ERRO: Estado deveria estar vazio!")
        return False

    # Limpar arquivo de teste
    if os.path.exists(test_file):
        os.remove(test_file)

    print("\n✅ TESTE 4 PASSOU!\n")
    return True


def teste_5_cooldown_duplo():
    """Teste 5: Simular lógica de cooldown duplo"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("TESTE 5: Simulação de cooldown duplo")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    test_file = 'dados/test_state.json'
    state = StateManager(state_file_path=test_file)

    # Simular compra no degrau 2 há 5 minutos
    compra_degrau2 = (datetime.now() - timedelta(minutes=5)).isoformat()
    state.set_state('ultima_compra_global_ts', compra_degrau2)
    state.set_state('ultima_compra_degrau_2_ts', compra_degrau2)

    print(f"📝 Compra degrau 2 registrada: há 5 minutos")

    # Simular compra no degrau 4 há 1 hora
    compra_degrau4 = (datetime.now() - timedelta(hours=1)).isoformat()
    state.set_state('ultima_compra_degrau_4_ts', compra_degrau4)

    print(f"📝 Compra degrau 4 registrada: há 1 hora")

    # Verificar cooldown global
    agora = datetime.now()
    ts_global = state.get_state('ultima_compra_global_ts')

    if ts_global:
        ultima_compra = datetime.fromisoformat(ts_global)
        tempo_decorrido = agora - ultima_compra
        minutos = int(tempo_decorrido.total_seconds() / 60)

        print(f"\n⏱️  Tempo desde última compra GLOBAL: {minutos} minutos")

        cooldown_global = 30  # minutos
        if minutos < cooldown_global:
            print(f"🔒 Cooldown global ATIVO (faltam {cooldown_global - minutos} min)")
        else:
            print(f"🔓 Cooldown global INATIVO")

    # Verificar cooldown por degrau
    for degrau in [2, 4]:
        chave = f'ultima_compra_degrau_{degrau}_ts'
        ts_degrau = state.get_state(chave)

        if ts_degrau:
            ultima_compra_degrau = datetime.fromisoformat(ts_degrau)
            tempo_decorrido = agora - ultima_compra_degrau
            horas = tempo_decorrido.total_seconds() / 3600

            print(f"\n⏱️  Tempo desde última compra DEGRAU {degrau}: {horas:.1f} horas")

    print("\n✅ TESTE 5 PASSOU!\n")
    return True


def limpar_arquivos_teste():
    """Limpar arquivos de teste"""
    arquivos = [
        'dados/test_state.json',
        'dados/test_state_corrupted.json',
        'dados/test_state_corrupted.json.corrupted'
    ]

    for arquivo in arquivos:
        if os.path.exists(arquivo):
            os.remove(arquivo)
            print(f"🗑️  Removido: {arquivo}")


def main():
    """Executar todos os testes"""
    print("\n")
    print("╔═══════════════════════════════════════════════╗")
    print("║  SUITE DE TESTES - StateManager              ║")
    print("╚═══════════════════════════════════════════════╝")
    print("\n")

    testes = [
        teste_1_criacao_inicial,
        teste_2_persistencia_timestamps,
        teste_3_recuperacao_apos_reinicio,
        teste_4_arquivo_corrompido,
        teste_5_cooldown_duplo
    ]

    resultados = []

    for teste in testes:
        try:
            resultado = teste()
            resultados.append(resultado)
        except Exception as e:
            print(f"❌ ERRO NO TESTE: {e}")
            import traceback
            traceback.print_exc()
            resultados.append(False)

    # Limpar arquivos de teste
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("LIMPEZA")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    limpar_arquivos_teste()

    # Relatório final
    print("\n")
    print("╔═══════════════════════════════════════════════╗")
    print("║  RELATÓRIO FINAL                             ║")
    print("╚═══════════════════════════════════════════════╝")
    print(f"\nTotal de testes: {len(resultados)}")
    print(f"✅ Passaram: {sum(resultados)}")
    print(f"❌ Falharam: {len(resultados) - sum(resultados)}")

    if all(resultados):
        print("\n🎉 TODOS OS TESTES PASSARAM! 🎉\n")
        return 0
    else:
        print("\n⚠️  ALGUNS TESTES FALHARAM! ⚠️\n")
        return 1


if __name__ == '__main__':
    exit(main())
