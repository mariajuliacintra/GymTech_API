from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import Paginacao, get_academia_atual, get_paginacao
from app.database import get_db
from app.models import Academia
from app.schemas.academia import (
    AcademiaCadastroResponse,
    AcademiaCreate,
    AcademiaListaResponse,
    AcademiaMeResponse,
    AcademiaResumoResponse,
)
from app.services import academia_service

router = APIRouter(prefix="/academias", tags=["Academias"])


@router.post(
    "",
    response_model=AcademiaCadastroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar academia",
)
def cadastrar_academia(dados: AcademiaCreate, db: Session = Depends(get_db)):
    """Cadastro público: cria uma academia nova (a senha é guardada como hash)."""
    return academia_service.cadastrar_academia(db, dados)


@router.get("/me", response_model=AcademiaMeResponse, summary="Dados da academia logada")
def minha_academia(academia: Academia = Depends(get_academia_atual)):
    """Rota protegida: devolve a academia dona do token."""
    return academia


@router.get("", response_model=AcademiaListaResponse, summary="Listar academias")
def listar_academias(
    _: Academia = Depends(get_academia_atual),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """
    Lista todas as academias (só id e nome; e-mail e CNPJ não são expostos).
    Exige uma academia logada.
    """
    academias, total = academia_service.listar_academias(db, pag.limit, pag.offset)
    return AcademiaListaResponse(
        total=total,
        itens=[AcademiaResumoResponse.model_validate(a) for a in academias],
    )
