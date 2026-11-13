from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.tempo import para_hora_local


class _EntradaAgendamento(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("data_horario", check_fields=False)
    @classmethod
    def _hora_local(cls, v: Optional[datetime]) -> Optional[datetime]:
        return v if v is None else para_hora_local(v)


class AgendamentoAvaliacaoCreate(_EntradaAgendamento):
    """
    Cadastro feito pelo aluno (ou pela academia). O `fk_id_aluno` é injetado pelo
    token se for o aluno, ou exigido no payload se for a academia.
    """
    fk_id_profissional: int = Field(ge=1, description="id_usuario do profissional")
    data_horario: datetime = Field(description="Horário no fuso da academia (AAAA-MM-DDTHH:MM:SS)")
    fk_id_aluno: Optional[int] = Field(default=None, description="Obrigatório para academia; ignorado para o aluno.")


class AgendamentoAvaliacaoUpdate(_EntradaAgendamento):
    """Apenas a academia tem permissão genérica de update para reagendar, se necessário."""
    fk_id_profissional: Optional[int] = Field(default=None, ge=1)
    data_horario: Optional[datetime] = None

    @model_validator(mode="after")
    def validar_envio(self) -> "AgendamentoAvaliacaoUpdate":
        if not self.model_fields_set:
            raise ValueError("Envie ao menos um campo para atualizar.")
        for campo in self.model_fields_set:
            if getattr(self, campo) is None:
                raise ValueError(f"O campo '{campo}' não pode ser nulo.")
        return self


class AgendamentoAvaliacaoResponse(BaseModel):
    id_agendamento_avaliacao: int
    fk_id_aluno: int
    nome_aluno: str
    fk_id_profissional: int
    nome_profissional: str
    data_horario: datetime
    status: str
    possui_ficha: bool

class AgendamentoAvaliacaoDetalheResponse(AgendamentoAvaliacaoResponse):
    mensagem: str = "Agendamento listado com sucesso!"


class AgendamentoAvaliacaoCadastroResponse(AgendamentoAvaliacaoResponse):
    mensagem: str = "Agendamento realizado com sucesso!"


class AgendamentoAvaliacaoUpdateResponse(AgendamentoAvaliacaoResponse):
    mensagem: str = "Agendamento atualizado com sucesso!"


class AgendamentoAvaliacaoCancelamentoResponse(AgendamentoAvaliacaoResponse):
    mensagem: str = "Agendamento cancelado com sucesso!"


class AgendamentoAvaliacaoListaResponse(BaseModel):
    mensagem: str = "Agendamentos listados com sucesso!"
    total: int
    itens: list[AgendamentoAvaliacaoResponse]
