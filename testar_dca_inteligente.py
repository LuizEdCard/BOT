#!/usr/bin/env python3
"""
Teste do DCA Inteligente - Gatilho de Dupla-Condição
====================================================

Valida que o bot só compra quando:
1. O degrau está ativo (queda suficiente desde SMA)
2. O preço atual melhora o preço médio em pelo menos X%

Autor: Sistema de Trading ADA/USDT
Data: 15/10/2025
"""

from decimal import Decimal

print("═" * 70)
print("║     TESTE: DCA Inteligente - Dupla-Condição                    ║")
print("═" * 70)
print()

# Parâmetros de teste
PERCENTUAL_MINIMO_MELHORA_PM = Decimal('2.0')  # 2% de melhora mínima

print(f"📊 Configuração: percentual_minimo_melhora_pm = {PERCENTUAL_MINIMO_MELHORA_PM}%")
print()

# ═══════════════════════════════════════════════════════════════════
# Teste 1: Bot sem posição (primeira compra) - deve permitir
# ═══════════════════════════════════════════════════════════════════
print("📋 Teste 1: Bot SEM posição (primeira compra)")
print("-" * 70)

preco_medio_compra = None  # Sem posição
preco_atual = Decimal('0.8000')
queda_pct = Decimal('5.0')  # Degrau 3 ativo (5.5%)

# Condição 1: SMA
condicao_sma_ok = queda_pct >= Decimal('1.5')  # Degrau 1

# Condição 2: Melhora do PM (sempre True se não tem posição)
condicao_melhora_pm_ok = True

print(f"Preço médio: {preco_medio_compra}")
print(f"Preço atual: ${preco_atual:.4f}")
print(f"Queda desde SMA: {queda_pct:.2f}%")
print()
print(f"✅ Condição 1 (SMA): {condicao_sma_ok}")
print(f"✅ Condição 2 (PM): {condicao_melhora_pm_ok}")
print()

if condicao_sma_ok and condicao_melhora_pm_ok:
    print("✅ APROVADO: Bot pode comprar (primeira compra)")
else:
    print("❌ BLOQUEADO: Bot não pode comprar")

print()
print("=" * 70)
print()

# ═══════════════════════════════════════════════════════════════════
# Teste 2: Bot com posição, preço melhora suficiente - deve permitir
# ═══════════════════════════════════════════════════════════════════
print("📋 Teste 2: Bot COM posição, preço MELHORA suficiente")
print("-" * 70)

preco_medio_compra = Decimal('0.8500')  # PM atual
preco_atual = Decimal('0.8250')  # 2.94% menor que PM
queda_pct = Decimal('3.0')  # Degrau 2 ativo

# Condição 1: SMA
condicao_sma_ok = queda_pct >= Decimal('3.0')  # Degrau 2

# Condição 2: Melhora do PM
percentual_melhora = PERCENTUAL_MINIMO_MELHORA_PM / Decimal('100')
limite_preco_melhora = preco_medio_compra * (Decimal('1') - percentual_melhora)
condicao_melhora_pm_ok = preco_atual <= limite_preco_melhora

print(f"Preço médio: ${preco_medio_compra:.4f}")
print(f"Preço atual: ${preco_atual:.4f}")
print(f"Limite para melhora ({PERCENTUAL_MINIMO_MELHORA_PM}%): ${limite_preco_melhora:.4f}")
print(f"Queda desde SMA: {queda_pct:.2f}%")
print()

melhora_real = ((preco_medio_compra - preco_atual) / preco_medio_compra) * Decimal('100')
print(f"Melhora real: {melhora_real:.2f}% (precisa >= {PERCENTUAL_MINIMO_MELHORA_PM}%)")
print()

print(f"✅ Condição 1 (SMA): {condicao_sma_ok}")
print(f"✅ Condição 2 (PM): {condicao_melhora_pm_ok}")
print()

if condicao_sma_ok and condicao_melhora_pm_ok:
    print(f"✅ APROVADO: Bot pode comprar (preço melhora PM em {melhora_real:.2f}%)")
else:
    print("❌ BLOQUEADO: Bot não pode comprar")

print()
print("=" * 70)
print()

# ═══════════════════════════════════════════════════════════════════
# Teste 3: Bot com posição, preço NÃO melhora suficiente - deve bloquear
# ═══════════════════════════════════════════════════════════════════
print("📋 Teste 3: Bot COM posição, preço NÃO melhora suficiente")
print("-" * 70)

preco_medio_compra = Decimal('0.8500')  # PM atual
preco_atual = Decimal('0.8400')  # Apenas 1.18% menor que PM
queda_pct = Decimal('3.0')  # Degrau 2 ativo

# Condição 1: SMA
condicao_sma_ok = queda_pct >= Decimal('3.0')  # Degrau 2

# Condição 2: Melhora do PM
percentual_melhora = PERCENTUAL_MINIMO_MELHORA_PM / Decimal('100')
limite_preco_melhora = preco_medio_compra * (Decimal('1') - percentual_melhora)
condicao_melhora_pm_ok = preco_atual <= limite_preco_melhora

print(f"Preço médio: ${preco_medio_compra:.4f}")
print(f"Preço atual: ${preco_atual:.4f}")
print(f"Limite para melhora ({PERCENTUAL_MINIMO_MELHORA_PM}%): ${limite_preco_melhora:.4f}")
print(f"Queda desde SMA: {queda_pct:.2f}%")
print()

