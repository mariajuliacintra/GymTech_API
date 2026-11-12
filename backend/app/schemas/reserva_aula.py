from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------- entrada
class ReservaAulaCreate(BaseModel):
    """
    Cadastro de reserva feito pelo ALUNO. O aluno vem do TOKEN, nunca do corpo;
    por isso campos desconhecidos (fk_id_aluno, status, id_reserva_aula...) dão
    422 em vez de serem ignorados em silêncio.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    fk_id_aula: int = Field(ge=1, description="id da aula que o aluno quer reservar")


# ---------------------------------------------------------------------- saída
class ReservaAulaResponse(BaseModel):
    id_reserva_aula: int
    fk_id_aula: int
    nome_aula: str
    tipo_aula: str
    data_horario_aula: datetime
    fk_id_profissional: int
    nome_profissional: str
    fk_id_aluno: int
    nome_aluno: str
    data_agendamento: datetime
    status: str
    capacidade_maxima: int
    vagas_ocupadas: int
    vagas_disponiveis: int


class ReservaAulaCadastroResponse(ReservaAulaResponse):
    mensagem: str = "Reserva realizada com sucesso!"


class ReservaAulaDetalheResponse(ReservaAulaResponse):
    mensagem: str = "Reserva carregada com sucesso!"


class ReservaAulaCancelamentoResponse(ReservaAulaResponse):
    mensagem: str = "Reserva cancelada com sucesso!"


class ReservaAulaListaResponse(BaseModel):
    mensagem: str = "Reservas listadas com sucesso!"
    total: int  # total que bate com o filtro (não só desta página)
    itens: list[ReservaAulaResponse]
