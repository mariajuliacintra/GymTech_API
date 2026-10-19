"""
Dependências de autenticação: usadas nas rotas com `Depends(...)`.

    get_academia_atual     -> exige token de ACADEMIA
    get_usuario_atual      -> exige token de ALUNO ou PROFISSIONAL
    get_aluno_atual        -> exige token de ALUNO
    get_profissional_atual -> exige token de PROFISSIONAL

Exemplo:
    def minha_rota(aluno: Aluno = Depends(get_aluno_atual)): ...
Se não houver token válido do tipo certo, a rota nem chega a ser executada.
"""
from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import NaoAutenticadoError, NaoAutorizadoError
from app.core.security import (
    TIPO_TOKEN_ACADEMIA,
    TIPO_TOKEN_ALUNO,
    TIPO_TOKEN_PROFISSIONAL,
    decodificar_token,
)
from app.database import get_db
from app.models import Academia, Aluno, Profissional, Usuario

# Cria o botão "Authorize" no /docs, onde se cola o token do login.
# auto_error=False para devolvermos sempre o nosso 401 padronizado.
bearer_scheme = HTTPBearer(auto_error=False)

_TOKEN_INVALIDO = "Token inválido ou expirado."


def _payload_do_token(credenciais: Optional[HTTPAuthorizationCredentials]) -> dict:
    if credenciais is None:
        raise NaoAutenticadoError("Não autenticado. Faça login e envie o token.")
    return decodificar_token(credenciais.credentials)


def _id_do_token(payload: dict) -> int:
    try:
        return int(payload["sub"])
    except ValueError:
        raise NaoAutenticadoError(_TOKEN_INVALIDO)


def get_academia_atual(
    credenciais: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Academia:
    """Devolve a academia dona do token; senão, responde 401/403."""
    payload = _payload_do_token(credenciais)

    if payload["tipo"] != TIPO_TOKEN_ACADEMIA:
        raise NaoAutorizadoError("Este recurso é exclusivo de academias.")

    # Busca no banco a cada requisição: se a academia foi removida, o token deixa de valer.
    academia = db.get(Academia, _id_do_token(payload))
    if academia is None:
        raise NaoAutenticadoError(_TOKEN_INVALIDO)
    return academia


def get_usuario_atual(
    credenciais: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Devolve o usuário (aluno ou profissional) dono do token."""
    payload = _payload_do_token(credenciais)

    if payload["tipo"] not in (TIPO_TOKEN_ALUNO, TIPO_TOKEN_PROFISSIONAL):
        raise NaoAutorizadoError("Este recurso é exclusivo de alunos e profissionais.")

    usuario = db.get(Usuario, _id_do_token(payload))
    # O tipo do token precisa continuar igual ao do banco.
    if usuario is None or usuario.tipo_perfil != payload["tipo"]:
        raise NaoAutenticadoError(_TOKEN_INVALIDO)
    # Usuário desativado pela academia perde o acesso mesmo com token ainda válido.
    if usuario.status != "Ativo":
        raise NaoAutorizadoError("Usuário inativo. Procure a sua academia.")
    return usuario


def get_aluno_atual(usuario: Usuario = Depends(get_usuario_atual)) -> Aluno:
    if usuario.tipo_perfil != TIPO_TOKEN_ALUNO or usuario.aluno is None:
        raise NaoAutorizadoError("Este recurso é exclusivo de alunos.")
    return usuario.aluno


def get_profissional_atual(usuario: Usuario = Depends(get_usuario_atual)) -> Profissional:
    if usuario.tipo_perfil != TIPO_TOKEN_PROFISSIONAL or usuario.profissional is None:
        raise NaoAutorizadoError("Este recurso é exclusivo de profissionais.")
    return usuario.profissional
