from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AvaliacaoFisica(Base):
    """
    Ficha da avaliação física (preenchida apenas pelo profissional).
    Relação 1:1 com o agendamento (via uq_avaliacao_agendamento no banco).
    """

    __tablename__ = "avaliacao_fisica"
    __table_args__ = (
        CheckConstraint("peso > 0", name="ck_avaliacao_peso"),
        CheckConstraint("altura > 0", name="ck_avaliacao_altura"),
        CheckConstraint(
            "percentual_gordura IS NULL OR percentual_gordura BETWEEN 0 AND 100",
            name="ck_avaliacao_gordura",
        ),
    )

    id_avaliacao: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fk_id_agendamento_avaliacao: Mapped[int] = mapped_column(
        ForeignKey("agendamento_avaliacao.id_agendamento_avaliacao"), unique=True
    )
    data_avaliacao: Mapped[date] = mapped_column(Date)
    peso: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    altura: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    percentual_gordura: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2))
    massa_magra: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    medidas_corporais: Mapped[Optional[str]] = mapped_column(Text)
    observacoes_tecnicas: Mapped[Optional[str]] = mapped_column(Text)

    agendamento: Mapped["AgendamentoAvaliacao"] = relationship(
        back_populates="avaliacao_fisica"
    )
