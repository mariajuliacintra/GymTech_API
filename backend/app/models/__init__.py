"""
Importar todos os models aqui garante que o SQLAlchemy conheça todas as
tabelas (e seus relacionamentos) assim que a aplicação inicia.
Ao criar um model novo, adicione o import abaixo.
"""
from app.models.academia import Academia
from app.models.aluno import Aluno
from app.models.profissional import Profissional
from app.models.exercicio import Exercicio
from app.models.usuario import Usuario

__all__ = ["Academia", "Usuario", "Aluno", "Profissional", "Exercicio"]
