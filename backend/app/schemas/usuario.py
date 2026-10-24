"""
Schemas do cadastro de usuários.

*Create  -> o que a API RECEBE (com senha).
*Response -> o que a API DEVOLVE (nunca contém a senha).
"""
from datetime import date, datetime
from typing import ClassVar, Optional, Union

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.validators import cpf_valido, somente_digitos
from app.schemas.verificacao import ProvaIdentidade


# ----------------------------------------------------------------- entrada
class UsuarioCreate(BaseModel):
    """Campos comuns a aluno e profissional."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nome: str = Field(min_length=3, max_length=100)
    cpf: str
    email: EmailStr
    senha: str = Field(min_length=8)
    telefone: Optional[str] = None
    data_nascimento: date

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, v: str) -> str:
        digitos = somente_digitos(v)
        if not cpf_valido(digitos):
            raise ValueError("CPF inválido")
        return digitos  # guardamos só os 11 dígitos, como o CHAR(11) do banco

    @field_validator("email")
    @classmethod
    def email_minusculo(cls, v: str) -> str:
        return str(v).lower()

    @field_validator("senha")
    @classmethod
    def validar_senha(cls, v: str) -> str:
        # o bcrypt só considera os 72 primeiros bytes da senha
        if len(v.encode("utf-8")) > 72:
            raise ValueError("A senha pode ter no máximo 72 bytes")
        return v

    @field_validator("telefone")
    @classmethod
    def validar_telefone(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        digitos = somente_digitos(v)
        if len(digitos) not in (10, 11):
            raise ValueError("Telefone deve ter DDD + número (10 ou 11 dígitos)")
        return digitos

    @field_validator("data_nascimento")
    @classmethod
    def validar_nascimento(cls, v: date) -> date:
        if v >= date.today():
            raise ValueError("Data de nascimento deve estar no passado")
        return v


class AlunoCreate(UsuarioCreate):
    modalidade_treino: Optional[str] = Field(default=None, max_length=50)
    objetivo: Optional[str] = Field(default=None, max_length=150)

class ProfissionalCreate(UsuarioCreate):
    especialidade: Optional[str] = Field(default=None, max_length=100)
    registro_profissional: str = Field(min_length=1, max_length=50)


# ------------------------------------------------------------------ saída
class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    fk_id_academia: int
    nome: str
    cpf: str
    email: str
    telefone: Optional[str]
    data_nascimento: date
    data_cadastro: datetime
    status: str
    tipo_perfil: str


class AlunoResponse(UsuarioResponse):
    modalidade_treino: Optional[str]
    objetivo: Optional[str]

    @classmethod
    def from_usuario(cls, usuario) -> "AlunoResponse":
        base = UsuarioResponse.model_validate(usuario).model_dump()
        return cls(
            **base,
            modalidade_treino=usuario.aluno.modalidade_treino,
            objetivo=usuario.aluno.objetivo,
        )


class ProfissionalResponse(UsuarioResponse):
    especialidade: Optional[str]
    registro_profissional: str

    @classmethod
    def from_usuario(cls, usuario) -> "ProfissionalResponse":
        base = UsuarioResponse.model_validate(usuario).model_dump()
        return cls(
            **base,
            especialidade=usuario.profissional.especialidade,
            registro_profissional=usuario.profissional.registro_profissional,
        )

class AlunoCadastroResponse(AlunoResponse):
    mensagem: str = "Aluno cadastrado com sucesso!"


class ProfissionalCadastroResponse(ProfissionalResponse):
    mensagem: str = "Profissional cadastrado com sucesso!"


class UsuarioMeResponse(UsuarioResponse):
    mensagem: str = "Dados do usuário carregados com sucesso!"


# ------------------------------------------------- saída: inativação (delete)
class UsuarioInativadoResponse(BaseModel):
    """
    Resposta da "deleção" (inativação) de aluno/profissional.

    `cancelamentos` mostra o que foi cancelado em cascata nas outras tabelas
    ligadas ao usuário, ex.: {"agendamentos cancelados": 3}. Fica vazio
    enquanto nenhuma tabela ligada ao usuário tiver sido criada.
    """

    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    nome: str
    tipo_perfil: str
    status: str
    cancelamentos: dict[str, int] = Field(default_factory=dict)
    mensagem: str


class AlunoDeleteResponse(UsuarioInativadoResponse):
    mensagem: str = "Aluno inativado com sucesso!"


class ProfissionalDeleteResponse(UsuarioInativadoResponse):
    mensagem: str = "Profissional inativado com sucesso!"


# --------------------------------------------------------- saída: listagens
def usuario_para_response(usuario) -> Union[AlunoResponse, ProfissionalResponse]:
    """Escolhe o schema certo (aluno ou profissional) conforme o tipo_perfil."""
    if usuario.tipo_perfil == "Aluno":
        return AlunoResponse.from_usuario(usuario)
    return ProfissionalResponse.from_usuario(usuario)


class AlunoListaResponse(BaseModel):
    mensagem: str = "Alunos listados com sucesso!"
    total: int  # total que bate com o filtro (não só desta página)
    itens: list[AlunoResponse]


class ProfissionalListaResponse(BaseModel):
    mensagem: str = "Profissionais listados com sucesso!"
    total: int
    itens: list[ProfissionalResponse]


class UsuarioListaResponse(BaseModel):
    mensagem: str = "Usuários listados com sucesso!"
    total: int
    itens: list[Union[AlunoResponse, ProfissionalResponse]]


# ------------------------------------------------- entrada: atualizar os próprios dados
class UsuarioUpdate(BaseModel):
    """
    O usuário atualiza os PRÓPRIOS dados (a academia não pode). É parcial:
    só vão para o banco os campos enviados. `verificacao` é obrigatória: prova
    de que é mesmo a pessoa (código de 6 dígitos enviado ao e-mail).

    Não dá para alterar: cpf, senha (use o "esqueci a senha"), status, tipo,
    academia. Enviar qualquer campo desconhecido é erro (422), não é ignorado.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    # campos que, se enviados, não podem ser null (telefone e os extras podem: limpam o valor)
    CAMPOS_NAO_NULOS: ClassVar[frozenset[str]] = frozenset({"nome", "email", "data_nascimento"})

    verificacao: ProvaIdentidade
    nome: Optional[str] = Field(default=None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    data_nascimento: Optional[date] = None

    @field_validator("email")
    @classmethod
    def email_minusculo(cls, v: Optional[str]) -> Optional[str]:
        return str(v).lower() if v else v

    @field_validator("telefone")
    @classmethod
    def validar_telefone(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        digitos = somente_digitos(v)
        if len(digitos) not in (10, 11):
            raise ValueError("Telefone deve ter DDD + número (10 ou 11 dígitos)")
        return digitos

    @field_validator("data_nascimento")
    @classmethod
    def validar_nascimento(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v >= date.today():
            raise ValueError("Data de nascimento deve estar no passado")
        return v

    @model_validator(mode="after")
    def validar_envio(self) -> "UsuarioUpdate":
        enviados = self.model_fields_set - {"verificacao"}
        if not enviados:
            raise ValueError("Envie ao menos um campo para atualizar.")
        for campo in enviados & self.CAMPOS_NAO_NULOS:
            if getattr(self, campo) is None:
                raise ValueError(f"O campo '{campo}' não pode ser nulo.")
        return self


class AlunoUpdate(UsuarioUpdate):
    modalidade_treino: Optional[str] = Field(default=None, max_length=50)
    objetivo: Optional[str] = Field(default=None, max_length=150)


class ProfissionalUpdate(UsuarioUpdate):
    CAMPOS_NAO_NULOS: ClassVar[frozenset[str]] = frozenset(
        {"nome", "email", "data_nascimento", "registro_profissional"}
    )

    especialidade: Optional[str] = Field(default=None, max_length=100)
    registro_profissional: Optional[str] = Field(default=None, min_length=1, max_length=50)


class AlunoUpdateResponse(AlunoResponse):
    mensagem: str = "Dados atualizados com sucesso!"


class ProfissionalUpdateResponse(ProfissionalResponse):
    mensagem: str = "Dados atualizados com sucesso!"
