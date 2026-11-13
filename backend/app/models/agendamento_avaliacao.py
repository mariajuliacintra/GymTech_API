from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AgendamentoAvaliacao(Base):
    """
    Agendamento de avaliação física do aluno com o profissional.
    Status 'Cancelado' invalida o agendamento.
    Status 'Realizado' é definido quando a ficha (avaliacao_fisica) é preenchida.
    """

    __tablename__ = "agendamento_avaliacao"

    id_agendamento_avaliacao: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fk_id_aluno: Mapped[int] = mapped_column(ForeignKey("aluno.id_usuario"))
    fk_id_profissional: Mapped[int] = mapped_column(ForeignKey("profissional.id_usuario"))
    data_horario: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(
        Enum("Agendado", "Realizado", "Cancelado", name="status_agend_aval"),
        default="Agendado",
        server_default="Agendado",
    )

    # Relação 1:1. O uselist=False garante que o ORM trate como um objeto único.
    avaliacao_fisica: Mapped["AvaliacaoFisica"] = relationship(
        back_populates="agendamento", uselist=False
    )
