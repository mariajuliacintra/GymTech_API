"""
Conexão com o MySQL.

- engine:       a "ponte" com o banco (mantém as conexões abertas).
- SessionLocal: fábrica de sessões (uma sessão = uma conversa com o banco).
- Base:         classe-mãe de todos os models (tabelas) do projeto.
- get_db:       dependência do FastAPI que abre uma sessão por requisição
                e garante que ela seja fechada no final.
"""
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# URL.create monta a URL com segurança, mesmo que a senha tenha
# caracteres especiais como @ ou #.
DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=settings.DB_USER,
    password=settings.DB_PASSWORD,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    database=settings.DB_NAME,
    query={"charset": "utf8mb4"},
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # testa a conexão antes de usar (evita "MySQL has gone away")
    echo=settings.DEBUG,  # com DEBUG=true, mostra os SQLs no terminal
)

SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Todos os models herdam desta classe."""


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
