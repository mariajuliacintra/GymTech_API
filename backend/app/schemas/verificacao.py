"""
Schemas da verificação de identidade (esqueci a senha e confirmação de alterações).

A pessoa prova quem é com o código de 6 dígitos que recebeu por e-mail.
"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ProvaIdentidade(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    codigo: str = Field(pattern=r"^\d{6}$")


class EsqueciSenhaRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr

    @field_validator("email")
    @classmethod
    def email_minusculo(cls, v: str) -> str:
        return str(v).lower()


class RedefinirSenhaRequest(EsqueciSenhaRequest):
    nova_senha: str = Field(min_length=8)
    verificacao: ProvaIdentidade

    @field_validator("nova_senha")
    @classmethod
    def validar_senha(cls, v: str) -> str:
        # o bcrypt só considera os 72 primeiros bytes da senha
        if len(v.encode("utf-8")) > 72:
            raise ValueError("A senha pode ter no máximo 72 bytes")
        return v


class MensagemResponse(BaseModel):
    mensagem: str


class CodigoEnviadoResponse(MensagemResponse):
    destino: str  # e-mail mascarado, ex.: j***@gmail.com
