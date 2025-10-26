#!/usr/bin/env python3
"""
Módulo de Validação de Timeframes

Fornece funções centralizadas para validar, normalizar e converter timeframes
em formatos esperados por diferentes partes do sistema.

Timeframes válidos: 1m, 5m, 15m, 30m, 1h, 4h, 1d
"""

from typing import Literal, Optional
import re


# Timeframes suportados em ordem de precisão
VALID_TIMEFRAMES = {
    '1m', '3m', '5m', '15m', '30m',         # Minutos
    '1h', '2h', '4h', '6h', '8h', '12h',   # Horas
    '1d', '1w'                              # Dias e Semanas
}

# Mapeamento de unidades
TIMEFRAME_MULTIPLIERS = {
    'm': 60,           # minutos para segundos
    'h': 3600,         # horas para segundos
    'd': 86400,        # dias para segundos
    'w': 604800,       # semanas para segundos
}

TIMEFRAME_TO_HOURS = {
    'm': 1/60,         # minuto para horas
    'h': 1,            # hora para horas
    'd': 24,           # dia para horas
    'w': 168,          # semana para horas
}


def validate_timeframe(timeframe: str) -> str:
    """
    Valida e normaliza um timeframe para formato padrão (lowercase).

    Args:
        timeframe: Timeframe a validar (ex: '1h', '4h', '1d', '30m')

    Returns:
        Timeframe normalizado em lowercase

    Raises:
        ValueError: Se timeframe é inválido
    """
    if not timeframe:
        raise ValueError("Timeframe não pode estar vazio")

    # Normalizar para lowercase
    timeframe_normalized = timeframe.lower().strip()

    # Validar formato básico: deve ser número seguido de letra
    if not re.match(r'^\d+[mhdws]$', timeframe_normalized):
        raise ValueError(
            f"Timeframe inválido: '{timeframe}'. "
            f"Formato esperado: número + unidade (m/h/d/w). "
            f"Exemplos válidos: 1m, 5m, 15m, 30m, 1h, 4h, 1d"
        )

    # Validar se está na lista de timeframes suportados
    if timeframe_normalized not in VALID_TIMEFRAMES:
        raise ValueError(
            f"Timeframe '{timeframe_normalized}' não suportado. "
            f"Timeframes válidos: {', '.join(sorted(VALID_TIMEFRAMES))}"
        )

    return timeframe_normalized


def timeframe_to_seconds(timeframe: str) -> int:
    """
    Converte timeframe para segundos.

    Args:
        timeframe: Timeframe a converter (ex: '1h' -> 3600)

    Returns:
        Número de segundos

    Raises:
        ValueError: Se timeframe é inválido
    """
    tf = validate_timeframe(timeframe)
    unit = tf[-1]
    value = int(tf[:-1])

    if unit not in TIMEFRAME_MULTIPLIERS:
        raise ValueError(f"Unidade desconhecida: {unit}")

    return value * TIMEFRAME_MULTIPLIERS[unit]


def timeframe_to_hours(timeframe: str) -> float:
    """
    Converte timeframe para horas (float).

    Args:
        timeframe: Timeframe a converter (ex: '30m' -> 0.5)

    Returns:
        Número de horas como float

    Raises:
        ValueError: Se timeframe é inválido
    """
    tf = validate_timeframe(timeframe)
    unit = tf[-1]
    value = int(tf[:-1])

    if unit not in TIMEFRAME_TO_HOURS:
        raise ValueError(f"Unidade desconhecida: {unit}")

    return value * TIMEFRAME_TO_HOURS[unit]


def timeframe_to_hours_int(timeframe: str) -> int:
    """
    Converte timeframe para horas (inteiro, arredondando para cima).

    Args:
        timeframe: Timeframe a converter (ex: '30m' -> 1)

    Returns:
        Número de horas como inteiro (mínimo 1)

    Raises:
        ValueError: Se timeframe é inválido
    """
    hours = timeframe_to_hours(timeframe)
    # Garantir mínimo de 1 hora para timeframes em minutos
    return max(1, int(hours) if hours >= 1 else 1)


def timeframe_in_minutes(timeframe: str) -> float:
    """
    Converte timeframe para minutos (float).

    Args:
        timeframe: Timeframe a converter (ex: '1h' -> 60)

    Returns:
        Número de minutos como float
    """
    tf = validate_timeframe(timeframe)
    return timeframe_to_seconds(tf) / 60


def is_valid_timeframe(timeframe: str) -> bool:
    """
    Verifica se um timeframe é válido sem lançar exceção.

    Args:
        timeframe: Timeframe a verificar

    Returns:
        True se válido, False caso contrário
    """
    try:
        validate_timeframe(timeframe)
        return True
    except ValueError:
        return False


def get_valid_timeframes() -> set:
    """
    Retorna o conjunto de timeframes válidos.

    Returns:
        Set com todos os timeframes suportados
    """
    return VALID_TIMEFRAMES.copy()


def timeframe_description(timeframe: str) -> str:
    """
    Retorna uma descrição legível do timeframe.

    Args:
        timeframe: Timeframe a descrever (ex: '1h')

    Returns:
        Descrição legível (ex: '1 hora')

    Raises:
        ValueError: Se timeframe é inválido
    """
    tf = validate_timeframe(timeframe)
    value = int(tf[:-1])
    unit = tf[-1]

    descriptions = {
        'm': 'minuto' if value == 1 else 'minutos',
        'h': 'hora' if value == 1 else 'horas',
        'd': 'dia' if value == 1 else 'dias',
        'w': 'semana' if value == 1 else 'semanas',
    }

    return f"{value} {descriptions.get(unit, 'período')}"


if __name__ == '__main__':
    """Testes básicos"""
    print("🧪 Teste do Validador de Timeframes\n")

    # Testes válidos
    testes_validos = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1d']
    for tf in testes_validos:
        normalized = validate_timeframe(tf)
        horas = timeframe_to_hours(tf)
        desc = timeframe_description(tf)
        print(f"✅ {tf:5} → normalizado: {normalized:5} | {desc:12} | {horas:5.2f}h")

    print("\n" + "─" * 70)

    # Testes inválidos
    print("\nTestes de Erro (esperado):\n")
    testes_invalidos = ['2h', '6h', 'abc', '60m', 'invalido', '']
    for tf in testes_invalidos:
        try:
            validate_timeframe(tf)
            print(f"❌ {tf}: Deveria ter falhado!")
        except ValueError as e:
            print(f"✅ {tf:15} → Erro detectado (esperado)")

    print("\n" + "─" * 70)
    print(f"\n✅ Timeframes válidos: {sorted(VALID_TIMEFRAMES)}")
