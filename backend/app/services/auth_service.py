"""Regras do login."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NaoAutenticadoError
from app.core.security import (
    TIPO_TOKEN_ACADEMIA,
    criar_token_acesso,
    gerar_hash_senha,
    verificar_senha,
)
from app.models import Academia
from app.schemas.auth import TokenResponse

# Hash usado quando o e-mail não existe, só para a resposta demorar o mesmo
# tempo de um login com e-mail existente (dificulta descobrir e-mails cadastrados).
_HASH_FALSO = gerar_hash_senha("senha-falsa-para-igualar-o-tempo")


def login_academia(db: Session, email: str, senha: str) -> TokenResponse:
    academia = db.scalar(
        select(Academia).where(func.lower(Academia.email_corporativo) == email)
    )

    senha_ok = verificar_senha(senha, academia.senha_adm if academia else _HASH_FALSO)

    # Mesma mensagem para "e-mail não existe" e "senha errada":
    # não revelamos qual dos dois falhou.
    if academia is None or not senha_ok:
        raise NaoAutenticadoError("E-mail ou senha incorretos.")

    token, expira_em = criar_token_acesso(str(academia.id_academia), TIPO_TOKEN_ACADEMIA)
    return TokenResponse(access_token=token, expires_in=expira_em)
