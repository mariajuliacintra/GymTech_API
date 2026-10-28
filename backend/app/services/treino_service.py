"""
Regras do treino. Três perfis usam este mesmo service, cada um com um ESCOPO:

    academia      -> todos os treinos da academia
    profissional  -> só os treinos em que ele é o profissional
    aluno         -> só os treinos dele (e só para ver)

O escopo é montado nas rotas a partir do TOKEN (nunca de um id enviado pelo
cliente), e todas as consultas o aplicam: treino fora do escopo responde 404,
igual a um id que não existe (não revela que existe).

Os DOIS ids da tabela `usuario`: o treino guarda o id do aluno e o id do
profissional, e os dois são linhas da mesma tabela `usuario`. Para trazer o
nome de cada um juntamos `usuario` duas vezes, com apelidos diferentes
(`aluno_usuario` e `profissional_usuario`), como em:
    SELECT ... FROM treino
      JOIN usuario AS aluno_usuario        ON aluno_usuario.id_usuario = treino.fk_id_aluno
      JOIN usuario AS profissional_usuario ON profissional_usuario.id_usuario = treino.fk_id_profissional

Regras:
- aluno e profissional do treino precisam ser da MESMA academia e estar ATIVOS
  (a tabela não tem fk_id_academia, então a API é quem garante isso);
- data_programada não pode ser anterior à data de criação (a regra do CHECK do
  banco, validada antes para devolver uma mensagem clara);
- cancelar = status 'Cancelado' (nada é apagado); treino cancelado não pode ser
  alterado nem cancelado de novo (409);
- quando um aluno ou profissional é INATIVADO, os treinos dele que ainda não
  ocorreram (data de hoje em diante, ou sem data) são cancelados em cascata;
  os de data passada ficam como histórico. Isso se pluga no cascata_service.
"""
from dataclasses import dataclass
from datetime import date
from typing import Literal, Optional, Union

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, aliased

from app.core.exceptions import ConflitoError, DadoInvalidoError, NaoEncontradoError
from app.models import Treino, Usuario
from app.schemas.treino import (
    TreinoResponse,
    TreinoUpdate,
    TreinoUpdateProfissional,
)
from app.services.cascata_service import ao_inativar

FiltroStatus = Literal["Ativo", "Cancelado", "Todos"]


@dataclass(frozen=True)
class Escopo:
    """Quais treinos quem está chamando pode alcançar."""

    id_academia: int
    id_aluno: Optional[int] = None  # se informado, só treinos deste aluno
    id_profissional: Optional[int] = None  # se informado, só treinos deste profissional


# ------------------------------------------------------------------ consultas
def _consulta_base():
    """SELECT do treino + nome do aluno + nome do profissional (usuario juntado 2 vezes)."""
    aluno_u = aliased(Usuario, name="aluno_usuario")
    prof_u = aliased(Usuario, name="profissional_usuario")
    consulta = (
        select(Treino, aluno_u.nome, prof_u.nome)
        .join(aluno_u, aluno_u.id_usuario == Treino.fk_id_aluno)
        .join(prof_u, prof_u.id_usuario == Treino.fk_id_profissional)
    )
    return aluno_u, prof_u, consulta


def _filtros_escopo(escopo: Escopo, aluno_u, prof_u) -> list:
    filtros = [
        aluno_u.fk_id_academia == escopo.id_academia,
        prof_u.fk_id_academia == escopo.id_academia,
    ]
    if escopo.id_aluno is not None:
        filtros.append(Treino.fk_id_aluno == escopo.id_aluno)
    if escopo.id_profissional is not None:
        filtros.append(Treino.fk_id_profissional == escopo.id_profissional)
    return filtros


def _resposta(treino: Treino, nome_aluno: str, nome_profissional: str) -> TreinoResponse:
    return TreinoResponse(
        id_treino=treino.id_treino,
        fk_id_aluno=treino.fk_id_aluno,
        nome_aluno=nome_aluno,
        fk_id_profissional=treino.fk_id_profissional,
        nome_profissional=nome_profissional,
        titulo_treino=treino.titulo_treino,
        data_criacao=treino.data_criacao,
        data_programada=treino.data_programada,
        status=treino.status,
    )


