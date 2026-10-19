from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    ConflitoError,
    NaoAutenticadoError,
    NaoAutorizadoError,
    NaoEncontradoError,
    TentativasExcedidasError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Liga cada erro de negócio ao status HTTP correspondente."""

    @app.exception_handler(NaoAutenticadoError)
    async def nao_autenticado_handler(request: Request, exc: NaoAutenticadoError):
        return JSONResponse(
            status_code=401,
            content={"detail": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(NaoAutorizadoError)
    async def nao_autorizado_handler(request: Request, exc: NaoAutorizadoError):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(NaoEncontradoError)
    async def nao_encontrado_handler(request: Request, exc: NaoEncontradoError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ConflitoError)
    async def conflito_handler(request: Request, exc: ConflitoError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(TentativasExcedidasError)
    async def tentativas_excedidas_handler(request: Request, exc: TentativasExcedidasError):
        return JSONResponse(
            status_code=429,
            content={"detail": str(exc)},
            headers={"Retry-After": str(exc.segundos_restantes)},
        )
