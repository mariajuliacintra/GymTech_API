"""Regras do login (academia, aluno e profissional)."""
from typing import NoReturn

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    NaoAutenticadoError,
    NaoAutorizadoError,
    TentativasExcedidasError,
)
from app.core.rate_limit import limitador_login
from app.core.security import (
    TIPO_TOKEN_ACADEMIA,
    criar_token_acesso,
    gerar_hash_senha,
    verificar_senha,
)
from app.models import Academia, Usuario
from app.schemas.auth import TokenResponse

# Hash usado quando o e-mail não existe, só para a resposta demorar o mesmo
# tempo de um login com e-mail existente (dificulta descobrir e-mails cadastrados).
_HASH_FALSO = gerar_hash_senha("senha-falsa-para-igualar-o-tempo")


def _falhar_login(chave) -> NoReturn:
    """
    Login errado: informa quantas tentativas restam ou, se acabaram,
    bloqueia (429). A mensagem é a mesma para "e-mail não existe" e
    "senha errada": não revelamos qual dos dois falhou.
    """
    restantes = limitador_login.tentativas_restantes(chave)
    if restantes <= 0:
        raise TentativasExcedidasError(limitador_login.segundos_de_bloqueio(chave))
    texto = "Resta 1 tentativa" if restantes == 1 else f"Restam {restantes} tentativas"
    raise NaoAutenticadoError(f"E-mail ou senha incorretos. {texto}.")


def _gerar_token(sub: int, tipo: str) -> TokenResponse:
    token, expira_em = criar_token_acesso(str(sub), tipo)
    return TokenResponse(access_token=token, expires_in=expira_em)


def login_academia(db: Session, email: str, senha: str) -> TokenResponse:
    chave = ("academia", email)
    limitador_login.iniciar_tentativa(chave)  # 429 se já estiver bloqueada

    academia = db.scalar(
        select(Academia).where(func.lower(Academia.email_corporativo) == email)
    )
    senha_ok = verificar_senha(senha, academia.senha_adm if academia else _HASH_FALSO)

    if academia is None or not senha_ok:
        _falhar_login(chave)

    limitador_login.limpar(chave)
    return _gerar_token(academia.id_academia, TIPO_TOKEN_ACADEMIA)


def login_usuario(db: Session, email: str, senha: str, tipo_esperado: str) -> TokenResponse:
    """
    Login de aluno ou profissional. `tipo_esperado` ('Aluno' ou 'Profissional')
    vem da rota usada: um aluno não consegue logar pela rota de profissional.
    A contagem de tentativas é por e-mail, compartilhada entre as duas rotas.
    """
    chave = ("usuario", email)
    limitador_login.iniciar_tentativa(chave)  # 429 se já estiver bloqueado

    # Se o e-mail for de outro tipo, tratamos como "não encontrado":
    # assim não dá para testar senhas pela rota errada nem descobrir o tipo.
    usuario = db.scalar(
        select(Usuario).where(
            func.lower(Usuario.email) == email,
            Usuario.tipo_perfil == tipo_esperado,
        )
    )
    senha_ok = verificar_senha(senha, usuario.senha if usuario else _HASH_FALSO)

    if usuario is None or not senha_ok:
        _falhar_login(chave)

    limitador_login.limpar(chave)  # credenciais corretas: zera a contagem

    if usuario.status != "Ativo":
        raise NaoAutorizadoError("Usuário inativo. Procure a sua academia.")

    return _gerar_token(usuario.id_usuario, usuario.tipo_perfil)
