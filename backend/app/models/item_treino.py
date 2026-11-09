from datetime import time
from decimal import Decimal
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ItemTreino(Base):
    """
    Um exercício dentro de um treino, com séries, repetições, carga e descanso
    (script SQL do projeto). É a tabela que liga `treino` a `exercicio`.

    A tabela não tem coluna de ordem: a ordem dos exercícios no treino é a da
    criação das linhas (id_item_treino crescente). Por isso, ao atualizar os
    itens de um treino a lista inteira é regravada, na ordem em que foi enviada.

    ON DELETE CASCADE no treino: se uma linha de treino for apagada direto no
    banco, os itens vão junto (a API nunca apaga treino: só cancela).
    A FK do exercício NÃO tem cascata: exercício usado em algum treino não
    pode ser excluído.
    """

    __tablename__ = "item_treino"
    __table_args__ = (
        CheckConstraint("series > 0", name="ck_item_series"),
        CheckConstraint("repeticoes > 0", name="ck_item_repeticoes"),
        CheckConstraint("carga_sugerida IS NULL OR carga_sugerida >= 0", name="ck_item_carga"),
    )

    id_item_treino: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fk_id_treino: Mapped[int] = mapped_column(ForeignKey("treino.id_treino", ondelete="CASCADE"))
    fk_id_exercicio: Mapped[int] = mapped_column(ForeignKey("exercicio.id_exercicio"))
    series: Mapped[int]
    repeticoes: Mapped[int]
    carga_sugerida: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    tempo_descanso: Mapped[Optional[time]] = mapped_column(Time)
