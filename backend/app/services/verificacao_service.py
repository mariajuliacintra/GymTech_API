"""
Verificação de identidade: "essa pessoa realmente é a dona da conta?"

Usada no esqueci-a-senha e em toda alteração de dados do usuário.
A API gera um código de 6 dígitos, envia para o e-mail cadastrado e, depois,
confere o que a pessoa digitou (regras do código em core/codigos.py).

Uso nos services (sempre nesta ordem):
    verificacao_service.conferir_prova(conta, finalidade, prova)   # 400 se não provar
    ... faz a alteração e dá commit ...
    verificacao_service.consumir_prova(conta, finalidade, prova)   # gasta o código

Consumir só DEPOIS do commit faz com que um erro de negócio (ex.: e-mail já
em uso) não obrigue a pessoa a pedir outro código.
"""
import logging
from dataclasses import dataclass

from app.core.codigos import armazenamento_codigos
from app.core.config import settings
from app.core.exceptions import ServicoIndisponivelError, VerificacaoInvalidaError
from app.models import Academia, Usuario
from app.schemas.verificacao import ProvaIdentidade
from app.services import email_service, email_templates

logger = logging.getLogger("gymtech.verificacao")

FINALIDADE_REDEFINIR_SENHA = "redefinir_senha"
FINALIDADE_ATUALIZAR_DADOS = "atualizar_dados"

# finalidade -> (assunto, motivo). O motivo completa a frase "Você recebeu este
# e-mail para ..."; o visual do e-mail está em email_templates.py.
_TEXTOS = {
    FINALIDADE_REDEFINIR_SENHA: (
        "GymTech: código para redefinir sua senha",
        "redefinição de senha",
    ),
    FINALIDADE_ATUALIZAR_DADOS: (
        "GymTech: código para confirmar a alteração dos seus dados",
        "confirmar a alteração dos seus dados",
    ),
}


@dataclass(frozen=True)
class Conta:
    """Quem está sendo verificado (academia, aluno ou profissional), de forma uniforme."""

    tipo: str  # "academia", "Aluno" ou "Profissional"
    id: int
    email: str
    nome: str  # usado na saudação do e-mail


@dataclass(frozen=True)
class EmailPendente:
    chave: tuple
    destino: str
    assunto: str
    corpo: str  # versão em texto simples
    corpo_html: str  # versão com visual


def conta_de_usuario(usuario: Usuario) -> Conta:
    return Conta(usuario.tipo_perfil, usuario.id_usuario, usuario.email, usuario.nome)


def conta_de_academia(academia: Academia) -> Conta:
    return Conta(
        "academia", academia.id_academia, academia.email_corporativo, academia.nome_academia
    )


def _chave(conta: Conta, finalidade: str) -> tuple:
    return (conta.tipo, conta.id, finalidade)


def mascarar_email(email: str) -> str:
    """'joao@gmail.com' -> 'j***@gmail.com'"""
    nome, _, dominio = email.partition("@")
    return f"{nome[:1]}***@{dominio}"


# ------------------------------------------------------------ envio (e-mail)
def emitir_codigo_email(conta: Conta, finalidade: str) -> EmailPendente:
    """Gera o código e monta o e-mail (sem enviar). 429 se pediu cedo demais."""
    chave = _chave(conta, finalidade)
    codigo = armazenamento_codigos.emitir(chave)
    assunto, motivo = _TEXTOS[finalidade]
    corpo, corpo_html = email_templates.montar_email_codigo(
        conta.nome, codigo, motivo, settings.CODIGO_TTL_MINUTOS
    )
    return EmailPendente(chave, conta.email, assunto, corpo, corpo_html)


def despachar_email(envio: EmailPendente) -> None:
    """Envia o e-mail. Se falhar, esquece o código (não há por que esperar o intervalo de reenvio)."""
    try:
        email_service.enviar_email(
            envio.destino, envio.assunto, envio.corpo, envio.corpo_html
        )
    except ServicoIndisponivelError:
        armazenamento_codigos.descartar(envio.chave)
        raise


def despachar_email_silencioso(envio: EmailPendente) -> None:
    """Para rodar em segundo plano (depois da resposta): a falha só vai para o log."""
    try:
        despachar_email(envio)
    except ServicoIndisponivelError:
        logger.error("E-mail de verificação não enviado (%s).", envio.chave[:2])


# --------------------------------------------------------------- conferência
def conferir_prova(conta: Conta, finalidade: str, prova: ProvaIdentidade) -> None:
    """Levanta VerificacaoInvalidaError (400) se o código não servir. Não gasta o código."""
    if not armazenamento_codigos.conferir(_chave(conta, finalidade), prova.codigo):
        logger.info("Código de e-mail recusado para %s.", _chave(conta, finalidade))
        raise VerificacaoInvalidaError()


def consumir_prova(conta: Conta, finalidade: str, prova: ProvaIdentidade) -> None:
    """Gasta o código (uso único). Chamar só depois que a alteração foi gravada."""
    armazenamento_codigos.consumir(_chave(conta, finalidade))
