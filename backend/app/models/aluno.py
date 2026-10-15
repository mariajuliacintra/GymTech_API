from typing import Optional

from sqlalchemy import CheckConstraint, Enum, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Aluno(Base):
    """
    Subtipo de usuario. A FK composta (id_usuario, tipo_perfil) garante que
    só existe aluno para um usuário cujo tipo_perfil seja 'Aluno'.
    """

    __tablename__ = "aluno"
    __table_args__ = (
        ForeignKeyConstraint(
            ["id_usuario", "tipo_perfil"],
            ["usuario.id_usuario", "usuario.tipo_perfil"],
            name="fk_aluno_usuario",
        ),
        CheckConstraint("tipo_perfil = 'Aluno'", name="ck_aluno_tipo"),
    )

    id_usuario: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    tipo_perfil: Mapped[str] = mapped_column(
        Enum("Profissional", "Aluno", name="tipo_perfil_usuario"),
        default="Aluno",
        server_default="Aluno",
    )
    modalidade_treino: Mapped[Optional[str]] = mapped_column(String(50))
    objetivo: Mapped[Optional[str]] = mapped_column(String(150))

    usuario: Mapped["Usuario"] = relationship(back_populates="aluno")
