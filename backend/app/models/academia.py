from sqlalchemy import CHAR, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Academia(Base):
    __tablename__ = "academia"

    id_academia: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome_academia: Mapped[str] = mapped_column(String(100))
    email_corporativo: Mapped[str] = mapped_column(String(100), unique=True)
    senha_adm: Mapped[str] = mapped_column(String(255))
    cnpj: Mapped[str] = mapped_column(CHAR(14), unique=True)

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="academia")
