"""
Regras de negócio do cadastro de usuários (feito por uma academia).

Cadastrar um aluno/profissional = criar a linha em `usuario` + a linha na
tabela filha, tudo numa ÚNICA transação: ou grava as duas, ou nenhuma.
"""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflitoError, NaoEncontradoError
from app.core.security import gerar_hash_senha
from app.models import Academia, Aluno, Profissional, Usuario
from app.schemas.usuario import AlunoCreate, ProfissionalCreate, UsuarioCreate


# ------------------------------------------------------------ verificações
def _buscar_academia(db: Session, id_academia: int) -> Academia:
    academia = db.get(Academia, id_academia)
    if academia is None:
        raise NaoEncontradoError("Academia não encontrada.")
    return academia


def _checar_duplicidade_usuario(db: Session, dados: UsuarioCreate) -> None:
    if db.scalar(select(Usuario.id_usuario).where(Usuario.cpf == dados.cpf)):
        raise ConflitoError("Já existe um usuário cadastrado com este CPF.")
    if db.scalar(select(Usuario.id_usuario).where(Usuario.email == dados.email)):
        raise ConflitoError("Já existe um usuário cadastrado com este e-mail.")


def _checar_registro_profissional(db: Session, registro: str) -> None:
    existe = db.scalar(
        select(Profissional.id_usuario).where(
            Profissional.registro_profissional == registro
        )
    )
    if existe:
        raise ConflitoError("Já existe um profissional com este registro profissional.")


def _montar_usuario(id_academia: int, dados: UsuarioCreate, tipo_perfil: str) -> Usuario:
    return Usuario(
        fk_id_academia=id_academia,
        nome=dados.nome,
        cpf=dados.cpf,
        email=dados.email,
        senha=gerar_hash_senha(dados.senha),  # nunca a senha pura
        telefone=dados.telefone,
        data_nascimento=dados.data_nascimento,
        tipo_perfil=tipo_perfil,
    )


def _salvar(db: Session, usuario: Usuario) -> Usuario:
    """Grava usuario + filha numa única transação (commit único)."""
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError as exc:
        # Rede de segurança: duas requisições simultâneas podem passar
        # pelas verificações acima e só o banco percebe a duplicidade.
        db.rollback()
        raise ConflitoError(
            "Dados em conflito com um cadastro existente "
            "(CPF, e-mail ou registro profissional)."
        ) from exc
    db.refresh(usuario)  # carrega data_cadastro, status etc. gerados pelo banco
    return usuario


# --------------------------------------------------------------- cadastros
def cadastrar_aluno(db: Session, id_academia: int, dados: AlunoCreate) -> Usuario:
    _buscar_academia(db, id_academia)
    _checar_duplicidade_usuario(db, dados)

    usuario = _montar_usuario(id_academia, dados, tipo_perfil="Aluno")
    usuario.aluno = Aluno(
        modalidade_treino=dados.modalidade_treino,
        objetivo=dados.objetivo,
    )
    return _salvar(db, usuario)


def cadastrar_profissional(
    db: Session, id_academia: int, dados: ProfissionalCreate
) -> Usuario:
    _buscar_academia(db, id_academia)
    _checar_duplicidade_usuario(db, dados)
    _checar_registro_profissional(db, dados.registro_profissional)

    usuario = _montar_usuario(id_academia, dados, tipo_perfil="Profissional")
    usuario.profissional = Profissional(
        especialidade=dados.especialidade,
        registro_profissional=dados.registro_profissional,
    )
    return _salvar(db, usuario)
