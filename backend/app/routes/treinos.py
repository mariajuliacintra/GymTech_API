"""
Treinos, visão da ACADEMIA (token de academia): alcança todos os treinos dela.

    POST   /treinos                      cadastrar (escolhe aluno e profissional)
    POST   /treinos/notificar-proximos   disparar lembretes por e-mail para treinos próximos
    GET    /treinos                      listar
    GET    /treinos/{id_treino}          ver um
    PATCH  /treinos/{id_treino}          atualizar (título, data, profissional, exercícios)
    DELETE /treinos/{id_treino}          cancelar (status 'Cancelado'; nada é apagado)

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
    NotificacaoTreinoExecucaoResponse,
    TreinoCadastroResponse,
    TreinoCancelamentoResponse,
    TreinoCreate,
    TreinoDetalheResponse,
    TreinoListaResponse,
    TreinoUpdate,
    TreinoUpdateResponse,
)
from app.services import notificacao_service, treino_service
from app.services.treino_service import Escopo, FiltroStatus

router = APIRouter(prefix="/treinos", tags=["Treinos"])


@dataclass
class FiltrosTreino:
    status: FiltroStatus
    data_de: Optional[date]
    data_ate: Optional[date]
    busca: Optional[str]
    incluir_itens: bool


def get_filtros_treino(
    status_treino: FiltroStatus = Query("Ativo", alias="status", description="Ativo (padrão), Cancelado ou Todas"),
    data_de: Optional[date] = Query(None, description="Data programada a partir de (AAAA-MM-DD)"),
    data_ate: Optional[date] = Query(None, description="Data programada até (AAAA-MM-DD)"),
    busca: Optional[str] = Query(None, min_length=1, max_length=100, description="Parte do título do treino"),
    incluir_itens: bool = Query(False, description="Traz também os exercícios de cada treino"),
) -> FiltrosTreino:
    """Filtros comuns às listagens de treino (academia, profissional e aluno)."""
    return FiltrosTreino(status_treino, data_de, data_ate, busca, incluir_itens)


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

    `itens` é obrigatório (ao menos 1): cada item traz `fk_id_exercicio` (da
    mesma academia, sem repetir), `series`, `repeticoes` e, opcionalmente,
    `carga_sugerida` e `tempo_descanso` (HH:MM:SS). A ordem da lista é a ordem
    dos exercícios no treino. Treino e itens são salvos juntos, ou nenhum.
    """
    treino = treino_service.cadastrar_treino(
        db, escopo, dados.fk_id_aluno, dados.fk_id_profissional,
        dados.titulo_treino, dados.data_programada, dados.itens,
    )
    return TreinoCadastroResponse(**treino.model_dump())


@router.post(
    "/notificar-proximos",
    response_model=NotificacaoTreinoExecucaoResponse,
    summary="Disparar notificações de treinos próximos (academia)",
)
def notificar_treinos_proximos(
    dias_antecedencia: Optional[int] = Query(
        None,
        ge=0,
        le=30,
        description="Janela em dias à frente (padrão: NOTIFICACAO_TREINO_DIAS_ANTECEDENCIA do .env)",
    ),
    escopo: Escopo = Depends(escopo_academia),
    db: Session = Depends(get_db),
):
    """
    Executa sob demanda o envio de e-mails de lembrete para os alunos da
    academia logada que têm treinos ativos programados nos próximos dias
    e ainda não foram notificados (`notificado = false`).

    Além desta rota manual, o agendador automático executa esta mesma
    rotina todos os dias no horário configurado no `.env` (padrão: 08:00).
    """
    return notificacao_service.processar_lembretes_treinos(
        db,
        id_academia=escopo.id_academia,
        dias_antecedencia=dias_antecedencia,
    )


@router.get("", response_model=TreinoListaResponse, summary="Listar treinos")
def listar_treinos(
    fk_id_aluno: Optional[int] = Query(None, ge=1, description="Só treinos deste aluno"),
    fk_id_profissional: Optional[int] = Query(None, ge=1, description="Só treinos deste profissional"),
    filtros: FiltrosTreino = Depends(get_filtros_treino),
    escopo: Escopo = Depends(escopo_academia),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """
    Treinos da academia, do mais próximo para o mais distante (sem data por último).
    Cada treino traz `quantidade_exercicios`; `itens` só vem preenchido com `?incluir_itens=true`.
    """
    itens, total = treino_service.listar_treinos(
        db, escopo, filtros.status, fk_id_aluno, fk_id_profissional,
        filtros.data_de, filtros.data_ate, filtros.busca, filtros.incluir_itens,
        pag.limit, pag.offset,
    )
    return TreinoListaResponse(total=total, itens=itens)


@router.get("/historico", response_model=TreinoListaResponse, summary="Histórico de treinos (academia)")
def historico_treinos(
    fk_id_aluno: Optional[int] = Query(None, ge=1, description="Só histórico deste aluno"),
    fk_id_profissional: Optional[int] = Query(None, ge=1, description="Só histórico deste profissional"),
    filtros: FiltrosTreino = Depends(get_filtros_treino),
    escopo: Escopo = Depends(escopo_academia),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """Histórico geral da academia (treinos passados)."""
    itens, total = treino_service.listar_treinos(
        db, escopo, filtros.status, fk_id_aluno, fk_id_profissional,
        filtros.data_de, filtros.data_ate, filtros.busca, filtros.incluir_itens,
        historico=True,
        limit=pag.limit, offset=pag.offset,
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
    limpa), `fk_id_profissional` e `itens`. O aluno não muda (seria outro treino).

    `itens` é opcional: se enviado, a lista de exercícios é **substituída por
    inteira**, na ordem enviada (e os `id_item_treino` mudam); se não, os
    exercícios ficam como estão. Treino cancelado não pode ser alterado (409).
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
