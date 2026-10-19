from fastapi import APIRouter, Depends

from app.core.dependencies import get_usuario_atual
from app.models import Usuario
from app.schemas.usuario import UsuarioResponse
from app.schemas.academia import AcademiaCadastroResponse

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.get("/me", response_model=AcademiaCadastroResponse, summary="Dados do usuário logado")
def meu_perfil(usuario: Usuario = Depends(get_usuario_atual)):
    """Rota protegida: devolve o aluno ou profissional dono do token."""
    return usuario
