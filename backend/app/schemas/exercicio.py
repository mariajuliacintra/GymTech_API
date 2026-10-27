from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _vazio_vira_none(v: Optional[str]) -> Optional[str]:
    """Texto opcional enviado em branco ("" ou só espaços) é tratado como 'não informado'."""
    return v or None


# --------------------------------------------------------------------- entrada
class ExercicioCreate(BaseModel):
    """
    Cadastro de exercício. A academia dona vem do TOKEN, nunca do corpo; por
    isso campos desconhecidos (fk_id_academia, id_exercicio...) dão erro 422
    em vez de serem ignorados em silêncio.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    nome_exercicio: str = Field(min_length=3, max_length=100)
    grupo_muscular: str = Field(min_length=3, max_length=50)  # obrigatório, como no banco
    descricao_execucao: Optional[str] = Field(default=None, max_length=2000)

    _limpar = field_validator("descricao_execucao")(_vazio_vira_none)


class ExercicioUpdate(BaseModel):
    """
    Atualização parcial: só os campos enviados mudam. `descricao_execucao`
    aceita null para limpar; `nome_exercicio` e `grupo_muscular` não (são
    obrigatórios no banco).
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    nome_exercicio: Optional[str] = Field(default=None, min_length=3, max_length=100)
    grupo_muscular: Optional[str] = Field(default=None, min_length=3, max_length=50)
    descricao_execucao: Optional[str] = Field(default=None, max_length=2000)

    _limpar = field_validator("descricao_execucao")(_vazio_vira_none)

    @model_validator(mode="after")
    def validar_envio(self) -> "ExercicioUpdate":
        if not self.model_fields_set:
            raise ValueError("Envie ao menos um campo para atualizar.")
        for campo in ("nome_exercicio", "grupo_muscular"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"O campo '{campo}' não pode ser nulo.")
        return self


# ---------------------------------------------------------------------- saída
class ExercicioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_exercicio: int
    fk_id_academia: int
    nome_exercicio: str
    grupo_muscular: str
    descricao_execucao: Optional[str]


class ExercicioCadastroResponse(ExercicioResponse):
    mensagem: str = "Exercício cadastrado com sucesso!"


class ExercicioDetalheResponse(ExercicioResponse):
    mensagem: str = "Exercício carregado com sucesso!"


class ExercicioUpdateResponse(ExercicioResponse):
    mensagem: str = "Exercício atualizado com sucesso!"


class ExercicioDeleteResponse(ExercicioResponse):
    mensagem: str = "Exercício excluído com sucesso!"


class ExercicioListaResponse(BaseModel):
    mensagem: str = "Exercícios listados com sucesso!"
    total: int  # total que bate com o filtro (não só desta página)
    itens: list[ExercicioResponse]
