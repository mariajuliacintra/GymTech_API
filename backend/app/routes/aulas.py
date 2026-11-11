"""
Aulas, visão da ACADEMIA (token de academia). É a única que cadastra e altera.

    POST   /aulas                 cadastrar
    GET    /aulas                 listar
    GET    /aulas/{id_aula}       ver uma
    PATCH  /aulas/{id_aula}       atualizar (nome, data/hora, capacidade, profissional)
    DELETE /aulas/{id_aula}       cancelar (status 'Cancelada'; nada é apagado)

Profissionais e alunos só visualizam: veja minhas_aulas.py.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import Paginacao, get_academia_atual, get_paginacao
from app.database import get_db
from app.models import Academia
from app.schemas.aula import (
    AulaCadastroResponse,
    AulaCancelamentoResponse,
    AulaCreate,
    AulaDetalheResponse,
    AulaListaResponse,
    AulaUpdate,
    AulaUpdateResponse,
)
from app.services import aula_service
from app.services.aula_service import Escopo, FiltroStatus

router = APIRouter(prefix="/aulas", tags=["Aulas"])


@dataclass
class FiltrosAula:
    status: FiltroStatus
    data_de: Optional[date]
    data_ate: Optional[date]
    busca: Optional[str]
    futuras: bool


def get_filtros_aula(
    status_aula: FiltroStatus = Query("Ativa", alias="status", description="Ativa (padrão), Cancelada ou Todas"),
    data_de: Optional[date] = Query(None, description="Aulas a partir deste dia (AAAA-MM-DD)"),
    data_ate: Optional[date] = Query(None, description="Aulas até este dia, inclusive (AAAA-MM-DD)"),
    busca: Optional[str] = Query(None, min_length=1, max_length=100, description="Parte do nome da aula"),
    futuras: bool = Query(False, description="Só aulas que ainda não aconteceram"),
) -> FiltrosAula:
    """Filtros comuns às listagens de aula (academia, profissional e aluno)."""
    return FiltrosAula(status_aula, data_de, data_ate, busca, futuras)


def escopo_academia(academia: Academia = Depends(get_academia_atual)) -> Escopo:
    return Escopo(id_academia=academia.id_academia)


@router.post(
    "",
    response_model=AulaCadastroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar aula",
)
def cadastrar_aula(
    dados: AulaCreate,
    escopo: Escopo = Depends(escopo_academia),
    db: Session = Depends(get_db),
):
    """
    Cadastra uma aula na academia logada.

    - `fk_id_profissional`: `id_usuario` de um profissional **ativo da academia**.
    - `data_horario`: início da aula, **no futuro**, no horário da academia
      (`2026-11-20T18:00:00`). Se vier com fuso (`...Z`), é convertido.
    - O mesmo profissional não pode ter duas aulas no mesmo horário (409).
    - `capacidade_maxima`: de 1 a 500.
    """
    aula = aula_service.cadastrar_aula(db, escopo, dados)
    return AulaCadastroResponse(**aula.model_dump())


@router.get("", response_model=AulaListaResponse, summary="Listar aulas")
def listar_aulas(
    fk_id_profissional: Optional[int] = Query(None, ge=1, description="Só aulas deste profissional"),
    filtros: FiltrosAula = Depends(get_filtros_aula),
    escopo: Escopo = Depends(escopo_academia),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """Aulas da academia, da mais próxima para a mais distante."""
    itens, total = aula_service.listar_aulas(
        db, escopo, filtros.status, fk_id_profissional,
        filtros.data_de, filtros.data_ate, filtros.busca, filtros.futuras,
        pag.limit, pag.offset,
    )
    return AulaListaResponse(total=total, itens=itens)


@router.get("/{id_aula}", response_model=AulaDetalheResponse, summary="Ver uma aula")
def obter_aula(
    id_aula: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_academia),
    db: Session = Depends(get_db),
):
    aula = aula_service.obter_aula(db, escopo, id_aula)
    return AulaDetalheResponse(**aula.model_dump())


@router.patch("/{id_aula}", response_model=AulaUpdateResponse, summary="Atualizar aula")
def atualizar_aula(
    dados: AulaUpdate,
    id_aula: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_academia),
    db: Session = Depends(get_db),
):
    """
    Atualiza só os campos enviados (`nome_aula`, `data_horario`,
    `capacidade_maxima`, `fk_id_profissional`; nenhum aceita null). As mesmas
    regras do cadastro valem. Aula cancelada ou que já aconteceu não muda (409).
    """
    aula = aula_service.atualizar_aula(db, escopo, id_aula, dados)
    return AulaUpdateResponse(**aula.model_dump())


@router.delete("/{id_aula}", response_model=AulaCancelamentoResponse, summary="Cancelar aula")
def cancelar_aula(
    id_aula: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_academia),
    db: Session = Depends(get_db),
):
    """**Cancela** a aula (status 'Cancelada'): some da listagem padrão, mas continua no banco."""
    aula = aula_service.cancelar_aula(db, escopo, id_aula)
    return AulaCancelamentoResponse(**aula.model_dump())
