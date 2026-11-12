from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReservaAula(Base):
    """
    Reserva de vaga feita por um aluno em uma aula.

    "Cancelar" é mudar status para 'Cancelado' (nada é apagado): assim o
    histórico fica preservado e o aluno pode voltar a reservar a mesma aula
    depois, caso mude de ideia (criando um novo registro 'Confirmado').
    """

    __tablename__ = "reserva_aula"

    id_reserva_aula: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fk_id_aula: Mapped[int] = mapped_column(ForeignKey("aula.id_aula"))
    fk_id_aluno: Mapped[int] = mapped_column(ForeignKey("aluno.id_usuario"))
    data_agendamento: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(
        Enum("Confirmado", "Cancelado", name="status_reserva_aula"),
        default="Confirmado",
        server_default="Confirmado",
    )
