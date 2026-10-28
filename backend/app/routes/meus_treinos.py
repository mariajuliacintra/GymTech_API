"""
Treinos, visão do PROFISSIONAL e do ALUNO (sempre os do próprio usuário logado).

Profissional (alcança só os treinos em que ele é o profissional):
    POST   /profissionais/me/treinos                cadastrar (para um aluno da academia)
    GET    /profissionais/me/treinos                listar
    GET    /profissionais/me/treinos/{id_treino}    ver um
    PATCH  /profissionais/me/treinos/{id_treino}    atualizar título/data
    DELETE /profissionais/me/treinos/{id_treino}    cancelar

Aluno (só visualiza os treinos dele):
    GET    /alunos/me/treinos                       listar
    GET    /alunos/me/treinos/{id_treino}           ver um

Quem é o profissional/aluno vem do token, nunca de um id enviado.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import Paginacao, get_aluno_atual, get_paginacao, get_profissional_atual
from app.database import get_db
from app.models import Aluno, Profissional
from app.routes.treinos import FiltrosTreino, get_filtros_treino
from app.schemas.treino import (
    TreinoCadastroResponse,
    TreinoCancelamentoResponse,
    TreinoCreateProfissional,
    TreinoDetalheResponse,
    TreinoListaResponse,
    TreinoUpdateProfissional,
    TreinoUpdateResponse,
)
from app.services import treino_service
from app.services.treino_service import Escopo

router = APIRouter(tags=["Meus treinos"])


def escopo_profissional(profissional: Profissional = Depends(get_profissional_atual)) -> Escopo:
    return Escopo(
        id_academia=profissional.usuario.fk_id_academia,
        id_profissional=profissional.id_usuario,
    )


def escopo_aluno(aluno: Aluno = Depends(get_aluno_atual)) -> Escopo:
    return Escopo(id_academia=aluno.usuario.fk_id_academia, id_aluno=aluno.id_usuario)


# ----------------------------------------------------------------- profissional
@router.post(
    "/profissionais/me/treinos",
    response_model=TreinoCadastroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar treino (profissional)",
)
def cadastrar_treino_profissional(
    dados: TreinoCreateProfissional,
    escopo: Escopo = Depends(escopo_profissional),
    db: Session = Depends(get_db),
):
    """
    O profissional logado cadastra um treino para um **aluno da mesma academia**
    (ativo). O profissional responsável é ele mesmo: `fk_id_profissional` não se envia.
    """
    treino = treino_service.cadastrar_treino(
        db, escopo, dados.fk_id_aluno, escopo.id_profissional,
        dados.titulo_treino, dados.data_programada,
    )
    return TreinoCadastroResponse(**treino.model_dump())


@router.get(
    "/profissionais/me/treinos",
    response_model=TreinoListaResponse,
    summary="Listar os meus treinos (profissional)",
)
def listar_treinos_profissional(
    fk_id_aluno: Optional[int] = Query(None, ge=1, description="Só treinos deste aluno"),
    filtros: FiltrosTreino = Depends(get_filtros_treino),
    escopo: Escopo = Depends(escopo_profissional),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """Treinos em que o profissional logado é o responsável."""
    itens, total = treino_service.listar_treinos(
        db, escopo, filtros.status, fk_id_aluno, None,
        filtros.data_de, filtros.data_ate, filtros.busca, pag.limit, pag.offset,
    )
    return TreinoListaResponse(total=total, itens=itens)


@router.get(
    "/profissionais/me/treinos/{id_treino}",
    response_model=TreinoDetalheResponse,
    summary="Ver um dos meus treinos (profissional)",
)
def obter_treino_profissional(
    id_treino: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_profissional),
    db: Session = Depends(get_db),
):
    treino = treino_service.obter_treino(db, escopo, id_treino)
    return TreinoDetalheResponse(**treino.model_dump())


@router.patch(
    "/profissionais/me/treinos/{id_treino}",
    response_model=TreinoUpdateResponse,
    summary="Atualizar um dos meus treinos (profissional)",
)
def atualizar_treino_profissional(
    dados: TreinoUpdateProfissional,
    id_treino: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_profissional),
    db: Session = Depends(get_db),
):
    """Atualiza `titulo_treino` e/ou `data_programada` (null limpa). Treino cancelado não muda (409)."""
    treino = treino_service.atualizar_treino(db, escopo, id_treino, dados)
    return TreinoUpdateResponse(**treino.model_dump())


@router.delete(
    "/profissionais/me/treinos/{id_treino}",
    response_model=TreinoCancelamentoResponse,
    summary="Cancelar um dos meus treinos (profissional)",
)
def cancelar_treino_profissional(
    id_treino: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_profissional),
    db: Session = Depends(get_db),
):
    treino = treino_service.cancelar_treino(db, escopo, id_treino)
    return TreinoCancelamentoResponse(**treino.model_dump())


# ----------------------------------------------------------------------- aluno
@router.get(
    "/alunos/me/treinos",
    response_model=TreinoListaResponse,
    summary="Listar os meus treinos (aluno)",
)
def listar_treinos_aluno(
    filtros: FiltrosTreino = Depends(get_filtros_treino),
    escopo: Escopo = Depends(escopo_aluno),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """Treinos do aluno logado (só visualização), do mais próximo para o mais distante."""
    itens, total = treino_service.listar_treinos(
        db, escopo, filtros.status, None, None,
        filtros.data_de, filtros.data_ate, filtros.busca, pag.limit, pag.offset,
    )
    return TreinoListaResponse(total=total, itens=itens)


@router.get(
    "/alunos/me/treinos/{id_treino}",
    response_model=TreinoDetalheResponse,
    summary="Ver um dos meus treinos (aluno)",
)
def obter_treino_aluno(
    id_treino: int = Path(ge=1),
    escopo: Escopo = Depends(escopo_aluno),
    db: Session = Depends(get_db),
):
    treino = treino_service.obter_treino(db, escopo, id_treino)
    return TreinoDetalheResponse(**treino.model_dump())
