"""
Alterações que o PRÓPRIO usuário (aluno ou profissional) faz nos seus dados.

Não existe rota para a academia alterar dados de aluno/profissional: aqui
quem é alterado vem sempre do token de quem está logado, nunca de um id na URL.
Toda alteração exige uma prova de identidade (código de 6 dígitos enviado por e-mail).

Passo a passo no app:
  1) POST /usuarios/me/codigo-email
  2) PATCH /alunos/me  ou  PATCH /profissionais/me, com os campos + "verificacao"
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_aluno_atual, get_profissional_atual, get_usuario_atual
from app.database import get_db
from app.models import Aluno, Profissional, Usuario
from app.schemas.usuario import (
    AlunoUpdate,
    AlunoUpdateResponse,
    ProfissionalUpdate,
    ProfissionalUpdateResponse,
)
from app.schemas.verificacao import CodigoEnviadoResponse
from app.services import usuario_service, verificacao_service

router = APIRouter(tags=["Meu perfil"])


@router.post(
    "/usuarios/me/codigo-email",
    response_model=CodigoEnviadoResponse,
    summary="Receber, por e-mail, o código para confirmar uma alteração",
)
def enviar_codigo_email(usuario: Usuario = Depends(get_usuario_atual)):
    """
    Envia um código de 6 dígitos para o e-mail cadastrado (vale 10 minutos).
    Peça só um por vez: há um intervalo de 60 segundos entre envios (429).
    """
    envio = verificacao_service.emitir_codigo_email(
        verificacao_service.conta_de_usuario(usuario),
        verificacao_service.FINALIDADE_ATUALIZAR_DADOS,
    )
    verificacao_service.despachar_email(envio)  # aqui a pessoa está logada: se falhar, ela precisa saber (503)
    destino = verificacao_service.mascarar_email(usuario.email)
    return CodigoEnviadoResponse(
        mensagem=f"Código enviado para {destino}. Ele vale por {settings.CODIGO_TTL_MINUTOS} minutos.",
        destino=destino,
    )


@router.patch(
    "/alunos/me",
    response_model=AlunoUpdateResponse,
    summary="Atualizar os meus dados (aluno)",
)
def atualizar_aluno(
    dados: AlunoUpdate,
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    """
    O aluno logado atualiza os **próprios** dados. Só os campos enviados mudam.
    Exige `verificacao` (código de 6 dígitos enviado por e-mail).
    CPF, senha, status e academia não podem ser alterados por aqui.
    """
    usuario = usuario_service.atualizar_aluno(db, aluno.usuario, dados)
    return AlunoUpdateResponse.from_usuario(usuario)


@router.patch(
    "/profissionais/me",
    response_model=ProfissionalUpdateResponse,
    summary="Atualizar os meus dados (profissional)",
)
def atualizar_profissional(
    dados: ProfissionalUpdate,
    profissional: Profissional = Depends(get_profissional_atual),
    db: Session = Depends(get_db),
):
    """
    O profissional logado atualiza os **próprios** dados. Só os campos enviados mudam.
    Exige `verificacao` (código de 6 dígitos enviado por e-mail).
    CPF, senha, status e academia não podem ser alterados por aqui.
    """
    usuario = usuario_service.atualizar_profissional(db, profissional.usuario, dados)
    return ProfissionalUpdateResponse.from_usuario(usuario)
