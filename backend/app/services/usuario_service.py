"""
Regras de negócio do cadastro de usuários (feito por uma academia).

Cadastrar um aluno/profissional = criar a linha em `usuario` + a linha na
tabela filha, tudo numa ÚNICA transação: ou grava as duas, ou nenhuma.

REATIVAÇÃO: a academia não precisa saber se a pessoa já foi aluno/profissional.
Ao cadastrar um CPF que já existe, o sistema decide sozinho:
    - não existe                                    -> cria (201)
    - existe, INATIVO, da MESMA academia, mesmo tipo -> reativa e atualiza os
                                                       dados com os enviados (200)
    - qualquer outro caso                           -> 409
(ver `_validar_reativacao` para o porquê de cada bloqueio)

"Deletar" um aluno/profissional = INATIVAR (usuario.status = 'Inativo') e
cancelar em cascata o que estiver ligado a ele (ver cascata_service.py),
também numa ÚNICA transação. Nada é apagado do banco.
"""
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflitoError, NaoEncontradoError
from app.core.security import gerar_hash_senha
from app.models import Academia, Aluno, Profissional, Usuario
from app.schemas.usuario import AlunoCreate, ProfissionalCreate, UsuarioCreate
from app.services.cascata_service import cancelar_vinculos


# ------------------------------------------------------------ verificações
def _buscar_academia(db: Session, id_academia: int) -> Academia:
    academia = db.get(Academia, id_academia)
    if academia is None:
        raise NaoEncontradoError("Academia não encontrada.")
    return academia


def _buscar_por_cpf(db: Session, cpf: str) -> Optional[Usuario]:
    # Sem FOR UPDATE de propósito: travar uma linha que ainda não existe
    # (cadastro novo) pode causar deadlock no MySQL entre cadastros simultâneos.
    return db.scalar(select(Usuario).where(Usuario.cpf == cpf))


def _checar_email_livre(
    db: Session, email: str, ignorar_id: Optional[int] = None
) -> None:
    """`ignorar_id`: na reativação, o e-mail do próprio usuário não conta como duplicado."""
    consulta = select(Usuario.id_usuario).where(Usuario.email == email)
    if ignorar_id is not None:
        consulta = consulta.where(Usuario.id_usuario != ignorar_id)
    if db.scalar(consulta):
        raise ConflitoError("Já existe um usuário cadastrado com este e-mail.")


def _checar_registro_profissional(
    db: Session, registro: str, ignorar_id: Optional[int] = None
) -> None:
    consulta = select(Profissional.id_usuario).where(
        Profissional.registro_profissional == registro
    )
    if ignorar_id is not None:
        consulta = consulta.where(Profissional.id_usuario != ignorar_id)
    if db.scalar(consulta):
        raise ConflitoError("Já existe um profissional com este registro profissional.")


def _validar_reativacao(
    db: Session,
    id_academia: int,
    existente: Usuario,
    dados: UsuarioCreate,
    tipo_perfil: str,
) -> None:
    """Confere se o CPF encontrado pode ser reativado por ESTA academia, neste tipo."""
    # CPF de outra academia, ou de alguém ainda ativo: mensagem genérica, que
    # não revela quem é nem onde está (e a conta ativa nunca é sobrescrita).
    # Não transferimos entre academias: o histórico futuro (treinos, avaliações)
    # da academia antiga passaria a ser visível pela nova.
    if existente.fk_id_academia != id_academia or existente.status == "Ativo":
        raise ConflitoError("Já existe um usuário cadastrado com este CPF.")

    # Aqui o usuário é da própria academia, então podemos ser específicos.
    # Trocar o tipo (aluno <-> profissional) não é permitido: o tipo é fixado
    # pela FK composta e cada tipo tem a sua tabela filha.
    if existente.tipo_perfil != tipo_perfil:
        raise ConflitoError(
            f"Este CPF pertence a um {existente.tipo_perfil.lower()} inativo da sua "
            f"academia e não pode ser cadastrado como {tipo_perfil.lower()}."
        )

    _checar_email_livre(db, dados.email, ignorar_id=existente.id_usuario)


