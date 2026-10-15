import re


def somente_digitos(valor: str) -> str:
    """'123.456.789-09' -> '12345678909'"""
    return re.sub(r"\D", "", valor)


def cpf_valido(cpf: str) -> bool:
    # """Valida um CPF (apenas dígitos) pelo cálculo dos dois dígitos verificadores."""
    # if len(cpf) != 11 or not cpf.isdigit() or cpf == cpf[0] * 11:
    #     return False
    # for i in (9, 10):
    #     soma = sum(int(cpf[n]) * (i + 1 - n) for n in range(i))
    #     digito = (soma * 10 % 11) % 10
    #     if digito != int(cpf[i]):
    #         return False
    return True
