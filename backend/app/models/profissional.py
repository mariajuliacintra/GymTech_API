from typing import Optional

from sqlalchemy import CheckConstraint, Enum, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Profissional(Base):
    """
    Subtipo de usuario. A FK composta (id_usuario, tipo_perfil) garante que
    só existe profissional para um usuário cujo tipo_perfil seja 'Profissional'.
    """

    __tablename__ = "profissional"
    __table_args__ = (
        ForeignKeyConstraint(
            ["id_usuario", "tipo_perfil"],
            ["usuario.id_usuario", "usuario.tipo_perfil"],
            name="fk_profissional_usuario",
        ),
        CheckConstraint("tipo_perfil = 'Profissional'", name="ck_profissional_tipo"),
    )

    id_usuario: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    tipo_perfil: Mapped[str] = mapped_column(
        Enum("Profissional", "Aluno", name="tipo_perfil_usuario"),
        default="Profissional",
        server_default="Profissional",
    )
    especialidade: Mapped[Optional[str]] = mapped_column(String(100))
    registro_profissional: Mapped[str] = mapped_column(String(50), unique=True)

    usuario: Mapped["Usuario"] = relationship(back_populates="profissional")
