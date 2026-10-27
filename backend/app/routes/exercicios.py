"""
CRUD de exercícios. Tudo exige token de ACADEMIA e só alcança os exercícios dela.

    POST   /exercicios                    cadastrar
    GET    /exercicios                    listar
    GET    /exercicios/{id_exercicio}     ver um
    PATCH  /exercicios/{id_exercicio}     atualizar (só os campos enviados)
    DELETE /exercicios/{id_exercicio}     excluir (apaga de verdade)
"""
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import Paginacao, get_academia_atual, get_paginacao
from app.database import get_db
from app.models import Academia
from app.schemas.exercicio import (
    ExercicioCadastroResponse,
    ExercicioCreate,
    ExercicioDeleteResponse,
    ExercicioDetalheResponse,
    ExercicioListaResponse,
    ExercicioResponse,
    ExercicioUpdate,
    ExercicioUpdateResponse,
)
from app.services import exercicio_service

router = APIRouter(prefix="/exercicios", tags=["Exercícios"])


@router.post(
    "",
    response_model=ExercicioCadastroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar exercício",
)
def cadastrar_exercicio(
    dados: ExercicioCreate,
    academia: Academia = Depends(get_academia_atual),
    db: Session = Depends(get_db),
):
    """Cadastra um exercício na academia logada. Nome repetido na mesma academia dá 409."""
    exercicio = exercicio_service.cadastrar_exercicio(db, academia.id_academia, dados)
    return ExercicioCadastroResponse.model_validate(exercicio)


@router.get("", response_model=ExercicioListaResponse, summary="Listar exercícios")
def listar_exercicios(
    grupo_muscular: Optional[str] = Query(None, min_length=1, max_length=50, description="Filtra pelo grupo muscular (sem diferenciar maiúsculas)"),
    busca: Optional[str] = Query(None, min_length=1, max_length=100, description="Parte do nome do exercício"),
    academia: Academia = Depends(get_academia_atual),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """Exercícios da academia logada, em ordem alfabética."""
    exercicios, total = exercicio_service.listar_exercicios(
        db, academia.id_academia, grupo_muscular, busca, pag.limit, pag.offset
    )
    return ExercicioListaResponse(
        total=total, itens=[ExercicioResponse.model_validate(e) for e in exercicios]
    )


@router.get(
    "/{id_exercicio}",
    response_model=ExercicioDetalheResponse,
    summary="Ver um exercício",
)
def obter_exercicio(
    id_exercicio: int = Path(ge=1),
    academia: Academia = Depends(get_academia_atual),
    db: Session = Depends(get_db),
):
    exercicio = exercicio_service.obter_exercicio(db, academia.id_academia, id_exercicio)
    return ExercicioDetalheResponse.model_validate(exercicio)


@router.patch(
    "/{id_exercicio}",
    response_model=ExercicioUpdateResponse,
    summary="Atualizar exercício",
)
def atualizar_exercicio(
    dados: ExercicioUpdate,
    id_exercicio: int = Path(ge=1),
    academia: Academia = Depends(get_academia_atual),
    db: Session = Depends(get_db),
):
    """Atualiza só os campos enviados. `descricao_execucao` aceita `null` para limpar."""
    exercicio = exercicio_service.atualizar_exercicio(
        db, academia.id_academia, id_exercicio, dados
    )
    return ExercicioUpdateResponse.model_validate(exercicio)


@router.delete(
    "/{id_exercicio}",
    response_model=ExercicioDeleteResponse,
    summary="Excluir exercício",
)
def excluir_exercicio(
    id_exercicio: int = Path(ge=1),
    academia: Academia = Depends(get_academia_atual),
    db: Session = Depends(get_db),
):
    """
    **Apaga** o exercício (a tabela não tem status). A resposta traz os dados
    dele como eram. Se algo já usar o exercício, responde 409 e não apaga.
    """
    copia = exercicio_service.excluir_exercicio(db, academia.id_academia, id_exercicio)
    return ExercicioDeleteResponse(**copia.model_dump())
