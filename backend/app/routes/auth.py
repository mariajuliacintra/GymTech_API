from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.security import TIPO_TOKEN_ALUNO, TIPO_TOKEN_PROFISSIONAL
from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.verificacao import (
    EsqueciSenhaRequest,
    MensagemResponse,
    RedefinirSenhaRequest,
)
from app.services import auth_service, senha_service, verificacao_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/academia/login", response_model=TokenResponse, summary="Login da academia")
def login_academia(dados: LoginRequest, db: Session = Depends(get_db)):
    """Recebe e-mail corporativo e senha; devolve o token de acesso (JWT)."""
    return auth_service.login_academia(db, dados.email, dados.senha)


@router.post("/aluno/login", response_model=TokenResponse, summary="Login do aluno")
def login_aluno(dados: LoginRequest, db: Session = Depends(get_db)):
    """Recebe e-mail e senha de um **aluno**; devolve o token de acesso (JWT)."""
    return auth_service.login_usuario(db, dados.email, dados.senha, TIPO_TOKEN_ALUNO)


@router.post(
    "/profissional/login", response_model=TokenResponse, summary="Login do profissional"
)
def login_profissional(dados: LoginRequest, db: Session = Depends(get_db)):
    """Recebe e-mail e senha de um **profissional**; devolve o token de acesso (JWT)."""
    return auth_service.login_usuario(
        db, dados.email, dados.senha, TIPO_TOKEN_PROFISSIONAL
    )


# ------------------------------------------------------------ esqueci a senha
Perfil = Literal["academia", "aluno", "profissional"]


@router.post(
    "/{perfil}/esqueci-senha",
    response_model=MensagemResponse,
    summary="Esqueci a senha: enviar código por e-mail",
)
def esqueci_senha(
    perfil: Perfil,
    dados: EsqueciSenhaRequest,
    segundo_plano: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Envia um código de 6 dígitos para o e-mail da conta (vale 10 minutos).

    A resposta é **sempre a mesma**, exista ou não uma conta com esse e-mail
    (assim ninguém descobre quem é cadastrado).
    """
    envio = senha_service.solicitar_codigo(db, perfil, dados.email)
    if envio is not None:
        segundo_plano.add_task(verificacao_service.despachar_email_silencioso, envio)
    return MensagemResponse(
        mensagem="Se o e-mail estiver cadastrado, enviamos um código de verificação."
    )


@router.post(
    "/{perfil}/redefinir-senha",
    response_model=MensagemResponse,
    summary="Redefinir a senha com o código recebido por e-mail",
)
def redefinir_senha(perfil: Perfil, dados: RedefinirSenhaRequest, db: Session = Depends(get_db)):
    """
    Troca a senha se o código recebido por e-mail estiver certo:
    `"verificacao": {"codigo": "123456"}`
    """
    senha_service.redefinir_senha(
        db, perfil, dados.email, dados.nova_senha, dados.verificacao
    )
    return MensagemResponse(mensagem="Senha redefinida com sucesso!")
