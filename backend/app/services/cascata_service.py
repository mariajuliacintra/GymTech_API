"""
Cascata da inativação de usuários (aluno / profissional).

POR QUE EXISTE: a "deleção" aqui é só trocar usuario.status para 'Inativo'
(um UPDATE). O ON DELETE CASCADE do banco só dispara em DELETE de verdade,
então ele NÃO cancelaria nada. A cascata precisa ser feita pela aplicação.

COMO FUNCIONA: cada módulo que tiver dados ligados a um usuário (agendamentos,
treinos, avaliações...) registra aqui uma função "cancelar" com o decorator
@ao_inativar. Quando um aluno/profissional é inativado, o usuario_service
chama TODAS as funções registradas para o tipo dele, na MESMA transação:
se qualquer uma falhar, nada é gravado (nem a inativação).

COMO ADICIONAR UMA TABELA NOVA NA CASCATA (exemplo futuro):

    # app/services/agendamento_service.py
    from sqlalchemy import func, update
    from app.services.cascata_service import ao_inativar

    @ao_inativar("Aluno", "agendamentos cancelados")
    def _cancelar_agendamentos_do_aluno(db, usuario) -> int:
        resultado = db.execute(
            update(Agendamento)
            .where(
                Agendamento.fk_id_aluno == usuario.id_usuario,
                Agendamento.status == "Agendado",      # ainda não ocorreu...
                Agendamento.data_hora > func.now(),    # ...e é no futuro
            )
            .values(status="Cancelado")
        )
        return resultado.rowcount   # quantos registros foram cancelados

REGRAS PARA AS FUNÇÕES REGISTRADAS:
  - receber (db, usuario) e devolver um int (quantos registros cancelou);
  - NÃO dar commit/rollback (quem comita é o usuario_service, uma vez só);
  - cancelar só o que ainda não ocorreu (o que já aconteceu é histórico);
  - o módulo que registra precisa ser importado ao subir a API; isso já
    acontece sozinho quando o service é usado por alguma rota.
"""
from typing import Callable

from sqlalchemy.orm import Session

from app.models import Usuario

Cancelador = Callable[[Session, Usuario], int]

# tipo_perfil -> lista de (descrição, função)
_canceladores: dict[str, list[tuple[str, Cancelador]]] = {
    "Aluno": [],
    "Profissional": [],
}


def ao_inativar(tipo_perfil: str, descricao: str) -> Callable[[Cancelador], Cancelador]:
    """Decorator: registra uma função que roda quando um usuário desse tipo é inativado."""
    if tipo_perfil not in _canceladores:
        raise ValueError(f"tipo_perfil inválido: {tipo_perfil!r}")

    def registrar(funcao: Cancelador) -> Cancelador:
        _canceladores[tipo_perfil].append((descricao, funcao))
        return funcao

    return registrar


def cancelar_vinculos(db: Session, usuario: Usuario) -> dict[str, int]:
    """
    Roda todos os cancelamentos registrados para o tipo do usuário.
    Devolve um resumo {descrição: quantidade}. Não faz commit.
    """
    resumo: dict[str, int] = {}
    for descricao, funcao in _canceladores[usuario.tipo_perfil]:
        resumo[descricao] = resumo.get(descricao, 0) + funcao(db, usuario)
    return resumo
