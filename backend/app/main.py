"""
Ponto de entrada da API.
Para rodar (dentro da pasta backend, com a venv ativada):
    uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    meus_treinos,
    treinos,
    usuarios,
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(academias.router)
app.include_router(academia_usuarios.router)
app.include_router(usuarios.router)
app.include_router(meu_perfil.router)
app.include_router(exercicios.router)
app.include_router(treinos.router)
app.include_router(meus_treinos.router)
