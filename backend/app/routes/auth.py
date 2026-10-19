from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import TIPO_TOKEN_ALUNO, TIPO_TOKEN_PROFISSIONAL
from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.services import auth_service

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
