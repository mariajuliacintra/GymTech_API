"""
Regras da aula. Três perfis usam este service, cada um com um ESCOPO:

    academia      -> todas as aulas da academia (e é a única que altera)
    profissional  -> só as aulas dele (só para ver)
    aluno         -> todas as aulas da academia dele (só para ver; agendar é a reserva)

O escopo é montado nas rotas a partir do TOKEN. Aula fora do escopo responde
404, igual a um id que não existe (não revela que existe).

Regras:
- o profissional da aula precisa ser da MESMA academia e estar ATIVO;
- data_horario precisa ser no FUTURO, no horário da academia (core/tempo.py),
  tanto ao cadastrar quanto ao mudar a data;
- o mesmo profissional não pode ter duas aulas ATIVAS no mesmo horário (a tabela
  não guarda duração, então só dá para detectar horário exatamente igual);
- aula que já aconteceu não pode ser alterada nem cancelada (histórico);
- cancelar = status 'Cancelada' (nada é apagado); aula cancelada não muda mais (409);
- quando um PROFISSIONAL é inativado, as aulas ativas dele que ainda não
  aconteceram são canceladas em cascata (cascata_service). Quando a reserva_aula
  existir, cancelar uma aula também cancelará as reservas dela.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Literal, Optional

from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, aliased

from app.core.exceptions import ConflitoError, DadoInvalidoError, NaoEncontradoError
from app.core.tempo import agora_local
from app.models import Aula, Usuario
from app.schemas.aula import AulaCreate, AulaResponse, AulaUpdate
from app.services.cascata_service import ao_inativar

FiltroStatus = Literal["Ativa", "Cancelada", "Todas"]

_CHECKS_AULA = ("ck_aula_capacidade",)


@dataclass(frozen=True)
class Escopo:
    """Quais aulas quem está chamando pode alcançar."""

    id_academia: int
    id_profissional: Optional[int] = None  # se informado, só as aulas deste profissional


# ------------------------------------------------------------------ consultas
def _consulta_base():
    """SELECT da aula + nome do profissional (junta usuario)."""
    prof_u = aliased(Usuario, name="profissional_usuario")
    return select(Aula, prof_u.nome).join(prof_u, prof_u.id_usuario == Aula.fk_id_profissional)


def _filtros_escopo(escopo: Escopo) -> list:
    filtros = [Aula.fk_id_academia == escopo.id_academia]
    if escopo.id_profissional is not None:
        filtros.append(Aula.fk_id_profissional == escopo.id_profissional)
    return filtros


def _resposta(linha) -> AulaResponse:
    aula, nome_profissional = linha
    return AulaResponse(
        id_aula=aula.id_aula,
        fk_id_academia=aula.fk_id_academia,
        fk_id_profissional=aula.fk_id_profissional,
        nome_profissional=nome_profissional,
        nome_aula=aula.nome_aula,
        data_horario=aula.data_horario,
        capacidade_maxima=aula.capacidade_maxima,
        status=aula.status,
    )


def _buscar(db: Session, escopo: Escopo, id_aula: int) -> AulaResponse:
    linha = db.execute(
        _consulta_base().where(Aula.id_aula == id_aula, *_filtros_escopo(escopo))
    ).first()
    if linha is None:
        raise NaoEncontradoError("Aula não encontrada.")
    return _resposta(linha)


def _travar(db: Session, id_aula: int) -> Aula:
    """Lê a linha da aula travando-a até o commit (duas alterações ao mesmo tempo não se atropelam)."""
    return db.scalars(
        select(Aula)
        .where(Aula.id_aula == id_aula)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()


def _confirmar(db: Session) -> None:
    try:
        db.commit()
    except DBAPIError as exc:
        db.rollback()
        # Rede de segurança: a API já valida antes, mas se o CHECK do banco disparar
        # mesmo assim, o aviso é claro em vez de um erro 500 (constraint reconhecida
        # pelo NOME, que aparece na mensagem do MySQL, do MariaDB e do SQLite).
        if any(nome in str(exc.orig) for nome in _CHECKS_AULA):
            raise DadoInvalidoError("A capacidade máxima deve ser maior que zero.") from exc
        if isinstance(exc, IntegrityError):
            raise ConflitoError("Não foi possível salvar a aula.") from exc
        raise


# ------------------------------------------------------------------ validações
def _validar_profissional(db: Session, id_academia: int, id_profissional: int) -> None:
    usuario = db.scalar(
        select(Usuario).where(
            Usuario.id_usuario == id_profissional,
            Usuario.tipo_perfil == "Profissional",
            Usuario.fk_id_academia == id_academia,
        )
    )
    # de outra academia, de outro tipo ou inexistente: mesma resposta
    if usuario is None:
        raise NaoEncontradoError("Profissional não encontrado.")
    if usuario.status != "Ativo":
        raise ConflitoError("Profissional inativo não pode dar aula.")


def _exigir_futuro(data_horario: datetime) -> None:
    if data_horario <= agora_local():
        raise DadoInvalidoError(
            "A aula precisa estar marcada para o futuro (horário da academia)."
        )


def _checar_conflito(
    db: Session, id_profissional: int, data_horario: datetime, ignorar_id: Optional[int] = None
) -> None:
    consulta = select(Aula.id_aula).where(
        Aula.fk_id_profissional == id_profissional,
        Aula.data_horario == data_horario,
        Aula.status == "Ativa",
    )
    if ignorar_id is not None:
        consulta = consulta.where(Aula.id_aula != ignorar_id)
    if db.scalar(consulta):
        raise ConflitoError("Este profissional já tem uma aula neste horário.")


# ------------------------------------------------------------------- cadastro
def cadastrar_aula(db: Session, escopo: Escopo, dados: AulaCreate) -> AulaResponse:
    _validar_profissional(db, escopo.id_academia, dados.fk_id_profissional)
    _exigir_futuro(dados.data_horario)
    _checar_conflito(db, dados.fk_id_profissional, dados.data_horario)

    aula = Aula(
        fk_id_academia=escopo.id_academia,
        fk_id_profissional=dados.fk_id_profissional,
        nome_aula=dados.nome_aula,
        data_horario=dados.data_horario,
        capacidade_maxima=dados.capacidade_maxima,
    )
    db.add(aula)
    _confirmar(db)
    return _buscar(db, escopo, aula.id_aula)


# ------------------------------------------------------------------- consulta
def listar_aulas(
    db: Session,
    escopo: Escopo,
    status: FiltroStatus = "Ativa",
    fk_id_profissional: Optional[int] = None,
    data_de: Optional[date] = None,
    data_ate: Optional[date] = None,
    busca: Optional[str] = None,
    futuras: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[AulaResponse], int]:
    """Aulas do escopo (por padrão só as ativas), da mais próxima para a mais distante. Devolve (página, total)."""
    if data_de and data_ate and data_de > data_ate:
        raise DadoInvalidoError("'data_de' não pode ser depois de 'data_ate'.")

    filtros = _filtros_escopo(escopo)
    if status != "Todas":
        filtros.append(Aula.status == status)
    if fk_id_profissional is not None:
        filtros.append(Aula.fk_id_profissional == fk_id_profissional)
    if data_de:
        filtros.append(Aula.data_horario >= datetime.combine(data_de, time.min))
    if data_ate:  # o dia inteiro de data_ate entra
        filtros.append(Aula.data_horario < datetime.combine(data_ate + timedelta(days=1), time.min))
    if busca:
        # autoescape: "%" e "_" digitados na busca valem como texto comum
        filtros.append(Aula.nome_aula.icontains(busca, autoescape=True))
    if futuras:
        filtros.append(Aula.data_horario > agora_local())

    total = db.scalar(select(func.count(Aula.id_aula)).where(*filtros)) or 0
    linhas = db.execute(
        _consulta_base()
        .where(*filtros)
        .order_by(Aula.data_horario, Aula.id_aula)
        .limit(limit)
        .offset(offset)
    ).all()
    return [_resposta(l) for l in linhas], total


def obter_aula(db: Session, escopo: Escopo, id_aula: int) -> AulaResponse:
    return _buscar(db, escopo, id_aula)


# ------------------------------------------------------------------ atualizar
def atualizar_aula(db: Session, escopo: Escopo, id_aula: int, dados: AulaUpdate) -> AulaResponse:
    _buscar(db, escopo, id_aula)  # confere o escopo (404)
    aula = _travar(db, id_aula)
    if aula.status == "Cancelada":
        raise ConflitoError("Aula cancelada não pode ser alterada.")
    if aula.data_horario <= agora_local():
        raise ConflitoError("Aula que já aconteceu não pode ser alterada.")

    campos = dados.model_dump(exclude_unset=True)
    novo_prof = campos.get("fk_id_profissional", aula.fk_id_profissional)
    nova_data = campos.get("data_horario", aula.data_horario)
    if "fk_id_profissional" in campos:
        _validar_profissional(db, escopo.id_academia, novo_prof)
    if "data_horario" in campos:
        _exigir_futuro(nova_data)
    if novo_prof != aula.fk_id_profissional or nova_data != aula.data_horario:
        _checar_conflito(db, novo_prof, nova_data, ignorar_id=id_aula)

    for campo, valor in campos.items():
        setattr(aula, campo, valor)
    _confirmar(db)
    return _buscar(db, escopo, id_aula)


# -------------------------------------------------------------------- cancelar
def cancelar_aula(db: Session, escopo: Escopo, id_aula: int) -> AulaResponse:
    _buscar(db, escopo, id_aula)  # confere o escopo (404)
    aula = _travar(db, id_aula)
    if aula.status == "Cancelada":
        raise ConflitoError("Aula já está cancelada.")
    if aula.data_horario <= agora_local():
        raise ConflitoError("Aula que já aconteceu não pode ser cancelada.")
    aula.status = "Cancelada"
    _confirmar(db)
    return _buscar(db, escopo, id_aula)


# ------------------------------------------------- cascata (inativar usuário)
@ao_inativar("Profissional", "aulas canceladas")
def _cancelar_aulas_do_profissional(db: Session, usuario: Usuario) -> int:
    """Cancela as aulas ativas do profissional que ainda não aconteceram."""
    resultado = db.execute(
        update(Aula)
        .where(
            Aula.fk_id_profissional == usuario.id_usuario,
            Aula.status == "Ativa",
            Aula.data_horario > agora_local(),
        )
        .values(status="Cancelada")
        .execution_options(synchronize_session=False)
    )
    return resultado.rowcount
