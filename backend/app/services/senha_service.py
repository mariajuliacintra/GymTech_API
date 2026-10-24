"""
Esqueci a senha (academia, aluno e profissional).

Fluxo:
  1) POST /auth/{perfil}/esqueci-senha     -> envia um código por e-mail
  2) POST /auth/{perfil}/redefinir-senha   -> envia o código + a nova senha;
     se o código estiver certo, a senha é trocada.

Para ninguém descobrir quais e-mails estão cadastrados, o passo 1 responde
sempre igual (existindo a conta ou não) e o passo 2 usa uma mensagem única de erro.
"""
import logging
from typing import Optional, Union

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.codigos import armazenamento_codigos  # noqa: F401  (documenta a dependência)
from app.core.exceptions import ReenvioDeCodigoError, VerificacaoInvalidaError
from app.core.rate_limit import limitador_login
from app.core.security import (
    TIPO_TOKEN_ACADEMIA,
    TIPO_TOKEN_ALUNO,
    TIPO_TOKEN_PROFISSIONAL,
    gerar_hash_senha,
)
from app.models import Academia, Usuario
from app.schemas.verificacao import ProvaIdentidade
from app.services import verificacao_service as verificacao
from app.services.verificacao_service import FINALIDADE_REDEFINIR_SENHA, Conta, EmailPendente

logger = logging.getLogger("gymtech.senha")

# valor da URL -> valor do "tipo" usado no token e no banco
PERFIS = {
    "academia": TIPO_TOKEN_ACADEMIA,
    "aluno": TIPO_TOKEN_ALUNO,
    "profissional": TIPO_TOKEN_PROFISSIONAL,
}


def _buscar_conta(db: Session, perfil: str, email: str) -> Optional[Union[Academia, Usuario]]:
    """A conta dona do e-mail naquele perfil; None se não existe (ou se o usuário está inativo)."""
    tipo = PERFIS[perfil]
    if tipo == TIPO_TOKEN_ACADEMIA:
        return db.scalar(
            select(Academia).where(func.lower(Academia.email_corporativo) == email)
        )
    return db.scalar(
        select(Usuario).where(
            func.lower(Usuario.email) == email,
            Usuario.tipo_perfil == tipo,
            Usuario.status == "Ativo",  # inativo "procura a academia", como no login
        )
    )


def _conta(obj: Union[Academia, Usuario]) -> Conta:
    if isinstance(obj, Academia):
        return verificacao.conta_de_academia(obj)
    return verificacao.conta_de_usuario(obj)


def solicitar_codigo(db: Session, perfil: str, email: str) -> Optional[EmailPendente]:
    """
    Prepara o código do passo 1. Devolve o e-mail a enviar, ou None quando não
    há nada a enviar (conta inexistente/inativa, ou pediu cedo demais). Em
    todos os casos a resposta da API é a mesma. O envio em si acontece em
    segundo plano, para a resposta demorar igual com ou sem conta.
    """
    conta_obj = _buscar_conta(db, perfil, email)
    if conta_obj is None:
        return None
    try:
        return verificacao.emitir_codigo_email(_conta(conta_obj), FINALIDADE_REDEFINIR_SENHA)
    except ReenvioDeCodigoError:
        return None


def redefinir_senha(
    db: Session, perfil: str, email: str, nova_senha: str, prova: ProvaIdentidade
) -> None:
    conta_obj = _buscar_conta(db, perfil, email)
    if conta_obj is None:
        raise VerificacaoInvalidaError()  # mesma mensagem de "código errado"

    conta = _conta(conta_obj)
    verificacao.conferir_prova(conta, FINALIDADE_REDEFINIR_SENHA, prova)

    novo_hash = gerar_hash_senha(nova_senha)  # nunca a senha pura
    if isinstance(conta_obj, Academia):
        conta_obj.senha_adm = novo_hash
        chave_login = ("academia", email)
    else:
        conta_obj.senha = novo_hash
        chave_login = ("usuario", email)
    db.commit()

    verificacao.consumir_prova(conta, FINALIDADE_REDEFINIR_SENHA, prova)
    # Quem provou ser o dono da conta não precisa ficar bloqueado por erros de login antigos.
    limitador_login.limpar(chave_login)
