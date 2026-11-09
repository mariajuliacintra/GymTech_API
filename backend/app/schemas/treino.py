import re
from datetime import date, time
from decimal import Decimal
from typing import ClassVar, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_FORMATO_TEMPO = re.compile(r"^\d{2}:\d{2}(:\d{2})?$")


class _EntradaTreino(BaseModel):
    """
    Base das entradas. `extra="forbid"`: campo desconhecido (status, data_criacao,
    fk_id_academia, e até fk_id_profissional onde ele não é permitido) dá 422
    em vez de ser ignorado em silêncio.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


# ----------------------------------------------------------- itens do treino
class ItemTreinoEntrada(_EntradaTreino):
    """
    Um exercício dentro do treino. Os limites de série/repetição/carga seguem o
    banco (séries e repetições > 0, carga >= 0 e até 9999,99), com tetos
    razoáveis para evitar erros de digitação.
    """

    fk_id_exercicio: int = Field(ge=1, description="id do exercício (da mesma academia)")
    series: int = Field(ge=1, le=50)
    repeticoes: int = Field(ge=1, le=500)
    carga_sugerida: Optional[Decimal] = Field(
        default=None, ge=0, max_digits=6, decimal_places=2, description="Em kg, até 9999,99"
    )
    tempo_descanso: Optional[time] = Field(default=None, description="HH:MM:SS (ex.: 00:01:30)")

    @field_validator("tempo_descanso", mode="before")
    @classmethod
    def _formato_do_tempo(cls, v):
        # só texto HH:MM[:SS]; número solto (90?) é ambíguo e fuso/fração não cabem no TIME
        if v is None:
            return v
        if not isinstance(v, str) or not _FORMATO_TEMPO.match(v):
            raise ValueError("Use o formato HH:MM:SS (ex.: 00:01:30)")
        return v


def _itens_validos(itens: Optional[list[ItemTreinoEntrada]]) -> Optional[list[ItemTreinoEntrada]]:
    """O mesmo exercício não pode aparecer duas vezes no mesmo treino."""
    if itens is None:
        return itens
    ids = [i.fk_id_exercicio for i in itens]
    if len(ids) != len(set(ids)):
        raise ValueError("O mesmo exercício não pode aparecer mais de uma vez no treino.")
    return itens


# --------------------------------------------------------------------- entrada
class TreinoCreate(_EntradaTreino):
    """Cadastro feito pela ACADEMIA: ela escolhe o aluno e o profissional. Exige ao menos 1 exercício."""

    fk_id_aluno: int = Field(ge=1, description="id_usuario do aluno")
    fk_id_profissional: int = Field(ge=1, description="id_usuario do profissional")
    titulo_treino: str = Field(min_length=3, max_length=100)
    data_programada: Optional[date] = None
    itens: list[ItemTreinoEntrada] = Field(min_length=1, max_length=50)

    _itens = field_validator("itens")(_itens_validos)


class TreinoCreateProfissional(_EntradaTreino):
    """Cadastro feito pelo PROFISSIONAL: o profissional é ele mesmo (vem do token)."""

    fk_id_aluno: int = Field(ge=1, description="id_usuario do aluno")
    titulo_treino: str = Field(min_length=3, max_length=100)
    data_programada: Optional[date] = None
    itens: list[ItemTreinoEntrada] = Field(min_length=1, max_length=50)

    _itens = field_validator("itens")(_itens_validos)


class _AtualizacaoTreino(_EntradaTreino):
    """
    Atualização parcial: só os campos enviados mudam. `data_programada` aceita
    null (limpa). Se `itens` for enviado, a lista de exercícios é SUBSTITUÍDA
    por inteiro (na ordem enviada); se não for enviado, os itens ficam como estão.
    """

    CAMPOS_NAO_NULOS: ClassVar[tuple[str, ...]] = ("titulo_treino", "fk_id_profissional", "itens")

    titulo_treino: Optional[str] = Field(default=None, min_length=3, max_length=100)
    data_programada: Optional[date] = None
    itens: Optional[list[ItemTreinoEntrada]] = Field(default=None, min_length=1, max_length=50)

    _itens = field_validator("itens")(_itens_validos)

    @model_validator(mode="after")
    def validar_envio(self) -> "_AtualizacaoTreino":
        if not self.model_fields_set:
            raise ValueError("Envie ao menos um campo para atualizar.")
        for campo in self.CAMPOS_NAO_NULOS:
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"O campo '{campo}' não pode ser nulo.")
        return self


class TreinoUpdate(_AtualizacaoTreino):
    """Atualização pela ACADEMIA: também pode trocar o profissional responsável."""

    fk_id_profissional: Optional[int] = Field(default=None, ge=1)


class TreinoUpdateProfissional(_AtualizacaoTreino):
    """Atualização pelo PROFISSIONAL: título, data e exercícios (não repassa o treino a outro)."""


# ---------------------------------------------------------------------- saída
class ItemTreinoResponse(BaseModel):
    id_item_treino: int
    fk_id_exercicio: int
    nome_exercicio: str
    grupo_muscular: str
    descricao_execucao: Optional[str]
    series: int
    repeticoes: int
    carga_sugerida: Optional[float]
    tempo_descanso: Optional[time]


class TreinoResponse(BaseModel):
    id_treino: int
    fk_id_aluno: int
    nome_aluno: str
    fk_id_profissional: int
    nome_profissional: str
    titulo_treino: str
    data_criacao: date
    data_programada: Optional[date]
    status: str
    quantidade_exercicios: int
    # null nas listagens (a menos que ?incluir_itens=true); sempre preenchido nas demais respostas
    itens: Optional[list[ItemTreinoResponse]] = None


class TreinoCadastroResponse(TreinoResponse):
    mensagem: str = "Treino cadastrado com sucesso!"


class TreinoDetalheResponse(TreinoResponse):
    mensagem: str = "Treino carregado com sucesso!"


class TreinoUpdateResponse(TreinoResponse):
    mensagem: str = "Treino atualizado com sucesso!"


class TreinoCancelamentoResponse(TreinoResponse):
    mensagem: str = "Treino cancelado com sucesso!"


class TreinoListaResponse(BaseModel):
    mensagem: str = "Treinos listados com sucesso!"
    total: int  # total que bate com o filtro (não só desta página)
    itens: list[TreinoResponse]
