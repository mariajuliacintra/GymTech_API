"""
Envio de e-mail por SMTP.

Funciona com qualquer provedor SMTP. Com uma conta Google (Gmail):
    SMTP_HOST=smtp.gmail.com   SMTP_PORT=587
    SMTP_USER=seu@gmail.com    SMTP_PASSWORD=<senha de app de 16 letras>
A "senha de app" é criada em myaccount.google.com > Segurança (exige a
verificação em duas etapas ligada); a senha normal da conta NÃO funciona.

Sem SMTP_HOST configurado:
  - com DEBUG=true: o e-mail NÃO é enviado, mas a versão em texto aparece no
    terminal (útil para testar o fluxo sem configurar nada). Para ver o visual
    HTML, use a pré-visualização descrita em email_templates.py;
  - com DEBUG=false: levanta ServicoIndisponivelError (503).
"""
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.core.config import settings
from app.core.exceptions import ServicoIndisponivelError

logger = logging.getLogger("gymtech.email")


def enviar_email(
    destino: str, assunto: str, corpo: str, corpo_html: Optional[str] = None
) -> None:
    """`corpo` é o texto simples; `corpo_html` (opcional) vai junto como versão com visual."""
    if not settings.SMTP_HOST:
        if settings.DEBUG:
            logger.warning(
                "SMTP não configurado (modo DEBUG): e-mail NÃO enviado.\n"
                "Para: %s\nAssunto: %s\n%s", destino, assunto, corpo,
            )
            return
        raise ServicoIndisponivelError("O envio de e-mail não está configurado.")

    mensagem = EmailMessage()
    mensagem["From"] = settings.SMTP_FROM or settings.SMTP_USER
    mensagem["To"] = destino
    mensagem["Subject"] = assunto
    mensagem.set_content(corpo)
    if corpo_html:
        mensagem.add_alternative(corpo_html, subtype="html")

    try:
        if settings.SMTP_PORT == 465:  # porta 465 = TLS direto
            conexao = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        else:
            conexao = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        with conexao as smtp:
            if settings.SMTP_PORT != 465 and settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(mensagem)
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("Falha ao enviar e-mail para %s: %s", destino, exc)
        raise ServicoIndisponivelError(
            "Não foi possível enviar o e-mail agora. Tente novamente em instantes."
        ) from exc
