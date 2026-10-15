from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflitoError
from app.core.security import gerar_hash_senha
from app.models import Academia
from app.schemas.academia import AcademiaCreate


def cadastrar_academia(db: Session, dados: AcademiaCreate) -> Academia:
    if db.scalar(
        select(Academia.id_academia).where(
            Academia.email_corporativo == dados.email_corporativo
        )
    ):
        raise ConflitoError("Já existe uma academia cadastrada com este e-mail.")
    if db.scalar(select(Academia.id_academia).where(Academia.cnpj == dados.cnpj)):
        raise ConflitoError("Já existe uma academia cadastrada com este CNPJ.")

    academia = Academia(
        nome_academia=dados.nome_academia,
        email_corporativo=dados.email_corporativo,
        senha_adm=gerar_hash_senha(dados.senha_adm),  # nunca a senha pura
        cnpj=dados.cnpj,
    )
    db.add(academia)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflitoError(
            "Dados em conflito com uma academia existente (e-mail ou CNPJ)."
        ) from exc
    db.refresh(academia)
    return academia
