"""
Schemas do cadastro de usuários.

*Create  -> o que a API RECEBE (com senha).
*Response -> o que a API DEVOLVE (nunca contém a senha).
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.validators import cpf_valido, somente_digitos


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
