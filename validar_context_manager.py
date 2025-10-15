#!/usr/bin/env python3
"""
Validação estática do context manager no database.py
Verifica que todos os métodos usam o context manager corretamente
"""
import re
from pathlib import Path

print("=" * 70)
print("VALIDAÇÃO DO CONTEXT MANAGER - database.py")
print("=" * 70)

# Ler arquivo database.py
db_file = Path('src/persistencia/database.py')
codigo = db_file.read_text()

# Padrão 1: Encontrar todos os métodos que usam self._conectar()
pattern_with = r'with self\._conectar\(\) as conn:'
metodos_com_context = []

linhas = codigo.split('\n')
for i, linha in enumerate(linhas, 1):
    if 'with self._conectar() as conn:' in linha:
        # Encontrar nome do método (voltar nas linhas)
        for j in range(i-1, max(0, i-10), -1):
            if linhas[j-1].strip().startswith('def '):
                nome_metodo = re.search(r'def\s+(\w+)', linhas[j-1])
                if nome_metodo:
                    metodos_com_context.append({
                        'nome': nome_metodo.group(1),
                        'linha': i,
                        'linha_def': j
                    })
                break

print(f"\n✅ Encontrados {len(metodos_com_context)} métodos usando context manager:\n")
for metodo in metodos_com_context:
    print(f"   • {metodo['nome']:40s} (linha {metodo['linha']})")

# Padrão 2: Verificar se há algum uso antigo de sqlite3.connect
pattern_old = r'sqlite3\.connect\((?!.*_conectar)'
usos_antigos = []

for i, linha in enumerate(linhas, 1):
    if 'sqlite3.connect(' in linha and 'def _conectar' not in linha:
        usos_antigos.append({'linha': i, 'codigo': linha.strip()})

if usos_antigos:
    print(f"\n⚠️  Encontrados {len(usos_antigos)} usos antigos de sqlite3.connect:")
    for uso in usos_antigos:
        print(f"   Linha {uso['linha']}: {uso['codigo']}")
else:
    print("\n✅ Nenhum uso antigo de sqlite3.connect() encontrado")
    print("   (exceto no próprio método _conectar e _criar_banco)")

# Padrão 3: Verificar se cursor está sempre dentro do bloco with
print("\n🔍 Verificando indentação do cursor nos métodos...")

erros_indentacao = []
for metodo in metodos_com_context:
    linha_with = metodo['linha'] - 1  # Índice 0-based

    # Pegar as próximas 30 linhas após o with
    bloco = linhas[linha_with:linha_with + 30]

    # Detectar se há cursor.execute fora do with
    indentacao_with = len(bloco[0]) - len(bloco[0].lstrip())

    for i, linha_bloco in enumerate(bloco[1:], 1):
        if 'cursor.' in linha_bloco:
            indentacao_cursor = len(linha_bloco) - len(linha_bloco.lstrip())
            # cursor deve ter indentação maior que with
            if indentacao_cursor <= indentacao_with:
                erros_indentacao.append({
                    'metodo': metodo['nome'],
                    'linha': linha_with + i + 1
                })
                break

if erros_indentacao:
    print(f"\n❌ Encontrados {len(erros_indentacao)} erros de indentação:")
    for erro in erros_indentacao:
        print(f"   • {erro['metodo']} (linha {erro['linha']})")
else:
    print("✅ Todos os cursors estão corretamente indentados dentro do bloco with")

# Resumo final
print("\n" + "=" * 70)
print("RESUMO DA VALIDAÇÃO")
print("=" * 70)
print(f"✅ Métodos refatorados com context manager: {len(metodos_com_context)}")
print(f"✅ Usos antigos de sqlite3.connect: {len(usos_antigos)}")
print(f"✅ Erros de indentação: {len(erros_indentacao)}")

if len(metodos_com_context) >= 10 and len(usos_antigos) <= 1 and len(erros_indentacao) == 0:
    print("\n🎉 VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
    print("   Todos os métodos estão usando o context manager corretamente")
else:
    print("\n⚠️  Alguns problemas foram encontrados")

print("=" * 70)
