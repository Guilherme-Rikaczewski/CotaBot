"""Formatação dos valores monetários gravados no banco."""

# Casas decimais usadas em `coins.conversion_value`.
CONVERSION_DECIMALS = 2


def format_conversion(value: float) -> str:
    """Valor de cotação como string, no formato gravado em `coins`.

    Sempre com duas casas — `f'{v:.2f}'` em vez de `str(round(v, 2))`
    porque o `round` devolveria '5.5' para 5,50 e '408061.0' para o BTC,
    deixando a coluna com larguras diferentes para o mesmo tipo de dado.
    """
    return f'{value:.{CONVERSION_DECIMALS}f}'
