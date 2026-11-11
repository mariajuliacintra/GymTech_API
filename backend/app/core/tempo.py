"""
Hora "de parede" da academia.

Colunas DATETIME (como data_horario da aula) não guardam fuso: o valor é só
"dia e hora". Para decidir se uma aula está no futuro, a API compara com a hora
atual NO FUSO DA ACADEMIA (settings.TIMEZONE, padrão America/Sao_Paulo), e não
com a hora do servidor da API nem a do banco, que podem estar em outro fuso
(servidores em nuvem costumam usar UTC e errariam em horas).

No Windows o Python precisa do pacote `tzdata` (está no requirements.txt).
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings

FUSO = ZoneInfo(settings.TIMEZONE)


def agora_local() -> datetime:
    """Agora, no fuso da academia, SEM informação de fuso (comparável com o DATETIME do banco)."""
    return datetime.now(FUSO).replace(tzinfo=None, microsecond=0)


def para_hora_local(valor: datetime) -> datetime:
    """
    Normaliza um datetime recebido: se vier COM fuso (ex.: "...Z" de um front em
    JavaScript), converte para o fuso da academia; sempre devolve sem fuso e sem
    frações de segundo (o DATETIME do banco as arredondaria).
    """
    if valor.tzinfo is not None:
        valor = valor.astimezone(FUSO).replace(tzinfo=None)
    return valor.replace(microsecond=0)
