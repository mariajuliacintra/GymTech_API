"""
Regras do CRUD de exercícios (feito pela ACADEMIA, sempre com o id vindo do token).

- Uma academia só enxerga e mexe nos exercícios DELA: exercício de outra
  academia responde 404, igual a um id que não existe (não revela que existe).
- Não pode haver dois exercícios com o mesmo nome na mesma academia (409).
- Excluir apaga a linha de verdade (a tabela não tem coluna de status). Se o
  exercício já estiver em uso por outra tabela (ex.: treinos), o banco recusa
  a exclusão e a API responde 409, sem apagar nada.
"""
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflitoError, NaoEncontradoError
from app.models import Exercicio
from app.schemas.exercicio import ExercicioCreate, ExercicioResponse, ExercicioUpdate


def _checar_nome_livre(
    db: Session, id_academia: int, nome: str, ignorar_id: Optional[int] = None
) -> None:
    consulta = select(Exercicio.id_exercicio).where(
        Exercicio.fk_id_academia == id_academia,
        func.lower(Exercicio.nome_exercicio) == nome.lower(),
    )
    if ignorar_id is not None:
        consulta = consulta.where(Exercicio.id_exercicio != ignorar_id)
    if db.scalar(consulta):
        raise ConflitoError("Já existe um exercício com este nome.")


def _salvar(db: Session, exercicio: Exercicio) -> Exercicio:
    db.add(exercicio)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflitoError("Não foi possível salvar o exercício.") from exc
    db.refresh(exercicio)
    return exercicio


def _buscar(
    db: Session, id_academia: int, id_exercicio: int, travar: bool = False
) -> Exercicio:
    """O exercício, só se for desta academia. `travar` bloqueia a linha até o commit (evita duas alterações ao mesmo tempo)."""
    consulta = select(Exercicio).where(
        Exercicio.id_exercicio == id_exercicio, Exercicio.fk_id_academia == id_academia
    )
    if travar:
        consulta = consulta.with_for_update()
    exercicio = db.scalar(consulta)
    if exercicio is None:
        raise NaoEncontradoError("Exercício não encontrado.")
    return exercicio


# ------------------------------------------------------------------- cadastro
def cadastrar_exercicio(db: Session, id_academia: int, dados: ExercicioCreate) -> Exercicio:
    _checar_nome_livre(db, id_academia, dados.nome_exercicio)
    exercicio = Exercicio(
        fk_id_academia=id_academia,
        nome_exercicio=dados.nome_exercicio,
        grupo_muscular=dados.grupo_muscular,
        descricao_execucao=dados.descricao_execucao,
    )
    return _salvar(db, exercicio)


# ------------------------------------------------------------------- consulta
def listar_exercicios(
    db: Session,
    id_academia: int,
    grupo_muscular: Optional[str] = None,
    busca: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Exercicio], int]:
    """Exercícios da academia, em ordem alfabética. Devolve (página, total)."""
    filtros = [Exercicio.fk_id_academia == id_academia]
    if grupo_muscular:
        filtros.append(func.lower(Exercicio.grupo_muscular) == grupo_muscular.lower())
    if busca:
        # autoescape: "%" e "_" digitados na busca valem como texto comum
        filtros.append(Exercicio.nome_exercicio.icontains(busca, autoescape=True))

    total = db.scalar(select(func.count()).select_from(Exercicio).where(*filtros)) or 0
    exercicios = db.scalars(
        select(Exercicio)
        .where(*filtros)
        .order_by(Exercicio.nome_exercicio, Exercicio.id_exercicio)
        .limit(limit)
        .offset(offset)
    ).all()
    return list(exercicios), total


def obter_exercicio(db: Session, id_academia: int, id_exercicio: int) -> Exercicio:
    return _buscar(db, id_academia, id_exercicio)


# ------------------------------------------------------------------ atualizar
def atualizar_exercicio(
    db: Session, id_academia: int, id_exercicio: int, dados: ExercicioUpdate
) -> Exercicio:
    exercicio = _buscar(db, id_academia, id_exercicio, travar=True)

    campos = dados.model_dump(exclude_unset=True)
    novo_nome = campos.get("nome_exercicio")
    if novo_nome is not None and novo_nome.lower() != exercicio.nome_exercicio.lower():
        _checar_nome_livre(db, id_academia, novo_nome, ignorar_id=id_exercicio)

    for campo, valor in campos.items():
        setattr(exercicio, campo, valor)
    return _salvar(db, exercicio)


# -------------------------------------------------------------------- excluir
def excluir_exercicio(db: Session, id_academia: int, id_exercicio: int) -> ExercicioResponse:
    """Apaga o exercício. Devolve uma cópia dos dados dele (a linha deixa de existir)."""
    exercicio = _buscar(db, id_academia, id_exercicio, travar=True)
    copia = ExercicioResponse.model_validate(exercicio)  # tirar a foto ANTES de apagar
    db.delete(exercicio)
    try:
        db.commit()
    except IntegrityError as exc:  # chave estrangeira: outra tabela ainda usa este exercício
        db.rollback()
        raise ConflitoError(
            "Este exercício está em uso e não pode ser excluído."
        ) from exc
    return copia