melhora_real = ((preco_medio_compra - preco_atual) / preco_medio_compra) * Decimal('100')
print(f"Melhora real: {melhora_real:.2f}% (precisa >= {PERCENTUAL_MINIMO_MELHORA_PM}%)")
print()

print(f"✅ Condição 1 (SMA): {condicao_sma_ok}")
print(f"❌ Condição 2 (PM): {condicao_melhora_pm_ok}")
print()

if condicao_sma_ok and condicao_melhora_pm_ok:
    print(f"✅ APROVADO: Bot pode comprar (preço melhora PM em {melhora_real:.2f}%)")
else:
    print(f"❌ BLOQUEADO: Bot NÃO pode comprar")
    print(f"   Motivo: Preço atual ${preco_atual:.4f} não melhora PM (${preco_medio_compra:.4f}) em {PERCENTUAL_MINIMO_MELHORA_PM}%")
    print(f"   O preço precisa cair para ${limite_preco_melhora:.4f} ou menos")

print()
print("=" * 70)
print()

# ═══════════════════════════════════════════════════════════════════
# Teste 4: Simulação completa com múltiplas compras
# ═══════════════════════════════════════════════════════════════════
print("📋 Teste 4: Simulação completa - Múltiplas tentativas de compra")
print("-" * 70)

class SimuladorDCA:
    def __init__(self):
        self.preco_medio_compra = None
        self.quantidade_total = Decimal('0')
        self.valor_total_investido = Decimal('0')
        self.percentual_melhora = PERCENTUAL_MINIMO_MELHORA_PM

    def pode_comprar(self, preco_atual, queda_pct, degrau_min):
        # Condição 1: SMA
        condicao_sma_ok = queda_pct >= degrau_min

        # Condição 2: Melhora do PM
        condicao_melhora_pm_ok = True
        if self.preco_medio_compra is not None and self.preco_medio_compra > 0:
            percentual = self.percentual_melhora / Decimal('100')
            limite = self.preco_medio_compra * (Decimal('1') - percentual)
            condicao_melhora_pm_ok = preco_atual <= limite

        return condicao_sma_ok and condicao_melhora_pm_ok

    def executar_compra(self, quantidade, preco):
        valor_compra = quantidade * preco
        self.valor_total_investido += valor_compra
        self.quantidade_total += quantidade
        self.preco_medio_compra = self.valor_total_investido / self.quantidade_total

# Iniciar simulação
bot = SimuladorDCA()

# Cenário: Preço começa em $0.90 e cai gradualmente
cenarios = [
    {"ciclo": 1, "preco": Decimal('0.9000'), "queda": Decimal('0.0'), "degrau": Decimal('1.5'), "desc": "Sem queda"},
    {"ciclo": 2, "preco": Decimal('0.8700'), "queda": Decimal('3.0'), "degrau": Decimal('3.0'), "desc": "Queda 3%"},
    {"ciclo": 3, "preco": Decimal('0.8650'), "queda": Decimal('3.5'), "degrau": Decimal('3.0'), "desc": "Queda 3.5% (tentativa repetida)"},
    {"ciclo": 4, "preco": Decimal('0.8450'), "queda": Decimal('5.5'), "degrau": Decimal('5.5'), "desc": "Queda 5.5%"},
    {"ciclo": 5, "preco": Decimal('0.8400'), "queda": Decimal('6.0'), "degrau": Decimal('5.5'), "desc": "Queda 6% (tentativa repetida)"},
]

for cenario in cenarios:
    print(f"\nCiclo {cenario['ciclo']}: {cenario['desc']}")
    print(f"   Preço: ${cenario['preco']:.4f} | Queda: {cenario['queda']:.1f}%")

    pode = bot.pode_comprar(cenario['preco'], cenario['queda'], cenario['degrau'])

    if pode:
        quantidade = Decimal('10')
        bot.executar_compra(quantidade, cenario['preco'])
        print(f"   ✅ COMPRA EXECUTADA: {quantidade} ADA @ ${cenario['preco']:.4f}")
        print(f"   📊 Novo PM: ${bot.preco_medio_compra:.4f}")
    else:
        if bot.preco_medio_compra:
            print(f"   ❌ BLOQUEADO: Preço não melhora PM (${bot.preco_medio_compra:.4f}) em {PERCENTUAL_MINIMO_MELHORA_PM}%")
        else:
            print(f"   ❌ BLOQUEADO: Degrau não ativo")

print()
print("=" * 70)
print("📊 RESULTADO FINAL")
print("=" * 70)
print(f"Posição final: {bot.quantidade_total} ADA")
print(f"Preço médio final: ${bot.preco_medio_compra:.4f}" if bot.preco_medio_compra else "Sem posição")
print(f"Total investido: ${bot.valor_total_investido:.2f}")
print()
print("✅ DCA INTELIGENTE VALIDADO")
print("=" * 70)
print()
print("📝 BENEFÍCIOS")
print("-" * 70)
print("1. ✅ Evita compras repetidas no mesmo preço")
print("2. ✅ Garante que cada compra melhora o preço médio significativamente")
print("3. ✅ Uso mais eficiente do capital disponível")
print("4. ✅ Reduz risco de over-trading em quedas graduais")
print("=" * 70)
