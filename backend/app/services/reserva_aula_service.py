"""
Regras das reservas de aula (reserva_aula). Três perfis usam este service,
cada um com um ESCOPO montado nas rotas a partir do TOKEN:

    academia      -> vê todas as reservas das aulas da academia e pode cancelar qualquer uma
    profissional  -> vê os alunos reservados nas aulas dele (somente leitura)
    aluno         -> reserva vaga, vê as próprias reservas e cancela as próprias reservas

Reserva fora do escopo responde 404, igual a um id que não existe.

Regras:
- o aluno só reserva aulas da PRÓPRIA academia, que estejam 'Ativa' e no FUTURO;
- a aula precisa ter vaga disponível (reservas 'Confirmado' < capacidade_maxima);
  ao reservar, a ocupação sobe e as vagas disponíveis diminuem; ao cancelar, a
  vaga é liberada imediatamente;
- um aluno não pode ter duas reservas 'Confirmado' simultâneas na mesma aula (409),
  nem duas reservas 'Confirmado' em aulas diferentes no mesmo horário (409);
- se o aluno reservar uma aula, cancelar e depois mudar de ideia, PODE reservar
  novamente a mesma aula (um novo registro 'Confirmado' é criado; o cancelado
  fica preservado como histórico);
- cancelar = status 'Cancelado' (nada é apagado); reserva já cancelada ou de aula
  que já aconteceu não pode ser cancelada novamente (409);
- cascata: quando um aluno ou profissional é inativado, suas reservas confirmadas
  em aulas futuras são canceladas automaticamente (cascata_service).
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Literal, Optional

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.core.exceptions import ConflitoError, DadoInvalidoError, NaoEncontradoError
from app.core.tempo import agora_local
from app.models import Aula, ReservaAula, Usuario
from app.schemas.reserva_aula import ReservaAulaResponse
from app.services.cascata_service import ao_inativar

FiltroStatus = Literal["Confirmado", "Cancelado", "Todas"]


@dataclass(frozen=True)
class Escopo:
    """Quais reservas quem está chamando pode alcançar."""

    id_academia: int
    id_profissional: Optional[int] = None  # se informado, só reservas de aulas deste profissional
    id_aluno: Optional[int] = None  # se informado, só reservas deste aluno


# ------------------------------------------------------------------ consultas
def _consulta_base():
    """SELECT da reserva + dados da aula + nome do aluno + nome do profissional + ocupação."""
    aluno_u = aliased(Usuario, name="reserva_aluno_usuario")
    prof_u = aliased(Usuario, name="reserva_prof_usuario")
    ocupadas = (
        select(func.count(ReservaAula.id_reserva_aula))
        .where(
            ReservaAula.fk_id_aula == Aula.id_aula,
            ReservaAula.status == "Confirmado",
        )
        .correlate(Aula)
        .scalar_subquery()
    )
    consulta = (
        select(
            ReservaAula,
            Aula,
            aluno_u.nome,
            prof_u.nome,
            ocupadas.label("vagas_ocupadas"),
        )
        .join(Aula, Aula.id_aula == ReservaAula.fk_id_aula)
        .join(aluno_u, aluno_u.id_usuario == ReservaAula.fk_id_aluno)
        .join(prof_u, prof_u.id_usuario == Aula.fk_id_profissional)
    )
    return aluno_u, prof_u, consulta


def _filtros_escopo(escopo: Escopo) -> list:
    filtros = [Aula.fk_id_academia == escopo.id_academia]
    if escopo.id_profissional is not None:
        filtros.append(Aula.fk_id_profissional == escopo.id_profissional)
    if escopo.id_aluno is not None:
        filtros.append(ReservaAula.fk_id_aluno == escopo.id_aluno)
    return filtros


def _resposta(linha) -> ReservaAulaResponse:
    reserva, aula, nome_aluno, nome_profissional, vagas_ocupadas = linha
    ocupadas = int(vagas_ocupadas or 0)
    return ReservaAulaResponse(
        id_reserva_aula=reserva.id_reserva_aula,
        fk_id_aula=aula.id_aula,
        nome_aula=aula.nome_aula,
        tipo_aula=aula.tipo_aula,
        data_horario_aula=aula.data_horario,
        fk_id_profissional=aula.fk_id_profissional,
        nome_profissional=nome_profissional,
        fk_id_aluno=reserva.fk_id_aluno,
        nome_aluno=nome_aluno,
        data_agendamento=reserva.data_agendamento,
        status=reserva.status,
        capacidade_maxima=aula.capacidade_maxima,
        vagas_ocupadas=ocupadas,
        vagas_disponiveis=max(0, aula.capacidade_maxima - ocupadas),
    )


def _buscar(db: Session, escopo: Escopo, id_reserva_aula: int) -> ReservaAulaResponse:
    _, _, consulta = _consulta_base()
    linha = db.execute(
        consulta.where(
            ReservaAula.id_reserva_aula == id_reserva_aula,
            *_filtros_escopo(escopo),
        )
    ).first()
    if linha is None:
        raise NaoEncontradoError("Reserva não encontrada.")
    return _resposta(linha)


def _contar_confirmadas(db: Session, id_aula: int) -> int:
    return (
        db.scalar(
            select(func.count(ReservaAula.id_reserva_aula)).where(
                ReservaAula.fk_id_aula == id_aula,
                ReservaAula.status == "Confirmado",
            )
        )
        or 0
    )


# ------------------------------------------------------------------- reservar
def reservar_aula(db: Session, escopo: Escopo, id_aula: int) -> ReservaAulaResponse:
    """
    O aluno logado reserva uma vaga na aula.
    Trava a linha da aula com FOR UPDATE para evitar overbooking em requisições simultâneas.
    """
    assert escopo.id_aluno is not None

    aula = db.scalars(
        select(Aula)
        .where(
            Aula.id_aula == id_aula,
            Aula.fk_id_academia == escopo.id_academia,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()

    if aula is None:
        raise NaoEncontradoError("Aula não encontrada.")
    if aula.status != "Ativa":
        raise ConflitoError("Não é possível reservar uma aula cancelada.")
    if aula.data_horario <= agora_local():
        raise ConflitoError("Não é possível reservar uma aula que já aconteceu.")

    # Já tem reserva CONFIRMADA nesta mesma aula? (Se havia uma 'Cancelado', pode reservar de novo!)
    ja_confirmada = db.scalar(
        select(ReservaAula.id_reserva_aula).where(
            ReservaAula.fk_id_aula == id_aula,
            ReservaAula.fk_id_aluno == escopo.id_aluno,
            ReservaAula.status == "Confirmado",
        )
    )
    if ja_confirmada:
        raise ConflitoError("Você já possui uma reserva confirmada para esta aula.")

    # Já tem reserva CONFIRMADA em outra aula ativa no mesmo horário?
    conflito_horario = db.scalar(
        select(ReservaAula.id_reserva_aula)
        .join(Aula, Aula.id_aula == ReservaAula.fk_id_aula)
        .where(
            ReservaAula.fk_id_aluno == escopo.id_aluno,
            ReservaAula.status == "Confirmado",
            Aula.status == "Ativa",
            Aula.data_horario == aula.data_horario,
            Aula.id_aula != id_aula,
        )
    )
    if conflito_horario:
        raise ConflitoError("Você já possui outra aula reservada neste mesmo horário.")

    # Confere se ainda há vaga disponível
    ocupadas = _contar_confirmadas(db, id_aula)
    if ocupadas >= aula.capacidade_maxima:
        raise ConflitoError("Esta aula já está lotada.")

    reserva = ReservaAula(
        fk_id_aula=id_aula,
        fk_id_aluno=escopo.id_aluno,
        status="Confirmado",
    )
    db.add(reserva)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflitoError("Não foi possível concluir a reserva.") from exc

    return _buscar(db, escopo, reserva.id_reserva_aula)


# ------------------------------------------------------------------- consulta
def listar_reservas(
    db: Session,
    escopo: Escopo,
    status: FiltroStatus = "Confirmado",
    fk_id_aula: Optional[int] = None,
    fk_id_aluno: Optional[int] = None,
    data_de: Optional[date] = None,
    data_ate: Optional[date] = None,
    futuras: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[ReservaAulaResponse], int]:
    """Reservas do escopo (por padrão só 'Confirmado'), ordenadas pela data da aula. Devolve (página, total)."""
    if data_de and data_ate and data_de > data_ate:
        raise DadoInvalidoError("'data_de' não pode ser depois de 'data_ate'.")

    _, _, consulta = _consulta_base()
    filtros = _filtros_escopo(escopo)
    if status != "Todas":
        filtros.append(ReservaAula.status == status)
    if fk_id_aula is not None:
        filtros.append(ReservaAula.fk_id_aula == fk_id_aula)
    if fk_id_aluno is not None:
        filtros.append(ReservaAula.fk_id_aluno == fk_id_aluno)
    if data_de:
        filtros.append(Aula.data_horario >= datetime.combine(data_de, time.min))
    if data_ate:
        filtros.append(Aula.data_horario < datetime.combine(data_ate + timedelta(days=1), time.min))
    if futuras:
        filtros.append(Aula.data_horario > agora_local())

    total = db.scalar(
        select(func.count(ReservaAula.id_reserva_aula))
        .select_from(ReservaAula)
        .join(Aula, Aula.id_aula == ReservaAula.fk_id_aula)
        .where(*filtros)
    ) or 0

    linhas = db.execute(
        consulta.where(*filtros)
        .order_by(Aula.data_horario, ReservaAula.id_reserva_aula)
        .limit(limit)
        .offset(offset)
    ).all()
    return [_resposta(l) for l in linhas], total


def obter_reserva(db: Session, escopo: Escopo, id_reserva_aula: int) -> ReservaAulaResponse:
    return _buscar(db, escopo, id_reserva_aula)


# -------------------------------------------------------------------- cancelar
def cancelar_reserva(
    db: Session, escopo: Escopo, id_reserva_aula: int
) -> ReservaAulaResponse:
    """Cancela a reserva (status = 'Cancelado'), liberando 1 vaga na aula."""
    atual = _buscar(db, escopo, id_reserva_aula)  # confere o escopo (404)

    # Trava na ordem Aula -> ReservaAula (mesma ordem de reservar_aula, evita deadlock)
    aula = db.scalars(
        select(Aula)
        .where(Aula.id_aula == atual.fk_id_aula)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()

    reserva = db.scalars(
        select(ReservaAula)
        .where(ReservaAula.id_reserva_aula == id_reserva_aula)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()

    if reserva.status == "Cancelado":
        raise ConflitoError("Reserva já está cancelada.")
    if aula.data_horario <= agora_local():
        raise ConflitoError("Não é possível cancelar a reserva de uma aula que já aconteceu.")

    reserva.status = "Cancelado"
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflitoError("Não foi possível cancelar a reserva.") from exc

    return _buscar(db, escopo, id_reserva_aula)


# ------------------------------------------------- cascata (inativar usuário)
@ao_inativar("Aluno", "reservas de aula canceladas")
def _cancelar_reservas_do_aluno(db: Session, usuario: Usuario) -> int:
    """Cancela as reservas confirmadas do aluno em aulas futuras."""
    ids_aulas_futuras = select(Aula.id_aula).where(Aula.data_horario > agora_local())
    resultado = db.execute(
        update(ReservaAula)
        .where(
            ReservaAula.fk_id_aluno == usuario.id_usuario,
            ReservaAula.status == "Confirmado",
            ReservaAula.fk_id_aula.in_(ids_aulas_futuras),
        )
        .values(status="Cancelado")
        .execution_options(synchronize_session=False)
    )
    return resultado.rowcount


@ao_inativar("Profissional", "reservas de aula canceladas")
def _cancelar_reservas_das_aulas_do_profissional(db: Session, usuario: Usuario) -> int:
    """Cancela as reservas confirmadas nas aulas futuras do profissional inativado."""
    ids_aulas_prof = select(Aula.id_aula).where(
        Aula.fk_id_profissional == usuario.id_usuario,
        Aula.data_horario > agora_local(),
    )
    resultado = db.execute(
        update(ReservaAula)
        .where(
            ReservaAula.fk_id_aula.in_(ids_aulas_prof),
            ReservaAula.status == "Confirmado",
        )
        .values(status="Cancelado")
        .execution_options(synchronize_session=False)
    )
    return resultado.rowcount
