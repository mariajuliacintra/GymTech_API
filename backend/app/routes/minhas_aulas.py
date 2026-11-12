"""
Aulas, visão do PROFISSIONAL e do ALUNO. Só leitura: quem cadastra e altera
aulas é a academia (aulas.py), e o aluno reserva vaga em reservas_aulas.py.

    GET /profissionais/me/aulas              as aulas em que ele é o profissional
    GET /profissionais/me/aulas/{id_aula}
    GET /alunos/me/aulas                     TODAS as aulas da academia do aluno
    GET /alunos/me/aulas/{id_aula}
"""
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.dependencies import Paginacao, get_aluno_atual, get_paginacao, get_profissional_atual
from app.database import get_db
from app.models import Aluno, Profissional
from app.routes.aulas import FiltrosAula, get_filtros_aula
from app.schemas.aula import AulaDetalheResponse, AulaListaResponse
from app.services import aula_service
from app.services.aula_service import Escopo

router = APIRouter(tags=["Minhas aulas"])


def escopo_profissional(profissional: Profissional = Depends(get_profissional_atual)) -> Escopo:
    return Escopo(
        id_academia=profissional.usuario.fk_id_academia,
        id_profissional=profissional.id_usuario,
    )


def escopo_aluno(aluno: Aluno = Depends(get_aluno_atual)) -> Escopo:
    # o aluno vê TODAS as aulas da academia dele (sem filtrar por profissional)
    return Escopo(id_academia=aluno.usuario.fk_id_academia)


@router.get("/profissionais/me/aulas", response_model=AulaListaResponse, summary="Listar as minhas aulas (profissional)")
def listar_aulas_profissional(
    filtros: FiltrosAula = Depends(get_filtros_aula),
    escopo: Escopo = Depends(escopo_profissional),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """Aulas em que o profissional logado é o responsável (só visualização)."""
    itens, total = aula_service.listar_aulas(
        db, escopo, filtros.status, None, filtros.tipo_aula,
        filtros.data_de, filtros.data_ate, filtros.busca, filtros.futuras,
        pag.limit, pag.offset,
    )
    return AulaListaResponse(total=total, itens=itens)


@router.get("/profissionais/me/aulas/{id_aula}", response_model=AulaDetalheResponse, summary="Ver uma das minhas aulas (profissional)")
def obter_aula_profissional(
    id_aula: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_profissional),
    db: Session = Depends(get_db),
):
    aula = aula_service.obter_aula(db, escopo, id_aula)
    return AulaDetalheResponse(**aula.model_dump())


@router.get("/alunos/me/aulas", response_model=AulaListaResponse, summary="Listar as aulas da academia (aluno)")
def listar_aulas_aluno(
    fk_id_profissional: Optional[int] = Query(None, ge=1, description="Só aulas deste profissional"),
    filtros: FiltrosAula = Depends(get_filtros_aula),
    escopo: Escopo = Depends(escopo_aluno),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """Todas as aulas da academia do aluno logado (só visualização). Para reservar vaga, use /alunos/me/reservas."""
    itens, total = aula_service.listar_aulas(
        db, escopo, filtros.status, fk_id_profissional, filtros.tipo_aula,
        filtros.data_de, filtros.data_ate, filtros.busca, filtros.futuras,
        pag.limit, pag.offset,
    )
    return AulaListaResponse(total=total, itens=itens)


@router.get("/alunos/me/aulas/{id_aula}", response_model=AulaDetalheResponse, summary="Ver uma aula da academia (aluno)")
def obter_aula_aluno(
    id_aula: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_aluno),
    db: Session = Depends(get_db),
):
    aula = aula_service.obter_aula(db, escopo, id_aula)
    return AulaDetalheResponse(**aula.model_dump())
