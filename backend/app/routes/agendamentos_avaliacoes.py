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
from app.schemas.agendamento_avaliacao import (
    AgendamentoAvaliacaoCadastroResponse,
    AgendamentoAvaliacaoCancelamentoResponse,
    AgendamentoAvaliacaoCreate,
    AgendamentoAvaliacaoDetalheResponse,
    AgendamentoAvaliacaoListaResponse,
    AgendamentoAvaliacaoUpdate,
    AgendamentoAvaliacaoUpdateResponse,
)
from app.schemas.avaliacao_fisica import (
    AvaliacaoFisicaCadastroResponse,
    AvaliacaoFisicaCreate,
    AvaliacaoFisicaDetalheResponse,
    AvaliacaoFisicaUpdate,
    AvaliacaoFisicaUpdateResponse,
)
from app.services import agendamento_avaliacao_service, avaliacao_fisica_service
from app.services.agendamento_avaliacao_service import Escopo as EscopoAgendamento
from app.services.agendamento_avaliacao_service import FiltroStatus
from app.services.avaliacao_fisica_service import Escopo as EscopoFicha

router = APIRouter(tags=["Avaliações Físicas"])


@dataclass
class FiltrosAgendamento:
    status: FiltroStatus
    data_de: Optional[date]
    data_ate: Optional[date]
    futuros: bool


def get_filtros_agendamento(
    status_agend: FiltroStatus = Query("Agendado", alias="status", description="Agendado (padrão), Realizado, Cancelado ou Todos"),
    data_de: Optional[date] = Query(None, description="A partir deste dia (AAAA-MM-DD)"),
    data_ate: Optional[date] = Query(None, description="Até este dia, inclusive (AAAA-MM-DD)"),
    futuros: bool = Query(False, description="Só agendamentos a partir de agora"),
) -> FiltrosAgendamento:
    return FiltrosAgendamento(status_agend, data_de, data_ate, futuros)


def _escopo_agend_academia(academia: Academia = Depends(get_academia_atual)) -> EscopoAgendamento:
    return EscopoAgendamento(id_academia=academia.id_academia)

def _escopo_agend_prof(profissional: Profissional = Depends(get_profissional_atual)) -> EscopoAgendamento:
    return EscopoAgendamento(id_academia=profissional.usuario.fk_id_academia, id_profissional=profissional.id_usuario)

def _escopo_agend_aluno(aluno: Aluno = Depends(get_aluno_atual)) -> EscopoAgendamento:
    return EscopoAgendamento(id_academia=aluno.usuario.fk_id_academia, id_aluno=aluno.id_usuario)


def _escopo_ficha_academia(academia: Academia = Depends(get_academia_atual)) -> EscopoFicha:
    return EscopoFicha(id_academia=academia.id_academia)

def _escopo_ficha_prof(profissional: Profissional = Depends(get_profissional_atual)) -> EscopoFicha:
    return EscopoFicha(id_academia=profissional.usuario.fk_id_academia, id_profissional=profissional.id_usuario)

def _escopo_ficha_aluno(aluno: Aluno = Depends(get_aluno_atual)) -> EscopoFicha:
    return EscopoFicha(id_academia=aluno.usuario.fk_id_academia, id_aluno=aluno.id_usuario)


# =====================================================================
# ACADEMIA
# =====================================================================
@router.post(
    "/agendamentos-avaliacoes",
    response_model=AgendamentoAvaliacaoCadastroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar agendamento (academia)",
)
def agendar_academia(
    dados: AgendamentoAvaliacaoCreate,
    escopo: EscopoAgendamento = Depends(_escopo_agend_academia),
    db: Session = Depends(get_db),
):
    """A academia agenda para o aluno. Envie `fk_id_aluno` e `fk_id_profissional`."""
    agend = agendamento_avaliacao_service.agendar(db, escopo, dados)
    return AgendamentoAvaliacaoCadastroResponse(**agend.model_dump())


