from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health():
    """Confere se a API está no ar."""
    return {"status": "ok"}


@router.get("/db")
def health_db(db: Session = Depends(get_db)):
    """Confere se a API consegue falar com o MySQL."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503, detail="Não foi possível conectar ao banco de dados."
        )
    return {"status": "ok", "database": "connected"}