def _aplicar_dados_comuns(usuario: Usuario, dados: UsuarioCreate) -> None:
    """Reativação: os dados enviados agora substituem os antigos."""
    usuario.nome = dados.nome
    usuario.email = dados.email
    usuario.senha = gerar_hash_senha(dados.senha)  # nunca a senha pura
    usuario.telefone = dados.telefone
    usuario.data_nascimento = dados.data_nascimento
    usuario.status = "Ativo"


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
# Os dois cadastros devolvem (usuario, reativado): reativado=True quando o CPF
# era de um usuário inativo da academia e ele foi reativado em vez de criado.
def cadastrar_aluno(
    db: Session, id_academia: int, dados: AlunoCreate
) -> tuple[Usuario, bool]:
    _buscar_academia(db, id_academia)

    existente = _buscar_por_cpf(db, dados.cpf)
    if existente is not None:
        _validar_reativacao(db, id_academia, existente, dados, "Aluno")
        _aplicar_dados_comuns(existente, dados)
        if existente.aluno is None:  # não deveria acontecer; rede de segurança
            existente.aluno = Aluno()
        existente.aluno.modalidade_treino = dados.modalidade_treino
        existente.aluno.objetivo = dados.objetivo
        return _salvar(db, existente), True

    _checar_email_livre(db, dados.email)
    usuario = _montar_usuario(id_academia, dados, tipo_perfil="Aluno")
    usuario.aluno = Aluno(
        modalidade_treino=dados.modalidade_treino,
        objetivo=dados.objetivo,
    )
    return _salvar(db, usuario), False


def cadastrar_profissional(
    db: Session, id_academia: int, dados: ProfissionalCreate
) -> tuple[Usuario, bool]:
    _buscar_academia(db, id_academia)

    existente = _buscar_por_cpf(db, dados.cpf)
    if existente is not None:
        _validar_reativacao(db, id_academia, existente, dados, "Profissional")
        _checar_registro_profissional(
            db, dados.registro_profissional, ignorar_id=existente.id_usuario
        )
        _aplicar_dados_comuns(existente, dados)
        if existente.profissional is None:  # rede de segurança
            existente.profissional = Profissional()
        existente.profissional.especialidade = dados.especialidade
        existente.profissional.registro_profissional = dados.registro_profissional
        return _salvar(db, existente), True

    _checar_email_livre(db, dados.email)
    _checar_registro_profissional(db, dados.registro_profissional)
    usuario = _montar_usuario(id_academia, dados, tipo_perfil="Profissional")
    usuario.profissional = Profissional(
        especialidade=dados.especialidade,
        registro_profissional=dados.registro_profissional,
    )
    return _salvar(db, usuario), False


# ------------------------------------------------------------ inativação
def _inativar(
    db: Session, id_academia: int, id_usuario: int, tipo_perfil: str
) -> tuple[Usuario, dict[str, int]]:
    """
    Inativa um usuário da academia e cancela os vínculos em cascata.
    Devolve (usuario, resumo_dos_cancelamentos).
    """
    # Filtrar por academia e tipo: uma academia não mexe em usuário de outra,
    # e um id de profissional não funciona na rota de aluno. Nos dois casos
    # respondemos 404 (não revelamos que o id existe em outro lugar).
    # with_for_update trava a linha: duas requisições simultâneas não
    # rodam a cascata duas vezes.
    usuario = db.scalar(
        select(Usuario)
        .where(
            Usuario.id_usuario == id_usuario,
            Usuario.fk_id_academia == id_academia,
            Usuario.tipo_perfil == tipo_perfil,
        )
        .with_for_update()
    )
    if usuario is None:
        raise NaoEncontradoError(f"{tipo_perfil} não encontrado.")
    if usuario.status == "Inativo":
        raise ConflitoError(f"{tipo_perfil} já está inativo.")

    usuario.status = "Inativo"
    try:
        cancelamentos = cancelar_vinculos(db, usuario)
        db.commit()  # inativação + cancelamentos: tudo ou nada
    except Exception:
        db.rollback()
        raise
    db.refresh(usuario)
    return usuario, cancelamentos


def inativar_aluno(
    db: Session, id_academia: int, id_usuario: int
) -> tuple[Usuario, dict[str, int]]:
    return _inativar(db, id_academia, id_usuario, tipo_perfil="Aluno")


def inativar_profissional(
    db: Session, id_academia: int, id_usuario: int
) -> tuple[Usuario, dict[str, int]]:
    return _inativar(db, id_academia, id_usuario, tipo_perfil="Profissional")


# -------------------------------------------------------------- listagens
def listar_usuarios(
    db: Session,
    id_academia: int,
    tipo_perfil: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Usuario], int]:
    """
    Usuários (com os dados da tabela filha) de UMA academia.
    Devolve (página_de_usuarios, total_que_bate_com_o_filtro).
    """
    filtros = [Usuario.fk_id_academia == id_academia]
    if tipo_perfil:
        filtros.append(Usuario.tipo_perfil == tipo_perfil)
    if status:
        filtros.append(Usuario.status == status)

    total = db.scalar(select(func.count()).select_from(Usuario).where(*filtros)) or 0
    usuarios = db.scalars(
        select(Usuario)
        .where(*filtros)
        # carrega as filhas já na consulta (evita 1 SELECT extra por usuário)
        .options(selectinload(Usuario.aluno), selectinload(Usuario.profissional))
        .order_by(Usuario.nome, Usuario.id_usuario)
        .limit(limit)
        .offset(offset)
    ).all()
    return list(usuarios), total
