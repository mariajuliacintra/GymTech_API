"""
Regras do Agendamento de Avaliação Física.

ESCOPOS:
    academia      -> vê todos e pode cancelar qualquer um (pode até agendar para um aluno)
    profissional  -> vê os seus agendamentos e pode cancelar
    aluno         -> agenda, vê os seus e cancela os seus

Regras de conflito de horário:
- O aluno não pode ter outro agendamento ativo no mesmo horário.
- O profissional não pode ter outro agendamento ativo no mesmo horário.
- O profissional não pode ter uma AULA ativa no mesmo horário.

Quando a ficha (avaliacao_fisica) é preenchida, o status do agendamento
muda para 'Realizado'.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Literal, Optional

from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, aliased

from app.core.exceptions import ConflitoError, DadoInvalidoError, NaoEncontradoError
from app.core.tempo import agora_local
from app.models import AgendamentoAvaliacao, Aula, AvaliacaoFisica, Usuario
from app.schemas.agendamento_avaliacao import (
    AgendamentoAvaliacaoCreate,
    AgendamentoAvaliacaoResponse,
    AgendamentoAvaliacaoUpdate,
)
from app.services.cascata_service import ao_inativar

FiltroStatus = Literal["Agendado", "Realizado", "Cancelado", "Todos"]


@dataclass(frozen=True)
class Escopo:
    """Quais agendamentos quem está chamando pode alcançar."""
    id_academia: int
    id_profissional: Optional[int] = None
    id_aluno: Optional[int] = None


# ------------------------------------------------------------------ consultas
def _consulta_base():
    aluno_u = aliased(Usuario, name="agend_aluno_usuario")
    prof_u = aliased(Usuario, name="agend_prof_usuario")
    # Subquery para saber se a ficha já existe (possui_ficha)
    ficha = (
        select(AvaliacaoFisica.id_avaliacao)
        .where(AvaliacaoFisica.fk_id_agendamento_avaliacao == AgendamentoAvaliacao.id_agendamento_avaliacao)
        .correlate(AgendamentoAvaliacao)
        .scalar_subquery()
    )
    consulta = (
        select(
            AgendamentoAvaliacao,
            aluno_u.nome,
            prof_u.nome,
            ficha.label("id_ficha"),
        )
        .join(aluno_u, aluno_u.id_usuario == AgendamentoAvaliacao.fk_id_aluno)
        .join(prof_u, prof_u.id_usuario == AgendamentoAvaliacao.fk_id_profissional)
    )
    return aluno_u, prof_u, consulta


def _filtros_escopo(escopo: Escopo, aluno_u, prof_u) -> list:
    filtros = [
        aluno_u.fk_id_academia == escopo.id_academia,
        prof_u.fk_id_academia == escopo.id_academia,
    ]
    if escopo.id_profissional is not None:
        filtros.append(AgendamentoAvaliacao.fk_id_profissional == escopo.id_profissional)
    if escopo.id_aluno is not None:
        filtros.append(AgendamentoAvaliacao.fk_id_aluno == escopo.id_aluno)
    return filtros


def _resposta(linha) -> AgendamentoAvaliacaoResponse:
    agend, nome_aluno, nome_profissional, id_ficha = linha
    return AgendamentoAvaliacaoResponse(
        id_agendamento_avaliacao=agend.id_agendamento_avaliacao,
        fk_id_aluno=agend.fk_id_aluno,
        nome_aluno=nome_aluno,
        fk_id_profissional=agend.fk_id_profissional,
        nome_profissional=nome_profissional,
        data_horario=agend.data_horario,
        status=agend.status,
        possui_ficha=id_ficha is not None,
    )


def _buscar(db: Session, escopo: Escopo, id_agend: int) -> AgendamentoAvaliacaoResponse:
    aluno_u, prof_u, consulta = _consulta_base()
    linha = db.execute(
        consulta.where(
            AgendamentoAvaliacao.id_agendamento_avaliacao == id_agend,
            *_filtros_escopo(escopo, aluno_u, prof_u)
        )
    ).first()
    if linha is None:
        raise NaoEncontradoError("Agendamento não encontrado.")
    return _resposta(linha)


def _travar(db: Session, id_agend: int) -> AgendamentoAvaliacao:
    return db.scalars(
        select(AgendamentoAvaliacao)
        .where(AgendamentoAvaliacao.id_agendamento_avaliacao == id_agend)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()


# ------------------------------------------------------------------ validações
def _validar_pessoas(db: Session, id_academia: int, id_aluno: int, id_profissional: int) -> None:
    aluno = db.scalar(
        select(Usuario).where(
            Usuario.id_usuario == id_aluno,
            Usuario.tipo_perfil == "Aluno",
            Usuario.fk_id_academia == id_academia,
        )
    )
    if aluno is None:
        raise NaoEncontradoError("Aluno não encontrado.")
    if aluno.status != "Ativo":
        raise ConflitoError("Aluno inativo não pode agendar avaliação.")

    prof = db.scalar(
        select(Usuario).where(
            Usuario.id_usuario == id_profissional,
            Usuario.tipo_perfil == "Profissional",
            Usuario.fk_id_academia == id_academia,
        )
    )
    if prof is None:
        raise NaoEncontradoError("Profissional não encontrado.")
    if prof.status != "Ativo":
        raise ConflitoError("Profissional inativo não pode realizar avaliação.")


def _checar_conflito(
    db: Session, id_aluno: int, id_profissional: int, data_horario: datetime, ignorar_id: Optional[int] = None
) -> None:
    if data_horario <= agora_local():
        raise DadoInvalidoError("A data e hora do agendamento devem ser no futuro.")

    # 1. Aluno já tem agendamento ativo nesse horário?
    q_aluno = select(AgendamentoAvaliacao.id_agendamento_avaliacao).where(
        AgendamentoAvaliacao.fk_id_aluno == id_aluno,
        AgendamentoAvaliacao.data_horario == data_horario,
        AgendamentoAvaliacao.status.in_(["Agendado", "Realizado"]),
    )
    if ignorar_id:
        q_aluno = q_aluno.where(AgendamentoAvaliacao.id_agendamento_avaliacao != ignorar_id)
    if db.scalar(q_aluno):
        raise ConflitoError("O aluno já possui um agendamento neste horário.")

    # 2. Profissional já tem agendamento ativo nesse horário?
    q_prof = select(AgendamentoAvaliacao.id_agendamento_avaliacao).where(
        AgendamentoAvaliacao.fk_id_profissional == id_profissional,
        AgendamentoAvaliacao.data_horario == data_horario,
        AgendamentoAvaliacao.status.in_(["Agendado", "Realizado"]),
    )
    if ignorar_id:
        q_prof = q_prof.where(AgendamentoAvaliacao.id_agendamento_avaliacao != ignorar_id)
    if db.scalar(q_prof):
        raise ConflitoError("O profissional já possui uma avaliação agendada neste horário.")

    # 3. Profissional já tem uma aula ativa nesse horário?
    if db.scalar(
        select(Aula.id_aula).where(
            Aula.fk_id_profissional == id_profissional,
            Aula.data_horario == data_horario,
            Aula.status == "Ativa"
        )
    ):
        raise ConflitoError("O profissional possui uma aula marcada neste mesmo horário.")


# ------------------------------------------------------------------- criar
def agendar(db: Session, escopo: Escopo, dados: AgendamentoAvaliacaoCreate) -> AgendamentoAvaliacaoResponse:
    # Se a academia chamou, fk_id_aluno vem nos dados; se for o aluno, usamos o do escopo
    id_aluno = escopo.id_aluno if escopo.id_aluno is not None else dados.fk_id_aluno
    if id_aluno is None:
        raise DadoInvalidoError("ID do aluno é obrigatório.")

    _validar_pessoas(db, escopo.id_academia, id_aluno, dados.fk_id_profissional)
    _checar_conflito(db, id_aluno, dados.fk_id_profissional, dados.data_horario)

    agendamento = AgendamentoAvaliacao(
        fk_id_aluno=id_aluno,
        fk_id_profissional=dados.fk_id_profissional,
        data_horario=dados.data_horario,
        status="Agendado",
    )
    db.add(agendamento)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflitoError("Não foi possível realizar o agendamento.") from exc

    return _buscar(db, escopo, agendamento.id_agendamento_avaliacao)


# ------------------------------------------------------------------- consulta
def listar_agendamentos(
    db: Session,
    escopo: Escopo,
    status: FiltroStatus = "Agendado",
    fk_id_aluno: Optional[int] = None,
    fk_id_profissional: Optional[int] = None,
    data_de: Optional[date] = None,
    data_ate: Optional[date] = None,
    futuros: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[AgendamentoAvaliacaoResponse], int]:
    
    if data_de and data_ate and data_de > data_ate:
        raise DadoInvalidoError("'data_de' não pode ser depois de 'data_ate'.")

    aluno_u, prof_u, consulta = _consulta_base()
    filtros = _filtros_escopo(escopo, aluno_u, prof_u)
    
    if status != "Todos":
        filtros.append(AgendamentoAvaliacao.status == status)
    if fk_id_aluno is not None:
        filtros.append(AgendamentoAvaliacao.fk_id_aluno == fk_id_aluno)
    if fk_id_profissional is not None:
        filtros.append(AgendamentoAvaliacao.fk_id_profissional == fk_id_profissional)
    if data_de:
        filtros.append(AgendamentoAvaliacao.data_horario >= datetime.combine(data_de, time.min))
    if data_ate:
        filtros.append(AgendamentoAvaliacao.data_horario < datetime.combine(data_ate + timedelta(days=1), time.min))
    if futuros:
        filtros.append(AgendamentoAvaliacao.data_horario >= agora_local())

    total = db.scalar(
        select(func.count(AgendamentoAvaliacao.id_agendamento_avaliacao))
        .select_from(AgendamentoAvaliacao)
        .join(aluno_u, aluno_u.id_usuario == AgendamentoAvaliacao.fk_id_aluno)
        .join(prof_u, prof_u.id_usuario == AgendamentoAvaliacao.fk_id_profissional)
        .where(*filtros)
    ) or 0

    linhas = db.execute(
        consulta.where(*filtros)
        .order_by(AgendamentoAvaliacao.data_horario, AgendamentoAvaliacao.id_agendamento_avaliacao)
        .limit(limit)
        .offset(offset)
    ).all()
    return [_resposta(l) for l in linhas], total


def obter_agendamento(db: Session, escopo: Escopo, id_agend: int) -> AgendamentoAvaliacaoResponse:
    return _buscar(db, escopo, id_agend)


# ------------------------------------------------------------------ reagendar (academia)
def atualizar_agendamento(
    db: Session, escopo: Escopo, id_agend: int, dados: AgendamentoAvaliacaoUpdate
) -> AgendamentoAvaliacaoResponse:
    _buscar(db, escopo, id_agend)
    agend = _travar(db, id_agend)

    if agend.status == "Cancelado":
        raise ConflitoError("Agendamento cancelado não pode ser alterado.")
    if agend.status == "Realizado":
        raise ConflitoError("Agendamento já realizado (com avaliação preenchida) não pode ser reagendado.")

    campos = dados.model_dump(exclude_unset=True)
    novo_prof = campos.get("fk_id_profissional", agend.fk_id_profissional)
    nova_data = campos.get("data_horario", agend.data_horario)

    if "fk_id_profissional" in campos:
        _validar_pessoas(db, escopo.id_academia, agend.fk_id_aluno, novo_prof)
    if novo_prof != agend.fk_id_profissional or nova_data != agend.data_horario:
        _checar_conflito(db, agend.fk_id_aluno, novo_prof, nova_data, ignorar_id=id_agend)

    for campo, valor in campos.items():
        setattr(agend, campo, valor)
    db.commit()
    return _buscar(db, escopo, id_agend)


# -------------------------------------------------------------------- cancelar
def cancelar_agendamento(db: Session, escopo: Escopo, id_agend: int) -> AgendamentoAvaliacaoResponse:
    _buscar(db, escopo, id_agend)
    agend = _travar(db, id_agend)

    if agend.status == "Cancelado":
        raise ConflitoError("Agendamento já está cancelado.")
    if agend.status == "Realizado":
        raise ConflitoError("Não é possível cancelar um agendamento cuja avaliação já foi realizada.")
    if agend.data_horario <= agora_local():
        raise ConflitoError("Não é possível cancelar um agendamento de data passada.")

    agend.status = "Cancelado"
    db.commit()
    return _buscar(db, escopo, id_agend)


# ------------------------------------------------- cascata (inativar usuário)
def _cancelar_pendentes(db: Session, coluna, id_usuario: int) -> int:
    resultado = db.execute(
        update(AgendamentoAvaliacao)
        .where(
            coluna == id_usuario,
            AgendamentoAvaliacao.status == "Agendado",
            AgendamentoAvaliacao.data_horario > agora_local(),
        )
        .values(status="Cancelado")
        .execution_options(synchronize_session=False)
    )
    return resultado.rowcount

@ao_inativar("Aluno", "agendamentos de avaliação cancelados")
def _cancelar_agendamentos_aluno(db: Session, usuario: Usuario) -> int:
    return _cancelar_pendentes(db, AgendamentoAvaliacao.fk_id_aluno, usuario.id_usuario)

@ao_inativar("Profissional", "agendamentos de avaliação cancelados")
def _cancelar_agendamentos_profissional(db: Session, usuario: Usuario) -> int:
    return _cancelar_pendentes(db, AgendamentoAvaliacao.fk_id_profissional, usuario.id_usuario)
