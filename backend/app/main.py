"""
Ponto de entrada da API.
Para rodar (dentro da pasta backend, com a venv ativada):
    uvicorn app.main:app --reload
"""
from fastapi import FastAPI

from app import models  # noqa: F401  (registra todas as tabelas)
from app.core.config import settings
from app.core.handlers import register_exception_handlers
from app.routes import (
    academia_usuarios,
    academias,
    auth,
    exercicios,
    health,
    meu_perfil,
    usuarios,
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(academias.router)
app.include_router(academia_usuarios.router)
app.include_router(usuarios.router)
app.include_router(meu_perfil.router)
app.include_router(exercicios.router)
