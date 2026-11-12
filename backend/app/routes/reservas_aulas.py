"""
Reservas de aula (reserva_aula), separadas por perfil:

Academia (vê todas da academia e pode cancelar qualquer uma):
    GET    /reservas-aulas                      listar
    GET    /reservas-aulas/{id_reserva_aula}    ver uma
    DELETE /reservas-aulas/{id_reserva_aula}    cancelar (libera a vaga)

Profissional (vê a turma reservada nas aulas dele, somente leitura):
    GET    /profissionais/me/reservas-aulas                      listar
    GET    /profissionais/me/reservas-aulas/{id_reserva_aula}    ver uma

Aluno (realiza, visualiza e cancela as próprias reservas):
    POST   /alunos/me/reservas                      reservar vaga em uma aula
    GET    /alunos/me/reservas                      listar minhas reservas
    GET    /alunos/me/reservas/{id_reserva_aula}    ver uma reserva minha
    DELETE /alunos/me/reservas/{id_reserva_aula}    cancelar minha reserva (libera a vaga)
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import (
    Paginacao,
    get_academia_atual,
    get_aluno_atual,
    get_paginacao,
    get_profissional_atual,
)
from app.database import get_db
from app.models import Academia, Aluno, Profissional
from app.schemas.reserva_aula import (
    ReservaAulaCadastroResponse,
    ReservaAulaCancelamentoResponse,
    ReservaAulaCreate,
    ReservaAulaDetalheResponse,
    ReservaAulaListaResponse,
)
from app.services import reserva_aula_service
from app.services.reserva_aula_service import Escopo, FiltroStatus

router = APIRouter(tags=["Reservas de aula"])


@dataclass
class FiltrosReserva:
    status: FiltroStatus
    fk_id_aula: Optional[int]
    data_de: Optional[date]
    data_ate: Optional[date]
    futuras: bool


def get_filtros_reserva(
    status_reserva: FiltroStatus = Query("Confirmado", alias="status", description="Confirmado (padrão), Cancelado ou Todas"),
    fk_id_aula: Optional[int] = Query(None, ge=1, description="Filtra por uma aula específica"),
    data_de: Optional[date] = Query(None, description="Aulas a partir deste dia (AAAA-MM-DD)"),
    data_ate: Optional[date] = Query(None, description="Aulas até este dia, inclusive (AAAA-MM-DD)"),
    futuras: bool = Query(False, description="Só reservas de aulas que ainda não aconteceram"),
) -> FiltrosReserva:
    return FiltrosReserva(status_reserva, fk_id_aula, data_de, data_ate, futuras)


def escopo_academia(academia: Academia = Depends(get_academia_atual)) -> Escopo:
    return Escopo(id_academia=academia.id_academia)


def escopo_profissional(profissional: Profissional = Depends(get_profissional_atual)) -> Escopo:
    return Escopo(
        id_academia=profissional.usuario.fk_id_academia,
        id_profissional=profissional.id_usuario,
    )


def escopo_aluno(aluno: Aluno = Depends(get_aluno_atual)) -> Escopo:
    return Escopo(
        id_academia=aluno.usuario.fk_id_academia,
        id_aluno=aluno.id_usuario,
    )


# -------------------------------------------------------------------- ACADEMIA
@router.get(
    "/reservas-aulas",
    response_model=ReservaAulaListaResponse,
    summary="Listar reservas da academia (academia)",
)
def listar_reservas_academia(
    fk_id_aluno: Optional[int] = Query(None, ge=1, description="Só reservas deste aluno"),
    filtros: FiltrosReserva = Depends(get_filtros_reserva),
    escopo: Escopo = Depends(escopo_academia),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """Lista todas as reservas de aulas da academia logada."""
    itens, total = reserva_aula_service.listar_reservas(
        db, escopo, filtros.status, filtros.fk_id_aula, fk_id_aluno,
        filtros.data_de, filtros.data_ate, filtros.futuras,
        pag.limit, pag.offset,
    )
    return ReservaAulaListaResponse(total=total, itens=itens)


@router.get(
    "/reservas-aulas/{id_reserva_aula}",
    response_model=ReservaAulaDetalheResponse,
    summary="Ver uma reserva (academia)",
)
def obter_reserva_academia(
    id_reserva_aula: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_academia),
    db: Session = Depends(get_db),
):
    reserva = reserva_aula_service.obter_reserva(db, escopo, id_reserva_aula)
    return ReservaAulaDetalheResponse(**reserva.model_dump())


@router.delete(
    "/reservas-aulas/{id_reserva_aula}",
    response_model=ReservaAulaCancelamentoResponse,
    summary="Cancelar reserva de um aluno (academia)",
)
def cancelar_reserva_academia(
    id_reserva_aula: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_academia),
    db: Session = Depends(get_db),
):
    """A academia cancela a reserva de qualquer aluno em suas aulas, liberando a vaga."""
    reserva = reserva_aula_service.cancelar_reserva(db, escopo, id_reserva_aula)
    return ReservaAulaCancelamentoResponse(**reserva.model_dump())


# ---------------------------------------------------------------- PROFISSIONAL
@router.get(
    "/profissionais/me/reservas-aulas",
    response_model=ReservaAulaListaResponse,
    summary="Listar alunos reservados nas minhas aulas (profissional)",
)
def listar_reservas_profissional(
    filtros: FiltrosReserva = Depends(get_filtros_reserva),
    escopo: Escopo = Depends(escopo_profissional),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """Lista os alunos reservados nas aulas do profissional logado (somente leitura)."""
    itens, total = reserva_aula_service.listar_reservas(
        db, escopo, filtros.status, filtros.fk_id_aula, None,
        filtros.data_de, filtros.data_ate, filtros.futuras,
        pag.limit, pag.offset,
    )
    return ReservaAulaListaResponse(total=total, itens=itens)


@router.get(
    "/profissionais/me/reservas-aulas/{id_reserva_aula}",
    response_model=ReservaAulaDetalheResponse,
    summary="Ver detalhe de uma reserva na minha aula (profissional)",
)
def obter_reserva_profissional(
    id_reserva_aula: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_profissional),
    db: Session = Depends(get_db),
):
    reserva = reserva_aula_service.obter_reserva(db, escopo, id_reserva_aula)
    return ReservaAulaDetalheResponse(**reserva.model_dump())


# ----------------------------------------------------------------------- ALUNO
@router.post(
    "/alunos/me/reservas",
    response_model=ReservaAulaCadastroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reservar vaga em uma aula (aluno)",
)
def reservar_aula(
    dados: ReservaAulaCreate,
    escopo: Escopo = Depends(escopo_aluno),
    db: Session = Depends(get_db),
):
    """
    O aluno logado reserva uma vaga em uma aula ativa e futura da sua academia.

    - Se a aula estiver lotada (`vagas_disponiveis == 0`), retorna **409**.
    - Se o aluno já tiver reserva confirmada na mesma aula ou em outra no mesmo
      horário, retorna **409**.
    - Se o aluno reservou antes e cancelou, pode reservar novamente (**201**).
    """
    reserva = reserva_aula_service.reservar_aula(db, escopo, dados.fk_id_aula)
    return ReservaAulaCadastroResponse(**reserva.model_dump())


@router.get(
    "/alunos/me/reservas",
    response_model=ReservaAulaListaResponse,
    summary="Listar minhas reservas (aluno)",
)
def listar_reservas_aluno(
    filtros: FiltrosReserva = Depends(get_filtros_reserva),
    escopo: Escopo = Depends(escopo_aluno),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """Lista as reservas do aluno logado."""
    itens, total = reserva_aula_service.listar_reservas(
        db, escopo, filtros.status, filtros.fk_id_aula, None,
        filtros.data_de, filtros.data_ate, filtros.futuras,
        pag.limit, pag.offset,
    )
    return ReservaAulaListaResponse(total=total, itens=itens)


@router.get(
    "/alunos/me/reservas/{id_reserva_aula}",
    response_model=ReservaAulaDetalheResponse,
    summary="Ver uma reserva minha (aluno)",
)
def obter_reserva_aluno(
    id_reserva_aula: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_aluno),
    db: Session = Depends(get_db),
):
    reserva = reserva_aula_service.obter_reserva(db, escopo, id_reserva_aula)
    return ReservaAulaDetalheResponse(**reserva.model_dump())


@router.delete(
    "/alunos/me/reservas/{id_reserva_aula}",
    response_model=ReservaAulaCancelamentoResponse,
    summary="Cancelar minha reserva (aluno)",
)
def cancelar_reserva_aluno(
    id_reserva_aula: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_aluno),
    db: Session = Depends(get_db),
):
    """O aluno cancela sua própria reserva (status 'Cancelado'), liberando a vaga."""
    reserva = reserva_aula_service.cancelar_reserva(db, escopo, id_reserva_aula)
    return ReservaAulaCancelamentoResponse(**reserva.model_dump())
