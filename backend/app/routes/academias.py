from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_academia_atual
from app.database import get_db
from app.models import Academia
from app.schemas.academia import AcademiaCreate, AcademiaResponse
from app.services import academia_service

router = APIRouter(prefix="/academias", tags=["Academias"])


@router.post(
    "",
    response_model=AcademiaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar academia",
)
def cadastrar_academia(dados: AcademiaCreate, db: Session = Depends(get_db)):
    """Cadastro público: cria uma academia nova (a senha é guardada como hash)."""
    return academia_service.cadastrar_academia(db, dados)


@router.get("/me", response_model=AcademiaResponse, summary="Dados da academia logada")
def minha_academia(academia: Academia = Depends(get_academia_atual)):
    """Rota protegida: devolve a academia dona do token."""
    return academia