@router.get(
    "/agendamentos-avaliacoes",
    response_model=AgendamentoAvaliacaoListaResponse,
    summary="Listar agendamentos (academia)",
)
def listar_agendamentos_academia(
    fk_id_aluno: Optional[int] = Query(None, ge=1),
    fk_id_profissional: Optional[int] = Query(None, ge=1),
    filtros: FiltrosAgendamento = Depends(get_filtros_agendamento),
    escopo: EscopoAgendamento = Depends(_escopo_agend_academia),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    itens, total = agendamento_avaliacao_service.listar_agendamentos(
        db, escopo, filtros.status, fk_id_aluno, fk_id_profissional,
        filtros.data_de, filtros.data_ate, filtros.futuros, pag.limit, pag.offset
    )
    return AgendamentoAvaliacaoListaResponse(total=total, itens=itens)


@router.get(
    "/agendamentos-avaliacoes/{id_agendamento_avaliacao}",
    response_model=AgendamentoAvaliacaoDetalheResponse,
    summary="Ver agendamento (academia)",
)
def obter_agendamento_academia(
    id_agendamento_avaliacao: int = Path(ge=1),
    escopo: EscopoAgendamento = Depends(_escopo_agend_academia),
    db: Session = Depends(get_db),
):
    agend = agendamento_avaliacao_service.obter_agendamento(db, escopo, id_agendamento_avaliacao)
    return AgendamentoAvaliacaoDetalheResponse(**agend.model_dump())


@router.patch(
    "/agendamentos-avaliacoes/{id_agendamento_avaliacao}",
    response_model=AgendamentoAvaliacaoUpdateResponse,
    summary="Reagendar avaliação (academia)",
)
def atualizar_agendamento_academia(
    dados: AgendamentoAvaliacaoUpdate,
    id_agendamento_avaliacao: int = Path(ge=1),
    escopo: EscopoAgendamento = Depends(_escopo_agend_academia),
    db: Session = Depends(get_db),
):
    """A academia atualiza data e/ou o profissional. Agendamento 'Realizado' não muda."""
    agend = agendamento_avaliacao_service.atualizar_agendamento(db, escopo, id_agendamento_avaliacao, dados)
    return AgendamentoAvaliacaoUpdateResponse(**agend.model_dump())


@router.delete(
    "/agendamentos-avaliacoes/{id_agendamento_avaliacao}",
    response_model=AgendamentoAvaliacaoCancelamentoResponse,
    summary="Cancelar agendamento (academia)",
)
def cancelar_agendamento_academia(
    id_agendamento_avaliacao: int = Path(ge=1),
    escopo: EscopoAgendamento = Depends(_escopo_agend_academia),
    db: Session = Depends(get_db),
):
    """Cancela se ainda não foi realizado."""
    agend = agendamento_avaliacao_service.cancelar_agendamento(db, escopo, id_agendamento_avaliacao)
    return AgendamentoAvaliacaoCancelamentoResponse(**agend.model_dump())


@router.get(
    "/agendamentos-avaliacoes/{id_agendamento_avaliacao}/avaliacao",
    response_model=AvaliacaoFisicaDetalheResponse,
    summary="Ver ficha de avaliação (academia)",
)
def obter_ficha_academia(
    id_agendamento_avaliacao: int = Path(ge=1),
    escopo: EscopoFicha = Depends(_escopo_ficha_academia),
    db: Session = Depends(get_db),
):
    ficha = avaliacao_fisica_service.obter_avaliacao(db, escopo, id_agendamento_avaliacao)
    return AvaliacaoFisicaDetalheResponse(**ficha.model_dump())


# =====================================================================
# PROFISSIONAL
# =====================================================================
@router.get(
    "/profissionais/me/agendamentos",
    response_model=AgendamentoAvaliacaoListaResponse,
    summary="Listar agendamentos comigo (profissional)",
)
def listar_agendamentos_prof(
    fk_id_aluno: Optional[int] = Query(None, ge=1),
    filtros: FiltrosAgendamento = Depends(get_filtros_agendamento),
    escopo: EscopoAgendamento = Depends(_escopo_agend_prof),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    itens, total = agendamento_avaliacao_service.listar_agendamentos(
        db, escopo, filtros.status, fk_id_aluno, None,
        filtros.data_de, filtros.data_ate, filtros.futuros, pag.limit, pag.offset
    )
    return AgendamentoAvaliacaoListaResponse(total=total, itens=itens)


@router.get(
    "/profissionais/me/agendamentos/{id_agendamento}",
    response_model=AgendamentoAvaliacaoDetalheResponse,
    summary="Ver agendamento (profissional)",
)
def obter_agendamento_prof(
    id_agendamento: int = Path(ge=1),
    escopo: EscopoAgendamento = Depends(_escopo_agend_prof),
    db: Session = Depends(get_db),
):
    agend = agendamento_avaliacao_service.obter_agendamento(db, escopo, id_agendamento)
    return AgendamentoAvaliacaoDetalheResponse(**agend.model_dump())


@router.delete(
    "/profissionais/me/agendamentos/{id_agendamento}",
    response_model=AgendamentoAvaliacaoCancelamentoResponse,
    summary="Cancelar agendamento (profissional)",
)
def cancelar_agendamento_prof(
    id_agendamento: int = Path(ge=1),
    escopo: EscopoAgendamento = Depends(_escopo_agend_prof),
    db: Session = Depends(get_db),
):
    agend = agendamento_avaliacao_service.cancelar_agendamento(db, escopo, id_agendamento)
    return AgendamentoAvaliacaoCancelamentoResponse(**agend.model_dump())


@router.post(
    "/profissionais/me/agendamentos/{id_agendamento}/avaliacao",
    response_model=AvaliacaoFisicaCadastroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Preencher ficha de avaliação (profissional)",
)
def preencher_ficha_prof(
    dados: AvaliacaoFisicaCreate,
    id_agendamento: int = Path(ge=1),
    escopo: EscopoFicha = Depends(_escopo_ficha_prof),
    db: Session = Depends(get_db),
):
    """Ao preencher a ficha, o agendamento correspondente é marcado como Realizado."""
    ficha = avaliacao_fisica_service.preencher_avaliacao(db, escopo, id_agendamento, dados)
    return AvaliacaoFisicaCadastroResponse(**ficha.model_dump())


@router.get(
    "/profissionais/me/agendamentos/{id_agendamento}/avaliacao",
    response_model=AvaliacaoFisicaDetalheResponse,
    summary="Ver ficha preenchida (profissional)",
)
def obter_ficha_prof(
    id_agendamento: int = Path(ge=1),
    escopo: EscopoFicha = Depends(_escopo_ficha_prof),
    db: Session = Depends(get_db),
):
    ficha = avaliacao_fisica_service.obter_avaliacao(db, escopo, id_agendamento)
    return AvaliacaoFisicaDetalheResponse(**ficha.model_dump())


@router.patch(
    "/profissionais/me/agendamentos/{id_agendamento}/avaliacao",
    response_model=AvaliacaoFisicaUpdateResponse,
    summary="Editar ficha preenchida (profissional)",
)
def atualizar_ficha_prof(
    dados: AvaliacaoFisicaUpdate,
    id_agendamento: int = Path(ge=1),
    escopo: EscopoFicha = Depends(_escopo_ficha_prof),
    db: Session = Depends(get_db),
):
    ficha = avaliacao_fisica_service.atualizar_avaliacao(db, escopo, id_agendamento, dados)
    return AvaliacaoFisicaUpdateResponse(**ficha.model_dump())


# =====================================================================
# ALUNO
# =====================================================================
@router.post(
    "/alunos/me/agendamentos",
    response_model=AgendamentoAvaliacaoCadastroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar agendamento (aluno)",
)
def agendar_aluno(
    dados: AgendamentoAvaliacaoCreate,
    escopo: EscopoAgendamento = Depends(_escopo_agend_aluno),
    db: Session = Depends(get_db),
):
    """
    O aluno logado agenda uma avaliação com um profissional.
    O `fk_id_aluno` enviado no corpo é ignorado, será usado o do token.
    """
    agend = agendamento_avaliacao_service.agendar(db, escopo, dados)
    return AgendamentoAvaliacaoCadastroResponse(**agend.model_dump())


@router.get(
    "/alunos/me/agendamentos",
    response_model=AgendamentoAvaliacaoListaResponse,
    summary="Listar meus agendamentos (aluno)",
)
def listar_agendamentos_aluno(
    fk_id_profissional: Optional[int] = Query(None, ge=1),
    filtros: FiltrosAgendamento = Depends(get_filtros_agendamento),
    escopo: EscopoAgendamento = Depends(_escopo_agend_aluno),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    itens, total = agendamento_avaliacao_service.listar_agendamentos(
        db, escopo, filtros.status, None, fk_id_profissional,
        filtros.data_de, filtros.data_ate, filtros.futuros, pag.limit, pag.offset
    )
    return AgendamentoAvaliacaoListaResponse(total=total, itens=itens)


@router.get(
    "/alunos/me/agendamentos/{id_agendamento}",
    response_model=AgendamentoAvaliacaoDetalheResponse,
    summary="Ver meu agendamento (aluno)",
)
def obter_agendamento_aluno(
    id_agendamento: int = Path(ge=1),
    escopo: EscopoAgendamento = Depends(_escopo_agend_aluno),
    db: Session = Depends(get_db),
):
    agend = agendamento_avaliacao_service.obter_agendamento(db, escopo, id_agendamento)
    return AgendamentoAvaliacaoDetalheResponse(**agend.model_dump())


@router.delete(
    "/alunos/me/agendamentos/{id_agendamento}",
    response_model=AgendamentoAvaliacaoCancelamentoResponse,
    summary="Cancelar meu agendamento (aluno)",
)
def cancelar_agendamento_aluno(
    id_agendamento: int = Path(ge=1),
    escopo: EscopoAgendamento = Depends(_escopo_agend_aluno),
    db: Session = Depends(get_db),
):
    agend = agendamento_avaliacao_service.cancelar_agendamento(db, escopo, id_agendamento)
    return AgendamentoAvaliacaoCancelamentoResponse(**agend.model_dump())


@router.get(
    "/alunos/me/agendamentos/{id_agendamento}/avaliacao",
    response_model=AvaliacaoFisicaDetalheResponse,
    summary="Ver minha ficha (aluno)",
)
def obter_ficha_aluno(
    id_agendamento: int = Path(ge=1),
    escopo: EscopoFicha = Depends(_escopo_ficha_aluno),
    db: Session = Depends(get_db),
):
    """O aluno apenas visualiza a ficha depois de preenchida pelo profissional."""
    ficha = avaliacao_fisica_service.obter_avaliacao(db, escopo, id_agendamento)
    return AvaliacaoFisicaDetalheResponse(**ficha.model_dump())
