from typing import Literal, Optional

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import Paginacao, get_academia_atual, get_paginacao
from app.database import get_db
from app.models import Academia
from app.schemas.usuario import (
    AlunoCadastroResponse,
    AlunoCreate,
    AlunoDeleteResponse,
    AlunoListaResponse,
    AlunoResponse,
    ProfissionalCadastroResponse,
    ProfissionalCreate,
    ProfissionalDeleteResponse,
    ProfissionalListaResponse,
    ProfissionalResponse,
    UsuarioListaResponse,
    usuario_para_response,
)
from app.services import usuario_service

# Todas as rotas daqui exigem uma academia logada. A academia vem do TOKEN,
router = APIRouter(tags=["Cadastro de usuários"])


StatusUsuario = Literal["Ativo", "Inativo"]


@router.post(
    "/alunos",
    response_model=AlunoCadastroResponse,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": AlunoCadastroResponse, "description": "Aluno inativo reativado"}},
    summary="Cadastrar (ou reativar) aluno",
)
def cadastrar_aluno(
    dados: AlunoCreate,
    response: Response,
    academia: Academia = Depends(get_academia_atual),
    db: Session = Depends(get_db),
):
    """
    A academia logada cadastra um usuário do tipo **Aluno**.

    - CPF novo: cria o aluno (**201**).
    - CPF de um aluno **inativo desta academia**: reativa o aluno e atualiza
      os dados com os enviados agora (**200**).
    - CPF de alguém ativo, de outra academia, ou de um profissional: **409**.
    """
    usuario, reativado = usuario_service.cadastrar_aluno(db, academia.id_academia, dados)
    resposta = AlunoCadastroResponse.from_usuario(usuario)
    if reativado:
        response.status_code = status.HTTP_200_OK
        resposta.mensagem = "Aluno reativado com sucesso!"
    return resposta


@router.post(
    "/profissionais",
    response_model=ProfissionalCadastroResponse,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": ProfissionalCadastroResponse, "description": "Profissional inativo reativado"}},
    summary="Cadastrar (ou reativar) profissional",
)
def cadastrar_profissional(
    dados: ProfissionalCreate,
    response: Response,
    academia: Academia = Depends(get_academia_atual),
    db: Session = Depends(get_db),
):
    """
    A academia logada cadastra um usuário do tipo **Profissional**.

    - CPF novo: cria o profissional (**201**).
    - CPF de um profissional **inativo desta academia**: reativa e atualiza
      os dados com os enviados agora (**200**).
    - CPF de alguém ativo, de outra academia, ou de um aluno: **409**.
    """
    usuario, reativado = usuario_service.cadastrar_profissional(
        db, academia.id_academia, dados
    )
    resposta = ProfissionalCadastroResponse.from_usuario(usuario)
    if reativado:
        response.status_code = status.HTTP_200_OK
        resposta.mensagem = "Profissional reativado com sucesso!"
    return resposta


@router.delete(
    "/alunos/{id_usuario}",
    response_model=AlunoDeleteResponse,
    summary="Inativar aluno",
)
def inativar_aluno(
    id_usuario: int = Path(ge=1),
    academia: Academia = Depends(get_academia_atual),
    db: Session = Depends(get_db),
):
    """
    A academia logada **inativa** um aluno dela (nada é apagado do banco).

    Tudo que estiver ligado ao aluno e ainda não tiver ocorrido é cancelado
    em cascata; o resumo vem em `cancelamentos`.
    """
    usuario, cancelamentos = usuario_service.inativar_aluno(
        db, academia.id_academia, id_usuario
    )
    return AlunoDeleteResponse(
        id_usuario=usuario.id_usuario,
        nome=usuario.nome,
        tipo_perfil=usuario.tipo_perfil,
        status=usuario.status,
        cancelamentos=cancelamentos,
    )


@router.delete(
    "/profissionais/{id_usuario}",
    response_model=ProfissionalDeleteResponse,
    summary="Inativar profissional",
)
def inativar_profissional(
    id_usuario: int = Path(ge=1),
    academia: Academia = Depends(get_academia_atual),
    db: Session = Depends(get_db),
):
    """
    A academia logada **inativa** um profissional dela (nada é apagado do banco).

    Tudo que estiver ligado ao profissional e ainda não tiver ocorrido é
    cancelado em cascata; o resumo vem em `cancelamentos`.
    """
    usuario, cancelamentos = usuario_service.inativar_profissional(
        db, academia.id_academia, id_usuario
    )
    return ProfissionalDeleteResponse(
        id_usuario=usuario.id_usuario,
        nome=usuario.nome,
        tipo_perfil=usuario.tipo_perfil,
        status=usuario.status,
        cancelamentos=cancelamentos,
    )


# -------------------------------------------------------------- listagens
# Todas listam só os usuários da academia logada (vinda do token).
@router.get("/alunos", response_model=AlunoListaResponse, summary="Listar alunos")
def listar_alunos(
    status_usuario: Optional[StatusUsuario] = Query(None, alias="status", description="Filtra por Ativo ou Inativo"),
    academia: Academia = Depends(get_academia_atual),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """Alunos da academia logada (ativos e inativos, salvo se filtrar com `?status=`)."""
    usuarios, total = usuario_service.listar_usuarios(
        db, academia.id_academia, "Aluno", status_usuario, pag.limit, pag.offset
    )
    return AlunoListaResponse(
        total=total, itens=[AlunoResponse.from_usuario(u) for u in usuarios]
    )


@router.get(
    "/profissionais",
    response_model=ProfissionalListaResponse,
    summary="Listar profissionais",
)
def listar_profissionais(
    status_usuario: Optional[StatusUsuario] = Query(None, alias="status", description="Filtra por Ativo ou Inativo"),
    academia: Academia = Depends(get_academia_atual),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """Profissionais da academia logada (ativos e inativos, salvo se filtrar com `?status=`)."""
    usuarios, total = usuario_service.listar_usuarios(
        db, academia.id_academia, "Profissional", status_usuario, pag.limit, pag.offset
    )
    return ProfissionalListaResponse(
        total=total, itens=[ProfissionalResponse.from_usuario(u) for u in usuarios]
    )


@router.get(
    "/usuarios",
    response_model=UsuarioListaResponse,
    summary="Listar alunos e profissionais juntos",
)
def listar_usuarios(
    status_usuario: Optional[StatusUsuario] = Query(None, alias="status", description="Filtra por Ativo ou Inativo"),
    academia: Academia = Depends(get_academia_atual),
    pag: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
):
    """Alunos e profissionais da academia logada, misturados (ordenados por nome)."""
    usuarios, total = usuario_service.listar_usuarios(
        db, academia.id_academia, None, status_usuario, pag.limit, pag.offset
    )
    return UsuarioListaResponse(
        total=total, itens=[usuario_para_response(u) for u in usuarios]
    )
