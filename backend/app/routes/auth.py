from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/academia/login", response_model=TokenResponse, summary="Login da academia")
def login_academia(dados: LoginRequest, db: Session = Depends(get_db)):
    """Recebe e-mail corporativo e senha; devolve o token de acesso (JWT)."""
    return auth_service.login_academia(db, dados.email, dados.senha)
