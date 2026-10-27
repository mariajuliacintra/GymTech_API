from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Exercicio(Base):
    """
    Exercício do catálogo de uma academia (ex.: "Supino reto", grupo "Peito").

    Espelha exatamente a tabela `exercicio` do script SQL do projeto.
    Essa tabela não tem coluna de status, então excluir é DELETE de verdade
    (e o banco recusa se algum treino já usar o exercício, quando existir).
    """

    __tablename__ = "exercicio"

    id_exercicio: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fk_id_academia: Mapped[int] = mapped_column(ForeignKey("academia.id_academia"))
    nome_exercicio: Mapped[str] = mapped_column(String(100))
    grupo_muscular: Mapped[str] = mapped_column(String(50))
    descricao_execucao: Mapped[Optional[str]] = mapped_column(Text)
