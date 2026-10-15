from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    CHAR,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Usuario(Base):
    """Supertipo: dados comuns a alunos e profissionais."""

    __tablename__ = "usuario"
    __table_args__ = (
        # Necessária para as FKs compostas de aluno e profissional.
        UniqueConstraint("id_usuario", "tipo_perfil", name="uq_usuario_id_tipo"),
    )

    id_usuario: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fk_id_academia: Mapped[int] = mapped_column(ForeignKey("academia.id_academia"))
    nome: Mapped[str] = mapped_column(String(100))
    cpf: Mapped[str] = mapped_column(CHAR(11), unique=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    senha: Mapped[str] = mapped_column(String(255))
    telefone: Mapped[Optional[str]] = mapped_column(CHAR(11))
    data_nascimento: Mapped[date] = mapped_column(Date)
    data_cadastro: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(
        Enum("Ativo", "Inativo", name="status_usuario"), server_default="Ativo"
    )
    tipo_perfil: Mapped[str] = mapped_column(
        Enum("Profissional", "Aluno", name="tipo_perfil_usuario")
    )

    academia: Mapped["Academia"] = relationship(back_populates="usuarios")
    aluno: Mapped[Optional["Aluno"]] = relationship(back_populates="usuario")
    profissional: Mapped[Optional["Profissional"]] = relationship(
        back_populates="usuario"
    )
