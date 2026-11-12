from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Aula(Base):
    """
    Aula de uma academia, dada por um profissional (script SQL do projeto).

    data_horario é um DATETIME sem fuso: vale o horário da academia
    (ver core/tempo.py). A tabela não guarda duração, só o início.

    "Cancelar" é mudar status para 'Cancelada' (nada é apagado): assim as
    reservas das aulas (reserva_aula) mantêm a referência e o histórico.
    """

    __tablename__ = "aula"
    __table_args__ = (CheckConstraint("capacidade_maxima > 0", name="ck_aula_capacidade"),)

    id_aula: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fk_id_academia: Mapped[int] = mapped_column(ForeignKey("academia.id_academia"))
    fk_id_profissional: Mapped[int] = mapped_column(ForeignKey("profissional.id_usuario"))
    nome_aula: Mapped[str] = mapped_column(String(100))
    data_horario: Mapped[datetime] = mapped_column(DateTime)
    capacidade_maxima: Mapped[int]
    status: Mapped[str] = mapped_column(
        Enum("Ativa", "Cancelada", name="status_aula"), server_default="Ativa"
    )
    tipo_aula: Mapped[str] = mapped_column(String(100))