def _buscar(db: Session, escopo: Escopo, id_treino: int) -> TreinoResponse:
    aluno_u, prof_u, consulta = _consulta_base()
    linha = db.execute(
        consulta.where(Treino.id_treino == id_treino, *_filtros_escopo(escopo, aluno_u, prof_u))
    ).first()
    if linha is None:
        raise NaoEncontradoError("Treino não encontrado.")
    return _resposta(*linha)


def _travar(db: Session, id_treino: int) -> Treino:
    """
    Lê a linha do treino travando-a até o commit (duas alterações ao mesmo
    tempo não se atropelam). Trava só a linha do treino, sem as de `usuario`,
    para não entrar em conflito com a inativação de usuários.
    """
    return db.scalars(
        select(Treino)
        .where(Treino.id_treino == id_treino)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()


def _hoje(db: Session) -> date:
    """A data de hoje segundo o BANCO (é a mesma que ele usa em data_criacao)."""
    return db.scalar(select(func.current_date()))


def _salvar(db: Session, treino: Treino) -> None:
    db.add(treino)
    try:
        db.commit()
    except DBAPIError as exc:
        db.rollback()
        # Rede de segurança: a API já valida as datas antes, mas se o CHECK do
        # banco disparar mesmo assim (ex.: fuso diferente perto da meia-noite),
        # o aviso é claro em vez de um erro 500. A constraint é reconhecida pelo
        # NOME, que aparece na mensagem do MySQL, do MariaDB e do SQLite (cada
        # um sinaliza o erro com uma classe/código diferente).
        if "ck_treino_datas" in str(exc.orig):
            raise DadoInvalidoError(
                "A data programada não pode ser anterior à data de criação do treino."
            ) from exc
        if isinstance(exc, IntegrityError):
            raise ConflitoError("Não foi possível salvar o treino.") from exc
        raise


# ---------------------------------------------------- validação das pessoas
def _validar_pessoa(
    db: Session, id_academia: int, id_usuario: int, tipo: str, rotulo: str, inativo_msg: str
) -> None:
    usuario = db.scalar(
        select(Usuario).where(
            Usuario.id_usuario == id_usuario,
            Usuario.tipo_perfil == tipo,
            Usuario.fk_id_academia == id_academia,
        )
    )
    # de outra academia, de outro tipo ou inexistente: mesma resposta
    if usuario is None:
        raise NaoEncontradoError(f"{rotulo} não encontrado.")
    if usuario.status != "Ativo":
        raise ConflitoError(inativo_msg)


def _validar_aluno(db: Session, id_academia: int, id_aluno: int) -> None:
    _validar_pessoa(db, id_academia, id_aluno, "Aluno", "Aluno", "Aluno inativo não pode receber treino.")


def _validar_profissional(db: Session, id_academia: int, id_profissional: int) -> None:
    _validar_pessoa(
        db, id_academia, id_profissional, "Profissional", "Profissional",
        "Profissional inativo não pode ser responsável por treino.",
    )


# ------------------------------------------------------------------- cadastro
def cadastrar_treino(
    db: Session,
    escopo: Escopo,
    id_aluno: int,
    id_profissional: int,
    titulo_treino: str,
    data_programada: Optional[date],
) -> TreinoResponse:
    _validar_aluno(db, escopo.id_academia, id_aluno)
    _validar_profissional(db, escopo.id_academia, id_profissional)
    # o treino nasce hoje (data_criacao é preenchida pelo banco)
    if data_programada is not None and data_programada < _hoje(db):
        raise DadoInvalidoError("A data programada não pode ser anterior à data de hoje.")

    treino = Treino(
        fk_id_aluno=id_aluno,
        fk_id_profissional=id_profissional,
        titulo_treino=titulo_treino,
        data_programada=data_programada,
    )
    _salvar(db, treino)
    return _buscar(db, escopo, treino.id_treino)


# ------------------------------------------------------------------- consulta
def listar_treinos(
    db: Session,
    escopo: Escopo,
    status: FiltroStatus = "Ativo",
    fk_id_aluno: Optional[int] = None,
    fk_id_profissional: Optional[int] = None,
    data_de: Optional[date] = None,
    data_ate: Optional[date] = None,
    busca: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[TreinoResponse], int]:
    """
    Treinos do escopo (por padrão só os ativos), do mais próximo para o mais
    distante; os sem data programada ficam por último. Devolve (página, total).
    """
    if data_de and data_ate and data_de > data_ate:
        raise DadoInvalidoError("'data_de' não pode ser depois de 'data_ate'.")

    aluno_u, prof_u, consulta = _consulta_base()
    filtros = _filtros_escopo(escopo, aluno_u, prof_u)
    if status != "Todos":
        filtros.append(Treino.status == status)
    if fk_id_aluno is not None:
        filtros.append(Treino.fk_id_aluno == fk_id_aluno)
    if fk_id_profissional is not None:
        filtros.append(Treino.fk_id_profissional == fk_id_profissional)
    if data_de:
        filtros.append(Treino.data_programada >= data_de)
    if data_ate:
        filtros.append(Treino.data_programada <= data_ate)
    if busca:
        # autoescape: "%" e "_" digitados na busca valem como texto comum
        filtros.append(Treino.titulo_treino.icontains(busca, autoescape=True))

    total = db.scalar(
        select(func.count(Treino.id_treino))
        .select_from(Treino)
        .join(aluno_u, aluno_u.id_usuario == Treino.fk_id_aluno)
        .join(prof_u, prof_u.id_usuario == Treino.fk_id_profissional)
        .where(*filtros)
    ) or 0
    linhas = db.execute(
        consulta.where(*filtros)
        .order_by(Treino.data_programada.is_(None), Treino.data_programada, Treino.id_treino)
        .limit(limit)
        .offset(offset)
    ).all()
    return [_resposta(*linha) for linha in linhas], total


def obter_treino(db: Session, escopo: Escopo, id_treino: int) -> TreinoResponse:
    return _buscar(db, escopo, id_treino)


# ------------------------------------------------------------------ atualizar
def atualizar_treino(
    db: Session,
    escopo: Escopo,
    id_treino: int,
    dados: Union[TreinoUpdate, TreinoUpdateProfissional],
) -> TreinoResponse:
    _buscar(db, escopo, id_treino)  # confere o escopo (404 se não for dele)
    treino = _travar(db, id_treino)
    if treino.status == "Cancelado":
        raise ConflitoError("Treino cancelado não pode ser alterado.")

    campos = dados.model_dump(exclude_unset=True)
    if "fk_id_profissional" in campos:
        _validar_profissional(db, escopo.id_academia, campos["fk_id_profissional"])
    nova_data = campos.get("data_programada")
    if nova_data is not None and nova_data < treino.data_criacao:
        raise DadoInvalidoError(
            "A data programada não pode ser anterior à data de criação do treino "
            f"({treino.data_criacao.strftime('%d/%m/%Y')})."
        )

    for campo, valor in campos.items():
        setattr(treino, campo, valor)
    _salvar(db, treino)
    return _buscar(db, escopo, id_treino)


# -------------------------------------------------------------------- cancelar
def cancelar_treino(db: Session, escopo: Escopo, id_treino: int) -> TreinoResponse:
    _buscar(db, escopo, id_treino)  # confere o escopo (404 se não for dele)
    treino = _travar(db, id_treino)
    if treino.status == "Cancelado":
        raise ConflitoError("Treino já está cancelado.")
    treino.status = "Cancelado"
    _salvar(db, treino)
    return _buscar(db, escopo, id_treino)


# ------------------------------------------------- cascata (inativar usuário)
def _cancelar_pendentes(db: Session, coluna, id_usuario: int) -> int:
    """Cancela os treinos ativos que ainda não ocorreram (hoje em diante, ou sem data)."""
    resultado = db.execute(
        update(Treino)
        .where(
            coluna == id_usuario,
            Treino.status == "Ativo",
            or_(Treino.data_programada.is_(None), Treino.data_programada >= func.current_date()),
        )
        .values(status="Cancelado")
        .execution_options(synchronize_session=False)
    )
    return resultado.rowcount


@ao_inativar("Aluno", "treinos cancelados")
def _cancelar_treinos_do_aluno(db: Session, usuario: Usuario) -> int:
    return _cancelar_pendentes(db, Treino.fk_id_aluno, usuario.id_usuario)


@ao_inativar("Profissional", "treinos cancelados")
def _cancelar_treinos_do_profissional(db: Session, usuario: Usuario) -> int:
    return _cancelar_pendentes(db, Treino.fk_id_profissional, usuario.id_usuario)
