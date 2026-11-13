"""
Regras da Avaliação Física.

- Somente o PROFISSIONAL cria (preenche) e edita a ficha (avaliacao_fisica).
- O profissional, o aluno e a academia podem VISUALIZAR (cada um com seu escopo).
- Para criar a ficha, o agendamento NÃO pode estar Cancelado nem já Realizado,
  e a data_horario do agendamento pode ser futura ou passada (não bloqueamos
  se o aluno chegar antes ou for preenchido dias depois).
- Ao criar a ficha, o status do agendamento vira 'Realizado' automaticamente.
"""
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflitoError, DadoInvalidoError, NaoEncontradoError
from app.core.tempo import agora_local
from app.models import AgendamentoAvaliacao, AvaliacaoFisica
from app.schemas.avaliacao_fisica import (
    AvaliacaoFisicaCreate,
    AvaliacaoFisicaResponse,
    AvaliacaoFisicaUpdate,
)
from app.services.agendamento_avaliacao_service import Escopo as EscopoAgendamento
from app.services.agendamento_avaliacao_service import _buscar as buscar_agendamento
from app.services.agendamento_avaliacao_service import _travar as travar_agendamento

_CHECKS_FICHA = ("ck_avaliacao_peso", "ck_avaliacao_altura", "ck_avaliacao_gordura")


@dataclass(frozen=True)
class Escopo:
    id_academia: int
    id_profissional: Optional[int] = None
    id_aluno: Optional[int] = None


def _converter_escopo(escopo: Escopo) -> EscopoAgendamento:
    return EscopoAgendamento(escopo.id_academia, escopo.id_profissional, escopo.id_aluno)


def _confirmar(db: Session) -> None:
    try:
        db.commit()
    except DBAPIError as exc:
        db.rollback()
        mensagem = str(exc.orig)
        if "ck_avaliacao_peso" in mensagem:
            raise DadoInvalidoError("O peso deve ser maior que zero.") from exc
        if "ck_avaliacao_altura" in mensagem:
            raise DadoInvalidoError("A altura deve ser maior que zero.") from exc
        if "ck_avaliacao_gordura" in mensagem:
            raise DadoInvalidoError("O percentual de gordura deve estar entre 0 e 100.") from exc
        if isinstance(exc, IntegrityError):
            raise ConflitoError("Não foi possível salvar a ficha de avaliação.") from exc
        raise


def preencher_avaliacao(
    db: Session, escopo: Escopo, id_agendamento: int, dados: AvaliacaoFisicaCreate
) -> AvaliacaoFisicaResponse:
    """O profissional preenche a ficha; o agendamento é marcado como Realizado."""
    assert escopo.id_profissional is not None, "Apenas profissionais podem preencher."

    # Confere se a reserva é da academia/profissional e existe
    buscar_agendamento(db, _converter_escopo(escopo), id_agendamento)
    
    agend = travar_agendamento(db, id_agendamento)
    if agend.status == "Cancelado":
        raise ConflitoError("Não é possível realizar a avaliação de um agendamento cancelado.")
    if agend.status == "Realizado":
        raise ConflitoError("Este agendamento já possui uma avaliação física preenchida. Use a rota de atualização.")

    ficha = AvaliacaoFisica(
        fk_id_agendamento_avaliacao=id_agendamento,
        data_avaliacao=agora_local().date(),
        peso=dados.peso,
        altura=dados.altura,
        percentual_gordura=dados.percentual_gordura,
        massa_magra=dados.massa_magra,
        medidas_corporais=dados.medidas_corporais,
        observacoes_tecnicas=dados.observacoes_tecnicas,
    )
    db.add(ficha)
    agend.status = "Realizado"
    _confirmar(db)

    # _confirmar() garante que foi para o banco. Podemos retornar.
    return AvaliacaoFisicaResponse.from_orm_model(ficha)


def obter_avaliacao(db: Session, escopo: Escopo, id_agendamento: int) -> AvaliacaoFisicaResponse:
    """Qualquer perfil (dentro do seu escopo) pode visualizar a ficha vinculada ao agendamento."""
    buscar_agendamento(db, _converter_escopo(escopo), id_agendamento)

    ficha = db.scalar(
        select(AvaliacaoFisica).where(AvaliacaoFisica.fk_id_agendamento_avaliacao == id_agendamento)
    )
    if ficha is None:
        raise NaoEncontradoError("Ainda não há ficha de avaliação preenchida para este agendamento.")
    return AvaliacaoFisicaResponse.from_orm_model(ficha)


def atualizar_avaliacao(
    db: Session, escopo: Escopo, id_agendamento: int, dados: AvaliacaoFisicaUpdate
) -> AvaliacaoFisicaResponse:
    """O profissional corrige dados da ficha."""
    assert escopo.id_profissional is not None, "Apenas profissionais podem editar."
    buscar_agendamento(db, _converter_escopo(escopo), id_agendamento)

    ficha = db.scalars(
        select(AvaliacaoFisica)
        .where(AvaliacaoFisica.fk_id_agendamento_avaliacao == id_agendamento)
        .with_for_update()
    ).first()

    if ficha is None:
        raise NaoEncontradoError("Ainda não há ficha de avaliação preenchida para este agendamento.")

    campos = dados.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(ficha, campo, valor)
    _confirmar(db)
    
    return AvaliacaoFisicaResponse.from_orm_model(ficha)
