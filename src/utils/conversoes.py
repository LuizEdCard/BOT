"""
Utilitários para conversões de tipos

Funções auxiliares para converter entre Decimal, float, int e outros tipos
de forma segura e consistente, especialmente para persistência em banco de dados.
"""

from decimal import Decimal
from typing import Any, Optional, Dict


def decimal_para_float(valor: Any) -> Optional[float]:
    """
    Converte Decimal para float de forma segura.

    Args:
        valor: Valor a converter (Decimal, str, float, int ou None)

    Returns:
        Float ou None se valor for None/inválido

    Examples:
        >>> decimal_para_float(Decimal('10.5'))
        10.5
        >>> decimal_para_float(None)
        None
        >>> decimal_para_float('15.3')
        15.3
    """
    if valor is None:
        return None

    try:
        return float(valor)
    except (ValueError, TypeError):
        return None


def preparar_valor_db(valor: Any) -> Any:
    """
    Prepara um valor para inserção no banco de dados.
    Converte Decimal para float, mantém outros tipos.

    Args:
        valor: Valor a preparar

    Returns:
        Valor convertido ou original

    Examples:
        >>> preparar_valor_db(Decimal('10.5'))
        10.5
        >>> preparar_valor_db('texto')
        'texto'
        >>> preparar_valor_db(None)
        None
    """
    if isinstance(valor, Decimal):
        return decimal_para_float(valor)
    return valor


def preparar_dados_db(dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converte todos os Decimals de um dicionário para float.

    Args:
        dados: Dicionário com valores mistos

    Returns:
        Dicionário com Decimals convertidos para float

    Examples:
        >>> preparar_dados_db({'preco': Decimal('10.5'), 'nome': 'ADA'})
        {'preco': 10.5, 'nome': 'ADA'}
    """
    return {
        chave: preparar_valor_db(valor)
        for chave, valor in dados.items()
    }


def extrair_valores_db(dados: Dict[str, Any], campos: list) -> tuple:
    """
    Extrai valores de um dicionário na ordem especificada,
    convertendo Decimals para float automaticamente.

    Args:
        dados: Dicionário com os dados
        campos: Lista de nomes de campos na ordem desejada

    Returns:
        Tupla com valores na ordem especificada

    Examples:
        >>> dados = {'preco': Decimal('10.5'), 'quantidade': Decimal('5'), 'nome': 'ADA'}
        >>> extrair_valores_db(dados, ['nome', 'preco', 'quantidade'])
        ('ADA', 10.5, 5.0)
    """
    return tuple(
        preparar_valor_db(dados.get(campo))
        for campo in campos
    )


def float_para_decimal(valor: Any) -> Optional[Decimal]:
    """
    Converte float/str/int para Decimal de forma segura.

    Args:
        valor: Valor a converter

    Returns:
        Decimal ou None se valor for None/inválido

    Examples:
        >>> float_para_decimal(10.5)
        Decimal('10.5')
        >>> float_para_decimal('15.3')
        Decimal('15.3')
        >>> float_para_decimal(None)
        None
    """
    if valor is None:
        return None

    try:
        # Converter para string primeiro para evitar imprecisão de float
        return Decimal(str(valor))
    except (ValueError, TypeError, ArithmeticError):
        return None
