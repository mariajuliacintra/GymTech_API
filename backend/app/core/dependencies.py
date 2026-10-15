"""
Dependências de autenticação: usadas nas rotas com `Depends(...)`.

Exemplo:
    def minha_rota(academia: Academia = Depends(get_academia_atual)): ...
Se não houver token válido de academia, a rota nem chega a ser executada.
"""
from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import NaoAutenticadoError, NaoAutorizadoError
from app.core.security import TIPO_TOKEN_ACADEMIA, decodificar_token
from app.database import get_db
from app.models import Academia

# Cria o botão "Authorize" no /docs, onde se cola o token do login.
# auto_error=False para devolvermos sempre o nosso 401 padronizado.
bearer_scheme = HTTPBearer(auto_error=False)


def get_academia_atual(
    credenciais: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Academia:
    """Devolve a academia dona do token; senão, responde 401/403."""
    if credenciais is None:
        raise NaoAutenticadoError("Não autenticado. Faça login e envie o token.")

    payload = decodificar_token(credenciais.credentials)

    if payload["tipo"] != TIPO_TOKEN_ACADEMIA:
        raise NaoAutorizadoError("Este recurso é exclusivo de academias.")

    try:
        id_academia = int(payload["sub"])
    except ValueError:
        raise NaoAutenticadoError("Token inválido ou expirado.")

    # Busca no banco a cada requisição: se a academia foi removida, o token deixa de valer.
    academia = db.get(Academia, id_academia)
    if academia is None:
        raise NaoAutenticadoError("Token inválido ou expirado.")
    return academia
