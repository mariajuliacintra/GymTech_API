from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_academia_atual
from app.database import get_db
from app.models import Academia
from app.schemas.usuario import (
    AlunoCreate,
    AlunoResponse,
    ProfissionalCreate,
    ProfissionalResponse,
    AlunoCadastroResponse,
    ProfissionalCadastroResponse
)
from app.services import usuario_service

# Todas as rotas daqui exigem uma academia logada. A academia vem do TOKEN,
# não da URL: não dá para cadastrar usuários em nome de outra academia.
router = APIRouter(tags=["Cadastro de usuários"])


@router.post(
    "/alunos",
    response_model= AlunoCadastroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar aluno",
    
)
def cadastrar_aluno(
    dados: AlunoCreate,
    academia: Academia = Depends(get_academia_atual),
    db: Session = Depends(get_db),
):
    """A academia logada cadastra um novo usuário do tipo **Aluno**."""
    usuario = usuario_service.cadastrar_aluno(db, academia.id_academia, dados)
    return AlunoResponse.from_usuario(usuario)


@router.post(
    "/profissionais",
    response_model= ProfissionalCadastroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar profissional",
)
def cadastrar_profissional(
    dados: ProfissionalCreate,
    academia: Academia = Depends(get_academia_atual),
    db: Session = Depends(get_db),
):
    """A academia logada cadastra um novo usuário do tipo **Profissional**."""
    usuario = usuario_service.cadastrar_profissional(db, academia.id_academia, dados)
    return ProfissionalResponse.from_usuario(usuario)
