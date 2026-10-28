"""
Treinos, visão da ACADEMIA (token de academia): alcança todos os treinos dela.

    POST   /treinos                 cadastrar (escolhe aluno e profissional)
    GET    /treinos                 listar
    GET    /treinos/{id_treino}     ver um
    PATCH  /treinos/{id_treino}     atualizar (título, data, profissional)
    DELETE /treinos/{id_treino}     cancelar (status 'Cancelado'; nada é apagado)

Profissionais e alunos usam as rotas de meus_treinos.py.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import Paginacao, get_academia_atual, get_paginacao
from app.database import get_db
from app.models import Academia
from app.schemas.treino import (
    TreinoCadastroResponse,
    TreinoCancelamentoResponse,
    TreinoCreate,
    TreinoDetalheResponse,
    TreinoListaResponse,
    TreinoUpdate,
    TreinoUpdateResponse,
)
from app.services import treino_service
from app.services.treino_service import Escopo, FiltroStatus

router = APIRouter(prefix="/treinos", tags=["Treinos"])


@dataclass
class FiltrosTreino:
    status: FiltroStatus
    data_de: Optional[date]
    data_ate: Optional[date]
    busca: Optional[str]


def get_filtros_treino(
    status_treino: FiltroStatus = Query("Ativo", alias="status", description="Ativo (padrão), Cancelado ou Todos"),
    data_de: Optional[date] = Query(None, description="Data programada a partir de (AAAA-MM-DD)"),
    data_ate: Optional[date] = Query(None, description="Data programada até (AAAA-MM-DD)"),
    busca: Optional[str] = Query(None, min_length=1, max_length=100, description="Parte do título do treino"),
) -> FiltrosTreino:
    """Filtros comuns às listagens de treino (academia, profissional e aluno)."""
    return FiltrosTreino(status_treino, data_de, data_ate, busca)


def escopo_academia(academia: Academia = Depends(get_academia_atual)) -> Escopo:
    return Escopo(id_academia=academia.id_academia)


@router.post(
    "",
    response_model=TreinoCadastroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar treino",
)
def cadastrar_treino(
    dados: TreinoCreate,
    escopo: Escopo = Depends(escopo_academia),
    db: Session = Depends(get_db),
):
    """
    Cadastra um treino ligando um **aluno** e um **profissional** (os dois pelo
    `id_usuario`, e os dois da academia logada e ativos). `data_programada` é
    opcional e não pode ser anterior a hoje.
    """
    treino = treino_service.cadastrar_treino(
        db, escopo, dados.fk_id_aluno, dados.fk_id_profissional,
        dados.titulo_treino, dados.data_programada,
    )
    return TreinoCadastroResponse(**treino.model_dump())


@router.get("", response_model=TreinoListaResponse, summary="Listar treinos")
def listar_treinos(
    fk_id_aluno: Optional[int] = Query(None, ge=1, description="Só treinos deste aluno"),
    fk_id_profissional: Optional[int] = Query(None, ge=1, description="Só treinos deste profissional"),
    filtros: FiltrosTreino = Depends(get_filtros_treino),
    escopo: Escopo = Depends(escopo_academia),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """Treinos da academia, do mais próximo para o mais distante (sem data por último)."""
    itens, total = treino_service.listar_treinos(
        db, escopo, filtros.status, fk_id_aluno, fk_id_profissional,
        filtros.data_de, filtros.data_ate, filtros.busca, pag.limit, pag.offset,
    )
    return TreinoListaResponse(total=total, itens=itens)


@router.get("/{id_treino}", response_model=TreinoDetalheResponse, summary="Ver um treino")
def obter_treino(
    id_treino: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_academia),
    db: Session = Depends(get_db),
):
    treino = treino_service.obter_treino(db, escopo, id_treino)
    return TreinoDetalheResponse(**treino.model_dump())


@router.patch("/{id_treino}", response_model=TreinoUpdateResponse, summary="Atualizar treino")
def atualizar_treino(
    dados: TreinoUpdate,
    id_treino: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_academia),
    db: Session = Depends(get_db),
):
    """
    Atualiza só os campos enviados: `titulo_treino`, `data_programada` (null
    limpa) e `fk_id_profissional`. O aluno não muda (seria outro treino).
    Treino cancelado não pode ser alterado (409).
    """
    treino = treino_service.atualizar_treino(db, escopo, id_treino, dados)
    return TreinoUpdateResponse(**treino.model_dump())


@router.delete("/{id_treino}", response_model=TreinoCancelamentoResponse, summary="Cancelar treino")
def cancelar_treino(
    id_treino: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_academia),
    db: Session = Depends(get_db),
):
    """**Cancela** o treino (status 'Cancelado'): ele some da listagem padrão, mas continua no banco."""
    treino = treino_service.cancelar_treino(db, escopo, id_treino)
    return TreinoCancelamentoResponse(**treino.model_dump())
