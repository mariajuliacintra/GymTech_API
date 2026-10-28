from datetime import date
from typing import ClassVar, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _EntradaTreino(BaseModel):
    """
    Base das entradas. `extra="forbid"`: campo desconhecido (status, data_criacao,
    fk_id_academia, e até fk_id_profissional onde ele não é permitido) dá 422
    em vez de ser ignorado em silêncio.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


# --------------------------------------------------------------------- entrada
class TreinoCreate(_EntradaTreino):
    """Cadastro feito pela ACADEMIA: ela escolhe o aluno e o profissional."""

    fk_id_aluno: int = Field(ge=1, description="id_usuario do aluno")
    fk_id_profissional: int = Field(ge=1, description="id_usuario do profissional")
    titulo_treino: str = Field(min_length=3, max_length=100)
    data_programada: Optional[date] = None


class TreinoCreateProfissional(_EntradaTreino):
    """Cadastro feito pelo PROFISSIONAL: o profissional é ele mesmo (vem do token)."""

    fk_id_aluno: int = Field(ge=1, description="id_usuario do aluno")
    titulo_treino: str = Field(min_length=3, max_length=100)
    data_programada: Optional[date] = None


class _AtualizacaoTreino(_EntradaTreino):
    """Atualização parcial: só os campos enviados mudam. `data_programada` aceita null (limpa)."""

    CAMPOS_NAO_NULOS: ClassVar[tuple[str, ...]] = ("titulo_treino", "fk_id_profissional")

    titulo_treino: Optional[str] = Field(default=None, min_length=3, max_length=100)
    data_programada: Optional[date] = None

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
    """Atualização pelo PROFISSIONAL: título e data (não repassa o treino a outro)."""


# ---------------------------------------------------------------------- saída
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
