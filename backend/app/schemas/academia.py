from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.validators import somente_digitos


class AcademiaCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nome_academia: str = Field(min_length=3, max_length=100)
    cnpj: str
    email_corporativo: EmailStr
    senha_adm: str = Field(min_length=8)

    @field_validator("cnpj")
    @classmethod
    def validar_cnpj(cls, v: str) -> str:
        # Por enquanto só confere se tem 14 dígitos (sem validar os dígitos
        # verificadores, como está o CPF em modo de testes).
        digitos = somente_digitos(v)
        if len(digitos) != 14:
            raise ValueError("CNPJ deve ter 14 dígitos")
        return digitos

    @field_validator("email_corporativo")
    @classmethod
    def email_minusculo(cls, v: str) -> str:
        return str(v).lower()

    @field_validator("senha_adm")
    @classmethod
    def validar_senha(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("A senha pode ter no máximo 72 bytes")
        return v


class AcademiaResponse(BaseModel):
    """Nunca inclui a senha."""

    model_config = ConfigDict(from_attributes=True)

    id_academia: int
    nome_academia: str
    email_corporativo: str
    cnpj: str


class AcademiaCadastroResponse(AcademiaResponse):
    mensagem: str = "Academia cadastrada com sucesso!"


class AcademiaMeResponse(AcademiaResponse):
    mensagem: str = "Dados da academia carregados com sucesso!"


class AcademiaResumoResponse(BaseModel):
    """Versão pública: sem e-mail corporativo nem CNPJ."""

    model_config = ConfigDict(from_attributes=True)

    id_academia: int
    nome_academia: str


class AcademiaListaResponse(BaseModel):
    mensagem: str = "Academias listadas com sucesso!"
    total: int
    itens: list[AcademiaResumoResponse]
