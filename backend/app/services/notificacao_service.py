"""
Notificações automáticas por e-mail para treinos próximos.

Como funciona:
  - O agendador diário (core/scheduler.py) chama `executar_rotina_diaria_treinos()`
    todos os dias no horário configurado (padrão 08:00 no fuso da academia).
  - A rotina busca todos os treinos com `status == 'Ativo'`, `notificado == False`
    e `data_programada` dentro da janela `[hoje, hoje + NOTIFICACAO_TREINO_DIAS_ANTECEDENCIA]`.
  - Para cada treino encontrado, monta o e-mail com os exercícios prescritos,
    envia via `email_service.enviar_email()` e marca `treino.notificado = True`
    (com commit individual para evitar reenvios caso um e-mail seguinte falhe).
  - Também pode ser disparada manualmente pela academia via `POST /treinos/notificar-proximos`.
"""
import logging
from collections import defaultdict
from datetime import timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.core.config import settings
from app.core.exceptions import ServicoIndisponivelError
from app.core.tempo import agora_local
from app.database import SessionLocal
from app.models import Academia, Exercicio, ItemTreino, Treino, Usuario
from app.schemas.treino import (
    NotificacaoTreinoExecucaoResponse,
    NotificacaoTreinoItemResponse,
)
from app.services import email_service, email_templates

logger = logging.getLogger("gymtech.notificacoes")


def _itens_dos_treinos(db: Session, ids_treino: list[int]) -> dict[int, list[dict]]:
    if not ids_treino:
        return {}
    linhas = db.execute(
        select(
            ItemTreino.fk_id_treino,
            Exercicio.nome_exercicio,
            Exercicio.grupo_muscular,
            ItemTreino.series,
            ItemTreino.repeticoes,
            ItemTreino.carga_sugerida,
            ItemTreino.tempo_descanso,
        )
        .join(Exercicio, Exercicio.id_exercicio == ItemTreino.fk_id_exercicio)
        .where(ItemTreino.fk_id_treino.in_(ids_treino))
        .order_by(ItemTreino.fk_id_treino, ItemTreino.id_item_treino)
    ).all()

    agrupado: dict[int, list[dict]] = defaultdict(list)
    for id_treino, nome_ex, grupo, series, reps, carga, descanso in linhas:
        agrupado[id_treino].append(
            {
                "nome_exercicio": nome_ex,
                "grupo_muscular": grupo,
                "series": series,
                "repeticoes": reps,
                "carga_sugerida": None if carga is None else float(carga),
                "tempo_descanso": None if descanso is None else descanso.strftime("%H:%M:%S"),
            }
        )
    return agrupado


def processar_lembretes_treinos(
    db: Session,
    id_academia: Optional[int] = None,
    dias_antecedencia: Optional[int] = None,
) -> NotificacaoTreinoExecucaoResponse:
    """
    Busca treinos ativos próximos ainda não notificados e envia e-mail aos alunos.
    Se `id_academia` for informado, restringe aos treinos daquela academia.
    """
    dias = (
        settings.NOTIFICACAO_TREINO_DIAS_ANTECEDENCIA
        if dias_antecedencia is None
        else dias_antecedencia
    )
    hoje = agora_local().date()
    data_limite = hoje + timedelta(days=dias)

    aluno_u = aliased(Usuario, name="notif_aluno_usuario")
    prof_u = aliased(Usuario, name="notif_prof_usuario")

    filtros = [
        Treino.status == "Ativo",
        Treino.notificado.is_(False),
        Treino.data_programada.is_not(None),
        Treino.data_programada >= hoje,
        Treino.data_programada <= data_limite,
        aluno_u.status == "Ativo",
    ]
    if id_academia is not None:
        filtros.append(aluno_u.fk_id_academia == id_academia)

    linhas = db.execute(
        select(
            Treino,
            aluno_u.nome,
            aluno_u.email,
            prof_u.nome,
            Academia.nome_academia,
        )
        .join(aluno_u, aluno_u.id_usuario == Treino.fk_id_aluno)
        .join(prof_u, prof_u.id_usuario == Treino.fk_id_profissional)
        .join(Academia, Academia.id_academia == aluno_u.fk_id_academia)
        .where(*filtros)
        .order_by(Treino.data_programada, Treino.id_treino)
    ).all()

    itens_por_treino = _itens_dos_treinos(db, [row[0].id_treino for row in linhas])

    enviados = 0
    falhas = 0
    detalhes: list[NotificacaoTreinoItemResponse] = []

    for treino, nome_aluno, email_aluno, nome_prof, nome_academia in linhas:
        dias_restantes = (treino.data_programada - hoje).days
        assunto = (
            f'GymTech: lembrete do seu treino "{treino.titulo_treino}" '
            f"({treino.data_programada.strftime('%d/%m/%Y')})"
        )
        corpo, corpo_html = email_templates.montar_email_lembrete_treino(
            nome_aluno=nome_aluno,
            titulo_treino=treino.titulo_treino,
            data_programada=treino.data_programada,
            dias_restantes=dias_restantes,
            nome_profissional=nome_prof,
            nome_academia=nome_academia,
            exercicios=itens_por_treino.get(treino.id_treino, []),
        )

        try:
            email_service.enviar_email(email_aluno, assunto, corpo, corpo_html)
            treino.notificado = True
            db.commit()
            enviados += 1
            detalhes.append(
                NotificacaoTreinoItemResponse(
                    id_treino=treino.id_treino,
                    titulo_treino=treino.titulo_treino,
                    data_programada=treino.data_programada,
                    fk_id_aluno=treino.fk_id_aluno,
                    nome_aluno=nome_aluno,
                    email_aluno=email_aluno,
                    enviado=True,
                )
            )
        except ServicoIndisponivelError as exc:
            db.rollback()
            falhas += 1
            logger.error(
                "Falha ao notificar aluno %s (treino %s): %s",
                email_aluno,
                treino.id_treino,
                exc,
            )
            detalhes.append(
                NotificacaoTreinoItemResponse(
                    id_treino=treino.id_treino,
                    titulo_treino=treino.titulo_treino,
                    data_programada=treino.data_programada,
                    fk_id_aluno=treino.fk_id_aluno,
                    nome_aluno=nome_aluno,
                    email_aluno=email_aluno,
                    enviado=False,
                    erro=str(exc),
                )
            )

    return NotificacaoTreinoExecucaoResponse(
        mensagem=(
            f"Processamento concluído: {enviados} notificação(ões) enviada(s), "
            f"{falhas} falha(s)."
        ),
        data_referencia=hoje,
        data_limite=data_limite,
        dias_antecedencia=dias,
        verificados=len(linhas),
        enviados=enviados,
        falhas=falhas,
        itens=detalhes,
    )


def executar_rotina_diaria_treinos() -> None:
    """Tarefa executada diariamente pelo agendador em segundo plano."""
    logger.info("Iniciando rotina diária de notificação de treinos próximos...")
    db = SessionLocal()
    try:
        resumo = processar_lembretes_treinos(db)
        logger.info(
            "Rotina diária finalizada: verificados=%d, enviados=%d, falhas=%d",
            resumo.verificados,
            resumo.enviados,
            resumo.falhas,
        )
    except Exception:
        logger.exception("Erro inesperado ao executar rotina diária de notificações de treino.")
    finally:
        db.close()
