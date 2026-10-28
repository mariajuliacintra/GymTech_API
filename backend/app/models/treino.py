from datetime import date
from typing import Optional

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Treino(Base):
    """
    Treino de um aluno, montado por um profissional (script SQL do projeto + coluna status).

    fk_id_aluno e fk_id_profissional guardam, cada um, o id_usuario de uma
    pessoa da tabela `usuario`. Para mostrar o nome dos dois, as consultas
    juntam `usuario` duas vezes, com apelidos diferentes (veja treino_service.py).

    A tabela não tem fk_id_academia: a academia do treino é a dos usuários
    envolvidos, e a API garante que os dois sejam da mesma academia.

    "Cancelar" é mudar status para 'Cancelado' (nada é apagado).
    """

    __tablename__ = "treino"
    __table_args__ = (
        CheckConstraint(
            "data_programada IS NULL OR data_programada >= data_criacao",
            name="ck_treino_datas",
        ),
    )

    id_treino: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fk_id_aluno: Mapped[int] = mapped_column(ForeignKey("aluno.id_usuario"))
    fk_id_profissional: Mapped[int] = mapped_column(ForeignKey("profissional.id_usuario"))
    titulo_treino: Mapped[str] = mapped_column(String(100))
    data_criacao: Mapped[date] = mapped_column(Date, server_default=text("(CURRENT_DATE)"))
    data_programada: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(
        Enum("Ativo", "Cancelado", name="status_treino"), server_default="Ativo"
    )
