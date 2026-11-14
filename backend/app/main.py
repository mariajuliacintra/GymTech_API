"""
Ponto de entrada da API.
Para rodar (dentro da pasta backend, com a venv ativada):
    uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  (registra todas as tabelas)
from app.core.config import settings
from app.core.handlers import register_exception_handlers
from app.core.scheduler import encerrar_agendador, iniciar_agendador
from app.routes import (
    academia_usuarios,
    academias,
    agendamentos_avaliacoes,
    aulas,
    auth,
    exercicios,
    health,
    meu_perfil,
    meus_treinos,
    minhas_aulas,
    reservas_aulas,
    treinos,
    usuarios,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    iniciar_agendador()
    try:
        yield
    finally:
        encerrar_agendador()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

origins= [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(academias.router)
app.include_router(academia_usuarios.router)
app.include_router(usuarios.router)
app.include_router(meu_perfil.router)
app.include_router(exercicios.router)
app.include_router(exercicios.router_profissional)
app.include_router(exercicios.router_aluno)
app.include_router(treinos.router)
app.include_router(meus_treinos.router)
app.include_router(aulas.router)
app.include_router(minhas_aulas.router)
app.include_router(reservas_aulas.router)
app.include_router(agendamentos_avaliacoes.router)
