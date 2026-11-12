from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.tempo import para_hora_local


class _EntradaAula(BaseModel):
    """
    Base das entradas. `extra="forbid"`: campo desconhecido (status, fk_id_academia,
    id_aula...) dá 422 em vez de ser ignorado em silêncio: a academia vem do token.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("data_horario", check_fields=False)
    @classmethod
    def _hora_local(cls, v: Optional[datetime]) -> Optional[datetime]:
        # aceita "2026-11-20T18:00:00" (horário da academia) ou com fuso ("...Z", "-03:00")
        return v if v is None else para_hora_local(v)


# --------------------------------------------------------------------- entrada
class AulaCreate(_EntradaAula):
    fk_id_profissional: int = Field(ge=1, description="id_usuario do profissional que dá a aula")
    nome_aula: str = Field(min_length=3, max_length=100)
    tipo_aula: str = Field(min_length=2, max_length=100)
    data_horario: datetime = Field(description="Início da aula, no horário da academia (AAAA-MM-DDTHH:MM:SS)")
    capacidade_maxima: int = Field(ge=1, le=500)


class AulaUpdate(_EntradaAula):
    """Atualização parcial: só os campos enviados mudam. Nenhum aceita null."""

    fk_id_profissional: Optional[int] = Field(default=None, ge=1)
    nome_aula: Optional[str] = Field(default=None, min_length=3, max_length=100)
    tipo_aula: Optional[str] = Field(default=None, min_length=2, max_length=100)
    data_horario: Optional[datetime] = None
    capacidade_maxima: Optional[int] = Field(default=None, ge=1, le=500)

    @model_validator(mode="after")
    def validar_envio(self) -> "AulaUpdate":
        if not self.model_fields_set:
            raise ValueError("Envie ao menos um campo para atualizar.")
        for campo in self.model_fields_set:
            if getattr(self, campo) is None:
                raise ValueError(f"O campo '{campo}' não pode ser nulo.")
        return self


# ---------------------------------------------------------------------- saída
class AulaResponse(BaseModel):
    id_aula: int
    fk_id_academia: int
    fk_id_profissional: int
    nome_profissional: str
    nome_aula: str
    tipo_aula: str
    data_horario: datetime
    capacidade_maxima: int
    vagas_ocupadas: int
    vagas_disponiveis: int
    status: str


class AulaCadastroResponse(AulaResponse):
    mensagem: str = "Aula cadastrada com sucesso!"


class AulaDetalheResponse(AulaResponse):
    mensagem: str = "Aula carregada com sucesso!"


class AulaUpdateResponse(AulaResponse):
    mensagem: str = "Aula atualizada com sucesso!"


class AulaCancelamentoResponse(AulaResponse):
    mensagem: str = "Aula cancelada com sucesso!"


class AulaListaResponse(BaseModel):
    mensagem: str = "Aulas listadas com sucesso!"
    total: int  # total que bate com o filtro (não só desta página)
    itens: list[AulaResponse]
